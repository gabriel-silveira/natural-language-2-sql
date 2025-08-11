from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from src.tools import db_list_tables, db_schema, db_nl2sql_rows
from src.config import OPENAI_API_KEY

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.7,
    api_key=OPENAI_API_KEY,
)

sql_agent = create_react_agent(
    model=llm,
    tools=[db_list_tables, db_schema, db_nl2sql_rows],  
    prompt="Você é um assistente capaz de interpretar questões do usuário e retornar resultados provenientes do banco de dados. Se necessário, gera um SQL para MariaDB.",
)
