"""
Ground-truth tự động cho việc đo lường chất lượng xếp hạng (ưu tiên #1 đã
thống nhất: "tăng độ chính xác ranking" — cần đo được TRƯỚC khi tinh chỉnh,
tránh "code chạy nhưng không biết có cải thiện chất lượng hay không").

Thay vì gán nhãn tay từ đầu (chậm, tốn công), tận dụng 2 nguồn suy ra được
trực tiếp từ dữ liệu đã có — nhưng ĐỘ TIN CẬY KHÁC NHAU, phải phân biệt rõ:

1. CẶP "KHÁC NGƯỜI" (nhãn "different") — 2 track cùng 1 video có khoảng thời
   gian xuất hiện GIAO NHAU. Đây là suy luận THUẦN THỜI GIAN, không dựa vào
   bất kỳ giả định nào của mô hình đang được đánh giá — 1 người không thể là
   2 track cùng lúc (logic y hệt bản vá group_top_k_per_video() trong
   demo_search.py). ĐÁNG TIN CẬY 100%.

2. CẶP "CÙNG NGƯỜI" (nhãn "same") — nửa đầu vs nửa sau của 1 track ĐỦ ỔN
   ĐỊNH NỘI TẠI (không bị track_split.py nghi ngờ nhảy người). Đây là suy
   luận YẾU HƠN — dùng ngưỡng RIÊNG (POSITIVE_COHERENCE_THRESHOLD, cao hơn
   hẳn EMBED_SIM_FLOOR đang được đánh giá) để giảm rủi ro circular reasoning
   (không thể dùng đúng ngưỡng đang cần kiểm chứng để tạo ra dữ liệu kiểm
   chứng ngưỡng đó). Vẫn có thể sai nếu track bị nhảy người NHẸ mà chưa đủ
   để vượt ngưỡng — coi đây là điểm khởi đầu, không phải nhãn hoàn hảo.

Loại trừ track thuộc video debug/visualization (vtest_seg_annotated.mp4,
video_id=7c082977-87d6-474f-9c7f-4633145fae6b) — đã xác nhận không phải
ảnh CCTV thật, xem WORKLOG.md.
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from demo_search import (  # noqa: E402
    ATTR_WEIGHT, EMBED_SIM_CEIL, EMBED_SIM_FLOOR, EMBED_WEIGHT,
    _aggregate_rows, _combine_with_embedding, _mean_pool_normalize, _score_against_reference,
)

EXCLUDE_VIDEO_IDS = {"7c082977-87d6-474f-9c7f-4633145fae6b"}  # vtest_seg_annotated.mp4 -- không phải ảnh thật

# Cao hơn hẳn EMBED_SIM_FLOOR (0.35) một cách CÓ CHỦ ĐÍCH -- xem docstring
# module: không dùng lại đúng ngưỡng đang cần kiểm chứng để sinh dữ liệu
# kiểm chứng ngưỡng đó.
POSITIVE_COHERENCE_THRESHOLD = 0.5
MIN_CROPS_FOR_POSITIVE = 8  # cần đủ crop mỗi nửa (>=4) để mean-pool có ý nghĩa

APPEARANCE_COLS = [
    "color_top", "color_top_confidence", "color_bottom", "color_bottom_confidence",
    "sleeve_length", "sleeve_length_confidence", "has_hat", "has_hat_confidence",
    "hairstyle", "hairstyle_confidence", "has_shoes", "has_shoes_confidence",
]


# ---------------------------------------------------------------------------
# Sinh cặp
# ---------------------------------------------------------------------------

def _time_overlaps(a_range: tuple[int, int], b_range: tuple[int, int]) -> bool:
    return a_range[0] <= b_range[1] and b_range[0] <= a_range[1]


def build_negative_pairs(db_path: str, case_id: str | None = None, max_per_video: int = 150) -> list[dict]:
    """Cặp 'chắc chắn khác người' -- 2 track cùng video, thời gian giao nhau."""
    conn = sqlite3.connect(db_path)
    query = "SELECT track_id, video_id, case_id, first_frame, last_frame FROM tracks"
    params: tuple = ()
    if case_id:
        query += " WHERE case_id = ?"
        params = (case_id,)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    by_video: dict[str, list[tuple]] = defaultdict(list)
    for track_id, video_id, cid, first_frame, last_frame in rows:
        if video_id in EXCLUDE_VIDEO_IDS:
            continue
        by_video[video_id].append((track_id, cid, first_frame, last_frame))

    rng = random.Random(42)
    pairs = []
    for video_id, tracks in by_video.items():
        overlapping = []
        for i in range(len(tracks)):
            for j in range(i + 1, len(tracks)):
                t1, cid, f1, l1 = tracks[i]
                t2, _, f2, l2 = tracks[j]
                if _time_overlaps((f1, l1), (f2, l2)):
                    overlapping.append({
                        "label": "different", "source": "time_overlap",
                        "case_id": cid, "video_id": video_id,
                        "a": {"track_id": t1, "half": None},
                        "b": {"track_id": t2, "half": None},
                    })
        if len(overlapping) > max_per_video:
            overlapping = rng.sample(overlapping, max_per_video)
        pairs.extend(overlapping)
    return pairs


def _load_track_embeddings_ordered(db_path: str, track_id: str) -> list[tuple[str, np.ndarray]]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT tc.crop_path, fe.embedding FROM track_crops tc
           JOIN features_embedding fe ON fe.track_id = tc.track_id AND fe.crop_path = tc.crop_path
           WHERE tc.track_id = ? ORDER BY tc.frame_number""",
        (track_id,),
    ).fetchall()
    conn.close()
    return [(cp, np.frombuffer(blob, dtype=np.float32)) for cp, blob in rows]


def build_positive_pairs(db_path: str, case_id: str | None = None, max_pairs: int = 300) -> list[dict]:
    """Cặp 'có khả năng cùng người' -- nửa đầu vs nửa sau của 1 track đủ ổn
    định nội tại (xem POSITIVE_COHERENCE_THRESHOLD ở đầu file)."""
    conn = sqlite3.connect(db_path)
    query = "SELECT track_id, video_id, case_id FROM tracks"
    params: tuple = ()
    if case_id:
        query += " WHERE case_id = ?"
        params = (case_id,)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    pairs = []
    for track_id, video_id, cid in rows:
        if video_id in EXCLUDE_VIDEO_IDS:
            continue
        items = _load_track_embeddings_ordered(db_path, track_id)
        if len(items) < MIN_CROPS_FOR_POSITIVE:
            continue
        mid = len(items) // 2
        first_emb = _mean_pool_normalize([e for _, e in items[:mid]])
        second_emb = _mean_pool_normalize([e for _, e in items[mid:]])
        if first_emb is None or second_emb is None:
            continue
        sim = float(np.dot(first_emb, second_emb))
        if sim < POSITIVE_COHERENCE_THRESHOLD:
            continue  # nghi ngờ nhảy người giữa chừng -- không dùng làm nguồn "cùng người"
        pairs.append({
            "label": "same", "source": "track_temporal_split",
            "case_id": cid, "video_id": video_id,
            "a": {"track_id": track_id, "half": "first"},
            "b": {"track_id": track_id, "half": "second"},
        })

    if len(pairs) > max_pairs:
        pairs = random.Random(42).sample(pairs, max_pairs)
    return pairs


# ---------------------------------------------------------------------------
# Tính điểm cho 1 cặp (dùng ĐÚNG hàm production trong demo_search.py)
# ---------------------------------------------------------------------------

def _get_side_features(db_path: str, side: dict) -> tuple[dict | None, np.ndarray | None]:
    """agg thuộc tính + embedding cho 1 bên của cặp -- cả track (half=None)
    lẫn nửa track (half='first'/'second')."""
    track_id = side["track_id"]
    items = _load_track_embeddings_ordered(db_path, track_id)
    if side["half"] == "first":
        items = items[: len(items) // 2]
    elif side["half"] == "second":
        items = items[len(items) // 2 :]
    if not items:
        return None, None
    crop_paths = [cp for cp, _ in items]
    embedding = _mean_pool_normalize([e for _, e in items])

    conn = sqlite3.connect(db_path)
    placeholders = ",".join("?" * len(crop_paths))
    appearance_rows = conn.execute(
        f"SELECT {','.join(APPEARANCE_COLS)} FROM features_appearance "
        f"WHERE track_id = ? AND crop_path IN ({placeholders})",
        (track_id, *crop_paths),
    ).fetchall()
    conn.close()
    appearance_dicts = [dict(zip(APPEARANCE_COLS, r)) for r in appearance_rows]
    agg = _aggregate_rows(appearance_dicts) if appearance_dicts else None
    return agg, embedding


def score_pair(db_path: str, pair: dict) -> dict | None:
    agg_a, emb_a = _get_side_features(db_path, pair["a"])
    agg_b, emb_b = _get_side_features(db_path, pair["b"])
    if agg_a is None or agg_b is None:
        return None
    attribute_result = _score_against_reference(agg_a, agg_b)
    combined = _combine_with_embedding(attribute_result, emb_a, emb_b)
    return {"score": combined["score"], "embed_similarity": combined.get("embed_similarity")}


# ---------------------------------------------------------------------------
# Đánh giá
# ---------------------------------------------------------------------------

def evaluate(db_path: str, pairs: list[dict], min_confident_score: float) -> dict:
    same_scores, diff_scores = [], []
    for pair in pairs:
        result = score_pair(db_path, pair)
        if result is None:
            continue
        (same_scores if pair["label"] == "same" else diff_scores).append(result["score"])

    def stats(values: list[float]) -> dict:
        if not values:
            return {"n": 0}
        arr = np.array(values)
        return {"n": len(values), "min": round(float(arr.min()), 3), "max": round(float(arr.max()), 3),
                "mean": round(float(arr.mean()), 3), "std": round(float(arr.std()), 3)}

    false_positive_rate = (
        sum(1 for s in diff_scores if s >= min_confident_score) / len(diff_scores) if diff_scores else None
    )
    false_negative_rate = (
        sum(1 for s in same_scores if s < min_confident_score) / len(same_scores) if same_scores else None
    )
    return {
        "same_person": stats(same_scores),
        "different_person": stats(diff_scores),
        "min_confident_score_threshold": min_confident_score,
        "false_positive_rate": round(false_positive_rate, 3) if false_positive_rate is not None else None,
        "false_negative_rate": round(false_negative_rate, 3) if false_negative_rate is not None else None,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

DEFAULT_PAIRS_PATH = str(Path(__file__).parent.parent / "ground_truth_pairs.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Xây + đánh giá ground-truth tự động cho xếp hạng.")
    parser.add_argument("--db-path", default="case.db")
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--pairs-path", default=DEFAULT_PAIRS_PATH)
    parser.add_argument("--build", action="store_true", help="Sinh cặp mới, ghi ra file (ghi đè).")
    parser.add_argument("--evaluate", action="store_true", help="Đọc file cặp đã có, đánh giá điểm hiện tại.")
    args = parser.parse_args()

    if args.build:
        negative = build_negative_pairs(args.db_path, case_id=args.case_id)
        positive = build_positive_pairs(args.db_path, case_id=args.case_id)
        pairs = negative + positive
        with open(args.pairs_path, "w", encoding="utf-8") as f:
            json.dump(pairs, f, ensure_ascii=False, indent=2)
        print(f"Đã sinh {len(negative)} cặp 'khác người' (đáng tin cậy) + "
              f"{len(positive)} cặp 'cùng người' (suy luận yếu hơn) -> {args.pairs_path}")

    if args.evaluate:
        with open(args.pairs_path, encoding="utf-8") as f:
            pairs = json.load(f)
        from demo_search import MIN_CONFIDENT_SCORE
        report = evaluate(args.db_path, pairs, MIN_CONFIDENT_SCORE)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"\n(EMBED_SIM_FLOOR={EMBED_SIM_FLOOR} EMBED_SIM_CEIL={EMBED_SIM_CEIL} "
              f"EMBED_WEIGHT={EMBED_WEIGHT} ATTR_WEIGHT={ATTR_WEIGHT})")

    if not args.build and not args.evaluate:
        parser.print_help()


if __name__ == "__main__":
    main()
