# Mở rộng nguồn tuyển dụng Việt Nam

Đợt đối chiếu ngày 28/09/2026 bổ sung 20 doanh nghiệp vào danh bạ, nâng tổng số mục Việt Nam lên 40. Đây là số mục tham khảo, không phải số doanh nghiệp đã cấp quyền, số nguồn realtime hay số pháp nhân độc lập đã kiểm toán. Các tập đoàn và đơn vị thành viên có thể cùng xuất hiện.

## Bằng chứng và trạng thái

`data/employer_references_20260928.json` lưu danh sách bổ sung và nguồn tham chiếu. Danh bạ ứng dụng nằm trong `data/company_watchlist.json`; giữ nguyên các mục cũ và mục Singapore. `official_page_review` nghĩa là đã xem nội dung trang chính thức; `official_search_reference` chỉ đối chiếu được kết quả tìm kiếm trên tên miền chính thức. Ngày tham chiếu không phải ngày cập nhật việc làm. Chưa xác nhận liên kết LinkedIn cho mọi doanh nghiệp; chỉ hiện khi có URL và bằng chứng từ doanh nghiệp (hiện có Bosch Vietnam).

Mọi nguồn bổ sung có `rights_status=unreviewed` và `page_discovery_enabled=false`. Không thay đổi `sources.json`, không tự cấp quyền thu thập, không sao chép JD. Danh bạ cung cấp đường dẫn để người dùng xem và ứng tuyển tại nguồn. Khi nguồn được duyệt, ghi nhận riêng phạm vi cho phép lưu, hiển thị lại, tần suất, thời hạn và xử lý bằng AI; sau đó cấu hình bộ thu thập thích hợp trong quản trị. Có mặt trên LinkedIn không làm LinkedIn trở thành nguồn dữ liệu của tin lấy từ website doanh nghiệp.

## Tìm hiểu thỏa thuận LinkedIn

[Tài liệu Job Posting API chính thức](https://learn.microsoft.com/en-us/linkedin/talent/job-postings/api/overview) mô tả API đăng tin lên LinkedIn, không cung cấp bằng chứng về quyền tải toàn bộ tin tuyển dụng. Tài liệu hiện hướng đối tác mới sang Apply Connect và yêu cầu thỏa thuận API; không coi quyền đăng tin là quyền đọc hoặc tái xuất bản.

[Biểu mẫu đối tác ATS chính thức](https://business.linkedin.com/hire/ats-partners/partner-application) là kênh tìm hiểu tích hợp ATS được tài liệu dẫn chiếu, chưa xác nhận phù hợp với sản phẩm tổng hợp dữ liệu này. Nếu có đại diện kinh doanh LinkedIn, đề nghị họ xác nhận kênh cấp phép phù hợp. Chưa gửi biểu mẫu hoặc liên hệ thay chủ dự án.

Nội dung cần làm rõ với nhà cung cấp: dữ liệu tin tuyển dụng và doanh nghiệp tại Việt Nam; quyền đọc, lưu lịch sử, hiển thị công khai và phân tích; trường dữ liệu và giới hạn phủ; cách cập nhật/đóng tin; tần suất và hạn mức; yêu cầu ghi nguồn/xóa dữ liệu; quyền gửi JD đến nhà cung cấp AI; chi phí và thời hạn. Chỉ tích hợp sau khi có xác nhận phạm vi cụ thể. Không cam kết toàn bộ LinkedIn hoặc cập nhật tức thời.
