from src.agents.nl2sql_agent import nl2sql_agent
from src.prompts.job_oportunity_match import oportunity_match


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