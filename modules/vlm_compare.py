"""
So sánh 2 ảnh người (ảnh tham chiếu vs ứng viên từ video) bằng ChatGPT
(OpenAI GPT vision) API — tinh chỉnh xếp hạng sau bước so màu cục bộ đơn
giản (modules/demo_search.py).

⚠️ VI PHẠM Privacy First CÓ CHỦ ĐÍCH, theo yêu cầu rõ ràng của người dùng sau
khi đã được giải thích đánh đổi (xem lịch sử trao đổi) — ảnh crop SẼ được gửi
lên API của OpenAI. Chỉ dùng khi tính năng "AI thị giác" được người dùng
chủ động bật trong UI (opt-in), không tự động, không áp dụng toàn bộ video.

Yêu cầu cấu hình: biến môi trường OPENAI_API_KEY (đặt trong terminal của
người dùng, không qua chat — key là thông tin nhạy cảm).

Nguyên tắc thiết kế (giữ đúng tinh thần Evidence Driven / Human in the Loop
của PRD dù dùng model mạnh hơn): prompt yêu cầu model đánh giá MỨC ĐỘ PHÙ HỢP
về đặc điểm ngoại hình quan sát được — không nhận diện khuôn mặt, không kết
luận danh tính. Model được nhắc rõ ảnh có thể rất nhỏ/mờ và phải hạ độ tin
cậy thay vì đoán liều.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

import cv2
import numpy as np
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent))
from appearance import COLOR_NAMES_VI  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_MODEL = "gpt-5.6"

# "low": model trả lời thẳng không suy luận nội bộ dài dòng trước khi điền
# schema — đo thực tế: loại bỏ hoàn toàn phần "reasoning_tokens" ẩn (94-166
# token/lệnh gọi tuỳ ảnh) mà không đổi độ chính xác same_person_likely qua
# nhiều cặp ảnh test (cả khớp lẫn không khớp) — nhiệm vụ so sánh 2 ảnh + điền
# schema có cấu trúc rõ ràng không cần suy luận nhiều bước. Giữ "low" thay vì
# "none" để còn chút biên an toàn cho các cặp ảnh khó hơn chưa test tới.
REASONING_EFFORT = {"effort": "low"}

SYSTEM_PROMPT = (
    "Bạn đang hỗ trợ điều tra viên so sánh 2 ảnh cắt từ camera giám sát để "
    "đánh giá mức độ CÓ THỂ là cùng một người, dựa trên đặc điểm ngoại hình "
    "quan sát được (quần áo, hình dáng, dáng đi, tư thế, phụ kiện...). "
    "Đây KHÔNG PHẢI nhận diện khuôn mặt và KHÔNG PHẢI kết luận danh tính cuối "
    "cùng — chỉ là một tín hiệu hỗ trợ để điều tra viên tự xem xét, không "
    "phải bằng chứng quyết định. Ảnh có thể rất nhỏ, mờ, độ phân giải thấp, "
    "góc chụp khác nhau — nếu không đủ rõ để đánh giá, hãy nói rõ độ tin cậy "
    "thấp thay vì đoán chắc chắn. Không suy luận về giới tính, tuổi tác, "
    "chủng tộc hay đặc điểm nhân khẩu học khác — chỉ tập trung vào trang "
    "phục và hình thể quan sát được trực tiếp.\n\n"
    "Ngoài trang phục cơ bản, hãy CHỦ ĐỘNG kiểm tra thêm 3 nhóm chi tiết sau "
    "vì chúng thường phân biệt người rõ hơn màu sắc quần áo (ít bị ảnh hưởng "
    "bởi ánh sáng): (1) túi/balo/túi xách — có/không, màu, vị trí đeo; "
    "(2) loại trang phục (quần dài/short/váy/đầm, áo khoác/sơ mi/thun) và "
    "hoạ tiết vải (trơn/sọc/caro/hoạ tiết); (3) phụ kiện — kính, khẩu trang, "
    "vật đang cầm trên tay. Điền kết quả so sánh riêng cho từng nhóm.\n\n"
    "Vóc dáng và dáng đi CHỈ ghi chú tham khảo trong build_gait_note — KHÔNG "
    "dùng để quyết định same_person_likely/confidence, vì góc quay và "
    "khoảng cách camera dễ làm sai lệch nhận định về vóc dáng, còn dáng đi "
    "khó đánh giá đáng tin cậy từ 1 khung hình tĩnh. Để chuỗi rỗng nếu không "
    "có gì đáng ghi chú. Trả lời bằng cách gọi hàm record_comparison với kết "
    "quả đánh giá."
)

MATCH_ENUM = ["khop", "khac", "khong_du_du_lieu"]

COMPARISON_SCHEMA = {
    "type": "object",
    "properties": {
        "same_person_likely": {
            "type": "boolean",
            "description": "true nếu đặc điểm ngoại hình quan sát được phù hợp với cùng 1 người",
        },
        "confidence": {
            "type": "string",
            "enum": ["cao", "trung_binh", "thap"],
            "description": "Độ tin cậy của đánh giá — hạ xuống 'thap' nếu ảnh quá nhỏ/mờ/góc khác biệt",
        },
        "bag_match": {
            "type": "string", "enum": MATCH_ENUM,
            "description": "So sánh túi/balo/túi xách (có/không, màu, vị trí đeo) giữa 2 ảnh",
        },
        "clothing_type_match": {
            "type": "string", "enum": MATCH_ENUM,
            "description": "So sánh loại trang phục (quần/váy/đầm, áo khoác/sơ mi/thun) và hoạ tiết vải giữa 2 ảnh",
        },
        "accessories_match": {
            "type": "string", "enum": MATCH_ENUM,
            "description": "So sánh phụ kiện (kính, khẩu trang, vật đang cầm) giữa 2 ảnh",
        },
        "build_gait_note": {
            "type": "string",
            "description": "CHỈ THAM KHẢO, không dùng để quyết định same_person_likely: ghi chú ngắn nếu vóc dáng/dáng đi giữa 2 ảnh rõ ràng khác biệt hoặc rõ ràng tương đồng; để chuỗi rỗng nếu không đủ dữ liệu",
        },
        "reasoning": {
            "type": "string",
            "description": "Giải thích NGẮN GỌN (tối đa 2-3 câu): đặc điểm nào khớp, đặc điểm nào khác biệt hoặc không quan sát được",
        },
    },
    "required": [
        "same_person_likely", "confidence", "bag_match", "clothing_type_match",
        "accessories_match", "build_gait_note", "reasoning",
    ],
    "additionalProperties": False,
}

CONFIDENCE_SCORE = {"cao": 1.0, "trung_binh": 0.6, "thap": 0.3}


def is_configured() -> bool:
    import os
    return bool(os.environ.get("OPENAI_API_KEY"))


def get_setup_instructions() -> str:
    return (
        "Chưa cấu hình AI thị giác. Cần biến môi trường OPENAI_API_KEY.\n\n"
        "1. Lấy API key tại https://platform.openai.com/api-keys\n"
        "2. Đặt biến môi trường trong terminal (KHÔNG dán key vào chat): "
        "OPENAI_API_KEY=<api-key-của-bạn>\n"
        "3. Khởi động lại app.py từ terminal đã đặt biến đó\n\n"
        "Lưu ý: bước tạo tài khoản và khai báo thanh toán bạn cần tự thực hiện — "
        "Claude không thể làm hộ."
    )


# Tiết kiệm token: OpenAI Vision chia ảnh "auto"/"high" thành các ô 512x512
# để phân tích chi tiết (tốn nhiều token hơn); "low" xử lý ảnh trong 1 lượt ở
# độ phân giải tối đa ~512px (không tile). Đo thực tế trên API: 1 lệnh so
# sánh giảm từ ~1774 xuống ~1623-1676 token khi ảnh đã nhỏ hơn ngưỡng này.
# Crop người trong app (đo trên nhiều case thật) thường chỉ 25-490px mỗi
# chiều — dùng "low" cho ảnh trong ngưỡng KHÔNG mất chi tiết thật (ảnh vốn
# đã nhỏ hơn độ phân giải mà "low" xử lý), chỉ ảnh lớn hơn (vd fallback dùng
# cả ảnh gốc khi không detect được người) mới cần "auto" để giữ chi tiết.
LOW_DETAIL_MAX_DIM = 512


def _detail_for_dims(width: int, height: int) -> str:
    return "low" if max(width, height) <= LOW_DETAIL_MAX_DIM else "auto"


def _encode_bgr_to_data_url(image_bgr: np.ndarray) -> tuple[str, str]:
    """Trả về (data_url, detail_level)."""
    ok, buf = cv2.imencode(".jpg", image_bgr)
    if not ok:
        raise RuntimeError("Không mã hoá được ảnh sang JPEG")
    b64 = base64.standard_b64encode(buf.tobytes()).decode("utf-8")
    h, w = image_bgr.shape[:2]
    return f"data:image/jpeg;base64,{b64}", _detail_for_dims(w, h)


def _read_image_to_data_url(path: str) -> tuple[str, str]:
    """Trả về (data_url, detail_level)."""
    with open(path, "rb") as f:
        raw = f.read()
    b64 = base64.standard_b64encode(raw).decode("utf-8")
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    detail = _detail_for_dims(img.shape[1], img.shape[0]) if img is not None else "auto"
    return f"data:image/jpeg;base64,{b64}", detail


def compare_person_images(
    reference_data_url: str,
    candidate_data_url: str,
    model: str = DEFAULT_MODEL,
    reference_context: str = "",
    reference_detail: str = "auto",
    candidate_detail: str = "auto",
) -> dict:
    """So sánh 2 ảnh (data URL base64), trả về:
        {"same_person_likely": bool, "confidence": "cao"|"trung_binh"|"thap",
         "bag_match": ..., "clothing_type_match": ..., "accessories_match": ...,
         "build_gait_note": str, "reasoning": str}

    reference_context: tóm tắt các đặc điểm đã biết trước về ảnh tham chiếu
    (túi/balo, loại trang phục...) — xem describe_extended_attrs_vi(). Giúp
    model neo đánh giá vào đúng những gì đã quan sát được ở ảnh tham chiếu
    thay vì phải tự suy luận lại từ đầu mỗi lần, đặc biệt hữu ích khi ảnh
    tham chiếu nhỏ/mờ hơn ảnh ứng viên. Bỏ qua nếu để trống.

    Raises RuntimeError nếu chưa cấu hình API key hoặc API lỗi.
    """
    if not is_configured():
        raise RuntimeError(get_setup_instructions())

    client = OpenAI()

    content = [
        {"type": "input_text", "text": "Ảnh 1 — ảnh tham chiếu (người cần tìm):"},
        {"type": "input_image", "image_url": reference_data_url, "detail": reference_detail},
    ]
    if reference_context:
        content.append({
            "type": "input_text",
            "text": f"Thông tin đã biết trước về ảnh tham chiếu (từ bước mô tả riêng): {reference_context}",
        })
    content += [
        {"type": "input_text", "text": "Ảnh 2 — ứng viên phát hiện được trong video giám sát:"},
        {"type": "input_image", "image_url": candidate_data_url, "detail": candidate_detail},
        {"type": "input_text", "text": "Đánh giá 2 ảnh có khả năng là cùng 1 người hay không dựa trên đặc điểm ngoại hình quan sát được."},
    ]

    response = client.responses.create(
        model=model,
        reasoning=REASONING_EFFORT,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "record_comparison",
                "schema": COMPARISON_SCHEMA,
                "strict": True,
            },
        },
    )

    message = next((item for item in response.output if item.type == "message"), None)
    content = message.content[0] if message and message.content else None

    if content is None:
        raise RuntimeError("Không nhận được kết quả so sánh có cấu trúc từ model.")

    if content.type == "refusal":
        return {
            "same_person_likely": False,
            "confidence": "thap",
            "bag_match": "khong_du_du_lieu",
            "clothing_type_match": "khong_du_du_lieu",
            "accessories_match": "khong_du_du_lieu",
            "build_gait_note": "",
            "reasoning": f"Model từ chối xử lý yêu cầu này (an toàn nội dung): {content.refusal}",
        }

    import json
    return json.loads(content.text)


def compare_reference_crop_to_file(
    reference_bgr: np.ndarray,
    candidate_crop_path: str,
    model: str = DEFAULT_MODEL,
    reference_context: str = "",
) -> dict:
    ref_url, ref_detail = _encode_bgr_to_data_url(reference_bgr)
    cand_url, cand_detail = _read_image_to_data_url(candidate_crop_path)
    return compare_person_images(
        ref_url, cand_url, model=model, reference_context=reference_context,
        reference_detail=ref_detail, candidate_detail=cand_detail,
    )


# ---------------------------------------------------------------------------
# Mô tả đặc điểm ảnh tham chiếu — thay heuristic màu HSV cổ điển
# (modules/appearance.py) khi người dùng bật AI thị giác. Lý do cần: heuristic
# màu cổ điển đã quan sát thấy đọc sai trên ảnh thật (ánh sáng trong nhà ám
# vàng khiến vải xám đọc thành đỏ; tóc dài che vai bị đọc nhầm thành màu áo).
# Chỉ chạy 1 lần cho ảnh tham chiếu (không phải mỗi crop video) nên rẻ.
# ---------------------------------------------------------------------------

DESCRIBE_SYSTEM_PROMPT = (
    "Bạn đang hỗ trợ điều tra viên mô tả đặc điểm ngoại hình của 1 người trong "
    "ảnh (cắt từ camera giám sát hoặc ảnh chụp) để dùng làm ảnh tham chiếu tìm "
    "kiếm trong video. Chỉ mô tả những gì QUAN SÁT ĐƯỢC TRỰC TIẾP — nếu một "
    "đặc điểm không nhìn thấy rõ (bị che khuất, góc chụp, độ phân giải thấp), "
    "dùng giá trị 'khong_ro' thay vì đoán liều. Đặc biệt cẩn thận phân biệt "
    "màu TÓC với màu ÁO — nếu tóc dài che một phần vai/lưng, KHÔNG tính vùng "
    "đó là màu áo, chỉ mô tả phần vải thật sự nhìn thấy được. Không suy luận "
    "về giới tính, tuổi tác, chủng tộc hay đặc điểm nhân khẩu học khác.\n\n"
    "Ngoài 6 đặc điểm cơ bản, hãy mô tả thêm: túi/balo/túi xách (có/không, "
    "màu, vị trí đeo), loại trang phục phần dưới (quần dài/short/váy/đầm), "
    "loại áo (áo khoác/sơ mi/thun/hoodie), hoạ tiết vải (trơn/sọc/caro/hoạ "
    "tiết), và phụ kiện (kính, khẩu trang, vật đang cầm). Đây là những chi "
    "tiết PHÂN BIỆT NGƯỜI RÕ HƠN màu quần áo (ít bị ảnh hưởng bởi ánh sáng).\n\n"
    "build_note (vóc dáng) và gait_note (dáng đi): CHỈ ghi khi RẤT RÕ RÀNG, "
    "để chuỗi rỗng nếu không chắc — đây là ghi chú tham khảo thêm cho điều "
    "tra viên, không phải đặc điểm dùng để so khớp tự động, vì góc quay/"
    "khoảng cách camera dễ gây sai lệch nhận định về vóc dáng, còn dáng đi "
    "khó đánh giá đáng tin cậy từ 1 ảnh tĩnh."
)

_COLOR_ENUM = ["do", "vang", "xanh_la", "xanh_duong", "den", "trang", "xam", "khac", "khong_ro"]

DESCRIBE_ATTRIBUTES_SCHEMA = {
    "type": "object",
    "properties": {
        "color_top": {
            "type": "string",
            "enum": _COLOR_ENUM,
            "description": "Màu áo/phần trên cơ thể chủ đạo — CHỈ tính vải áo, không tính tóc",
        },
        "color_bottom": {
            "type": "string",
            "enum": _COLOR_ENUM,
            "description": "Màu quần/váy chủ đạo",
        },
        "sleeve_length": {"type": "string", "enum": ["dai_tay", "ngan_tay", "khong_ro"]},
        "has_hat": {
            "type": "string",
            "enum": ["co", "khong_ro"],
            "description": "'co' chỉ khi CHẮC CHẮN nhìn thấy mũ; nếu không có mũ hoặc không chắc, dùng 'khong_ro'",
        },
        "hairstyle": {"type": "string", "enum": ["dai", "ngan", "khong_ro"]},
        "has_shoes": {"type": "string", "enum": ["co", "khong", "khong_ro"]},
        "has_bag": {
            "type": "string", "enum": ["co", "khong", "khong_ro"],
            "description": "Có mang túi/balo/túi xách quan sát được không",
        },
        "bag_color": {
            "type": "string", "enum": _COLOR_ENUM,
            "description": "Màu túi/balo chủ đạo — chỉ có ý nghĩa nếu has_bag='co', dùng 'khong_ro' nếu khác",
        },
        "bag_position": {
            "type": "string", "enum": ["vai_trai", "vai_phai", "sau_lung", "cam_tay", "khong_ro"],
            "description": "Vị trí đeo/mang túi — chỉ có ý nghĩa nếu has_bag='co'",
        },
        "bottom_type": {
            "type": "string", "enum": ["quan_dai", "quan_short", "vay", "dam", "khong_ro"],
            "description": "Loại trang phục phần dưới cơ thể",
        },
        "outerwear_type": {
            "type": "string", "enum": ["ao_khoac", "so_mi", "thun", "hoodie", "khac", "khong_ro"],
            "description": "Loại áo/trang phục phần trên",
        },
        "pattern": {
            "type": "string", "enum": ["tron", "soc", "ca_ro", "hoa_tiet", "khong_ro"],
            "description": "Hoạ tiết vải quần áo (chọn cái nổi bật nhất nếu áo/quần khác hoạ tiết nhau)",
        },
        "has_glasses": {"type": "string", "enum": ["co", "khong", "khong_ro"]},
        "has_mask": {"type": "string", "enum": ["co", "khong", "khong_ro"], "description": "Khẩu trang che mặt"},
        "holding_object": {
            "type": "string", "enum": ["dien_thoai", "o_du", "khac", "khong", "khong_ro"],
            "description": "Vật đang cầm/sử dụng trên tay quan sát được, nếu có",
        },
        "build_note": {
            "type": "string",
            "description": "CHỈ THAM KHẢO: ghi chú ngắn về vóc dáng tương đối (vd 'dáng gầy') NẾU rất rõ ràng; để chuỗi rỗng nếu không chắc",
        },
        "gait_note": {
            "type": "string",
            "description": "CHỈ THAM KHẢO: ghi chú ngắn về dáng đi/tư thế đặc trưng (vd 'dùng gậy chống') NẾU rất rõ ràng; để chuỗi rỗng nếu ảnh tĩnh không đủ để đánh giá",
        },
        "reasoning": {"type": "string", "description": "Giải thích NGẮN GỌN (tối đa 2-3 câu) những gì quan sát được"},
    },
    "required": [
        "color_top", "color_bottom", "sleeve_length", "has_hat", "hairstyle", "has_shoes",
        "has_bag", "bag_color", "bag_position", "bottom_type", "outerwear_type", "pattern",
        "has_glasses", "has_mask", "holding_object", "build_note", "gait_note", "reasoning",
    ],
    "additionalProperties": False,
}

# Thuộc tính mở rộng CHỈ có khi dùng AI thị giác (heuristic màu cổ điển trong
# appearance.py không trích được — không khả thi để chạy VLM cho hàng nghìn
# crop video, xem VLM_POOL_PER_VIDEO trong demo_search.py) — nên KHÔNG tham
# gia công thức chấm điểm cục bộ (_score_against_reference), chỉ dùng để: (a)
# hiển thị mô tả ảnh tham chiếu đầy đủ hơn cho điều tra viên, (b) làm ngữ
# cảnh gửi kèm khi AI so sánh ứng viên (xem reference_context ở
# compare_person_images) — AI so sánh trực tiếp 2 ảnh nên tự nhận ra các chi
# tiết này mà không cần công thức so khớp riêng.
EXTENDED_REFERENCE_ATTRS = [
    "has_bag", "bag_color", "bag_position", "bottom_type", "outerwear_type",
    "pattern", "has_glasses", "has_mask", "holding_object",
]

BAG_POSITION_NAMES_VI = {
    "vai_trai": "vai trái", "vai_phai": "vai phải", "sau_lung": "sau lưng",
    "cam_tay": "cầm tay", "khong_ro": "không rõ",
}
BOTTOM_TYPE_NAMES_VI = {
    "quan_dai": "quần dài", "quan_short": "quần short", "vay": "váy", "dam": "đầm", "khong_ro": "không rõ",
}
OUTERWEAR_TYPE_NAMES_VI = {
    "ao_khoac": "áo khoác", "so_mi": "áo sơ mi", "thun": "áo thun", "hoodie": "hoodie",
    "khac": "khác", "khong_ro": "không rõ",
}
PATTERN_NAMES_VI = {"tron": "trơn", "soc": "sọc", "ca_ro": "caro", "hoa_tiet": "có hoạ tiết", "khong_ro": "không rõ"}
HOLDING_OBJECT_NAMES_VI = {
    "dien_thoai": "điện thoại", "o_du": "ô/dù", "khac": "vật khác", "khong": "không cầm gì", "khong_ro": "không rõ",
}
MATCH_NAMES_VI = {"khop": "khớp", "khac": "khác", "khong_du_du_lieu": "không đủ dữ liệu"}


def describe_extended_attrs_vi(extended: dict) -> str:
    """Tóm tắt tiếng Việt gọn cho các thuộc tính mở rộng (túi/balo, loại
    trang phục, hoạ tiết, phụ kiện) — dùng cả để hiển thị cho điều tra viên
    và làm reference_context gửi cho VLM khi so sánh ứng viên."""
    parts = []
    has_bag = extended.get("has_bag")
    if has_bag == "co":
        bag_color = COLOR_NAMES_VI.get(extended.get("bag_color"), "")
        bag_pos = BAG_POSITION_NAMES_VI.get(extended.get("bag_position"), "")
        detail = ", ".join(x for x in [bag_color, bag_pos] if x and x != "không rõ")
        parts.append("có túi/balo" + (f" ({detail})" if detail else ""))
    elif has_bag == "khong":
        parts.append("không mang túi")

    bottom_type = extended.get("bottom_type")
    if bottom_type and bottom_type != "khong_ro":
        parts.append(f"phần dưới: {BOTTOM_TYPE_NAMES_VI.get(bottom_type, bottom_type)}")

    outerwear = extended.get("outerwear_type")
    if outerwear and outerwear != "khong_ro":
        parts.append(f"áo: {OUTERWEAR_TYPE_NAMES_VI.get(outerwear, outerwear)}")

    pattern = extended.get("pattern")
    if pattern and pattern != "khong_ro":
        parts.append(f"hoạ tiết {PATTERN_NAMES_VI.get(pattern, pattern)}")

    if extended.get("has_glasses") == "co":
        parts.append("đeo kính")
    if extended.get("has_mask") == "co":
        parts.append("đeo khẩu trang")

    holding = extended.get("holding_object")
    if holding and holding not in ("khong", "khong_ro"):
        parts.append(f"đang cầm {HOLDING_OBJECT_NAMES_VI.get(holding, holding)}")

    return ", ".join(parts) if parts else "không có chi tiết bổ sung rõ ràng"


def describe_reference_attributes(image_bgr: np.ndarray, model: str = DEFAULT_MODEL) -> dict:
    """Dùng ChatGPT Vision mô tả trực tiếp đặc điểm ngoại hình của người trong
    ảnh tham chiếu. Trả về dict cùng vocabulary giá trị với
    appearance.extract_appearance() (color_top, color_bottom, sleeve_length,
    has_hat, hairstyle, has_shoes) — cắm thẳng vào pipeline chấm điểm hiện có
    mà không cần sửa gì ở search()/_score_against_reference().

    Raises RuntimeError nếu chưa cấu hình API key hoặc API lỗi.
    """
    if not is_configured():
        raise RuntimeError(get_setup_instructions())

    client = OpenAI()
    data_url, detail = _encode_bgr_to_data_url(image_bgr)

    response = client.responses.create(
        model=model,
        reasoning=REASONING_EFFORT,
        input=[
            {"role": "system", "content": DESCRIBE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Mô tả đặc điểm ngoại hình của người trong ảnh này."},
                    {"type": "input_image", "image_url": data_url, "detail": detail},
                ],
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "describe_attributes",
                "schema": DESCRIBE_ATTRIBUTES_SCHEMA,
                "strict": True,
            },
        },
    )

    message = next((item for item in response.output if item.type == "message"), None)
    content = message.content[0] if message and message.content else None

    if content is None:
        raise RuntimeError("Không nhận được kết quả mô tả có cấu trúc từ model.")

    if content.type == "refusal":
        raise RuntimeError(f"Model từ chối mô tả ảnh này (an toàn nội dung): {content.refusal}")

    import json
    return json.loads(content.text)


def vlm_verdict_to_score(verdict: dict) -> float:
    """Chuyển kết quả so sánh thành điểm 0..1 — 0 nếu model đánh giá KHÔNG
    phải cùng 1 người, bất kể độ tin cậy (tránh cho điểm dương tính khi model
    đã kết luận khác người, dù không chắc chắn)."""
    if not verdict.get("same_person_likely"):
        return 0.0
    return CONFIDENCE_SCORE.get(verdict.get("confidence"), 0.3)
