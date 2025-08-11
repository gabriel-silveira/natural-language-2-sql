from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from langchain_community.utilities import SQLDatabase
from src.config import MARIADB_URI


# --------- Conexão com MariaDB ---------
def build_engine() -> Engine:
    uri = MARIADB_URI
    assert uri, "Defina MARIADB_URI"
    engine = create_engine(
        uri,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=1800,  # evita conexões zumbis
        connect_args={"connect_timeout": 5},
    )
    return engine

ENGINE: Engine = build_engine()

DB = SQLDatabase.from_uri(MARIADB_URI, sample_rows_in_table_info=2)

