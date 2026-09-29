# Tiếp tục Job Intelligence Vietnam — 29/09/2026

## Mục tiêu
Ưu tiên TIN TUYỂN DỤNG THỰC TẾ, có lịch cập nhật và kiểm tra hết hạn. Không lấy số mục danh bạ thay cho số nguồn đã kết nối. Người dùng muốn phủ 200–500 doanh nghiệp, chấp nhận trang tuyển dụng chính thức thay LinkedIn. Giữ giao diện xanh lá nhạt, tiếng Việt và dữ liệu hiện có.

## Hiện trạng mới
- Repo: C:/Users/admin/OneDrive/Documents/GitHub/job_intelligence ; GitHub https://github.com/Vynhh611/job_intelligence ; nhánh main.
- Website: https://job-intelligence-asia.streamlit.app/ ; điểm vào app.py.
- Lượt 29/09: 666 tin Việt Nam từ 11 nguồn thành công, gồm 657 tin mới và 9 tin cũ được xác nhận lại. Giữ nguyên 187 bản ghi ngoài Việt Nam. Đây là snapshot; xem data/discovery_status.json khi tiếp tục.
- SmartRecruiters: Bosch Vietnam 272, Accor Vietnam 114, KMS Technology 9, SGS Vietnam 136, Eurofins Vietnam 100, Renesas Electronics Vietnam 15.
- Lever: Ninja Van 2, Lalamove 3, cargo-partner 10, Ataccama 1. Ashby: Airwallex 4.
- Danh bạ 266 mục doanh nghiệp/đơn vị/thương hiệu, 146 liên kết tuyển dụng, 120 mục cần tìm hoặc xác minh. Chỉ 11 nguồn kết nối, chưa phủ việc làm 200–500 doanh nghiệp.
- Cập nhật theo yêu cầu người dùng 29/09: bổ sung JD công khai trong data/job_content.json qua job_content.py, tách khỏi chỉ mục metadata; không dữ liệu ứng viên. authorized=false và ai_authorized=false. discovery_enabled=true có access_basis=reviewed_public_api_metadata và tài liệu API. Không coi tài liệu API là hợp đồng cấp phép của doanh nghiệp. Người dùng chưa có hợp đồng dữ liệu riêng. Đọc docs/public-job-sources.md.
- Kiểm tra một URL tin mỗi nguồn: 11/11 HTTP 200. Tin đang public không đảm bảo HR còn nhận hồ sơ.
- Workflow discover_jobs.yml dự kiến mỗi 6 giờ (GitHub có thể trễ). Hai lần không thấy cách ít nhất 6 giờ mới đóng. Lần mất đầu và quá 36 giờ chưa xác nhận có nhãn. Lỗi/thiếu trang/sai schema giữ snapshot cũ; xuất hiện lại thì mở lại.
- Đã giữ commit b4fdff7 (Dev Container) từ remote. Lấy hash triển khai mới nhất bằng git log và CI, không dùng hash bàn giao cũ.

## Tiếp tục
1. Kiểm tra trạng thái nguồn, website và workflow thực tế. Mở rộng nguồn có thể dùng theo ngành/doanh nghiệp, ưu tiên thêm tin thật.
2. Ghi căn cứ, phạm vi sử dụng cho từng nguồn. JD công khai đã được người dùng yêu cầu hiển thị và đối chiếu tại chỗ; public_description_enabled là cấu hình riêng, không phải giấy phép hợp đồng. Không tự bật AI, không vượt CAPTCHA/login/hạn chế; nguồn chưa dùng được phải có lý do cụ thể.
3. Không gửi email/biểu mẫu hoặc mua dịch vụ nếu chưa được yêu cầu. Không tạo tin giả, không khẳng định toàn bộ doanh nghiệp trong danh bạ đã được kết nối.
4. Đối chiếu dữ liệu cũ và Git/remote trước khi đẩy; duy trì dữ liệu Singapore và những thay đổi của người dùng.

## Thành phần
- discovery_collector.py, collectors/transport.py: metadata, phân trang, đóng/mở lại và lịch sử.
- freshness.py, app.py: trạng thái, nguồn, giờ Việt Nam.
- sources.json: cấu hình thật; scripts/connect_public_boards.py là bootstrap có kiểm soát, giữ thay đổi operator về sau.
- data/discovered_jobs.json, discovery_status.json, discovery_history.json: tin và lịch sử.
- collector.py: JD có quyền riêng. source_discovery.py: phát hiện ATS opt-in, không tự bật nguồn.
- docs/public-job-sources.md: căn cứ và số liệu. docs/data-partnerships.md: danh bạ/LinkedIn, chưa liên hệ.
- storage.py: JSON mặc định, PostgreSQL tùy chọn chưa cấu hình thật. AI chưa bật. CV chỉ trong bộ nhớ phiên.

## Vận hành
PowerShell, thư viện trong .runtime. Đặt PYTHONPATH tới .runtime rồi chạy python -m unittest discover -s tests -v và python discovery_collector.py. Công cụ có thể cần quyền đọc runtime/mạng. Git mạng dùng C:/Users/admin/AppData/Local/GitHubDesktop/app-3.6.6/resources/app/git/cmd/git.exe. Không in thông tin xác thực.

Đã có luồng cập nhật website qua main. Không chạy lại dò toàn cầu TSMG lớn; phân trang có giới hạn thời gian. Không giả định tab trình duyệt/tiến trình local còn tồn tại. Đối chiếu kết quả kiểm tra, dữ liệu và CI mới nhất trước khi tiếp tục.

## Trải nghiệm JD / địa điểm / CV (29/09)
- job_content.py lấy các mục JD từ API công khai của 11 nguồn đã kết nối. Workflow chạy sau discovery; lỗi giữ bản JD cũ và fetched_at cũ. Không thay authorized/ai_authorized thành true.
- locations.py chuẩn hóa bí danh Hà Nội, TP.HCM và các địa điểm; giữ source_location để xem địa chỉ gốc, tách địa điểm đa thành phố trong bộ lọc.
- services.rank_jobs: xếp hạng từ khóa/kỹ năng có thể giải thích, không dự đoán trúng tuyển. CV chỉ trong bộ nhớ phiên. Tìm kiếm luôn có, 12 tin mỗi trang, JD thiếu không được chấm 0 giả.
- Trang chi tiết hiển thị đầy đủ các section từ nguồn trước phần trích xuất; phòng ban, kinh nghiệm, hợp đồng, ngày đăng, địa chỉ gốc nếu có.
