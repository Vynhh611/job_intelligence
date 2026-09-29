# Mở rộng nguồn tuyển dụng Việt Nam

Đợt danh bạ 28/09 có 261 mục, 141 liên kết tuyển dụng và 120 mục cần tìm hoặc xác minh nguồn. Đợt 29/09 bổ sung 5 đơn vị có tin thực tế, nâng danh bạ lên 266 mục và 146 liên kết. Đây không phải số doanh nghiệp cấp phép hay số pháp nhân độc lập. [Lượt đồng bộ thực tế](public-job-sources.md) đã lấy 666 tin Việt Nam từ 11 nguồn; số tin và số mục danh bạ là các chỉ tiêu riêng.

## Đợt mở rộng lên hơn 200 mục

`data/employer_expansion.tsv` là danh sách nghiên cứu thủ công, không phải danh sách được LinkedIn cung cấp. `directory_expansion.py` chỉ kiểm tra robots.txt và trang đầu của 223 website đề xuất, giới hạn 6 tác vụ đồng thời, HTTPS công khai, kích thước và thời gian mỗi yêu cầu; không theo chuyển hướng, không đọc JD. `data/employer_website_checks.json` lưu kết quả kiểm tra và các liên kết ứng viên, kể cả lỗi. Website trả lỗi hoặc không cho kiểm tra vẫn ở trạng thái chưa xác minh, không đồng nghĩa doanh nghiệp không tồn tại.

`scripts/merge_employer_expansion.py` chỉ đưa các liên kết đã rà soát trong danh sách chấp nhận vào danh bạ; không tự chọn mọi URL có chữ careers. Loại liên kết bán sách của Fahasa, liên kết mạng xã hội/bài thông báo đơn lẻ của Central, loại mục GCS Vietnam cần đối chiếu tên hiện tại và Trung Nguyên E-Coffee để giảm trùng nhóm. Thêm 17 nguồn tham chiếu tìm kiếm chính thức trong `data/directory_search_references.json`. Giữ nguyên mục cũ, dữ liệu Singapore và toàn bộ cấu hình quyền thu thập.

`homepage_checked` chỉ xác nhận đã đọc được website, không xác minh tư cách pháp nhân hay địa chỉ văn phòng Việt Nam. `official_homepage_link` ghi nhận đường dẫn tuyển dụng xuất hiện trên website đã đọc, không đảm bảo trang đích đang có vị trí mở. Các trang tuyển dụng toàn cầu cần lọc Vietnam. Trang chủ hiển thị riêng tổng tin, tổng danh bạ và số liên kết tuyển dụng; danh bạ có bộ lọc trạng thái nguồn và tìm kiếm không dấu.

## Bằng chứng và trạng thái

`data/employer_references_20260928.json` lưu danh sách bổ sung và nguồn tham chiếu. Danh bạ ứng dụng nằm trong `data/company_watchlist.json`; giữ nguyên các mục cũ và mục Singapore. `official_page_review` nghĩa là đã xem nội dung trang chính thức; `official_search_reference` chỉ đối chiếu được kết quả tìm kiếm trên tên miền chính thức. Ngày tham chiếu không phải ngày cập nhật việc làm. Chưa xác nhận liên kết LinkedIn cho mọi doanh nghiệp; chỉ hiện khi có URL và bằng chứng từ doanh nghiệp (hiện có Bosch Vietnam).

Đợt danh bạ ban đầu không bật nguồn. Đợt 29/09 ghi rõ `access_basis=reviewed_public_api_metadata` cho 11 bảng được kết nối trong `sources.json`; phạm vi chỉ là metadata và liên kết, `authorized=false` và AI tắt. Tài liệu API không phải thỏa thuận cấp phép của doanh nghiệp. Các nguồn khác vẫn cần rà soát; không tự cấp quyền JD chỉ vì có URL công khai. Có mặt trên LinkedIn không làm LinkedIn trở thành nguồn dữ liệu của tin lấy từ website doanh nghiệp.

## Tìm hiểu thỏa thuận LinkedIn

[Tài liệu Job Posting API chính thức](https://learn.microsoft.com/en-us/linkedin/talent/job-postings/api/overview) mô tả API đăng tin lên LinkedIn, không cung cấp bằng chứng về quyền tải toàn bộ tin tuyển dụng. Tài liệu hiện hướng đối tác mới sang Apply Connect và yêu cầu thỏa thuận API; không coi quyền đăng tin là quyền đọc hoặc tái xuất bản.

[Biểu mẫu đối tác ATS chính thức](https://business.linkedin.com/hire/ats-partners/partner-application) là kênh tìm hiểu tích hợp ATS được tài liệu dẫn chiếu, chưa xác nhận phù hợp với sản phẩm tổng hợp dữ liệu này. Nếu có đại diện kinh doanh LinkedIn, đề nghị họ xác nhận kênh cấp phép phù hợp. Chưa gửi biểu mẫu hoặc liên hệ thay chủ dự án.

Nội dung cần làm rõ với nhà cung cấp: dữ liệu tin tuyển dụng và doanh nghiệp tại Việt Nam; quyền đọc, lưu lịch sử, hiển thị công khai và phân tích; trường dữ liệu và giới hạn phủ; cách cập nhật/đóng tin; tần suất và hạn mức; yêu cầu ghi nguồn/xóa dữ liệu; quyền gửi JD đến nhà cung cấp AI; chi phí và thời hạn. Chỉ tích hợp sau khi có xác nhận phạm vi cụ thể. Không cam kết toàn bộ LinkedIn hoặc cập nhật tức thời.
