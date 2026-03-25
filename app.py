from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)


class Registro(db.Model):
    __tablename__ = "registros"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    categoria = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    data_registro = db.Column(db.Date, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Registro {self.id} - {self.nome}>"


@app.route("/")
def index():
    busca = request.args.get("busca", "").strip()
    categoria = request.args.get("categoria", "").strip()
    status = request.args.get("status", "").strip()

    query = Registro.query

    if busca:
        query = query.filter(Registro.nome.ilike(f"%{busca}%"))

    if categoria:
        query = query.filter(Registro.categoria == categoria)

    if status:
        query = query.filter(Registro.status == status)

    registros = query.order_by(Registro.id.desc()).all()

    categorias = (
        db.session.query(Registro.categoria)
        .distinct()
        .order_by(Registro.categoria.asc())
        .all()
    )
    categorias = [item[0] for item in categorias]

    status_list = (
        db.session.query(Registro.status)
        .distinct()
        .order_by(Registro.status.asc())
        .all()
    )
    status_list = [item[0] for item in status_list]

    total_registros = len(registros)
    total_valor = sum(registro.valor for registro in registros)

    return render_template(
        "index.html",
        registros=registros,
        categorias=categorias,
        status_list=status_list,
        busca=busca,
        categoria=categoria,
        status=status,
        total_registros=total_registros,
        total_valor=total_valor,
    )


@app.route("/criar", methods=["GET", "POST"])
def criar():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        categoria = request.form.get("categoria", "").strip()
        valor = request.form.get("valor", "").strip()
        status = request.form.get("status", "").strip()
        data_registro = request.form.get("data_registro", "").strip()

        if not all([nome, categoria, valor, status, data_registro]):
            flash("Preencha todos os campos.", "erro")
            return redirect(url_for("criar"))

        try:
            valor = float(valor.replace(",", "."))
        except ValueError:
            flash("O valor precisa ser numérico.", "erro")
            return redirect(url_for("criar"))

        try:
            data_registro = datetime.strptime(data_registro, "%Y-%m-%d").date()
        except ValueError:
            flash("Data inválida.", "erro")
            return redirect(url_for("criar"))

        novo_registro = Registro(
            nome=nome,
            categoria=categoria,
            valor=valor,
            status=status,
            data_registro=data_registro,
        )

        db.session.add(novo_registro)
        db.session.commit()

        flash("Registro criado com sucesso.", "sucesso")
        return redirect(url_for("index"))

    return render_template("create.html")


@app.route("/editar/<int:registro_id>", methods=["GET", "POST"])
def editar(registro_id):
    registro = Registro.query.get_or_404(registro_id)

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        categoria = request.form.get("categoria", "").strip()
        valor = request.form.get("valor", "").strip()
        status = request.form.get("status", "").strip()
        data_registro = request.form.get("data_registro", "").strip()

        if not all([nome, categoria, valor, status, data_registro]):
            flash("Preencha todos os campos.", "erro")
            return redirect(url_for("editar", registro_id=registro.id))

        try:
            valor = float(valor.replace(",", "."))
        except ValueError:
            flash("O valor precisa ser numérico.", "erro")
            return redirect(url_for("editar", registro_id=registro.id))

        try:
            data_registro = datetime.strptime(data_registro, "%Y-%m-%d").date()
        except ValueError:
            flash("Data inválida.", "erro")
            return redirect(url_for("editar", registro_id=registro.id))

        registro.nome = nome
        registro.categoria = categoria
        registro.valor = valor
        registro.status = status
        registro.data_registro = data_registro

        db.session.commit()

        flash("Registro atualizado com sucesso.", "sucesso")
        return redirect(url_for("index"))

    return render_template("edit.html", registro=registro)


@app.route("/excluir/<int:registro_id>", methods=["POST"])
def excluir(registro_id):
    registro = Registro.query.get_or_404(registro_id)

    db.session.delete(registro)
    db.session.commit()

    flash("Registro excluído com sucesso.", "sucesso")
    return redirect(url_for("index"))


@app.route("/init-db")
def init_db():
    with app.app_context():
        db.create_all()
    flash("Banco inicializado com sucesso.", "sucesso")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)