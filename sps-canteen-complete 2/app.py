
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from models import db, User, MenuItem, Order
from sqlalchemy import or_
import socket

app = Flask(__name__)
app.config['SECRET_KEY'] = 'canteen-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def seed_default_data():
    created = False
    if not User.query.filter_by(username="kitchen").first():
        db.session.add(User(username="kitchen", password="kitchen123", role="kitchen"))
        created = True
    if MenuItem.query.count() == 0:
        db.session.add_all([
            MenuItem(name="Chicken Wrap", price=6.50, available=True),
            MenuItem(name="Veggie Sushi Box", price=5.00, available=True),
            MenuItem(name="Fruit Cup", price=3.00, available=True),
            MenuItem(name="Iced Tea", price=2.80, available=True),
            MenuItem(name="Beef Pie", price=4.50, available=True),
            MenuItem(name="Sausage Roll", price=3.80, available=True),
            MenuItem(name="Ham & Cheese Toastie", price=4.20, available=True),
            MenuItem(name="Margherita Pizza Slice", price=3.50, available=True),
            MenuItem(name="Chicken Salad Bowl", price=6.90, available=True),
            MenuItem(name="Yoghurt Parfait", price=3.70, available=True),
            MenuItem(name="Apple Juice", price=2.50, available=True),
            MenuItem(name="Water 600ml", price=2.00, available=True),
        ])
        created = True
    if created:
        db.session.commit()

def login_required(view):
    def wrapped(*a, **kw):
        if 'user_id' not in session:
            flash("Please log in first.", "error")
            return redirect(url_for('login'))
        return view(*a, **kw)
    wrapped.__name__ = view.__name__
    return wrapped

def kitchen_required(view):
    def wrapped(*a, **kw):
        if 'user_id' not in session:
            flash("Please log in first.", "error")
            return redirect(url_for('login'))
        u = User.query.get(session['user_id'])
        if not u or u.role != "kitchen":
            abort(403)
        return view(*a, **kw)
    wrapped.__name__ = view.__name__
    return wrapped

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u = request.form.get('username', '').strip()
        p = request.form.get('password', '').strip()
        if not u or not p:
            flash("Username and password required.", "error")
            return redirect(url_for('register'))
        if User.query.filter_by(username=u).first():
            flash("Username taken.", "error")
            return redirect(url_for('register'))
        db.session.add(User(username=u, password=p, role='student'))
        db.session.commit()
        flash("Account created. Please login.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username', '').strip()
        p = request.form.get('password', '').strip()
        user = User.query.filter_by(username=u).first()
        if not user or user.password != p:
            flash("Invalid username or password.", "error")
            return redirect(url_for('login'))
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        return redirect(url_for('menu'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for('home'))

@app.route('/menu', methods=['GET', 'POST'])
@login_required
def menu():
    items = MenuItem.query.filter(or_(MenuItem.available == True, MenuItem.available.is_(None))).all()
    if request.method == 'POST':
        item_id = request.form.get('item_id')
        qty_raw = request.form.get('quantity', '1')
        try:
            qty = int(qty_raw)
        except ValueError:
            qty = 1
        item = MenuItem.query.get(item_id)
        if not item:
            flash("Invalid item.", "error")
            return redirect(url_for('menu'))
        db.session.add(Order(user_id=session['user_id'], item_id=item.id, quantity=max(1, qty)))
        db.session.commit()
        flash(f"Ordered {max(1, qty)} × {item.name}.", "success")
        return redirect(url_for('my_orders'))
    return render_template('menu.html', items=items)

@app.route('/my-orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.created_at.desc()).all()
    return render_template('my_orders.html', orders=orders)

@app.route('/kitchen/orders')
@kitchen_required
def kitchen_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('kitchen_orders.html', orders=orders)

@app.route('/kitchen/menu', methods=['GET', 'POST'])
@kitchen_required
def kitchen_menu():
    if request.method == 'POST':
        n = request.form.get('name', '').strip()
        p_raw = request.form.get('price', '').strip()
        a = 'available' in request.form
        if not n or not p_raw:
            flash("Name and price required.", "error")
            return redirect(url_for('kitchen_menu'))
        try:
            p = float(p_raw)
        except ValueError:
            flash("Price must be a number.", "error")
            return redirect(url_for('kitchen_menu'))
        db.session.add(MenuItem(name=n, price=p, available=a))
        db.session.commit()
        flash("Menu item added.", "success")
        return redirect(url_for('kitchen_menu'))
    items = MenuItem.query.order_by(MenuItem.id.asc()).all()
    return render_template('kitchen_menu.html', items=items)

@app.route('/view_menu', methods=['GET', 'POST'])
@login_required
def view_menu():
    return redirect(url_for('menu'))

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', message="Access denied."), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', message="Page not found."), 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_default_data()
    # Auto-find a free port starting from 5001
    port = 5001
    while True:
        try:
            with socket.socket() as s:
                s.bind(("127.0.0.1", port))
            break
        except OSError:
            port += 1
    app.run(debug=True, port=port)
