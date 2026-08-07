"""
Module 2 — Appearance (màu sắc, trang phục).

Trích xuất đặc điểm ngoại hình TĨNH từ một ảnh crop:
- color_top (màu áo) + confidence
- color_bottom (màu quần) + confidence
- sleeve_length (dài tay/ngắn tay/không rõ) + confidence
- has_hat (có mũ/không rõ) + confidence
- hairstyle (tóc dài/tóc ngắn/không rõ) + confidence
- has_shoes (có giày/không rõ) + confidence

Kỹ thuật: OpenCV thuần (không deep learning) — chia crop theo tỷ lệ chiều
cao thành các vùng cơ thể (đầu/áo/quần/chân), phân tích màu bằng histogram
HSV, ánh xạ sang tên màu cơ bản; các đặc điểm nhị phân (tay áo, mũ, giày)
dùng heuristic phát hiện da hở hoặc so màu giữa các vùng liền kề.

CHỦ ĐỊNH KHÔNG có "giới tính": suy luận giới tính từ ảnh CCTV độ phân giải
thấp không có tín hiệu hình ảnh đáng tin cậy, dễ rập khuôn hoá, và một suy
luận sai hiển thị như "đặc điểm đã trích xuất" có thể khiến điều tra viên
loại nhầm đúng người — rủi ro cao hơn nhiều so với đoán sai màu áo. Đã trao
đổi với người dùng và quyết định bỏ thuộc tính này.

Ràng buộc (xem CLAUDE.md / PRD mục 8.3): chỉ trả về đặc điểm thô + confidence
riêng cho từng đặc điểm. KHÔNG so sánh giữa các track, KHÔNG tính điểm khớp
với bất kỳ tiêu chí tìm kiếm nào — việc đó thuộc AI Reasoning team (Evidence
Fusion), không thuộc module này.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import cv2
import numpy as np

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

TOP_RATIO = 0.45  # tỷ lệ chiều cao dành cho vùng áo (phần còn lại là quần)
HEAD_RATIO = 0.16  # tỷ lệ chiều cao dành cho vùng đầu/tóc/mũ (đo riêng, không
                   # đổi TOP_RATIO để giữ nguyên logic color_top/sleeve_length
                   # đã kiểm chứng bằng mắt trước đó)
SHOULDER_BAND_RATIO = (0.16, 0.30)  # dải vai — ngay dưới đầu, dùng cho hairstyle
FEET_RATIO = 0.90  # từ tỷ lệ này tới đáy bbox coi là vùng chân/giày
MIN_VALID_PIXELS = 30  # dưới ngưỡng này coi như không đủ dữ liệu để kết luận màu

# Ngưỡng HSV (OpenCV: H 0-179, S/V 0-255) để phân biệt đen/trắng/xám trước
# khi xét tới hue — màu vô sắc (achromatic) không nên bị ép vào 1 hue cụ thể.
BLACK_V_MAX = 55
WHITE_V_MIN = 190
WHITE_S_MAX = 45
GRAY_S_MAX = 40

# Khoảng hue cho các màu có sắc (chromatic) — không phủ hết 0-179 một cách
# tuỳ tiện: khoảng nào không rơi vào các dải dưới đây được gắn nhãn "khac"
# thay vì đoán bừa (ví dụ tím/hồng không nằm trong danh sách màu yêu cầu).
HUE_RANGES = {
    "do": [(0, 9), (169, 179)],
    "vang": [(10, 34)],
    "xanh_la": [(35, 85)],
    "xanh_duong": [(86, 130)],
}

COLOR_NAMES_VI = {
    "do": "đỏ", "vang": "vàng", "xanh_la": "xanh lá", "xanh_duong": "xanh dương",
    "den": "đen", "trang": "trắng", "xam": "xám", "khac": "khác", "khong_ro": "không rõ",
}

SLEEVE_NAMES_VI = {"dai_tay": "dài tay", "ngan_tay": "ngắn tay", "khong_ro": "không rõ"}
HAT_NAMES_VI = {"co": "có mũ", "khong_ro": "không rõ"}
HAIRSTYLE_NAMES_VI = {"dai": "tóc dài", "ngan": "tóc ngắn", "khong_ro": "không rõ"}
SHOES_NAMES_VI = {"co": "có giày", "khong": "không giày", "khong_ro": "không rõ"}


def _hue_bucket(hue: int) -> str:
    for name, ranges in HUE_RANGES.items():
        for lo, hi in ranges:
            if lo <= hue <= hi:
                return name
    return "khac"


def _classify_region_color(bgr_region: np.ndarray, mask_region: np.ndarray | None) -> dict:
    """Phân loại màu chủ đạo của một vùng ảnh (áo hoặc quần).

    mask_region (nếu có): mảng uint8 cùng kích thước, 255 = pixel thuộc
    người (dùng khi có mask từ segmentation), 0 = nền — loại bỏ nền khỏi
    histogram màu để không làm lệch kết quả.
    """
    if bgr_region.size == 0:
        return {"color": "khong_ro", "confidence": 0.0}

    hsv = cv2.cvtColor(bgr_region, cv2.COLOR_BGR2HSV)
    if mask_region is not None:
        valid = mask_region > 0
    else:
        valid = np.ones(hsv.shape[:2], dtype=bool)

    if valid.sum() < MIN_VALID_PIXELS:
        return {"color": "khong_ro", "confidence": 0.0}

    h = hsv[:, :, 0][valid]
    s = hsv[:, :, 1][valid]
    v = hsv[:, :, 2][valid]
    n = h.size

    black_ratio = (v < BLACK_V_MAX).sum() / n
    white_ratio = ((v > WHITE_V_MIN) & (s < WHITE_S_MAX)).sum() / n
    gray_ratio = ((s < GRAY_S_MAX) & (v >= BLACK_V_MAX) & (v <= WHITE_V_MIN)).sum() / n

    achromatic = {"den": black_ratio, "trang": white_ratio, "xam": gray_ratio}
    best_achromatic_name = max(achromatic, key=achromatic.get)
    best_achromatic_ratio = achromatic[best_achromatic_name]

    if best_achromatic_ratio >= 0.5:
        return {"color": best_achromatic_name, "confidence": round(float(best_achromatic_ratio), 3)}

    # Màu có sắc: chỉ xét các pixel đủ sáng + đủ bão hoà để hue có ý nghĩa
    chromatic_mask = (s >= GRAY_S_MAX) & (v >= BLACK_V_MAX)
    if chromatic_mask.sum() < MIN_VALID_PIXELS:
        return {"color": "khong_ro", "confidence": 0.0}

    hue_valid = h[chromatic_mask]
    buckets: dict[str, int] = {}
    for hue in hue_valid:
        name = _hue_bucket(int(hue))
        buckets[name] = buckets.get(name, 0) + 1

    best_name = max(buckets, key=buckets.get)
    confidence = buckets[best_name] / hue_valid.size
    return {"color": best_name, "confidence": round(float(confidence), 3)}


MIN_SLEEVE_REGION_H = 36  # dưới ngưỡng này (px), heuristic không đủ tin cậy để thử
MIN_BAND_VALID_PIXELS = 12  # số pixel foreground tối thiểu trong 1 dải để tính tỷ lệ da


def _skin_ratio_masked(bgr_region: np.ndarray, mask_region: np.ndarray | None) -> float | None:
    """Tỷ lệ pixel giống màu da trong vùng (chỉ tính trên pixel foreground
    nếu có mask — tránh nền/người khác lẫn vào làm sai lệch). Trả về None
    nếu không đủ pixel foreground để kết luận."""
    if bgr_region.size == 0:
        return None
    ycrcb = cv2.cvtColor(bgr_region, cv2.COLOR_BGR2YCrCb)
    cr = ycrcb[:, :, 1]
    cb = ycrcb[:, :, 2]
    skin_mask = (cr >= 133) & (cr <= 173) & (cb >= 77) & (cb <= 127)

    if mask_region is not None:
        valid = mask_region > 0
    else:
        valid = np.ones(skin_mask.shape, dtype=bool)

    if valid.sum() < MIN_BAND_VALID_PIXELS:
        return None
    return float((skin_mask & valid).sum()) / float(valid.sum())


def _classify_sleeve_length(top_bgr: np.ndarray, top_mask: np.ndarray | None) -> dict:
    """Ước lượng dài/ngắn tay bằng heuristic da hở ở vùng cánh tay dưới.

    Logic: nếu tay áo dài, vùng gần khuỷu/cổ tay (2 bên, khoảng nửa dưới của
    vùng áo) vẫn là vải áo. Nếu tay áo ngắn, vùng đó lộ da. So sánh với dải
    tham chiếu ở khoảng giữa vùng áo (ngang ngực/vai, luôn là vải, đặt lệch
    xuống dưới đầu để không lẫn với tóc/mặt).

    Giới hạn đã biết (xác nhận bằng kiểm tra mắt trên video test): ở độ phân
    giải CCTV thấp (bbox vài chục pixel), ranh giới giữa các vùng cơ thể theo
    tỷ lệ cố định không khớp chính xác với vai/tay thật — heuristic dễ sai
    khi crop nhỏ. Đã thêm: (1) ngưỡng kích thước tối thiểu, dưới đó luôn trả
    "không rõ"; (2) dùng mask (nếu có) để loại pixel nền khỏi tính màu da,
    giảm dương tính giả do nền lẫn vào; (3) dải tham chiếu đặt thấp hơn để
    tránh vùng đầu/tóc. Ngay cả sau khi sửa, đây vẫn là heuristic màu cổ
    điển — không thay thế được model tay áo huấn luyện riêng hoặc keypoint
    tư thế (Module 3) để định vị chính xác khuỷu/cổ tay.
    """
    h, w = top_bgr.shape[:2]
    if h < MIN_SLEEVE_REGION_H or w < 12:
        return {"sleeve_length": "khong_ro", "confidence": 0.1}

    arm_band_w = max(3, int(w * 0.25))
    # Dải tham chiếu: 35%-55% chiều cao vùng áo — bỏ qua ~35% đầu (thường là
    # đầu/tóc/mặt khi bbox bắt đầu từ đỉnh đầu), lấy đúng vùng vai/ngực.
    ref_band = top_bgr[int(h * 0.35):int(h * 0.55), :]
    ref_mask = top_mask[int(h * 0.35):int(h * 0.55), :] if top_mask is not None else None
    # Dải cánh tay dưới: 65%-100% chiều cao vùng áo, 2 bên mép — nơi tay áo
    # ngắn sẽ lộ cẳng tay, tay áo dài vẫn còn vải.
    lower_left = top_bgr[int(h * 0.65):h, 0:arm_band_w]
    lower_right = top_bgr[int(h * 0.65):h, w - arm_band_w:w]
    lower_left_mask = top_mask[int(h * 0.65):h, 0:arm_band_w] if top_mask is not None else None
    lower_right_mask = top_mask[int(h * 0.65):h, w - arm_band_w:w] if top_mask is not None else None

    ref_skin = _skin_ratio_masked(ref_band, ref_mask)
    left_skin = _skin_ratio_masked(lower_left, lower_left_mask)
    right_skin = _skin_ratio_masked(lower_right, lower_right_mask)
    lower_candidates = [v for v in (left_skin, right_skin) if v is not None]

    if ref_skin is None or not lower_candidates:
        return {"sleeve_length": "khong_ro", "confidence": 0.15}

    lower_skin = max(lower_candidates)
    skin_signal = lower_skin - ref_skin

    if skin_signal > 0.25:
        confidence = round(min(0.85, 0.45 + skin_signal), 3)
        return {"sleeve_length": "ngan_tay", "confidence": confidence}
    if lower_skin < 0.06:
        confidence = round(min(0.85, 0.45 + (0.06 - lower_skin) * 3), 3)
        return {"sleeve_length": "dai_tay", "confidence": confidence}
    return {"sleeve_length": "khong_ro", "confidence": 0.25}


# Kích thước tối thiểu của chính vùng CROWN (đỉnh đầu, = 45% vùng đầu) —
# không phải vùng đầu tổng. Đã phát hiện bằng kiểm tra mắt: vùng đầu ở crop
# CCTV trung vị (~79px cao) chỉ cho crown ~5px cao, quá nhỏ, dễ ra màu nhiễu
# "tự tin" hoàn toàn sai (ví dụ báo "vàng" 0.838 từ nhiễu nén ảnh). Ngưỡng
# này khiến phần lớn crop nhỏ/trung bình trả "không rõ" — chấp nhận được,
# còn hơn báo sai.
MIN_CROWN_H = 8
MIN_CROWN_W = 10
# Mũ chỉ được kết luận "có" khi màu vùng đỉnh đầu là màu KHÔNG tự nhiên cho
# tóc/da đầu (đỏ/xanh lá/xanh dương/vàng/trắng). Đen/xám/khác luôn trả
# "không rõ" vì không thể phân biệt tóc đen với mũ đen ở độ phân giải này —
# thà bỏ sót còn hơn báo sai tự tin.
CONFIDENT_HAT_COLORS = {"do", "xanh_la", "xanh_duong", "vang", "trang"}


def _classify_hat(head_bgr: np.ndarray, head_mask: np.ndarray | None) -> dict:
    """Heuristic phát hiện mũ — CHỈ nhận diện được mũ có màu khác biệt rõ với
    tóc/da tự nhiên. Mũ đen/nâu/xám gần như không phân biệt được với tóc đen
    ở crop CCTV nhỏ — nếu vậy sẽ trả "không rõ", không đoán bừa."""
    h, w = head_bgr.shape[:2]
    crown_h = int(h * 0.45)
    if crown_h < MIN_CROWN_H or w < MIN_CROWN_W:
        return {"has_hat": "khong_ro", "confidence": 0.1}

    crown = head_bgr[0:crown_h, :]
    crown_mask = head_mask[0:crown_h, :] if head_mask is not None else None
    crown_result = _classify_region_color(crown, crown_mask)

    if crown_result["color"] in CONFIDENT_HAT_COLORS and crown_result["confidence"] > 0.6:
        return {"has_hat": "co", "confidence": round(crown_result["confidence"] * 0.85, 3)}
    return {"has_hat": "khong_ro", "confidence": 0.2}


MIN_HAIR_REGION_H = 6  # ngưỡng áp cho chính vùng tóc (65% dưới vùng đầu), không phải vùng đầu tổng


def _classify_hairstyle(head_bgr: np.ndarray, head_mask: np.ndarray | None,
                         shoulder_bgr: np.ndarray, shoulder_mask: np.ndarray | None,
                         has_hat: str) -> dict:
    """Heuristic ước lượng tóc dài/ngắn: so màu vùng gáy/tóc trong đầu với 2
    bên vai — nếu cùng tông màu, khả năng cao tóc phủ xuống vai (tóc dài).

    Nếu đã xác định có đội mũ, tóc bị che — không đánh giá được, trả về
    "không rõ" thay vì cố đoán qua lớp mũ.
    """
    if has_hat == "co":
        return {"hairstyle": "khong_ro", "confidence": 0.15}

    h, w = head_bgr.shape[:2]
    hair_split = int(h * 0.35)
    hair_h = h - hair_split
    # Kiểm tra kích thước của CHÍNH vùng tóc (65% dưới vùng đầu) — cùng lỗi
    # đã sửa ở _classify_hat: kiểm tra kích thước vùng đầu tổng là không đủ,
    # vùng con dùng để phân loại mới là thứ cần đủ lớn.
    if hair_h < MIN_HAIR_REGION_H or w < 8:
        return {"hairstyle": "khong_ro", "confidence": 0.1}

    hair_region = head_bgr[hair_split:h, :]
    hair_mask = head_mask[hair_split:h, :] if head_mask is not None else None
    hair_color = _classify_region_color(hair_region, hair_mask)
    if hair_color["color"] == "khong_ro" or hair_color["confidence"] < 0.35:
        return {"hairstyle": "khong_ro", "confidence": 0.15}

    sh, sw = shoulder_bgr.shape[:2]
    if sh < 6 or sw < 8:
        return {"hairstyle": "khong_ro", "confidence": 0.2}

    band_w = max(2, int(sw * 0.25))
    left = shoulder_bgr[:, 0:band_w]
    right = shoulder_bgr[:, sw - band_w:sw]
    left_mask = shoulder_mask[:, 0:band_w] if shoulder_mask is not None else None
    right_mask = shoulder_mask[:, sw - band_w:sw] if shoulder_mask is not None else None
    left_color = _classify_region_color(left, left_mask)
    right_color = _classify_region_color(right, right_mask)

    matches = sum(
        1 for c in (left_color, right_color)
        if c["color"] == hair_color["color"] and c["confidence"] > 0.4
    )
    if matches >= 1:
        confidence = round(min(0.7, 0.35 + 0.15 * matches), 3)
        return {"hairstyle": "dai", "confidence": confidence}
    return {"hairstyle": "ngan", "confidence": 0.3}


MIN_SHOES_REGION_H = 6
MIN_SHOES_VALID_PIXELS = 8


def _classify_shoes(feet_bgr: np.ndarray, feet_mask: np.ndarray | None) -> dict:
    """Heuristic phát hiện giày qua tỷ lệ da hở ở vùng đáy bbox (bàn chân).

    Giới hạn nghiêm trọng đã biết: vùng chân chỉ còn vài pixel ở crop CCTV
    điển hình (bbox cao ~80px thì vùng này chỉ ~6-8px) — kỳ vọng phần lớn
    kết quả sẽ là "không rõ". Ngoài ra đi chân đất gần như không xuất hiện
    trong bối cảnh giám sát thực tế nên thuộc tính này có giá trị phân biệt
    thấp — vẫn triển khai theo yêu cầu nhưng không nên dùng để loại ứng viên.
    """
    h, w = feet_bgr.shape[:2]
    if h < MIN_SHOES_REGION_H or w < 6:
        return {"has_shoes": "khong_ro", "confidence": 0.1}

    skin_ratio = _skin_ratio_masked(feet_bgr, feet_mask)
    if skin_ratio is None:
        return {"has_shoes": "khong_ro", "confidence": 0.1}

    if skin_ratio < 0.3:
        confidence = round(min(0.65, 0.35 + (0.3 - skin_ratio)), 3)
        return {"has_shoes": "co", "confidence": confidence}
    if skin_ratio > 0.6:
        confidence = round(min(0.6, 0.25 + (skin_ratio - 0.6)), 3)
        return {"has_shoes": "khong", "confidence": confidence}
    return {"has_shoes": "khong_ro", "confidence": 0.2}


def extract_appearance(image: np.ndarray, mask: np.ndarray | None = None) -> dict:
    """Trích đặc điểm ngoại hình tĩnh từ một crop người.

    Args:
        image: ảnh crop BGR (từ cv2.imread hoặc frame[y1:y2, x1:x2]).
        mask: mặt nạ nhị phân uint8 cùng kích thước image (255=người,
            0=nền), tuỳ chọn. Khi có, loại nền ra khỏi tính màu — quan
            trọng khi bbox chứa cả nền hoặc một phần người khác đứng cạnh.

    Returns:
        dict với color_top, color_bottom, sleeve_length, has_hat, hairstyle,
        has_shoes — mỗi thuộc tính kèm "<tên>_confidence" riêng.
    """
    h, w = image.shape[:2]
    split_y = int(h * TOP_RATIO)
    top_region = image[0:split_y, :]
    bottom_region = image[split_y:h, :]
    top_mask = mask[0:split_y, :] if mask is not None else None
    bottom_mask = mask[split_y:h, :] if mask is not None else None

    # color_top dùng vùng RIÊNG, bỏ qua HEAD_RATIO đầu tiên — top_region đầy
    # đủ (0..TOP_RATIO) vẫn giữ nguyên để sleeve_length dùng (không đổi, xem
    # comment ở HEAD_RATIO phía trên). Lý do cần vùng riêng: tóc dài phủ qua
    # vai vẫn nằm trong 0..45% chiều cao bbox, khiến color_top đọc nhầm màu
    # tóc thành màu áo (đã quan sát thực tế: tóc vàng nâu bị đọc thành "đỏ").
    # Bỏ đoạn đầu (thường là tóc/đầu) giảm rủi ro này — không giải quyết dứt
    # điểm nếu tóc dài phủ quá vai xuống lưng, cần pose/keypoint (Module 3,
    # ngoài phạm vi) để định vị chính xác vai mới xử lý triệt để.
    head_split = int(h * HEAD_RATIO)
    color_top_region = image[head_split:split_y, :] if head_split < split_y else top_region
    color_top_mask = (mask[head_split:split_y, :] if mask is not None else None) if head_split < split_y else top_mask

    top_result = _classify_region_color(color_top_region, color_top_mask)
    bottom_result = _classify_region_color(bottom_region, bottom_mask)
    sleeve_result = _classify_sleeve_length(top_region, top_mask)

    head_region = image[0:head_split, :]
    head_mask = mask[0:head_split, :] if mask is not None else None
    hat_result = _classify_hat(head_region, head_mask)

    sh_lo, sh_hi = int(h * SHOULDER_BAND_RATIO[0]), int(h * SHOULDER_BAND_RATIO[1])
    shoulder_region = image[sh_lo:sh_hi, :]
    shoulder_mask = mask[sh_lo:sh_hi, :] if mask is not None else None
    hairstyle_result = _classify_hairstyle(
        head_region, head_mask, shoulder_region, shoulder_mask, hat_result["has_hat"]
    )

    feet_split = int(h * FEET_RATIO)
    feet_region = image[feet_split:h, :]
    feet_mask = mask[feet_split:h, :] if mask is not None else None
    shoes_result = _classify_shoes(feet_region, feet_mask)

    return {
        "color_top": top_result["color"],
        "color_top_confidence": top_result["confidence"],
        "color_bottom": bottom_result["color"],
        "color_bottom_confidence": bottom_result["confidence"],
        "sleeve_length": sleeve_result["sleeve_length"],
        "sleeve_length_confidence": sleeve_result["confidence"],
        "has_hat": hat_result["has_hat"],
        "has_hat_confidence": hat_result["confidence"],
        "hairstyle": hairstyle_result["hairstyle"],
        "hairstyle_confidence": hairstyle_result["confidence"],
        "has_shoes": shoes_result["has_shoes"],
        "has_shoes_confidence": shoes_result["confidence"],
    }


def polygon_to_local_mask(polygon_points: list, bbox_x: int, bbox_y: int, crop_w: int, crop_h: int) -> np.ndarray:
    """Chuyển polygon mask (toạ độ ảnh gốc, từ pipeline_ingest) sang mặt nạ
    nhị phân trong hệ toạ độ cục bộ của crop (đã bù trừ bbox_x, bbox_y)."""
    mask = np.zeros((crop_h, crop_w), dtype=np.uint8)
    pts = np.array(polygon_points, dtype=np.int32) - np.array([bbox_x, bbox_y])
    cv2.fillPoly(mask, [pts], 255)
    return mask


def extract_appearance_from_file(crop_path: str, mask_polygon: list | None = None,
                                  bbox_x: int = 0, bbox_y: int = 0) -> dict:
    image = cv2.imread(crop_path)
    if image is None:
        raise FileNotFoundError(f"Không đọc được ảnh crop: {crop_path}")
    mask = None
    if mask_polygon:
        h, w = image.shape[:2]
        mask = polygon_to_local_mask(mask_polygon, bbox_x, bbox_y, w, h)
    return extract_appearance(image, mask)


# ---------------------------------------------------------------------------
# Tích hợp DB — chạy trên toàn bộ crop của 1 case (hoặc 1 track cụ thể)
# ---------------------------------------------------------------------------

APPEARANCE_EXTRA_COLUMNS = [
    ("has_hat", "TEXT"), ("has_hat_confidence", "REAL"),
    ("hairstyle", "TEXT"), ("hairstyle_confidence", "REAL"),
    ("has_shoes", "TEXT"), ("has_shoes_confidence", "REAL"),
]


def init_appearance_table(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS features_appearance (
                track_id TEXT NOT NULL,
                crop_path TEXT NOT NULL,
                color_top TEXT,
                color_top_confidence REAL,
                color_bottom TEXT,
                color_bottom_confidence REAL,
                sleeve_length TEXT,
                sleeve_length_confidence REAL,
                PRIMARY KEY (track_id, crop_path)
            )"""
        )
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(features_appearance)")}
        for col_name, col_type in APPEARANCE_EXTRA_COLUMNS:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE features_appearance ADD COLUMN {col_name} {col_type}")
        conn.commit()
    finally:
        conn.close()


def process_case(db_path: str, case_id: str, track_id: str | None = None, skip_existing: bool = True) -> int:
    """Chạy trích xuất appearance cho mọi crop của case (hoặc 1 track), ghi
    vào bảng features_appearance. Trả về số crop đã xử lý.

    Tối ưu: kiểm tra crop đã xử lý bằng 1 query duy nhất lấy toàn bộ cặp
    (track_id, crop_path) đã có sẵn rồi lọc trong Python — thay vì 1 SELECT
    tồn tại riêng cho từng crop (N+1 query, chậm rõ rệt khi case đã có nhiều
    crop và ta chỉ thêm 1 video mới, như khi thêm video vào case đang có)."""
    init_appearance_table(db_path)
    conn = sqlite3.connect(db_path)
    query = """
        SELECT c.track_id, c.crop_path, c.mask_polygon, c.bbox_x, c.bbox_y
        FROM track_crops c JOIN tracks t ON t.track_id = c.track_id
        WHERE t.case_id = ?
    """
    params: list = [case_id]
    if track_id:
        query += " AND c.track_id = ?"
        params.append(track_id)
    rows = conn.execute(query, params).fetchall()

    already_done: set[tuple[str, str]] = set()
    if skip_existing and rows:
        already_done = {
            (r[0], r[1]) for r in conn.execute("SELECT track_id, crop_path FROM features_appearance")
        }

    processed = 0
    for row_track_id, crop_path, mask_polygon_json, bbox_x, bbox_y in rows:
        if skip_existing and (row_track_id, crop_path) in already_done:
            continue

        mask_polygon = json.loads(mask_polygon_json) if mask_polygon_json else None
        try:
            result = extract_appearance_from_file(crop_path, mask_polygon, bbox_x, bbox_y)
        except FileNotFoundError:
            continue

        conn.execute(
            """INSERT OR REPLACE INTO features_appearance
               (track_id, crop_path, color_top, color_top_confidence,
                color_bottom, color_bottom_confidence, sleeve_length, sleeve_length_confidence,
                has_hat, has_hat_confidence, hairstyle, hairstyle_confidence,
                has_shoes, has_shoes_confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row_track_id, crop_path,
                result["color_top"], result["color_top_confidence"],
                result["color_bottom"], result["color_bottom_confidence"],
                result["sleeve_length"], result["sleeve_length_confidence"],
                result["has_hat"], result["has_hat_confidence"],
                result["hairstyle"], result["hairstyle_confidence"],
                result["has_shoes"], result["has_shoes_confidence"],
            ),
        )
        processed += 1

    conn.commit()
    conn.close()
    return processed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Module 2 — trích đặc điểm ngoại hình cho toàn bộ crop của 1 case")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--track-id", default=None)
    parser.add_argument("--db-path", default="case.db")
    args = parser.parse_args()

    n = process_case(args.db_path, args.case_id, args.track_id)
    print(f"Đã xử lý {n} crop cho case {args.case_id}")


if __name__ == "__main__":
    main()
