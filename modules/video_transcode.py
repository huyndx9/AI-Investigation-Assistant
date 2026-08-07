"""
Chuyển mã video sang định dạng phát được trên trình duyệt (H.264/mp4).

Video CCTV gốc (.avi, codec cũ) không phát được bằng thẻ <video> HTML — cần
1 bản sao riêng cho mục đích XEM. Video gốc dùng để xử lý AI (pipeline_ingest,
appearance...) KHÔNG BAO GIỜ bị sửa hay ghi đè — hàm ở đây luôn ghi ra file
mới, không đụng tới nguồn.

Dùng ffmpeg thật (không giới hạn qua API wrapper) qua subprocess, lấy binary
tĩnh từ gói imageio-ffmpeg (không cần cài ffmpeg hệ thống thủ công trên máy
Windows này). Gọi thẳng ffmpeg CLI để sau này mở rộng dễ dàng sang thumbnail,
cắt clip, HLS... mà không bị giới hạn bởi một API Python hẹp.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()


def transcode_for_web(source_path: str, output_path: str, crf: int = 28) -> str:
    """Chuyển 1 video sang H.264/mp4, yuv420p (tương thích trình duyệt rộng
    nhất), +faststart (phát được khi chưa tải xong toàn bộ file).

    crf thấp hơn = chất lượng cao hơn, file to hơn. 28 là mức cân bằng hợp lý
    cho video giám sát (không cần chất lượng phát hành, chỉ cần xem rõ).
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG_BIN, "-y", "-i", source_path,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg transcode thất bại ({source_path}):\n{result.stderr[-2000:]}")
    return output_path


def extract_thumbnail(source_path: str, time_sec: float, output_path: str) -> str:
    """Trích 1 khung hình tại thời điểm time_sec làm ảnh thumbnail (jpg)."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG_BIN, "-y", "-ss", str(max(0.0, time_sec)), "-i", source_path,
        "-frames:v", "1", "-q:v", "3",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg trích thumbnail thất bại ({source_path}):\n{result.stderr[-2000:]}")
    return output_path


def ensure_web_video(source_path: str, cache_path: str) -> str:
    """Trả về đường dẫn bản mp4 phát-được-trên-trình-duyệt, tái dùng nếu đã
    chuyển mã trước đó (theo cache_path) thay vì làm lại mỗi lần."""
    if Path(cache_path).is_file():
        return cache_path
    return transcode_for_web(source_path, cache_path)
