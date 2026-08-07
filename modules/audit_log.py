"""
Audit log — ghi lại truy vấn tìm kiếm và feedback của điều tra viên.

Khớp với FR-15..17 trong PRD_AI_Investigation_Assistant_v0.1.md (mục 8.6):
- FR-15: ghi log mọi truy vấn (case, tham số, thời gian).
- FR-16: ghi log kết quả của từng ứng viên cụ thể (điểm, lý do xếp hạng).
- FR-17: audit log không có đường sửa/xoá qua UI thường — module này chỉ
  cung cấp hàm INSERT, không có hàm update/delete nào cho 3 bảng audit.
  (Lưu ý: đây là ràng buộc ở tầng ứng dụng, chưa phải kiểm soát quyền truy
  cập DB thật — prototype hiện chưa có hệ thống tài khoản/phân quyền, xem
  README mục Giới hạn.)

Tách bảng riêng (search_runs / search_run_candidates / candidate_feedback)
thay vì bảng chung, để không đụng tới schema cốt lõi (cases/videos/tracks...)
— giống cách modules/geo_route.py tách bảng video_geo.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
import uuid

FEEDBACK_VALUES = ("correct", "incorrect", "needs_review")
FEEDBACK_LABELS_VI = {"correct": "Đúng", "incorrect": "Sai", "needs_review": "Cần xem lại"}


def init_audit_tables(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS search_runs (
            run_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            timestamp_epoch REAL NOT NULL,
            ref_image_paths TEXT NOT NULL,
            ref_description TEXT,
            top_k INTEGER NOT NULL,
            use_vlm INTEGER NOT NULL,
            n_candidates INTEGER NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS search_run_candidates (
            run_id TEXT NOT NULL,
            rank INTEGER NOT NULL,
            track_id TEXT NOT NULL,
            video_id TEXT NOT NULL,
            video_label TEXT,
            score REAL NOT NULL,
            explanation TEXT,
            PRIMARY KEY (run_id, track_id)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS candidate_feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            track_id TEXT NOT NULL,
            video_id TEXT,
            feedback TEXT NOT NULL CHECK (feedback IN ('correct','incorrect','needs_review')),
            timestamp_epoch REAL NOT NULL,
            note TEXT
        )"""
    )
    conn.commit()
    conn.close()


def record_search_run(
    db_path: str,
    case_id: str,
    ref_image_paths: list[str],
    ref_description: str,
    top_k: int,
    use_vlm: bool,
    candidates: list[dict],
) -> str:
    """Ghi 1 lần chạy search + toàn bộ ứng viên trả về (kể cả khi rỗng — 1 lần
    tìm không ra kết quả vẫn là 1 truy vấn cần truy vết theo FR-15)."""
    init_audit_tables(db_path)
    run_id = uuid.uuid4().hex
    now = time.time()
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO search_runs
           (run_id, case_id, timestamp_epoch, ref_image_paths, ref_description,
            top_k, use_vlm, n_candidates)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, case_id, now, json.dumps(ref_image_paths, ensure_ascii=False),
         ref_description, int(top_k), int(bool(use_vlm)), len(candidates)),
    )
    for rank, c in enumerate(candidates, start=1):
        conn.execute(
            """INSERT INTO search_run_candidates
               (run_id, rank, track_id, video_id, video_label, score, explanation)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (run_id, rank, c["track_id"], c["video_id"], c.get("video_label"),
             c["score"], json.dumps(c.get("explanation", []), ensure_ascii=False)),
        )
    conn.commit()
    conn.close()
    return run_id


def record_feedback(db_path: str, run_id: str, track_id: str, video_id: str | None,
                     feedback: str, note: str = "") -> int:
    if feedback not in FEEDBACK_VALUES:
        raise ValueError(f"feedback phải là 1 trong {FEEDBACK_VALUES}, nhận '{feedback}'")
    init_audit_tables(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        """INSERT INTO candidate_feedback (run_id, track_id, video_id, feedback, timestamp_epoch, note)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (run_id, track_id, video_id, feedback, time.time(), note),
    )
    feedback_id = cur.lastrowid
    conn.commit()
    conn.close()
    return feedback_id


def get_feedback_for_candidate(db_path: str, run_id: str, track_id: str) -> list[dict]:
    """Lịch sử feedback (có thể chấm nhiều lần) cho 1 ứng viên trong 1 lần
    chạy search cụ thể — mới nhất trước."""
    init_audit_tables(db_path)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT feedback, timestamp_epoch, note FROM candidate_feedback
           WHERE run_id = ? AND track_id = ? ORDER BY timestamp_epoch DESC""",
        (run_id, track_id),
    ).fetchall()
    conn.close()
    return [{"feedback": r[0], "timestamp_epoch": r[1], "note": r[2]} for r in rows]


def list_recent_runs(db_path: str, case_id: str | None = None, limit: int = 20) -> list[dict]:
    init_audit_tables(db_path)
    conn = sqlite3.connect(db_path)
    if case_id:
        rows = conn.execute(
            """SELECT run_id, case_id, timestamp_epoch, ref_description, top_k, use_vlm, n_candidates
               FROM search_runs WHERE case_id = ? ORDER BY timestamp_epoch DESC LIMIT ?""",
            (case_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT run_id, case_id, timestamp_epoch, ref_description, top_k, use_vlm, n_candidates
               FROM search_runs ORDER BY timestamp_epoch DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    conn.close()
    return [
        {
            "run_id": r[0], "case_id": r[1], "timestamp_epoch": r[2], "ref_description": r[3],
            "top_k": r[4], "use_vlm": bool(r[5]), "n_candidates": r[6],
        }
        for r in rows
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Xem nhanh audit log đã ghi.")
    parser.add_argument("--db-path", default="case.db")
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    init_audit_tables(args.db_path)
    runs = list_recent_runs(args.db_path, case_id=args.case_id, limit=args.limit)
    if not runs:
        print("Chưa có lần chạy search nào được ghi log.")
        return
    for r in runs:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["timestamp_epoch"]))
        vlm = "có" if r["use_vlm"] else "không"
        print(f"[{ts}] case={r['case_id']} run={r['run_id'][:8]} "
              f"top_k={r['top_k']} vlm={vlm} n_candidates={r['n_candidates']} "
              f"ref='{r['ref_description']}'")


if __name__ == "__main__":
    main()
