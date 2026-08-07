"""
Giao diện demo — quản lý case nhiều video, tìm theo ảnh tham chiếu, xem video
với timeline đánh dấu điểm khớp (bấm để nhảy tới).

ĐÂY LÀ PROTOTYPE MINH HOẠ, không phải giao diện Phase 1 MVP đầy đủ mô tả
trong PRD (chưa có audit log FR-15..17, chưa dùng body_build/accessories,
chấm điểm bằng công thức đơn giản chứ không phải Evidence Fusion thật —
xem modules/demo_search.py). Mục đích: kiểm chứng nhanh toàn bộ pipeline
Module 1 + Module 2 + luồng xem xét bằng chứng end-to-end.

Chạy: python app.py
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from urllib.parse import quote

import gradio as gr


def _load_dotenv(path: str = ".env") -> None:
    """Nạp biến môi trường từ file .env cục bộ (nếu có) — không ghi đè biến
    đã có sẵn trong môi trường. Tránh phải truyền API key qua tham số dòng
    lệnh hoặc chat."""
    env_path = Path(path)
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and value and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

sys.path.insert(0, str(Path(__file__).parent / "modules"))
from appearance import (  # noqa: E402
    COLOR_NAMES_VI, HAIRSTYLE_NAMES_VI, HAT_NAMES_VI, SHOES_NAMES_VI, SLEEVE_NAMES_VI,
)
from demo_search import (  # noqa: E402
    MIN_CONFIDENT_SCORE, VLM_POOL_PER_VIDEO, add_video_to_case, clear_case_videos, create_case,
    filter_prescreen_for_vlm, get_reference_appearance_multi, get_web_video_path, group_top_k_per_video,
    list_cases, list_videos_in_case, refine_with_vlm, search,
)
from highlight_video import build_highlighted_video  # noqa: E402
import audit_log  # noqa: E402
import geo_route  # noqa: E402
import vlm_compare  # noqa: E402

DB_PATH = "case.db"
OUTPUT_DIR = str(Path("output").resolve())
MARKER_COLORS = ["#ff5252", "#4caf50", "#2196f3", "#ffc107", "#e040fb", "#00bcd4", "#ff9800", "#8bc34a"]


# ---------------------------------------------------------------------------
# Trợ giúp hiển thị
# ---------------------------------------------------------------------------

def _describe(features: dict) -> str:
    top = COLOR_NAMES_VI.get(features.get("color_top"), features.get("color_top"))
    bottom = COLOR_NAMES_VI.get(features.get("color_bottom"), features.get("color_bottom"))
    sleeve = SLEEVE_NAMES_VI.get(features.get("sleeve_length"), features.get("sleeve_length"))
    hat = HAT_NAMES_VI.get(features.get("has_hat"), features.get("has_hat"))
    hair = HAIRSTYLE_NAMES_VI.get(features.get("hairstyle"), features.get("hairstyle"))
    shoes = SHOES_NAMES_VI.get(features.get("has_shoes"), features.get("has_shoes"))
    return f"áo {top}, quần {bottom}, tay áo {sleeve}, {hat}, {hair}, {shoes}"


def _describe_videos_with_matches(candidates: list[dict]) -> dict:
    """Tóm tắt danh sách video có ít nhất 1 ứng viên đủ tiêu chuẩn — mục "1"
    trong 2 phần kết quả (video nào có đối tượng xuất hiện). Tách riêng khỏi
    danh sách ứng viên chi tiết (mục "2") vì điều tra viên cần biết ngay CÓ
    BAO NHIÊU camera/video ghi nhận đối tượng trước khi đọc từng ứng viên."""
    by_video: dict[str, list[dict]] = {}
    for c in candidates:
        by_video.setdefault(c["video_label"], []).append(c)
    rows = [
        (label, len(items), max(c["score"] for c in items))
        for label, items in by_video.items()
    ]
    rows.sort(key=lambda r: r[2], reverse=True)
    text = "\n".join(f"- {label} — {n} lần xuất hiện, điểm cao nhất {best:.2f}" for label, n, best in rows)
    return {"n_videos": len(rows), "text": text or "(không có)"}


def _case_label(c: dict) -> str:
    return f"{c['name']} ({c['n_videos']} video)"


def _case_choices(db_path: str) -> list[tuple[str, str]]:
    return [(_case_label(c), c["case_id"]) for c in list_cases(db_path)]


def _video_label(v: dict) -> str:
    return v["camera_label"] or Path(v["source_path"]).name


def _video_choices(db_path: str, case_id: str) -> list[tuple[str, str]]:
    if not case_id:
        return []
    return [(_video_label(v), v["video_id"]) for v in list_videos_in_case(db_path, case_id)]


def _file_url(path: str) -> str:
    return "/gradio_api/file=" + quote(str(Path(path).resolve()).replace("\\", "/"))


def build_player_html(case_id: str, video_id: str, candidates: list[dict], highlight_track_id: str | None) -> str:
    """Video + thanh thời gian có đánh dấu các đoạn ứng viên khớp trong VIDEO
    NÀY (lọc theo video_id — timeline chỉ có ý nghĩa trong 1 video). Bấm vào
    1 vạch màu để nhảy player tới đúng giây đó. Ứng viên đang chọn (nếu có)
    được viền trắng để dễ nhận ra."""
    if not video_id:
        return "<div style='color:#888;padding:20px;'>Chưa chọn video để xem.</div>"

    videos = {v["video_id"]: v for v in list_videos_in_case(DB_PATH, case_id)}
    video = videos.get(video_id)
    if video is None:
        return "<div style='color:#888;padding:20px;'>Không tìm thấy video.</div>"

    duration = (video["total_frames"] / video["fps"]) if video["fps"] else 0
    this_video_candidates = [c for c in candidates if c["video_id"] == video_id]

    if this_video_candidates:
        # Vẽ khung + nhãn cho các track ứng viên, cùng màu với vạch trên
        # timeline bên dưới để dễ đối chiếu — cache theo bộ track_id cụ thể
        # (đổi kết quả tìm kiếm khác sẽ tạo bản mới, không dùng nhầm bản cũ).
        track_specs = [
            {
                "track_id": c["track_id"],
                "label": f"{c['track_id'].split('_')[-1]} ({c['score']:.2f})",
                "color": MARKER_COLORS[i % len(MARKER_COLORS)],
            }
            for i, c in enumerate(this_video_candidates)
        ]
        cache_key = hashlib.sha1(",".join(sorted(t["track_id"] for t in track_specs)).encode()).hexdigest()[:10]
        highlighted_path = str(Path(OUTPUT_DIR) / case_id / "web" / f"{video_id}_hl_{cache_key}.mp4")
        web_path = build_highlighted_video(DB_PATH, video["source_path"], video_id, track_specs, highlighted_path)
    else:
        web_path = get_web_video_path(DB_PATH, case_id, video_id, OUTPUT_DIR)

    video_url = _file_url(web_path)

    seek_fragment = ""
    marker_divs = []
    for i, c in enumerate(this_video_candidates):
        color = MARKER_COLORS[i % len(MARKER_COLORS)]
        left_pct = (c["first_seen_sec"] / duration * 100) if duration else 0
        width_pct = max(0.8, (c["last_seen_sec"] - c["first_seen_sec"]) / duration * 100) if duration else 0.8
        border = "border:2px solid #fff;" if c["track_id"] == highlight_track_id else ""
        marker_divs.append(
            f'<div style="position:absolute;left:{left_pct:.2f}%;width:{width_pct:.2f}%;top:0;bottom:0;'
            f'background:{color};cursor:pointer;border-radius:2px;{border}" '
            f'title="track {c["track_id"].split(chr(95))[-1]} — điểm {c["score"]:.2f} — '
            f'giây {c["first_seen_sec"]}-{c["last_seen_sec"]}" '
            f"onclick=\"var v=document.getElementById('aia_player'); "
            f"v.currentTime={c['first_seen_sec']}; v.play();\"></div>"
        )
        if c["track_id"] == highlight_track_id:
            seek_fragment = f"#t={c['first_seen_sec']}"

    markers_html = "".join(marker_divs) or '<div style="color:#666;font-size:11px;padding:4px;">Chưa có ứng viên nào cho video này — bấm Tìm kiếm trước.</div>'

    return f'''
    <div style="font-family:sans-serif;">
      <div style="font-size:13px;color:#aaa;margin-bottom:4px;">Camera: {_video_label(video)}</div>
      <video id="aia_player" src="{video_url}{seek_fragment}" controls style="width:100%;max-height:420px;background:#000;border-radius:6px;"></video>
      <div style="position:relative;height:22px;background:#222;margin-top:6px;border-radius:4px;overflow:hidden;">
        {markers_html}
      </div>
      <div style="font-size:11px;color:#888;margin-top:4px;">Bấm vào vạch màu trên thanh thời gian để nhảy tới đoạn nghi có đối tượng khớp.</div>
    </div>
    '''


def build_candidates_html(candidates: list[dict], all_video_labels: list[str] | None = None) -> str:
    """Danh sách ứng viên NHÓM THEO VIDEO — mỗi hàng là 1 video/camera, tên
    video ở đầu hàng. Trước đây dùng gr.Gallery dạng lưới phẳng: không biết
    ảnh nào thuộc video nào nếu không đọc chữ nhỏ trong caption, và ảnh bị
    CẮT do Gallery ép vào ô vuông cố định (object-fit: cover). Ở đây tự dựng
    HTML: ảnh dùng object-fit: contain (luôn hiện đủ cả ảnh, có viền đệm nếu
    tỉ lệ khác ô), nhóm rõ theo video.

    all_video_labels: TOÀN BỘ video trong case (kể cả video không có ứng
    viên nào) — nếu truyền vào, những video không xuất hiện trong candidates
    vẫn được liệt kê kèm dòng "Không có đối tượng phù hợp", thay vì bị lược
    bỏ hoàn toàn khỏi báo cáo. Lý do cần: điều tra viên cần biết "đã kiểm tra
    camera này, không thấy" — khác với "camera này chưa từng được xét".

    Bấm vào 1 ảnh cần gọi được callback Python (tương đương gallery.select()
    cũ) — nhưng gr.HTML không có sự kiện click sẵn, nên dùng 1 ô nhập (KHÔNG
    dùng visible=False — đã xác nhận thực tế Gradio 6 không mount DOM cho ô
    ẩn kiểu đó nên JS không tìm thấy; ô này visible=True nhưng tự ẩn bằng CSS
    ở phần đầu layout) làm cầu nối: onclick set giá trị ô + dispatch 'input'
    -> Python lắng nghe qua .change(). Cùng kỹ thuật với các vạch thời gian
    trong build_player_html (onclick chèn qua innerHTML vẫn chạy bình
    thường, chỉ riêng thẻ <script> mới không — xem giải thích đầy đủ trong
    modules/geo_route.py)."""
    if not candidates and not all_video_labels:
        return "<p style='color:#888'>Chưa có kết quả.</p>"

    order: list[str] = []
    groups: dict[str, list[tuple[int, dict]]] = {}
    for idx, c in enumerate(candidates):
        key = c["video_label"]
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append((idx, c))

    for label in all_video_labels or []:
        if label not in groups:
            groups[label] = []
            order.append(label)

    select_js = (
        "var w=document.getElementById('aia_gallery_idx'),i=w.querySelector('input'),"
        "s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
        "s.call(i,{idx});i.dispatchEvent(new Event('input',{{bubbles:true}}));"
    )

    rows = []
    for video_label in order:
        items = groups[video_label]
        if not items:
            rows.append(
                f'<div style="margin-bottom:12px;">'
                f'<div style="font-size:13px;font-weight:600;color:#eee;margin-bottom:4px;">📹 {video_label}</div>'
                f'<div style="font-size:12px;color:#666;">Không có đối tượng phù hợp.</div></div>'
            )
            continue
        thumbs = []
        for idx, c in items:
            if not c.get("sample_crop_path"):
                continue
            src = _file_url(c["sample_crop_path"])
            caption = f"#{idx + 1} · {c['score']:.2f} · {c['first_seen_sec']}-{c['last_seen_sec']}s"
            onclick = select_js.format(idx=idx)
            thumbs.append(
                f'<div onclick="{onclick}" style="cursor:pointer;flex:0 0 auto;text-align:center;">'
                f'<div style="width:100px;height:150px;background:#181818;border-radius:6px;'
                f'display:flex;align-items:center;justify-content:center;overflow:hidden;border:1px solid #333;">'
                f'<img src="{src}" style="max-width:100%;max-height:100%;object-fit:contain;" /></div>'
                f'<div style="font-size:10px;color:#999;margin-top:3px;width:100px;">{caption}</div></div>'
            )
        if not thumbs:
            continue
        rows.append(
            f'<div style="margin-bottom:12px;">'
            f'<div style="font-size:13px;font-weight:600;color:#eee;margin-bottom:6px;">📹 {video_label}</div>'
            f'<div style="display:flex;gap:8px;overflow-x:auto;padding-bottom:6px;">{"".join(thumbs)}</div></div>'
        )

    return f'<div style="font-family:sans-serif;">{"".join(rows)}</div>'


def build_evidence_panel(candidate: dict | None) -> str:
    """Bảng đặc điểm đầy đủ của 1 ứng viên đang chọn — tra cứu trực tiếp,
    không phải đọc văn bản dài."""
    if candidate is None:
        return "*Chọn 1 ứng viên trong danh sách bên dưới để xem chi tiết.*"

    a = candidate["track_appearance"]

    def row(label: str, value: str, conf_key: str) -> str:
        conf = a.get(conf_key, 0.0)
        return f"| {label} | {value} | {conf:.0%} |"

    lines = [
        f"### Track `{candidate['track_id'].split('_')[-1]}` — camera {candidate['video_label']} — điểm khớp {candidate['score']:.2f}",
        f"Xuất hiện: giây **{candidate['first_seen_sec']}** đến **{candidate['last_seen_sec']}**",
        "",
        "| Đặc điểm | Giá trị | Độ tin cậy |",
        "|---|---|---|",
        row("Màu áo", COLOR_NAMES_VI.get(a.get("color_top"), "?"), "color_top_confidence"),
        row("Màu quần", COLOR_NAMES_VI.get(a.get("color_bottom"), "?"), "color_bottom_confidence"),
        row("Tay áo", SLEEVE_NAMES_VI.get(a.get("sleeve_length"), "?"), "sleeve_length_confidence"),
        row("Mũ", HAT_NAMES_VI.get(a.get("has_hat"), "?"), "has_hat_confidence"),
        row("Tóc", HAIRSTYLE_NAMES_VI.get(a.get("hairstyle"), "?"), "hairstyle_confidence"),
        row("Giày", SHOES_NAMES_VI.get(a.get("has_shoes"), "?"), "has_shoes_confidence"),
        "",
        "**Lý do điểm số:**",
    ]
    for e in candidate["explanation"]:
        lines.append(f"- {e}")

    verdict = candidate.get("vlm_verdict")
    if verdict:
        lines.append("")
        lines.append("---")
        lines.append("**🔍 Đánh giá bằng AI thị giác (đã gửi ảnh crop ra ngoài qua OpenAI API):**")
        same = "Có khả năng CÙNG người" if verdict.get("same_person_likely") else "Có khả năng KHÁC người"
        conf_vi = {"cao": "cao", "trung_binh": "trung bình", "thap": "thấp"}.get(verdict.get("confidence"), "?")
        lines.append(f"- Kết luận: **{same}** — độ tin cậy: **{conf_vi}**")
        lines.append(f"- Lý do: {verdict.get('reasoning', '(không có)')}")
        bag_m = verdict.get("bag_match")
        if bag_m:
            lines.append(f"- Túi/balo: {vlm_compare.MATCH_NAMES_VI.get(bag_m, bag_m)}")
        cloth_m = verdict.get("clothing_type_match")
        if cloth_m:
            lines.append(f"- Loại trang phục & hoạ tiết: {vlm_compare.MATCH_NAMES_VI.get(cloth_m, cloth_m)}")
        acc_m = verdict.get("accessories_match")
        if acc_m:
            lines.append(f"- Phụ kiện (kính/khẩu trang/đồ cầm tay): {vlm_compare.MATCH_NAMES_VI.get(acc_m, acc_m)}")
        bg_note = verdict.get("build_gait_note")
        if bg_note:
            lines.append(f"- Vóc dáng/dáng đi (chỉ tham khảo): {bg_note}")
        if "local_score" in candidate:
            lines.append(f"- Điểm màu sắc (local): {candidate['local_score']:.2f} → điểm kết hợp: {candidate['score']:.2f}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Case management callbacks
# ---------------------------------------------------------------------------

def on_create_case(case_name):
    if not case_name or not case_name.strip():
        return gr.update(), gr.update(), "⚠️ Nhập tên case trước."
    case_id = create_case(DB_PATH, case_name.strip())
    choices = _case_choices(DB_PATH)
    return gr.update(choices=choices, value=case_id), "", f"✅ Đã tạo case: {case_name}"


def on_refresh_cases():
    choices = _case_choices(DB_PATH)
    return gr.update(choices=choices)


def on_add_videos(case_id, video_files, camera_label, sample_fps, progress=gr.Progress()):
    if not case_id:
        return gr.update(), "⚠️ Chọn hoặc tạo case trước.", gr.update(), gr.update(), "", "", ""
    if not video_files:
        return gr.update(), "⚠️ Chọn ít nhất 1 file video.", gr.update(), gr.update(), "", "", ""

    files = video_files if isinstance(video_files, list) else [video_files]
    for i, f in enumerate(files):
        progress((i + 1) / len(files), desc=f"Đang xử lý video {i + 1}/{len(files)}...")
        label = camera_label.strip() if camera_label and camera_label.strip() else None
        add_video_to_case(DB_PATH, case_id, f, camera_label=label, sample_fps=sample_fps)

    video_choices = _video_choices(DB_PATH, case_id)
    n = len(video_choices)
    new_video_id = video_choices[-1][1] if video_choices else None
    # Xây lại player trực tiếp thay vì chỉ đổi value của video_dropdown và
    # trông chờ video_dropdown.change() tự kích hoạt on_video_selected — đã
    # xác nhận cascade đó không đáng tin cậy (video hiển thị bị cũ sau khi
    # thêm video mới), nên gọi thẳng build_player_html() ở đây. Tương tự cho
    # phần vị trí camera — gọi thẳng on_geo_video_selected() thay vì trông
    # chờ video_dropdown.change() tự kích hoạt.
    player_html = build_player_html(case_id, new_video_id, [], None) if new_video_id else "*Chưa có video.*"
    geo_addr, geo_start, geo_stat = (
        on_geo_video_selected(case_id, new_video_id) if new_video_id else ("", "", "")
    )
    return (
        gr.update(choices=video_choices, value=new_video_id),
        f"✅ Đã thêm {len(files)} video. Case hiện có {n} video.",
        gr.update(choices=_case_choices(DB_PATH), value=case_id),
        player_html,
        geo_addr, geo_start, geo_stat,
    )


def on_case_selected(case_id):
    video_choices = _video_choices(DB_PATH, case_id)
    new_video_id = video_choices[0][1] if video_choices else None
    player_html = build_player_html(case_id, new_video_id, [], None) if new_video_id else "*Chưa có video.*"
    geo_addr, geo_start, geo_stat = (
        on_geo_video_selected(case_id, new_video_id) if new_video_id else ("", "", "")
    )
    return (
        gr.update(choices=video_choices, value=new_video_id),
        player_html,
        geo_addr, geo_start, geo_stat,
    )


def on_video_selected(case_id, video_id, candidates):
    html = build_player_html(case_id, video_id, candidates or [], None)
    return html


def on_clear_case_videos(case_id, confirmed):
    """Xoá toàn bộ video + dữ liệu dẫn xuất của case đang chọn. Yêu cầu tick
    xác nhận trước — thao tác không thể hoàn tác (xem clear_case_videos)."""
    if not case_id:
        return (
            gr.update(), gr.update(), "⚠️ Chọn case trước.", gr.update(), None, "*Chưa có kết quả.*", "",
            "*Chưa có kết quả.*", False, "", "", "", None, None,
        )
    if not confirmed:
        return (
            gr.update(), gr.update(), "⚠️ Vui lòng tick xác nhận trước khi xoá.",
            gr.update(), None, "*Chưa có kết quả.*", "", "*Chưa có kết quả.*", False, "", "", "", None, None,
        )

    n = clear_case_videos(DB_PATH, case_id)
    player_html = "*Chưa có video.*"
    return (
        gr.update(choices=[], value=None),  # video_dropdown
        gr.update(choices=_case_choices(DB_PATH), value=case_id),  # case_dropdown
        f"✅ Đã xoá {n} video khỏi case. Case hiện trống, sẵn sàng thêm video mới.",  # clear_status
        player_html,  # player
        None, "*Chưa có kết quả.*", "", "*Chưa có kết quả.*",  # candidates_state, gallery, search_status, evidence_panel
        False,  # clear_confirm_input (tự bỏ tick sau khi xoá xong)
        "", "", "",  # geo_address/start_time/status — reset
        None, None,  # current_run_id_state, current_candidate_state — reset, tránh chấm feedback nhầm lần chạy cũ
    )


# ---------------------------------------------------------------------------
# Tìm kiếm
# ---------------------------------------------------------------------------

def run_search(case_id, ref_image_paths, top_k, use_vlm, progress=gr.Progress()):
    # 8 giá trị trả về cho MỌI nhánh (kể cả lỗi sớm): thêm run_id (audit log,
    # None nếu chưa thực sự chạy search) + candidate đang xem (để nút feedback
    # Đúng/Sai/Cần xem lại biết đang chấm cho track nào — xem
    # current_candidate_state, modules/audit_log.py).
    if not case_id:
        return None, "*Chưa có kết quả.*", "⚠️ Chọn hoặc tạo case trước.", gr.update(), "*Chưa có kết quả.*", gr.update(), None, None
    if not ref_image_paths:
        return None, "*Chưa có kết quả.*", "⚠️ Vui lòng chọn ít nhất 1 ảnh tham chiếu.", gr.update(), "*Chưa có kết quả.*", gr.update(), None, None
    if use_vlm and not vlm_compare.is_configured():
        return None, "*Chưa có kết quả.*", f"⚠️ {vlm_compare.get_setup_instructions()}", gr.update(), "*Chưa có kết quả.*", gr.update(), None, None

    progress(0.1, desc=f"Đang trích đặc điểm từ {len(ref_image_paths)} ảnh tham chiếu...")
    ref_features = get_reference_appearance_multi(ref_image_paths, use_vlm=use_vlm)
    if ref_features is None:
        return None, "*Chưa có kết quả.*", "❌ Không phát hiện được người trong ảnh tham chiếu nào.", gr.update(), "*Chưa có kết quả.*", gr.update(), None, None

    progress(0.5, desc="Đang so khớp với các ứng viên trong toàn bộ case...")
    # Khi bật AI thị giác, lấy 1 tập ứng viên RỘNG HƠN "Số ứng viên hiển thị"
    # MỖI VIDEO để gửi cho AI xem xét — tránh cắt mất ứng viên đúng chỉ vì
    # điểm so màu/ReID cục bộ (heuristic thô) xếp nó ngoài top-K nhỏ trước
    # khi AI kịp thấy (xem VLM_POOL_PER_VIDEO trong demo_search.py). Tính
    # theo TỪNG VIDEO (không phải tổng case) để mọi video được xét công bằng.
    search_top_k = max(int(top_k), VLM_POOL_PER_VIDEO) if use_vlm else int(top_k)
    candidates = search(case_id, DB_PATH, ref_features, top_k=search_top_k)

    vlm_note = ""
    if use_vlm and candidates:
        # Lọc bớt track gần như chắc chắn khác người trước khi gửi API — tiết
        # kiệm lệnh gọi cho track rõ ràng không liên quan (xem
        # filter_prescreen_for_vlm/VLM_PRESCREEN_FLOOR trong demo_search.py).
        candidates_for_vlm = filter_prescreen_for_vlm(candidates)
        progress(0.7, desc=f"Đang gửi {len(candidates_for_vlm)} ảnh crop tới ChatGPT Vision để tinh chỉnh (gửi ra ngoài mạng nội bộ)...")
        try:
            candidates = refine_with_vlm(ref_features, candidates_for_vlm)
            vlm_note = " Đã tinh chỉnh bằng AI thị giác (ChatGPT Vision)."
        except Exception as e:
            # Best-effort: lỗi API (hết quota, mạng, key sai...) không nên làm
            # sập cả giao diện — quay về kết quả so màu local và báo rõ lý do.
            vlm_note = f" ⚠️ Lỗi khi gọi AI thị giác, dùng kết quả so màu local: {e}"
        # Đã tinh chỉnh xong (hoặc lỗi, rơi về điểm local) — giờ mới cắt về
        # đúng số lượng người dùng muốn xem, THEO TỪNG VIDEO (điểm đã đổi sau
        # VLM nên phải nhóm lại chứ không dùng lại nhóm từ trước lúc gọi VLM).
        candidates = group_top_k_per_video(candidates, int(top_k))

    ref_desc = _describe(ref_features)
    n_used, n_total = ref_features.get("_n_images_used", 0), ref_features.get("_n_images_total", 0)
    used_note = f" (dùng {n_used}/{n_total} ảnh)" if n_used < n_total else ""
    ref_vlm_notes = ref_features.get("_vlm_notes")
    if ref_vlm_notes:
        used_note += f" · Mô tả bằng AI thị giác: {ref_vlm_notes[0]}"
    extended = ref_features.get("_extended")
    if extended:
        used_note += f" · Chi tiết khác: {vlm_compare.describe_extended_attrs_vi(extended)}"
    if ref_features.get("_build_note"):
        used_note += f" · Vóc dáng (chỉ tham khảo): {ref_features['_build_note']}"
    if ref_features.get("_gait_note"):
        used_note += f" · Dáng đi (chỉ tham khảo): {ref_features['_gait_note']}"

    # Toàn bộ video trong case — dùng để LIỆT KÊ ĐỦ mọi video ở phần "Ứng
    # viên phù hợp", kể cả video không có ứng viên nào (ghi rõ "Không có đối
    # tượng phù hợp" thay vì lược bỏ khỏi báo cáo — điều tra viên cần biết
    # camera nào ĐÃ được kiểm tra, không chỉ camera nào có kết quả).
    all_video_labels = [label for label, _ in _video_choices(DB_PATH, case_id)]

    if not candidates:
        status = f"Đặc điểm tham chiếu: {ref_desc}{used_note}. Không tìm thấy ứng viên nào."
        run_id = audit_log.record_search_run(DB_PATH, case_id, ref_image_paths, ref_desc, top_k, use_vlm, [])
        return None, build_candidates_html([], all_video_labels), status, gr.update(), "*Chưa có kết quả.*", gr.update(), run_id, None

    # Lọc theo ngưỡng tin cậy tối thiểu — hiển thị ứng viên điểm quá thấp
    # (vd chỉ tình cờ trùng màu áo/quần, ngoại hình thực tế khác hẳn) dễ
    # khiến điều tra viên tưởng nhầm là có manh mối, làm phức tạp hướng điều
    # tra. Báo rõ "không tìm thấy" thay vì âm thầm hiển thị kết quả yếu.
    best_score = max(c["score"] for c in candidates)
    candidates = [c for c in candidates if c["score"] >= MIN_CONFIDENT_SCORE]
    if not candidates:
        status = (
            f"Đặc điểm tham chiếu: {ref_desc}{used_note}. "
            f"Không tìm thấy đối tượng phù hợp — điểm khớp cao nhất chỉ đạt {best_score:.2f}, "
            f"quá thấp để tin cậy là cùng 1 người (ngưỡng {MIN_CONFIDENT_SCORE})."
        )
        run_id = audit_log.record_search_run(DB_PATH, case_id, ref_image_paths, ref_desc, top_k, use_vlm, [])
        return None, build_candidates_html([], all_video_labels), status, gr.update(), "*Chưa có kết quả.*", gr.update(), run_id, None

    candidates_html = build_candidates_html(candidates, all_video_labels)
    videos_summary = _describe_videos_with_matches(candidates)
    status = (
        f"Đặc điểm tham chiếu: {ref_desc}{used_note}.\n\n"
        f"**📹 Video có đối tượng xuất hiện ({videos_summary['n_videos']}):**\n{videos_summary['text']}\n\n"
        f"**Ứng viên phù hợp đủ tiêu chuẩn ({len(candidates)}, tối đa {int(top_k)} người/video):**{vlm_note}"
    )

    # Audit log (FR-15/16): ghi lại truy vấn NÀY (case, ảnh tham chiếu, tham
    # số) + TOÀN BỘ ứng viên đủ tiêu chuẩn kèm lý do xếp hạng — không chỉ
    # ứng viên #1 đang hiển thị mặc định, vì điều tra viên có thể bấm xem
    # ứng viên khác và cần feedback được gắn đúng vào lần chạy này.
    run_id = audit_log.record_search_run(DB_PATH, case_id, ref_image_paths, ref_desc, top_k, use_vlm, candidates)

    top1 = candidates[0]
    player_html = build_player_html(case_id, top1["video_id"], candidates, top1["track_id"])
    video_dropdown_update = gr.update(
        choices=_video_choices(DB_PATH, case_id), value=top1["video_id"]
    )
    evidence = build_evidence_panel(top1)

    progress(1.0, desc="Xong")
    return candidates, candidates_html, status, video_dropdown_update, evidence, player_html, run_id, top1


def on_gallery_click(idx, case_id, candidates):
    """Cầu nối JS -> Python cho việc bấm chọn 1 ứng viên trong
    build_candidates_html() — xem giải thích cơ chế ở đó. idx là giá trị số
    do JS ghi vào ô ẩn gallery_click_index."""
    if not candidates or idx is None:
        return gr.update(), "*Chưa có kết quả.*", gr.update(), gr.update()
    idx = int(idx)
    if idx < 0 or idx >= len(candidates):
        return gr.update(), "*Chưa có kết quả.*", gr.update(), gr.update()
    c = candidates[idx]
    player_html = build_player_html(case_id, c["video_id"], candidates, c["track_id"])
    evidence = build_evidence_panel(c)
    video_dropdown_update = gr.update(value=c["video_id"])
    # Cập nhật current_candidate_state để nút feedback (Đúng/Sai/Cần xem lại)
    # chấm đúng track đang xem — xem current_run_id_state/current_candidate_state.
    return video_dropdown_update, evidence, player_html, c


def on_feedback(feedback_value, run_id, candidate):
    """Ghi nhận đánh giá của điều tra viên cho ứng viên đang xem trong
    Evidence panel (FR-16 mở rộng — audit log không chỉ ghi HỆ THỐNG đề xuất
    gì mà cả CON NGƯỜI phản hồi thế nào, làm nền cho việc cải tiến sau này)."""
    if not run_id or not candidate:
        return "⚠️ Chưa có ứng viên nào đang được chọn để chấm feedback — hãy bấm vào 1 ảnh trong 'Ứng viên phù hợp' trước."
    audit_log.record_feedback(DB_PATH, run_id, candidate["track_id"], candidate["video_id"], feedback_value)
    label = audit_log.FEEDBACK_LABELS_VI[feedback_value]
    return f"✅ Đã ghi nhận: **{label}** cho track `{candidate['track_id'].split('_')[-1]}` (camera {candidate['video_label']})."


def _make_feedback_handler(feedback_value):
    def handler(run_id, candidate):
        return on_feedback(feedback_value, run_id, candidate)
    return handler


# ---------------------------------------------------------------------------
# Vị trí camera & lộ trình trên bản đồ — MODULE MỞ RỘNG (modules/geo_route.py)
#
# Tách hoàn toàn khỏi lược đồ DB cốt lõi (bảng riêng video_geo) — nếu tính
# năng này không khả thi, xoá phần callback + UI dưới đây và file
# modules/geo_route.py, không ảnh hưởng phần còn lại của app.
# ---------------------------------------------------------------------------

def on_geo_video_selected(case_id, video_id):
    """Nạp địa chỉ/giờ quay đã lưu (nếu có) cho video vừa chọn, hoặc gợi ý
    địa chỉ từ tên camera (theo quy ước 'tên_địa chỉ') nếu chưa từng thiết
    lập — điều tra viên vẫn nên kiểm tra lại địa chỉ trước khi lưu."""
    if not case_id or not video_id:
        return "", "", "⚠️ Chọn case và video trước."
    existing = geo_route.get_video_geo(DB_PATH, video_id)
    if existing:
        return (
            existing["address_label"] or "",
            geo_route.format_epoch(existing["recording_start_epoch"]),
            "Đã có dữ liệu đã lưu trước đó cho video này — có thể sửa rồi lưu lại.",
        )
    videos = list_videos_in_case(DB_PATH, case_id)
    label = next((_video_label(v) for v in videos if v["video_id"] == video_id), None)
    suggested = geo_route.suggest_address_from_label(label)
    return (
        suggested or "",
        "",
        "Video chưa có địa chỉ — " + (
            f"gợi ý từ tên camera: '{suggested}' (kiểm tra lại trước khi lưu)."
            if suggested else "chưa có gợi ý (tên camera không theo quy ước 'tên_địa chỉ')."
        ),
    )


def on_save_video_geo(video_id, address_label, start_time_text):
    """Lưu địa chỉ + giờ quay cho video — toạ độ được TÌM TỰ ĐỘNG từ địa chỉ
    qua Nominatim (OpenStreetMap, miễn phí). Độ phủ địa chỉ chi tiết (số nhà,
    tên dong) ở Hàn Quốc qua OSM còn hạn chế — nếu không tìm được, hãy thử
    địa chỉ tổng quát hơn (tên phường/quận, hoặc địa danh gần đó)."""
    if not video_id:
        return "⚠️ Chọn video trước."
    address_label = (address_label or "").strip()
    if not address_label:
        return "⚠️ Nhập địa chỉ trước (dùng để tự tìm toạ độ)."
    start_epoch = geo_route.parse_datetime_local(start_time_text)
    if start_time_text and start_time_text.strip() and start_epoch is None:
        return "⚠️ Giờ quay sai định dạng — dùng 'YYYY-MM-DD HH:MM:SS' (vd 2026-08-06 14:30:00)."
    coords = geo_route.geocode_address(address_label)
    if coords is None:
        return (
            f"⚠️ Không tìm được toạ độ cho địa chỉ '{address_label}'. "
            "Địa chỉ chi tiết (số nhà, tên dong) ở Hàn Quốc qua OpenStreetMap có thể chưa có dữ liệu — "
            "thử địa chỉ tổng quát hơn (tên phường/quận/thành phố) hoặc 1 địa danh gần đó."
        )
    lat, lng = coords
    geo_route.set_video_geo(
        DB_PATH, video_id, lat=lat, lng=lng,
        address_label=address_label, recording_start_epoch=start_epoch,
    )
    return f"✅ Đã lưu: {address_label} → toạ độ ({lat:.5f}, {lng:.5f})"


def on_show_route(case_id, candidates):
    if not case_id:
        return "<p style='color:#888'>Chọn case trước.</p>"
    if not candidates:
        return "<p style='color:#888'>Chưa có kết quả tìm kiếm — bấm 'Tìm kiếm' trước.</p>"
    geo_by_video = geo_route.get_case_geo(DB_PATH, case_id)
    points = geo_route.build_route(candidates, geo_by_video)
    n_skipped = len(candidates) - len(points)
    return geo_route.build_route_map_html(points, n_skipped_no_geo=n_skipped)


# ---------------------------------------------------------------------------
# Giao diện
# ---------------------------------------------------------------------------

with gr.Blocks(title="AI Investigation Assistant — Demo") as demo:
    candidates_state = gr.State([])
    # Audit log (FR-15..17): run_id của lần search gần nhất + ứng viên đang
    # xem trong Evidence panel — cần cả 2 để biết feedback (Đúng/Sai/Cần xem
    # lại) đang chấm cho ĐÚNG track nào của ĐÚNG lần chạy nào.
    current_run_id_state = gr.State(None)
    current_candidate_state = gr.State(None)
    # gr.Number(visible=False) KHÔNG mount DOM trong Gradio 6 (đã xác nhận
    # thực tế: querySelector không tìm thấy input) — nên ô cầu nối JS->Python
    # cho build_candidates_html() phải để visible=True rồi tự ẩn bằng CSS ở
    # đây thay vì dùng visible=False. Thẻ <style> vẫn được áp dụng khi chèn
    # qua innerHTML (khác <script> — xem giải thích ở modules/geo_route.py).
    gr.HTML(
        "<style>#aia_gallery_idx{position:fixed;left:-9999px;top:-9999px;opacity:0;pointer-events:none;}</style>"
    )

    gr.Markdown(
        "# AI Investigation Assistant — Demo\n"
        "Prototype minh hoạ Module 1 (ingest + track) + Module 2 (appearance). "
        "**Không phải kết luận danh tính** — chỉ là ứng viên có đặc điểm khớp, "
        "điều tra viên tự xem xét và quyết định.\n\n"
        "Đặc điểm dùng để so khớp: màu áo, màu quần, tay áo, mũ, kiểu tóc, giày. "
        "**Không có giới tính** — suy luận giới tính từ ảnh CCTV không đủ tin cậy để dùng làm bằng chứng."
    )

    with gr.Row():
        # ---------------- Cột trái: quản lý case ----------------
        with gr.Column(scale=1):
            gr.Markdown("## Vụ án (Case)")
            with gr.Row():
                case_dropdown = gr.Dropdown(choices=_case_choices(DB_PATH), label="Case đang làm việc", scale=4)
                refresh_cases_btn = gr.Button("🔄", scale=1, min_width=40)
            with gr.Row():
                new_case_name = gr.Textbox(label="Tên case mới", placeholder="Vd: Vụ mất trộm khu B - 03/08")
                create_case_btn = gr.Button("Tạo case")
            case_status = gr.Markdown("")

            gr.Markdown("### Thêm video vào case")
            video_files_input = gr.File(
                label="Video (có thể chọn nhiều — nhiều camera/nguồn). Tải lên xong sẽ TỰ ĐỘNG thêm vào case.",
                file_types=["video"], file_count="multiple", type="filepath",
            )
            camera_label_input = gr.Textbox(label="Nhãn camera (tuỳ chọn, để trống sẽ dùng tên file — đặt trước khi tải video lên nếu muốn dùng)")
            sample_fps_input = gr.Slider(1, 10, value=2, step=1, label="Tốc độ lấy mẫu (fps)")
            add_video_status = gr.Markdown("")

            with gr.Accordion("⚠️ Xoá dữ liệu case (không thể hoàn tác)", open=False):
                gr.Markdown(
                    "Case demo có thể còn video từ những lần test trước — xoá để "
                    "chắc chắn case đang chọn thật sự trống trước khi kiểm thử."
                )
                clear_confirm_input = gr.Checkbox(
                    value=False,
                    label="Tôi hiểu thao tác này xoá vĩnh viễn toàn bộ video, track và "
                    "đặc điểm đã trích xuất của case đang chọn — không thể hoàn tác.",
                )
                clear_videos_btn = gr.Button("🗑️ Xoá tất cả video trong case này", variant="stop")
                clear_status = gr.Markdown("")

            gr.Markdown("### Ảnh tham chiếu (người cần tìm)")
            ref_images_input = gr.File(
                label="Có thể chọn nhiều ảnh (nhiều góc/khoảnh khắc)",
                file_types=["image"], file_count="multiple", type="filepath",
            )
            top_k_input = gr.Slider(
                1, 20, value=5, step=1, label="Số ứng viên hiển thị MỖI VIDEO",
                info="Áp dụng riêng cho từng video/camera — video nào cũng được xét, không bị video khác chiếm hết chỗ.",
            )
            use_vlm_input = gr.Checkbox(
                value=False,
                label="🔍 Dùng AI thị giác (ChatGPT Vision)",
                info="⚠️ Gửi ảnh ra ngoài mạng nội bộ lên API của OpenAI. Bật sẽ: (1) AI mô tả trực tiếp đặc điểm ảnh tham chiếu thay cho thuật toán màu cục bộ (chính xác hơn khi ánh sáng ám màu hoặc tóc dài che vai); (2) AI so sánh lại top ứng viên sau khi tìm kiếm. Cần tự cấu hình OPENAI_API_KEY. Mặc định TẮT.",
            )
            search_btn = gr.Button("Tìm kiếm", variant="primary")
            search_status = gr.Markdown("")

        # ---------------- Cột phải: xem video + kết quả ----------------
        with gr.Column(scale=2):
            gr.Markdown("## Xem video")
            with gr.Row():
                with gr.Column(scale=2):
                    video_dropdown = gr.Dropdown(choices=[], label="Video đang xem")
                    player = gr.HTML(build_player_html("", "", [], None))
                with gr.Column(scale=1):
                    gr.Markdown("##### 📍 Vị trí & giờ quay (mở rộng, tuỳ chọn)")
                    gr.Markdown(
                        "Áp dụng cho video đang xem bên trái — cần cho mục "
                        "'🗺️ Lộ trình trên bản đồ' bên dưới. Toạ độ luôn cần tự xác nhận.",
                    )
                    geo_address_input = gr.Textbox(
                        label="Địa chỉ", placeholder="vd Yongin-si, Gyeonggi-do",
                        info="Toạ độ tự động tìm từ địa chỉ này (OpenStreetMap) khi bấm Lưu.",
                    )
                    geo_start_time_input = gr.Textbox(
                        label="Giờ bắt đầu quay thực", placeholder="YYYY-MM-DD HH:MM:SS"
                    )
                    geo_save_btn = gr.Button("Lưu vị trí & giờ quay", size="sm")
                    geo_status = gr.Markdown("")

            gr.Markdown("## Ứng viên phù hợp")
            gr.Markdown("*Nhóm theo video/camera — bấm vào 1 ảnh để xem trên video.*")
            gallery = gr.HTML("*Chưa có kết quả.*")
            gallery_click_index = gr.Number(value=-1, elem_id="aia_gallery_idx")

            gr.Markdown("## Chi tiết bằng chứng (Evidence)")
            evidence_panel = gr.Markdown("*Chọn 1 ứng viên trong danh sách bên trên để xem chi tiết.*")
            gr.Markdown("*Đánh giá của bạn cho ứng viên đang xem ở trên — ghi vào audit log, không sửa/xoá được:*")
            with gr.Row():
                feedback_correct_btn = gr.Button("✅ Đúng", size="sm")
                feedback_incorrect_btn = gr.Button("❌ Sai", size="sm")
                feedback_review_btn = gr.Button("⚠️ Cần xem lại", size="sm")
            feedback_status = gr.Markdown("")

            with gr.Accordion("🗺️ Lộ trình trên bản đồ (mở rộng, tuỳ chọn)", open=False):
                gr.Markdown(
                    "Nối các ứng viên đủ tiêu chuẩn theo GIỜ QUAY THỰC TẾ của từng camera — cần thiết "
                    "lập vị trí & giờ quay ở mục '📍' cạnh video bên trên trước. Chỉ là gợi ý thứ tự "
                    "khả dĩ dựa trên điểm khớp, **không phải kết luận lộ trình chắc chắn**."
                )
                show_route_btn = gr.Button("Xem lộ trình")
                route_map = gr.HTML("*Chưa xem lộ trình.*")

    # ------------- wiring -------------
    geo_field_outputs = [geo_address_input, geo_start_time_input, geo_status]

    create_case_btn.click(
        on_create_case, inputs=[new_case_name], outputs=[case_dropdown, new_case_name, case_status]
    )
    case_dropdown.change(
        on_case_selected, inputs=[case_dropdown], outputs=[video_dropdown, player] + geo_field_outputs
    )
    video_files_input.upload(
        on_add_videos,
        inputs=[case_dropdown, video_files_input, camera_label_input, sample_fps_input],
        outputs=[video_dropdown, add_video_status, case_dropdown, player] + geo_field_outputs,
    )
    video_dropdown.change(
        on_video_selected, inputs=[case_dropdown, video_dropdown, candidates_state], outputs=[player]
    )
    video_dropdown.change(
        on_geo_video_selected, inputs=[case_dropdown, video_dropdown], outputs=geo_field_outputs
    )
    search_btn.click(
        run_search,
        inputs=[case_dropdown, ref_images_input, top_k_input, use_vlm_input],
        outputs=[
            candidates_state, gallery, search_status, video_dropdown, evidence_panel, player,
            current_run_id_state, current_candidate_state,
        ],
    )
    clear_videos_btn.click(
        on_clear_case_videos,
        inputs=[case_dropdown, clear_confirm_input],
        outputs=[
            video_dropdown, case_dropdown, clear_status, player,
            candidates_state, gallery, search_status, evidence_panel, clear_confirm_input,
        ] + geo_field_outputs + [current_run_id_state, current_candidate_state],
    )
    gallery_click_index.change(
        on_gallery_click,
        inputs=[gallery_click_index, case_dropdown, candidates_state],
        outputs=[video_dropdown, evidence_panel, player, current_candidate_state],
    )
    refresh_cases_btn.click(on_refresh_cases, outputs=[case_dropdown])

    feedback_correct_btn.click(
        _make_feedback_handler("correct"),
        inputs=[current_run_id_state, current_candidate_state],
        outputs=[feedback_status],
    )
    feedback_incorrect_btn.click(
        _make_feedback_handler("incorrect"),
        inputs=[current_run_id_state, current_candidate_state],
        outputs=[feedback_status],
    )
    feedback_review_btn.click(
        _make_feedback_handler("needs_review"),
        inputs=[current_run_id_state, current_candidate_state],
        outputs=[feedback_status],
    )

    geo_save_btn.click(
        on_save_video_geo,
        inputs=[video_dropdown, geo_address_input, geo_start_time_input],
        outputs=[geo_status],
    )
    show_route_btn.click(
        on_show_route, inputs=[case_dropdown, candidates_state], outputs=[route_map]
    )

if __name__ == "__main__":
    demo.queue().launch(server_name="127.0.0.1", server_port=7860, allowed_paths=[OUTPUT_DIR])
