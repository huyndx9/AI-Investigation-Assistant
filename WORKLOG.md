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
