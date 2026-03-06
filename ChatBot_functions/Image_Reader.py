import os
import numpy as np
from PIL import Image
import easyocr
from langchain.schema import Document

class ImageLoader:
    def __init__(self, folder_path, extensions=None):
        self.folder_path = folder_path
        self.extensions = extensions or [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]
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
            ext = os.path.splitext(filename)[1].lower()
            if ext in self.extensions:
                filepath = os.path.join(self.folder_path, filename)
                try:
                    img = Image.open(filepath)
                    img_corrected = self.correct_rotation(img)
                    image_np = np.array(img_corrected)
                    results = self.reader.readtext(image_np, detail=0)
                    text = "\n".join(results)
                    if text.strip():
                        documents.append(Document(page_content=text, metadata={"source": filepath.replace('stagging/','')}))
                        print(f"OCR extracted text from {filename} with rotation correction")
                    else:
                        print(f"No text found in {filename}")
                except Exception as e:
                    print(f"Failed to OCR {filename}: {e}")
        return documents
