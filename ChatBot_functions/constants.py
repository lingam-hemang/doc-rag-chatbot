import os
BASE_DATA_DIR = f"{os.getcwd()}/files"
STAGING_FOLDER = f"{BASE_DATA_DIR}/staging"
CHAT_HISTORY_DIR = f"{os.getcwd()}/ChatBot_Files/Chat_History"
BASE_VECTORDB_DIR = f"{os.getcwd()}/ChatBot_Files/VectorDB"
CURRENT_HISTORY_FILE = os.path.join(CHAT_HISTORY_DIR, "current.json")
CURRENT_VECTORDB_PATH = os.path.join(BASE_VECTORDB_DIR, "current")
MODEL = 'mistral'