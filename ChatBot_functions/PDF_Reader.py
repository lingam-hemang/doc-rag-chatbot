import os
import numpy as np
import fitz  # PyMuPDF
from PIL import Image
import easyocr
from langchain.schema import Document

class PDFLoader:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.reader = easyocr.Reader(['en'], gpu=False)

    def correct_rotation(self, image: Image.Image) -> Image.Image:
        image_np = np.array(image)
        try:
            orientation_info = self.reader.detect(image_np, width_ths=0.5, decoder='greedy')[0]
            angle = orientation_info[0]
            if angle != 0:
                return image.rotate(-angle, expand=True)
        except Exception as e:
            print(f"Rotation detection failed: {e}")
        return image

    def load(self):
        documents = []
        for filename in os.listdir(self.folder_path):
            if not filename.lower().endswith(".pdf"):
                continue
            filepath = os.path.join(self.folder_path, filename)
            try:
                doc = fitz.open(filepath)
                full_text = ""
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    text = page.get_text()
                    if text.strip():
                        full_text += text + "\n"
                    else:
                        pix = page.get_pixmap()
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        img_corrected = self.correct_rotation(img)
                        image_np = np.array(img_corrected)
                        results = self.reader.readtext(image_np, detail=0)
                        ocr_text = "\n".join(results)
                        full_text += ocr_text + "\n"
                if full_text.strip():
                    documents.append(Document(page_content=full_text, metadata={"source": filepath.replace('stagging/','')}))
                    print(f"Loaded PDF (with easyocr rotation correction): {filename}")
                else:
                    print(f"No text found in PDF even after OCR: {filename}")
            except Exception as e:
                print(f"Failed to load PDF {filename}: {e}")
        return documents
    
    