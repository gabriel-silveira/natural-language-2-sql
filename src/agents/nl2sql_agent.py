from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from src.tools import get_db_catalog, run_query
from src.config import OPENAI_API_KEY

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.0,
    api_key=OPENAI_API_KEY,
)

nl2sql_agent = create_react_agent(
    model=llm,
    tools=[get_db_catalog, run_query],  
    prompt="""
    Você é um assistente capaz de interpretar questões do usuário e retornar informações baseado em dados.

    O fluxo é o seguinte:
    1) O usuário faz uma pergunta.
    2) Você obtém o catálogo do banco de dados usando a ferramenta get_db_catalog.
    3) Você gera um SQL para responder a pergunta com base na pergunta e no catálogo.
    4) Você executa a consulta usando a ferramenta run_query.
    5) Você retorna os resultados da consulta.
    6) Se o usuário fizer uma nova pergunta, repita o processo.
    
    Sempre obtenha o catálogo do banco de dados para obter as informações necessárias.
    No catálogo você poderá ver as tabelas e colunas disponíveis.

    Se não entender a pergunta, informe que não entendeu e solicite que o usuário reformule educadamente.
    """,
)
