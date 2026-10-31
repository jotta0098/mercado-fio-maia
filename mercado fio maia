
import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask, request, redirect, url_for, session,
    flash, render_template_string
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import escape

# =====================================================
# CONFIGURAÇÃO
# =====================================================

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fio-maia-chave-local-2026")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mercado.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Faça login para continuar."


# =====================================================
# BANCO DE DADOS
# =====================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="admin")
    active = db.Column(db.Boolean, default=True)

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
    price = db.Column(db.Float, nullable=False, default=0)
    cost = db.Column(db.Float, nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    minimum_stock = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.now)


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total = db.Column(db.Float, nullable=False)
    received = db.Column(db.Float, nullable=False)
    change = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(30), default="Dinheiro")
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))


class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    product_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)


class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# =====================================================
# FUNÇÕES AUXILIARES
# =====================================================

def admin_required(function):
    @wraps(function)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != "admin":
            flash("Você não tem permissão para acessar esta área.", "erro")
            return redirect(url_for("dashboard"))
        return function(*args, **kwargs)
    return wrapper


def money(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def get_cart():
    return session.get("cart", {})


def cart_details():
    cart = get_cart()
    items = []
    total = 0

    for product_id, quantity in cart.items():
        product = db.session.get(Product, int(product_id))
        if product:
            subtotal = product.price * quantity
            items.append({
                "product": product,
                "quantity": quantity,
                "subtotal": subtotal
            })
            total += subtotal

    return items, total


# =====================================================
# VISUAL DO SISTEMA
# =====================================================

BASE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mercadinho Fio Maia</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#f3f5f7;font-family:Arial,sans-serif;color:#20252b}
header{background:#123d2b;color:white;padding:20px 5%;display:flex;
justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
header h2{margin:0}
nav{background:#1b5139;padding:13px 5%;display:flex;gap:18px;flex-wrap:wrap}
nav a{color:white;text-decoration:none;font-weight:bold}
main{max-width:1150px;margin:25px auto;padding:0 16px}
.card{background:white;padding:22px;border-radius:12px;margin-bottom:18px;
box-shadow:0 2px 10px #0000000c}
h2,h3{margin-top:0}
input,select{width:100%;padding:12px;border:1px solid #ccc;border-radius:7px;
margin:6px 0 14px;font-size:15px}
button,.btn{background:#17643f;color:white;padding:12px 17px;border:0;
border-radius:7px;cursor:pointer;text-decoration:none;display:inline-block;font-size:14px}
button:hover,.btn:hover{background:#10452c}
.danger{background:#b52d2d}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:15px}
.stat{background:white;padding:20px;border-radius:12px}
.stat strong{display:block;font-size:25px;margin-top:10px;color:#17643f}
table{width:100%;border-collapse:collapse;background:white}
th,td{text-align:left;padding:12px;border-bottom:1px solid #eee}
th{background:#edf3ef}
.alert{padding:12px;background:#e5f5e9;border-radius:7px;margin:10px 0}
.erro{background:#ffe5e5}
small{color:#666}
.actions{display:flex;gap:8px;flex-wrap:wrap}
@media(max-width:600px){table{font-size:12px}th,td{padding:8px}}
</style>
</head>
<body>
<header>
<h2>🏪 Mercadinho Fio Maia</h2>
{% if current_user.is_authenticated %}
<span>Olá, {{ current_user.name }}</span>
{% endif %}
</header>
{% if current_user.is_authenticated %}
<nav>
<a href="{{ url_for('dashboard') }}">Início</a>
<a href="{{ url_for('products') }}">Produtos e estoque</a>
<a href="{{ url_for('pos') }}">Frente de caixa</a>
<a href="{{ url_for('sales') }}">Histórico de vendas</a>
<a href="{{ url_for('logout') }}">Sair</a>
</nav>
{% endif %}
<main>
{% for category, message in get_flashed_messages(with_categories=true) %}
<div class="alert {{ 'erro' if category == 'erro' else '' }}">{{ message }}</div>
{% endfor %}
{{ body|safe }}
</main>
</body>
</html>
"""


def page(template, **kwargs):
    content = render_template_string(template, **kwargs)
    return render_template_string(BASE, body=content)


# =====================================================
# PRIMEIRO ACESSO
# =====================================================

@app.route("/setup", methods=["GET", "POST"])
def setup():
    if User.query.filter_by(role="admin").first():
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not name or not username:
            flash("Preencha todos os campos.", "erro")
        elif len(password) < 8:
            flash("A senha precisa ter pelo menos 8 caracteres.", "erro")
        elif password != confirm:
            flash("As senhas não são iguais.", "erro")
        elif User.query.filter_by(username=username).first():
            flash("Esse usuário já existe.", "erro")
        else:
            user = User(name=name, username=username, role="admin")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Administrador criado! Faça seu login.")
            return redirect(url_for("login"))

    return page("""
    <div class="card">
    <h2>Configuração inicial</h2>
    <p>Crie o usuário administrador do mercadinho.</p>
    <form method="post">
    Nome completo<input name="name" required>
    Usuário<input name="username" required>
    Senha<input type="password" name="password" minlength="8" required>
    Repita a senha<input type="password" name="confirm" required>
    <button>Criar administrador</button>
    </form></div>
    """)


# =====================================================
# LOGIN
# =====================================================

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if not User.query.filter_by(role="admin").first():
        return redirect(url_for("setup"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and user.active and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Usuário ou senha incorretos.", "erro")

    return page("""
    <div class="card" style="max-width:430px;margin:40px auto">
    <h2>Entrar no sistema</h2>
    <form method="post">
    Usuário<input name="username" required>
    Senha<input type="password" name="password" required>
    <button style="width:100%">Entrar</button>
    </form></div>
    """)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("login"))


# =====================================================
# PAINEL PRINCIPAL
# =====================================================

@app.route("/dashboard")
@login_required
def dashboard():
    products = Product.query.count()
    low_stock = Product.query.filter(Product.stock <= Product.minimum_stock).count()

    today = datetime.now().date()
    today_sales = Sale.query.filter(
        db.func.date(Sale.created_at) == today.isoformat()
    ).all()

    total_today = sum(s.total for s in today_sales)

    return page("""
    <h2>Painel principal</h2>
    <div class="grid">
      <div class="stat">Produtos cadastrados<strong>{{ products }}</strong></div>
      <div class="stat">Produtos com estoque baixo<strong>{{ low_stock }}</strong></div>
      <div class="stat">Vendas de hoje<strong>{{ sales_count }}</strong></div>
      <div class="stat">Total vendido hoje<strong>{{ total }}</strong></div>
    </div>
    <div class="card" style="margin-top:20px">
    <h3>Acesso rápido</h3>
    <div class="actions">
    <a class="btn" href="{{ url_for('products') }}">Cadastrar produto</a>
    <a class="btn" href="{{ url_for('pos') }}">Abrir caixa</a>
    <a class="btn" href="{{ url_for('sales') }}">Ver vendas</a>
    </div></div>
    """,
    products=products,
    low_stock=low_stock,
    sales_count=len(today_sales),
    total=money(total_today))


# =====================================================
# CADASTRO E ESTOQUE DE PRODUTOS
# =====================================================

@app.route("/products", methods=["GET", "POST"])
@login_required
def products():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip()

        try:
            price = float(request.form.get("price", "0").replace(",", "."))
            cost = float(request.form.get("cost", "0").replace(",", "."))
            stock = int(request.form.get("stock", "0"))
            minimum = int(request.form.get("minimum", "5"))
        except ValueError:
            flash("Confira os valores informados.", "erro")
            return redirect(url_for("products"))

        if not name or not code or price < 0 or cost < 0 or stock < 0 or minimum < 0:
            flash("Preencha os dados corretamente.", "erro")
        elif Product.query.filter_by(code=code).first():
            flash("Já existe um produto com esse código.", "erro")
        else:
            product = Product(
                name=name, code=code, price=price,
                cost=cost, stock=stock, minimum_stock=minimum
            )
            db.session.add(product)
            db.session.flush()

            if stock > 0:
                db.session.add(StockMovement(
                    product_id=product.id,
                    description="Estoque inicial",
                    quantity=stock,
                    user_id=current_user.id
                ))

            db.session.commit()
            flash("Produto cadastrado com sucesso!")

        return redirect(url_for("products"))

    search = request.args.get("q", "").strip()
    query = Product.query

    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f"%{search}%"),
                Product.code.ilike(f"%{search}%")
            )
        )

    product_list = query.order_by(Product.name).all()

    return page("""
    <div class="card">
    <h2>Cadastrar produto</h2>
    <form method="post">
    <div class="grid">
      <div>Nome do produto<input name="name" placeholder="Ex.: Café" required></div>
      <div>Código / código de barras<input name="code" required></div>
      <div>Preço de compra (R$)<input name="cost" type="number" min="0" step="0.01" value="0"></div>
      <div>Preço de venda (R$)<input name="price" type="number" min="0" step="0.01" required></div>
      <div>Quantidade inicial<input name="stock" type="number" min="0" value="0" required></div>
      <div>Estoque mínimo<input name="minimum" type="number" min="0" value="5"></div>
    </div>
    <button>Cadastrar produto</button>
    </form></div>

    <div class="card">
    <h2>Produtos cadastrados</h2>
    <form method="get">
    <input name="q" value="{{ search }}" placeholder="Pesquisar por nome ou código">
    <button>Pesquisar</button>
    </form>
    <div style="overflow-x:auto">
    <table>
    <tr><th>Produto</th><th>Código</th><th>Preço</th><th>Estoque</th><th>Ação</th></tr>
    {% for p in products %}
    <tr>
    <td>{{ p.name }}</td><td>{{ p.code }}</td>
    <td>{{ money(p.price) }}</td>
    <td>{{ p.stock }}</td>
    <td><a href="{{ url_for('add_stock', product_id=p.id) }}">Adicionar estoque</a></td>
    </tr>
    {% else %}
    <tr><td colspan="5">Nenhum produto encontrado.</td></tr>
    {% endfor %}
    </table></div></div>
    """, products=product_list, search=search, money=money)


@app.route("/stock/<int:product_id>", methods=["GET", "POST"])
@login_required
def add_stock(product_id):
    product = db.get_or_404(Product, product_id)

    if request.method == "POST":
        try:
            quantity = int(request.form.get("quantity", "0"))
        except ValueError:
            quantity = 0

        if quantity <= 0:
            flash("Informe uma quantidade maior que zero.", "erro")
        else:
            product.stock += quantity
            db.session.add(StockMovement(
                product_id=product.id,
                description="Entrada de mercadoria",
                quantity=quantity,
                user_id=current_user.id
            ))
            db.session.commit()
            flash("Estoque atualizado!")
            return redirect(url_for("products"))

    return page("""
    <div class="card">
    <h2>Adicionar estoque</h2>
    <p>Produto: <b>{{ product.name }}</b></p>
    <p>Estoque atual: <b>{{ product.stock }}</b></p>
    <form method="post">
    Quantidade recebida<input type="number" name="quantity" min="1" required>
    <button>Adicionar ao estoque</button>
    </form>
    <a href="{{ url_for('products') }}">Voltar</a>
    </div>
    """, product=product)


# =====================================================
# FRENTE DE CAIXA
# =====================================================

@app.route("/pos", methods=["GET", "POST"])
@login_required
def pos():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            code = request.form.get("code", "").strip()
            try:
                quantity = int(request.form.get("quantity", "1"))
            except ValueError:
                quantity = 0

            product = Product.query.filter(
                db.or_(Product.code == code, Product.name.ilike(code))
            ).first()

            if not product:
                flash("Produto não encontrado.", "erro")
            elif quantity <= 0:
                flash("Informe uma quantidade válida.", "erro")
            else:
                cart = get_cart()
                key = str(product.id)
                new_quantity = cart.get(key, 0) + quantity

                if new_quantity > product.stock:
                    flash(f"Estoque insuficiente. Disponível: {product.stock}.", "erro")
                else:
                    cart[key] = new_quantity
                    session["cart"] = cart
                    session.modified = True
                    flash("Produto adicionado ao carrinho.")

        elif action == "remove":
            cart = get_cart()
            cart.pop(request.form.get("product_id"), None)
            session["cart"] = cart
            session.modified = True

        elif action == "clear":
            session["cart"] = {}
            session.modified = True

        elif action == "finish":
            items, total = cart_details()

            try:
                received = float(request.form.get("received", "0").replace(",", "."))
            except ValueError:
                received = 0

            if not items:
                flash("O carrinho está vazio.", "erro")
            elif received < total:
                flash("O valor recebido é menor que o total da compra.", "erro")
            else:
                # Confere novamente o estoque antes de finalizar.
                for item in items:
                    if item["quantity"] > item["product"].stock:
                        flash(
                            f"Estoque insuficiente para {item['product'].name}.",
                            "erro"
                        )
                        return redirect(url_for("pos"))

                sale = Sale(
                    total=round(total, 2),
                    received=round(received, 2),
                    change=round(received - total, 2),
                    payment_method=request.form.get("payment_method", "Dinheiro"),
                    user_id=current_user.id
                )
                db.session.add(sale)
                db.session.flush()

                for item in items:
                    product = item["product"]
                    quantity = item["quantity"]
                    product.stock -= quantity

                    db.session.add(SaleItem(
                        sale_id=sale.id,
                        product_id=product.id,
                        product_name=product.name,
                        quantity=quantity,
                        unit_price=product.price,
                        subtotal=round(product.price * quantity, 2)
                    ))

                    db.session.add(StockMovement(
                        product_id=product.id,
                        description=f"Venda #{sale.id}",
                        quantity=-quantity,
                        user_id=current_user.id
                    ))

                db.session.commit()
                session["cart"] = {}
                session.modified = True

                flash(
                    f"Venda #{sale.id} concluída! Total: {money(total)} | "
                    f"Troco: {money(received - total)}"
                )
                return redirect(url_for("sale_detail", sale_id=sale.id))

    items, total = cart_details()
    return page("""
    <div class="card">
    <h2>🛒 Frente de caixa</h2>
    <form method="post">
    <input type="hidden" name="action" value="add">
    Código de barras ou nome do produto
    <input name="code" autofocus placeholder="Digite ou passe o leitor no código" required>
    Quantidade
    <input type="number" name="quantity" min="1" value="1" required>
    <button>Adicionar ao carrinho</button>
    </form></div>

    <div class="card">
    <h3>Produtos da compra</h3>
    <div style="overflow-x:auto">
    <table>
    <tr><th>Produto</th><th>Quantidade</th><th>Preço</th><th>Subtotal</th><th></th></tr>
    {% for item in items %}
    <tr>
    <td>{{ item.product.name }}</td>
    <td>{{ item.quantity }}</td>
    <td>{{ money(item.product.price) }}</td>
    <td>{{ money(item.subtotal) }}</td>
    <td>
    <form method="post">
    <input type="hidden" name="action" value="remove">
    <input type="hidden" name="product_id" value="{{ item.product.id }}">
    <button class="danger">Remover</button>
    </form>
    </td>
    </tr>
    {% else %}
    <tr><td colspan="5">Nenhum produto no carrinho.</td></tr>
    {% endfor %}
    </table></div>

    <h2>Total: {{ money(total) }}</h2>

    <form method="post">
    <input type="hidden" name="action" value="finish">
    Valor recebido (R$)
    <input type="number" name="received" min="{{ total }}" step="0.01" required>
    Forma de pagamento
    <select name="payment_method">
    <option>Dinheiro</option>
    <option>Pix</option>
    <option>Cartão de débito</option>
    <option>Cartão de crédito</option>
    </select>
    <button style="width:100%">FINALIZAR VENDA</button>
    </form>

    <form method="post" style="margin-top:12px">
    <input type="hidden" name="action" value="clear">
    <button class="danger">Cancelar compra</button>
    </form>
    </div>
    """, items=items, total=total, money=money)


# =====================================================
# HISTÓRICO DE VENDAS
# =====================================================

@app.route("/sales")
@login_required
def sales():
    sale_list = Sale.query.order_by(Sale.created_at.desc()).limit(200).all()

    return page("""
    <div class="card">
    <h2>Histórico de vendas</h2>
    <div style="overflow-x:auto">
    <table>
    <tr><th>Número</th><th>Data e horário</th><th>Total</th><th>Recebido</th><th>Troco</th><th></th></tr>
    {% for s in sales %}
    <tr>
    <td>#{{ s.id }}</td>
    <td>{{ s.created_at.strftime("%d/%m/%Y %H:%M:%S") }}</td>
    <td>{{ money(s.total) }}</td>
    <td>{{ money(s.received) }}</td>
    <td>{{ money(s.change) }}</td>
    <td><a href="{{ url_for('sale_detail', sale_id=s.id) }}">Detalhes</a></td>
    </tr>
    {% else %}
    <tr><td colspan="6">Nenhuma venda registrada.</td></tr>
    {% endfor %}
    </table></div></div>
    """, sales=sale_list, money=money)


@app.route("/sale/<int:sale_id>")
@login_required
def sale_detail(sale_id):
    sale = db.get_or_404(Sale, sale_id)
    items = SaleItem.query.filter_by(sale_id=sale.id).all()

    return page("""
    <div class="card">
    <h2>Venda #{{ sale.id }}</h2>
    <p>Data: {{ sale.created_at.strftime("%d/%m/%Y às %H:%M:%S") }}</p>
    <p>Pagamento: {{ sale.payment_method }}</p>
    <table>
    <tr><th>Produto</th><th>Quantidade</th><th>Preço</th><th>Subtotal</th></tr>
    {% for item in items %}
    <tr>
    <td>{{ item.product_name }}</td>
    <td>{{ item.quantity }}</td>
    <td>{{ money(item.unit_price) }}</td>
    <td>{{ money(item.subtotal) }}</td>
    </tr>
    {% endfor %}
    </table>
    <h3>Total: {{ money(sale.total) }}</h3>
    <p>Recebido: {{ money(sale.received) }}</p>
    <p>Troco: {{ money(sale.change) }}</p>
    <button onclick="window.print()">Imprimir comprovante</button>
    <a class="btn" href="{{ url_for('pos') }}">Nova venda</a>
    </div>
    """, sale=sale, items=items, money=money)


# =====================================================
# INICIAR A APLICAÇÃO
# =====================================================

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
