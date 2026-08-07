"""
Phát hiện + sửa track bị "nhảy người" — 1 track_id nhưng giữa chừng tracker
(ByteTrack/BoT-SORT ở modules/pipeline_ingest.py) gán nhầm sang 1 người khác
(thường do che khuất hoặc 2 người đi cắt ngang nhau). Xác nhận bằng mắt qua
crop ảnh thật (xem WORKLOG.md) trước khi viết module này — không suy đoán.

Cách phát hiện: với mỗi track, quét mọi điểm chia đôi (theo thứ tự khung
hình), so sánh embedding trung bình nửa trái vs nửa phải. Nếu độ tương đồng
thấp nhất tìm được <= EMBED_SIM_FLOOR (ngưỡng "khác người" đã hiệu chỉnh sẵn
trong demo_search.py) thì rất có khả năng đây là 1 track bị gộp nhầm 2 người
— tách tại điểm chia đôi có tương đồng thấp nhất đó.

Giới hạn đã biết: chỉ phát hiện được ĐÚNG 1 điểm gãy mỗi track (đủ cho phần
lớn trường hợp quan sát được — track bị gộp bởi 1 lần chuyển ID). Track bị
gộp nhiều hơn 2 người (hiếm) sẽ cần chạy lại module này nhiều lần (mỗi lần
tách xong, track con lại được quét ở lần chạy sau).

Mặc định CHỈ BÁO CÁO (dry-run), không sửa DB — dùng --apply để thực sự tách.
Việc tách track là sửa dữ liệu điều tra đã có, nên cố tình không mặc định
tự động ghi, khác với các script backfill khác trong dự án.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from demo_search import EMBED_SIM_FLOOR  # noqa: E402 — dùng lại ngưỡng đã hiệu chỉnh, không bịa số mới

MIN_CROPS_PER_SIDE = 2  # cần tối thiểu vài crop mỗi bên để mean-pool có ý nghĩa


def _load_track_embeddings(db_path: str, track_id: str) -> list[tuple[int, str, np.ndarray]]:
    """Trả về [(frame_number, crop_path, embedding), ...] sắp theo khung hình."""
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT tc.frame_number, tc.crop_path, fe.embedding
           FROM track_crops tc JOIN features_embedding fe
             ON fe.track_id = tc.track_id AND fe.crop_path = tc.crop_path
           WHERE tc.track_id = ? ORDER BY tc.frame_number""",
        (track_id,),
    ).fetchall()
    conn.close()
    return [(fn, cp, np.frombuffer(blob, dtype=np.float32)) for fn, cp, blob in rows]


def find_split_point(items: list[tuple[int, str, np.ndarray]]) -> tuple[int, float] | None:
    """items đã sắp theo khung hình. Trả về (chỉ số điểm chia, độ tương đồng
    thấp nhất) nếu tìm thấy điểm nghi ngờ "nhảy người", None nếu không."""
    n = len(items)
    if n < MIN_CROPS_PER_SIDE * 2:
        return None
    embeddings = [e for _, _, e in items]
    best_split, best_sim = None, 1.0
    for split in range(MIN_CROPS_PER_SIDE, n - MIN_CROPS_PER_SIDE + 1):
        left = np.mean(embeddings[:split], axis=0)
        right = np.mean(embeddings[split:], axis=0)
        ln, rn = np.linalg.norm(left), np.linalg.norm(right)
        if ln == 0 or rn == 0:
            continue
        sim = float(np.dot(left, right) / (ln * rn))
        if sim < best_sim:
            best_sim, best_split = sim, split
    if best_split is None or best_sim > EMBED_SIM_FLOOR:
        return None
    return best_split, best_sim


def scan_for_candidates(db_path: str, case_id: str | None = None) -> list[dict]:
    """Quét toàn bộ track (hoặc trong 1 case) tìm ứng viên nghi "nhảy người"."""
    conn = sqlite3.connect(db_path)
    if case_id:
        track_rows = conn.execute(
            "SELECT track_id, video_id, case_id FROM tracks WHERE case_id = ?", (case_id,)
        ).fetchall()
    else:
        track_rows = conn.execute("SELECT track_id, video_id, case_id FROM tracks").fetchall()
    conn.close()

    candidates = []
    for track_id, video_id, cid in track_rows:
        items = _load_track_embeddings(db_path, track_id)
        result = find_split_point(items)
        if result is None:
            continue
        split_idx, sim = result
        candidates.append({
            "track_id": track_id, "video_id": video_id, "case_id": cid,
            "split_idx": split_idx, "similarity": sim, "n_crops": len(items),
            "split_frame": items[split_idx][0],
        })
    candidates.sort(key=lambda c: c["similarity"])
    return candidates


def split_track(db_path: str, track_id: str) -> str | None:
    """Tách 1 track tại điểm nghi ngờ nhất. Trả về track_id mới nếu đã tách,
    None nếu track này không đủ điều kiện tách (không tìm thấy điểm gãy)."""
    items = _load_track_embeddings(db_path, track_id)
    result = find_split_point(items)
    if result is None:
        return None
    split_idx, _sim = result

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT case_id, video_id, local_track_index FROM tracks WHERE track_id = ?", (track_id,)
    ).fetchone()
    if row is None:
        conn.close()
        return None
    case_id, video_id, _old_local_index = row

    max_local = conn.execute(
        "SELECT MAX(local_track_index) FROM tracks WHERE video_id = ?", (video_id,)
    ).fetchone()[0]
    new_local_index = (max_local or 0) + 1
    new_track_id = f"{video_id}_t{new_local_index}"

    second_half_crop_paths = [cp for _, cp, _ in items[split_idx:]]
    first_half_last_frame = items[split_idx - 1][0]
    second_half_first_frame = items[split_idx][0]
    second_half_last_frame = items[-1][0]

    conn.execute("UPDATE tracks SET last_frame = ? WHERE track_id = ?", (first_half_last_frame, track_id))
    conn.execute(
        """INSERT INTO tracks (track_id, case_id, video_id, local_track_index, first_frame, last_frame)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (new_track_id, case_id, video_id, new_local_index, second_half_first_frame, second_half_last_frame),
    )
    placeholders = ",".join("?" * len(second_half_crop_paths))
    for table in ("track_crops", "features_appearance", "features_embedding"):
        conn.execute(
            f"UPDATE {table} SET track_id = ? WHERE track_id = ? AND crop_path IN ({placeholders})",
            (new_track_id, track_id, *second_half_crop_paths),
        )
    conn.commit()
    conn.close()
    return new_track_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Phát hiện/sửa track bị nhảy sang người khác.")
    parser.add_argument("--db-path", default="case.db")
    parser.add_argument("--case-id", default=None, help="Chỉ quét 1 case (bỏ trống = quét toàn DB).")
    parser.add_argument("--apply", action="store_true", help="Thực sự tách track (mặc định chỉ báo cáo).")
    args = parser.parse_args()

    candidates = scan_for_candidates(args.db_path, case_id=args.case_id)
    if not candidates:
        print("Không tìm thấy track nào nghi ngờ bị nhảy người.")
        return

    print(f"Tìm thấy {len(candidates)} track nghi ngờ bị nhảy người:")
    for c in candidates:
        print(f"  sim={c['similarity']:.3f}  n_crops={c['n_crops']:3d}  "
              f"split_frame={c['split_frame']}  track={c['track_id']}  case={c['case_id']}")

    if not args.apply:
        print("\n(Chế độ báo cáo — không sửa DB. Chạy lại kèm --apply để thực sự tách.)")
        return

    print("\nĐang tách...")
    for c in candidates:
        new_id = split_track(args.db_path, c["track_id"])
        if new_id:
            print(f"  {c['track_id']} -> giữ nguyên (phần đầu) + tách thêm {new_id} (phần sau)")
        else:
            print(f"  {c['track_id']} -> bỏ qua (không còn đủ điều kiện tách, có thể đã bị đổi)")


if __name__ == "__main__":
    main()
