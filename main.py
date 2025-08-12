from src.agents.nl2sql_agent import nl2sql_agent


oportunity_match = """
Com base na vaga descrita abaixo, encontre 5 candidatos que mais se adequam à vaga e exiba um resumo de cada um com o percentual de compatibilidade com a vaga.
Dê prioridade para candidatos que tenham experiência em pelo menos um dos requisitos.
Ao fim, eleja o melhor candidato e justifique sua escolha.

DESCRIÇÃO DA VAGA
#15332 - Analista de Inteligência Artificial
Local: Quinhaú / Embu - SP

Tipo: Presencial

PERFIL DA EMPRESA:
Empresa nascida no Japão, que chegou ao Brasil em 1973, trazendo consigo uma sólida expertise e o compromisso inabalável com a qualidade em transformação de plásticos, com um foco na produção de dutos, tubos e mangueiras flexíveis. Pioneiros na fabricação de tubos corrugados em PEAD no país, revolucionamos o mercado ao desenvolver soluções flexíveis e resistentes para diversos segmentos. Seus produtos estão presentes no dia a dia de todos, de grandes obras até a casa de consumidores espalhados pelo Brasil e pelo mundo, sempre com a excelência e inovação.


Requisitos:
•Linguagem Python (avançado): Padrões de projeto, orientação a objetos, boas práticas de organização de código.
•Frameworks de agentes: experiência com LangChain, LangGraph, AutoGPT, ou implementações próprias de agentes.
•Modelos de linguagem (LLMs): conhecimento em OpenAI, Hugging Face Transformers, Mistral, entre outros.
•Orquestração e Tools: criação de agentes que usam múltiplas ferramentas (ex: banco de dados, API externa, RAG).
•Memória e persistência de contexto: uso de Redis, ChromaDB, ou outras soluções de memória vetorial.
•Integração com APIs REST e bancos de dados.
•Conhecimentos em cloud computing (Azure) para deploy e escalabilidade.
•Foco em criação de agentes.

Diferenciais:
•Experiência com RAG (Retrieval-Augmented Generation).
•Noções de aprendizado por reforço aplicado a agentes autônomos.
•Conhecimento em ciência de dados ou NLP tradicional.
•Contribuições open-source ou projetos em GitHub relacionados a agentes inteligentes.

INFORMAÇÕES COMPLEMENTARES:
Principais Atividades e Desafios:
•Projetar, desenvolver e manter agentes inteligentes (baseados em LLMs, regras, planejamento ou multiagentes).
•Traduzir problemas de negócio em arquiteturas de IA, considerando interação com usuários, tomada de decisão e automação de tarefas.
•Desenvolver fluxos de prompt engineering, orquestração de ferramentas (tools) e memória de contexto para agentes conversacionais.
•Integrar os agentes a APIs externas, bases de dados e ferramentas de automação.
•Testar, avaliar e monitorar o comportamento e desempenho dos agentes com foco em eficiência, custo e robustez.
•Trabalhar em conjunto com times de dados, produto e engenharia para garantir alinhamento técnico e funcional.
"""


if __name__ == "__main__":
    response = nl2sql_agent.invoke({
        "messages": [
            # {
            #     "role": "user",
            #     "content": "Me d  todos os dados do candidato de nome Gabriel Silveira de Souza",
            # },
            # {
            #     "role": "user",
            #     "content": "Me dê um pequeno resumo de todos os candidatos de nome igual ou similar a Gabriel Silveira. Depois faça um comparativo entre eles.",
            # },
            {
                "role": "user",
                "content": oportunity_match,
            }
        ],
    })

    for message in response['messages']:
        message.pretty_print()