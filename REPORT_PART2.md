# Phần 2: Xây dựng CSDL và backend tìm kiếm ảnh đồ vật

## 1. Mục tiêu phần 2

Phần này nhận dữ liệu đầu ra từ phần 1 gồm:

- `features_output.json`: lưu đầy đủ đặc trưng của 1000 ảnh.
- `features_output.csv`: lưu đặc trưng dạng bảng.
- `features_summary.csv`: lưu đặc trưng tổng hợp.
- `normalized_images/`: chứa 1000 ảnh đã resize về 224 x 224.

Mục tiêu của phần 2 là thiết kế CSDL để quản lý metadata và vector đặc trưng, sau đó xây dựng API tìm kiếm ảnh tương đồng. Với một ảnh đầu vào, hệ thống trả về 5 ảnh giống nhất theo độ tương đồng nội dung.

## 2. Thiết kế CSDL

Em chọn mô hình quan hệ vì dữ liệu có cấu trúc rõ ràng: mỗi ảnh có một bản ghi metadata và một vector đặc trưng tương ứng.

### Bảng `images`

Bảng này lưu thông tin định danh và metadata cơ bản của ảnh:

| Thuộc tính | Ý nghĩa |
|---|---|
| `id` | Khóa chính |
| `filename` | Tên file ảnh, đặt unique để không trùng |
| `original_path` | Đường dẫn gốc từ dữ liệu phần 1 |
| `stored_path` | Đường dẫn ảnh trong thư mục backend |
| `original_width`, `original_height` | Kích thước ảnh ban đầu |
| `original_aspect` | Tỉ lệ khung hình |
| `channels` | Số kênh màu |
| `status` | Trạng thái xử lý ảnh |

### Bảng `feature_vectors`

Bảng này lưu vector đặc trưng phục vụ tìm kiếm:

| Thuộc tính | Ý nghĩa |
|---|---|
| `image_id` | Khóa ngoại trỏ tới `images.id` |
| `vector_dim` | Số chiều vector |
| `raw_vector` | Vector đặc trưng gốc dạng float32 BLOB |
| `norm_vector` | Vector đã chuẩn hóa và L2-normalize |
| `raw_json` | Toàn bộ đặc trưng gốc dạng JSON để kiểm tra và giải thích |

### Bảng `vector_metadata`

Bảng này lưu thông tin cấu hình cho toàn bộ vector:

| Thuộc tính | Ý nghĩa |
|---|---|
| `vector_spec` | Danh sách thuộc tính được dùng để ghép vector |
| `mean` | Giá trị trung bình từng chiều, dùng để chuẩn hóa ảnh mới |
| `std` | Độ lệch chuẩn từng chiều |
| `feature_groups` | Mô tả nhóm đặc trưng: màu sắc, kết cấu, hình dạng |

## 3. Các đặc trưng được lưu và sử dụng

Hệ thống sử dụng các nhóm đặc trưng từ phần 1:

### 3.1. Đặc trưng màu sắc

Gồm histogram RGB, histogram HSV, trung bình và độ lệch chuẩn màu. Nhóm này giúp phân biệt các đồ vật có màu sắc khác nhau, ví dụ cốc trắng, chai xanh, hộp đỏ.

### 3.2. Đặc trưng kết cấu

Gồm LBP và GLCM. Nhóm này giúp mô tả bề mặt vật thể như trơn, nhám, có vân, nhiều cạnh hoặc ít cạnh.

### 3.3. Đặc trưng hình dạng

Gồm HOG, SIFT và ORB/SURF fallback. Nhóm này giúp mô tả biên, góc, điểm đặc trưng và cấu trúc hình học của đồ vật.

## 4. Quy trình import dữ liệu vào CSDL

Quy trình import gồm các bước:

1. Đọc file `features_output.json`.
2. Lọc các ảnh có `status = success`.
3. Ghép các thuộc tính số và histogram thành một vector duy nhất.
4. Tính `mean` và `std` trên toàn bộ dataset.
5. Chuẩn hóa vector theo công thức:

```text
x_scaled = (x - mean) / std
```

6. L2-normalize vector để phục vụ cosine similarity:

```text
x_norm = x_scaled / ||x_scaled||
```

7. Lưu metadata vào bảng `images`.
8. Lưu `raw_vector`, `norm_vector`, `raw_json` vào bảng `feature_vectors`.
9. Lưu `vector_spec`, `mean`, `std` vào bảng `vector_metadata`.

## 5. Cơ chế tìm kiếm ảnh tương đồng

Hệ thống dùng Cosine Similarity giữa vector ảnh truy vấn và vector trong CSDL.

Với hai vector đã chuẩn hóa `q` và `v`, độ tương đồng được tính bằng:

```text
similarity(q, v) = q . v
```

Khoảng cách được tính bằng:

```text
distance(q, v) = 1 - similarity(q, v)
```

Sau đó hệ thống sắp xếp các ảnh theo `similarity` giảm dần và trả về top 5 ảnh giống nhất.

## 6. Luồng xử lý API

### 6.1. Tìm kiếm bằng ảnh có sẵn

Endpoint: `POST /search-by-filename`

Quy trình:

1. Nhận tên file ảnh.
2. Lấy vector đã chuẩn hóa của ảnh đó từ CSDL.
3. So sánh với toàn bộ vector trong CSDL.
4. Loại bỏ chính ảnh truy vấn nếu `exclude_self = true`.
5. Trả về top 5 ảnh giống nhất.

### 6.2. Tìm kiếm bằng ảnh upload mới

Endpoint: `POST /search-image`

Quy trình:

1. Nhận ảnh upload từ người dùng.
2. Resize ảnh về 224 x 224.
3. Trích xuất đặc trưng màu sắc, kết cấu và hình dạng.
4. Ghép vector theo đúng `vector_spec` đã lưu.
5. Chuẩn hóa bằng `mean` và `std` của dataset.
6. Tính cosine similarity với toàn bộ ảnh trong CSDL.
7. Trả về top 5 ảnh giống nhất.

## 7. Đánh giá ưu điểm

- CSDL tách rõ metadata ảnh và vector đặc trưng.
- Có thể mở rộng thêm đặc trưng mới mà không làm thay đổi quá nhiều backend.
- Cosine similarity đơn giản, dễ giải thích trong báo cáo.
- Dữ liệu 1000 ảnh nhỏ nên tìm kiếm tuyến tính vẫn chạy nhanh.
- Nếu dữ liệu lớn hơn, có thể thay phần tìm kiếm tuyến tính bằng FAISS hoặc Annoy.

## 8. Kết quả đầu ra của phần 2

- Database SQLite đã import 1000 ảnh.
- API backend bằng FastAPI.
- Endpoint tìm kiếm ảnh tương đồng.
- File schema SQLite và MySQL.
- Script import dữ liệu và script test tìm kiếm.
