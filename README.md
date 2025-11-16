# Skin Cancer AI Detection

Hệ thống nhận diện ung thư da qua ảnh chụp vùng da nghi ngờ, sử dụng Deep Learning và Computer Vision.

## Mục tiêu
- Hỗ trợ phát hiện sớm nguy cơ ung thư da.
- Ứng dụng mô hình U-Net để tách vùng tổn thương.
- Áp dụng CNN (EfficientNet, ResNet) để phân loại tổn thương ác tính/không ác tính.

## Công nghệ
| Thành phần | Công cụ |
|-------------|----------|
| Ngôn ngữ | Python |
| Deep Learning | TensorFlow |
| Computer Vision | OpenCV |
| Đánh giá mô hình | Scikit-learn |
| Backend | Flask |
| Cơ sở dữ liệu | MySQL |
| Giao diện | HTML / CSS / JavaScript |

## Cấu trúc thư mục
```bash
src/
  ├─ preprocessing/   # Xử lý ảnh
  ├─ segmentation/    # U-Net
  ├─ classification/  # CNN
  ├─ api/             # Flask API
  ├─ decision/        # Hệ thống hỗ trợ ra quyết định
  └─ db/              # Kết nối database
