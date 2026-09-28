# Job Intelligence Vietnam

Nền tảng nghiên cứu nghề nghiệp bằng Streamlit, giao diện tiếng Việt xanh lá nhạt. Giữ nguyên điểm vào `app.py`, kho dữ liệu JSON và lịch GitHub Actions. Không tạo việc làm, đánh giá doanh nghiệp hay mức lương giả.

## Chạy và kiểm thử

Python 3.12 trở lên:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
python -m unittest discover -s tests -v
python collector.py --dry-run
```

Trên máy này thư viện kiểm thử được cài riêng vào `.runtime` (không đưa lên Git). PowerShell:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) '.runtime'
python -m streamlit run app.py --global.developmentMode false
```

## Các chức năng

- Tìm kiếm chức danh, công ty, chức năng và kỹ năng; lọc địa điểm, ngành doanh nghiệp, kinh nghiệm, ngôn ngữ, hợp đồng, hình thức làm việc, thời điểm phát hiện, công bố lương. Có phân trang và xuất CSV chống công thức độc hại.
- Chỉ hiển thị Việt Nam. Tin Singapore/Taiwan trong lịch sử không bị xóa hoặc đổi trạng thái vì thay đổi phạm vi.
- Hồ sơ công việc hai cột, `?job=<id>`, nhiệm vụ và yêu cầu trích từ JD, dẫn chứng kỹ năng, lương công bố, nguồn, thời điểm phát hiện/kiểm tra, lưu trong phiên, đường dẫn ứng tuyển.
- Danh bạ doanh nghiệp, thông tin đã có nguồn, lịch sử tuyển dụng, số tin công bố lương. Chưa có đánh giá nhân viên được cấp quyền.
- CV PDF/DOCX trong bộ nhớ, tối đa 5 MB; PDF tối đa 30 trang, DOCX giải nén tối đa 20 MB. Không ghi CV, không log nội dung, không gửi AI. Có nút xóa khỏi phiên. Không OCR.
- Đối chiếu kỹ năng ba nhóm có câu JD/CV và gợi ý bổ sung. “Đáp ứng” chỉ nghĩa có câu mô tả áp dụng kỹ năng, chưa xác minh năng lực, mức thành thạo, số năm hay học vấn. Không dùng điểm tuyển dụng.
- Lộ trình minh họa cho tám nhóm nghề, so sánh kỹ năng từ tin hiện có. Không hứa hẹn thăng tiến.
- Thống kê có phạm vi, kỳ quan sát và ngày cập nhật. Dưới 20 tin không hiện biểu đồ. Tin mới nghĩa là lần đầu hệ thống thấy, không chắc là ngày nhà tuyển dụng đăng.

## Quản trị nguồn không sửa Python/JSON

Đặt `JOB_ADMIN_PASSWORD` bằng biến môi trường hoặc Streamlit Secrets. Không commit mật khẩu. Mở **Quản trị nguồn**:

1. Thêm tên doanh nghiệp và URL ATS chính thức. Hỗ trợ nhận diện Greenhouse, Lever, Ashby, SmartRecruiters.
2. Nguồn mới mặc định tắt. Chỉ tích kích hoạt sau khi xác minh quyền lưu và công bố dữ liệu, kèm URL bằng chứng. Kết nối API công khai không đồng nghĩa được phép tái sử dụng.
3. Muốn sửa hoặc tắt nguồn, nhập lại cùng URL board và lưu trạng thái mới.
4. Có thể thêm bất kỳ doanh nghiệp/ngành nào vào danh sách chờ xác minh bằng URL tuyển dụng chính thức. Danh sách không bị giới hạn số doanh nghiệp cố định.
5. Xem lần chạy, số tin, lỗi từng nguồn và báo cáo kiểm tra kết nối.

**Lưu ý triển khai:** cấu hình thay đổi trên giao diện được lưu ở máy đang chạy ứng dụng. Streamlit Cloud không đồng bộ ngược về GitHub và có thể mất thay đổi khi redeploy. Nếu dùng JSON, dùng nút tải `sources.json` để đưa cấu hình đã duyệt vào repo; không cần sửa JSON thủ công. Nên chỉ có một quản trị viên ghi cấu hình tại một thời điểm trong phiên bản lưu bằng tệp này.

Nguồn đầy đủ dùng `authorized=true`; chỉ mục liên kết dùng `discovery_enabled=true`, mặc định false khi chưa có trường này. Quản trị cho phép chọn riêng phạm vi chỉ liên kết hoặc JD đầy đủ; quyền xử lý AI là một lựa chọn riêng. SmartRecruiters được xử lý qua bộ thu thập JD, không qua chỉ mục liên kết.

## Thu thập & lịch sử

- `collector.py`: Greenhouse, Lever, Ashby, SmartRecruiters; chỉ nguồn có quyền mới chạy.
- `collectors/transport.py`: phân trang Lever, phát hiện trang lặp hoặc phản hồi sai, từ chối coi phản hồi thiếu là danh sách rỗng.
- `collectors/smartrecruiters.py`: Posting API có phân trang và nội dung chi tiết Việt Nam.
- `discovery_collector.py`: chỉ lưu metadata/liên kết, không JD; cũng phải bật quyền rõ ràng.
- Retry/timeout, nhịp nghỉ request; đóng tin sau hai lần kiểm tra thành công liên tiếp không thấy tin. Lỗi request không làm đóng tin.
- `data/history.json` và `data/discovery_history.json` lưu phiên bản trước khi đổi. Không cắt lịch sử còn 30.000 bản ghi như trước.
- Loại trùng chỉ với URL đồng nhất, bỏ tham số tracking nhưng giữ mã tin trong query. Không tự gộp hai tin chỉ vì cùng tên/vị trí.
- Ghi JSON qua tệp tạm rồi đổi tên. Cấu hình cũ tự được sao lưu trước khi lưu nguồn trên giao diện.

Workflow giữ lịch cũ: thu thập JD khoảng 07:17 và liên kết khoảng 07:47 giờ Việt Nam. Các workflow ghi dữ liệu dùng chung khóa chạy để tránh xung đột. CI kiểm thử khi sửa mã/PR. Lịch GitHub có thể trễ. Quyền repository Contents: write cần được cho phép để workflow commit dữ liệu.

Tài liệu API tham khảo: [Lever public Postings API](https://github.com/lever/postings-api), [SmartRecruiters Posting endpoints](https://developers.smartrecruiters.com/docs/endpoints). Không tự động bật nguồn chỉ vì API trả về thành công.

## Dữ liệu và quyền còn thiếu

Đã đồng bộ dữ liệu từ GitHub: 196 liên kết lịch sử, trong đó 9 tin Việt Nam được hiển thị trong phạm vi sản phẩm mới. Chưa có JD đầy đủ; tất cả nguồn JD vẫn `authorized=false`. Quyền nguồn chưa được xác nhận, nên không tự bật thu thập mới. Không chèn dữ liệu kiểm thử vào sản phẩm.

- LinkedIn, VietnamWorks, TopCV, CareerViet, ITviec, Vieclam24h, Glints: cần hợp đồng/feed/API được phép. Chưa có adapter live cho những nền tảng này.
- Workday và các portal riêng: chưa có adapter được xác minh. Có thể lưu trang chính thức trong danh bạ chờ tích hợp.
- Phát hiện ATS tự động từ trang tuyển dụng trong danh bạ đã được bật kiểm tra; chưa khám phá doanh nghiệp diện rộng trên Internet. Không vượt CAPTCHA/login hay tự bật nguồn chưa duyệt.
- Đã có adapter diễn giải JD bằng OpenAI, chỉ hoạt động khi cấu hình khóa/model và nguồn có quyền xử lý bên ngoài. Hiện chưa bật; phần trích xuất giữ nguyên ngôn ngữ gốc.
- Chưa có dữ liệu lương thị trường được cấp quyền để ước tính. Có lọc khoảng lương công bố khi tiền tệ/kỳ trả được xác định; tin thiếu thông tin này không được tự suy đoán.
- Mặc định JSON/Git; đã có backend PostgreSQL tùy chọn với lịch sử và kiểm tra phiên bản. Chưa cấu hình máy chủ thật để di trú hoặc xác minh kết nối production; xem hướng dẫn bên dưới.
- Bộ phân loại kỹ năng/quốc gia dựa từ khóa không bao phủ mọi nghề/địa danh. Dữ liệu thiếu giữ “Chưa công bố”, không suy luận chắc chắn.

## Triển khai vào repo hiện có

Giữ cấu hình Streamlit trỏ đến `app.py`; commit/push mã đã kiểm thử vào nhánh triển khai hiện có. Không cần tạo dự án mới. Thiết lập secret quản trị và cấu hình nguồn có quyền trước khi kỳ vọng có việc làm thực. Sau khi cấu hình nguồn trong repo, chạy workflow và kiểm tra bảng sức khỏe nguồn. Chưa thực thi GitHub Actions từ xa trong lần sửa cục bộ này.

Bản sao trước khi sửa nằm tại `backups/before-vietnam-*`, được Git bỏ qua; không xóa khi chưa kiểm tra. Dữ liệu và cấu hình nguồn gốc được giữ nguyên. Các tài liệu `README_START_HERE.md` và `README_SOURCE_PACK.md` là tài liệu phiên bản cũ; README này mô tả hành vi hiện tại.

Các hợp đồng tích hợp ở integrations.py dành cho feed được cấp phép và dịch vụ diễn giải JD; mặc định từ chối gọi nếu chưa được cấp quyền, kiểm tra dẫn chứng trả về, không nhận CV. Đã có adapter OpenAI tùy chọn, mặc định tắt; chưa cấu hình tài khoản để gọi thật.
## Bổ sung vận hành: nguồn chờ duyệt, AI và PostgreSQL

### Quyền nguồn

Quản trị hiện có danh sách chọn nguồn để sửa trực tiếp và hai phạm vi quyền: chỉ metadata/liên kết hoặc JD đầy đủ. Quyền xử lý JD bằng OpenAI là một lựa chọn riêng, mặc định tắt. Người dùng xác nhận hiện **chưa có nguồn được cấp quyền**, do đó không kích hoạt nguồn nào trong lần nâng cấp này.

### Phát hiện ATS có kiểm soát

`source_discovery.py` nhận diện ATS từ URL trong danh bạ hoặc tìm liên kết ATS trên trang tuyển dụng chính thức. Trang web chỉ được truy cập khi doanh nghiệp có `page_discovery_enabled=true`; kiểm tra robots.txt, giới hạn 1 MB, từ chối redirect và địa chỉ nội bộ. Không tự khám phá toàn bộ Internet, không thu thập JD và không tự bật nguồn. Kết quả nằm trong `data/source_candidates.json` để quản trị xét duyệt.

```sh
python source_discovery.py --offline
python source_discovery.py
```

Lệnh offline chỉ kiểm tra các URL đã có trong danh bạ, không gọi Internet. Workflow `Discover candidate ATS sources` chạy sáng thứ Hai, tối đa 10 trang được bật mỗi lần. Nguồn chưa được phép kiểm tra không bị truy cập. Đây là phát hiện ATS từ danh bạ do quản trị cung cấp, chưa phải công cụ tìm doanh nghiệp mới trên toàn Internet.

### PostgreSQL tùy chọn

Đã có backend PostgreSQL chạy cùng giao diện website và hai collector. Mặc định vẫn JSON. Backend dùng tài liệu JSONB có phiên bản và lịch sử, chưa chuẩn hóa thành bảng riêng cho mọi trường việc làm. Giao dịch theo từng tài liệu; chưa có giao dịch nguyên tử bao trùm toàn bộ một đợt thu thập. Các workflow ghi dữ liệu vẫn được chạy lần lượt để tránh xung đột.

1. Chuẩn bị PostgreSQL của bạn, lưu `DATABASE_URL` trong biến môi trường máy chạy di trú. Không đặt URI chứa mật khẩu trong lệnh hoặc kho mã.
2. Cài `requirements.txt` (đã gồm psycopg).
3. Chạy `python migrate_storage.py` để xem danh sách nhập; `python migrate_storage.py --apply` tạo schema và nhập **chỉ các tài liệu chưa có**. Không ghi đè dữ liệu sẵn có trong PostgreSQL, không xóa JSON gốc. Có thể chạy lại an toàn sau khi nhập bị gián đoạn.
4. Đặt cùng `DATABASE_URL` vào Streamlit Secrets và GitHub repository Actions Secret. Khi đó thay đổi quản trị được collector nhìn thấy qua cơ sở dữ liệu dùng chung, không cần tải rồi chép cấu hình thủ công.
5. Sao lưu: `python migrate_storage.py --export-dir backups/postgres-export-new`. Thư mục đích phải chưa tồn tại; không ghi đè tệp dự án.

Kết nối lỗi sẽ dừng thay vì âm thầm dùng kho JSON khác. Lỗi không in URI hay mật khẩu. Kiểm thử SQL dùng mô phỏng kết nối; **chưa có máy chủ PostgreSQL để xác minh tích hợp thật**.

### Diễn giải JD tiếng Việt bằng OpenAI

Adapter thực tế ở `ai_explainer.py`, dùng Responses API với JSON Schema, `store=false`, giới hạn đầu vào/đầu ra và timeout. Tùy chọn này không có retry tự động để tránh tạo thêm phí không mong muốn. CV không nằm trong hợp đồng đầu vào, không được gửi đến API.

- Thiết lập `OPENAI_API_KEY`, `OPENAI_MODEL`, `JOB_AI_ENABLED=true` trong Streamlit Secrets. Chọn model hỗ trợ Structured Outputs mà tài khoản của bạn được phép dùng; không có model tự chọn mặc định.
- Nguồn phải có cả quyền lưu JD và quyền xử lý JD bên ngoài (`ai_authorized=true`). Chỉ quản trị viên đã đăng nhập có nút tạo nội dung.
- Kết quả chỉ được lưu khi hoàn tất và từng ý có đoạn trích đúng trong JD. Kiểm tra đoạn trích không bảo đảm diễn giải luôn đúng nghĩa; giao diện công khai nhắc người đọc kiểm tra bản gốc. Không có review của con người được giả định.
- Bản diễn giải gắn hash JD, tự ẩn khi mô tả thay đổi. Không bật cho mọi lượt xem để tránh phát sinh phí không kiểm soát.
- Không có khóa API trong môi trường hiện tại; đã kiểm thử hợp đồng bằng phản hồi mô phỏng, chưa gọi dịch vụ thật.

Tài liệu: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses), [psycopg](https://www.psycopg.org/psycopg3/docs/basic/usage.html).

### Lương công bố

Có bộ lọc lương VND/USD theo tháng khi trường cấu trúc hoặc nội dung công bố chứa đủ khoảng lương, tiền tệ và kỳ trả. Không tự quy đổi USD/VND, không suy luận lương năm thành tháng, không đoán gross/net. Chưa có mô hình ước tính lương thị trường.
