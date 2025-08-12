from src.agents.nl2sql_agent import nl2sql_agent


if __name__ == "__main__":
    response = nl2sql_agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": "Me dê todos os dados do candidato de nome Gabriel Silveira de Souza",
            },
        ],
    })

    for message in response['messages']:
        message.pretty_print()