from src.agents import sql_agent


if __name__ == "__main__":
    response = sql_agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": "Me dê a ficha completa do candidato de nome Gabriel Silveira",
            },
        ],
    })

    for message in response['messages']:
        message.pretty_print()
        # print(f"{message['role']}: {message['content']}\n\n")