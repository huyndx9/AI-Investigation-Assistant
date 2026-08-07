# PRD — AI Investigation Assistant
## Phase 1 MVP: Evidence Candidate Ranking Tool

| | |
|---|---|
| **Phiên bản** | 0.1 (Draft) |
| **Phạm vi** | Phase 1 MVP only |
| **Chủ sở hữu tài liệu** | Product Management (Team A) |
| **Trạng thái** | Draft — chờ review từ BA, CV team, AI Reasoning team, Backend |
| **Tài liệu liên quan** | Vision & Master Product Specification v1.0 |

---

## 1. Mục đích tài liệu

Tài liệu này định nghĩa **chính xác những gì Phase 1 MVP sẽ làm và không làm**. Nó thu hẹp phạm vi từ Master Product Specification (vốn mô tả tầm nhìn dài hạn 5 phase) xuống thành một tập yêu cầu có thể build, test và nghiệm thu được trong khung thời gian MVP.

Đây là tài liệu tham chiếu chung cho BA, PM, CV team, AI Reasoning team, Backend, Frontend, QA và DevOps. Khi có mâu thuẫn giữa tài liệu này và Master Spec, **PRD này là nguồn quyết định cho Phase 1**.

---

## 2. Bối cảnh & vấn đề

Điều tra viên hiện phải xem thủ công hàng trăm giờ video giám sát từ nhiều nguồn (CCTV, dashcam, camera điện thoại) để tìm một đối tượng cụ thể trong một vụ án đã có sự cho phép của cơ quan có thẩm quyền. Việc này tốn thời gian, phụ thuộc trí nhớ và kinh nghiệm cá nhân, dễ bỏ sót.

**AI Investigation Assistant** hỗ trợ điều tra viên bằng cách tự động trích xuất đặc điểm của người xuất hiện trong video có sẵn, và **xếp hạng các ứng viên theo xác suất khớp** với mô tả đối tượng nghi vấn — để điều tra viên xem xét và quyết định, không phải để hệ thống tự xác minh danh tính.

---

## 3. Nguyên tắc thiết kế (áp dụng xuyên suốt mọi yêu cầu bên dưới)

| Nguyên tắc | Ý nghĩa cho Phase 1 MVP |
|---|---|
| Human in the Loop | Hệ thống chỉ đề xuất, không kết luận. Mọi màn hình kết quả phải có lựa chọn xem xét thủ công. |
| Explainable AI | Mỗi ứng viên trong danh sách phải kèm lý do được xếp hạng (đặc điểm nào khớp, mức độ tin cậy). |
| Privacy First | Toàn bộ xử lý on-premise. Không có API gửi video ra ngoài mạng nội bộ. |
| Evidence Driven | Hệ thống không gắn nhãn "nghi phạm" cho bất kỳ ai — chỉ gắn nhãn "ứng viên có đặc điểm khớp". |
| Truy vết được (Audit Trail) | **Có ngay từ Phase 1**, không đợi đến bản Enterprise. Mọi truy vấn phải ghi log ai, khi nào, tiêu chí gì. |

---

## 4. Trong phạm vi (In Scope) — Phase 1 MVP

- Nhập video từ nhiều nguồn (CCTV, dashcam, camera điện thoại) cho **một vụ án đã được cấp phép cụ thể**.
- Phát hiện người và theo dõi (tracking) trong phạm vi một camera.
- Trích xuất đặc điểm **ngoại hình tĩnh**: màu sắc quần áo, phụ kiện, chiều cao tương đối.
- Trích xuất đặc điểm **hình thể (build)**: tỷ lệ vai/hông, tỷ lệ chi trên/chi dưới — nhóm đặc điểm ổn định qua nhiều khung hình.
- Lọc và tìm kiếm ứng viên theo tiêu chí do điều tra viên nhập (màu áo, chiều cao, phụ kiện...).
- Danh sách ứng viên xếp hạng theo xác suất khớp, kèm giải thích lý do xếp hạng.
- Xuất báo cáo PDF (danh sách ứng viên, ảnh/clip, ghi chú của điều tra viên).
- Audit log: ghi lại mọi truy vấn, kết quả xem, và người thực hiện.
- Giao diện quản lý vụ án (case) đơn giản: tạo, đặt tên, đóng vụ án.

## 5. Ngoài phạm vi (Out of Scope) — Phase 1 MVP

- **Dáng đi/dáng đứng động** (nhịp bước, độ mở bàn chân, biên độ vung tay) — đây là **R&D spike có điều kiện**, chỉ đưa vào MVP nếu spike đạt tiêu chí thành công đã thống nhất (xem mục 10).
- Đồng bộ thời gian đa camera, timeline, heatmap, evidence graph — thuộc Phase 2.
- Reasoning Engine nâng cao, Investigation Copilot bằng ngôn ngữ tự nhiên — thuộc Phase 3-4.
- Xử lý real-time / cảnh báo trực tiếp — sản phẩm là công cụ hậu kiểm (post-event).
- Xác minh danh tính thật (gắn tên, đối chiếu CSDL công dân) — hệ thống không làm việc này ở bất kỳ phase nào theo nguyên tắc Evidence Driven.
- Cổng chia sẻ cộng đồng / thu thập video từ người dân — cần khung pháp lý riêng, không thuộc MVP.
- Multi-tenant, role permission chi tiết, GPU cluster — thuộc bản Enterprise (Phase 5).

---

## 6. Vai trò người dùng (Personas)

| Vai trò | Mô tả | Nhu cầu chính |
|---|---|---|
| Điều tra viên | Người dùng chính, thao tác trực tiếp trên hệ thống | Tìm nhanh ứng viên khớp mô tả, hiểu vì sao được đề xuất |
| Quản lý vụ án / Trưởng nhóm điều tra | Giám sát tiến độ, duyệt báo cáo | Xem audit log, xuất báo cáo tổng hợp |
| Quản trị hệ thống (Admin) | Vận hành, bảo trì | Quản lý case, theo dõi hiệu năng xử lý |

---

## 7. User Stories chính (Phase 1)

| ID | User Story | Ưu tiên |
|---|---|---|
| US-01 | Là điều tra viên, tôi muốn tạo một vụ án mới để bắt đầu phân tích video liên quan | Cao |
| US-02 | Là điều tra viên, tôi muốn nhập video từ nhiều nguồn khác nhau vào cùng một vụ án | Cao |
| US-03 | Là điều tra viên, tôi muốn thiết lập tiêu chí lọc (màu áo, chiều cao, phụ kiện) để thu hẹp danh sách | Cao |
| US-04 | Là điều tra viên, tôi muốn xem danh sách ứng viên được xếp hạng kèm lý do khớp | Cao |
| US-05 | Là điều tra viên, tôi muốn xem clip ngắn và ảnh chụp của từng ứng viên để so sánh trực quan | Cao |
| US-06 | Là điều tra viên, tôi muốn xuất báo cáo PDF tổng hợp kết quả điều tra | Trung bình |
| US-07 | Là quản lý, tôi muốn xem lại audit log để biết ai đã truy vấn gì trong vụ án | Cao |
| US-08 | Là admin, tôi muốn theo dõi thời gian xử lý video để đánh giá hiệu năng hệ thống | Trung bình |

---

## 8. Yêu cầu chức năng (Functional Requirements)

### 8.1 Quản lý vụ án
- FR-01: Hệ thống cho phép tạo/đóng/xem danh sách vụ án, mỗi vụ án cách ly dữ liệu với vụ án khác.
- FR-02: Mỗi vụ án lưu thông tin: tên, mô tả, ngày tạo, người phụ trách.

### 8.2 Nhập & xử lý video
- FR-03: Hỗ trợ nhập video từ file cục bộ (không yêu cầu kết nối camera trực tiếp ở MVP).
- FR-04: Tự động giải mã, trích keyframe, không xử lý toàn bộ video liên tục (tối ưu tài nguyên).
- FR-05: Phát hiện người (person detection) và theo dõi trong phạm vi một camera.

### 8.3 Trích xuất đặc điểm — **thuộc phạm vi CV team (Team D)**
- FR-06: Trích xuất đặc điểm ngoại hình tĩnh (màu quần áo, phụ kiện, chiều cao tương đối) kèm điểm tin cậy riêng cho từng đặc điểm.
- FR-07: Trích xuất tỷ lệ hình thể (build) từ keypoint tư thế, có hiệu chỉnh phối cảnh theo góc camera.
- FR-08: Đầu ra của CV team là **feature vector kèm confidence score** cho từng đặc điểm — không tự xếp hạng, không tự kết luận.

### 8.4 Tìm kiếm, lọc & xếp hạng — **thuộc phạm vi AI Reasoning team (Team E)**
- FR-09: Cho phép điều tra viên thiết lập bộ tiêu chí lọc qua giao diện (chọn màu, khoảng chiều cao, phụ kiện...).
- FR-10: Tổng hợp các đặc điểm và điểm tin cậy thành **một xác suất khớp duy nhất** theo mô hình trọng số — không dùng cascade filter loại cứng từng bước.
- FR-11: Mỗi ứng viên trong kết quả phải hiển thị: ảnh/clip, điểm xác suất tổng hợp, và danh sách đặc điểm đóng góp vào điểm đó (explainability).
- FR-12: Danh sách kết quả giới hạn khoảng 10-20 ứng viên có điểm cao nhất.

> **Ranh giới trách nhiệm:** CV team (Team D) sở hữu toàn bộ việc trích xuất đặc điểm thô và điểm tin cậy riêng lẻ. AI Reasoning team (Team E) sở hữu toàn bộ logic tổng hợp, xếp hạng và giải thích. Không team nào được tự ý thay đổi logic thuộc phạm vi của team kia mà không qua thống nhất chung.

### 8.5 Xem xét & xuất báo cáo
- FR-13: Điều tra viên có thể xem chậm, phóng to, ghi chú trên từng ứng viên.
- FR-14: Xuất báo cáo PDF gồm: danh sách ứng viên, ảnh, điểm xếp hạng, ghi chú của điều tra viên, thông tin vụ án.

### 8.6 Audit Log (bắt buộc từ Phase 1, không hoãn)
- FR-15: Ghi log mọi truy vấn: người thực hiện, thời gian, tiêu chí lọc đã dùng.
- FR-16: Ghi log mọi lần xem/xuất kết quả của một ứng viên cụ thể.
- FR-17: Audit log không thể chỉnh sửa hoặc xoá bởi người dùng thường (chỉ admin có quyền xem, không có quyền sửa).

---

## 9. Yêu cầu phi chức năng (Non-Functional Requirements)

| Hạng mục | Yêu cầu |
|---|---|
| Bảo mật & riêng tư | Toàn bộ xử lý và lưu trữ on-premise. Không có kết nối cloud xử lý video. |
| Hiệu năng | Xử lý 1 giờ video ở keyframe-rate hợp lý trong thời gian chấp nhận được trên phần cứng GPU tiêu chuẩn (mức cụ thể do CV team đề xuất sau khi benchmark). |
| Khả năng giải thích | Không có "hộp đen" — mọi điểm số xếp hạng phải truy ngược được về đặc điểm đầu vào. |
| Khả năng mở rộng | Kiến trúc module hoá — thay thế một module AI không ảnh hưởng các module khác. |
| Khả dụng bằng chứng | Kết quả và audit log phải đủ chi tiết để hỗ trợ chain-of-custody khi dùng làm tài liệu tham khảo trong điều tra. |

---

## 10. Phụ thuộc & điều kiện tiên quyết

- **CV Spike (dáng người/dáng đi):** trước khi cam kết đưa nhóm đặc điểm hình thể vào FR-07 chính thức, CV team cần hoàn thành spike kiểm chứng trên tập dữ liệu thử nghiệm nội bộ, với tiêu chí thành công (độ chính xác tối thiểu, điều kiện góc camera chấp nhận được) do CV team và PM thống nhất trước khi bắt đầu Sprint 1.
- **Go/No-go:** nếu spike không đạt, FR-07 thu hẹp lại chỉ còn nhóm đặc điểm ngoại hình tĩnh (FR-06), hình thể động (dáng đi) chuyển thành backlog cho Phase 3.
- **Cấp phép pháp lý:** mỗi vụ án (case) trong hệ thống giả định đã có sự cho phép/cấp phép phù hợp từ cơ quan có thẩm quyền trước khi nhập dữ liệu — đây là điều kiện vận hành, không phải tính năng phần mềm.

---

## 11. Rủi ro đã biết

| Rủi ro | Mức độ | Ghi chú |
|---|---|---|
| Trích xuất dáng đi ngoài trời kém chính xác | Cao | Đã tách thành spike có điều kiện (mục 10), không nằm trong cam kết MVP mặc định |
| Ước lượng chiều cao/tỷ lệ hình thể bị méo do góc camera | Trung bình | Cần hiệu chỉnh phối cảnh, chỉ hiển thị dạng khoảng/phân cấp, không hiển thị số tuyệt đối |
| Chồng chéo trách nhiệm CV team và AI Reasoning team | Trung bình | Đã phân định rõ ở mục 8.4 |
| Audit log bị xem là "tính năng phụ" và bị trì hoãn | Trung bình | Đã đưa vào FR-15 đến FR-17, bắt buộc trong Definition of Done của MVP |

---

## 12. Tiêu chí hoàn thành Phase 1 MVP (Definition of Done)

MVP được coi là hoàn thành khi:

1. Điều tra viên có thể tạo vụ án, nhập video, thiết lập bộ lọc, và nhận danh sách ứng viên xếp hạng có giải thích (FR-01 đến FR-12).
2. Mọi truy vấn và lượt xem đều được ghi audit log đầy đủ (FR-15 đến FR-17).
3. Báo cáo PDF xuất ra đầy đủ thông tin cần thiết (FR-14).
4. Kết quả spike dáng người/dáng đi đã có (đạt hoặc không đạt), và phạm vi FR-07 được chốt tương ứng.
5. Không có thành phần nào xử lý hoặc lưu trữ dữ liệu ngoài mạng nội bộ.

---

## 13. Câu hỏi còn mở (Open Questions)

- Tiêu chí thành công cụ thể (con số %) cho CV spike là gì — cần CV team đề xuất trước Sprint 1.
- Định dạng lưu trữ metadata (SQLite thuần hay kèm vector DB như FAISS) — cần Team H xác nhận dựa trên khối lượng dữ liệu dự kiến.
- Quy trình cấp quyền truy cập vụ án (ai được tạo case, ai được xem) — cần chốt trước khi thiết kế audit log chi tiết.

---

## 14. Phụ lục — Thuật ngữ

| Thuật ngữ | Giải thích |
|---|---|
| Ứng viên (Candidate) | Một người được hệ thống phát hiện và xếp hạng theo mức độ khớp với tiêu chí tìm kiếm — không đồng nghĩa với "nghi phạm" |
| Feature vector | Tập hợp các giá trị số mô tả đặc điểm ngoại hình/hình thể của một người, do CV team tạo ra |
| Confidence score | Điểm tin cậy cho một đặc điểm riêng lẻ hoặc điểm xác suất tổng hợp cho một ứng viên |
| Audit log | Nhật ký ghi lại hành động truy vấn/xem của người dùng, phục vụ truy vết và chain-of-custody |
