"""
Demo tìm kiếm theo ảnh tham chiếu — PROTOTYPE, KHÔNG PHẢI Evidence Fusion
chính thức mô tả trong PRD (mục 8.4, FR-09 đến FR-12).

Vì sao tách riêng file này thay vì để trong appearance.py: theo ranh giới
trách nhiệm CV team / AI Reasoning team, modules/appearance.py (Module 2)
tuyệt đối không được so sánh giữa các track hay tính điểm khớp với tiêu chí
tìm kiếm (xem docstring của appearance.py). Việc so khớp + xếp hạng ở đây là
một bản dựng đơn giản, có chủ đích, để có ngay một demo end-to-end — KHÔNG
đại diện cho thiết kế Evidence Fusion đầy đủ (thứ cần mô hình trọng số đã
thống nhất, explainability đầy đủ theo FR-11, do AI Reasoning team sở hữu).

Hạn chế đã biết của bản demo này:
- Chỉ dùng đặc điểm ngoại hình tĩnh (màu áo/quần) — chưa có body_build,
  accessories, pose (các module đó chưa được yêu cầu build).
- Chấm điểm bằng so khớp màu đơn giản có trọng số cố định, không phải mô
  hình xác suất đã calibrate.
- "Giây xuất hiện" báo theo khoảng first_frame..last_frame của cả track,
  không phải từng lần xuất hiện rời rạc nếu track có khoảng trống.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import sys
import uuid
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

sys.path.insert(0, str(Path(__file__).parent))
from appearance import extract_appearance, process_case  # noqa: E402
from pipeline_ingest import DEFAULT_DETECTOR_MODEL, DEFAULT_DEVICE, ensure_case, ingest_video, init_db  # noqa: E402
from video_transcode import ensure_web_video  # noqa: E402
import embedding  # noqa: E402
import i18n  # noqa: E402
import vlm_compare  # noqa: E402

ATTRIBUTE_WEIGHTS = {
    "color_top": 0.28,
    "color_bottom": 0.28,
    "sleeve_length": 0.10,
    "has_hat": 0.09,
    "hairstyle": 0.15,
    "has_shoes": 0.10,
}
ALL_ATTRIBUTES = list(ATTRIBUTE_WEIGHTS.keys())
UNKNOWN_VALUES = {"khong_ro"}

# Điểm kết hợp = EMBED_WEIGHT * embed_score + ATTR_WEIGHT * attribute_score.
# embed_score là cosine similarity của embedding ReID (modules/embedding.py)
# đã hiệu chỉnh qua FLOOR/CEIL trước khi trộn — vì "không liên quan" của
# model này không nằm ở similarity=0 mà ở khoảng ~0.5 (đo thực nghiệm trên
# case terrace_2_goc_camera_d8cb89: khác người trung bình 0.524 cao nhất
# 0.804, cùng người trung bình 0.759 thấp nhất 0.469) — nếu trộn similarity
# thô, người không liên quan vẫn có sàn điểm ảo, có thể lấn át chênh lệch
# thuộc tính rõ ràng. CÁC SỐ NÀY HIỆU CHỈNH TỪ 1 CASE (~15 track) — là điểm
# khởi đầu hợp lý, cần xem lại khi có thêm dữ liệu kiểm chứng rộng hơn.
EMBED_SIM_FLOOR = 0.35
EMBED_SIM_CEIL = 0.85
EMBED_WEIGHT = 0.6
ATTR_WEIGHT = 0.4

# Ngưỡng điểm tối thiểu để coi 1 track là "ứng viên đáng tin" — dưới ngưỡng
# này, hiển thị kết quả sẽ gây hiểu nhầm (đầu tư giờ đọc/xác minh cho 1 track
# mà thực ra không giống đối tượng). Chọn 0.45 vì: 1 track hoàn toàn KHÔNG
# liên quan (embed_score=0, tức cosine <= EMBED_SIM_FLOOR) nhưng tình cờ
# khớp mọi thuộc tính màu sắc (attr_score=1.0 — dễ xảy ra do chỉ có vài màu
# cơ bản) vẫn đạt 0.4*1.0=0.4 — đặt ngưỡng ngay trên mức đó để bắt đúng
# trường hợp "trùng màu ngẫu nhiên nhưng ngoại hình khác hẳn" là lỗi đã quan
# sát được. Ứng viên thật trong dữ liệu kiểm chứng đạt 0.56-0.92. Đây là
# điểm khởi đầu, cần hiệu chỉnh thêm khi có nhiều dữ liệu thực tế hơn.
MIN_CONFIDENT_SCORE = 0.45

# Khi bật AI thị giác, gửi ÍT NHẤT ngần này ứng viên MỖI VIDEO (theo điểm cục
# bộ) cho AI so sánh, thay vì chỉ đúng bằng "Số ứng viên hiển thị" người dùng
# chọn. Lý do cần: đã quan sát thực tế — track đúng người có thể xếp hạng
# #6-10 vì so màu/ReID cục bộ chỉ là heuristic thô (đặc biệt yếu với ảnh tham
# chiếu quay từ phía sau, đã nén lại), nên bị cắt khỏi top-K nhỏ TRƯỚC KHI AI
# có cơ hội xem xét — AI vẫn so sánh đúng, chỉ là chưa từng nhìn thấy ứng
# viên đúng.
#
# TÍNH THEO TỪNG VIDEO (không phải tổng cả case) — trước đây dùng 1 con số
# chung cho toàn case (25), gây lỗi thực tế: case 4 video, 2 video đầu đã đủ
# số kết quả hiển thị (top_k toàn case) nên 2 video sau KHÔNG được xét tới dù
# có thể chứa đúng đối tượng — video ingest sau bị "đói" ngân sách một cách
# bất công. search() giờ luôn nhóm theo video trước khi cắt top-K.
VLM_POOL_PER_VIDEO = 10

# Lọc bớt track gần như chắc chắn KHÁC người TRƯỚC khi gửi cho AI thị giác —
# tiết kiệm lệnh gọi API cho các track rõ ràng không liên quan (vd người đi
# ngang qua nền, ReID similarity rất thấp). Đặt THẤP HƠN EMBED_SIM_FLOOR
# (0.35) một khoảng an toàn — không dùng thẳng floor vì đã đo được 1 ca thật
# đúng người có similarity ngay sát 0.35, lọc quá sát ngưỡng đó có rủi ro bỏ
# sót ca khó tương tự. Track chưa có embedding (case cũ chưa backfill) luôn
# được giữ lại — không có cơ sở để loại.
VLM_PRESCREEN_FLOOR = EMBED_SIM_FLOOR - 0.05


# ---------------------------------------------------------------------------
# Quản lý case — nhiều video trong 1 case (thay cho case_id tự sinh từ hash
# file trước đây, mỗi video 1 case riêng). Cho phép điều tra viên gom nhiều
# camera/nguồn video vào cùng 1 vụ án, tìm kiếm chạy trên toàn bộ.
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "case"


def create_case(db_path: str, case_name: str) -> str:
    """Tạo case mới, trả về case_id để dùng cho add_video_to_case/search."""
    init_db(db_path)
    case_id = f"{_slugify(case_name)}_{uuid.uuid4().hex[:6]}"
    ensure_case(db_path, case_id, name=case_name)
    return case_id


def list_cases(db_path: str) -> list[dict]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT c.case_id, c.name, c.created_at, COUNT(v.video_id) AS n_videos
           FROM cases c LEFT JOIN videos v ON v.case_id = c.case_id
           GROUP BY c.case_id ORDER BY c.created_at DESC"""
    ).fetchall()
    conn.close()
    return [{"case_id": r[0], "name": r[1], "created_at": r[2], "n_videos": r[3]} for r in rows]


def list_videos_in_case(db_path: str, case_id: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT video_id, source_path, camera_label, fps, total_frames, added_at
           FROM videos WHERE case_id = ? ORDER BY added_at""",
        (case_id,),
    ).fetchall()
    conn.close()
    return [
        {
            "video_id": r[0], "source_path": r[1], "camera_label": r[2],
            "fps": r[3], "total_frames": r[4], "added_at": r[5],
        }
        for r in rows
    ]


def get_web_video_path(db_path: str, case_id: str, video_id: str, output_dir: str = "output") -> str | None:
    """Đường dẫn bản mp4 phát-được-trên-trình-duyệt cho 1 video trong case,
    tự chuyển mã lần đầu và tái dùng (cache) các lần sau. Trả None nếu
    video_id không tồn tại. Video gốc không bị đụng tới."""
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT source_path FROM videos WHERE video_id = ?", (video_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    source_path = row[0]
    cache_path = str(Path(output_dir) / case_id / "web" / f"{video_id}.mp4")
    return ensure_web_video(source_path, cache_path)


def add_video_to_case(
    db_path: str, case_id: str, video_path: str,
    camera_label: str | None = None, sample_fps: float = 5.0,
) -> str:
    """Thêm 1 video vào case đã có, trả về video_id. Bỏ qua ingest lại nếu
    đường dẫn này đã từng được thêm vào CHÍNH case_id này (tránh xử lý trùng
    khi người dùng vô tình bấm thêm 2 lần) — luôn chạy lại appearance vì đó
    là thao tác rẻ (tự bỏ qua crop đã xử lý, xem process_case)."""
    conn = sqlite3.connect(db_path)
    existing = conn.execute(
        "SELECT video_id FROM videos WHERE case_id = ? AND source_path = ?",
        (case_id, str(Path(video_path))),
    ).fetchone()
    conn.close()

    if existing:
        video_id = existing[0]
    else:
        result = ingest_video(
            case_id=case_id, video_path=video_path, db_path=db_path,
            camera_label=camera_label, sample_fps=sample_fps,
        )
        video_id = result.video_id

    process_case(db_path, case_id)
    embedding.process_case_embeddings(db_path, case_id)
    return video_id


def clear_case_videos(db_path: str, case_id: str, output_dir: str = "output") -> int:
    """Xoá TOÀN BỘ video + dữ liệu dẫn xuất (track, crop, đặc điểm ngoại
    hình, embedding ReID) của 1 case — giữ lại bản ghi case (tên, ngày tạo)
    để có thể thêm video mới vào lại. Không thể hoàn tác.

    Lý do cần: case demo tích luỹ qua nhiều lần test trước đó khiến việc
    chọn nhầm case cũ (đã có sẵn video) rồi tìm kiếm cho ra kết quả không
    phải do video vừa thêm — dễ gây hiểu nhầm khi kiểm thử. Trả về số video
    đã xoá."""
    conn = sqlite3.connect(db_path)
    video_ids = [r[0] for r in conn.execute("SELECT video_id FROM videos WHERE case_id = ?", (case_id,)).fetchall()]
    n_videos = len(video_ids)
    if video_ids:
        track_ids = [
            r[0] for r in conn.execute("SELECT track_id FROM tracks WHERE case_id = ?", (case_id,)).fetchall()
        ]
        if track_ids:
            placeholders = ",".join("?" * len(track_ids))
            conn.execute(f"DELETE FROM features_embedding WHERE track_id IN ({placeholders})", track_ids)
            conn.execute(f"DELETE FROM features_appearance WHERE track_id IN ({placeholders})", track_ids)
            conn.execute(f"DELETE FROM track_crops WHERE track_id IN ({placeholders})", track_ids)
        conn.execute("DELETE FROM tracks WHERE case_id = ?", (case_id,))
        conn.execute("DELETE FROM videos WHERE case_id = ?", (case_id,))
        conn.commit()
    conn.close()

    case_output_dir = Path(output_dir) / case_id
    if case_output_dir.is_dir():
        shutil.rmtree(case_output_dir, ignore_errors=True)

    return n_videos


def get_reference_appearance(
    image_path: str, conf_threshold: float = 0.3, use_vlm: bool = False, lang: str = i18n.DEFAULT_LANGUAGE,
) -> dict | None:
    """Phát hiện người trong ảnh tham chiếu (chọn detection tin cậy nhất nếu
    có nhiều người), trích đặc điểm ngoại hình giống hệt cách làm với crop
    trong video — đảm bảo so sánh cùng loại dữ liệu.

    use_vlm=True: dùng ChatGPT Vision mô tả đặc điểm thay vì heuristic màu
    HSV cổ điển (xem vlm_compare.describe_reference_attributes — lý do cần:
    heuristic màu đã quan sát thấy đọc sai trên ảnh thật, ánh sáng ám màu
    hoặc tóc dài che vai). Rơi về heuristic cũ nếu gọi API lỗi (best-effort,
    không chặn tìm kiếm chỉ vì API tạm thời lỗi)."""
    image = cv2.imread(image_path)
    if image is None:
        return None

    model = YOLO(DEFAULT_DETECTOR_MODEL)
    results = model.predict(image, classes=[0], conf=conf_threshold, device=DEFAULT_DEVICE, verbose=False)
    result = results[0]

    if result.boxes is None or len(result.boxes) == 0:
        # Không phát hiện được người — dùng cả ảnh, coi như đã là crop sẵn
        crop = image
        mask = None
    else:
        confs = result.boxes.conf.cpu().numpy()
        best_i = int(np.argmax(confs))
        x1, y1, x2, y2 = result.boxes.xyxy.cpu().numpy()[best_i]
        x1i, y1i, x2i, y2i = max(0, int(x1)), max(0, int(y1)), int(x2), int(y2)
        crop = image[y1i:y2i, x1i:x2i]
        mask = None
        if result.masks is not None:
            poly = result.masks.xy[best_i]
            if len(poly) >= 3:
                local_poly = np.array(poly, dtype=np.int32) - np.array([x1i, y1i])
                mask = np.zeros(crop.shape[:2], dtype=np.uint8)
                cv2.fillPoly(mask, [local_poly], 255)

    if crop.size == 0:
        return None

    vlm_note = None
    if use_vlm and vlm_compare.is_configured():
        try:
            vlm_result = vlm_compare.describe_reference_attributes(crop)
            features = {attr: vlm_result[attr] for attr in ALL_ATTRIBUTES}
            vlm_note = vlm_result.get("reasoning")
            features["_extended"] = {
                attr: vlm_result.get(attr, "khong_ro") for attr in vlm_compare.EXTENDED_REFERENCE_ATTRS
            }
            if vlm_result.get("build_note"):
                features["_build_note"] = vlm_result["build_note"]
            if vlm_result.get("gait_note"):
                features["_gait_note"] = vlm_result["gait_note"]
        except Exception as e:
            features = extract_appearance(crop, mask)
            vlm_note = i18n.t("ref_vlm_describe_error_template", lang).format(error=e)
    else:
        features = extract_appearance(crop, mask)

    features["_crop"] = crop
    features["_embedding"] = embedding.extract_embedding(crop)
    if vlm_note:
        features["_vlm_note"] = vlm_note
    return features


def _aggregate_rows(rows: list[dict], attrs: list[str] = ALL_ATTRIBUTES) -> dict:
    """Gộp nhiều dòng appearance (1 dòng / crop, hoặc 1 dòng / ảnh tham
    chiếu) thành 1 bộ đặc điểm đại diện — bỏ phiếu đa số cho từng thuộc
    tính, bỏ qua giá trị "không rõ" khi còn giá trị khác để bỏ phiếu (không
    để "không rõ" làm loãng kết quả nếu phần lớn nguồn đã xác định được).
    attrs mặc định là 6 thuộc tính cổ điển; truyền EXTENDED_REFERENCE_ATTRS
    để gộp các thuộc tính mở rộng (túi/balo, loại trang phục...) qua nhiều
    ảnh tham chiếu theo cùng logic."""
    agg = {}
    for attr in attrs:
        values = [r[attr] for r in rows if r.get(attr) not in (None,) and r[attr] != "khong_ro"]
        if not values:
            agg[attr] = "khong_ro"
            agg[f"{attr}_confidence"] = 0.0
            continue
        counts = Counter(values)
        best_value, best_count = counts.most_common(1)[0]
        agg[attr] = best_value
        agg[f"{attr}_confidence"] = round(best_count / len(values), 3)
    return agg


def _mean_pool_normalize(vectors: list[np.ndarray]) -> np.ndarray | None:
    """Mean-pool nhiều embedding rồi renormalize về vector đơn vị — dùng cả
    khi gộp nhiều ảnh tham chiếu và khi gộp nhiều crop của cùng 1 track."""
    if not vectors:
        return None
    mean_vec = np.mean(vectors, axis=0)
    norm = np.linalg.norm(mean_vec)
    if norm < 1e-8:
        return None
    return (mean_vec / norm).astype(np.float32)


def _aggregate_embeddings(rows: list[dict]) -> np.ndarray | None:
    """Gộp embedding từ nhiều ảnh tham chiếu bằng mean-pool rồi renormalize —
    hợp lý hơn bỏ phiếu đa số (dùng cho thuộc tính rời rạc) vì embedding là
    vector liên tục; trung bình nhiều góc/khoảnh khắc của cùng 1 người vẫn
    là 1 điểm hợp lệ trong không gian embedding."""
    vectors = [r["_embedding"] for r in rows if r.get("_embedding") is not None]
    return _mean_pool_normalize(vectors)


def get_reference_appearance_multi(
    image_paths: list[str], conf_threshold: float = 0.3, use_vlm: bool = False, lang: str = i18n.DEFAULT_LANGUAGE,
) -> dict | None:
    """Trích đặc điểm tham chiếu từ NHIỀU ảnh (nhiều góc/khoảnh khắc của cùng
    một người) rồi gộp bằng bỏ phiếu đa số — mô tả đối tượng đầy đủ hơn 1 ảnh
    đơn lẻ (ví dụ 1 ảnh chỉ thấy áo, ảnh khác mới thấy rõ mũ)."""
    per_image_features = []
    sample_crop = None
    vlm_notes = []
    build_notes = []
    gait_notes = []
    for path in image_paths:
        features = get_reference_appearance(path, conf_threshold, use_vlm=use_vlm, lang=lang)
        if features is None:
            continue
        if sample_crop is None:
            sample_crop = features.get("_crop")
        if features.get("_vlm_note"):
            vlm_notes.append(features["_vlm_note"])
        if features.get("_build_note"):
            build_notes.append(features["_build_note"])
        if features.get("_gait_note"):
            gait_notes.append(features["_gait_note"])
        per_image_features.append(features)

    if not per_image_features:
        return None

    agg = _aggregate_rows(per_image_features)
    agg["_crop"] = sample_crop
    agg["_embedding"] = _aggregate_embeddings(per_image_features)
    agg["_n_images_used"] = len(per_image_features)
    agg["_n_images_total"] = len(image_paths)
    if vlm_notes:
        agg["_vlm_notes"] = vlm_notes
    extended_rows = [f["_extended"] for f in per_image_features if f.get("_extended")]
    if extended_rows:
        agg["_extended"] = _aggregate_rows(extended_rows, vlm_compare.EXTENDED_REFERENCE_ATTRS)
    if build_notes:
        agg["_build_note"] = build_notes[0]
    if gait_notes:
        agg["_gait_note"] = gait_notes[0]
    return agg


def _score_against_reference(ref: dict, track_agg: dict, lang: str = i18n.DEFAULT_LANGUAGE) -> dict:
    total_weight_used = 0.0
    weighted_sum = 0.0
    confidence_weighted_sum = 0.0
    explanation = []

    for attr, weight in ATTRIBUTE_WEIGHTS.items():
        attr_label = i18n.t(i18n.ATTR_LABEL_KEYS[attr], lang)
        ref_val = ref.get(attr)
        track_val = track_agg.get(attr)
        if ref_val in UNKNOWN_VALUES or track_val in UNKNOWN_VALUES:
            explanation.append(i18n.t("expl_skip_template", lang).format(attr=attr_label))
            continue
        match = 1.0 if ref_val == track_val else 0.0
        contrib = weight * match
        weighted_sum += contrib
        total_weight_used += weight
        if match:
            ref_conf = ref.get(f"{attr}_confidence", 0.5) or 0.5
            track_conf = track_agg.get(f"{attr}_confidence", 0.5) or 0.5
            confidence_weighted_sum += weight * ref_conf * track_conf
        value_table = i18n.ATTR_VALUE_TABLES[attr]
        result_label = i18n.t("match_khop", lang) if match else i18n.t("match_khac", lang)
        explanation.append(i18n.t("expl_compare_template", lang).format(
            attr=attr_label, ref=i18n.value(value_table, ref_val, lang), track=i18n.value(value_table, track_val, lang),
            result=result_label, weight=weight,
        ))

    if total_weight_used == 0:
        return {"score": 0.0, "explanation": explanation + [i18n.t("expl_no_common_attrs", lang)]}

    score = weighted_sum / total_weight_used
    # Phạt nhẹ nếu chỉ so được ít thuộc tính (độ tin cậy tổng thể thấp hơn)
    coverage = total_weight_used / sum(ATTRIBUTE_WEIGHTS.values())
    score_adjusted = score * (0.7 + 0.3 * coverage)

    # Tie-break: so khớp nhị phân từng thuộc tính khiến RẤT NHIỀU track khác
    # nhau nhận điểm chính giống hệt nhau (vd nhiều người cùng mặc áo đen,
    # quần đen). Nếu không có tie-break, search() sắp theo điểm rồi cắt
    # top_k sẽ để thứ tự ngẫu nhiên từ SQL (thực chất là thứ tự ingest video)
    # quyết định ai lọt top-K — có thể loại bỏ âm thầm ứng viên đúng ở
    # camera ingest sau, dù điểm giống hệt ứng viên hiển thị. Cộng thêm một
    # lượng rất nhỏ dựa trên độ tin cậy trích xuất đặc điểm (tín hiệu thật,
    # không phải ngẫu nhiên) để phá vỡ tie theo cách công bằng giữa các
    # camera, đồng thời không đủ lớn để đảo thứ hạng giữa các điểm thực sự
    # khác nhau (chênh lệch nhỏ nhất giữa các mức điểm chính là ~0.09/tổng
    # trọng số, tie-break tối đa 0.01 << mức đó).
    confidence_tiebreak = (confidence_weighted_sum / total_weight_used) if total_weight_used else 0.0
    score_final = score_adjusted + confidence_tiebreak * 0.01

    return {"score": round(score_final, 4), "explanation": explanation}


def _combine_with_embedding(
    attribute_result: dict, ref_embedding: np.ndarray | None, track_embedding: np.ndarray | None,
    lang: str = i18n.DEFAULT_LANGUAGE,
) -> dict:
    """Kết hợp điểm thuộc tính (attribute_result["score"]) với điểm tương
    đồng ReID thành điểm cuối. Nếu thiếu embedding ở 1 trong 2 bên (case cũ
    chưa backfill, ảnh tham chiếu/crop quá nhỏ để trích embedding...), rơi
    về dùng riêng điểm thuộc tính — không crash, không âm thầm cho điểm 0."""
    explanation = list(attribute_result["explanation"])
    attr_score = attribute_result["score"]

    if ref_embedding is None or track_embedding is None:
        explanation.append(i18n.t("expl_reid_no_data", lang))
        return {"score": attr_score, "explanation": explanation, "embed_similarity": None}

    cosine_sim = embedding.cosine_similarity(ref_embedding, track_embedding)
    embed_score = max(0.0, min(1.0, (cosine_sim - EMBED_SIM_FLOOR) / (EMBED_SIM_CEIL - EMBED_SIM_FLOOR)))
    final_score = EMBED_WEIGHT * embed_score + ATTR_WEIGHT * attr_score
    explanation.append(i18n.t("expl_reid_template", lang).format(
        sim=cosine_sim, score=embed_score, embed_w=EMBED_WEIGHT, attr=attr_score, attr_w=ATTR_WEIGHT,
    ))
    return {"score": round(final_score, 4), "explanation": explanation, "embed_similarity": cosine_sim}


def search(
    case_id: str,
    db_path: str,
    reference_features: dict,
    top_k: int = 5,
    lang: str = i18n.DEFAULT_LANGUAGE,
) -> list[dict]:
    """So khớp reference_features với mọi track trong TOÀN BỘ video của case
    (không phải 1 video đơn lẻ) — mỗi ứng viên trả kèm video_id/video_label
    để biết xuất hiện ở camera/video nào.

    Tối ưu: 3 query tổng cộng bất kể case có bao nhiêu track (JOIN + IN),
    thay vì 2 query lặp lại cho từng track (N+1) như bản trước — quan trọng
    khi case có nhiều video, tổng số track có thể lên tới hàng trăm.
    """
    conn = sqlite3.connect(db_path)

    track_rows = conn.execute(
        """SELECT t.track_id, t.first_frame, t.last_frame, t.video_id,
                  v.fps, v.camera_label, v.source_path
           FROM tracks t JOIN videos v ON v.video_id = t.video_id
           WHERE t.case_id = ?""",
        (case_id,),
    ).fetchall()
    if not track_rows:
        conn.close()
        return []

    track_ids = [r[0] for r in track_rows]
    placeholders = ",".join("?" * len(track_ids))

    feature_rows_all = conn.execute(
        f"""SELECT track_id, color_top, color_top_confidence, color_bottom, color_bottom_confidence,
                   sleeve_length, sleeve_length_confidence,
                   has_hat, has_hat_confidence, hairstyle, hairstyle_confidence,
                   has_shoes, has_shoes_confidence
            FROM features_appearance WHERE track_id IN ({placeholders})""",
        track_ids,
    ).fetchall()
    features_by_track: dict[str, list[dict]] = defaultdict(list)
    for r in feature_rows_all:
        features_by_track[r[0]].append({
            "color_top": r[1], "color_top_confidence": r[2],
            "color_bottom": r[3], "color_bottom_confidence": r[4],
            "sleeve_length": r[5], "sleeve_length_confidence": r[6],
            "has_hat": r[7], "has_hat_confidence": r[8],
            "hairstyle": r[9], "hairstyle_confidence": r[10],
            "has_shoes": r[11], "has_shoes_confidence": r[12],
        })

    crop_rows_all = conn.execute(
        f"""SELECT track_id, crop_path, bbox_w, bbox_h
            FROM track_crops WHERE track_id IN ({placeholders})""",
        track_ids,
    ).fetchall()

    embedding_rows_all = conn.execute(
        f"""SELECT track_id, embedding FROM features_embedding WHERE track_id IN ({placeholders})""",
        track_ids,
    ).fetchall()
    conn.close()

    best_crop_by_track: dict[str, str] = {}
    best_area_by_track: dict[str, int] = {}
    for tid, crop_path, w, h in crop_rows_all:
        area = (w or 0) * (h or 0)
        if area > best_area_by_track.get(tid, -1):
            best_area_by_track[tid] = area
            best_crop_by_track[tid] = crop_path

    embeddings_by_track: dict[str, list[np.ndarray]] = defaultdict(list)
    for tid, blob in embedding_rows_all:
        embeddings_by_track[tid].append(np.frombuffer(blob, dtype=np.float32))

    ref_embedding = reference_features.get("_embedding")

    candidates = []
    for track_id, first_frame, last_frame, video_id, fps, camera_label, source_path in track_rows:
        feature_rows = features_by_track.get(track_id)
        if not feature_rows:
            continue
        track_agg = _aggregate_rows(feature_rows)
        attribute_result = _score_against_reference(reference_features, track_agg, lang=lang)
        track_embedding = _mean_pool_normalize(embeddings_by_track.get(track_id, []))
        scored = _combine_with_embedding(attribute_result, ref_embedding, track_embedding, lang=lang)
        video_fps = fps or 25.0

        candidates.append({
            "track_id": track_id,
            "video_id": video_id,
            "video_label": camera_label or Path(source_path).name,
            "score": scored["score"],
            "explanation": scored["explanation"],
            "embed_similarity": scored.get("embed_similarity"),
            "track_appearance": track_agg,
            "first_seen_sec": round(first_frame / video_fps, 1),
            "last_seen_sec": round(last_frame / video_fps, 1),
            "sample_crop_path": best_crop_by_track.get(track_id),
        })

    return group_top_k_per_video(candidates, top_k)


def _time_overlaps(a: dict, b: dict) -> bool:
    """2 track cùng video có khoảng thời gian [first_seen_sec, last_seen_sec]
    giao nhau nghĩa là cùng xuất hiện trong ít nhất 1 khung hình chung — vô lý
    nếu cả 2 đều được báo là ứng viên cho CÙNG 1 người tham chiếu (1 người
    không thể là 2 track khác nhau tại cùng thời điểm)."""
    return a["first_seen_sec"] <= b["last_seen_sec"] and b["first_seen_sec"] <= a["last_seen_sec"]


def group_top_k_per_video(candidates: list[dict], top_k: int) -> list[dict]:
    """Cắt top-K THEO TỪNG VIDEO (video_id) thay vì toàn case — cắt theo
    tổng case khiến video ingest sau bị "đói" nếu video trước đã chiếm hết
    số lượng hiển thị, dù video sau có thể chứa đúng đối tượng với điểm cao
    hơn (lỗi thực tế đã quan sát: case 4 video, 2 video đầu đủ 5 kết quả nên
    2 video sau không được báo). Dùng lại được cả trước VLM (trong search())
    lẫn sau VLM (điểm đổi, cần cắt lại theo điểm mới — xem run_search() ở
    app.py).

    Đồng thời loại bỏ trùng lặp theo thời gian: nếu 2 track trong CÙNG 1 video
    có khoảng thời gian xuất hiện giao nhau (cùng lúc trong khung hình), chỉ
    giữ lại track có điểm khớp cao hơn — tránh báo mâu thuẫn 2 "đối tượng phù
    hợp" khác nhau tại cùng 1 thời điểm trên cùng 1 camera."""
    by_video: dict[str, list[dict]] = defaultdict(list)
    for c in candidates:
        by_video[c["video_id"]].append(c)
    result = []
    for items in by_video.values():
        items.sort(key=lambda c: c["score"], reverse=True)
        kept: list[dict] = []
        for c in items:
            if any(_time_overlaps(c, k) for k in kept):
                continue
            kept.append(c)
            if len(kept) >= top_k:
                break
        result.extend(kept)
    result.sort(key=lambda c: c["score"], reverse=True)
    return result


def filter_prescreen_for_vlm(candidates: list[dict]) -> list[dict]:
    """Lọc bớt track gần như chắc chắn KHÁC người trước khi gửi cho AI thị
    giác — xem VLM_PRESCREEN_FLOOR. Giữ nguyên track chưa có embedding (case
    cũ chưa backfill) vì không có cơ sở để loại."""
    return [
        c for c in candidates
        if c.get("embed_similarity") is None or c["embed_similarity"] >= VLM_PRESCREEN_FLOOR
    ]


# ---------------------------------------------------------------------------
# Tinh chỉnh bằng AI thị giác (VLM) — HOÀN TOÀN OPT-IN
#
# ⚠️ Gửi ảnh crop ra ngoài mạng nội bộ lên API của OpenAI. Chỉ chạy khi
# người dùng chủ động bật trong UI. Xem cảnh báo đầy đủ trong
# modules/vlm_compare.py. Đây là bước RE-RANK sau khi đã có kết quả từ
# search() — không thay thế so khớp màu local, chỉ tinh chỉnh top ứng viên
# (gọi API cho toàn bộ track sẽ quá chậm/tốn kém).
# ---------------------------------------------------------------------------

VLM_MAX_WORKERS = 10  # gọi API OpenAI song song — độ trễ mỗi lệnh (2-5s) chủ
# yếu do mạng/model chứ không phải CPU nên tăng luồng gần như tuyến tính lợi
# ích tới điểm này. Tăng từ 5 lên 10 sau khi người dùng phản hồi 25 ảnh mất
# ~68s cảm giác chậm — giảm gần một nửa thời gian chờ, không đổi số lệnh gọi
# hay độ chính xác. Nếu gặp lỗi rate-limit (tài khoản phổ thông), hạ lại.


def _refine_one_candidate(args: tuple[dict, np.ndarray, str, str]) -> dict:
    c, reference_crop, vlm_model, reference_context = args
    c = dict(c)
    if not c.get("sample_crop_path"):
        c["vlm_verdict"] = None
        return c

    verdict = vlm_compare.compare_reference_crop_to_file(
        reference_crop, c["sample_crop_path"], model=vlm_model, reference_context=reference_context
    )
    vlm_score = vlm_compare.vlm_verdict_to_score(verdict)
    c["vlm_verdict"] = verdict
    c["local_score"] = c["score"]
    c["score"] = round(0.4 * c["local_score"] + 0.6 * vlm_score, 3)
    return c


def refine_with_vlm(
    reference_features: dict,
    candidates: list[dict],
    vlm_model: str = vlm_compare.DEFAULT_MODEL,
) -> list[dict]:
    """Với mỗi candidate (đã có sample_crop_path), gọi ChatGPT Vision so sánh
    với ảnh tham chiếu, gắn thêm vlm_verdict + điểm kết hợp, sắp xếp lại.

    reference_features phải có "_crop" (ảnh BGR) — trả về bởi
    get_reference_appearance_multi(). Không sửa candidates gốc — trả về bản
    sao mới đã gắn thêm dữ liệu VLM.

    Nếu reference_features có "_extended" (túi/balo, loại trang phục... —
    chỉ có khi mô tả ảnh tham chiếu bằng AI thị giác), tóm tắt thành 1 câu
    ngữ cảnh gửi kèm mỗi lệnh so sánh — giúp model neo vào đúng đặc điểm đã
    quan sát được ở ảnh tham chiếu thay vì tự suy luận lại từ đầu.

    Gọi API song song (ThreadPoolExecutor) thay vì tuần tự — đây là các lệnh
    gọi mạng độc lập, chờ tuần tự từng cái là lãng phí thời gian không cần
    thiết. Dùng .map() (không phải submit() thủ công) để đảm bảo thứ tự kết
    quả khớp thứ tự candidates đầu vào dù chạy song song.
    """
    reference_crop = reference_features.get("_crop")
    if reference_crop is None:
        raise RuntimeError("Ảnh tham chiếu không có sẵn để so sánh bằng AI thị giác.")

    extended = reference_features.get("_extended")
    reference_context = vlm_compare.describe_extended_attrs_vi(extended) if extended else ""

    with ThreadPoolExecutor(max_workers=VLM_MAX_WORKERS) as executor:
        refined = list(executor.map(
            _refine_one_candidate,
            [(c, reference_crop, vlm_model, reference_context) for c in candidates],
        ))

    refined.sort(key=lambda c: c["score"], reverse=True)
    return refined
