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
    # -------------------------------------------------------------------
    # Dynamically-generated placeholder / empty-state text. These live
    # inside HTML strings built by app.py's build_player_html(),
    # build_candidates_html(), build_evidence_panel(), and
    # on_clear_case_videos()/run_search()'s early-return branches -- NOT
    # simple component defaults -- so callers must pass the current
    # language into those functions explicitly. Does NOT cover the
    # per-candidate match explanation sentences (still built in Vietnamese
    # by demo_search.py) or the route map's internal markup (geo_route.py)
    # -- those remain a separate, larger localization task.
    # -------------------------------------------------------------------
    "player_no_video_selected": {
        "ko": "볼 영상을 선택하지 않았습니다.", "en": "No video selected to view.",
        "vi": "Chưa chọn video để xem.",
    },
    "player_video_not_found": {"ko": "영상을 찾을 수 없습니다.", "en": "Video not found.", "vi": "Không tìm thấy video."},
    "player_no_candidates_for_video": {
        "ko": "이 영상에는 아직 후보가 없습니다 — 먼저 검색을 눌러주세요.",
        "en": "No candidates for this video yet — click Search first.",
        "vi": "Chưa có ứng viên nào cho video này — bấm Tìm kiếm trước.",
    },
    "player_timeline_hint": {
        "ko": "타임라인의 색상 막대를 클릭하면 일치 의심 구간으로 이동합니다.",
        "en": "Click a colored bar on the timeline to jump to a suspected matching segment.",
        "vi": "Bấm vào vạch màu trên thanh thời gian để nhảy tới đoạn nghi có đối tượng khớp.",
    },
    "player_camera_prefix": {"ko": "카메라:", "en": "Camera:", "vi": "Camera:"},
    "player_marker_tooltip_template": {
        "ko": "트랙 {track} — 점수 {score} — {start}-{end}초",
        "en": "track {track} — score {score} — sec {start}-{end}",
        "vi": "track {track} — điểm {score} — giây {start}-{end}",
    },
    "clear_no_video_placeholder": {"ko": "*아직 영상이 없습니다.*", "en": "*No video yet.*", "vi": "*Chưa có video.*"},
    "candidates_no_results": {"ko": "*아직 결과가 없습니다.*", "en": "*No results yet.*", "vi": "*Chưa có kết quả.*"},
    "candidates_no_match_for_video": {
        "ko": "일치하는 대상이 없습니다.", "en": "No matching object.", "vi": "Không có đối tượng phù hợp.",
    },
    "evidence_no_selection": {
        "ko": "위 목록에서 후보를 선택하면 상세 정보가 표시됩니다.",
        "en": "Select a candidate in the list above to see details.",
        "vi": "Chọn 1 ứng viên trong danh sách bên trên để xem chi tiết.",
    },
    "route_select_case_first": {"ko": "먼저 사건을 선택하세요.", "en": "Select a case first.", "vi": "Chọn case trước."},
    "route_no_search_yet": {
        "ko": "아직 검색 결과가 없습니다 — 먼저 '검색'을 눌러주세요.",
        "en": "No search results yet — click 'Search' first.",
        "vi": "Chưa có kết quả tìm kiếm — bấm 'Tìm kiếm' trước.",
    },
    "route_not_viewed_yet": {"ko": "*아직 경로를 보지 않았습니다.*", "en": "*Route not viewed yet.*", "vi": "*Chưa xem lộ trình.*"},
    # -------------------------------------------------------------------
    # Evidence panel (full content) + search status + geo status + route
    # map popup text -- generated at request time by app.py, demo_search.py,
    # vlm_compare.py, and geo_route.py's build_route_map_html(). Added when
    # the static-chrome/placeholder localization above turned out not to be
    # enough -- investigators read this content the most.
    # -------------------------------------------------------------------
    "evidence_header_template": {
        "ko": "### 트랙 `{track}` — 카메라 {camera} — 일치 점수 {score}",
        "en": "### Track `{track}` — camera {camera} — match score {score}",
        "vi": "### Track `{track}` — camera {camera} — điểm khớp {score}",
    },
    "evidence_seen_template": {
        "ko": "출현: **{start}**초 ~ **{end}**초",
        "en": "Appears: second **{start}** to **{end}**",
        "vi": "Xuất hiện: giây **{start}** đến **{end}**",
    },
    "evidence_col_attribute": {"ko": "특징", "en": "Attribute", "vi": "Đặc điểm"},
    "evidence_col_value": {"ko": "값", "en": "Value", "vi": "Giá trị"},
    "evidence_col_confidence": {"ko": "신뢰도", "en": "Confidence", "vi": "Độ tin cậy"},
    "attr_color_top": {"ko": "상의 색상", "en": "Top color", "vi": "Màu áo"},
    "attr_color_bottom": {"ko": "하의 색상", "en": "Bottom color", "vi": "Màu quần"},
    "attr_sleeve": {"ko": "소매", "en": "Sleeve", "vi": "Tay áo"},
    "attr_hat": {"ko": "모자", "en": "Hat", "vi": "Mũ"},
    "attr_hair": {"ko": "머리", "en": "Hair", "vi": "Tóc"},
    "attr_shoes": {"ko": "신발", "en": "Shoes", "vi": "Giày"},
    "evidence_score_reason_title": {"ko": "**점수 근거:**", "en": "**Score reasoning:**", "vi": "**Lý do điểm số:**"},
    "evidence_vlm_title": {
        "ko": "**🔍 시각 AI 평가 (크롭 이미지를 OpenAI API로 전송함):**",
        "en": "**🔍 Visual AI assessment (crop images sent to the OpenAI API):**",
        "vi": "**🔍 Đánh giá bằng AI thị giác (đã gửi ảnh crop ra ngoài qua OpenAI API):**",
    },
    "vlm_same_person": {"ko": "동일 인물 가능성 있음", "en": "Likely the SAME person", "vi": "Có khả năng CÙNG người"},
    "vlm_diff_person": {"ko": "다른 인물 가능성 있음", "en": "Likely a DIFFERENT person", "vi": "Có khả năng KHÁC người"},
    "vlm_confidence_cao": {"ko": "높음", "en": "high", "vi": "cao"},
    "vlm_confidence_trung_binh": {"ko": "중간", "en": "medium", "vi": "trung bình"},
    "vlm_confidence_thap": {"ko": "낮음", "en": "low", "vi": "thấp"},
    "evidence_verdict_template": {
        "ko": "- 결론: **{same}** — 신뢰도: **{confidence}**",
        "en": "- Verdict: **{same}** — confidence: **{confidence}**",
        "vi": "- Kết luận: **{same}** — độ tin cậy: **{confidence}**",
    },
    "evidence_reasoning_prefix": {"ko": "- 이유:", "en": "- Reasoning:", "vi": "- Lý do:"},
    "evidence_reasoning_none": {"ko": "(없음)", "en": "(none)", "vi": "(không có)"},
    "evidence_bag_prefix": {"ko": "- 가방/배낭:", "en": "- Bag/backpack:", "vi": "- Túi/balo:"},
    "evidence_clothing_prefix": {
        "ko": "- 옷 종류 & 무늬:", "en": "- Clothing type & pattern:", "vi": "- Loại trang phục & hoạ tiết:",
    },
    "evidence_accessories_prefix": {
        "ko": "- 액세서리 (안경/마스크/소지품):", "en": "- Accessories (glasses/mask/handheld items):",
        "vi": "- Phụ kiện (kính/khẩu trang/đồ cầm tay):",
    },
    "evidence_build_gait_prefix": {
        "ko": "- 체형/걸음걸이 (참고용):", "en": "- Build/gait (reference only):", "vi": "- Vóc dáng/dáng đi (chỉ tham khảo):",
    },
    "evidence_color_score_template": {
        "ko": "- 색상 점수 (로컬): {local:.2f} → 결합 점수: {combined:.2f}",
        "en": "- Color score (local): {local:.2f} → combined score: {combined:.2f}",
        "vi": "- Điểm màu sắc (local): {local:.2f} → điểm kết hợp: {combined:.2f}",
    },
    "match_khop": {"ko": "일치", "en": "match", "vi": "khớp"},
    "match_khac": {"ko": "불일치", "en": "different", "vi": "khác"},
    "match_khong_du_du_lieu": {"ko": "데이터 부족", "en": "insufficient data", "vi": "không đủ dữ liệu"},
    # Score-explanation strings built by modules/demo_search.py
    "expl_skip_template": {
        "ko": "{attr}: 건너뜀 (한쪽 데이터 부족)",
        "en": "{attr}: skipped (insufficient data on one side)",
        "vi": "{attr}: bỏ qua (không đủ dữ liệu ở 1 trong 2 bên)",
    },
    "expl_compare_template": {
        "ko": "{attr}: 참조={ref} vs 트랙={track} -> {result} (가중치 {weight})",
        "en": "{attr}: reference={ref} vs track={track} -> {result} (weight {weight})",
        "vi": "{attr}: ảnh={ref} vs track={track} -> {result} (trọng số {weight})",
    },
    "expl_no_common_attrs": {
        "ko": "비교할 공통 특징이 부족합니다.", "en": "Not enough common features to compare.",
        "vi": "Không đủ đặc điểm chung để so sánh.",
    },
    "expl_reid_no_data": {
        "ko": "외형 특징(ReID): 임베딩 데이터가 없어 속성 점수만 사용합니다.",
        "en": "Appearance features (ReID): no embedding data available, using the attribute score only.",
        "vi": "Đặc điểm ngoại hình (ReID): chưa có dữ liệu embedding, dùng riêng điểm thuộc tính.",
    },
    "expl_reid_template": {
        "ko": "외형 특징(ReID): 유사도 {sim:.2f} -> 점수 {score:.2f} (가중치 {embed_w}) — 속성 점수 {attr:.2f} (가중치 {attr_w})",
        "en": "Appearance features (ReID): similarity {sim:.2f} -> score {score:.2f} (weight {embed_w}) — "
              "attribute score {attr:.2f} (weight {attr_w})",
        "vi": "Đặc điểm ngoại hình (ReID): tương đồng {sim:.2f} -> điểm {score:.2f} (trọng số {embed_w}) — "
              "điểm thuộc tính {attr:.2f} (trọng số {attr_w})",
    },
    # Reference-description sentence built by app.py's _describe()
    "ref_desc_template": {
        "ko": "상의 {top}, 하의 {bottom}, 소매 {sleeve}, {hat}, {hair}, {shoes}",
        "en": "top {top}, bottom {bottom}, sleeve {sleeve}, {hat}, {hair}, {shoes}",
        "vi": "áo {top}, quần {bottom}, tay áo {sleeve}, {hat}, {hair}, {shoes}",
    },
    # run_search() status / progress / error text (app.py)
    "ref_vlm_describe_error_template": {
        "ko": "⚠️ 참조 이미지 설명 중 시각 AI 오류, 로컬 색상 휴리스틱을 사용합니다: {error}",
        "en": "⚠️ Visual AI error while describing the reference image, using the local color heuristic instead: {error}",
        "vi": "⚠️ Lỗi AI thị giác khi mô tả ảnh tham chiếu, dùng heuristic màu cục bộ: {error}",
    },
    "search_progress_extract": {
        "ko": "참조 이미지 {n}장에서 특징을 추출하는 중...",
        "en": "Extracting features from {n} reference image(s)...",
        "vi": "Đang trích đặc điểm từ {n} ảnh tham chiếu...",
    },
    "search_progress_match": {
        "ko": "사건 전체 후보와 대조하는 중...", "en": "Matching against candidates across the case...",
        "vi": "Đang so khớp với các ứng viên trong toàn bộ case...",
    },
    "search_progress_vlm": {
        "ko": "크롭 이미지 {n}장을 ChatGPT Vision으로 전송하여 정밀 비교하는 중 (내부 네트워크 밖으로 전송)...",
        "en": "Sending {n} crop image(s) to ChatGPT Vision for refinement (leaves the local network)...",
        "vi": "Đang gửi {n} ảnh crop tới ChatGPT Vision để tinh chỉnh (gửi ra ngoài mạng nội bộ)...",
    },
    "search_progress_done": {"ko": "완료", "en": "Done", "vi": "Xong"},
    "search_err_no_case": {
        "ko": "⚠️ 먼저 사건을 선택하거나 생성하세요.", "en": "⚠️ Select or create a case first.",
        "vi": "⚠️ Chọn hoặc tạo case trước.",
    },
    "search_err_no_ref_images": {
        "ko": "⚠️ 참조 이미지를 1장 이상 선택하세요.", "en": "⚠️ Select at least 1 reference image.",
        "vi": "⚠️ Vui lòng chọn ít nhất 1 ảnh tham chiếu.",
    },
    "search_err_no_person_detected": {
        "ko": "❌ 참조 이미지에서 사람을 감지하지 못했습니다.", "en": "❌ No person was detected in any reference image.",
        "vi": "❌ Không phát hiện được người trong ảnh tham chiếu nào.",
    },
    "search_vlm_refined_note": {
        "ko": " 시각 AI(ChatGPT Vision)로 정밀 비교했습니다.", "en": " Refined using visual AI (ChatGPT Vision).",
        "vi": " Đã tinh chỉnh bằng AI thị giác (ChatGPT Vision).",
    },
    "search_vlm_error_note": {
        "ko": " ⚠️ 시각 AI 호출 오류, 로컬 색상 비교 결과를 사용합니다: {error}",
        "en": " ⚠️ Error calling visual AI, using local color-matching results instead: {error}",
        "vi": " ⚠️ Lỗi khi gọi AI thị giác, dùng kết quả so màu local: {error}",
    },
    "search_ref_features_prefix": {"ko": "참조 특징:", "en": "Reference features:", "vi": "Đặc điểm tham chiếu:"},
    "search_used_images_note": {
        "ko": " ({used}/{total}장 사용)", "en": " (used {used}/{total} images)", "vi": " (dùng {used}/{total} ảnh)",
    },
    "search_vlm_desc_prefix": {
        "ko": " · 시각 AI 설명: ", "en": " · Described by visual AI: ", "vi": " · Mô tả bằng AI thị giác: ",
    },
    "search_extra_details_prefix": {
        "ko": " · 기타 세부사항: ", "en": " · Other details: ", "vi": " · Chi tiết khác: ",
    },
    "search_build_note_prefix": {
        "ko": " · 체형 (참고용): ", "en": " · Build (reference only): ", "vi": " · Vóc dáng (chỉ tham khảo): ",
    },
    "search_gait_note_prefix": {
        "ko": " · 걸음걸이 (참고용): ", "en": " · Gait (reference only): ", "vi": " · Dáng đi (chỉ tham khảo): ",
    },
    "search_no_candidates": {
        "ko": "후보를 찾지 못했습니다.", "en": "No candidates found.", "vi": "Không tìm thấy ứng viên nào.",
    },
    "search_low_confidence_template": {
        "ko": "일치하는 대상을 찾지 못했습니다 — 최고 점수가 {best:.2f}에 불과해, 동일 인물로 신뢰하기에는 "
              "너무 낮습니다 (기준값 {threshold}).",
        "en": "No qualifying match found — the highest score was only {best:.2f}, too low to be confident "
              "it's the same person (threshold {threshold}).",
        "vi": "Không tìm thấy đối tượng phù hợp — điểm khớp cao nhất chỉ đạt {best:.2f}, quá thấp để tin cậy "
              "là cùng 1 người (ngưỡng {threshold}).",
    },
    "search_videos_with_matches_title": {
        "ko": "📹 대상이 나타난 영상 ({n}개):", "en": "📹 Videos where the subject appears ({n}):",
        "vi": "📹 Video có đối tượng xuất hiện ({n}):",
    },
    "search_candidates_qualified_title": {
        "ko": "기준을 충족한 후보 ({n}명, 영상당 최대 {top_k}명):",
        "en": "Qualifying candidates ({n}, up to {top_k} per video):",
        "vi": "Ứng viên phù hợp đủ tiêu chuẩn ({n}, tối đa {top_k} người/video):",
    },
    "search_video_match_row_template": {
        "ko": "- {label} — {n}회 출현, 최고 점수 {best:.2f}",
        "en": "- {label} — {n} appearance(s), best score {best:.2f}",
        "vi": "- {label} — {n} lần xuất hiện, điểm cao nhất {best:.2f}",
    },
    "search_no_videos": {"ko": "(없음)", "en": "(none)", "vi": "(không có)"},
    # Case / video management status text (app.py)
    "case_err_no_name": {
        "ko": "⚠️ 먼저 사건 이름을 입력하세요.", "en": "⚠️ Enter a case name first.", "vi": "⚠️ Nhập tên case trước.",
    },
    "case_created_template": {
        "ko": "✅ 사건 생성됨: {name}", "en": "✅ Case created: {name}", "vi": "✅ Đã tạo case: {name}",
    },
    "add_video_err_no_files": {
        "ko": "⚠️ 영상 파일을 1개 이상 선택하세요.", "en": "⚠️ Select at least 1 video file.",
        "vi": "⚠️ Chọn ít nhất 1 file video.",
    },
    "add_video_progress_template": {
        "ko": "영상 {i}/{n} 처리 중...", "en": "Processing video {i}/{n}...", "vi": "Đang xử lý video {i}/{n}...",
    },
    "add_video_success_template": {
        "ko": "✅ 영상 {count}개 추가됨. 현재 사건에 영상 {total}개가 있습니다.",
        "en": "✅ Added {count} video(s). The case now has {total} video(s).",
        "vi": "✅ Đã thêm {count} video. Case hiện có {total} video.",
    },
    "clear_err_no_case": {
        "ko": "⚠️ 먼저 사건을 선택하세요.", "en": "⚠️ Select a case first.", "vi": "⚠️ Chọn case trước.",
    },
    "clear_err_not_confirmed": {
        "ko": "⚠️ 삭제 전에 확인란을 체크하세요.", "en": "⚠️ Please tick the confirmation box before deleting.",
        "vi": "⚠️ Vui lòng tick xác nhận trước khi xoá.",
    },
    "clear_success_template": {
        "ko": "✅ 영상 {n}개를 사건에서 삭제했습니다. 사건이 비워졌으며 새 영상을 추가할 수 있습니다.",
        "en": "✅ Deleted {n} video(s) from the case. The case is now empty and ready for new videos.",
        "vi": "✅ Đã xoá {n} video khỏi case. Case hiện trống, sẵn sàng thêm video mới.",
    },
    # Geo (location/time) status text (app.py)
    "geo_err_select_first": {
        "ko": "⚠️ 사건과 영상을 먼저 선택하세요.", "en": "⚠️ Select a case and video first.",
        "vi": "⚠️ Chọn case và video trước.",
    },
    "geo_existing_data": {
        "ko": "이 영상에 대해 이전에 저장된 데이터가 있습니다 — 수정 후 다시 저장할 수 있습니다.",
        "en": "This video already has previously saved data — you can edit and save it again.",
        "vi": "Đã có dữ liệu đã lưu trước đó cho video này — có thể sửa rồi lưu lại.",
    },
    "geo_no_address_prefix": {
        "ko": "영상에 아직 주소가 없습니다 — ", "en": "This video has no address yet — ",
        "vi": "Video chưa có địa chỉ — ",
    },
    "geo_suggested_template": {
        "ko": "카메라 이름에서 제안: '{suggested}' (저장 전에 다시 확인하세요).",
        "en": "suggested from the camera name: '{suggested}' (verify before saving).",
        "vi": "gợi ý từ tên camera: '{suggested}' (kiểm tra lại trước khi lưu).",
    },
    "geo_no_suggestion": {
        "ko": "제안할 수 없습니다 (카메라 이름이 '이름_주소' 규칙을 따르지 않음).",
        "en": "no suggestion available (camera name doesn't follow the 'name_address' convention).",
        "vi": "chưa có gợi ý (tên camera không theo quy ước 'tên_địa chỉ').",
    },
    "geo_save_err_no_video": {
        "ko": "⚠️ 먼저 영상을 선택하세요.", "en": "⚠️ Select a video first.", "vi": "⚠️ Chọn video trước.",
    },
    "geo_save_err_no_address": {
        "ko": "⚠️ 좌표를 자동으로 찾기 위해 주소를 먼저 입력하세요.",
        "en": "⚠️ Enter an address first (used to look up coordinates automatically).",
        "vi": "⚠️ Nhập địa chỉ trước (dùng để tự tìm toạ độ).",
    },
    "geo_save_err_bad_time": {
        "ko": "⚠️ 촬영 시각 형식이 잘못되었습니다 — 'YYYY-MM-DD HH:MM:SS' 형식을 사용하세요 (예: 2026-08-06 14:30:00).",
        "en": "⚠️ Recording time has the wrong format — use 'YYYY-MM-DD HH:MM:SS' (e.g. 2026-08-06 14:30:00).",
        "vi": "⚠️ Giờ quay sai định dạng — dùng 'YYYY-MM-DD HH:MM:SS' (vd 2026-08-06 14:30:00).",
    },
    "geo_save_err_no_coords_template": {
        "ko": "⚠️ 주소 '{address}'의 좌표를 찾을 수 없습니다. 한국의 상세 주소(번지, 동 이름)는 OpenStreetMap에 "
              "데이터가 없을 수 있습니다 — 더 넓은 범위의 주소(동/구/시 이름)나 근처의 랜드마크를 시도해보세요.",
        "en": "⚠️ Could not find coordinates for address '{address}'. Detailed Korean addresses (building "
              "number, dong name) may not be covered by OpenStreetMap — try a broader address "
              "(neighborhood/district/city name) or a nearby landmark.",
        "vi": "⚠️ Không tìm được toạ độ cho địa chỉ '{address}'. Địa chỉ chi tiết (số nhà, tên dong) ở Hàn "
              "Quốc qua OpenStreetMap có thể chưa có dữ liệu — thử địa chỉ tổng quát hơn (tên phường/quận/"
              "thành phố) hoặc 1 địa danh gần đó.",
    },
    "geo_save_success_template": {
        "ko": "✅ 저장됨: {address} → 좌표 ({lat:.5f}, {lng:.5f})",
        "en": "✅ Saved: {address} → coordinates ({lat:.5f}, {lng:.5f})",
        "vi": "✅ Đã lưu: {address} → toạ độ ({lat:.5f}, {lng:.5f})",
    },
    # AI-vision (VLM) setup instructions (modules/vlm_compare.py)
    "vlm_setup_title": {
        "ko": "시각 AI가 설정되지 않았습니다. OPENAI_API_KEY 환경 변수가 필요합니다.",
        "en": "Visual AI is not configured. The OPENAI_API_KEY environment variable is required.",
        "vi": "Chưa cấu hình AI thị giác. Cần biến môi trường OPENAI_API_KEY.",
    },
    "vlm_setup_step1": {
        "ko": "1. https://platform.openai.com/api-keys 에서 API 키를 발급받으세요",
        "en": "1. Get an API key at https://platform.openai.com/api-keys",
        "vi": "1. Lấy API key tại https://platform.openai.com/api-keys",
    },
    "vlm_setup_step2": {
        "ko": "2. 터미널에서 환경 변수를 설정하세요 (채팅에 키를 붙여넣지 마세요): OPENAI_API_KEY=<your-api-key>",
        "en": "2. Set the environment variable in your terminal (do NOT paste the key into chat): "
              "OPENAI_API_KEY=<your-api-key>",
        "vi": "2. Đặt biến môi trường trong terminal (KHÔNG dán key vào chat): OPENAI_API_KEY=<api-key-của-bạn>",
    },
    "vlm_setup_step3": {
        "ko": "3. 해당 환경 변수가 설정된 터미널에서 app.py를 다시 시작하세요",
        "en": "3. Restart app.py from a terminal where that variable is set",
        "vi": "3. Khởi động lại app.py từ terminal đã đặt biến đó",
    },
    "vlm_setup_note": {
        "ko": "참고: 계정 생성 및 결제 정보 등록은 직접 진행해야 합니다 — Claude가 대신할 수 없습니다.",
        "en": "Note: account creation and billing setup must be done by you — Claude cannot do this for you.",
        "vi": "Lưu ý: bước tạo tài khoản và khai báo thanh toán bạn cần tự thực hiện — Claude không thể làm hộ.",
    },
    # Extended reference-attribute description (modules/vlm_compare.py)
    "ext_has_bag": {"ko": "가방/배낭 있음", "en": "has bag/backpack", "vi": "có túi/balo"},
    "ext_no_bag": {"ko": "가방 없음", "en": "no bag", "vi": "không mang túi"},
    "ext_bottom_prefix": {"ko": "하의: ", "en": "bottom: ", "vi": "phần dưới: "},
    "ext_outerwear_prefix": {"ko": "상의: ", "en": "top: ", "vi": "áo: "},
    "ext_pattern_prefix": {"ko": "무늬 ", "en": "pattern ", "vi": "hoạ tiết "},
    "ext_glasses": {"ko": "안경 착용", "en": "wearing glasses", "vi": "đeo kính"},
    "ext_mask": {"ko": "마스크 착용", "en": "wearing a mask", "vi": "đeo khẩu trang"},
    "ext_holding_prefix": {"ko": "들고 있음: ", "en": "holding: ", "vi": "đang cầm "},
    "ext_no_extra_details": {
        "ko": "추가로 특이한 세부사항 없음", "en": "no notable additional details",
        "vi": "không có chi tiết bổ sung rõ ràng",
    },
    # Route map popup text (modules/geo_route.py's build_route_map_html())
    "route_map_skipped_note_template": {
        "ko": "후보 {n}명이 있지만 해당 영상에 아직 좌표/촬영 시각이 설정되지 않았습니다 — 위의 '📍 카메라 "
              "위치 및 촬영 시각' 항목을 확인하세요.",
        "en": "There are {n} candidate(s) but their videos don't have location/recording time set yet — "
              "see the '📍 Camera location & recording time' section above.",
        "vi": "Có {n} ứng viên nhưng video tương ứng chưa thiết lập toạ độ/giờ quay — xem mục '📍 Vị trí "
              "camera & giờ quay thực'.",
    },
    "route_map_skipped_note_short_template": {
        "ko": "⚠️ 다른 후보 {n}명은 영상에 좌표/촬영 시각이 없어 제외되었습니다.",
        "en": "⚠️ {n} other candidate(s) were skipped because their video has no location/recording time set.",
        "vi": "⚠️ {n} ứng viên khác bị bỏ qua vì video chưa có toạ độ/giờ quay.",
    },
    "route_map_no_data": {
        "ko": "지도에 경로를 그리기 위한 데이터(카메라 좌표 + 실제 촬영 시각)가 아직 충분하지 않습니다.",
        "en": "Not enough data yet (camera coordinates + actual recording time) to plot a route on the map.",
        "vi": "Chưa có đủ dữ liệu (toạ độ camera + giờ quay thực tế) để dựng lộ trình trên bản đồ.",
    },
    "route_map_popup_camera": {"ko": "카메라:", "en": "Camera:", "vi": "Camera:"},
    "route_map_popup_time": {"ko": "시각:", "en": "Time:", "vi": "Giờ:"},
    "route_map_popup_score": {"ko": "일치 점수:", "en": "Match score:", "vi": "Điểm khớp:"},
    "route_map_popup_sightings_template": {
        "ko": "이 카메라에서 총 {n}회 일치 (가장 높은 신뢰도 점수 표시)",
        "en": "Total {n} matches at this camera (showing the highest-confidence score)",
        "vi": "Tổng {n} lần khớp tại camera này (hiện điểm tin cậy cao nhất)",
    },
    "route_map_popup_overlap_template": {
        "ko": "⚠️ 원래 좌표와 겹치는 지점 {n}개 (상세 주소가 해석되지 않음) — 지도에서 보기 쉽도록 살짝 "
              "분산했으며, 절대적으로 정확하지 않습니다.",
        "en": "⚠️ {n} point(s) overlapping the original coordinates (detailed address not resolved) — "
              "positions have been spread slightly for visibility, not exact.",
        "vi": "⚠️ {n} điểm trùng toạ độ gốc (địa chỉ chi tiết chưa giải mã được) — vị trí trên bản đồ đã "
              "tách nhẹ cho dễ nhìn, không chính xác tuyệt đối.",
    },
    "route_map_legend": {
        "ko": "점 위 숫자 = 각 카메라에 설정된 실제 촬영 시각 순서 (1 = 가장 이른 시각) — 점 색상은 신뢰도를 "
              "나타냅니다 (초록: 높음, 노랑: 중간, 주황: 낮음). 원래 좌표가 겹치는 점은 보기 쉽도록 살짝 "
              "분산했습니다 (각 점의 팝업 참고). 이는 가능성 있는 순서 제안일 뿐이며, 확정된 경로 결론이 "
              "아닙니다 — 수사관이 직접 확인해야 합니다.",
        "en": "The number on each point = order by each camera's ACTUAL recording time (1 = earliest) — "
              "point color reflects confidence (green: high, yellow: medium, orange: low). Points sharing "
              "the same original coordinates have been spread slightly for visibility (see each point's "
              "popup). This is only a plausible ordering suggestion, NOT a confirmed route conclusion — "
              "the investigator must verify it.",
        "vi": "Số trên điểm = thứ tự theo giờ quay THỰC TẾ đã thiết lập cho từng camera (1 = sớm nhất) — "
              "màu điểm theo độ tin cậy (xanh lá: cao, vàng: trung bình, cam: thấp). Điểm trùng toạ độ gốc "
              "được tách nhẹ để dễ nhìn (xem popup từng điểm). Đây là gợi ý thứ tự khả dĩ, KHÔNG PHẢI kết "
              "luận lộ trình chắc chắn — điều tra viên tự xác minh.",
    },
}

# ---------------------------------------------------------------------------
# Attribute VALUE lookup tables -- translate the fixed vocabulary codes
# stored in the DB / used by appearance.py & vlm_compare.py (e.g. "den",
# "dai_tay", "vai_trai") into the current language. Separate from STRINGS
# above because these are keyed by data code, not by UI-role identifier.
# ---------------------------------------------------------------------------

COLOR_VALUES: dict[str, dict[str, str]] = {
    "do": {"ko": "빨강", "en": "red", "vi": "đỏ"},
    "vang": {"ko": "노랑", "en": "yellow", "vi": "vàng"},
    "xanh_la": {"ko": "초록", "en": "green", "vi": "xanh lá"},
    "xanh_duong": {"ko": "파랑", "en": "blue", "vi": "xanh dương"},
    "den": {"ko": "검정", "en": "black", "vi": "đen"},
    "trang": {"ko": "흰색", "en": "white", "vi": "trắng"},
    "xam": {"ko": "회색", "en": "gray", "vi": "xám"},
    "khac": {"ko": "기타", "en": "other", "vi": "khác"},
    "khong_ro": {"ko": "불명확", "en": "unclear", "vi": "không rõ"},
}
SLEEVE_VALUES: dict[str, dict[str, str]] = {
    "dai_tay": {"ko": "긴팔", "en": "long sleeve", "vi": "dài tay"},
    "ngan_tay": {"ko": "반팔", "en": "short sleeve", "vi": "ngắn tay"},
    "khong_ro": {"ko": "불명확", "en": "unclear", "vi": "không rõ"},
}
HAT_VALUES: dict[str, dict[str, str]] = {
    "co": {"ko": "모자 착용", "en": "wearing a hat", "vi": "có mũ"},
    "khong_ro": {"ko": "불명확", "en": "unclear", "vi": "không rõ"},
}
HAIRSTYLE_VALUES: dict[str, dict[str, str]] = {
    "dai": {"ko": "긴 머리", "en": "long hair", "vi": "tóc dài"},
    "ngan": {"ko": "짧은 머리", "en": "short hair", "vi": "tóc ngắn"},
    "khong_ro": {"ko": "불명확", "en": "unclear", "vi": "không rõ"},
}
SHOES_VALUES: dict[str, dict[str, str]] = {
    "co": {"ko": "신발 착용", "en": "wearing shoes", "vi": "có giày"},
    "khong": {"ko": "신발 없음", "en": "no shoes", "vi": "không giày"},
    "khong_ro": {"ko": "불명확", "en": "unclear", "vi": "không rõ"},
}
BAG_POSITION_VALUES: dict[str, dict[str, str]] = {
    "vai_trai": {"ko": "왼쪽 어깨", "en": "left shoulder", "vi": "vai trái"},
    "vai_phai": {"ko": "오른쪽 어깨", "en": "right shoulder", "vi": "vai phải"},
    "sau_lung": {"ko": "등 뒤", "en": "on the back", "vi": "sau lưng"},
    "cam_tay": {"ko": "손에 듦", "en": "held in hand", "vi": "cầm tay"},
    "khong_ro": {"ko": "불명확", "en": "unclear", "vi": "không rõ"},
}
BOTTOM_TYPE_VALUES: dict[str, dict[str, str]] = {
    "quan_dai": {"ko": "긴 바지", "en": "long pants", "vi": "quần dài"},
    "quan_short": {"ko": "반바지", "en": "shorts", "vi": "quần short"},
    "vay": {"ko": "치마", "en": "skirt", "vi": "váy"},
    "dam": {"ko": "원피스", "en": "dress", "vi": "đầm"},
    "khong_ro": {"ko": "불명확", "en": "unclear", "vi": "không rõ"},
}
OUTERWEAR_TYPE_VALUES: dict[str, dict[str, str]] = {
    "ao_khoac": {"ko": "자켓/외투", "en": "jacket/coat", "vi": "áo khoác"},
    "so_mi": {"ko": "셔츠", "en": "shirt", "vi": "áo sơ mi"},
    "thun": {"ko": "티셔츠", "en": "t-shirt", "vi": "áo thun"},
    "hoodie": {"ko": "후드티", "en": "hoodie", "vi": "hoodie"},
    "khac": {"ko": "기타", "en": "other", "vi": "khác"},
    "khong_ro": {"ko": "불명확", "en": "unclear", "vi": "không rõ"},
}
PATTERN_VALUES: dict[str, dict[str, str]] = {
    "tron": {"ko": "무지", "en": "plain", "vi": "trơn"},
    "soc": {"ko": "줄무늬", "en": "striped", "vi": "sọc"},
    "ca_ro": {"ko": "체크무늬", "en": "plaid", "vi": "caro"},
    "hoa_tiet": {"ko": "패턴 있음", "en": "patterned", "vi": "có hoạ tiết"},
    "khong_ro": {"ko": "불명확", "en": "unclear", "vi": "không rõ"},
}
HOLDING_OBJECT_VALUES: dict[str, dict[str, str]] = {
    "dien_thoai": {"ko": "휴대폰", "en": "phone", "vi": "điện thoại"},
    "o_du": {"ko": "우산", "en": "umbrella", "vi": "ô/dù"},
    "khac": {"ko": "기타 물건", "en": "other object", "vi": "vật khác"},
    "khong": {"ko": "손에 든 것 없음", "en": "not holding anything", "vi": "không cầm gì"},
    "khong_ro": {"ko": "불명확", "en": "unclear", "vi": "không rõ"},
}

# Maps ATTRIBUTE_WEIGHTS keys (modules/demo_search.py) to STRINGS label keys
# and to the value table used to translate that attribute's raw code.
ATTR_LABEL_KEYS: dict[str, str] = {
    "color_top": "attr_color_top",
    "color_bottom": "attr_color_bottom",
    "sleeve_length": "attr_sleeve",
    "has_hat": "attr_hat",
    "hairstyle": "attr_hair",
    "has_shoes": "attr_shoes",
}
ATTR_VALUE_TABLES: dict[str, dict[str, dict[str, str]]] = {
    "color_top": COLOR_VALUES,
    "color_bottom": COLOR_VALUES,
    "sleeve_length": SLEEVE_VALUES,
    "has_hat": HAT_VALUES,
    "hairstyle": HAIRSTYLE_VALUES,
    "has_shoes": SHOES_VALUES,
}


def t(key: str, lang: str) -> str:
    """Look up a translated string. Falls back to English, then to the key
    itself, so a missing translation never crashes the UI."""
    entry = STRINGS.get(key, {})
    return entry.get(lang) or entry.get("en") or key


def value(table: dict[str, dict[str, str]], code: str | None, lang: str) -> str:
    """Look up a raw data code (e.g. 'den', 'dai_tay') in one of the
    attribute-value tables above. Falls back to English, then the raw code
    itself, so an unrecognized code never crashes the UI."""
    entry = table.get(code or "", {})
    return entry.get(lang) or entry.get("en") or (code or "?")


def describe_extended_attrs(extended: dict, lang: str) -> str:
    """Localized equivalent of vlm_compare's old describe_extended_attrs_vi()
    -- summarizes the extended reference attributes (bag, clothing type,
    pattern, accessories) collected when visual AI describes the reference
    image."""
    parts = []
    has_bag = extended.get("has_bag")
    if has_bag == "co":
        detail_codes = [extended.get("bag_color"), extended.get("bag_position")]
        detail = ", ".join(
            value(COLOR_VALUES if i == 0 else BAG_POSITION_VALUES, code, lang)
            for i, code in enumerate(detail_codes)
            if code and code != "khong_ro"
        )
        parts.append(t("ext_has_bag", lang) + (f" ({detail})" if detail else ""))
    elif has_bag == "khong":
        parts.append(t("ext_no_bag", lang))

    bottom_type = extended.get("bottom_type")
    if bottom_type and bottom_type != "khong_ro":
        parts.append(t("ext_bottom_prefix", lang) + value(BOTTOM_TYPE_VALUES, bottom_type, lang))

    outerwear = extended.get("outerwear_type")
    if outerwear and outerwear != "khong_ro":
        parts.append(t("ext_outerwear_prefix", lang) + value(OUTERWEAR_TYPE_VALUES, outerwear, lang))

    pattern = extended.get("pattern")
    if pattern and pattern != "khong_ro":
        parts.append(t("ext_pattern_prefix", lang) + value(PATTERN_VALUES, pattern, lang))

    if extended.get("has_glasses") == "co":
        parts.append(t("ext_glasses", lang))
    if extended.get("has_mask") == "co":
        parts.append(t("ext_mask", lang))

    holding = extended.get("holding_object")
    if holding and holding not in ("khong", "khong_ro"):
        parts.append(t("ext_holding_prefix", lang) + value(HOLDING_OBJECT_VALUES, holding, lang))

    return ", ".join(parts) if parts else t("ext_no_extra_details", lang)
