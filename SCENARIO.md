# 🎭 Trải Nghiệm Lịch Trình Tự Động Hóa (App Scenario)

Tài liệu này mô tả chi tiết dòng chảy sự kiện (Workflow) diễn ra hàng ngày của hệ thống **Vietlott AI Pipeline v4.0** mà không cần bất kỳ sự can thiệp thủ công nào từ con người.

---

## 🕛 Khung Giờ 1: Thu Thập Dữ Liệu (00:15 Sáng)
**Bối cảnh:** Vietlott đã quay thưởng xong từ chiều tối hôm trước. Nguồn dữ liệu thứ ba (`vietvudanh/vietlott-data`) vừa tổng hợp và đẩy file JSONL mới nhất lên GitHub lúc 00:00.

1. **GitHub Actions Đánh Thức:** Đúng 00:15 (Giờ VN), các Workflow `crawl_645`, `crawl_655`, hoặc `crawl_535` tự động khởi chạy.
2. **Kéo Dữ Liệu Xuyên Màn Đêm:** Hệ thống tải file dữ liệu JSONL mới nhất về, Parse ra bộ số và giải thưởng. Quá trình này hoàn toàn **bỏ qua giao diện Web chậm chạp** và **vượt mặt lớp bảo vệ Cloudflare** của trang chủ Vietlott.
3. **Cập Nhật Database:** Bộ số mới được lưu trữ gọn gàng vào Supabase Cloud (`lottery_results`).
4. **Báo Cáo Telegram:** Điện thoại của bạn rung lên một thông báo:
   > *"✅ [CRAWL] Power 6/55 — Kỳ #1000. Kết quả: 01 - 04 - 15 - 22 - 34 - 45 | Jackpot2: 50. Nguồn: vietvudanh/vietlott-data. SUCCESS."*

---

## 🔎 Khung Giờ 2: Dò Số & Trao Thưởng (Ngay Lập Tức)
**Bối cảnh:** Ngay khi dữ liệu mới được cắm vào DB thành công, hệ thống cần biết bộ số mà AI đã tiên tri từ vài ngày trước hôm nay có trúng giải nào không.

1. **Kích Hoạt Dây Chuyền:** Workflow `check_results` được "đánh thức" tự động nhờ cơ chế chuỗi `workflow_run` bắt tín hiệu từ Crawler.
2. **Đối Chiếu Tiên Tri:** Hệ thống lôi bộ số dự đoán đang Active của AI ra, so sánh từng con số với kết quả vừa Crawl được.
3. **Chốt Kết Quả & Update DB:** Lưu lại số vạch trúng, số lượng trùng khớp, và hạng giải đạt được (VD: `PRIZE_3`, `JACKPOT_2`...) vào bảng `match_results`.
4. **Báo Cáo Telegram:** Bạn nhận được thông báo thứ hai:
   > *"✅ [DÒ] Power 6/55 — Lần dò 3/5. Bộ số AI dự đoán vs Kết quả thực tế. Trùng: 04, 15, 34 → ✨ 3/6 số (Giải 3). Lịch sử 3 lần dò gần nhất... Còn 2 lần chờ xổ nữa."*

---

## 🤖 Khung Giờ 3: Khởi Tạo Chu Kỳ Dự Đoán Mới (Nối Tiếp Tức Thì)
**Bối cảnh:** Nếu chu kỳ dự đoán trước đó đã xài hết (quá 5 lần dò) hoặc bạn vừa xoá dữ liệu cũ, AI cần đưa ra *lời sấm truyền* mới cho 5 kỳ tiếp theo.

1. **Khởi Động Mô Hình:** Workflow `manage_cycle` bắt đầu chạy. Nó tự tải bộ AI Weights (LSTM, XGBoost) từ Supabase Storage xuống bộ nhớ.
2. **Phân Tích Dữ Liệu Khổng Lồ:** AI load hàng trăm kết quả lịch sử gần nhất, kết hợp các thuật toán Tần số (Frequency), Độ giãn cách (Gap), và Vị trí (Position Bias) để tìm ra quy luật ẩn.
3. **Tiên Tri Chốt Số:** Hệ thống trí tuệ *Ensemble* chốt hạ 6 con số (hoặc 5 số + 1 Đặc biệt đối với Lotto 5/35) có xác suất nổ cao nhất trong 5 vòng xổ kế tiếp.
4. **Bảo Lưu Kết Quả:** Chu kỳ mới (`prediction_cycles`) được lập, bộ số tiên tri được khoá vào DB chờ dò lô.
5. **Báo Cáo Telegram:** Lời dự báo xuất hiện trên nhóm chat:
   > *"🎯 [GENERATE] Lời sấm truyền kỳ mới: 08 - 12 - 25 - 34 - 42 - 50. Dò với 5 kỳ tiếp theo. Trọng số: LSTM 40% | XGB 35% | Stat 25%."*

---

## 📈 Tác Vụ Cuối Tuần: Hội Đồng Đánh Giá AI (01:00 Sáng Thứ 2)
**Bối cảnh:** Sau một tuần (khoảng 2-3 chu kỳ dự đoán), AI tự nhìn lại bản thân xem dạo này "đoán có linh không" để quyết định gọi Kaggle siêu máy tính đào tạo lại (Retrain).

1. **Kiểm Soát Chất Lượng:** Workflow `retrain_evaluation` tự động chạy hàng tuần vào rạng sáng.
2. **Phân Tích Hiệu Suất:** Tính toán số lần trúng lớn hơn hoặc bằng mức chuẩn (Ví dụ: trúng 3 số trở lên).
3. **Báo Động Đỏ & Gửi Lệnh Kaggle:** Nếu thành tích tụt giảm bất thường, hệ thống thông báo lên Telegram: *"⚠️ RETRAIN TRIGGERED. Lý do: Accuracy tụt giảm."*. Sau đó gọi Trigger API sang Kaggle để khởi động cụm máy chủ GPU đào tạo Model mới mất khoảng 30 phút.
4. **Nâng Cấp Thông Minh (Auto Deploy):** Model mới học xong từ Kaggle sẽ được tự động Push thẳng lên Supabase đè phiên bản cũ (VD: v4 → v5). Kể từ chu kỳ sau, AI sẽ bắt đầu chốt số với "bộ não" đã được tinh chỉnh mới nhất toàn tinh túy năm 2026.

---

## 💡 Tổng Kết Dành Cho Bạn (Người Quản Trị)
✔️ **Zero-Touch:** Bạn không cần phải treo máy tính, không cần mở Browser, không can thiệp thủ công.  
✔️ **An Nhàn:** Bạn chỉ việc... đi ngủ. Sáng mờ mắt thức dậy, mở Telegram lên xem tối hôm qua AI đã tự thu thập kết quả gì, dò ra mấy nháy, trúng giải mấy, và nó định đánh thế nào cho các ngày tới.  
✔️ **100% Cloud-Native:** Mọi cấu phần từ Database, Storage, cho đến các Bot chạy Pipeline đều an vị vĩnh viễn và bảo mật trên nền tảng Đám Mây Đặt Miễn Phí (Github Actions, Supabase, Kaggle).
