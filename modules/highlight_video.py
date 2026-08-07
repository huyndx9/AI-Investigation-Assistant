"""
Tạo bản video có vẽ khung + nhãn cho các track ứng viên (kết quả tìm kiếm),
dùng để xem trực tiếp trong UI — không phải để xử lý AI (source gốc không
đổi, xem modules/video_transcode.py).

Khác với modules/visualize_tracks.py (công cụ debug, chỉ ghi lại các keyframe
đã xử lý nên video output ngắn/giật): hàm ở đây duyệt TOÀN BỘ frame gốc để
giữ video mượt, và "giữ" vị trí khung ở giá trị keyframe gần nhất cho tới khi
có cập nhật mới hoặc track đã kết thúc — khung sẽ nhảy vị trí ở mỗi keyframe
thay vì mất hẳn giữa 2 lần lấy mẫu.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).parent))
from video_transcode import transcode_for_web  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def _hex_to_bgr(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return (b, g, r)


ARROW_COLOR_BGR = (255, 160, 40)  # xanh dương nhạt (BGR) — mũi tên cho track KHÔNG phải ứng viên khớp


def build_highlighted_video(
    db_path: str,
    source_path: str,
    video_id: str,
    tracks: list[dict],  # [{"track_id": str, "label": str, "color": "#rrggbb"}, ...] — ứng viên khớp, vẽ KHUNG
    output_path: str,
    arrow_track_ids: list[str] | None = None,  # track ĐÃ được tạo nhưng KHÔNG phải ứng viên khớp — vẽ MŨI TÊN nhỏ trên đầu
) -> str:
    """Vẽ khung (ứng viên khớp) + mũi tên nhỏ (mọi track khác đã được tạo,
    không phải ứng viên) lên toàn bộ video, xuất ra bản mp4 phát-được-trên-
    trình-duyệt tại output_path (cache: gọi lại với cùng output_path sẽ bỏ
    qua nếu file đã tồn tại).

    Mũi tên giúp điều tra viên phân biệt 2 loại "không thấy trong kết quả":
    (a) người ĐÃ được hệ thống phát hiện/theo dõi nhưng không khớp đủ điểm
    (có mũi tên, không có khung) — lỗi ở bước so khớp; (b) người hệ thống
    KHÔNG HỀ phát hiện được (không có gì cả) — lỗi ở bước detect. Trước đây
    chỉ vẽ khung ứng viên khớp nên 2 trường hợp này không phân biệt được
    bằng mắt (xem WORKLOG.md)."""
    if Path(output_path).is_file():
        return output_path

    import sqlite3
    conn = sqlite3.connect(db_path)
    box_track_ids = [t["track_id"] for t in tracks]
    arrow_track_ids = [tid for tid in (arrow_track_ids or []) if tid not in set(box_track_ids)]
    all_track_ids = box_track_ids + arrow_track_ids
    placeholders = ",".join("?" * len(all_track_ids))
    rows = conn.execute(
        f"""SELECT track_id, frame_number, bbox_x, bbox_y, bbox_w, bbox_h
            FROM track_crops WHERE track_id IN ({placeholders}) ORDER BY frame_number""",
        all_track_ids,
    ).fetchall()
    conn.close()

    style_by_track = {t["track_id"]: ("box", t["label"], _hex_to_bgr(t["color"])) for t in tracks}
    for tid in arrow_track_ids:
        style_by_track[tid] = ("arrow", None, ARROW_COLOR_BGR)
    last_frame_by_track = {}
    for track_id, frame_number, *_ in rows:
        last_frame_by_track[track_id] = max(last_frame_by_track.get(track_id, -1), frame_number)

    updates_by_frame: dict[int, list[tuple]] = {}
    for track_id, frame_number, x, y, w, h in rows:
        updates_by_frame.setdefault(frame_number, []).append((track_id, x, y, w, h))

    cap = cv2.VideoCapture(source_path)
    if not cap.isOpened():
        raise RuntimeError(f"Không mở được video gốc: {source_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w_frame = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h_frame = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    intermediate_path = str(Path(output_path).with_suffix(".raw.mp4"))
    Path(intermediate_path).parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(intermediate_path, fourcc, fps, (w_frame, h_frame))

    current_boxes: dict[str, tuple[int, int, int, int]] = {}
    frame_number = -1
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_number += 1

        for track_id, x, y, w, h in updates_by_frame.get(frame_number, []):
            current_boxes[track_id] = (x, y, w, h)

        for track_id in [tid for tid in current_boxes if frame_number > last_frame_by_track.get(tid, -1)]:
            del current_boxes[track_id]

        for track_id, (x, y, w, h) in current_boxes.items():
            kind, label, color = style_by_track[track_id]
            if kind == "box":
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, label, (x, max(0, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)
            else:
                # Mũi tên nhỏ trỏ xuống đầu — không che mặt/thân như khung,
                # đủ để nhận biết "đã có track" mà không nhầm với ứng viên khớp.
                tip_x, tip_y = x + w // 2, max(0, y - 2)
                start = (tip_x, max(0, tip_y - 18))
                cv2.arrowedLine(frame, start, (tip_x, tip_y), color, 2, cv2.LINE_AA, tipLength=0.5)

        writer.write(frame)

    cap.release()
    writer.release()

    transcode_for_web(intermediate_path, output_path)
    Path(intermediate_path).unlink(missing_ok=True)
    return output_path
