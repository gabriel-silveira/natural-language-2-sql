from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from src.tools import get_db_catalog, run_query
from src.config import OPENAI_API_KEY

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.7,
    api_key=OPENAI_API_KEY,
)

nl2sql_agent = create_react_agent(
    model=llm,
    tools=[get_db_catalog, run_query],  
    prompt="""
    Você é um assistente que capaz de interpretar questões do usuário e retornar informações baseado em dados.
    O fluxo é o seguinte:
    1) O usuário faz uma pergunta.
    2) Você gera um SQL para responder a pergunta.
    3) Você executa o SQL no banco de dados e retorna os resultados.
    
    Sempre obtenha o catálogo do banco de dados para obter as informações necessárias.
    No catálogo você poderá ver as tabelas e colunas disponíveis.
    """,
)
