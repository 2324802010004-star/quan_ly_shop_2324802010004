from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from vietnam_qr_pay import QRPay, BanksObject

app = Flask(__name__)
app.secret_key = 'BiMatCuaToi123'

def get_db():
    return mysql.connector.connect(
        host="127.0.0.1", user="app_user", password="MatKhauManh123!", database="quanly_shop"
    )

@app.route('/')
def index():
    search_query = request.args.get('search', '')
    db = get_db(); cursor = db.cursor(dictionary=True)
    if search_query:
        cursor.execute("SELECT * FROM sanpham WHERE ten_ao LIKE %s", ('%' + search_query + '%',))
    else:
        cursor.execute("SELECT * FROM sanpham")
    sanphams = cursor.fetchall()
    db.close()
    
    cart_count = 0
    if 'user_id' in session:
        db = get_db(); cursor = db.cursor()
        cursor.execute("SELECT SUM(so_luong) FROM giohang WHERE user_id=%s", (session['user_id'],))
        result = cursor.fetchone()
        if result[0]: cart_count = result[0]
        db.close()
    return render_template('index.html', sanphams=sanphams, user=session.get('user'), role=session.get('role'), search_query=search_query, cart_count=cart_count)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        db.close()
        if user and check_password_hash(user['password'], password):
            session['user'] = username
            session['user_id'] = user['id']
            session['role'] = user['role']
            return redirect(url_for('index'))
        flash('Sai tài khoản hoặc mật khẩu!')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        db = get_db(); cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, 'user')", (username, password))
            db.commit()
            flash('Đăng ký thành công!')
            return redirect(url_for('login'))
        except:
            flash('Tài khoản đã tồn tại!')
        finally:
            db.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/add', methods=['POST'])
def add():
    if session.get('role') != 'admin': return "Bạn không có quyền!", 403
    ten_ao = request.form['ten_ao']; gia = request.form['gia']; size = request.form['size']; hinh_anh = request.form['hinh_anh']
    db = get_db(); cursor = db.cursor()
    cursor.execute("INSERT INTO sanpham (ten_ao, gia, size, hinh_anh) VALUES (%s, %s, %s, %s)", (ten_ao, gia, size, hinh_anh))
    db.commit(); db.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete(id):
    if session.get('role') != 'admin': return "Bạn không có quyền!", 403
    db = get_db(); cursor = db.cursor()
    cursor.execute("DELETE FROM sanpham WHERE id=%s", (id,))
    db.commit(); db.close()
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if session.get('role') != 'admin': return "Bạn không có quyền!", 403
    db = get_db(); cursor = db.cursor(dictionary=True)
    if request.method == 'POST':
        ten_ao = request.form['ten_ao']; gia = request.form['gia']; size = request.form['size']; hinh_anh = request.form['hinh_anh']
        cursor.execute("UPDATE sanpham SET ten_ao=%s, gia=%s, size=%s, hinh_anh=%s WHERE id=%s", (ten_ao, gia, size, hinh_anh, id))
        db.commit(); db.close()
        return redirect(url_for('index'))
    cursor.execute("SELECT * FROM sanpham WHERE id=%s", (id,))
    sanpham = cursor.fetchone()
    db.close()
    return render_template('edit.html', sanpham=sanpham)

@app.route('/add_to_cart/<int:sanpham_id>')
def add_to_cart(sanpham_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db(); cursor = db.cursor()
    cursor.execute("SELECT * FROM giohang WHERE user_id=%s AND sanpham_id=%s", (session['user_id'], sanpham_id))
    item = cursor.fetchone()
    if item:
        cursor.execute("UPDATE giohang SET so_luong = so_luong + 1 WHERE id=%s", (item[0],))
    else:
        cursor.execute("INSERT INTO giohang (user_id, sanpham_id) VALUES (%s, %s)", (session['user_id'], sanpham_id))
    db.commit(); db.close()
    return redirect(url_for('index'))

@app.route('/cart')
def cart():
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT g.id, g.so_luong, s.ten_ao, s.gia, s.hinh_anh, (g.so_luong * s.gia) as thanh_tien 
        FROM giohang g JOIN sanpham s ON g.sanpham_id = s.id 
        WHERE g.user_id = %s
    """, (session['user_id'],))
    items = cursor.fetchall()
    tong_tien = sum(item['thanh_tien'] for item in items)
    db.close()
    return render_template('cart.html', items=items, tong_tien=tong_tien)

@app.route('/remove_cart/<int:id>')
def remove_cart(id):
    db = get_db(); cursor = db.cursor()
    cursor.execute("DELETE FROM giohang WHERE id=%s", (id,))
    db.commit(); db.close()
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET'])
def checkout_page():
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT g.id, g.so_luong, s.ten_ao, s.gia, s.hinh_anh, (g.so_luong * s.gia) as thanh_tien 
        FROM giohang g JOIN sanpham s ON g.sanpham_id = s.id 
        WHERE g.user_id = %s
    """, (session['user_id'],))
    items = cursor.fetchall()
    tong_tien = sum(item['thanh_tien'] for item in items)
    db.close()
    
    qr_content = None
    if tong_tien > 0:
        qr_pay = QRPay.init_viet_qr(
            bank_bin=BanksObject["vietcombank"].bin, 
            bank_number="0123456789", 
            amount=str(tong_tien),
            purpose="Thanh toan SHAVIK"
        )
        qr_content = qr_pay.build()
    return render_template('checkout.html', items=items, tong_tien=tong_tien, qr_content=qr_content)

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session: return redirect(url_for('login'))
    ho_ten = request.form.get('ho_ten'); sdt = request.form.get('sdt')
    dia_chi = request.form.get('dia_chi'); phuong_thuc_tt = request.form.get('phuong_thuc_tt')
    
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT g.sanpham_id, g.so_luong, s.gia FROM giohang g JOIN sanpham s ON g.sanpham_id = s.id WHERE g.user_id = %s", (session['user_id'],))
    items = cursor.fetchall()
    if not items: return redirect(url_for('cart'))
    
    tong_tien = sum(item['so_luong'] * item['gia'] for item in items)
    cursor.execute("""
        INSERT INTO donhang (user_id, tong_tien, ho_ten, sdt, dia_chi, phuong_thuc_tt) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (session['user_id'], tong_tien, ho_ten, sdt, dia_chi, phuong_thuc_tt))
    donhang_id = cursor.lastrowid
    for item in items:
        cursor.execute("INSERT INTO chitiet_donhang (donhang_id, sanpham_id, so_luong, gia) VALUES (%s, %s, %s, %s)", (donhang_id, item['sanpham_id'], item['so_luong'], item['gia']))
    cursor.execute("DELETE FROM giohang WHERE user_id=%s", (session['user_id'],))
    db.commit(); db.close()
    return render_template('success.html', phuong_thuc_tt=phuong_thuc_tt)

@app.route('/my_orders')
def my_orders():
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM donhang WHERE user_id=%s ORDER BY ngay_dat DESC", (session['user_id'],))
    orders = cursor.fetchall()
    for order in orders:
        cursor.execute("""
            SELECT c.so_luong, c.gia, s.ten_ao, s.hinh_anh 
            FROM chitiet_donhang c JOIN sanpham s ON c.sanpham_id = s.id 
            WHERE c.donhang_id = %s
        """, (order['id'],))
        order['items'] = cursor.fetchall()
    db.close()
    return render_template('my_orders.html', orders=orders)

@app.route('/admin/orders')
def admin_orders():
    if session.get('role') != 'admin': return "Bạn không có quyền!", 403
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT d.*, u.username FROM donhang d JOIN users u ON d.user_id = u.id ORDER BY d.ngay_dat DESC")
    orders = cursor.fetchall()
    db.close()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/update_order/<int:id>/<string:status>')
def update_order(id, status):
    if session.get('role') != 'admin': return "Bạn không có quyền!", 403
    db = get_db(); cursor = db.cursor()
    cursor.execute("UPDATE donhang SET trang_thai=%s WHERE id=%s", (status, id))
    db.commit(); db.close()
    return redirect(url_for('admin_orders'))

@app.route('/admin/users')
def admin_users():
    if session.get('role') != 'admin': return "Bạn không có quyền!", 403
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, username, role FROM users")
    users = cursor.fetchall()
    db.close()
    return render_template('admin_users.html', users=users)

@app.route('/admin/delete_user/<int:id>')
def delete_user(id):
    if session.get('role') != 'admin': return "Bạn không có quyền!", 403
    if id == session.get('user_id'): return "Không thể tự xóa chính mình!", 400
    db = get_db(); cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id=%s", (id,))
    db.commit(); db.close()
    return redirect(url_for('admin_users'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000)
