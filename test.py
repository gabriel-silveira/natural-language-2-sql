from src.tools import db_query

result = db_query("SELECT * FROM candidatos ORDER BY id_candidato LIMIT 10")

print(result)