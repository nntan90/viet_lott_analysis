# 🎭 Trải Nghiệm Lịch Trình Tự Động Hóa (App Scenario)

Tài liệu này mô tả chi tiết dòng chảy sự kiện (Workflow) diễn ra hàng ngày của hệ thống **Vietlott AI Pipeline v4.0** (Nâng cấp Minh Chính) mà không cần bất kỳ sự can thiệp thủ công nào từ con người.

---

## 🕛 Khung Giờ 1: Thu Thập Dữ Liệu (22:00 Tối)
**Bối cảnh:** Vietlott vừa xổ số xong được vài tiếng. Dữ liệu trên hệ thống truyền thống đã xuất hiện trên trang `minhchinh.com`.

1. **GitHub Actions Đánh Thức:** Đúng 22:00 (Giờ VN - ICT), các Workflow `crawl_645`, `crawl_655`, hoặc `crawl_535` tự động khởi chạy.
2. **Kéo Dữ Liệu Nóng:** Hệ thống khởi động `BeautifulSoup`, chọc thẳng vào mã nguồn HTML tĩnh của `minhchinh.com`. Code tự động bóc tách các thẻ HTML chứa Bộ Số, Ngày Xổ, và đào sâu vào Link chi tiết để lấy chính xác Mã Kỳ Quay (`draw_id`).
   - Riêng đối với hệ **Lotto 5/35**, Crawler đủ thông minh để nhận thức và tách bạch 2 bản ghi `13h` và `21h` ngay trong ngày về 2 cụm Sáng/Tối (`AM`/`PM`).
3. **Cập Nhật Database:** Bộ số mới được thẩm định và lưu trữ gọn gàng vào Supabase Cloud (`lottery_results`).
4. **Báo Cáo Telegram:** Điện thoại của bạn rung lên một thông báo:
   > *"✅ [CRAWL] Power 6/55 — Kỳ #1311. Kết quả: 05 - 08 - 18 - 30 - 39 - 54 | Jackpot2: 51. Nguồn: minhchinh.com. SUCCESS."*

---

## 🔎 Khung Giờ 2: Dò Số & Trao Thưởng (22:30 Tối)
**Bối cảnh:** Nửa tiếng sau khi tất cả dữ liệu thô đã nằm an toàn trong Database, hệ thống cần biết bộ số mà AI đã tiên tri từ vài ngày trước hôm nay có trúng giải nào không.

1. **Khởi Chạy Cron Độc Lập:** Đúng 22:30 (Giờ VN - ICT), Workflow `check_results` bừng tỉnh. Nó không còn lệ thuộc Crawler mà lập trình tự tính toán Múi giờ để lọc đúng những kết quả diễn ra trong phần `"Hôm nay"`.
2. **Đối Chiếu Tiên Tri & Gộp Session:** Hệ thống lôi bộ số dự đoán đang Active của AI ra, so sánh từng con số. Tuyệt vời hơn, đối với nhánh **Lotto 5/35**, AI sẽ quét và báo cáo trọn gói cả 2 kết quả `AM` (Trưa) và `PM` (Tối) cùng một lượt.
3. **Chốt Kết Quả & Update DB:** Lưu lại số vạch trúng, số lượng trùng khớp, và hạng giải đạt được (VD: `PRIZE_3`, `JACKPOT_2`...) vào bảng `match_results`.
4. **Báo Cáo Telegram:** Bạn nhận được thông báo thứ hai:
   > *"✅ [DÒ] Power 6/55 — Lần dò 3/5. Bộ số AI dự đoán vs Kết quả thực tế. Trùng: 08, 18, 30 → ✨ 3/6 số (Giải 3). Lịch sử 3 lần dò gần nhất... Còn 2 lần chờ xổ nữa."*

---

## 🤖 Khung Giờ 3: Khởi Tạo Chu Kỳ Dự Đoán Mới (Nối Tiếp Tức Thì)
**Bối cảnh:** Nếu chu kỳ dự đoán trước đó đã xài hết (Thường là 5 lần dò, riêng 5/35 là 10 lần dò do quay 2 buổi/ngày) hoặc bạn vừa xoá dữ liệu cũ, AI tích hợp bộ Trọng số thông minh đưa ra *lời sấm truyền* mới.

1. **Khởi Động Mô Hình:** Workflow `manage_cycle` bắt đầu chạy. Nó tự lấy thông số AI hiệu chỉnh số Max Draws độ dài (VD: AI dự đoán tốt thì giữ nguyên 10 vòng, đoán kém thì chủ động hạ xuống 6 vòng để mau Reset).
2. **Phân Tích Dữ Liệu Khổng Lồ:** AI load hàng trăm kết quả lịch sử gần nhất, kết hợp các thuật toán Tần số (Frequency), Độ giãn cách (Gap), và Vị trí (Position Bias) để tìm ra quy luật ẩn.
3. **Tiên Tri Chốt Số:** Hệ thống trí tuệ *Ensemble* chốt hạ bộ số có xác suất nổ cao nhất trong chu kỳ tới.
4. **Bảo Lưu Kết Quả:** Chu kỳ mới (`prediction_cycles`) được lập, bộ số tiên tri được khoá vào DB chờ dò lô.
5. **Báo Cáo Telegram:** Lời dự báo xuất hiện trên nhóm chat:
   > *"🎯 [GENERATE] Lời sấm truyền kỳ mới: 08 - 12 - 25 - 34 - 42 - 50. Sinh Tồn: 10 kỳ tiếp theo. Trọng số: LSTM 40% | XGB 35% | Stat 25%."*

---

## 📈 Tác Vụ Cuối Tuần: Hội Đồng Đánh Giá AI (Rạng Sáng Chủ Nhật)
**Bối cảnh:** Sau một tuần (vài chu kỳ dự đoán), AI tự nhìn lại bản thân xem dạo này "đoán có linh không" để quyết định gọi Kaggle siêu máy tính đào tạo lại (Retrain) trọng số thuật toán.

1. **Kiểm Soát Chất Lượng:** Workflow `retrain_evaluation` định kỳ đánh giá kho tàng `match_results`.
2. **Phân Tích Hiệu Suất:** Tính toán số lần trúng lớn hơn hoặc bằng mức chuẩn (Ví dụ: trúng 3 số trở lên).
3. **Báo Động Đỏ & Gửi Lệnh Kaggle:** Nếu thành tích tụt giảm bất thường, hệ thống thông báo báo động đỏ lên Telegram và Trigger API sang cụm máy chủ Telsa GPU P100 của Kaggle để huấn luyện lại Model.
4. **Nâng Cấp Thông Minh (Auto Deploy):** Model mới học xong từ Kaggle sẽ được tự động Push thẳng lên kho Supabase đè phiên bản cũ (VD: v4 → v5). Kể từ lúc này AI chốt số bằng "Bộ não" xịn hơn.

---

## 💡 Tổng Kết Dành Cho Bạn (Người Quản Trị)
✔️ **Zero-Touch:** Bạn không cần phải treo máy tính, không mở Browser, không can thiệp thủ công.  
✔️ **An Nhàn:** Bạn chỉ việc... đi ngủ. Mở mắt thức dậy, mở Telegram lên xem tối hôm qua AI cào KQXS gì, dò trúng giải mấy, có tự sinh Chu kỳ 10 vòng nào mới không.  
✔️ **100% Cloud-Native:** Mọi cấu phần từ Database (Supabase), Storage (GCP), cho đến Bot (Github Actions, Kaggle) đều tự trị vĩnh viễn và bảo mật trên nền tảng Đám Mây Đặt Miễn Phí.
