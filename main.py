from src import ShorekeeperAgent, get_db, init_db


def main():
    # Initialize the tables in the database
    init_db()

    # Open Local database session
    db = next(get_db())

    # Create an instance of ShorekeeperAgent
    agent = ShorekeeperAgent(db)

    running = True
    for msg in agent.messages:
        if msg["role"] == "system":
            continue
        if msg["role"] == "assistant":
            print(f"Shorekeeper: {msg['content']}")
        else:
            print(f"Luna: {msg['content']}")
    while running:
        chat = str(input("Luna: ")).strip()
        if not chat:
            continue

        if chat.strip().lower() == "exit":
            running = False
            break
        response = agent.step(user_msg=chat)
        print("Shorekeeper: ", response)


main()
