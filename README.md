# Quan ly shop - MSSV 2324802010004

Flask + MySQL + Gunicorn + Nginx, chay tren VPS Ubuntu Server 24.04.

## 1. Cai goi he thong
    sudo apt update
    sudo apt install -y python3-venv python3-pip mysql-server nginx git ufw

## 2. Lay ma nguon va cai thu vien
    git clone https://github.com/2324802010004-star/quan_ly_shop_2324802010004.git ~/myapp
    cd ~/myapp
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

## 3. Tao co so du lieu va user rieng cho ung dung
    sudo mysql
    CREATE DATABASE quanly_shop CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE USER 'app_user'@'localhost' IDENTIFIED BY '<mat_khau_manh>';
    GRANT ALL PRIVILEGES ON quanly_shop.* TO 'app_user'@'localhost';
    FLUSH PRIVILEGES;
    EXIT;

Sau do tao cac bang (users, sanpham, giohang, donhang, chitiet_donhang) theo cau truc cua du an.

## 4. Cau hinh bi mat
    cp .env.example .env
    nano .env

Dat SECRET_KEY ngau nhien va mat khau DB. Khong dua file .env len GitHub.

## 5. Chay backend nhu dich vu systemd (chi nghe 127.0.0.1:8000)
Tao /etc/systemd/system/myapp.service chay gunicorn bind 127.0.0.1:8000, roi:
    sudo systemctl daemon-reload
    sudo systemctl enable --now myapp

## 6. Nginx reverse proxy cong 80
Tao /etc/nginx/sites-available/myapp co proxy_pass http://127.0.0.1:8000; roi:
    sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl restart nginx

## 7. Tuong lua ufw
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow from 192.168.98.0/24 to any port 22 proto tcp
    sudo ufw allow 80/tcp
    sudo ufw enable

## 8. Tao tai khoan admin
Dang ky mot tai khoan tren web, roi:
    sudo mysql -e "UPDATE quanly_shop.users SET role='admin' WHERE username='<ten>';"

Truy cap: http://<IP-VPS>
