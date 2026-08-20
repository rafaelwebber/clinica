from db import SessionLocal
conn = SessionLocal()

#nao lembro para que eu queria usar essa função
def buscar_id(id_mensagem):
    row = conn.fetch_one(
        """SELECT * 
        FROM template 
        WHERE id_mensagem=:id_mensagem""",
        {"id_mensagem": id_mensagem}
    )
    return (row)