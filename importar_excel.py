import pandas as pd
from app import app, db, Caixa, ItemCaixa, gerar_codigo, gerar_barcode

with app.app_context():

    df = pd.read_excel("dados.xlsx")

    caixas_map = {}

    for _, row in df.iterrows():

        vendedor = row["vendedor"]
        destino = row["destino"]

        chave = f"{vendedor}-{destino}"

        if chave not in caixas_map:
            codigo = gerar_codigo("CX")
            barcode = gerar_barcode(codigo)

            caixa = Caixa(
                codigo_caixa=codigo,
                vendedor=vendedor,
                destino=destino,
                barcode_arquivo=barcode
            )

            db.session.add(caixa)
            db.session.flush()

            caixas_map[chave] = caixa

        caixa = caixas_map[chave]

        codigo_item = gerar_codigo("IT")
        barcode_item = gerar_barcode(codigo_item)

        item = ItemCaixa(
            codigo_item=codigo_item,
            nome_produto=row["produto"],
            sku=row["sku"],
            categoria=row["categoria"],
            quantidade=int(row["quantidade"]),
            enviado=bool(row["enviado"]),
            barcode_arquivo=barcode_item,
            caixa_id=caixa.id
        )

        db.session.add(item)

    db.session.commit()

print("Importação concluída!")