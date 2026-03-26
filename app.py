from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import datetime
import pandas as pd

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'dev'

db = SQLAlchemy(app)

class Caixa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True)
    vendedor = db.Column(db.String(50))
    data = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    itens = db.relationship('Item', backref='caixa', lazy=True)


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



@app.route('/')
def index():
    busca = request.args.get('busca')

    if busca:
        caixas = Caixa.query.filter(
            (Caixa.codigo.contains(busca)) |
            (Caixa.vendedor.contains(busca))
        ).all()
    else:
        caixas = Caixa.query.all()

    return render_template('index.html', caixas=caixas)


@app.route('/nova_caixa', methods=['GET', 'POST'])
def nova_caixa():
    if request.method == 'POST':
        caixa = Caixa(
            codigo=f"CX-{int(datetime.datetime.now().timestamp())}",
            vendedor=request.form['vendedor']
        )
        db.session.add(caixa)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('criar_caixa.html')


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
        return redirect(url_for('index'))

    return render_template('criar_item.html', caixa_id=caixa_id)



def importar_excel():
    df = pd.read_excel('dados.xlsx')

    grupos = df.groupby('Vendedor')

    for vendedor, dados in grupos:
        caixa = Caixa(
            codigo=f"CX-{vendedor}",
            vendedor=str(vendedor)
        )

        db.session.add(caixa)
        db.session.commit()

        for _, row in dados.iterrows():
            item = Item(
                codigo=row['Código do produto'],
                descricao=row['Descrição do produto'],
                cor=row['Cor'],
                tamanho=row['Tamanho'],
                recebidas=int(row['Peças recebidas']),
                processadas=int(row['Peças processadas']),
                divergencia=int(row['Divergência']),
                caixa_id=caixa.id
            )

            db.session.add(item)

    db.session.commit()





if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()
        importar_excel() 

    app.run(debug=True)