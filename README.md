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
| Cơ sở dữ liệu | Firebase |
| Giao diện | HTML / CSS / JavaScript |

## Hướng dẫn chạy Local

Làm theo các bước dưới đây để chạy hệ thống trên máy local.

1 Clone dự án

git clone https://github.com/thuantcn1802/AI4Life.git

cd AI4Life

2 Tạo môi trường chạy: Dùng Conda: 

conda create -n ai4life python=3.10 -y

conda activate ai4life

pip install -r requirements.txt

3 Thiết lập biến môi trường (API Key – nếu dùng Groq)

Tự tạo API Key

Link: https://console.groq.com/keys

Sau đó tạo file .env:

GROQ_API_KE Y= your_api_key_here

4 Chạy ứng dụng (trong conda)

python app.py

5 Truy cập giao diện web

Ứng dụng Flask chạy tại:
http://127.0.0.1:5000

