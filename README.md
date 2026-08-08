# AI Investigation Assistant — Prototype

Công cụ hỗ trợ điều tra viên tìm kiếm 1 người qua nhiều video camera giám sát, dựa vào **đặc điểm ngoại hình** (quần áo, dáng người) — không phải nhận diện khuôn mặt.

> ⚠️ **Đây là PROTOTYPE minh hoạ**, không phải sản phẩm hoàn chỉnh. Xem mục [Giới hạn đã biết](#giới-hạn-đã-biết--chưa-sẵn-sàng-cho-thực-tế) trước khi cân nhắc dùng cho ca thật.

## Động lực

Dự án này bắt đầu sau khi tác giả đọc được [bản tin về 1 vụ án](https://www.yonhapnewstv.co.kr/news/AKR202608030945281Z0) mà đến nay kẻ gây án vẫn chưa bị bắt và chịu trách nhiệm trước pháp luật. Cảm giác phẫn nộ trước việc đó là lý do trực tiếp thôi thúc xây dựng công cụ này — với hy vọng rút ngắn thời gian điều tra viên phải bỏ ra để rà soát hàng giờ camera giám sát, tăng khả năng lần ra manh mối trong các vụ án tương tự.
![alt text](image.png)
Đây cũng chính là lý do các nguyên tắc **Human in the Loop / Không kết luận danh tính** được đặt làm ưu tiên xuyên suốt — công cụ chỉ nhằm hỗ trợ điều tra viên tìm đúng người nhanh hơn, không thay thế quy trình điều tra và xét xử đúng pháp luật.

## Đây KHÔNG PHẢI là gì

- **Không phải nhận diện khuôn mặt** — không trích xuất, không so sánh đặc điểm khuôn mặt.
- **Không kết luận danh tính.** Mọi kết quả là "ứng viên có đặc điểm khớp", kèm điểm số + giải thích — điều tra viên tự xem lại bằng chứng (video, ảnh crop) và tự quyết định.
- **Không suy luận giới tính, tuổi tác, chủng tộc** — chủ động loại bỏ khỏi thiết kế vì CCTV độ phân giải thấp không đủ tin cậy cho việc này, và suy luận sai dễ khiến điều tra viên loại nhầm đúng người.

Ba nguyên tắc trên xuyên suốt toàn bộ pipeline — xem thêm `PRD_AI_Investigation_Assistant_v0.1.md`.

## Tính năng chính

- **Quản lý case nhiều video/camera** — gom nhiều nguồn video vào 1 vụ án, tìm kiếm chạy trên toàn bộ.
- **Tự động thêm video khi tải lên** — không cần bấm nút riêng, video được xử lý (phát hiện người + theo dõi + trích đặc điểm) ngay khi upload.
- **Tìm theo ảnh tham chiếu** — hỗ trợ nhiều ảnh cùng 1 người (nhiều góc/khoảnh khắc), gộp bằng bỏ phiếu đa số.
- **So khớp 2 tầng**: đặc điểm ngoại hình rời rạc (màu áo/quần, tay áo, mũ, tóc, giày — OpenCV thuần, chạy local) kết hợp với **embedding ReID** (mô hình `yolo26n-reid.onnx`, đo độ tương đồng dáng người/trang phục tổng thể).
- **Tinh chỉnh bằng AI thị giác (tuỳ chọn, opt-in)** — gửi ảnh crop cho ChatGPT Vision so sánh lại top ứng viên, có giải thích bằng tiếng Việt; đồng thời có thể dùng AI mô tả trực tiếp đặc điểm ảnh tham chiếu (túi/balo, loại trang phục, hoạ tiết, phụ kiện...) thay cho heuristic màu cổ điển khi ánh sáng/tóc gây nhiễu.
- **Kết quả theo từng video, không bị 1 camera "chiếm hết chỗ"** — mỗi video/camera luôn được xét công bằng, tối đa N ứng viên hiển thị mỗi video (không phải toàn case).
- **Trình phát video có timeline đánh dấu** — bấm vào ứng viên để nhảy thẳng tới đoạn nghi có đối tượng.
- **Lộ trình trên bản đồ (mở rộng, tuỳ chọn)** — thiết lập vị trí + giờ quay thực cho từng camera, hệ thống nối các lần xuất hiện theo thời gian thành gợi ý lộ trình (không phải kết luận chắc chắn), mỗi camera chỉ 1 điểm đại diện.
- **Nhật ký kiểm toán (audit log)** — mọi lần tìm kiếm (case, ảnh tham chiếu, tham số, toàn bộ ứng viên kèm lý do xếp hạng) được ghi lại tự động; điều tra viên có thể chấm "Đúng/Sai/Cần xem lại" cho từng ứng viên ngay trong Evidence panel.

## Kiến trúc / các module

| File | Vai trò |
|---|---|
| `app.py` | Giao diện Gradio — điều phối toàn bộ luồng, không chứa logic AI. |
| `modules/pipeline_ingest.py` | **Module 1** — giải mã video, lấy mẫu khung hình, phát hiện + theo dõi người (YOLO segmentation + ByteTrack), lưu track/crop vào DB. |
| `modules/appearance.py` | **Module 2** — trích đặc điểm ngoại hình tĩnh (màu áo/quần, tay áo, mũ, tóc, giày) từ 1 crop bằng OpenCV thuần (HSV histogram), không so sánh giữa các track. |
| `modules/embedding.py` | Trích embedding ReID (512 chiều) từ crop qua `yolo26n-reid.onnx` — tín hiệu so khớp chính, mạnh hơn màu sắc rời rạc. |
| `modules/vlm_compare.py` | Tích hợp OpenAI Vision (opt-in) — so sánh ảnh tham chiếu với ứng viên, và mô tả trực tiếp đặc điểm ảnh tham chiếu. |
| `modules/demo_search.py` | Ghép các tín hiệu trên thành điểm khớp cuối, xếp hạng theo từng video — **PROTOTYPE cho bước so khớp, không phải thiết kế Evidence Fusion đầy đủ theo PRD**. |
| `modules/geo_route.py` | Module mở rộng, tách biệt hoàn toàn khỏi schema cốt lõi — vị trí camera + giờ quay thực + dựng lộ trình trên bản đồ (Leaflet/OpenStreetMap). |
| `modules/video_transcode.py` | Chuyển mã video gốc sang H.264/mp4 để phát được trên trình duyệt — không đụng tới file gốc dùng cho xử lý AI. |
| `modules/highlight_video.py` | Dựng bản video có vẽ khung/nhãn cho track ứng viên, phục vụ xem trực tiếp trong UI. |
| `modules/visualize_tracks.py` | Công cụ debug — vẽ lại bbox/track_id đã lưu trong DB để tự kiểm tra bằng mắt (không chạy lại model). |
| `modules/audit_log.py` | Ghi nhật ký mọi lần tìm kiếm + feedback điều tra viên (FR-15..17 trong PRD) — chỉ có hàm ghi, không có sửa/xoá qua UI. |
| `modules/track_split.py` | Công cụ sửa dữ liệu đã ingest — phát hiện + tách track bị tracker gán nhầm cho 2 người khác nhau giữa chừng, dựa vào điểm gãy trong embedding ReID. |
| `modules/ground_truth.py` | Sinh cặp ground-truth tự động (từ track giao nhau về thời gian + track ổn định nội tại) để đo khách quan false positive/negative rate của bước xếp hạng, thay vì chỉnh tay không kiểm chứng được. |

Dữ liệu lưu trong SQLite (`case.db`): `cases`, `videos`, `tracks`, `track_crops`, `features_appearance`, `features_embedding`, và các bảng phụ `video_geo`, `search_runs`/`search_run_candidates`/`candidate_feedback` (module mở rộng).

## Cài đặt

Yêu cầu Python 3.14 trở lên. Xem `requirements.txt` để biết chi tiết — lưu ý riêng phần `torch`/`torchvision`/`onnxruntime-gpu` gắn với 1 tag CUDA cụ thể, đọc kỹ comment đầu file trước khi cài hoặc nâng cấp.

```bash
pip install -r requirements.txt
```

`ffmpeg` không cần cài hệ thống — dùng binary tĩnh đóng gói sẵn trong `imageio-ffmpeg`.

### Cấu hình AI thị giác (tuỳ chọn)

Tính năng "Dùng AI thị giác (ChatGPT Vision)" cần biến môi trường `OPENAI_API_KEY`. Tạo file `.env` ở thư mục gốc (không commit file này):

```
OPENAI_API_KEY=<api-key-của-bạn>
```

Không bật tính năng này thì toàn bộ hệ thống chạy hoàn toàn local, không gửi dữ liệu ra ngoài.

## Chạy thử

```bash
python app.py
```

Mở `http://localhost:7860`.

**Quy trình cơ bản**: Tạo case → tải video lên (tự động xử lý) → tải ảnh tham chiếu (người cần tìm) → bấm Tìm kiếm → xem danh sách video có đối tượng xuất hiện + ứng viên phù hợp → bấm vào 1 ứng viên để xem trên video + đọc chi tiết bằng chứng.

## Giới hạn đã biết — chưa sẵn sàng cho thực tế

- **Chỉ là công cụ lọc sơ bộ (triage), không phải công cụ ra quyết định.** Đo được bằng ground-truth tự động (`modules/ground_truth.py`, 2880 cặp chắc chắn khác người + 300 cặp có khả năng cùng người, xem `ground_truth_pairs.json`): ở ngưỡng hiện tại, **~33% cặp CHẮC CHẮN khác người vẫn vượt ngưỡng tin cậy** (false positive rate) — là tín hiệu xếp hạng, không phải bằng chứng chắc chắn. Có phương án giảm còn ~17.5% bằng cách chỉnh lại ngưỡng (đổi lại tăng tỷ lệ bỏ sót người đúng từ ~2.3% lên ~10%) — chưa áp dụng, đang chờ quyết định đánh đổi.
- **Phân loại màu áo/quần nhạy với ánh sáng (color constancy)** — đã xác nhận cụ thể: 1 track áo nâu/be bị nhận nhầm "đen" vì đa số crop nhỏ/xa camera thiếu sáng. Đã sửa 1 phần (gộp màu theo trọng số diện tích crop thay vì đếm đều), nhưng thử hạ ngưỡng đen sâu hơn thì phát hiện **cả video có thể bị ám màu** (crop chắc chắn màu đen thật cũng bị đổi thành xanh dương khi hạ ngưỡng) — sửa triệt để cần khôi phục cân bằng trắng, ngoài phạm vi hiện tại.
- **Không xử lý được đổi trang phục** hoặc nhiều người mặc đồ giống nhau (đồng phục...).
- **Geocode địa chỉ chi tiết ở Hàn Quốc qua OpenStreetMap (miễn phí) độ chính xác còn hạn chế** — cần geocoder chuyên cho Hàn Quốc nếu độ chính xác vị trí quan trọng.
- **Chưa đánh giá ràng buộc pháp lý/quyền riêng tư** (vd PIPA tại Hàn Quốc) cho loại phân tích video giám sát này.

## Trạng thái dự án

Prototype minh hoạ Module 1 (ingest + track) + Module 2 (appearance) + các mở rộng thử nghiệm (ReID, AI thị giác, bản đồ). Chưa phải giao diện Phase 1 MVP đầy đủ theo `PRD_AI_Investigation_Assistant_v0.1.md` (thiếu audit log, thiết kế Evidence Fusion chính thức do AI Reasoning team sở hữu).
