"""
Module bổ sung — embedding ngoại hình bằng model person re-identification
(ReID) chuyên dụng, dùng làm tín hiệu so khớp CHÍNH giữa các track/ảnh tham
chiếu — thay cho việc chỉ dựa vào 6 thuộc tính rời rạc (màu áo/quần, tay áo,
mũ, tóc, giày) của modules/appearance.py, vốn khiến nhiều người khác nhau
nhận điểm giống hệt nhau (xem lịch sử: case terrace_2_goc_camera_d8cb89 từng
có 6+ track trùng điểm 0.955 tuyệt đối).

Dùng yolo26n-reid.onnx (đã có sẵn trong repo, từng được thử cho BoT-SORT+ReID
trong modules/tracker_configs/botsort_reid.yaml rồi bị loại — nhưng lý do bị
loại chỉ áp dụng cho việc GHÉP TRACK theo thời gian, không áp dụng cho việc
so sánh độ tương đồng ngoại hình tại thời điểm tìm kiếm, là việc module này
làm). Chạy 100% local (Privacy First) — không gửi dữ liệu ra ngoài, khác với
modules/vlm_compare.py.

Lưu ý quan trọng: đây là model ReID ngoại hình tổng quát (dáng người, trang
phục, tư thế), KHÔNG PHẢI nhận diện khuôn mặt. Similarity cao là tín hiệu hỗ
trợ xếp hạng mạnh, không phải bằng chứng định danh chắc chắn — đuôi phân phối
giữa "cùng người" và "khác người" có thể chồng lấn, đặc biệt với ảnh CCTV độ
phân giải thấp. Giữ đúng tinh thần Human in the Loop của PRD: điều tra viên
tự xem xét, không nhận kết luận tự động.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from pipeline_ingest import DEFAULT_DEVICE  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

REID_MODEL_PATH = str(Path(__file__).parent.parent / "yolo26n-reid.onnx")
EMBEDDING_DIM = 512  # kích thước vector đầu ra của yolo26n-reid.onnx

# Các crop liên tiếp của CÙNG 1 track gần như giống hệt nhau về ngoại hình,
# nên không cần trích embedding cho từng crop — chỉ lấy đều 1/N crop theo
# thời gian mỗi track (đo thực tế: bước embedding chiếm ~92% tổng thời gian
# ingest do chạy CPU ~20ms/crop, trong khi track trung bình có 36-39 crop).
# Giảm 5 lần số crop cần trích ở đây giảm gần tương ứng tổng thời gian ingest,
# mà điểm khớp cuối cùng không đổi nhiều vì search() vẫn mean-pool các
# embedding của cùng track thành 1 vector đại diện.
EMBED_EVERY_N_CROPS = 5

_ENCODER = None  # lazy singleton — load model ~0.36s, không load lại mỗi crop


def _get_encoder():
    global _ENCODER
    if _ENCODER is None:
        from ultralytics.trackers.utils.reid import ReID
        _ENCODER = ReID(REID_MODEL_PATH, device=DEFAULT_DEVICE)
    return _ENCODER


def extract_embedding(image_bgr: np.ndarray) -> np.ndarray | None:
    """Trích embedding ngoại hình (512 chiều, đã L2-normalize) từ 1 ảnh crop
    người. Coi toàn bộ ảnh là 1 detection (bbox = kích thước ảnh) vì crop
    trên đĩa đã được cắt sát người từ bước ingest, không cần detect lại.

    Trả về None nếu ảnh quá nhỏ để trích xuất có ý nghĩa.
    """
    h, w = image_bgr.shape[:2]
    if h < 8 or w < 8:
        return None
    dets = np.array([[w / 2, h / 2, w, h]], dtype=np.float32)
    feats = _get_encoder()(image_bgr, dets)
    feat = feats[0]
    if feat is None:
        return None
    return np.ascontiguousarray(feat, dtype=np.float32)


def extract_embedding_from_file(crop_path: str) -> np.ndarray | None:
    image = cv2.imread(crop_path)
    if image is None:
        raise FileNotFoundError(f"Không đọc được ảnh crop: {crop_path}")
    return extract_embedding(image)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-8:
        return 0.0
    return float(np.dot(a, b) / denom)


# ---------------------------------------------------------------------------
# Tích hợp DB — chạy trên toàn bộ crop của 1 case (hoặc 1 track cụ thể)
# ---------------------------------------------------------------------------

def init_embedding_table(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS features_embedding (
                track_id TEXT NOT NULL,
                crop_path TEXT NOT NULL,
                embedding BLOB NOT NULL,
                embedding_dim INTEGER NOT NULL,
                PRIMARY KEY (track_id, crop_path)
            )"""
        )
        conn.commit()
    finally:
        conn.close()


def process_case_embeddings(
    db_path: str, case_id: str, track_id: str | None = None, skip_existing: bool = True,
    embed_every_n: int = EMBED_EVERY_N_CROPS,
) -> int:
    """Chạy trích xuất embedding cho crop của case (hoặc 1 track), ghi vào
    bảng features_embedding. Trả về số crop đã xử lý.

    Cùng cấu trúc với appearance.process_case(): 1 query lấy toàn bộ crop
    cần xử lý, 1 query lấy các cặp (track_id, crop_path) đã có sẵn để lọc
    trong Python — tránh N+1 khi case đã có nhiều crop và ta chỉ thêm ít
    video mới.

    embed_every_n: chỉ trích embedding cho 1/N crop mỗi track, lấy đều theo
    thứ tự thời gian (sắp theo crop_path — tên file mã hoá số khung tăng
    dần) — xem giải thích ở EMBED_EVERY_N_CROPS. Track có ít hơn N crop vẫn
    được ít nhất 1 embedding (phần tử đầu tiên).
    """
    init_embedding_table(db_path)
    conn = sqlite3.connect(db_path)
    query = """
        SELECT c.track_id, c.crop_path
        FROM track_crops c JOIN tracks t ON t.track_id = c.track_id
        WHERE t.case_id = ?
    """
    params: list = [case_id]
    if track_id:
        query += " AND c.track_id = ?"
        params.append(track_id)
    rows = conn.execute(query, params).fetchall()

    by_track: dict[str, list[str]] = {}
    for row_track_id, crop_path in rows:
        by_track.setdefault(row_track_id, []).append(crop_path)
    selected_rows: list[tuple[str, str]] = []
    for tid, paths in by_track.items():
        paths.sort()
        selected_rows.extend((tid, p) for p in paths[::embed_every_n])

    already_done: set[tuple[str, str]] = set()
    if skip_existing and selected_rows:
        already_done = {
            (r[0], r[1]) for r in conn.execute("SELECT track_id, crop_path FROM features_embedding")
        }

    processed = 0
    for row_track_id, crop_path in selected_rows:
        if skip_existing and (row_track_id, crop_path) in already_done:
            continue

        try:
            vec = extract_embedding_from_file(crop_path)
        except FileNotFoundError:
            continue
        if vec is None:
            continue

        conn.execute(
            """INSERT OR REPLACE INTO features_embedding
               (track_id, crop_path, embedding, embedding_dim)
               VALUES (?, ?, ?, ?)""",
            (row_track_id, crop_path, vec.tobytes(), vec.shape[0]),
        )
        processed += 1
        # Commit định kỳ thay vì 1 transaction lớn cho cả case — case lớn
        # (hàng nghìn crop) trên CPU có thể chạy nhiều phút; commit từng đợt
        # giữ tiến độ đã làm nếu tiến trình bị ngắt giữa chừng, và tránh giữ
        # khoá ghi trên toàn bộ file DB quá lâu, chặn các tiến trình khác.
        if processed % 200 == 0:
            conn.commit()
            print(f"  ... đã xử lý {processed} crop", flush=True)

    conn.commit()
    conn.close()
    return processed


# ---------------------------------------------------------------------------
# CLI — cũng dùng để backfill embedding cho case đã ingest từ trước
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trích embedding ReID cho toàn bộ crop của 1 case (dùng để backfill case đã ingest trước khi có module này)"
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--track-id", default=None)
    parser.add_argument("--db-path", default="case.db")
    args = parser.parse_args()

    n = process_case_embeddings(args.db_path, args.case_id, args.track_id)
    print(f"Đã trích embedding cho {n} crop của case {args.case_id}")


if __name__ == "__main__":
    main()
