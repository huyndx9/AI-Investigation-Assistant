"""
Module MỞ RỘNG (tuỳ chọn) — dựng lộ trình đối tượng trên bản đồ dựa vào vị
trí camera (toạ độ) + giờ quay thực tế của video + kết quả tìm kiếm đã có.

THIẾT KẾ ĐỂ DỄ GỠ BỎ nếu không khả thi: dùng 1 bảng DB RIÊNG (video_geo),
KHÔNG đụng tới bảng "videos" hay bất kỳ bảng cốt lõi nào của
modules/pipeline_ingest.py / modules/demo_search.py. Muốn gỡ tính năng này
chỉ cần: xoá bảng video_geo, bỏ phần UI liên quan trong app.py, xoá file
này — phần còn lại của hệ thống không bị ảnh hưởng.

Vị trí camera lấy bằng cách NHẬP TAY (toạ độ lat/lng) — không tự động
geocode địa chỉ chữ qua API ngoài (tránh thêm 1 phụ thuộc trả phí + rủi ro
địa chỉ sai/mơ hồ dẫn tới toạ độ sai). suggest_address_from_label() chỉ GỢI
Ý phần chữ sau dấu "_" trong tên camera để điền sẵn ô địa chỉ, điều tra viên
vẫn phải tự xác nhận toạ độ thật.

Nguyên tắc Explainable AI / Human in the Loop: mỗi điểm trên bản đồ luôn đi
kèm điểm khớp (score) từ kết quả tìm kiếm — KHÔNG vẽ như một kết luận chắc
chắn, chỉ là gợi ý thứ tự khả dĩ để điều tra viên tự đánh giá. Video chưa
được thiết lập toạ độ + giờ quay sẽ bị bỏ qua khi dựng lộ trình (không đoán
bừa vị trí).
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import i18n  # noqa: E402


def init_geo_table(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS video_geo (
                video_id TEXT PRIMARY KEY,
                address_label TEXT,
                lat REAL,
                lng REAL,
                recording_start_epoch REAL
            )"""
        )
        conn.commit()
    finally:
        conn.close()


def suggest_address_from_label(text: str | None) -> str | None:
    """Gợi ý địa chỉ theo quy ước 'tên camera_địa chỉ' — CHỈ LÀ GỢI Ý ĐIỀN
    SẴN, không tự geocode. Trả về None nếu không có dấu '_' hoặc phần sau
    rỗng, để không điền nhầm khi tên không theo quy ước này."""
    if not text or "_" not in text:
        return None
    address = text.split("_", 1)[1].strip()
    return address or None


def parse_datetime_local(text: str | None) -> float | None:
    """Chuyển chuỗi giờ quay (định dạng 'YYYY-MM-DD HH:MM:SS' hoặc
    'YYYY-MM-DD HH:MM') người dùng nhập thành epoch giây. Trả về None nếu
    rỗng hoặc sai định dạng (không đoán bừa)."""
    if not text or not text.strip():
        return None
    text = text.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt).timestamp()
        except ValueError:
            continue
    return None


def geocode_address(address: str) -> tuple[float, float] | None:
    """Geocode địa chỉ chữ -> (lat, lng) qua Nominatim (OpenStreetMap) — MIỄN
    PHÍ, không cần API key/tài khoản, tránh thêm 1 phụ thuộc trả phí. Độ phủ
    Hàn Quốc qua OSM ở mức chấp nhận được cho địa chỉ theo tên đường/khu vực,
    có thể không chính xác bằng geocoder chính thức (VWorld/Kakao) cho địa
    chỉ chi tiết — nếu cần độ chính xác cao hơn, người dùng vẫn có thể tinh
    chỉnh trực tiếp trong bảng video_geo (sqlite3 case.db).

    Trả về None nếu không tìm thấy hoặc lỗi mạng — không chặn việc lưu địa
    chỉ, chỉ là chưa có toạ độ cho tới khi geocode thành công."""
    import json
    import urllib.parse
    import urllib.request

    if not address or not address.strip():
        return None
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": address.strip(), "format": "json", "limit": 1}
    )
    req = urllib.request.Request(url, headers={"User-Agent": "AI-Investigation-Assistant/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    if not data:
        return None
    try:
        return float(data[0]["lat"]), float(data[0]["lon"])
    except (KeyError, ValueError, TypeError):
        return None


def format_epoch(epoch: float | None) -> str:
    if epoch is None:
        return ""
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")


def set_video_geo(
    db_path: str, video_id: str,
    lat: float | None, lng: float | None,
    address_label: str | None, recording_start_epoch: float | None,
) -> None:
    init_geo_table(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO video_geo (video_id, address_label, lat, lng, recording_start_epoch)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(video_id) DO UPDATE SET
               address_label = excluded.address_label,
               lat = excluded.lat,
               lng = excluded.lng,
               recording_start_epoch = excluded.recording_start_epoch""",
        (video_id, address_label, lat, lng, recording_start_epoch),
    )
    conn.commit()
    conn.close()


def get_video_geo(db_path: str, video_id: str) -> dict | None:
    init_geo_table(db_path)
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT address_label, lat, lng, recording_start_epoch FROM video_geo WHERE video_id = ?",
        (video_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {"address_label": row[0], "lat": row[1], "lng": row[2], "recording_start_epoch": row[3]}


def get_case_geo(db_path: str, case_id: str) -> dict[str, dict]:
    """video_id -> thông tin toạ độ, chỉ những video trong case ĐÃ có đủ
    lat/lng (video chưa thiết lập sẽ không xuất hiện trong kết quả)."""
    init_geo_table(db_path)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT g.video_id, g.address_label, g.lat, g.lng, g.recording_start_epoch
           FROM video_geo g JOIN videos v ON v.video_id = g.video_id
           WHERE v.case_id = ? AND g.lat IS NOT NULL AND g.lng IS NOT NULL""",
        (case_id,),
    ).fetchall()
    conn.close()
    return {
        r[0]: {"address_label": r[1], "lat": r[2], "lng": r[3], "recording_start_epoch": r[4]}
        for r in rows
    }


# ---------------------------------------------------------------------------
# Dựng lộ trình từ kết quả tìm kiếm đã có (app.run_search()) + toạ độ camera
# ---------------------------------------------------------------------------

def build_route(candidates: list[dict], geo_by_video: dict[str, dict]) -> list[dict]:
    """Ghép ứng viên (kết quả tìm kiếm — đã lọc đủ tiêu chuẩn) với toạ độ +
    giờ quay thực của camera đó, tính giờ tuyệt đối, sắp theo thời gian.
    Video CHƯA thiết lập toạ độ/giờ quay bị bỏ qua — không đoán bừa vị trí
    hay thứ tự thời gian.

    MỖI CAMERA CHỈ 1 ĐIỂM trên bản đồ — 1 camera là 1 vị trí thật, không
    phải "1 lần khớp = 1 điểm" (1 camera có thể có nhiều track khớp cùng 1
    lần đối tượng đi qua, do thuật toán theo dõi tách track). Trong các
    track khớp tại cùng 1 camera, giữ lại track có ĐIỂM KHỚP CAO NHẤT làm
    đại diện — thời gian dùng để sắp xếp là thời gian của track đại diện đó;
    số track khớp khác tại camera này được ghi lại (n_sightings) để hiển thị
    trong popup, không bị mất thông tin."""
    from collections import defaultdict

    grouped: dict[str, list[dict]] = defaultdict(list)
    for c in candidates:
        geo = geo_by_video.get(c["video_id"])
        if not geo or geo.get("recording_start_epoch") is None:
            continue
        abs_time = geo["recording_start_epoch"] + c["first_seen_sec"]
        grouped[c["video_id"]].append({
            "video_label": c["video_label"],
            "address_label": geo.get("address_label") or c["video_label"],
            "lat": geo["lat"],
            "lng": geo["lng"],
            "abs_time": abs_time,
            "abs_time_str": format_epoch(abs_time),
            "score": c["score"],
            "track_id": c["track_id"],
        })

    points = []
    for items in grouped.values():
        best = max(items, key=lambda p: p["score"])
        best = dict(best)
        best["n_sightings"] = len(items)
        points.append(best)
    points.sort(key=lambda p: p["abs_time"])
    return points


def _spread_overlapping_points(points: list[dict]) -> list[dict]:
    """Toạ độ trùng nhau (thường do geocode địa chỉ chi tiết ở Hàn Quốc qua
    OpenStreetMap không giải mã được số nhà cụ thể, rơi về cùng 1 điểm trung
    tâm khu vực — xem describe ở build_route_map_html) sẽ chồng khít lên
    nhau trên bản đồ, nhìn như chỉ có 1 điểm dù thực ra có nhiều. Tách nhẹ
    (bán kính ~25m, KHÔNG đổi toạ độ gốc dùng để hiển thị trong popup) theo
    hình tròn quanh vị trí gốc để mắt thường thấy rõ có nhiều điểm — đây là
    kỹ thuật hiển thị bản đồ tiêu chuẩn (marker spiderfy), không phải suy
    đoán vị trí thật khác đi."""
    import math
    from collections import defaultdict

    groups: dict[tuple[float, float], list[int]] = defaultdict(list)
    for i, p in enumerate(points):
        groups[(round(p["lat"], 5), round(p["lng"], 5))].append(i)

    result = [dict(p) for p in points]
    OFFSET_DEG = 0.00025  # ~25-28m ở vĩ độ Hàn Quốc — đủ tách mắt nhìn, không lệch xa
    for indices in groups.values():
        if len(indices) < 2:
            continue
        n = len(indices)
        for k, idx in enumerate(indices):
            angle = 2 * math.pi * k / n
            result[idx]["display_lat"] = points[idx]["lat"] + OFFSET_DEG * math.cos(angle)
            result[idx]["display_lng"] = points[idx]["lng"] + OFFSET_DEG * math.sin(angle)
            result[idx]["overlap_count"] = n
    for p in result:
        p.setdefault("display_lat", p["lat"])
        p.setdefault("display_lng", p["lng"])
        p.setdefault("overlap_count", 1)
    return result


def _score_color(score: float) -> str:
    if score >= 0.7:
        return "#4caf50"  # xanh lá — tin cậy cao
    if score >= 0.55:
        return "#ffc107"  # vàng — trung bình
    return "#ff9800"  # cam — thấp, gần ngưỡng tối thiểu


def build_route_map_html(
    points: list[dict], n_skipped_no_geo: int = 0, height: int = 440, lang: str = i18n.DEFAULT_LANGUAGE,
) -> str:
    """HTML nhúng Leaflet.js + OpenStreetMap (miễn phí, không cần API key)
    vẽ các điểm camera theo thứ tự thời gian tuyệt đối, tô màu marker theo
    điểm khớp thay vì vẽ 1 đường nối như kết luận chắc chắn — mỗi điểm chỉ
    là 1 ứng viên có độ tin cậy riêng, điều tra viên tự đánh giá.
    """
    if not points:
        note = ""
        if n_skipped_no_geo:
            note = f"<p style='color:#f39c12'>{i18n.t('route_map_skipped_note_template', lang).format(n=n_skipped_no_geo)}</p>"
        return f"<p style='color:#888'>{i18n.t('route_map_no_data', lang)}</p>{note}"

    import base64
    import json

    spread = _spread_overlapping_points(points)

    markers_js = json.dumps([
        {
            "lat": p["display_lat"], "lng": p["display_lng"], "color": _score_color(p["score"]),
            "order": i + 1,
            # Đặt color trực tiếp lên TỪNG thẻ (không chỉ div bọc ngoài) và
            # thêm !important — CSS theme tối của Gradio (trang chủ ứng
            # dụng) có luật chọn (selector) áp trực tiếp lên <b>/<i> với độ
            # ưu tiên cao hơn kế thừa từ div cha, đã quan sát thực tế dòng
            # tiêu đề in đậm vẫn sáng màu dù div ngoài đã set color.
            "popup": (
                '<div style="color:#111 !important;font-size:13px;line-height:1.6;">'
                f"<b style=\"color:#111 !important;\">#{i+1} {p['address_label']}</b><br>"
                f"<span style=\"color:#111 !important;\">{i18n.t('route_map_popup_camera', lang)} {p['video_label']}<br>"
                f"{i18n.t('route_map_popup_time', lang)} {p['abs_time_str']}<br>"
                f"{i18n.t('route_map_popup_score', lang)} {p['score']:.2f}"
                + (f"<br>{i18n.t('route_map_popup_sightings_template', lang).format(n=p['n_sightings'])}"
                   if p.get("n_sightings", 1) > 1 else "")
                + "</span>"
                + (
                    "<br><i style=\"color:#b45309 !important;\">"
                    f"⚠️ {i18n.t('route_map_popup_overlap_template', lang).format(n=p['overlap_count'])}</i>"
                    if p["overlap_count"] > 1 else ""
                )
                + "</div>"
            ),
        }
        for i, p in enumerate(spread)
    ])
    line_js = json.dumps([[p["lat"], p["lng"]] for p in points])
    center_lat = sum(p["lat"] for p in points) / len(points)
    center_lng = sum(p["lng"] for p in points) / len(points)

    skipped_note = (
        f"<div style='font-size:12px;color:#f39c12;margin-bottom:6px;'>"
        f"{i18n.t('route_map_skipped_note_short_template', lang).format(n=n_skipped_no_geo)}</div>"
        if n_skipped_no_geo else ""
    )

    map_id = "aia_route_map"

    # QUAN TRỌNG: Gradio render gr.HTML bằng cách gán qua innerHTML — thẻ
    # <script> chèn theo cách này KHÔNG tự chạy (hành vi chuẩn của trình
    # duyệt, đã xác nhận thực tế: window.L luôn undefined dù thẻ <script>
    # vẫn xuất hiện trong DOM). Dùng thủ thuật <img src="data:," onerror=...>
    # làm điểm vào JS (thuộc tính onerror/onload VẪN chạy khi chèn qua
    # innerHTML, khác với <script>) — từ đó tự tạo thẻ <script> bằng
    # document.createElement() (script tạo bằng DOM API thì chạy bình
    # thường). Mã JS được base64 hoá để tránh mọi rắc rối escape dấu
    # ngoặc kép/đơn khi nhúng vào thuộc tính HTML.
    js_code = f"""(function() {{
      var mapId = "{map_id}";
      var markers = {markers_js};
      var line = {line_js};
      var centerLat = {center_lat}, centerLng = {center_lng};
      function initMap() {{
        var el = document.getElementById(mapId);
        if (!el || el._aia_map_done) return;
        el._aia_map_done = true;
        var map = L.map(el).setView([centerLat, centerLng], 15);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
          attribution: '&copy; OpenStreetMap contributors', maxZoom: 19,
        }}).addTo(map);
        markers.forEach(function(m) {{
          var icon = L.divIcon({{
            html: '<div style="background:' + m.color + ';color:#fff;width:26px;height:26px;' +
              'border-radius:50%;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.5);' +
              'display:flex;align-items:center;justify-content:center;font-weight:bold;' +
              'font-size:12px;font-family:sans-serif;">' + m.order + '</div>',
            className: '', iconSize: [26, 26], iconAnchor: [13, 13],
          }});
          L.marker([m.lat, m.lng], {{icon: icon}}).addTo(map).bindPopup(m.popup);
        }});
        if (line.length > 1) {{
          L.polyline(line, {{color: '#888', weight: 2, dashArray: '6,6'}}).addTo(map);
        }}
        map.fitBounds(L.latLngBounds(line), {{padding: [40, 40]}});
      }}
      if (window.L) {{ initMap(); return; }}
      var link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      document.head.appendChild(link);
      var script = document.createElement('script');
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      script.onload = initMap;
      document.head.appendChild(script);
    }})();"""
    js_b64 = base64.b64encode(js_code.encode("utf-8")).decode("ascii")

    return f"""
    <div style="font-family:sans-serif;">
      {skipped_note}
      <div style="font-size:12px;color:#aaa;margin-bottom:6px;">
        {i18n.t("route_map_legend", lang)}
      </div>
      <div id="{map_id}" style="height:{height}px;border-radius:6px;"></div>
      <img src="data:," alt="" style="display:none" onerror="eval(atob('{js_b64}'))" />
    </div>
    """
