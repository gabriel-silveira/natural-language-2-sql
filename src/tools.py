from typing import List, Optional, Dict, Any
import re, json
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.db import DB, ENGINE
from src.config import OPENAI_API_KEY
from sqlalchemy import text

ALLOWED_TABLES = ["candidatos", "entrevistas"]


def build_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=OPENAI_API_KEY,
    )


def _enforce_allowed_tables(sql: str) -> None:
    if not ALLOWED_TABLES:
        return
    lowered = sql.lower()
    print("Verificando tabelas permitidas...")
    for t in ALLOWED_TABLES:
        if t and t.lower() in lowered:
            # encontrou uma permitida; seguimos checando proibidas
            print(f"Tabela permitida: {t}")
            pass
    # Checagem simples: se houver FROM/ JOIN com tabela fora da allowlist, recuse
    tokens = re.findall(r"(from|join)\s+([`\"\[\]]?[\w\.]+[`\"\[\]]?)", lowered)
    if tokens:
        for _, tbl in tokens:
            base = tbl.strip("`\"[]").split(".")[-1]
            if base not in {t.strip() for t in ALLOWED_TABLES if t}:
                raise ValueError(f"Tabela não permitida: {base}")


def _validate_select_only(sql: str) -> str:
    if not re.match(r"^\s*select\b", sql.strip(), re.IGNORECASE):
        raise ValueError("Somente consultas SELECT são permitidas.")
    # Impõe LIMIT se não houver
    if not re.search(r"\blimit\s+\d+\s*;?\s*$", sql, re.IGNORECASE):
        sql = sql.rstrip().rstrip(";") + " LIMIT 200;"
    return sql


# Cadeia NL → SQL
def build_nl2sql_chain() -> str:
    llm = build_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system",
        "Você gera SQL para MariaDB. Regras:\n"
        "- Gere apenas UM único SELECT válido.\n"
        "- Não use DML/DDL (INSERT/UPDATE/DELETE/CREATE/etc.).\n"
        "- Utilize apenas tabelas/colunas existentes no schema abaixo.\n"
        "- Se precisar limitar linhas, use LIMIT.\n"),
        ("system", "Schema disponível:\n{schema}"),
        ("human", "Pergunta do usuário:\n{question}\n\n"
            "Saída esperada: apenas o SQL (sem comentários nem explicações)."),
    ])

    return prompt | llm | StrOutputParser()


# --------- Ferramentas ---------

@tool("db_list_tables", return_direct=False)
def db_list_tables(_: str = "") -> List[str]:
    """Lista nomes de tabelas do banco que o agente pode usar."""
    names = sorted(DB.get_usable_table_names())
    if ALLOWED_TABLES:
        names = [n for n in names if n in ALLOWED_TABLES]
    return names


@tool("db_schema", return_direct=False)
def db_schema(table_names: Optional[List[str]] = None) -> str:
    """Retorna o schema (DDL simplificado + amostras) das tabelas informadas.
    Se não for passado, retorna das tabelas permitidas."""

    if table_names is None or len(table_names) == 0:
        table_names = db_list_tables()

    if ALLOWED_TABLES:
        for t in table_names:
            if t not in ALLOWED_TABLES:
                raise ValueError(f"Tabela não permitida: {t}")

    return DB.get_table_info(table_names)


@tool("db_query", return_direct=False)
def db_query(sql: str) -> Dict[str, Any]:
    """Executa SQL (somente SELECT) no MariaDB e retorna linhas como JSON.
    Garante LIMIT e recusa comandos de escrita."""

    _enforce_allowed_tables(sql)

    safe_sql = _validate_select_only(sql)

    with ENGINE.connect() as conn:
        conn.execute(text("SET SESSION time_zone = '+00:00'"))
        res = conn.execute(text(safe_sql))
        rows = [dict(r._mapping) for r in res]

    return {"sql": safe_sql, "rows": rows, "row_count": len(rows)}


@tool("db_nl2sql_rows", return_direct=True)
def db_nl2sql_rows(question: str) -> str:
    """
    Recebe uma pergunta em linguagem natural, gera um SELECT e retorna APENAS os resultados em JSON (array de objetos).
    """

    # 1) Debug
    print(f"Pergunta: {question}\n\n")

    # 1) Schema (pode otimizar passando só as tabelas candidatas)
    schema = DB.get_table_info(db_list_tables())

    # 1.5) Debug
    print(f"Schema: {schema}\n\n")

    # 2) Gera SQL
    chain = build_nl2sql_chain()
    sql = chain.invoke({"schema": schema, "question": question}).strip()

    # 2.5) Debug
    print(f"SQL gerado: {sql}\n\n")

    # 3) Segurança
    _enforce_allowed_tables(sql)
    safe_sql = _validate_select_only(sql)

    # 4) Executa e retorna SOMENTE os rows em JSON
    with ENGINE.connect() as conn:
        conn.execute(text("SET SESSION time_zone = '+00:00'"))
        result = conn.execute(text(safe_sql))
        rows = [dict(r._mapping) for r in result]

    # Retorna JSON puro (string). Como return_direct=True, o agente repassa isso sem alterações.
    return json.dumps(rows, ensure_ascii=False)
