# Nhật ký làm việc chung (Bạn / Claude Code / VS Code AI)

Không ai trong 2 AI có cơ chế theo dõi file real-time — đây là nơi đồng bộ
tình hình giữa cả 3 bên, thay cho việc phải nhớ/đoán người khác vừa làm gì.

## Quy ước

1. **TRƯỚC khi bắt đầu việc gì** — đọc vài mục gần nhất ở dưới để biết tình
   hình mới nhất trước khi giả định trạng thái code/dữ liệu.
2. **SAU khi làm xong việc gì** (kể cả việc nhỏ, kể cả chỉ test qua UI không
   sửa code) — thêm 1 mục MỚI LÊN ĐẦU (mới nhất ở trên cùng) theo mẫu:

```
## YYYY-MM-DD HH:MM — <Ai làm: Bạn / Claude Code / VS Code AI>
- Đã làm gì (ngắn gọn, 1-3 dòng)
- File/case/module nào bị ảnh hưởng
- Lưu ý cho người tiếp theo (nếu có) — vd dữ liệu test đã đổi, cần chạy lại gì
```

3. Không cần dài dòng — mục tiêu là đủ để người khác không bị bất ngờ, không
   phải báo cáo đầy đủ.

## 2026-08-07 17:10 — Claude Code
- Làm xong 2 việc trên branch `feature/track-stability` (stack trên
  `feature/audit-log`, chưa merge cái nào vào `master`):
  1. **`modules/track_split.py`** (mới) — phát hiện + tách track bị "nhảy
     người" (tracker gán nhầm 1 track_id cho 2 người khác nhau giữa chừng).
     Xác nhận NGUYÊN NHÂN bằng ảnh crop thật trước khi viết code (track
     `c1a19c1b-..._t70`, case `UI_71ea7dd918b2ce62`: đầu track là người đội
     mũ bảo hiểm, cuối track là người khác mặc đồng phục xanh). Quét toàn
     DB: 87 track nghi ngờ, nhưng phát hiện 1 số case cũ (`test1_f3f914`)
     dùng crop kiểu silhouette màu (dữ liệu test tổng hợp, không phải ảnh
     thật) — CHƯA chạy `--apply` cho case nào, đang chờ xác nhận phạm vi.
  2. **Mũi tên xanh cho track không khớp** — `modules/highlight_video.py` +
     `modules/demo_search.py` (`list_track_ids_for_video`) + `app.py`
     (`build_player_html`): video kết quả giờ vẽ khung (như cũ) cho ứng viên
     khớp, VÀ mũi tên xanh nhỏ trên đầu cho MỌI track khác đã tạo trong video
     đó (kể cả không khớp) — giúp phân biệt "có track nhưng không đủ điểm"
     (có mũi tên) với "không hề phát hiện được" (không có gì). Verify bằng
     cách gọi trực tiếp `build_highlighted_video()` + trích frame thật bằng
     cv2, xác nhận cả khung đỏ + mũi tên xanh cùng hiển thị đúng.
- **Lưu ý cho người tiếp theo**: `image.png`/README dòng 10 vẫn treo. Cả
  `feature/audit-log` và `feature/track-stability` đều CHƯA merge vào
  `master`. Việc tiếp theo đã thống nhất: sau khi xong tách track, quay lại
  làm phương án 1 (chỉnh tham số tracker trong `modules/tracker_configs/`)
  để giảm nhảy-người cho video ingest MỚI.

## 2026-08-07 00:00 — VS Code AI
- Đã ghi nhận quy ước làm việc chung và sẽ đọc `WORKLOG.md` trước khi bắt đầu
  bất kỳ việc gì trên project này.
- Từ giờ, mọi thay đổi/kiểm tra/bugfix sẽ được ghi mới lên đầu file sau khi
  hoàn tất để người khác không bị bất ngờ.
- Lưu ý cho người tiếp theo: nếu bắt đầu một task mới, hãy đọc vài mục gần
  nhất ở đầu file trước.

---

## 2026-08-07 15:05 — Claude Code
- Làm xong "Audit log trước" (ưu tiên #1 đã chốt) trên branch `feature/audit-log`.
- Thêm `modules/audit_log.py` (bảng `search_runs`, `search_run_candidates`,
  `candidate_feedback` — khớp FR-15/16/17 trong PRD mục 8.6, chỉ có hàm
  INSERT, không có update/delete qua UI). Wire vào `app.py`:
  `run_search()` ghi log mọi lần chạy (kể cả 0 kết quả) kèm lý do xếp hạng
  của từng ứng viên; thêm 3 nút "✅ Đúng / ❌ Sai / ⚠️ Cần xem lại" dưới
  Evidence panel để điều tra viên chấm feedback cho ứng viên đang xem.
- Đã verify end-to-end qua browser thật: chạy search trên case
  `benchmark_combined_6430af` (6 video) → xác nhận `search_runs` +
  `search_run_candidates` ghi đúng (17 ứng viên) → bấm ứng viên #1 (track
  `..._t83`) → bấm "✅ Đúng" → xác nhận `candidate_feedback` có đúng 1 dòng
  `feedback='correct'` khớp track đó.
- **Lưu ý cho người tiếp theo**: `image.png`/README dòng 10 vẫn còn treo,
  chưa quyết định. Chưa merge `feature/audit-log` vào `master` — đang chờ
  xác nhận trước khi merge/commit theo đúng quy tắc làm việc.

## 2026-08-07 16:00 — VS Code AI
- Đã tạo workflow benchmark nhỏ ở `modules/benchmark.py` và test mẫu ở
  `tests/test_benchmark.py`.
- Workflow hiện hỗ trợ đánh nhãn candidate theo feedback (`same_person`/
  `different_person`) và tính `top1_accuracy` cơ bản.
- Đã verify bằng `python -m unittest discover -s tests -p 'test_benchmark.py'`:
  2 tests passed.
- Lưu ý cho người tiếp theo: cần chạy một run search thực tế rồi dùng module
  này để sinh JSON benchmark đầu tiên.

---

## 2026-08-07 — Claude Code
- Tạo file này theo yêu cầu, làm nơi trao đổi tình hình chung giữa 3 bên.
- Trước đó trong ngày: `git init` + `.gitignore` (loại trừ `.env`, `case.db`,
  `output/`, `test_assets/`, model weights `.onnx/.pt`, và `image.png` — ảnh
  CCTV thật nhạy cảm, đã cân nhắc và không đưa vào tài liệu dự án) + initial
  commit (`35f4de5`).
- Sửa lỗi `group_top_k_per_video()` trong `modules/demo_search.py`: loại bỏ
  trường hợp 2 track cùng 1 video có khoảng thời gian xuất hiện giao nhau
  (mâu thuẫn — 1 người không thể là 2 track cùng lúc), chỉ giữ track điểm cao
  hơn. Đã restart server + verify qua browser thật, không còn overlap.
- **Lưu ý cho người tiếp theo**: case `benchmark_combined_6430af` hiện có
  6 video (`lab4p-c0/c1/c2/c3`, `campus4-c1`, `passageway1-c3` — video cuối
  mới xuất hiện ngoài dự kiến, có thể do bạn hoặc VS Code AI thêm qua UI).
  `README.md` dòng 10 vẫn còn tham chiếu `image.png` (ảnh CCTV nhạy cảm nói
  trên) — chưa quyết định giữ/xoá.
- Việc đang treo, chưa bắt đầu: 3 hướng ưu tiên đã thống nhất (tăng độ chính
  xác ranking, tăng độ ổn định tracking, xây quy trình đánh giá + audit log).
