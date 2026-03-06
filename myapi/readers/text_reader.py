import os
from langchain.schema import Document
from langchain_community.document_loaders import TextLoader as TextFileLoader

class TextLoader:
    def __init__(self, folder_path, extensions=None):
        self.folder_path = folder_path
        self.extensions = extensions or [".txt"]

    def load(self):
        documents = []
        for filename in os.listdir(self.folder_path):
            ext = os.path.splitext(filename)[1].lower()
            if ext in self.extensions:
                filepath = os.path.join(self.folder_path, filename)
                try:
                    loader = TextFileLoader(filepath, autodetect_encoding=True)
                    document = loader.load()
                    documents.extend(document)
                    print(f"Loaded text file: {filename}")
                except Exception as e:
                    print(f"Failed to load text file {filename}: {e}")
        return documents
    
