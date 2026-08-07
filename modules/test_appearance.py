"""
Script test cho Module 2 (modules/appearance.py).

Chạy trích xuất appearance trên vài crop mẫu của một track, in kết quả ra
console để kiểm tra bằng mắt xem màu suy luận có hợp lý không.

Cách chạy:
    python modules/test_appearance.py --case-id TEST_CASE_01 --limit 5
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from appearance import (  # noqa: E402
    COLOR_NAMES_VI, HAIRSTYLE_NAMES_VI, HAT_NAMES_VI, SHOES_NAMES_VI, SLEEVE_NAMES_VI,
    extract_appearance_from_file,
)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Module 2 trên vài crop mẫu")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--db-path", default="case.db")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db_path)
    rows = conn.execute(
        """SELECT c.track_id, c.crop_path, c.mask_polygon, c.bbox_x, c.bbox_y
           FROM track_crops c JOIN tracks t ON t.track_id = c.track_id
           WHERE t.case_id = ?
           ORDER BY RANDOM() LIMIT ?""",
        (args.case_id, args.limit),
    ).fetchall()
    conn.close()

    if not rows:
        print(f"Không tìm thấy crop nào cho case {args.case_id}. Đã chạy pipeline_ingest chưa?")
        return

    for track_id, crop_path, mask_polygon_json, bbox_x, bbox_y in rows:
        mask_polygon = json.loads(mask_polygon_json) if mask_polygon_json else None
        result = extract_appearance_from_file(crop_path, mask_polygon, bbox_x, bbox_y)
        print(f"--- track={track_id}")
        print(f"    crop: {crop_path}")
        print(f"    áo   : {COLOR_NAMES_VI[result['color_top']]} (conf={result['color_top_confidence']})")
        print(f"    quần : {COLOR_NAMES_VI[result['color_bottom']]} (conf={result['color_bottom_confidence']})")
        print(f"    tay  : {SLEEVE_NAMES_VI[result['sleeve_length']]} (conf={result['sleeve_length_confidence']})")
        print(f"    mũ   : {HAT_NAMES_VI[result['has_hat']]} (conf={result['has_hat_confidence']})")
        print(f"    tóc  : {HAIRSTYLE_NAMES_VI[result['hairstyle']]} (conf={result['hairstyle_confidence']})")
        print(f"    giày : {SHOES_NAMES_VI[result['has_shoes']]} (conf={result['has_shoes_confidence']})")


if __name__ == "__main__":
    main()
