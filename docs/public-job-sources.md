# Đồng bộ tin thực tế — 29/09/2026

Lượt đồng bộ đầu tiên kiểm tra thành công 11 nguồn, thu được 666 tin Việt Nam còn được công khai: 657 tin mới và 9 tin cũ được xác nhận lại. Không sửa 187 bản ghi lịch sử ngoài Việt Nam. Chỉ mục discovery giữ metadata. Theo yêu cầu tiếp theo của người dùng, JD công khai được cập nhật riêng trong job_content.json; không lưu dữ liệu ứng viên.

| Doanh nghiệp | Nguồn / bảng | Tin Việt Nam tại lượt đầu |
|---|---|---:|
| Bosch Vietnam | SmartRecruiters / BoschGroup | 272 |
| Accor Vietnam | SmartRecruiters / AccorHotel | 114 |
| KMS Technology | SmartRecruiters / KMSTechnology1 | 9 |
| SGS Vietnam | SmartRecruiters / SGS | 136 |
| Eurofins Vietnam | SmartRecruiters / Eurofins | 100 |
| Renesas Electronics Vietnam | SmartRecruiters / RenesasElectronics | 15 |
| cargo-partner | Lever / cargo-partner | 10 |
| Ataccama | Lever / ataccama | 1 |
| Ninja Van | Lever / ninjavan | 2 |
| Lalamove | Lever / lalamove | 3 |
| Airwallex | Ashby / airwallex | 4 |

## Căn cứ và giới hạn sử dụng

Các URL bảng tuyển dụng và phản hồi API đã được đối chiếu trực tiếp. Chỉ mục dùng API công khai đã được nhà cung cấp mô tả để lưu các dữ kiện cơ bản: tiêu đề, doanh nghiệp, địa điểm, mã tin, URL gốc, loại hợp đồng/hình thức làm việc nếu có, thời điểm đăng nếu có và mốc kiểm tra.

- [Lever Postings API](https://github.com/lever/postings-api) mô tả phân trang, địa điểm bổ sung và nói rõ tin ở trạng thái published công khai, có thể được bên thứ ba thu thập.
- [SmartRecruiters Posting API](https://developers.smartrecruiters.com/docs/posting-api) mô tả truy cập các posting được công khai. [Endpoints](https://developers.smartrecruiters.com/docs/endpoints) mô tả danh sách tin active, country, limit, offset và totalFound. Bộ discovery gọi danh sách `country=vn`; bộ job_content gọi endpoint posting detail cho các mã tin Việt Nam đã phát hiện. Không gọi endpoint internal/applicant. URL tin gốc sử dụng đường dẫn jobs.smartrecruiters.com theo mã posting.
- [Ashby Job Postings API](https://developers.ashbyhq.com/docs/public-job-posting-api) mô tả danh sách published và isListed; không nhập các tin isListed=false. Bộ discovery bỏ JD; bộ job_content đọc các trường mô tả công khai cho đúng mã tin đã phát hiện.

Đây là căn cứ kỹ thuật cho chỉ mục metadata công khai theo phạm vi đã rà soát, KHÔNG phải thỏa thuận do doanh nghiệp cấp, chứng nhận pháp lý hay giấy phép tái xuất bản toàn bộ nội dung. `access_basis=reviewed_public_api_metadata`, `permission_mode=links`, `authorized=false`, `ai_authorized=false` phân biệt rõ phạm vi này. Tài liệu API không được trình bày như hợp đồng cấp phép. Nếu xuất hiện hạn chế áp dụng hoặc yêu cầu gỡ nguồn, tắt discovery_enabled của nguồn; lịch sử được giữ nguyên. Không đồng nhất URL công khai bất kỳ với quyền sao chép JD.

## Cập nhật và hết hạn

Workflow `discover_jobs.yml` dự kiến mỗi 6 giờ (~01:47, 07:47, 13:47, 19:47 giờ Việt Nam), có thể bị GitHub trì hoãn. Có thể chạy thủ công workflow khi cần. Không cam kết realtime tức thời.

Chỉ áp dụng snapshot khi phân trang đầy đủ. Sai schema, trang lặp, tổng SmartRecruiters đổi giữa lượt, mã quốc gia sai hoặc quá thời gian đều giữ dữ liệu nguồn cũ và báo lỗi. HTTP 401/403/429 không được thử vượt qua. Mốc last_seen chỉ thay đổi khi thấy tin; last_checked_at ghi lần kiểm tra thành công, kể cả khi không thấy.

Lần không thấy đầu tiên gắn trạng thái chờ xác nhận. Lần không thấy thứ hai cách ít nhất 6 giờ đánh dấu closed; thử lại ngay không tính là một lần độc lập. Tin xuất hiện lại được mở lại và tăng reopen_count. Tin quá 36 giờ chưa xác nhận có nhãn cần kiểm tra lại. Công khai tại nguồn không chứng minh nhà tuyển dụng vẫn nhận hồ sơ hoặc mọi tin evergreen là vị trí mới; người dùng xem tin gốc trước khi ứng tuyển.

Lịch sử chỉ thêm sự kiện khi metadata/trạng thái thay đổi, không nhân bản toàn bộ snapshot vì đồng hồ polling thay đổi. Dữ liệu ngoài Việt Nam được giữ nguyên. Những nguồn khác trong danh bạ chưa được kết nối không được tính vào 11 nguồn hoạt động.

## Thay đổi phạm vi theo yêu cầu người dùng 29/09
Người dùng yêu cầu hiển thị JD đầy đủ khi mở tin, thêm thông tin công việc và xếp hạng đối chiếu CV. public_description_enabled=true chỉ bật đọc nội dung posting công khai qua API của các nguồn đã kết nối; không biểu thị hợp đồng cấp quyền và không bật AI. JD được lưu riêng, kèm API URL, URL gốc và thời điểm lấy; HTML chuyển thành văn bản, loại script/style. Khi nguồn trả lỗi giữ bản trước và thời điểm trước; 401/403/429 dừng nguồn đó. CV không gửi ra ngoài.
