# NL2SQL Tool

Uma ferramenta de processamento de linguagem natural para SQL que permite consultar bancos de dados MariaDB usando perguntas em linguagem natural.

## Visão Geral

Este projeto implementa um agente de IA capaz de interpretar perguntas em linguagem natural, convertê-las em consultas SQL e retornar os resultados do banco de dados. O agente utiliza o modelo GPT-4o da OpenAI para entender as perguntas e gerar SQL adequado com base no esquema do banco de dados.

## Funcionalidades

- Conversão de perguntas em linguagem natural para consultas SQL
- Acesso seguro ao banco de dados através de schema seguro e views
- Validação de consultas SQL para garantir que apenas operações SELECT sejam permitidas
- Exportação do catálogo do banco de dados para referência do modelo de linguagem
- Suporte a consultas complexas com base no contexto do banco de dados

## Estrutura do Projeto

```
/nl2sql-tool
├── .env                    # Variáveis de ambiente (MARIADB_URI, OPENAI_API_KEY, etc.)
├── db_schema.json          # Esquema do banco de dados em formato JSON
├── main.py                 # Ponto de entrada da aplicação
├── pyproject.toml          # Configuração do projeto e dependências
└── src/                    # Código-fonte
    ├── agents/             # Definição dos agentes de IA
    │   └── nl2sql_agent.py # Agente principal para conversão NL para SQL
    ├── config.py           # Configurações e carregamento de variáveis de ambiente
    ├── db.py               # Conexão com o banco de dados
    ├── prompts/            # Prompts predefinidos para o agente
    │   └── job_oportunity_match.py # Exemplo de prompt para matching de vagas
    ├── services/           # Serviços auxiliares
    │   ├── create_safe_schema.py   # Criação de schema seguro
    │   └── export_db_catalog.py    # Exportação do catálogo do banco
    └── tools.py            # Ferramentas utilizadas pelo agente
```

## Requisitos

- Python 3.9+
- MariaDB/MySQL
- Chave de API da OpenAI

## Instalação

1. Clone o repositório:

```bash
git clone <repositório>
cd nl2sql-tool
```

2. Crie e ative um ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
```

3. Instale as dependências:

```bash
pip install -e .
```

4. Configure o arquivo `.env` com suas credenciais:

```
MARIADB_URI=mysql+pymysql://usuario:senha@localhost:3306/banco
OPENAI_API_KEY=sua-chave-api-openai
SCHEMA_SAFE_PASSWORD=senha-schema-seguro
```

## Uso

O arquivo `main.py` demonstra como utilizar o agente NL2SQL:

```python
from src.agents.nl2sql_agent import nl2sql_agent
from src.prompts.job_oportunity_match import oportunity_match

if __name__ == "__main__":
    response = nl2sql_agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": "Com base na vaga descrita abaixo, encontre 5 candidatos que mais se adequam à vaga e exiba um resumo de cada um com o percentual de compatibilidade com a vaga.
Dê prioridade para candidatos que tenham experiência em pelo menos um dos requisitos a seguir:
•Frameworks de agentes: experiência com LangChain, LangGraph, AutoGPT, ou implementações próprias de agentes.
•Modelos de linguagem (LLMs): conhecimento em OpenAI, Hugging Face Transformers, Mistral, entre outros.",
            }
        ],
    })

    for message in response['messages']:
        message.pretty_print()
```

## Segurança

O projeto implementa várias camadas de segurança:

1. Validação de consultas SQL para permitir apenas operações SELECT
2. Imposição de LIMIT em todas as consultas
3. Acesso ao banco de dados através de schema seguro e views que omitem campos sensíveis
4. Permissões de usuário restritas (apenas SELECT)

## Componentes Principais

### NL2SQL Agent

O agente principal que converte linguagem natural para SQL, definido em `src/agents/nl2sql_agent.py`. Utiliza o modelo GPT-4o da OpenAI e ferramentas personalizadas.

### Ferramentas

Definidas em `src/tools.py`, incluem:

- `get_db_catalog`: Obtém o catálogo do banco de dados
- `run_query`: Executa consultas SQL validadas
- `db_nl2sql_rows`: Converte perguntas em linguagem natural para SQL e retorna os resultados

### Serviços

- `export_db_catalog.py`: Exporta o catálogo do banco de dados como JSON
- `create_safe_schema.py`: Cria um schema seguro com views que omitem campos sensíveis

## Exemplo de Uso

O projeto inclui um exemplo de uso para matching de vagas de emprego com candidatos, demonstrando como o agente pode ser utilizado para análise de dados complexa.

## Licença

MIT
