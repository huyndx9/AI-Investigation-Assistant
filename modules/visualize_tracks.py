"""
Công cụ kiểm tra bằng mắt cho Module 1 — không thuộc pipeline chính thức,
chỉ dùng để người dùng tự xác nhận detection/tracking có hợp lý không.

Đọc lại đúng bbox + track_id đã lưu trong case.db (không chạy lại model —
đảm bảo video xem được khớp 100% với dữ liệu thật đã ghi), vẽ đè lên từng
keyframe của video gốc, xuất ra một video mới để xem bằng trình phát video
bất kỳ (VLC, Windows Media Player, ...).

Cách chạy:
    python modules/visualize_tracks.py --video-id <video_id> --db-path case.db --output annotated.mp4

Lấy video_id từ output của modules/test_pipeline_ingest.py hoặc query:
    SELECT video_id, source_path FROM videos;
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Mỗi track_id một màu ổn định (dựa trên hash) để dễ theo dõi qua các frame
_COLOR_PALETTE = [
    (66, 135, 245), (52, 199, 89), (255, 149, 0), (255, 45, 85),
    (175, 82, 222), (0, 199, 190), (255, 214, 10), (191, 90, 242),
]


def _color_for_track(track_id: str) -> tuple[int, int, int]:
    return _COLOR_PALETTE[hash(track_id) % len(_COLOR_PALETTE)]


def visualize(video_id: str, db_path: str = "case.db", output_path: str | None = None) -> str:
    conn = sqlite3.connect(db_path)
    video_row = conn.execute(
        "SELECT source_path, fps FROM videos WHERE video_id = ?", (video_id,)
    ).fetchone()
    if video_row is None:
        raise ValueError(f"Không tìm thấy video_id={video_id} trong {db_path}")
    source_path, fps = video_row

    rows = conn.execute(
        """SELECT frame_number, track_id, bbox_x, bbox_y, bbox_w, bbox_h, detection_confidence, mask_polygon
           FROM track_crops
           WHERE track_id IN (SELECT track_id FROM tracks WHERE video_id = ?)
           ORDER BY frame_number""",
        (video_id,),
    ).fetchall()
    conn.close()

    if not rows:
        raise ValueError(f"Không có track_crops nào cho video_id={video_id} — chưa ingest hay 0 track?")

    boxes_by_frame: dict[int, list[tuple]] = defaultdict(list)
    for frame_number, track_id, x, y, w, h, conf, mask_polygon in rows:
        polygon = np.array(json.loads(mask_polygon), dtype=np.int32) if mask_polygon else None
        boxes_by_frame[frame_number].append((track_id, x, y, w, h, conf, polygon))

    frame_numbers = sorted(boxes_by_frame.keys())

    cap = cv2.VideoCapture(source_path)
    if not cap.isOpened():
        raise RuntimeError(f"Không mở lại được video gốc: {source_path}")

    output_path = output_path or str(Path(source_path).with_suffix("")) + "_annotated.mp4"
    writer = None
    frames_written = 0

    for frame_number in frame_numbers:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ok, frame = cap.read()
        if not ok:
            continue

        if writer is None:
            h_frame, w_frame = frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_path, fourcc, max(1.0, fps or 5.0), (w_frame, h_frame))

        for track_id, x, y, w, h, conf, polygon in boxes_by_frame[frame_number]:
            color = _color_for_track(track_id)
            label = f"{track_id.split('_')[-1]} ({conf:.2f})"

            if polygon is not None and len(polygon) >= 3:
                # Tô mờ + viền đúng hình người — giúp phân biệt 2 người đứng
                # gần nhau dù khung chữ nhật của họ chồng lấn.
                overlay = frame.copy()
                cv2.fillPoly(overlay, [polygon], color)
                cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, dst=frame)
                cv2.polylines(frame, [polygon], True, color, 2, cv2.LINE_AA)
            # Khung chữ nhật mỏng vẫn giữ lại làm tham chiếu (vùng model thực
            # sự dùng để ghép track — vẫn là bbox, không phải mask, xem ghi
            # chú trong pipeline_ingest.py).
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 1)
            cv2.putText(
                frame, label, (x, max(0, y - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA,
            )
        cv2.putText(
            frame, f"frame {frame_number}", (10, 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA,
        )

        writer.write(frame)
        frames_written += 1

    cap.release()
    if writer is not None:
        writer.release()

    print(f"Đã ghi {frames_written} keyframe có annotation vào: {output_path}")
    print("Mở file này bằng VLC / Windows Media Player để xem trực tiếp.")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Xuất video có vẽ bbox + track_id để kiểm tra bằng mắt")
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--db-path", default="case.db")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    visualize(args.video_id, db_path=args.db_path, output_path=args.output)


if __name__ == "__main__":
    main()
