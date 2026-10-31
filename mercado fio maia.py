import os
from datetime import datetime, date
from functools import wraps
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import Flask, request, redirect, url_for, session, flash, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import func, or_
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'troque-esta-chave-em-producao')
database_url = os.environ.get('DATABASE_URL', 'sqlite:///mercado.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}
if database_url.startswith('sqlite:'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'connect_args': {'check_same_thread': False}}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para continuar.'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)

    @property
    def is_active(self):
        return self.active

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(60), unique=True, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    cost = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    minimum_stock = db.Column(db.Integer, nullable=False, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    received = db.Column(db.Numeric(10, 2), nullable=False)
    change = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(30), default='Dinheiro')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)


class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def as_money(value):
    try:
        amount = Decimal(str(value or '0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        amount = Decimal('0.00')
    return amount


def money(value):
    return f"R$ {as_money(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper


def get_cart():
    return session.get('cart', {})


def cart_details():
    result, total = [], Decimal('0.00')
    for product_id, quantity in get_cart().items():
        product = db.session.get(Product, int(product_id))
        if product and int(quantity) > 0:
            subtotal = as_money(product.price) * int(quantity)
            result.append({'product': product, 'quantity': int(quantity), 'subtotal': subtotal})
            total += subtotal
    return result, total


BASE = r'''<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mercadinho Fio Maia</title>
<style>
:root{--green:#174d35;--green2:#216b48;--bg:#f4f6f5;--ink:#202923}*{box-sizing:border-box}body{margin:0;background:var(--bg);font-family:Arial,sans-serif;color:var(--ink)}header{background:var(--green);color:white;padding:18px max(4%,calc((100% - 1180px)/2));display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}header h1{font-size:21px;margin:0}nav{background:#216342;padding:12px max(4%,calc((100% - 1180px)/2));display:flex;gap:17px;flex-wrap:wrap}nav a{color:white;text-decoration:none;font-weight:700;font-size:14px}main{max-width:1180px;margin:26px auto;padding:0 16px}.card,.stat{background:white;padding:21px;border-radius:13px;margin-bottom:18px;box-shadow:0 3px 14px #14251b0b}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:14px}.stat span{color:#66736b;font-size:14px}.stat strong{display:block;font-size:25px;color:var(--green);margin-top:9px}input,select{width:100%;padding:12px;border:1px solid #ccd5ce;border-radius:8px;margin:6px 0 14px;font-size:15px;background:white}button,.btn{display:inline-block;background:var(--green2);color:white;border:0;border-radius:8px;padding:12px 16px;text-decoration:none;cursor:pointer;font-weight:700;font-size:14px}button:hover,.btn:hover{background:var(--green)}.danger{background:#b52d35}.muted{color:#68756d}.alert{padding:12px 15px;background:#e2f4e8;border-radius:8px;margin:10px 0 16px}.alert.erro{background:#ffe6e6;color:#8d2020}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;background:white;min-width:580px}th,td{text-align:left;padding:12px;border-bottom:1px solid #edf0ed}th{background:#edf3ef}.actions{display:flex;gap:8px;flex-wrap:wrap}.low{color:#b52d35;font-weight:bold}.total{font-size:25px;font-weight:bold;color:var(--green)}label{font-size:14px;font-weight:600}@media(max-width:600px){main{margin:16px auto}header{padding:16px}nav{gap:12px;padding:12px 16px}nav a{font-size:13px}.card{padding:16px}}
@media print{header,nav,.no-print,button,.btn{display:none!important}body{background:white}.card{box-shadow:none}}
</style></head><body><header><h1>🏪 Mercadinho Fio Maia</h1>{% if current_user.is_authenticated %}<span>Olá, {{ current_user.name }}</span>{% endif %}</header>
{% if current_user.is_authenticated %}<nav><a href="{{ url_for('dashboard') }}">Início</a><a href="{{ url_for('products') }}">Produtos e estoque</a><a href="{{ url_for('pos') }}">Frente de caixa</a><a href="{{ url_for('sales') }}">Histórico de vendas</a><a href="{{ url_for('logout') }}">Sair</a></nav>{% endif %}
<main>{% for category,message in get_flashed_messages(with_categories=true) %}<div class="alert {{ 'erro' if category=='erro' else '' }}">{{ message }}</div>{% endfor %}{{ body|safe }}</main></body></html>'''


def page(template, **kwargs):
    body = render_template_string(template, **kwargs)
    return render_template_string(BASE, body=body)


@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if User.query.first():
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        if not name or not username:
            flash('Preencha todos os campos.', 'erro')
        elif len(password) < 8:
            flash('A senha precisa ter pelo menos 8 caracteres.', 'erro')
        elif password != confirm:
            flash('As senhas não são iguais.', 'erro')
        else:
            user = User(name=name, username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Administrador criado! Entre com seu usuário e senha.')
            return redirect(url_for('login'))
    return page('''<div class="card" style="max-width:480px;margin:35px auto"><h2>Configuração inicial</h2><p class="muted">Crie o administrador do mercadinho.</p><form method="post"><label>Nome completo</label><input name="name" required><label>Usuário</label><input name="username" required><label>Senha (mínimo 8 caracteres)</label><input type="password" name="password" minlength="8" required><label>Repita a senha</label><input type="password" name="confirm" required><button style="width:100%">Criar administrador</button></form></div>''')


@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if not User.query.first():
        return redirect(url_for('setup'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.active and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha incorretos.', 'erro')
    return page('''<div class="card" style="max-width:430px;margin:40px auto"><h2>Entrar no sistema</h2><form method="post"><label>Usuário</label><input name="username" autocomplete="username" required><label>Senha</label><input type="password" name="password" autocomplete="current-password" required><button style="width:100%">Entrar</button></form></div>''')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    products_count = Product.query.count()
    low_stock = Product.query.filter(Product.stock <= Product.minimum_stock).count()
    today = date.today().isoformat()
    today_sales = Sale.query.filter(func.date(Sale.created_at) == today).all()
    total_today = sum((as_money(s.total) for s in today_sales), Decimal('0.00'))
    return page('''<h2>Painel principal</h2><div class="grid"><div class="stat"><span>Produtos cadastrados</span><strong>{{ products }}</strong></div><div class="stat"><span>Produtos com estoque baixo</span><strong>{{ low_stock }}</strong></div><div class="stat"><span>Vendas de hoje</span><strong>{{ sales_count }}</strong></div><div class="stat"><span>Total vendido hoje</span><strong>{{ total }}</strong></div></div><div class="card"><h3>Acesso rápido</h3><div class="actions"><a class="btn" href="{{ url_for('products') }}">Cadastrar produto</a><a class="btn" href="{{ url_for('pos') }}">Abrir caixa</a><a class="btn" href="{{ url_for('sales') }}">Ver vendas</a></div></div>''', products=products_count, low_stock=low_stock, sales_count=len(today_sales), total=money(total_today))


@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip()
        try:
            price = as_money(request.form.get('price'))
            cost = as_money(request.form.get('cost'))
            stock = int(request.form.get('stock', '0'))
            minimum = int(request.form.get('minimum', '5'))
        except (ValueError, InvalidOperation):
            flash('Confira os valores informados.', 'erro')
            return redirect(url_for('products'))
        if not name or not code or price < 0 or cost < 0 or stock < 0 or minimum < 0:
            flash('Preencha os dados corretamente.', 'erro')
        elif Product.query.filter_by(code=code).first():
            flash('Já existe um produto com esse código.', 'erro')
        else:
            product = Product(name=name, code=code, price=price, cost=cost, stock=stock, minimum_stock=minimum)
            db.session.add(product)
            db.session.flush()
            if stock:
                db.session.add(StockMovement(product_id=product.id, description='Estoque inicial', quantity=stock, user_id=current_user.id))
            db.session.commit()
            flash('Produto cadastrado com sucesso!')
        return redirect(url_for('products'))
    search = request.args.get('q', '').strip()
    query = Product.query
    if search:
        query = query.filter(or_(Product.name.ilike(f'%{search}%'), Product.code.ilike(f'%{search}%')))
    product_list = query.order_by(Product.name).all()
    return page('''<div class="card"><h2>Cadastrar produto</h2><form method="post"><div class="grid"><div><label>Nome do produto</label><input name="name" placeholder="Ex.: Café" required></div><div><label>Código / código de barras</label><input name="code" required></div><div><label>Preço de compra (R$)</label><input name="cost" type="number" min="0" step="0.01" value="0"></div><div><label>Preço de venda (R$)</label><input name="price" type="number" min="0" step="0.01" required></div><div><label>Quantidade inicial</label><input name="stock" type="number" min="0" value="0" required></div><div><label>Estoque mínimo</label><input name="minimum" type="number" min="0" value="5"></div></div><button>Cadastrar produto</button></form></div><div class="card"><h2>Produtos cadastrados</h2><form method="get"><input name="q" value="{{ search }}" placeholder="Pesquisar por nome ou código"><button>Pesquisar</button></form><div class="table-wrap"><table><tr><th>Produto</th><th>Código</th><th>Preço</th><th>Estoque</th><th>Ação</th></tr>{% for p in products %}<tr><td>{{ p.name }}</td><td>{{ p.code }}</td><td>{{ money(p.price) }}</td><td class="{{ 'low' if p.stock <= p.minimum_stock else '' }}">{{ p.stock }}</td><td><a href="{{ url_for('add_stock', product_id=p.id) }}">Adicionar estoque</a></td></tr>{% else %}<tr><td colspan="5">Nenhum produto encontrado.</td></tr>{% endfor %}</table></div></div>''', products=product_list, search=search, money=money)


@app.route('/stock/<int:product_id>', methods=['GET', 'POST'])
@login_required
def add_stock(product_id):
    product = db.get_or_404(Product, product_id)
    if request.method == 'POST':
        try:
            quantity = int(request.form.get('quantity', '0'))
        except ValueError:
            quantity = 0
        if quantity <= 0:
            flash('Informe uma quantidade maior que zero.', 'erro')
        else:
            product.stock += quantity
            db.session.add(StockMovement(product_id=product.id, description='Entrada de mercadoria', quantity=quantity, user_id=current_user.id))
            db.session.commit()
            flash('Estoque atualizado!')
            return redirect(url_for('products'))
    return page('''<div class="card" style="max-width:520px"><h2>Adicionar estoque</h2><p>Produto: <b>{{ product.name }}</b></p><p>Estoque atual: <b>{{ product.stock }}</b></p><form method="post"><label>Quantidade recebida</label><input type="number" name="quantity" min="1" required><button>Adicionar ao estoque</button></form><a href="{{ url_for('products') }}">Voltar</a></div>''', product=product)


@app.route('/pos', methods=['GET', 'POST'])
@login_required
def pos():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            code = request.form.get('code', '').strip()
            try:
                quantity = int(request.form.get('quantity', '1'))
            except ValueError:
                quantity = 0
            product = Product.query.filter(or_(Product.code == code, Product.name.ilike(code))).first()
            if not product:
                flash('Produto não encontrado.', 'erro')
            elif quantity <= 0:
                flash('Informe uma quantidade válida.', 'erro')
            else:
                cart = get_cart()
                key = str(product.id)
                new_quantity = int(cart.get(key, 0)) + quantity
                if new_quantity > product.stock:
                    flash(f'Estoque insuficiente. Disponível: {product.stock}.', 'erro')
                else:
                    cart[key] = new_quantity
                    session['cart'] = cart
                    session.modified = True
                    flash('Produto adicionado ao carrinho.')
        elif action == 'remove':
            cart = get_cart()
            cart.pop(request.form.get('product_id'), None)
            session['cart'] = cart
            session.modified = True
        elif action == 'clear':
            session['cart'] = {}
            session.modified = True
        elif action == 'finish':
            items, total = cart_details()
            method = request.form.get('payment_method', 'Dinheiro')
            if method not in ['Dinheiro', 'Pix', 'Cartão de débito', 'Cartão de crédito']:
                method = 'Dinheiro'
            try:
                received = as_money(request.form.get('received', '0'))
            except InvalidOperation:
                received = Decimal('0.00')
            if not items:
                flash('O carrinho está vazio.', 'erro')
            elif received < total:
                flash('O valor recebido é menor que o total da compra.', 'erro')
            elif any(item['quantity'] > item['product'].stock for item in items):
                flash('Estoque insuficiente. Confira os produtos antes de finalizar.', 'erro')
                return redirect(url_for('pos'))
            else:
                sale = Sale(total=total, received=received, change=received-total, payment_method=method, user_id=current_user.id)
                db.session.add(sale)
                db.session.flush()
                for item in items:
                    product, quantity = item['product'], item['quantity']
                    product.stock -= quantity
                    db.session.add(SaleItem(sale_id=sale.id, product_id=product.id, product_name=product.name, quantity=quantity, unit_price=product.price, subtotal=item['subtotal']))
                    db.session.add(StockMovement(product_id=product.id, description=f'Venda #{sale.id}', quantity=-quantity, user_id=current_user.id))
                db.session.commit()
                session['cart'] = {}
                session.modified = True
                flash(f'Venda #{sale.id} concluída! Total: {money(total)} | Troco: {money(received-total)}')
                return redirect(url_for('sale_detail', sale_id=sale.id))
    items, total = cart_details()
    return page('''<div class="card"><h2>🛒 Frente de caixa</h2><form method="post"><input type="hidden" name="action" value="add"><label>Código de barras ou nome do produto</label><input name="code" autofocus placeholder="Digite ou passe o leitor no código" required><label>Quantidade</label><input type="number" name="quantity" min="1" value="1" required><button>Adicionar ao carrinho</button></form></div><div class="card"><h3>Produtos da compra</h3><div class="table-wrap"><table><tr><th>Produto</th><th>Quantidade</th><th>Preço</th><th>Subtotal</th><th></th></tr>{% for item in items %}<tr><td>{{ item.product.name }}</td><td>{{ item.quantity }}</td><td>{{ money(item.product.price) }}</td><td>{{ money(item.subtotal) }}</td><td><form method="post"><input type="hidden" name="action" value="remove"><input type="hidden" name="product_id" value="{{ item.product.id }}"><button class="danger">Remover</button></form></td></tr>{% else %}<tr><td colspan="5">Nenhum produto no carrinho.</td></tr>{% endfor %}</table></div><p class="total">Total: {{ money(total) }}</p><form method="post"><input type="hidden" name="action" value="finish"><label>Valor recebido (R$)</label><input type="number" name="received" min="{{ total }}" step="0.01" value="{{ total }}" required><label>Forma de pagamento</label><select name="payment_method"><option>Dinheiro</option><option>Pix</option><option>Cartão de débito</option><option>Cartão de crédito</option></select><button style="width:100%">FINALIZAR VENDA</button></form><form method="post" class="no-print" style="margin-top:12px"><input type="hidden" name="action" value="clear"><button class="danger">Cancelar compra</button></form></div>''', items=items, total=total, money=money)


@app.route('/sales')
@login_required
def sales():
    sale_list = Sale.query.order_by(Sale.created_at.desc()).limit(300).all()
    return page('''<div class="card"><h2>Histórico de vendas</h2><div class="table-wrap"><table><tr><th>Número</th><th>Data e horário</th><th>Pagamento</th><th>Total</th><th></th></tr>{% for s in sales %}<tr><td>#{{ s.id }}</td><td>{{ s.created_at.strftime('%d/%m/%Y %H:%M') }}</td><td>{{ s.payment_method }}</td><td>{{ money(s.total) }}</td><td><a href="{{ url_for('sale_detail', sale_id=s.id) }}">Detalhes</a></td></tr>{% else %}<tr><td colspan="5">Nenhuma venda registrada.</td></tr>{% endfor %}</table></div></div>''', sales=sale_list, money=money)


@app.route('/sale/<int:sale_id>')
@login_required
def sale_detail(sale_id):
    sale = db.get_or_404(Sale, sale_id)
    items = SaleItem.query.filter_by(sale_id=sale.id).all()
    return page('''<div class="card"><h2>Comprovante - Venda #{{ sale.id }}</h2><p>Data: {{ sale.created_at.strftime('%d/%m/%Y às %H:%M:%S') }}</p><p>Pagamento: {{ sale.payment_method }}</p><div class="table-wrap"><table><tr><th>Produto</th><th>Quantidade</th><th>Preço</th><th>Subtotal</th></tr>{% for item in items %}<tr><td>{{ item.product_name }}</td><td>{{ item.quantity }}</td><td>{{ money(item.unit_price) }}</td><td>{{ money(item.subtotal) }}</td></tr>{% endfor %}</table></div><h3>Total: {{ money(sale.total) }}</h3><p>Recebido: {{ money(sale.received) }}</p><p>Troco: {{ money(sale.change) }}</p><div class="actions no-print"><button onclick="window.print()">Imprimir comprovante</button><a class="btn" href="{{ url_for('pos') }}">Nova venda</a></div></div>''', sale=sale, items=items, money=money)


@app.get('/health')
def health():
    return {'status': 'ok'}, 200


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
