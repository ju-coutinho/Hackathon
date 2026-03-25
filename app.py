from datetime import datetime
from pathlib import Path
import os

from dotenv import load_dotenv
load_dotenv()

import barcode
from barcode.writer import ImageWriter

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)


# ================= MODELOS =================

class Caixa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo_caixa = db.Column(db.String(50), unique=True, nullable=False)
    vendedor = db.Column(db.String(100), nullable=False)
    destino = db.Column(db.String(150), nullable=False)
    status_caixa = db.Column(db.String(50), default="Aberta")
    barcode_arquivo = db.Column(db.String(255))
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)

    itens = db.relationship("ItemCaixa", backref="caixa", cascade="all, delete")


    @property
    def total_unidades(self):
        return sum(i.quantidade for i in self.itens)

    @property
    def todos_enviados(self):
        return all(i.enviado for i in self.itens) if self.itens else False


class ItemCaixa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo_item = db.Column(db.String(50), unique=True)
    nome_produto = db.Column(db.String(150))
    sku = db.Column(db.String(100))
    categoria = db.Column(db.String(100))
    quantidade = db.Column(db.Integer)
    enviado = db.Column(db.Boolean, default=False)
    barcode_arquivo = db.Column(db.String(255))

    caixa_id = db.Column(db.Integer, db.ForeignKey("caixa.id"))


class Conferencia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conferido_por = db.Column(db.String(100))
    quantidade_esperada = db.Column(db.Integer)
    quantidade_recebida = db.Column(db.Integer)
    tudo_certo = db.Column(db.Boolean)
    divergencias = db.Column(db.Text)
    data_conferencia = db.Column(db.DateTime, default=datetime.utcnow)

    caixa_id = db.Column(db.Integer, db.ForeignKey("caixa.id"))


# ================= FUNÇÕES =================

def gerar_codigo(prefixo):
    data = datetime.now().strftime("%Y%m%d")
    return f"{prefixo}-{data}-{int(datetime.now().timestamp())}"


def gerar_barcode(codigo):
    pasta = Path("static/barcodes")
    pasta.mkdir(parents=True, exist_ok=True)

    caminho = pasta / codigo
    code = barcode.get("code128", codigo, writer=ImageWriter())
    path = code.save(str(caminho))

    return path.replace("static/", "").replace("\\", "/")


def atualizar_status(caixa):
    if caixa.todos_enviados:
        caixa.status_caixa = "Pronta"
    else:
        caixa.status_caixa = "Pendente"


with app.app_context():
    db.create_all()


# ================= ROTAS =================

@app.route("/")
def index():
    caixas = Caixa.query.order_by(Caixa.id.desc()).all()
    return render_template("index.html", caixas=caixas)


@app.route("/nova-caixa", methods=["GET", "POST"])
def nova_caixa():
    if request.method == "POST":
        vendedor = request.form["vendedor"]
        destino = request.form["destino"]

        codigo = gerar_codigo("CX")
        barcode_path = gerar_barcode(codigo)

        caixa = Caixa(
            codigo_caixa=codigo,
            vendedor=vendedor,
            destino=destino,
            barcode_arquivo=barcode_path
        )

        db.session.add(caixa)
        db.session.commit()

        return redirect(url_for("detalhe_caixa", id=caixa.id))

    return render_template("criar_caixa.html")


@app.route("/caixa/<int:id>")
def detalhe_caixa(id):
    caixa = Caixa.query.get_or_404(id)
    return render_template("detalhe_caixa.html", caixa=caixa)


@app.route("/caixa/<int:id>/item", methods=["POST"])
def add_item(id):
    caixa = Caixa.query.get_or_404(id)

    codigo = gerar_codigo("IT")
    barcode_path = gerar_barcode(codigo)

    item = ItemCaixa(
        codigo_item=codigo,
        nome_produto=request.form["nome"],
        sku=request.form["sku"],
        categoria=request.form["categoria"],
        quantidade=int(request.form["quantidade"]),
        enviado="enviado" in request.form,
        barcode_arquivo=barcode_path,
        caixa_id=caixa.id
    )

    db.session.add(item)
    atualizar_status(caixa)
    db.session.commit()

    return redirect(url_for("detalhe_caixa", id=id))


@app.route("/toggle/<int:id>")
def toggle(id):
    item = ItemCaixa.query.get_or_404(id)
    item.enviado = not item.enviado

    atualizar_status(item.caixa)
    db.session.commit()

    return redirect(url_for("detalhe_caixa", id=item.caixa_id))


@app.route("/buscar", methods=["GET", "POST"])
def buscar():
    caixa = None
    if request.method == "POST":
        codigo = request.form["codigo"]
        caixa = Caixa.query.filter_by(codigo_caixa=codigo).first()
    return render_template("buscar_caixa.html", caixa=caixa)


@app.route("/conferir/<int:id>", methods=["GET", "POST"])
def conferir(id):
    caixa = Caixa.query.get_or_404(id)

    if request.method == "POST":
        recebida = int(request.form["recebida"])
        esperada = caixa.total_unidades

        conf = Conferencia(
            conferido_por=request.form["nome"],
            quantidade_esperada=esperada,
            quantidade_recebida=recebida,
            tudo_certo=(esperada == recebida),
            divergencias=request.form["div"],
            caixa_id=id
        )

        db.session.add(conf)
        db.session.commit()

        return redirect(url_for("relatorio", id=id))

    return render_template("conferencia.html", caixa=caixa)


@app.route("/relatorio/<int:id>")
def relatorio(id):
    caixa = Caixa.query.get_or_404(id)
    conf = Conferencia.query.filter_by(caixa_id=id).order_by(Conferencia.id.desc()).first()
    return render_template("relatorio.html", caixa=caixa, conf=conf)


@app.route("/etiqueta/caixa/<int:id>")
def etiqueta_caixa(id):
    caixa = Caixa.query.get_or_404(id)
    return render_template("etiqueta_caixa.html", caixa=caixa)


@app.route("/etiqueta/item/<int:id>")
def etiqueta_item(id):
    item = ItemCaixa.query.get_or_404(id)
    return render_template("etiqueta_item.html", item=item)


if __name__ == "__main__":
    app.run(debug=True)