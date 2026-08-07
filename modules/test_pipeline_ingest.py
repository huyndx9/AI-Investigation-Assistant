"""
Script test cho Module 1 (modules/pipeline_ingest.py).

Chạy thử pipeline trên một video mẫu, in ra số keyframe/track/crop đã xử lý,
và kiểm tra sơ bộ dữ liệu đã ghi vào case.db + thư mục output/.

Cách chạy:
    python modules/test_pipeline_ingest.py --video test_assets/vtest.avi
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
from pipeline_ingest import ingest_video  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Module 1 trên một video mẫu")
    parser.add_argument("--video", required=True)
    parser.add_argument("--case-id", default="TEST_CASE_01")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--db-path", default="case.db")
    parser.add_argument("--sample-fps", type=float, default=5.0)
    args = parser.parse_args()

    print(f"[test] Ingest video: {args.video}")
    result = ingest_video(
        case_id=args.case_id,
        video_path=args.video,
        output_dir=args.output_dir,
        db_path=args.db_path,
        case_name="Case test tự động",
        camera_label="cam_test_1",
        sample_fps=args.sample_fps,
    )

    print()
    print("=== Kết quả ingest ===")
    print(f"case_id            : {result.case_id}")
    print(f"video_id           : {result.video_id}")
    print(f"tổng số frame      : {result.total_frames}")
    print(f"keyframe đã xử lý  : {result.keyframes_processed}")
    print(f"số track phát hiện : {result.tracks_found}")
    print(f"số crop đã lưu     : {result.crops_saved}")

    print()
    print("=== Kiểm tra trong case.db ===")
    conn = sqlite3.connect(args.db_path)
    n_cases = conn.execute("SELECT COUNT(*) FROM cases WHERE case_id = ?", (args.case_id,)).fetchone()[0]
    n_videos = conn.execute("SELECT COUNT(*) FROM videos WHERE video_id = ?", (result.video_id,)).fetchone()[0]
    n_tracks = conn.execute("SELECT COUNT(*) FROM tracks WHERE video_id = ?", (result.video_id,)).fetchone()[0]
    n_crops = conn.execute(
        "SELECT COUNT(*) FROM track_crops WHERE track_id IN (SELECT track_id FROM tracks WHERE video_id = ?)",
        (result.video_id,),
    ).fetchone()[0]
    conn.close()
    print(f"cases   : {n_cases} (kỳ vọng 1)")
    print(f"videos  : {n_videos} (kỳ vọng 1)")
    print(f"tracks  : {n_tracks} (kỳ vọng = số track phát hiện ở trên)")
    print(f"crops   : {n_crops} (kỳ vọng = số crop đã lưu ở trên)")

    print()
    print("=== Kiểm tra thư mục crop trên đĩa ===")
    crops_dir = Path(args.output_dir) / args.case_id / "crops"
    if crops_dir.exists():
        track_dirs = sorted(p for p in crops_dir.iterdir() if p.is_dir())
        print(f"Số thư mục track trong {crops_dir}: {len(track_dirs)}")
        for td in track_dirs[:5]:
            n_files = len(list(td.glob("*.jpg")))
            print(f"  - {td.name}: {n_files} ảnh crop")
    else:
        print(f"KHÔNG tìm thấy thư mục {crops_dir} — có thể không phát hiện được người nào.")

    if result.tracks_found == 0:
        print()
        print("[cảnh báo] Không phát hiện track nào. Nếu video test có người thật mà vẫn")
        print("ra 0 track, kiểm tra lại conf_threshold hoặc chất lượng model detection.")


if __name__ == "__main__":
    main()
