from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from src.tools import get_db_catalog
from src.config import OPENAI_API_KEY

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.7,
    api_key=OPENAI_API_KEY,
)

nl2sql_agent = create_react_agent(
    model=llm,
    tools=[get_db_catalog],  
    prompt="""
    Você é um assistente capaz de interpretar questões do usuário, criar consultas SQL e retornar resultados provenientes do banco de dados.
    Sempre obtenha o catálogo do banco de dados para obter as informações necessárias.
    No catálogo você poderá ver as tabelas e colunas disponíveis.
    """,
)
