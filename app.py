from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import datetime
import os
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'dev'
db = SQLAlchemy(app)


class Caixa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True)
    vendedor = db.Column(db.String(50))
    data = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50))
    descricao = db.Column(db.String(200))
    cor = db.Column(db.String(50))
    tamanho = db.Column(db.String(10))
    recebidas = db.Column(db.Integer)
    processadas = db.Column(db.Integer)
    divergencia = db.Column(db.Integer)
    caixa_id = db.Column(db.Integer, db.ForeignKey('caixa.id'))

class Conferencia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    caixa_id = db.Column(db.Integer)
    conferido_por = db.Column(db.String(50))
    data = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    observacao = db.Column(db.Text)


def gerar_codigo(prefixo):
    return f"{prefixo}-{int(datetime.datetime.now().timestamp())}"

def gerar_barcode(codigo):
    os.makedirs("static/barcodes", exist_ok=True)
    path = f"static/barcodes/{codigo}"
    CODE128 = barcode.get_barcode_class('code128')
    CODE128(codigo, writer=ImageWriter()).save(path)
    return f"barcodes/{codigo}.png"


@app.route('/')
def index():
    caixas = Caixa.query.all()
    return render_template('index.html', caixas=caixas)

@app.route('/nova_caixa', methods=['GET', 'POST'])
def nova_caixa():
    if request.method == 'POST':
        codigo = gerar_codigo("CX")
        gerar_barcode(codigo)

        caixa = Caixa(
            codigo=codigo,
            vendedor=request.form['vendedor']
        )
        db.session.add(caixa)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('criar_caixa.html')

@app.route('/caixa/<int:id>')
def detalhe_caixa(id):
    caixa = Caixa.query.get_or_404(id)
    itens = Item.query.filter_by(caixa_id=id).all()
    return render_template('detalhe_caixa.html', caixa=caixa, itens=itens)

@app.route('/item/<int:caixa_id>', methods=['GET', 'POST'])
def criar_item(caixa_id):
    if request.method == 'POST':
        item = Item(
            codigo=request.form['codigo'],
            descricao=request.form['descricao'],
            cor=request.form['cor'],
            tamanho=request.form['tamanho'],
            recebidas=int(request.form['recebidas']),
            processadas=int(request.form['processadas']),
            divergencia=int(request.form['divergencia']),
            caixa_id=caixa_id
        )
        db.session.add(item)
        db.session.commit()
        return redirect(url_for('detalhe_caixa', id=caixa_id))

    return render_template('criar_item.html', caixa_id=caixa_id)

@app.route('/buscar', methods=['GET', 'POST'])
def buscar():
    caixa = None
    if request.method == 'POST':
        codigo = request.form['codigo']
        caixa = Caixa.query.filter_by(codigo=codigo).first()
    return render_template('buscar_caixa.html', caixa=caixa)

@app.route('/conferencia/<int:id>', methods=['GET', 'POST'])
def conferencia(id):
    caixa = Caixa.query.get_or_404(id)

    if request.method == 'POST':
        conf = Conferencia(
            caixa_id=id,
            conferido_por=request.form['nome'],
            observacao=request.form['obs']
        )
        db.session.add(conf)
        db.session.commit()

    return render_template('conferencia.html', caixa=caixa)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)