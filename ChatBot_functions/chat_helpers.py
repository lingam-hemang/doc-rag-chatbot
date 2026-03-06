import os
import json
import time
import shutil
from datetime import datetime
from . import constants

from langchain.docstore.document import Document
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import OllamaLLM
from langchain.schema import HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.chat_message_histories import ChatMessageHistory

# from langchain_community.llms import Ollama
# from langchain_community.embeddings.ollama import OllamaEmbeddings
# from langchain_community.vectorstores import Chroma

from .PDF_Reader import PDFLoader
from .Word_Reader import WordLoader
from .Text_Reader import TextLoader
from .Image_Reader import ImageLoader

BASE_DATA_DIR = constants.BASE_DATA_DIR
STAGING_FOLDER = constants.STAGING_FOLDER
CHAT_HISTORY_DIR = constants.CHAT_HISTORY_DIR
BASE_VECTORDB_DIR = constants.BASE_VECTORDB_DIR
CURRENT_HISTORY_FILE = constants.CURRENT_HISTORY_FILE
CURRENT_VECTORDB_PATH = constants.CURRENT_VECTORDB_PATH
MODEL = constants.MODEL

def load_chat_history():
    history = ChatMessageHistory()
    with open(CURRENT_HISTORY_FILE, "r") as f:
        data = json.load(f)
        for entry in data:
            if entry["type"] == "human":
                history.add_user_message(entry["message"])
            elif entry["type"] == "bot":
                history.add_ai_message(entry["message"])
    return history

def save_chat_history(history):
    data = []
    for msg in history.messages:
        if isinstance(msg, HumanMessage): data.append({"type": "human", "message": msg.content})
        elif isinstance(msg, AIMessage): data.append({"type": "ai", "message": msg.content})
        else: data.append({"type": "system", "message": msg.content})
    
    with open(CURRENT_HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_vector_store():
    if not os.path.exists(CURRENT_VECTORDB_PATH):
        print(f"Vector DB not found at {CURRENT_VECTORDB_PATH}")
        return None

    embedding = OllamaEmbeddings(model=MODEL)
    vectorstore = Chroma(persist_directory=CURRENT_VECTORDB_PATH, embedding_function=embedding)
    return vectorstore

def create_snapshot():
    timestamp = datetime.now().strftime("%d.%m.%Y_%H%M%S")
    
    if os.path.exists(CURRENT_VECTORDB_PATH):
        snapshot_db = os.path.join(BASE_VECTORDB_DIR, f'vectordb_{timestamp}')
        shutil.copytree(CURRENT_VECTORDB_PATH, snapshot_db)
        print(f"[Snapshot] Vector store moved to: 'VectorDB/vectordb_{timestamp}'")
    
    if os.path.exists(CURRENT_HISTORY_FILE) and os.stat(CURRENT_HISTORY_FILE).st_size!=2:
        snapshot_hist = os.path.join(CHAT_HISTORY_DIR, f'chat_history_{timestamp}.json')
        shutil.move(CURRENT_HISTORY_FILE, snapshot_hist)
        print(f"[Snapshot] Chat history saved to: 'Chat_History/chat_history_{timestamp}.json'")
    
        with open(CURRENT_HISTORY_FILE, "w") as f:
            f.write("[]")
            print("[Init] Initialized new empty chat history at 'Chat_History/current.json'")

def add_documents_vectordb(documents, process_all_files):
    process_incr_files = (not process_all_files)
    create_snapshot()
    
    if os.path.exists(CURRENT_VECTORDB_PATH) and process_incr_files:
        vectorstore = load_vector_store()
        vectorstore.add_documents(documents)
        print('[Added] New documents to the current VectorDB')
    elif os.path.exists(CURRENT_VECTORDB_PATH) and process_all_files:
        shutil.rmtree(CURRENT_VECTORDB_PATH)
        print("[Init] Initialized new VectorDB with complete existing files at 'VectorDB/current'")
        embedding = OllamaEmbeddings(model=MODEL)
        vectorstore = Chroma.from_documents(documents, embedding, persist_directory=CURRENT_VECTORDB_PATH)
    else:
        print("[Init] Initialized new VectorDB at 'VectorDB/current'")
        embedding = OllamaEmbeddings(model=MODEL)
        vectorstore = Chroma.from_documents(documents, embedding, persist_directory=CURRENT_VECTORDB_PATH)
        with open(CURRENT_HISTORY_FILE, "w") as f:
            f.write("[]")
            print("[Init] Initialized new empty chat history at 'Chat_History/current.json'")
        

def recreate_vectordb():
    create_snapshot()
    shutil.rmtree(CURRENT_VECTORDB_PATH)
    embedding = OllamaEmbeddings(model=MODEL)
    documents,process_all_files = load_documents(process_all_files=True)
    vectorstore = Chroma.from_documents(documents, embedding, persist_directory=CURRENT_VECTORDB_PATH)
    

def load_documents(process_all_files=False):
    docs = []
    if process_all_files:
        pdf_loader = PDFLoader(os.path.join(BASE_DATA_DIR,'pdfs'))
        docs.extend(pdf_loader.load())
        text_loader = TextLoader(os.path.join(BASE_DATA_DIR,'txts'))
        docs.extend(text_loader.load())
        word_loader = WordLoader(os.path.join(BASE_DATA_DIR,'docs'))
        docs.extend(word_loader.load())
        image_loader = ImageLoader(os.path.join(BASE_DATA_DIR,'images'))
        docs.extend(image_loader.load())
        
        print(f"Loaded {len(docs)} documents total.")
    
    else:
        pdf_loader = PDFLoader(os.path.join(STAGING_FOLDER,'pdfs'))
        docs.extend(pdf_loader.load())
        text_loader = TextLoader(os.path.join(STAGING_FOLDER,'txts'))
        docs.extend(text_loader.load())
        word_loader = WordLoader(os.path.join(STAGING_FOLDER,'docs'))
        docs.extend(word_loader.load())
        image_loader = ImageLoader(os.path.join(STAGING_FOLDER,'images'))
        docs.extend(image_loader.load())
        
        print(f"{len(docs)} documents to be added in the vector store.")
        
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500, 
        chunk_overlap=150
    )
    docs = text_splitter.split_documents(docs)
    return docs, process_all_files

def move_folder_contents(src_folder: str, dest_folder: str):
    os.makedirs(dest_folder, exist_ok=True)  # Ensure destination exists
    move_files = False

    for root,_,file_lst in os.walk(src_folder):
        for file_name in file_lst:
            src_path = os.path.join(root, file_name)
            dest_path = src_path.replace(src_folder,dest_folder)
            shutil.move(src_path, dest_path)
            move_files = True
    
    if move_files:
        print(f"Moved all contents from '{src_folder.split('/')[-1]}' to '{dest_folder.split('/')[-1]}'")
    else:
        print("No files to be moved")

def clear_staging():
    cout = 0
    for root,_,file_lst in os.walk(STAGING_FOLDER):
        for file_name in file_lst:
            file_path = os.path.join(root, file_name)
            os.remove(file_path)
            cout+=1
    print(f'Cleared staging area {cout} files removed')

def build_chain():
    vectordb = load_vector_store()
    history = load_chat_history()
    
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        chat_memory=history
    )
    
    llm = OllamaLLM(model=MODEL)
    retriever = vectordb.as_retriever()
    chain = ConversationalRetrievalChain.from_llm(llm=llm, retriever=retriever, memory=memory)

    return chain, history

def get_reply(question):
    chain, history = build_chain()

    question = question.strip()
    response = chain.invoke({"question": question})
    save_chat_history(history)

    return response.get('answer', str(response)).strip()