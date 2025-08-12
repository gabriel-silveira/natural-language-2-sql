from typing import List, Optional, Dict, Any
import re, json
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sqlalchemy import text

from src.db import DB, ENGINE
from src.config import OPENAI_API_KEY, MARIADB_URI
from src.db import ALLOWED_TABLES
from src.services.export_db_catalog import export_db_catalog


@tool()
def run_query(sql: str) -> Dict[str, Any]:
    """Executa SQL (somente SELECT) no MariaDB e retorna linhas como JSON."""
    safe_sql = _validate_select_only(sql)

    with ENGINE.connect() as conn:
        conn.execute(text("SET SESSION time_zone = '+00:00'"))
        res = conn.execute(text(safe_sql))
        rows = [dict(r._mapping) for r in res]

    return {"sql": safe_sql, "rows": rows, "row_count": len(rows)}


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
    # Adicionar logs para debug
    print(f"SQL recebido para validação: '{sql}'")
    print(f"Primeiros 10 caracteres (representação): {repr(sql[:10])}")
    
    # Remover marcadores de código Markdown se presentes
    if sql.startswith('```'):
        # Encontra o final do bloco de código
        end_marker = sql.rfind('```')
        if end_marker > 3:  # Certifica-se de que há um marcador de fim
            # Extrai apenas o conteúdo entre os marcadores
            # Pula a primeira linha se contiver apenas ```sql ou similar
            lines = sql[3:end_marker].strip().split('\n')
            if lines[0].strip().lower() in ['sql', 'mysql', 'mariadb']:
                sql = '\n'.join(lines[1:]).strip()
            else:
                sql = '\n'.join(lines).strip()
            print(f"SQL após remoção de marcadores Markdown: '{sql}'")
    
    # Normalizar a string removendo espaços extras e caracteres invisíveis
    normalized_sql = sql.strip()
    
    # Verificar se começa com SELECT
    if not re.match(r"(?i)^\s*select\b", normalized_sql, re.IGNORECASE):
        print(f"ERRO: SQL não começa com SELECT: '{normalized_sql}'")
        raise ValueError("Somente consultas SELECT são permitidas.")
    
    # Impõe LIMIT se não houver
    if not re.search(r"\blimit\s+\d+\s*;?\s*$", normalized_sql, re.IGNORECASE):
        normalized_sql = normalized_sql.rstrip().rstrip(";") + " LIMIT 200;"
        print(f"SQL com LIMIT adicionado: '{normalized_sql}'")
    
    return normalized_sql


# Cadeia NL → SQL
def build_nl2sql_chain() -> str:
    llm = build_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system",
        "Você gera SQL para MariaDB. Regras:\n"
        "- Gere apenas UM único SELECT válido.\n"
        "- Não use DML/DDL (INSERT/UPDATE/DELETE/CREATE/etc.).\n"
        "- Utilize apenas tabelas/colunas existentes no schema abaixo.\n"
        "- Se precisar limitar linhas, use LIMIT.\n"
        "- Para campos de texto (VARCHAR, CHAR, TEXT), use LIKE com wildcards para busca parcial.\n"
        "- Quando buscar por nomes ou outros campos de texto, use LIKE '%termo%' em vez de = 'termo'.\n"
        "- Exemplo: use 'nome LIKE \'%Gabriel%Silveira%\'' em vez de 'nome = \'Gabriel Silveira\'' para encontrar 'Gabriel Silveira de Souza'.\n"),
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


@tool("get_db_catalog", return_direct=False)
def get_db_catalog() -> str:
    """Exporta o catálogo do MariaDB como JSON (string)."""

    print("Obtendo catálogo do banco...")

    catalog = export_db_catalog(
        url=MARIADB_URI,
        sample_rows=0,
        mask_pii=True,
        max_text_len=160,
    )

    return catalog


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
    # Usando .invoke() em vez de chamar diretamente
    table_names = db_list_tables.invoke("")
    schema = DB.get_table_info(table_names)

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
        
        # Converter resultados para dicionário e tratar tipos de dados não serializáveis
        rows = []
        for r in result:
            row_dict = dict(r._mapping)
            # Converter objetos date/datetime para string ISO
            for key, value in row_dict.items():
                if hasattr(value, 'isoformat'):  # Verifica se é date, datetime ou similar
                    row_dict[key] = value.isoformat()
            rows.append(row_dict)

    # Retorna JSON puro (string). Como return_direct=True, o agente repassa isso sem alterações.
    return json.dumps(rows, ensure_ascii=False)
