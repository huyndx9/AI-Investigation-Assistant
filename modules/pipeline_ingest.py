"""
Module 1 — Video ingest pipeline.

Phạm vi (theo PRD Phase 1 MVP):
- FR-03: nhập video từ file cục bộ.
- FR-04: giải mã, trích keyframe theo nhịp lấy mẫu cố định — không chạy model
  AI trên từng frame liên tục để tối ưu tài nguyên.
- FR-05: phát hiện người (person detection) và theo dõi (tracking) trong
  phạm vi MỘT camera — track_id không được merge giữa các video khác nhau.

Ranh giới: module này chỉ trích xuất bbox + crop ảnh + track_id thô. Không
tính đặc điểm ngoại hình/hình thể (thuộc modules/appearance.py,
modules/pose.py, modules/body_build.py) và không so sánh/xếp hạng ứng viên.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Dùng model segmentation (không phải detection thường) — ngoài bbox, model
# này trả về đường viền (polygon) chính xác theo hình người. Lý do: khi 2
# người đứng/đi gần nhau, bbox của họ chồng lấn rất nhiều dù người thật
# không chồng — viền chính xác giúp phân biệt rõ ràng bằng mắt (xem
# modules/visualize_tracks.py) và cho crop sạch hơn (ít dính nền/người khác)
# để các module trích đặc điểm ngoại hình sau này dùng.
#
# Lưu ý: việc này KHÔNG tự sửa lỗi track_id bị gán nhầm giữa hai người theo
# THỜI GIAN (đã sửa bằng track_buffer, xem tracker_configs/). Thuật toán ghép
# track hiện tại vẫn dùng IOU theo bbox, không dùng mask — muốn mask thực sự
# tham gia vào việc ghép track cần sửa sâu hơn vào tracker, chưa làm ở đây.
DEFAULT_DETECTOR_MODEL = "yolov8n-seg.pt"
DEFAULT_TRACKER_CONFIG = str(Path(__file__).parent / "tracker_configs" / "bytetrack_conservative.yaml")
PERSON_CLASS_ID = 0  # COCO class id cho "person"
DEFAULT_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                owner TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                source_path TEXT NOT NULL,
                camera_label TEXT,
                fps REAL,
                frame_width INTEGER,
                frame_height INTEGER,
                total_frames INTEGER,
                added_at TEXT NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases(case_id)
            );

            CREATE TABLE IF NOT EXISTS tracks (
                track_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                video_id TEXT NOT NULL,
                local_track_index INTEGER NOT NULL,
                first_frame INTEGER NOT NULL,
                last_frame INTEGER NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases(case_id),
                FOREIGN KEY (video_id) REFERENCES videos(video_id)
            );

            CREATE TABLE IF NOT EXISTS track_crops (
                crop_id TEXT PRIMARY KEY,
                track_id TEXT NOT NULL,
                frame_number INTEGER NOT NULL,
                timestamp_sec REAL NOT NULL,
                crop_path TEXT NOT NULL,
                bbox_x INTEGER NOT NULL,
                bbox_y INTEGER NOT NULL,
                bbox_w INTEGER NOT NULL,
                bbox_h INTEGER NOT NULL,
                detection_confidence REAL NOT NULL,
                mask_polygon TEXT,
                FOREIGN KEY (track_id) REFERENCES tracks(track_id)
            );
            """
        )
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(track_crops)")}
        if "mask_polygon" not in existing_cols:
            conn.execute("ALTER TABLE track_crops ADD COLUMN mask_polygon TEXT")
        conn.commit()
    finally:
        conn.close()


def ensure_case(db_path: str, case_id: str, name: str | None = None, owner: str | None = None) -> None:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT case_id FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO cases (case_id, name, description, owner, created_at) VALUES (?, ?, ?, ?, ?)",
                (case_id, name or case_id, None, owner, _now_iso()),
            )
            conn.commit()
    finally:
        conn.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Kết quả ingest
# ---------------------------------------------------------------------------

@dataclass
class IngestResult:
    case_id: str
    video_id: str
    source_path: str
    total_frames: int
    keyframes_processed: int
    tracks_found: int
    crops_saved: int
    track_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def _keyframe_stride(fps: float, sample_fps: float) -> int:
    """Số frame bỏ qua giữa hai keyframe liên tiếp.

    Không chạy model detection/tracking trên mọi frame — chỉ lấy mẫu theo
    sample_fps để tối ưu tài nguyên (FR-04).

    Đã kiểm chứng trên video mẫu (vtest.avi, fps gốc=10): xử lý đủ khung hình
    cho 38 track, lấy mẫu 5 fps cho 66 track, lấy mẫu 2 fps cho 59 track —
    lấy mẫu thưa hơn dẫn tới ByteTrack dễ mất liên tục (khoảng cách giữa 2
    keyframe vượt quá khả năng dự đoán của Kalman filter, một người bị che
    khuất tạm thời dễ bị tạo thành track mới thay vì nối track cũ), nhưng
    quan hệ không tuyến tính tuyệt đối — số liệu cụ thể phụ thuộc cảnh quay.
    Nếu ưu tiên độ ổn định track_id hơn tốc độ xử lý, tăng sample_fps gần
    bằng fps gốc của video; nếu ưu tiên tài nguyên, chấp nhận nhiều track bị
    phân mảnh hơn (module Evidence Fusion sau này cần xử lý việc một người
    thật có thể có nhiều track_id).
    """
    if fps <= 0:
        fps = 25.0
    return max(1, round(fps / sample_fps))


def ingest_video(
    case_id: str,
    video_path: str,
    output_dir: str = "output",
    db_path: str = "case.db",
    case_name: str | None = None,
    camera_label: str | None = None,
    sample_fps: float = 5.0,
    detector_model: str = DEFAULT_DETECTOR_MODEL,
    conf_threshold: float = 0.4,
    device: str = DEFAULT_DEVICE,
) -> IngestResult:
    video_path = str(Path(video_path))
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Không tìm thấy video: {video_path}")

    init_db(db_path)
    ensure_case(db_path, case_id, name=case_name)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Không giải mã được video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    stride = _keyframe_stride(fps, sample_fps)

    video_id = str(uuid.uuid4())
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO videos
           (video_id, case_id, source_path, camera_label, fps, frame_width, frame_height, total_frames, added_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (video_id, case_id, video_path, camera_label, fps, frame_width, frame_height, total_frames, _now_iso()),
    )
    conn.commit()

    crops_dir_base = Path(output_dir) / case_id / "crops"
    model = YOLO(detector_model)

    keyframes_processed = 0
    crops_saved = 0
    seen_local_track_ids: set[int] = set()
    track_frame_range: dict[int, list[int]] = {}
    global_track_id_of: dict[int, str] = {}

    frame_number = -1
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_number += 1

        if frame_number % stride != 0:
            continue
        keyframes_processed += 1
        timestamp_sec = frame_number / fps if fps > 0 else 0.0

        results = model.track(
            frame,
            persist=True,
            classes=[PERSON_CLASS_ID],
            tracker=DEFAULT_TRACKER_CONFIG,
            conf=conf_threshold,
            device=device,
            verbose=False,
        )
        result = results[0]
        if result.boxes is None or result.boxes.id is None:
            continue

        boxes_xyxy = result.boxes.xyxy.cpu().numpy()
        confs = result.boxes.conf.cpu().numpy()
        local_ids = result.boxes.id.int().cpu().numpy()
        # result.masks.xy: 1 polygon (mảng điểm x,y theo toạ độ ảnh gốc) cho
        # mỗi detection, cùng thứ tự với result.boxes — có thể None nếu dùng
        # model detection thường (không phải -seg) hoặc không phát hiện được
        # viền cho một số box.
        polygons = result.masks.xy if result.masks is not None else None

        for i, ((x1, y1, x2, y2), conf, local_id) in enumerate(zip(boxes_xyxy, confs, local_ids)):
            local_id = int(local_id)
            x1i, y1i, x2i, y2i = max(0, int(x1)), max(0, int(y1)), int(x2), int(y2)
            crop = frame[y1i:y2i, x1i:x2i]
            if crop.size == 0:
                continue

            mask_polygon_json = None
            if polygons is not None and i < len(polygons) and len(polygons[i]) >= 3:
                mask_polygon_json = json.dumps(np.round(polygons[i]).astype(int).tolist())

            if local_id not in global_track_id_of:
                global_track_id_of[local_id] = f"{video_id}_t{local_id}"
                track_frame_range[local_id] = [frame_number, frame_number]
                seen_local_track_ids.add(local_id)
            else:
                track_frame_range[local_id][1] = frame_number

            track_id = global_track_id_of[local_id]
            crop_dir = crops_dir_base / track_id
            crop_dir.mkdir(parents=True, exist_ok=True)
            crop_path = str(crop_dir / f"frame_{frame_number:08d}.jpg")
            cv2.imwrite(crop_path, crop)

            conn.execute(
                """INSERT INTO track_crops
                   (crop_id, track_id, frame_number, timestamp_sec, crop_path,
                    bbox_x, bbox_y, bbox_w, bbox_h, detection_confidence, mask_polygon)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()), track_id, frame_number, timestamp_sec, crop_path,
                    x1i, y1i, x2i - x1i, y2i - y1i, float(conf), mask_polygon_json,
                ),
            )
            crops_saved += 1

    cap.release()

    for local_id, (first_frame, last_frame) in track_frame_range.items():
        track_id = global_track_id_of[local_id]
        conn.execute(
            """INSERT INTO tracks
               (track_id, case_id, video_id, local_track_index, first_frame, last_frame)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (track_id, case_id, video_id, local_id, first_frame, last_frame),
        )
    conn.commit()
    conn.close()

    return IngestResult(
        case_id=case_id,
        video_id=video_id,
        source_path=video_path,
        total_frames=total_frames,
        keyframes_processed=keyframes_processed,
        tracks_found=len(seen_local_track_ids),
        crops_saved=crops_saved,
        track_ids=[global_track_id_of[i] for i in seen_local_track_ids],
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Module 1 — ingest video vào case, detect + track người.")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--case-name", default=None)
    parser.add_argument("--video", required=True, help="Đường dẫn video cục bộ")
    parser.add_argument("--camera-label", default=None)
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--db-path", default="case.db")
    parser.add_argument("--sample-fps", type=float, default=5.0)
    parser.add_argument("--conf", type=float, default=0.4)
    parser.add_argument("--model", default=DEFAULT_DETECTOR_MODEL)
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    args = parser.parse_args()

    result = ingest_video(
        case_id=args.case_id,
        video_path=args.video,
        output_dir=args.output_dir,
        db_path=args.db_path,
        case_name=args.case_name,
        camera_label=args.camera_label,
        sample_fps=args.sample_fps,
        detector_model=args.model,
        conf_threshold=args.conf,
        device=args.device,
    )

    print(f"Case: {result.case_id}")
    print(f"Video ID: {result.video_id}")
    print(f"Tổng số frame: {result.total_frames}")
    print(f"Keyframe đã xử lý: {result.keyframes_processed}")
    print(f"Số track phát hiện được: {result.tracks_found}")
    print(f"Số crop đã lưu: {result.crops_saved}")


if __name__ == "__main__":
    main()
