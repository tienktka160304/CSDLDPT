1. Backend này có những gì?
   Cấu trúc chính:

part2_image_search_backend/
├── app/
│ ├── main.py
│ ├── search.py
│ ├── database.py
│ ├── feature_vector.py
│ └── feature_extractor.py
├── scripts/
│ ├── import_features.py
│ └── test_search.py
├── sql/
│ ├── schema_sqlite.sql
│ └── schema_mysql.sql
├── data/
│ ├── image_search.db
│ └── normalized_images/
├── REPORT_PART2.md
├── README.md
└── requirements.txt
Ý nghĩa từng phần
File / thư mục Chức năng
app/main.py Chạy FastAPI, tạo các API tìm kiếm ảnh
app/search.py Load vector ảnh từ database và tính độ tương đồng
app/database.py Kết nối SQLite, đọc/ghi vector dạng BLOB
app/feature_vector.py Chuyển feature JSON thành vector số, chuẩn hóa vector
app/feature_extractor.py Trích xuất đặc trưng cho ảnh mới upload
scripts/import_features.py Import dữ liệu từ file feature của phần 1 vào database
scripts/test_search.py Test tìm kiếm nhanh bằng terminal
sql/schema_sqlite.sql Cấu trúc database SQLite
sql/schema_mysql.sql Cấu trúc database MySQL để đưa vào báo cáo
data/image_search.db Database đã import sẵn 1000 ảnh
data/normalized_images/ 1000 ảnh đã chuẩn hóa
REPORT_PART2.md Nội dung báo cáo cho phần của m 2. Database lưu những gì?
Backend dùng SQLite để demo cho dễ chạy, không cần cài MySQL.

Database có 3 bảng chính:

Bảng images
Lưu thông tin ảnh:

id
filename
original_path
stored_path
original_width
original_height
original_aspect
channels
status
created_at
Ví dụ nó lưu tên ảnh như:

0000_image10025.jpg
0001_image10097.jpg
...
Bảng này dùng để biết ảnh nào đang có trong hệ thống, ảnh nằm ở đâu, kích thước gốc là bao nhiêu.

Bảng feature_vectors
Lưu vector đặc trưng của từng ảnh:

image_id
vector_dim
raw_vector
norm_vector
raw_json
Trong đó:

Cột Ý nghĩa
image_id Khóa ngoại nối với bảng images
vector_dim Số chiều của vector đặc trưng
raw_vector Vector gốc sau khi ghép các feature
norm_vector Vector đã chuẩn hóa, dùng để tìm kiếm
raw_json Feature gốc từ phần 1, lưu lại để kiểm tra/báo cáo
Điểm quan trọng là backend không so sánh trực tiếp ảnh bằng pixel, mà so sánh bằng vector đặc trưng.

Bảng vector_metadata
Lưu thông tin chuẩn hóa:

key
value
Nó lưu các thứ như:

vector_spec
mean
std
feature_groups
total_images
vector_dim
Cái này rất quan trọng vì khi upload ảnh mới, backend cần dùng đúng mean, std, vector_spec giống lúc import dataset ban đầu.

3. Backend có chức năng gì?
   Backend có mấy API chính:

GET /
Kiểm tra server có chạy không.

Trả về kiểu:

{
"message": "Image search backend is running",
"docs": "/docs",
"health": "/health"
}
GET /health
Kiểm tra trạng thái hệ thống.

Nó cho biết:

database đang dùng
thư mục ảnh
tổng số ảnh
số chiều vector
Dùng cái này để test nhanh xem backend có nhận DB chưa.

GET /images-list
Lấy danh sách ảnh trong database.

Ví dụ:

http://127.0.0.1:8000/images-list?limit=20&offset=0
Nó trả về danh sách ảnh, mỗi ảnh có:

id
filename
stored_path
image_url
width
height
status
POST /search-by-filename
Tìm ảnh tương tự bằng ảnh đã có sẵn trong dataset.

Đây là API ổn nhất để demo.

Body mẫu:

{
"filename": "0000_image10025.jpg",
"top_k": 5,
"exclude_self": true
}
Ý nghĩa:

Trường Ý nghĩa
filename Tên ảnh truy vấn
top_k Số ảnh muốn trả về
exclude_self Có loại ảnh chính nó ra khỏi kết quả không
Kết quả trả về dạng:

{
"query": "0000_image10025.jpg",
"top_k": 5,
"results": [
{
"rank": 1,
"id": 123,
"filename": "...jpg",
"similarity": 0.92,
"distance": 0.08,
"image_url": "/images/...jpg"
}
]
}
POST /search-image
Upload một ảnh mới, backend tự trích xuất đặc trưng rồi tìm ảnh giống nhất trong CSDL.

Dùng khi đầu vào là ảnh ngoài dataset.

Form gồm:

file: ảnh upload
top_k: số kết quả muốn lấy
API này hoạt động được, nhưng để báo cáo/demo ổn định nhất thì nên dùng search-by-filename, vì ảnh có sẵn trong dataset đã dùng đúng feature từ phần 1.

/images/{filename}
Đây là đường dẫn để xem ảnh.

Ví dụ:

http://127.0.0.1:8000/images/0000_image10025.jpg
Khi frontend làm giao diện, nó sẽ dùng image_url để hiển thị ảnh kết quả.

4. Backend hoạt động như nào?
   Luồng xử lý chính như sau:

Ảnh dataset phần 1
↓
features_output.json
↓
import_features.py
↓
Tạo vector đặc trưng
↓
Chuẩn hóa vector
↓
Lưu vào image_search.db
↓
FastAPI load database
↓
Người dùng gửi ảnh truy vấn
↓
Tính cosine similarity
↓
Trả về top 5 ảnh giống nhất 5. Cách tìm kiếm ảnh tương đồng
Backend dùng công thức:

similarity = cosine similarity
Tức là nó đo độ giống nhau giữa 2 vector.

Nếu 2 ảnh càng giống nhau thì:

similarity càng gần 1
distance càng gần 0
Trong code:

sims = self.matrix @ query_vector
Vì toàn bộ vector đã được L2-normalize nên tích vô hướng chính là cosine similarity.

6. Vector đặc trưng gồm những gì?
   Backend ghép nhiều nhóm feature thành một vector lớn.

Nhóm màu sắc
Gồm:

RGB histogram
HSV histogram
color mean
color std
Dùng để phân biệt ảnh theo màu chủ đạo.

Ví dụ:

cốc trắng
ghế nâu
chai xanh
đồ vật đen
Nhóm texture
Gồm:

LBP
GLCM
Dùng để nhận diện bề mặt, hoa văn, độ nhám, độ lặp mẫu.

Ví dụ:

vải
gỗ
kim loại
nhựa
bề mặt sọc
bề mặt trơn
Nhóm shape / keypoint
Gồm:

HOG
SIFT
ORB/SURF fallback
Dùng để mô tả hình dạng, cạnh, góc, điểm đặc trưng của vật thể.

Ví dụ:

vật tròn
vật vuông
vật dài
vật có nhiều cạnh
vật có nhiều điểm góc 7. Khi chạy backend thì chuyện gì xảy ra?
Khi m chạy lệnh:

uvicorn app.main:app --reload
Backend sẽ:

Mở database data/image_search.db.

Đọc toàn bộ vector đã chuẩn hóa trong bảng feature_vectors.

Load các vector vào RAM thành một ma trận.

Chờ người dùng gọi API.

Khi có truy vấn, nó so sánh vector truy vấn với toàn bộ vector trong ma trận.

Sắp xếp theo độ giống nhau giảm dần.

Trả về top 5 ảnh giống nhất.

8. Cách dùng backend
   Bước 1: Giải nén project
   Giải nén file zip rồi vào thư mục:

cd part2_image_search_backend
Bước 2: Cài thư viện
pip install -r requirements.txt
Bước 3: Chạy backend
uvicorn app.main:app --reload
Nếu chạy thành công, terminal sẽ hiện kiểu:

Uvicorn running on http://127.0.0.1:8000
Bước 4: Mở trang test API
Mở trình duyệt:

http://127.0.0.1:8000/docs
Đây là giao diện Swagger UI, dùng để test API không cần viết frontend.

9. Cách demo API tìm kiếm ảnh có sẵn
   Vào:

POST /search-by-filename
Bấm Try it out, nhập body:

{
"filename": "0000_image10025.jpg",
"top_k": 5,
"exclude_self": true
}
Sau đó bấm Execute.

Nó sẽ trả về 5 ảnh giống nhất.

Muốn xem ảnh kết quả thì lấy trường:

image_url
Ví dụ:

/images/0001_image10097.jpg
Mở thành:

http://127.0.0.1:8000/images/0001_image10097.jpg 10. Cách demo upload ảnh mới
Vào:

POST /search-image
Bấm Try it out.

Chọn một file ảnh, nhập:

top_k = 5
Bấm Execute.

Backend sẽ:

đọc ảnh
resize về 224x224
trích xuất feature
chuẩn hóa vector
so sánh với 1000 ảnh trong DB
trả về top 5 11. Cách test nhanh bằng terminal
Có thể chạy:

python scripts/test_search.py
File này gọi thử engine tìm kiếm để xem backend có hoạt động đúng không.

12. Nếu muốn import lại database từ phần 1
    Nếu phần 1 đưa cho m file:

features_output.json
normalized_images/
Thì chạy:

python scripts/import_features.py \
 --json /path/to/output_features/features_output.json \
 --images-dir /path/to/output_features/normalized_images \
 --db data/image_search.db
Script này sẽ:

đọc features_output.json
lọc ảnh status = success
tạo vector_spec
flatten feature thành vector
tính mean/std
chuẩn hóa vector
lưu ảnh vào bảng images
lưu vector vào bảng feature_vectors
lưu metadata vào bảng vector_metadata 13. Phần này nên nói trong báo cáo như nào?
M có thể trình bày ngắn gọn như này:

Nhóm xây dựng backend tìm kiếm ảnh dựa trên vector đặc trưng đã được trích xuất từ phần xử lý dữ liệu. Hệ thống sử dụng cơ sở dữ liệu để lưu metadata ảnh, vector đặc trưng gốc, vector đã chuẩn hóa và thông tin chuẩn hóa. Khi người dùng truy vấn bằng một ảnh có sẵn hoặc upload ảnh mới, backend chuyển ảnh truy vấn thành vector, chuẩn hóa theo cùng cấu hình với tập dữ liệu, sau đó tính độ tương đồng cosine với toàn bộ ảnh trong cơ sở dữ liệu. Kết quả trả về là top 5 ảnh có độ tương đồng cao nhất.

14. M nên demo phần nào cho chắc?
    Nên demo theo thứ tự này:

1. Chạy server FastAPI
1. Mở /health để chứng minh database đã load
1. Mở /images-list để chứng minh có danh sách ảnh
1. Gọi /search-by-filename với một ảnh có sẵn
1. Mở image_url để xem top 5 ảnh kết quả
1. Nếu còn thời gian thì demo /search-image
   Phần ổn nhất để chấm điểm là:

/search-by-filename
Vì nó dùng đúng vector đã import từ dữ liệu phần 1, kết quả sẽ ổn định hơn upload ảnh mới.

giờ hãy viết bản docs cho t

Thought for 1m 27s
T đã viết xong bản docs dạng Markdown cho backend phần 2.

Tải tại đây:
BACKEND_DOCS_PART2.md

# Tài liệu Backend - Hệ thống lưu trữ và tìm kiếm ảnh đồ vật tương đồng

## 1. Giới thiệu

Backend này phục vụ **phần 2** của bài tập lớn môn **Hệ cơ sở dữ liệu đa phương tiện**: xây dựng cơ sở dữ liệu và cơ chế tìm kiếm ảnh đồ vật tương đồng dựa trên các đặc trưng ảnh đã trích xuất ở phần 1.

Hệ thống không so sánh ảnh trực tiếp bằng từng điểm ảnh, mà chuyển mỗi ảnh thành một **vector đặc trưng**. Vector này chứa thông tin về màu sắc, texture, hình dạng và keypoint. Khi người dùng truy vấn bằng một ảnh, hệ thống sẽ tính độ tương đồng giữa vector của ảnh truy vấn và vector của toàn bộ ảnh trong cơ sở dữ liệu, sau đó trả về **top 5 ảnh giống nhất**.

---

## 2. Mục tiêu của backend

Backend được xây dựng để thực hiện các nhiệm vụ chính sau:

1. Lưu trữ thông tin ảnh và vector đặc trưng vào cơ sở dữ liệu.
2. Quản lý metadata của ảnh như tên file, kích thước gốc, đường dẫn lưu ảnh, trạng thái xử lý.
3. Lưu vector đặc trưng gốc và vector đã chuẩn hóa.
4. Cung cấp API tìm kiếm ảnh tương đồng bằng tên ảnh có sẵn trong dataset.
5. Cung cấp API upload ảnh mới và tìm ảnh tương đồng.
6. Trả về danh sách top-k ảnh giống nhất, trong đó mặc định là top 5.
7. Hỗ trợ frontend hoặc Swagger UI gọi API để demo hệ thống.

---

## 3. Công nghệ sử dụng

| Thành phần                   | Công nghệ              |
| ---------------------------- | ---------------------- |
| Ngôn ngữ backend             | Python                 |
| Framework API                | FastAPI                |
| Server chạy API              | Uvicorn                |
| Cơ sở dữ liệu demo           | SQLite                 |
| Xử lý ảnh                    | OpenCV                 |
| Trích xuất đặc trưng bổ sung | scikit-image           |
| Tính toán vector             | NumPy                  |
| Test API                     | Swagger UI tại `/docs` |

Lý do chọn SQLite cho bản demo: dễ chạy, không cần cài server database riêng, phù hợp để demo bài tập lớn. Trong báo cáo vẫn có file schema MySQL để trình bày phương án triển khai với hệ quản trị CSDL quan hệ.

---

## 4. Cấu trúc thư mục

```text
part2_image_search_backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── search.py
│   ├── feature_vector.py
│   └── feature_extractor.py
├── scripts/
│   ├── import_features.py
│   └── test_search.py
├── sql/
│   ├── schema_sqlite.sql
│   └── schema_mysql.sql
├── data/
│   ├── image_search.db
│   └── normalized_images/
├── README.md
├── REPORT_PART2.md
├── requirements.txt
└── sample_top5_0000.png
```

### Ý nghĩa các file chính

| File / Thư mục               | Chức năng                                                                    |
| ---------------------------- | ---------------------------------------------------------------------------- |
| `app/main.py`                | Khởi tạo FastAPI, định nghĩa các endpoint API                                |
| `app/database.py`            | Kết nối database, đọc metadata, chuyển vector giữa dạng NumPy và BLOB        |
| `app/search.py`              | Load vector từ database, tính cosine similarity, trả về top-k ảnh tương đồng |
| `app/feature_vector.py`      | Xây dựng cấu trúc vector, flatten feature JSON, chuẩn hóa vector             |
| `app/feature_extractor.py`   | Trích xuất đặc trưng từ ảnh mới upload                                       |
| `scripts/import_features.py` | Import dữ liệu từ `features_output.json` của phần 1 vào database             |
| `scripts/test_search.py`     | Test nhanh cơ chế tìm kiếm bằng terminal                                     |
| `sql/schema_sqlite.sql`      | Script tạo bảng SQLite                                                       |
| `sql/schema_mysql.sql`       | Script tạo bảng MySQL để đưa vào báo cáo                                     |
| `data/image_search.db`       | Database đã import sẵn dữ liệu ảnh                                           |
| `data/normalized_images/`    | Thư mục chứa ảnh đã chuẩn hóa kích thước                                     |
| `REPORT_PART2.md`            | Nội dung báo cáo cho phần backend và CSDL                                    |

---

## 5. Dữ liệu đầu vào

Backend nhận dữ liệu đầu vào từ phần 1, gồm:

```text
features_output.json
normalized_images/
```

Trong đó:

- `features_output.json`: chứa đặc trưng đã trích xuất của từng ảnh.
- `normalized_images/`: chứa các ảnh đã resize về cùng kích thước, ví dụ 224x224.

Mỗi record trong file JSON thường có các thông tin như:

```json
{
  "filename": "0000_image10025.jpg",
  "filepath": "...",
  "original_width": 640,
  "original_height": 480,
  "original_aspect": 1.3333,
  "channels": 3,
  "status": "success",
  "hist_rgb_R": [...],
  "hist_rgb_G": [...],
  "hist_rgb_B": [...],
  "hist_hsv_H": [...],
  "lbp_histogram": [...],
  "glcm_contrast_mean": 0.0,
  "hog_vector_100": [...],
  "sift_avg_descriptor": [...]
}
```

---

## 6. Thiết kế cơ sở dữ liệu

Backend sử dụng SQLite với 3 bảng chính:

1. `images`
2. `feature_vectors`
3. `vector_metadata`

### 6.1. Bảng `images`

Bảng này lưu thông tin cơ bản của ảnh.

| Cột               | Kiểu dữ liệu | Ý nghĩa                                   |
| ----------------- | ------------ | ----------------------------------------- |
| `id`              | INTEGER      | Khóa chính, tự tăng                       |
| `filename`        | TEXT         | Tên file ảnh, duy nhất                    |
| `original_path`   | TEXT         | Đường dẫn ảnh gốc                         |
| `stored_path`     | TEXT         | Đường dẫn ảnh sau khi chuẩn hóa           |
| `original_width`  | INTEGER      | Chiều rộng ảnh gốc                        |
| `original_height` | INTEGER      | Chiều cao ảnh gốc                         |
| `original_aspect` | REAL         | Tỉ lệ khung hình ảnh gốc                  |
| `channels`        | INTEGER      | Số kênh màu, thường là 3                  |
| `status`          | TEXT         | Trạng thái xử lý ảnh, thường là `success` |
| `created_at`      | TEXT         | Thời điểm thêm vào database               |

Mục đích của bảng này là quản lý thông tin định danh và metadata của ảnh.

### 6.2. Bảng `feature_vectors`

Bảng này lưu vector đặc trưng của từng ảnh.

| Cột           | Kiểu dữ liệu | Ý nghĩa                                               |
| ------------- | ------------ | ----------------------------------------------------- |
| `image_id`    | INTEGER      | Khóa chính, đồng thời là khóa ngoại đến bảng `images` |
| `vector_dim`  | INTEGER      | Số chiều vector đặc trưng                             |
| `raw_vector`  | BLOB         | Vector gốc sau khi ghép các đặc trưng                 |
| `norm_vector` | BLOB         | Vector đã chuẩn hóa, dùng để tìm kiếm                 |
| `raw_json`    | TEXT         | Feature JSON gốc để kiểm tra và đối chiếu             |

Mục đích của bảng này là lưu trữ dữ liệu đặc trưng phục vụ tìm kiếm ảnh tương đồng.

### 6.3. Bảng `vector_metadata`

Bảng này lưu các thông tin phục vụ chuẩn hóa vector.

| Cột     | Kiểu dữ liệu | Ý nghĩa                    |
| ------- | ------------ | -------------------------- |
| `key`   | TEXT         | Tên metadata               |
| `value` | TEXT         | Giá trị metadata dạng JSON |

Một số metadata quan trọng:

| Key              | Ý nghĩa                                              |
| ---------------- | ---------------------------------------------------- |
| `vector_spec`    | Danh sách các trường feature được dùng để tạo vector |
| `mean`           | Giá trị trung bình của từng chiều vector             |
| `std`            | Độ lệch chuẩn của từng chiều vector                  |
| `feature_groups` | Mô tả các nhóm đặc trưng                             |
| `total_images`   | Tổng số ảnh đã import                                |
| `vector_dim`     | Số chiều vector                                      |

---

## 7. Nhóm đặc trưng được sử dụng

Vector đặc trưng của mỗi ảnh được tạo bằng cách ghép nhiều nhóm đặc trưng khác nhau.

### 7.1. Đặc trưng màu sắc

Gồm:

- Histogram RGB
- Histogram HSV
- Giá trị trung bình màu
- Độ lệch chuẩn màu

Ý nghĩa:

- Giúp nhận diện màu chủ đạo của đồ vật.
- Phân biệt các vật thể có màu sắc khác nhau.
- Ví dụ: chai xanh, cốc trắng, hộp đỏ, ghế nâu.

### 7.2. Đặc trưng texture

Gồm:

- LBP histogram
- GLCM contrast
- GLCM dissimilarity
- GLCM homogeneity
- GLCM energy
- GLCM correlation
- GLCM ASM

Ý nghĩa:

- Giúp mô tả bề mặt vật thể.
- Phân biệt bề mặt trơn, nhám, có hoa văn, có vân gỗ, vải, kim loại.

### 7.3. Đặc trưng hình dạng và keypoint

Gồm:

- HOG
- SIFT
- SURF hoặc ORB fallback

Ý nghĩa:

- HOG mô tả hướng cạnh và hình dạng tổng thể.
- SIFT/ORB mô tả các điểm đặc trưng cục bộ.
- Giúp phân biệt vật tròn, vật vuông, vật dài, vật có nhiều góc cạnh.

---

## 8. Quy trình import dữ liệu vào database

Quy trình import dữ liệu gồm các bước:

```text
features_output.json
        ↓
Đọc danh sách record có status = success
        ↓
Xây dựng vector_spec từ record mẫu
        ↓
Flatten từng record thành raw_vector
        ↓
Tính mean và std trên toàn bộ dataset
        ↓
Chuẩn hóa vector bằng z-score
        ↓
L2-normalize vector
        ↓
Lưu metadata ảnh vào bảng images
        ↓
Lưu vector vào bảng feature_vectors
        ↓
Lưu mean, std, vector_spec vào bảng vector_metadata
```

Lệnh import lại database:

```bash
python scripts/import_features.py \
  --json /path/to/features_output.json \
  --images-dir /path/to/normalized_images \
  --db data/image_search.db
```

Sau khi chạy thành công, terminal sẽ hiển thị:

```text
Imported 1000 images
Vector dimension: ...
Database: data/image_search.db
```

---

## 9. Cơ chế chuẩn hóa vector

Mỗi ảnh có nhiều loại đặc trưng khác nhau. Các đặc trưng này có miền giá trị khác nhau, ví dụ histogram thường nằm trong khoảng 0-1, còn một số đặc trưng khác có thể có giá trị lớn hơn. Vì vậy hệ thống cần chuẩn hóa trước khi so sánh.

Backend sử dụng 2 bước chuẩn hóa:

### 9.1. Chuẩn hóa z-score

Với mỗi chiều vector:

```text
x_standardized = (x - mean) / std
```

Trong đó:

- `x` là giá trị đặc trưng ban đầu.
- `mean` là trung bình của chiều đó trên toàn bộ dataset.
- `std` là độ lệch chuẩn của chiều đó trên toàn bộ dataset.

Mục đích là đưa các nhóm đặc trưng về cùng thang đo.

### 9.2. Chuẩn hóa L2

Sau z-score, vector được chuẩn hóa L2:

```text
x_normalized = x_standardized / ||x_standardized||
```

Mục đích là đưa vector về độ dài 1, giúp tính cosine similarity nhanh bằng tích vô hướng.

---

## 10. Cơ chế tìm kiếm ảnh tương đồng

Backend sử dụng **cosine similarity** để đo độ tương đồng giữa ảnh truy vấn và ảnh trong database.

Công thức:

```text
similarity = cosine(query_vector, database_vector)
```

Do các vector đã được L2-normalize, cosine similarity có thể tính nhanh bằng tích vô hướng:

```text
similarity = query_vector · database_vector
```

Ý nghĩa điểm số:

| Giá trị similarity | Ý nghĩa                                   |
| ------------------ | ----------------------------------------- |
| Gần 1              | Hai ảnh rất giống nhau                    |
| Gần 0              | Hai ảnh ít liên quan                      |
| Nhỏ hơn 0          | Hai vector khác hướng, độ tương đồng thấp |

Backend cũng trả về thêm `distance`:

```text
distance = 1 - similarity
```

Ảnh nào có similarity cao hơn sẽ được xếp hạng cao hơn.

---

## 11. Luồng hoạt động tổng thể

```text
Người dùng / Frontend
        ↓
Gửi tên ảnh hoặc upload ảnh mới
        ↓
FastAPI backend nhận request
        ↓
Nếu tìm bằng filename:
    Lấy norm_vector từ database
Nếu upload ảnh mới:
    Trích xuất feature từ ảnh
    Flatten feature thành vector
    Chuẩn hóa bằng mean/std đã lưu
    L2-normalize vector
        ↓
So sánh vector truy vấn với toàn bộ vector trong database
        ↓
Tính cosine similarity
        ↓
Sắp xếp giảm dần theo similarity
        ↓
Trả về top 5 ảnh giống nhất
```

---

## 12. Các API của backend

Sau khi chạy server, truy cập Swagger UI tại:

```text
http://127.0.0.1:8000/docs
```

### 12.1. API kiểm tra server

```http
GET /
```

Chức năng: kiểm tra backend có đang chạy hay không.

Response mẫu:

```json
{
  "message": "Image search backend is running",
  "docs": "/docs",
  "health": "/health"
}
```

---

### 12.2. API kiểm tra trạng thái hệ thống

```http
GET /health
```

Chức năng: kiểm tra database, thư mục ảnh, số lượng ảnh và số chiều vector.

Response mẫu:

```json
{
  "status": "ok",
  "database": ".../data/image_search.db",
  "images_dir": ".../data/normalized_images",
  "total_images": 1000,
  "vector_dim": 573
}
```

Ghi chú: `vector_dim` có thể thay đổi tùy file đặc trưng phần 1.

---

### 12.3. API lấy danh sách ảnh

```http
GET /images-list?limit=20&offset=0
```

Chức năng: lấy danh sách ảnh đang có trong database.

Tham số:

| Tên      | Ý nghĩa                     |
| -------- | --------------------------- |
| `limit`  | Số ảnh muốn lấy, tối đa 100 |
| `offset` | Vị trí bắt đầu lấy dữ liệu  |

Response mẫu:

```json
{
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "filename": "0000_image10025.jpg",
      "stored_path": "0000_image10025.jpg",
      "image_url": "/images/0000_image10025.jpg",
      "original_width": 640,
      "original_height": 480,
      "status": "success"
    }
  ]
}
```

---

### 12.4. API tìm kiếm bằng ảnh có sẵn trong dataset

```http
POST /search-by-filename
```

Chức năng: tìm top-k ảnh tương đồng với một ảnh đã có sẵn trong database.

Request body:

```json
{
  "filename": "0000_image10025.jpg",
  "top_k": 5,
  "exclude_self": true
}
```

Ý nghĩa các trường:

| Trường         | Kiểu    | Ý nghĩa                                       |
| -------------- | ------- | --------------------------------------------- |
| `filename`     | string  | Tên ảnh truy vấn                              |
| `top_k`        | integer | Số ảnh kết quả muốn lấy                       |
| `exclude_self` | boolean | Nếu `true`, loại ảnh truy vấn ra khỏi kết quả |

Response mẫu:

```json
{
  "query": "0000_image10025.jpg",
  "top_k": 5,
  "results": [
    {
      "rank": 1,
      "id": 215,
      "filename": "0214_imagexxxx.jpg",
      "stored_path": "0214_imagexxxx.jpg",
      "similarity": 0.923456,
      "distance": 0.076544,
      "image_url": "/images/0214_imagexxxx.jpg"
    }
  ]
}
```

Đây là API nên dùng chính khi demo vì nó sử dụng đúng vector đã trích xuất từ phần 1.

---

### 12.5. API upload ảnh mới để tìm kiếm

```http
POST /search-image
```

Chức năng: upload một ảnh mới, backend trích xuất đặc trưng và tìm top-k ảnh tương đồng trong database.

Kiểu request: `multipart/form-data`

Tham số:

| Tên     | Kiểu    | Ý nghĩa                             |
| ------- | ------- | ----------------------------------- |
| `file`  | file    | Ảnh cần tìm kiếm                    |
| `top_k` | integer | Số ảnh kết quả muốn lấy, mặc định 5 |

Response mẫu:

```json
{
  "query_filename": "query.jpg",
  "top_k": 5,
  "results": [
    {
      "rank": 1,
      "id": 10,
      "filename": "0009_image10154.jpg",
      "stored_path": "0009_image10154.jpg",
      "similarity": 0.812345,
      "distance": 0.187655,
      "image_url": "/images/0009_image10154.jpg"
    }
  ]
}
```

Ghi chú: API upload ảnh mới hoạt động bằng bộ trích xuất đặc trưng viết lại trong backend. Nếu nhóm có code trích xuất đặc trưng gốc của phần 1 thì có thể thay logic trong `app/feature_extractor.py` để kết quả upload ảnh mới khớp tuyệt đối hơn.

---

### 12.6. API xem ảnh theo filename

```http
GET /images/{filename}
```

Ví dụ:

```text
http://127.0.0.1:8000/images/0000_image10025.jpg
```

Chức năng: trả về file ảnh để frontend hiển thị ảnh truy vấn hoặc ảnh kết quả.

---

## 13. Hướng dẫn cài đặt và chạy backend

### Bước 1. Giải nén project

Giải nén file backend, sau đó mở terminal tại thư mục project:

```bash
cd part2_image_search_backend
```

### Bước 2. Cài thư viện

```bash
pip install -r requirements.txt
```

### Bước 3. Chạy server

```bash
uvicorn app.main:app --reload
```

Nếu chạy thành công, terminal sẽ hiển thị:

```text
Uvicorn running on http://127.0.0.1:8000
```

### Bước 4. Mở Swagger UI

Mở trình duyệt và truy cập:

```text
http://127.0.0.1:8000/docs
```

Tại đây có thể test trực tiếp các API.

---

## 14. Hướng dẫn demo

Nên demo theo thứ tự sau:

### Bước 1. Kiểm tra backend

Mở:

```text
http://127.0.0.1:8000/health
```

Mục đích: chứng minh backend đã load database và vector thành công.

### Bước 2. Xem danh sách ảnh

Mở:

```text
http://127.0.0.1:8000/images-list?limit=10&offset=0
```

Mục đích: lấy tên file ảnh để dùng làm ảnh truy vấn.

### Bước 3. Tìm kiếm ảnh tương đồng bằng filename

Vào Swagger UI:

```text
http://127.0.0.1:8000/docs
```

Chọn API:

```text
POST /search-by-filename
```

Nhập body:

```json
{
  "filename": "0000_image10025.jpg",
  "top_k": 5,
  "exclude_self": true
}
```

Bấm `Execute`.

### Bước 4. Xem ảnh kết quả

Trong response, lấy trường `image_url`, ví dụ:

```text
/images/0001_image10097.jpg
```

Mở đường dẫn đầy đủ:

```text
http://127.0.0.1:8000/images/0001_image10097.jpg
```

---

## 15. Test nhanh bằng terminal

Có thể chạy script test:

```bash
python scripts/test_search.py
```

Script này dùng engine tìm kiếm để kiểm tra hệ thống có trả về top ảnh tương đồng hay không.

---

## 16. Tích hợp với frontend

Frontend chỉ cần gọi API của backend.

### Gọi API lấy danh sách ảnh

```javascript
const res = await fetch("http://127.0.0.1:8000/images-list?limit=20&offset=0");
const data = await res.json();
```

### Gọi API tìm kiếm bằng filename

```javascript
const res = await fetch("http://127.0.0.1:8000/search-by-filename", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    filename: "0000_image10025.jpg",
    top_k: 5,
    exclude_self: true,
  }),
});

const data = await res.json();
```

### Hiển thị ảnh kết quả

Mỗi result có trường:

```text
image_url
```

Frontend ghép với base URL:

```javascript
const fullImageUrl = "http://127.0.0.1:8000" + result.image_url;
```

Sau đó hiển thị bằng thẻ:

```html
<img src="http://127.0.0.1:8000/images/0001_image10097.jpg" />
```

---

## 17. Các lỗi thường gặp

### 17.1. Lỗi thiếu thư viện

Biểu hiện:

```text
ModuleNotFoundError: No module named 'fastapi'
```

Cách xử lý:

```bash
pip install -r requirements.txt
```

### 17.2. Không mở được ảnh

Biểu hiện:

```text
404 Not Found khi mở /images/filename.jpg
```

Nguyên nhân có thể:

- Thiếu thư mục `data/normalized_images/`.
- Tên file ảnh không tồn tại.
- Chạy backend sai thư mục project.

Cách xử lý:

- Kiểm tra thư mục `data/normalized_images/` có ảnh hay không.
- Gọi `/images-list` để lấy đúng tên ảnh.

### 17.3. Không tìm thấy filename

Biểu hiện:

```json
{
  "detail": "Không tìm thấy ảnh: ..."
}
```

Nguyên nhân: tên ảnh không tồn tại trong database.

Cách xử lý: dùng API `/images-list` để lấy tên ảnh hợp lệ.

### 17.4. Lỗi khi upload ảnh mới

Nguyên nhân có thể:

- File upload không phải ảnh.
- OpenCV không đọc được ảnh.
- Ảnh bị lỗi định dạng.

Cách xử lý:

- Dùng file `.jpg`, `.jpeg`, `.png`.
- Thử ảnh khác.
- Ưu tiên demo bằng `/search-by-filename` để kết quả ổn định.

---

## 18. Nội dung giải thích khi thuyết trình

Có thể trình bày ngắn gọn như sau:

> Ở phần backend, nhóm xây dựng cơ sở dữ liệu để lưu thông tin ảnh và vector đặc trưng đã được trích xuất từ phần xử lý dữ liệu. Mỗi ảnh được biểu diễn bằng một vector gồm các nhóm đặc trưng màu sắc, texture, hình dạng và keypoint. Trước khi lưu vào database, vector được chuẩn hóa bằng z-score và L2-normalization. Khi người dùng truy vấn bằng một ảnh, hệ thống lấy vector của ảnh truy vấn, tính cosine similarity với toàn bộ vector trong database, sắp xếp theo độ tương đồng giảm dần và trả về top 5 ảnh giống nhất.

---

## 19. Vai trò của phần backend trong toàn bộ hệ thống

Trong hệ thống tìm kiếm ảnh đồ vật, backend đóng vai trò là tầng xử lý chính:

```text
Frontend / Giao diện người dùng
        ↓
Backend API
        ↓
Cơ sở dữ liệu ảnh và vector
        ↓
Thuật toán tính độ tương đồng
        ↓
Top 5 ảnh giống nhất
```

Frontend chỉ chịu trách nhiệm upload ảnh, chọn ảnh truy vấn và hiển thị kết quả. Backend chịu trách nhiệm lưu trữ dữ liệu, xử lý vector, tính toán độ tương đồng và trả kết quả.

---

## 20. Kết luận

Backend đã hoàn thành các chức năng chính của phần 2:

- Thiết kế database lưu metadata ảnh và feature vector.
- Import dữ liệu đặc trưng từ phần 1.
- Chuẩn hóa và lưu vector phục vụ tìm kiếm.
- Xây dựng API tìm kiếm ảnh tương đồng.
- Trả về top 5 ảnh giống nhất theo cosine similarity.
- Có thể tích hợp với frontend để demo hoàn chỉnh hệ thống.

Đây là thành phần trung gian quan trọng kết nối dữ liệu đặc trưng của phần 1 với giao diện demo và báo cáo kết quả ở phần 3.

Bản docs có đủ các phần:

Giới thiệu backend

Mục tiêu hệ thống

Công nghệ sử dụng

Cấu trúc thư mục

Thiết kế CSDL

Các bảng images, feature_vectors, vector_metadata

Các nhóm đặc trưng ảnh

Quy trình import dữ liệu

Cơ chế chuẩn hóa vector

Cơ chế tìm kiếm bằng cosine similarity

Danh sách API

Cách chạy backend

Cách demo

Cách tích hợp frontend

Lỗi thường gặp

Đoạn giải thích để thuyết trình

M có thể copy thẳng nội dung này vào README.md, hoặc dùng làm tài liệu nộp kèm cho phần backend.

Your download's being scanned. We'll let you know if there's an issue.
