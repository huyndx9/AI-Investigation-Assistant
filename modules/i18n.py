"""
Static UI text translations for the Gradio interface (Korean / English /
Vietnamese).

Scope: only covers UI CHROME -- labels, buttons, section headers, static
instructions built once when the layout is created. It does NOT cover
dynamically generated text (search result summaries, evidence
explanations, error/status messages produced at request time by
app.py/demo_search.py/geo_route.py) -- those are still built in
Vietnamese. Localizing that dynamic content would mean rewriting the
string-building logic across several files and is a separate, larger
piece of work.

Keys are English identifiers so the mapping stays readable regardless of
which language is currently displayed.
"""

from __future__ import annotations

DEFAULT_LANGUAGE = "ko"
LANGUAGES = ["ko", "en", "vi"]

# Always shown in all three languages at once so the selector itself stays
# discoverable no matter which language is currently active.
LANGUAGE_SELECTOR_LABEL = "🌐 Language / 언어 / Ngôn ngữ"
LANGUAGE_CHOICES = [("한국어", "ko"), ("English", "en"), ("Tiếng Việt", "vi")]

STRINGS: dict[str, dict[str, str]] = {
    "app_header": {
        "ko": (
            "# AI Investigation Assistant — 데모\n\n"
            "모듈 1(수집 + 추적) + 모듈 2(외형 특징)를 시연하는 프로토타입입니다. "
            "**신원을 단정하지 않습니다** — 특징이 일치하는 후보일 뿐이며, "
            "수사관이 직접 검토하고 판단합니다.\n\n"
            "비교 대상 특징: 상의 색상, 하의 색상, 소매 길이, 모자, 머리 스타일, 신발. "
            "**성별을 추론하지 않습니다** — 저해상도 CCTV 영상으로 성별을 추론하는 것은 "
            "증거로 사용하기에 신뢰할 수 없습니다."
        ),
        "en": (
            "# AI Investigation Assistant — Demo\n\n"
            "Prototype demonstrating Module 1 (ingest + track) + Module 2 (appearance). "
            "**Not an identity conclusion** — only a candidate with matching characteristics; "
            "the investigator reviews and decides.\n\n"
            "Matching features: top color, bottom color, sleeve length, hat, hairstyle, shoes. "
            "**No gender inference** — inferring gender from low-resolution CCTV footage is not "
            "reliable enough to use as evidence."
        ),
        "vi": (
            "# AI Investigation Assistant — Demo\n\n"
            "Prototype minh hoạ Module 1 (ingest + track) + Module 2 (appearance). "
            "**Không phải kết luận danh tính** — chỉ là ứng viên có đặc điểm khớp, "
            "điều tra viên tự xem xét và quyết định.\n\n"
            "Đặc điểm dùng để so khớp: màu áo, màu quần, tay áo, mũ, kiểu tóc, giày. "
            "**Không có giới tính** — suy luận giới tính từ ảnh CCTV không đủ tin cậy để "
            "dùng làm bằng chứng."
        ),
    },
    "case_section_title": {"ko": "## 사건 (Case)", "en": "## Case Management", "vi": "## Vụ án (Case)"},
    "case_dropdown_label": {"ko": "작업 중인 사건", "en": "Current case", "vi": "Case đang làm việc"},
    "create_case_button": {"ko": "사건 생성", "en": "Create case", "vi": "Tạo case"},
    "new_case_name_label": {"ko": "새 사건 이름", "en": "New case name", "vi": "Tên case mới"},
    "new_case_name_placeholder": {
        "ko": "예: B구역 절도 사건 - 8/3",
        "en": "e.g. Theft case, Block B - Aug 3",
        "vi": "Vd: Vụ mất trộm khu B - 03/08",
    },
    "add_video_section_title": {
        "ko": "### 사건에 영상 추가", "en": "### Add video to case", "vi": "### Thêm video vào case",
    },
    "video_files_label": {
        "ko": "영상 파일 (여러 개 선택 가능 — 여러 카메라/출처). 업로드가 끝나면 사건에 자동으로 추가됩니다.",
        "en": "Video files (multiple allowed — multiple cameras/sources). Automatically added to "
              "the case once uploaded.",
        "vi": "Video (có thể chọn nhiều — nhiều camera/nguồn). Tải lên xong sẽ TỰ ĐỘNG thêm vào case.",
    },
    "camera_label_input_label": {
        "ko": "카메라 라벨 (선택 사항, 비워두면 파일명을 사용합니다 — 사용하려면 업로드 전에 입력하세요)",
        "en": "Camera label (optional; leave blank to use the file name — set before uploading if "
              "you want to use it)",
        "vi": "Nhãn camera (tuỳ chọn, để trống sẽ dùng tên file — đặt trước khi tải video lên nếu "
              "muốn dùng)",
    },
    "sample_fps_label": {"ko": "샘플링 속도 (fps)", "en": "Sampling rate (fps)", "vi": "Tốc độ lấy mẫu (fps)"},
    "clear_accordion_title": {
        "ko": "⚠️ 사건 데이터 삭제 (되돌릴 수 없음)",
        "en": "⚠️ Clear case data (cannot be undone)",
        "vi": "⚠️ Xoá dữ liệu case (không thể hoàn tác)",
    },
    "clear_accordion_markdown": {
        "ko": "데모 사건에 이전 테스트에서 남은 영상이 있을 수 있습니다 — 테스트 전에 선택한 사건이 "
              "완전히 비어 있는지 확인하려면 삭제하세요.",
        "en": "The demo case may still contain videos from previous tests — clear it to make sure "
              "the selected case is truly empty before testing.",
        "vi": "Case demo có thể còn video từ những lần test trước — xoá để chắc chắn case đang chọn "
              "thật sự trống trước khi kiểm thử.",
    },
    "clear_confirm_checkbox_label": {
        "ko": "이 작업은 선택한 사건의 모든 영상, 트랙, 추출된 특징을 영구적으로 삭제하며 되돌릴 수 "
              "없다는 것을 이해합니다.",
        "en": "I understand this permanently deletes all videos, tracks, and extracted features of "
              "the selected case — this cannot be undone.",
        "vi": "Tôi hiểu thao tác này xoá vĩnh viễn toàn bộ video, track và đặc điểm đã trích xuất của "
              "case đang chọn — không thể hoàn tác.",
    },
    "clear_videos_button": {
        "ko": "🗑️ 이 사건의 모든 영상 삭제",
        "en": "🗑️ Delete all videos in this case",
        "vi": "🗑️ Xoá tất cả video trong case này",
    },
    "ref_images_section_title": {
        "ko": "### 참조 이미지 (찾을 대상)", "en": "### Reference image (person to find)",
        "vi": "### Ảnh tham chiếu (người cần tìm)",
    },
    "ref_images_label": {
        "ko": "여러 장 선택 가능 (다양한 각도/순간)",
        "en": "Multiple images allowed (different angles/moments)",
        "vi": "Có thể chọn nhiều ảnh (nhiều góc/khoảnh khắc)",
    },
    "top_k_label": {
        "ko": "영상별 표시할 후보 수", "en": "Number of candidates shown PER VIDEO",
        "vi": "Số ứng viên hiển thị MỖI VIDEO",
    },
    "top_k_info": {
        "ko": "영상/카메라별로 개별 적용됩니다 — 모든 영상이 검토되며, 다른 영상에 밀려 제외되지 않습니다.",
        "en": "Applied separately per video/camera — every video is considered, none crowded out by "
              "another.",
        "vi": "Áp dụng riêng cho từng video/camera — video nào cũng được xét, không bị video khác "
              "chiếm hết chỗ.",
    },
    "use_vlm_label": {
        "ko": "🔍 시각 AI 사용 (ChatGPT Vision)", "en": "🔍 Use visual AI (ChatGPT Vision)",
        "vi": "🔍 Dùng AI thị giác (ChatGPT Vision)",
    },
    "use_vlm_info": {
        "ko": "⚠️ 이미지를 내부 네트워크 밖의 OpenAI API로 전송합니다. 활성화하면: (1) 로컬 색상 "
              "휴리스틱 대신 AI가 참조 이미지의 특징을 직접 설명합니다 (조명에 색조가 있거나 긴 "
              "머리가 어깨를 가릴 때 더 정확함); (2) 검색 후 AI가 상위 후보를 다시 비교합니다. "
              "OPENAI_API_KEY 설정이 필요합니다. 기본값은 꺼짐입니다.",
        "en": "⚠️ Sends images outside the local network to the OpenAI API. When enabled: (1) AI "
              "directly describes the reference image's features instead of the local color "
              "heuristic (more accurate when lighting has a color cast or long hair covers the "
              "shoulders); (2) AI re-compares the top candidates after search. Requires "
              "OPENAI_API_KEY to be configured. Off by default.",
        "vi": "⚠️ Gửi ảnh ra ngoài mạng nội bộ lên API của OpenAI. Bật sẽ: (1) AI mô tả trực tiếp "
              "đặc điểm ảnh tham chiếu thay cho thuật toán màu cục bộ (chính xác hơn khi ánh sáng "
              "ám màu hoặc tóc dài che vai); (2) AI so sánh lại top ứng viên sau khi tìm kiếm. Cần "
              "tự cấu hình OPENAI_API_KEY. Mặc định TẮT.",
    },
    "search_button": {"ko": "검색", "en": "Search", "vi": "Tìm kiếm"},
    "view_video_section_title": {"ko": "## 영상 보기", "en": "## Watch video", "vi": "## Xem video"},
    "video_dropdown_label": {
        "ko": "현재 보고 있는 영상", "en": "Currently viewing video", "vi": "Video đang xem",
    },
    "geo_section_title": {
        "ko": "##### 📍 위치 및 촬영 시각 (확장 기능, 선택 사항)",
        "en": "##### 📍 Location & recording time (extension, optional)",
        "vi": "##### 📍 Vị trí & giờ quay (mở rộng, tuỳ chọn)",
    },
    "geo_section_markdown": {
        "ko": "왼쪽에 표시된 영상에 적용됩니다 — 아래 '🗺️ 지도 위 경로' 항목에 필요합니다. 좌표는 "
              "항상 직접 확인해야 합니다.",
        "en": "Applies to the video currently shown on the left — required for the '🗺️ Route on "
              "map' section below. Coordinates should always be verified manually.",
        "vi": "Áp dụng cho video đang xem bên trái — cần cho mục '🗺️ Lộ trình trên bản đồ' bên "
              "dưới. Toạ độ luôn cần tự xác nhận.",
    },
    "geo_address_label": {"ko": "주소", "en": "Address", "vi": "Địa chỉ"},
    "geo_address_placeholder": {
        "ko": "예: 경기도 용인시", "en": "e.g. Yongin-si, Gyeonggi-do", "vi": "vd Yongin-si, Gyeonggi-do",
    },
    "geo_address_info": {
        "ko": "저장을 클릭하면 이 주소로 좌표를 자동으로 조회합니다 (OpenStreetMap).",
        "en": "Coordinates are automatically looked up from this address (OpenStreetMap) when you "
              "click Save.",
        "vi": "Toạ độ tự động tìm từ địa chỉ này (OpenStreetMap) khi bấm Lưu.",
    },
    "geo_start_time_label": {
        "ko": "실제 촬영 시작 시각", "en": "Actual recording start time", "vi": "Giờ bắt đầu quay thực",
    },
    "geo_save_button": {
        "ko": "위치 및 시각 저장", "en": "Save location & time", "vi": "Lưu vị trí & giờ quay",
    },
    "candidates_section_title": {
        "ko": "## 일치하는 후보", "en": "## Matching candidates", "vi": "## Ứng viên phù hợp",
    },
    "candidates_section_subtitle": {
        "ko": "*영상/카메라별로 그룹화됨 — 이미지를 클릭하면 영상에서 확인할 수 있습니다.*",
        "en": "*Grouped by video/camera — click an image to view it in the video.*",
        "vi": "*Nhóm theo video/camera — bấm vào 1 ảnh để xem trên video.*",
    },
    "evidence_section_title": {
        "ko": "## 증거 상세 정보", "en": "## Evidence details", "vi": "## Chi tiết bằng chứng (Evidence)",
    },
    "route_accordion_title": {
        "ko": "🗺️ 지도 위 경로 (확장 기능, 선택 사항)",
        "en": "🗺️ Route on map (extension, optional)",
        "vi": "🗺️ Lộ trình trên bản đồ (mở rộng, tuỳ chọn)",
    },
    "route_accordion_markdown": {
        "ko": "각 카메라의 실제 촬영 시각을 기준으로 조건을 충족하는 후보들을 연결합니다 — 먼저 위 "
              "영상 옆의 '📍' 항목에서 위치와 시각을 설정해야 합니다. 이는 일치 점수를 기반으로 한 "
              "가능성 있는 순서 제안일 뿐이며, **확정된 경로 결론이 아닙니다**.",
        "en": "Connects qualifying candidates by each camera's ACTUAL RECORDING TIME — you must set "
              "up location & time in the '📍' section next to the video above first. This is only a "
              "plausible ordering suggestion based on match scores, **not a confirmed route "
              "conclusion**.",
        "vi": "Nối các ứng viên đủ tiêu chuẩn theo GIỜ QUAY THỰC TẾ của từng camera — cần thiết lập "
              "vị trí & giờ quay ở mục '📍' cạnh video bên trên trước. Chỉ là gợi ý thứ tự khả dĩ "
              "dựa trên điểm khớp, **không phải kết luận lộ trình chắc chắn**.",
    },
    "show_route_button": {"ko": "경로 보기", "en": "View route", "vi": "Xem lộ trình"},
}


def t(key: str, lang: str) -> str:
    """Look up a translated string. Falls back to English, then to the key
    itself, so a missing translation never crashes the UI."""
    entry = STRINGS.get(key, {})
    return entry.get(lang) or entry.get("en") or key
