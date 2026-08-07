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

## 2026-08-07 17:30 — Claude Code
- Chạy `modules/track_split.py --apply` cho case `UI_71ea7dd918b2ce62` (phạm
  vi đã thống nhất) — 3 lượt liên tiếp (16 → 3 → 1 → 0 track nghi ngờ còn
  lại, vài track bị gộp >2 người nên cần tách nhiều lần, đúng như giới hạn
  đã ghi trong module). Verify: điểm tách của track `t70` rơi đúng
  frame 1520/1525 — khớp chính xác ranh giới đã xác nhận bằng mắt trước đó
  (người đội mũ bảo hiểm kết thúc ở đây, người mặc đồ xanh bắt đầu). DB
  integrity_check: ok. Case này giờ có 97 track (từ 81 track gốc).
- Các case khác (test1_f3f914, TEST_CASE_01...) CHƯA được xử lý — theo đúng
  phạm vi đã thống nhất (nhiều track ở đó là dữ liệu test tổng hợp, không
  phải ảnh CCTV thật).
- Tiếp theo: chuyển sang phương án 1 (chỉnh `modules/tracker_configs/*.yaml`)
  để giảm nhảy-người cho video ingest MỚI sau này (đã thống nhất "làm lần
  lượt" — xong tách track mới sang chỉnh tracker).

## 2026-08-07 18:00 — Claude Code
- Xong phương án 1: chỉnh `modules/tracker_configs/bytetrack_conservative.yaml`
  — `track_buffer` 10 → 5. Không đoán mò: tính ra track_buffer=10 tương
  đương 2.0 GIÂY THẬT (10 keyframe × 1/sample_fps=0.2s) là cửa sổ cho phép
  ghép nhầm người — quá dài cho cảnh đông người. Kiểm chứng thực nghiệm:
  ingest lại ĐÚNG video đã lỗi (case scratch riêng, không đụng dữ liệu thật)
  với config mới → số track nghi ngờ gộp nhầm giảm từ 16 xuống 11 (đo bằng
  `track_split.py`, cùng 1 video, chỉ đổi track_buffer). Cải thiện thật
  nhưng KHÔNG triệt để — đúng như đã ghi sẵn trong comment cũ của file này.
- Cả `track_buffer` mới lẫn `track_split.py` đều KHÔNG được benchmark trên
  tập dữ liệu lớn/đa dạng có ground-truth (giới hạn đã biết, ghi trong
  README) — 2 thay đổi này bổ trợ nhau (tracker giảm rủi ro cho video ingest
  MỚI, track_split sửa dữ liệu ĐÃ CÓ) chứ không thay thế việc cần benchmark
  nghiêm túc sau này.
- Đã hoàn thành cả 3 việc thống nhất "làm lần lượt": (1) tách track cũ,
  (2) mũi tên đánh dấu track không khớp, (3) chỉnh tracker. Cả 2 branch
  (`feature/audit-log`, `feature/track-stability`) vẫn CHƯA merge vào
  `master` — chờ xác nhận.

## 2026-08-07 18:30 — Claude Code
- Test thêm qua UI thật trên `master` trước khi merge (theo yêu cầu): chọn
  lại đúng case `UI_71ea7dd918b2ce62` (đã tách track + tuning tracker),
  xác nhận video kết quả tự động dùng bản có mũi tên ngay cả khi CHƯA tìm
  kiếm (0 candidates), trích frame thật từ file video sinh ra để xem bằng
  mắt — mũi tên xanh hiển thị đúng. Chạy search thật (2 ảnh tham chiếu tự
  chụp từ chính video này) — audit log ghi đúng cả 2 lần (kể cả lần 0 kết
  quả), không lỗi server (chỉ có traceback asyncio vô hại quen thuộc).
- **Đã merge `feature/audit-log` + `feature/track-stability` vào `master`**
  (fast-forward, không xung đột — `master` trước đó vẫn ở đúng initial
  commit nên merge sạch). Đã xoá 2 branch tạm sau khi merge xong.
  `master` hiện tại: `cfe6eb1`.
- Việc còn treo: quyết định `image.png`/README dòng 10 (giữ/xoá). VS Code AI
  vẫn cần tự commit `modules/benchmark.py` + `tests/` (đang untracked).

## 2026-08-07 18:35 — Claude Code
- Bạn xác nhận 2 việc còn treo:
  1. `image.png`/README dòng 10 — **giữ nguyên**, không đổi gì. Coi như đã
     chốt, không hỏi lại nữa.
  2. `modules/benchmark.py` + `tests/` — **để VS Code AI tự commit phần của
     họ**. Tôi không đụng tới 2 mục này.
- Không còn việc gì treo lại từ phía tôi tại thời điểm này.

## 2026-08-07 19:00 — Claude Code
- **Bug thật do chính track_split.py gây ra**: Bạn báo "khung hiển thị nhầm
  đối tượng, có lúc không hiện khung, dù ảnh ứng viên phù hợp vẫn đúng".
  Nguyên nhân: `build_player_html()` (app.py) cache video có vẽ khung theo
  key = hash(TÊN track_id) — nhưng `track_split.py` lại RÚT NGẮN phạm vi
  khung hình của 1 track_id ĐÃ CÓ SẴN khi tách (vd `t70` từ 1475-1575 xuống
  còn 1475-1520). Nếu video đã cache TRƯỚC khi tách mà sau đó bị dùng lại
  do trùng tên track_id, khung sẽ vẽ theo phạm vi CŨ — sai vị trí/thời điểm.
- **Đã sửa**: thêm `get_track_frame_ranges()` (`modules/demo_search.py`),
  cache key giờ hash cả `(track_id, first_frame, last_frame)` — đổi phạm vi
  khung hình (do tách track) sẽ tự làm cache miss, buộc vẽ lại. Verify thật:
  dùng chính 1 crop của track `t187` (track tách ra) làm ảnh tham chiếu →
  match đúng chính nó (điểm 0.886) → sinh video mới (cache key đổi từ
  `37a5e3bff4` sang `c8faf0f204`, xác nhận không dùng nhầm cache cũ) →
  trích frame thật trong đúng khoảng 580-620 → khung đỏ khớp chính xác
  người trong ảnh tham chiếu. Restart server, không lỗi.
- File cache cũ (trước khi sửa) vẫn còn nằm rải rác trong `output/*/web/`
  — không còn bị dùng nhầm nữa (hash khác nên không match), chỉ là rác vô
  hại, chưa dọn (không ảnh hưởng tính đúng đắn).
- **Lưu ý quan trọng cho tương lai**: bất kỳ script nào sau này MUTATE dữ
  liệu track/crop đã có sẵn (không chỉ thêm mới) đều cần rà lại xem cache
  key ở nơi khác có dựa trên dữ liệu đã đổi hay không — đây là lỗi thuộc
  nhóm "cache invalidation", dễ tái diễn ở chỗ khác nếu không để ý.

## 2026-08-07 19:15 — Claude Code
- Đã sửa lý do gốc khiến bạn vẫn thấy "nhiều kết quả hiển thị sai" sau lần
  fix trước: lần trước tôi CHỈ chạy `track_split.py --apply` cho 1 case
  (`UI_71ea7dd918b2ce62`), 71 track nghi ngờ ở các case khác vẫn chưa sửa.
  Rà lại kỹ hơn: nhận định "case cũ = dữ liệu test tổng hợp" trước đây quá
  rộng — thực ra chỉ ĐÚNG 1 video duy nhất (`vtest_seg_annotated.mp4` trong
  case `test1_f3f914` — video debug/visualization bị lỡ ingest như nguồn
  thật, crop kiểu silhouette màu), còn lại mọi video khác ở mọi case đều là
  video benchmark thật, hợp lệ để sửa.
- Bạn xác nhận mở rộng phạm vi — đã chạy `--apply` (nhiều lượt tới khi sạch)
  cho toàn bộ case còn lại: `benchmark_combined_6430af` (5→0),
  `da_camera_test_goc_quay_khac_nhau_4a668d` (7→0),
  `terrace_2_goc_camera_d8cb89` (16→3→0), `UI_7386199102492dfd` (3→0),
  `TEST_CASE_01` (4→1→0), `vu_an_test_da_video_a17ac2` (4→1→0),
  `test1_f3f914` (27→4→0, dùng script lọc riêng để LOẠI TRỪ video debug
  nói trên).
- Quét lại toàn DB: chỉ còn đúng 5 track thuộc video debug đã loại trừ có
  chủ đích — mọi case dữ liệu thật đã sạch hoàn toàn. `PRAGMA
  integrity_check`: ok. Tổng track trong DB: 1574 (từ ~1479 ban đầu).
  Không có thay đổi code (chỉ mutate `case.db`, đã gitignore) — không cần
  restart server, đã kiểm tra log không lỗi thật.

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
