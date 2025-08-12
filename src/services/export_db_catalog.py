#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exporta o catálogo de um banco MariaDB para uso em LLMs (NL→SQL).
- Coleta: tabelas, colunas (tipo/nullable/default/comentários), PK, FKs, índices, comentários.
- Saídas: JSON (sempre) e Markdown (opcional).
- Amostragem de linhas (opcional) para dar contexto de valores típicos.

Uso:
  python db_schema.py \
    --url "mariadb+mariadbconnector://user:pass@host:3306/meu_schema" \
    --schema meu_schema \
    --out-json catalog.json \
    --out-md catalog.md \
    --include-views \
    --sample-rows 3 \
    --mask-pii \
    --max-text-len 160

Observações de segurança:
- O script só realiza leitura de metadados e (se habilitado) SELECT com LIMIT.
- Ideal rodar com usuário de leitura (read-only).
"""

from __future__ import annotations
import argparse
import json
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import uuid

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from src.tools import ALLOWED_TABLES


# ------------------------------- Utilidades ----------------------------------


def guess_schema_from_url(engine: Engine) -> Optional[str]:
    """Tenta obter o schema padrão via SELECT DATABASE()."""
    try:
        with engine.connect() as conn:
            return conn.execute(text("SELECT DATABASE()")).scalar()
    except Exception:
        return None


def normalize_type(t: Any) -> str:
    """
    Converte o tipo do SQLAlchemy para string estável e normalizada (minúsculas).
    Observação: se o driver devolver ENUM sem os valores, manteremos "enum" simples.
    """
    try:
        s = str(t)
    except Exception:
        s = repr(t)
    return s.strip().lower()


def json_fallback(o):
    """Converte objetos não-serializáveis do Python para representações JSON-safe."""
    if isinstance(o, (datetime, date, time)):
        return o.isoformat()
    if isinstance(o, timedelta):
        return o.total_seconds()
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, (bytes, bytearray, memoryview)):
        return o.decode("utf-8", "replace")
    if isinstance(o, (set, tuple)):
        return list(o)
    if isinstance(o, uuid.UUID):
        return str(o)
    return str(o)


# Regex simples para PII comum no BR
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
PHONE_RE = re.compile(r"\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9?\d{4}[-\s]?\d{4})\b")


def mask_pii_value(v: Any, max_len: Optional[int]) -> Any:
    """Masca e normaliza valores de texto para evitar PII em sample_rows."""
    if v is None:
        return None
    if isinstance(v, (int, float, bool, Decimal)):
        return v
    s = json_fallback(v)  # já resolve datetime/bytes/etc
    s = EMAIL_RE.sub("[email]", s)
    s = CPF_RE.sub("[cpf]", s)
    s = PHONE_RE.sub("[phone]", s)
    # achatar quebras de linha e espaços excessivos
    s = re.sub(r"\s+", " ", s).strip()
    if max_len and len(s) > max_len:
        s = s[:max_len] + "…"
    return s


def load_fk_rules(engine: Engine, schema: str) -> Dict[str, Dict[str, Optional[str]]]:
    """
    (2) Carrega UPDATE_RULE e DELETE_RULE por CONSTRAINT_NAME para o schema,
    a partir de INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS.
    """
    q = text("""
        SELECT CONSTRAINT_NAME, UPDATE_RULE, DELETE_RULE
        FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = :schema
    """)
    with engine.connect() as conn:
        rows = conn.execute(q, {"schema": schema}).mappings().all()
    return {
        r["CONSTRAINT_NAME"]: {
            "on_update": r.get("UPDATE_RULE"),
            "on_delete": r.get("DELETE_RULE"),
        }
        for r in rows
    }


# --------------------------- Construção do catálogo ---------------------------


def build_table_dict(
    engine: Engine,
    schema: str,
    table: str,
    inspector,
    sample_rows: int = 0,
    *,
    fk_rules: Optional[Dict[str, Dict[str, Optional[str]]]] = None,
    mask_pii: bool = False,
    max_text_len: Optional[int] = None,
) -> Dict[str, Any]:
    # Comentário da tabela
    tcomment = inspector.get_table_comment(table_name=table, schema=schema) or {}
    tbl: Dict[str, Any] = {
        "name": table,
        "comment": tcomment.get("text") or "",
        "columns": [],
        "primary_key": [],
        "foreign_keys": [],
        "indexes": [],
    }

    # Colunas
    for col in inspector.get_columns(table, schema=schema):
        # (5) autoincrement -> booleano sempre
        ai = col.get("autoincrement")
        ai_bool = bool(ai)
        tbl["columns"].append({
            "name": col.get("name"),
            "type": normalize_type(col.get("type")),  # (3) minúsculas
            "nullable": bool(col.get("nullable")),
            "default": col.get("default"),
            "autoincrement": ai_bool,                 # (5)
            "comment": (col.get("comment") or ""),
        })

    # PK
    pk = inspector.get_pk_constraint(table, schema=schema) or {}
    tbl["primary_key"] = pk.get("constrained_columns") or []

    # FKs
    for fk in inspector.get_foreign_keys(table, schema=schema):
        fk_entry = {
            "name": fk.get("name"),
            "columns": fk.get("constrained_columns") or [],
            "ref_schema": fk.get("referred_schema"),
            "ref_table": fk.get("referred_table"),
            "ref_columns": fk.get("referred_columns") or [],
            "on_update": (fk.get("options") or {}).get("onupdate"),
            "on_delete": (fk.get("options") or {}).get("ondelete"),
        }
        # (2) complementar via REFERENTIAL_CONSTRAINTS pelo nome da constraint
        if fk_rules and fk_entry["name"] in fk_rules:
            if not fk_entry["on_update"]:
                fk_entry["on_update"] = fk_rules[fk_entry["name"]]["on_update"]
            if not fk_entry["on_delete"]:
                fk_entry["on_delete"] = fk_rules[fk_entry["name"]]["on_delete"]
        tbl["foreign_keys"].append(fk_entry)

    # Índices (inclui UNIQUE e não-únicos)
    for idx in inspector.get_indexes(table, schema=schema):
        tbl["indexes"].append({
            "name": idx.get("name"),
            "unique": bool(idx.get("unique")),
            "columns": idx.get("column_names") or [],
            "type": idx.get("type"),  # pode ser None
        })

    # Amostra de linhas (opcional)
    if sample_rows and sample_rows > 0:
        try:
            with engine.connect() as conn:
                col_names = [c["name"] for c in inspector.get_columns(table, schema=schema)]
                if not col_names:
                    tbl["sample_rows"] = []
                else:
                    cols_sql = ", ".join(f"`{c}`" for c in col_names)
                    sql = text(f"SELECT {cols_sql} FROM `{schema}`.`{table}` LIMIT :lim")
                    rows = conn.execute(sql, {"lim": int(sample_rows)}).mappings().all()

                    def _norm_row(d):
                        base = dict(d)
                        if mask_pii:
                            return {k: mask_pii_value(v, max_text_len) for k, v in base.items()}
                        else:
                            return {k: json_fallback(v) for k, v in base.items()}

                    tbl["sample_rows"] = [_norm_row(r) for r in rows]
        except SQLAlchemyError:
            tbl["sample_rows"] = []

    return tbl


def to_markdown(catalog: Dict[str, Any]) -> str:
    """Gera um resumo Markdown compacto para prompt/visualização humana."""
    lines: List[str] = []
    lines.append(f"# Catálogo — schema `{catalog.get('schema','')}`")
    lines.append("")
    for t in catalog.get("tables", []):
        lines.append(f"## {t['name']}")
        if t.get("comment"):
            lines.append(f"> {t['comment']}")
        # Resumo de colunas
        cols = []
        for c in t["columns"]:
            col_bits = [f"`{c['name']}` {c['type']}"]
            if not c["nullable"]:
                col_bits.append("NOT NULL")
            if c.get("default") is not None:
                col_bits.append(f"DEFAULT {c['default']}")
            if c.get("comment"):
                col_bits.append(f"// {c['comment']}")
            cols.append(" - " + " | ".join(col_bits))
        if cols:
            lines.append("**Colunas:**")
            lines.extend(cols)
        # PK
        if t.get("primary_key"):
            lines.append(f"**PK:** {', '.join('`'+c+'`' for c in t['primary_key'])}")
        # FKs
        if t.get("foreign_keys"):
            lines.append("**FKs:**")
            for fk in t["foreign_keys"]:
                src = ", ".join(f"`{c}`" for c in fk["columns"])
                dst_cols = ", ".join(f"`{c}`" for c in (fk["ref_columns"] or []))
                ref = f"`{fk.get('ref_table')}`({dst_cols})"
                ou = f" ON UPDATE {fk['on_update']}" if fk.get("on_update") else ""
                od = f" ON DELETE {fk['on_delete']}" if fk.get("on_delete") else ""
                lines.append(f" - {src} → {ref}{ou}{od}")
        # Índices
        if t.get("indexes"):
            lines.append("**Índices:**")
            for idx in t["indexes"]:
                cols_join = ", ".join(f"`{c}`" for c in (idx.get("columns") or []))
                uniq = " UNIQUE" if idx.get("unique") else ""
                lines.append(f" - `{idx.get('name')}`{uniq} ({cols_join})")
        # Amostra (se houver)
        if t.get("sample_rows"):
            lines.append("**Amostra:**")
            for r in t["sample_rows"]:
                lines.append(" - " + ", ".join(f"`{k}`={repr(v)}" for k, v in r.items()))
        lines.append("")
    return "\n".join(lines)


def export_db_catalog(
    url: str,
    *,
    schema: Optional[str] = None,
    include_views: bool = False,
    sample_rows: int = 0,
    mask_pii: bool = False,
    max_text_len: int = 160,
) -> str:
    """
    Exporta o catálogo do MariaDB como JSON (string).

    Parâmetros:
      - url: URL SQLAlchemy (ex.: mariadb+mariadbconnector://user:pass@host:3306/db)
      - schema: nome do schema/banco; se None, tenta descobrir via SELECT DATABASE()
      - include_views: se True, inclui views
      - sample_rows: N linhas de amostra por tabela (0 desliga)
      - mask_pii: se True, mascara e-mail/CPF/telefone e achata textos nas amostras
      - max_text_len: limite de tamanho de textos em amostras (válido com mask_pii)

    Retorna:
      - JSON (str) com o catálogo.
    """
    engine = create_engine(url, pool_pre_ping=True)

    eff_schema = schema or guess_schema_from_url(engine)
    if not eff_schema:
        raise ValueError("Não foi possível determinar o schema. Informe 'schema=' ou ajuste a URL.")

    insp = inspect(engine)

    # Tabelas e (opcional) views
    tables = list(insp.get_table_names(schema=eff_schema))
    if include_views:
        tables.extend(insp.get_view_names(schema=eff_schema))

    # Regras ON UPDATE/DELETE por constraint
    fk_rules = load_fk_rules(engine, eff_schema)

    catalog: Dict[str, Any] = {"schema": eff_schema, "tables": []}

    for t in tables:
        try:
            if ALLOWED_TABLES and t in ALLOWED_TABLES:
                print(f"Exportando tabela permitida: {t}")

                catalog["tables"].append(
                    build_table_dict(
                        engine,
                        eff_schema,
                        t,
                        insp,
                        sample_rows=sample_rows,
                        fk_rules=fk_rules,
                        mask_pii=mask_pii,
                        max_text_len=max_text_len,
                    )
                )
        except SQLAlchemyError as e:
            print(f"Falha ao inspecionar a tabela: {e}")

            catalog["tables"].append({
                "name": t,
                "error": f"Falha ao inspecionar a tabela: {e}",
            })

    return json.dumps(catalog, ensure_ascii=False, indent=2, default=json_fallback)


# ----------------------------------- CLI -------------------------------------


def main():
    ap = argparse.ArgumentParser(description="Exporta catálogo MariaDB para LLM (NL→SQL).")
    ap.add_argument("--url", required=True, help="URL SQLAlchemy. Ex.: mariadb+mariadbconnector://user:pass@host:3306/db")
    ap.add_argument("--schema", help="Schema/banco (default: o da URL).")
    ap.add_argument("--out-json", help="Arquivo de saída JSON (default: imprime no stdout).")
    ap.add_argument("--out-md", help="Arquivo de saída Markdown (opcional).")
    ap.add_argument("--include-views", action="store_true", help="Incluir views no catálogo.")
    ap.add_argument("--sample-rows", type=int, default=0, help="Amostra N linhas por tabela (0=desliga).")
    # (4) flags de PII/limite de texto em amostras
    ap.add_argument("--mask-pii", action="store_true", help="Mascarar PII (e-mail, CPF, telefone) e achatar textos nas sample_rows.")
    ap.add_argument("--max-text-len", type=int, default=160, help="Tamanho máximo de texto em sample_rows (aplica com --mask-pii).")
    args = ap.parse_args()

    engine = create_engine(args.url, pool_pre_ping=True)

    schema = args.schema or guess_schema_from_url(engine)
    if not schema:
        raise SystemExit("Não foi possível determinar o schema. Use --schema.")

    insp = inspect(engine)

    # Tabelas físicas
    tables = insp.get_table_names(schema=schema)
    all_tables: List[str] = list(tables)

    # Views (opcional)
    if args.include_views:
        views = insp.get_view_names(schema=schema)
        all_tables.extend(views)

    # (2) carregar regras ON UPDATE/DELETE por constraint
    fk_rules = load_fk_rules(engine, schema)

    catalog: Dict[str, Any] = {"schema": schema, "tables": []}

    for t in all_tables:
        try:
            catalog["tables"].append(
                build_table_dict(
                    engine,
                    schema,
                    t,
                    insp,
                    sample_rows=args.sample_rows,
                    fk_rules=fk_rules,
                    mask_pii=args.mask_pii,
                    max_text_len=args.max_text_len,
                )
            )
        except SQLAlchemyError as e:
            catalog["tables"].append({
                "name": t,
                "error": f"Falha ao inspecionar a tabela: {e}",
            })

    # Saída JSON
    json_text = json.dumps(catalog, ensure_ascii=False, indent=2, default=json_fallback)
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            f.write(json_text)
    else:
        print(json_text)

    # Saída Markdown (opcional)
    if args.out_md:
        md_text = to_markdown(catalog)
        with open(args.out_md, "w", encoding="utf-8") as f:
            f.write(md_text)

    # Dica de prompt para NL→SQL (exibida apenas quando não salva em arquivo)
    guidance = f"""
=== SUGESTÃO DE CONTEXTO PARA LLM ===
Você é um assistente que traduz perguntas em SQL (MariaDB).
- Use apenas tabelas/colunas do catálogo abaixo.
- Prefira JOINs seguindo as chaves estrangeiras.
- Inclua LIMIT 50 por padrão.
- Proibido executar instruções que alterem dados (INSERT/UPDATE/DELETE/DDL).
Catálogo (JSON):
<cole aqui o JSON gerado para o schema {schema}>
"""
    if not args.out_json:
        print(guidance)
