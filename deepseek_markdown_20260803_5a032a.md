# 🕵️ AI Investigation Assistant (AIA)
## Trợ lý điều tra thông minh đa nguồn

---

## 1. Tổng quan

AI Investigation Assistant là một phần mềm desktop/web dành cho điều tra viên (cảnh sát, an ninh, bảo vệ) giúp tự động phát hiện, trích xuất và lọc các đối tượng trong video giám sát từ nhiều nguồn khác nhau (CCTV, camera nhà dân, dashcam, điện thoại,…) dựa trên hàng loạt đặc điểm hình thể, quần áo và hành vi.

Sản phẩm không thay thế con người, không kết luận tội phạm, mà đóng vai trò như một trợ lý thông minh giúp điều tra viên tìm kiếm nhanh hơn, chính xác hơn, và không bị ràng buộc bởi nhận diện khuôn mặt.

---

## 2. Vấn đề đang giải quyết

- Điều tra viên mất hàng chục giờ xem thủ công video từ nhiều camera khác nhau.
- Phải tự ghi nhớ và so sánh đặc điểm của đối tượng (màu áo, dáng đi, chiều cao…) bằng mắt.
- Dễ bỏ sót hoặc nhầm lẫn khi có quá nhiều người xuất hiện.
- Hệ thống nhận diện khuôn mặt không hiệu quả khi đeo khẩu trang, quay lưng, hoặc vướng rào cản pháp lý.

---

## 3. Giải pháp cốt lõi

- Nhập video từ bất kỳ nguồn nào vào ứng dụng.
- AI tự động phân tích từng video để phát hiện con người và trích xuất đặc điểm:
  - Màu sắc quần áo, phụ kiện
  - Dáng đi, tư thế, biên độ vung tay
  - Chiều cao tương đối (so với vật thể xung quanh)
  - Tốc độ và hướng di chuyển
  - Hình dạng cơ thể, tỷ lệ các bộ phận
- Cho phép lọc theo tổ hợp các đặc điểm (ví dụ: áo đỏ, quần jeans, đi lê chân trái, cao hơn trung bình).
- Hiển thị danh sách ứng viên (khoảng 10–20 người) kèm clip ngắn và ảnh chụp rõ nhất.
- Người dùng xem xét và quyết định cuối cùng – AI chỉ hỗ trợ, không thay thế con người.

---

## 4. Các nhóm đặc điểm AI trích xuất

**Nhóm tĩnh (Appearance)**
- Màu sắc (áo, quần, giày, mũ, balo)
- Hình dạng (dài tay, ngắn tay, có mũ, có quai)
- Phụ kiện (túi xách, điện thoại, ô, gậy)
- Chiều cao tương đối (so với người xung quanh hoặc vật thể tham chiếu)

**Nhóm chuyển động (Motion & Gait)**
- Dáng đi (biên độ vung tay, độ rộng bước chân, nhịp điệu)
- Tư thế (đi thẳng, khom lưng, lê chân)
- Tốc độ di chuyển (m/s ước lượng)
- Hướng di chuyển
- Độ mở của bàn chân (hình chữ V hay song song)

**Nhóm ngữ cảnh (Context)**
- Thời điểm xuất hiện (sau khi đồng bộ thời gian)
- Vị trí trong khung hình
- Tương tác với vật thể (cầm, đặt, thả)

---

## 5. Quy trình sử dụng (User Journey)

| Bước | Hành động | Vai trò của AI |
|------|-----------|----------------|
| 1 | Điều tra viên tạo case mới, mô tả sơ bộ | Lưu metadata, tạo phiên làm việc |
| 2 | Kéo thả nhiều video vào ứng dụng | Giải mã, phát hiện người, trích xuất đặc điểm |
| 3 | Chọn các tiêu chí lọc (màu sắc, dáng đi, chiều cao…) | – |
| 4 | Nhấn nút "Tìm kiếm" | Áp dụng cascade filter → trả về danh sách ứng viên rút gọn |
| 5 | Xem clip, so sánh, chọn ứng viên đúng | Không quyết định, chỉ gợi ý |
| 6 | Xuất báo cáo PDF kèm timeline, ảnh, ghi chú | Tự động tổng hợp thông tin |

---

## 6. Kiến trúc kỹ thuật đề xuất

**Frontend (GUI)**: Electron (Desktop) hoặc React + WASM (Web)  
**Backend xử lý AI**: Python FastAPI  
**Phát hiện người**: YOLOv9 hoặc RTMDet  
**Ước lượng tư thế**: RTMPose hoặc OpenPose  
**Theo dõi đối tượng**: ByteTrack hoặc DeepSORT  
**Nhận diện dáng đi**: OpenGait hoặc GEI + CNN  
**Trích xuất màu & đồ vật**: CLIP hoặc các mô hình classification  
**Cơ sở dữ liệu**: SQLite (cục bộ, lưu metadata)  
**GPU tăng tốc**: CUDA (NVIDIA) hoặc OpenVINO (Intel)

---

## 7. Cấu trúc thư mục dự án (sơ bộ)

---

## 8. Lộ trình phát triển (Roadmap)

**Phase 1 – MVP (2–3 tháng)**
- Upload video, phát hiện người (YOLO), trích xuất màu sắc và pose cơ bản.
- Lọc theo màu, chiều cao tương đối, tốc độ, hướng di chuyển.
- Giao diện danh sách ứng viên, xuất báo cáo đơn giản.
- Chạy trên máy tính cục bộ (on-premise).

**Phase 2 – Nâng cao (3–6 tháng)**
- Cải thiện gait recognition (GEI + Siamese Network).
- Đồng bộ thời gian tương đối giữa các video (dựa trên sự kiện chung).
- Tự động dựng timeline và bản đồ đường đi của đối tượng.
- Thêm tính năng so sánh đối tượng trực quan.

**Phase 3 – Cộng đồng và đám mây (6–12 tháng)**
- Ứng dụng di động cho người dân tải lên video (crowdsourcing).
- Cổng chia sẻ an toàn (mã hóa đầu cuối).
- Tùy chọn chạy trên cloud với chi phí linh hoạt.

---

## 9. Ưu điểm cạnh tranh

- Không phụ thuộc vào nhận diện khuôn mặt → hoạt động với khẩu trang, quay lưng, hợp pháp hơn.
- Tận dụng mọi nguồn video (không chỉ CCTV chuyên dụng).
- Con người ra quyết định cuối cùng → giảm rủi ro sai sót, dễ dàng sử dụng trong điều tra chính thức.
- Chi phí thấp vì sử dụng mã nguồn mở và chạy nội bộ (không đám mây đắt tiền).
- Dễ dàng mở rộng với nhiều loại camera và định dạng video.

---

## 10. Đối tượng người dùng

- Cảnh sát điều tra
- An ninh nội bộ của các tòa nhà, khu công nghiệp
- Quản lý trung tâm thương mại, sân bay, bến xe
- Các công ty cung cấp giải pháp an ninh

---

## 11. Các trường hợp sử dụng cụ thể

- Tìm người mất tích: Lọc theo quần áo, dáng đi, tốc độ trong khu vực cuối cùng xuất hiện.
- Trộm cắp trong tòa nhà: Tổng hợp 30 camera, tìm người mang balo lớn, đi lòng vòng, không phải cư dân.
- Tai nạn giao thông: Tìm người rời khỏi hiện trường dựa trên dáng đi và màu xe.
- Sự kiện đông người: Sau sự cố, lọc nhanh nghi phạm theo phụ kiện và tư thế đặc biệt.

---

## 12. Rủi ro và hạn chế đã lường trước

- Chiều cao và cân nặng chỉ là ước lượng tương đối, không tuyệt đối. Chúng tôi sử dụng khoảng hoặc phân cấp (thấp/trung bình/cao) thay vì số cm chính xác.
- Đồng bộ thời gian đòi hỏi người dùng chọn mốc tham chiếu thủ công nếu video không có cùng mốc giờ chính xác.
- Không xử lý real-time – sản phẩm là công cụ hậu kiểm (post-event), không phải hệ thống cảnh báo trực tiếp.
- Yêu cầu phần cứng: cần GPU (NVIDIA) để chạy nhanh nếu số lượng video lớn.

---

## 13. Bảo mật và quyền riêng tư

- Tất cả video và dữ liệu chỉ được lưu trên máy tính của điều tra viên (on-premise). Không gửi bất kỳ dữ liệu thô nào lên cloud.
- Mã nguồn có thể được công khai với giấy phép mã nguồn mở (MIT/Apache) sau khi phiên bản ổn định.
- Tuân thủ các quy định về quyền riêng tư và dữ liệu của quốc gia triển khai.

---

## 14. Đóng góp

Mọi đóng góp về ý tưởng, mã nguồn, tài liệu đều được chào đón. Hãy tạo issue hoặc pull request trên repository (sẽ công bố sau).

---

## 15. Liên hệ

*(Thông tin liên hệ của dự án sẽ được cập nhật sau.)*

---

**“AI không thay thế thám tử, AI là người bạn đồng hành giúp thám tử nhìn rõ hơn.”**