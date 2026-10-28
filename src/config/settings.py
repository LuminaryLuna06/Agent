import os
from dotenv import load_dotenv

load_dotenv()

LLAMA_URL = os.getenv("LLAMA_URL")
CONTEXT_WINDOW = 8000
DATABASE_FILE = "./test.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"
