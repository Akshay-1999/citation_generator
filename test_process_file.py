import pytesseract
from PIL import Image
import fitz  # PyMuPDF library
from pathlib import Path
import os
import asyncio
import shutil

# 1. Point pytesseract to your installation path!
# pytesseract.pytesseract.tesseract_cmd = r'C:\Users\akpatil\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
tesseract_path = os.environ.get("TESSERACT_CMD")
    
# Second, check if it's already in the system PATH (works out of the box on Ubuntu)
if not tesseract_path:
    tesseract_path = shutil.which("tesseract")
    
# Third, check common Windows installation paths
if not tesseract_path and os.name == 'nt':
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe") # Your local path
    ]
    for path in common_paths:
        if os.path.exists(path):
            tesseract_path = path
            break
            
if not tesseract_path:
    print("TESSERACT_CMD not found")
  
        
pytesseract.pytesseract.tesseract_cmd = tesseract_path
# Open the source PDF document
pdf_path = r"D:\Akshay\Work and Document\Training\LLM AND AI\citation\citation_generator\uploaded_files\Naukri_SrinathS[7y_0m].pdf"
doc = fitz.open(pdf_path)

# Ensure the output folder exists
folder_path_str = r"D:\Akshay\Work and Document\Training\LLM AND AI\citation\citation_generator\Image_converted_resume"
os.makedirs(folder_path_str, exist_ok=True)

# Loop through every page in the PDF and save it as an image
for page_num in range(len(doc)):
    page = doc.load_page(page_num)
    pix = page.get_pixmap(dpi=150) 
    output_image_path = fr"{folder_path_str}\{1+page_num}_page.png"
    pix.save(output_image_path)

doc.close()

# Define your async execution properly
async def extract_text_async():
    folder_path = Path(folder_path_str)
    loop = asyncio.get_running_loop()
    #get all the image files
    image_files = [item for item in folder_path.iterdir() if item.suffix == ".png"]
    #sort the image file 
    image_files.sort(key=lambda x: int(x.name.split('_')[0]))
    
    # We will store tasks here
    tasks = []
    
    for item in image_files:
        print(item)
        # Use run_in_executor so the blocking pytesseract function runs in a background thread!
        task = loop.run_in_executor(None, pytesseract.image_to_string, str(item))
        tasks.append(task)
            
    # Run all OCR tasks concurrently in the background threads and wait for them all to finish
    results = await asyncio.gather(*tasks)
    
    # Join the resulting list of strings into one complete string
    complete_text = "\n\n".join(results)
    return complete_text

# Run the async loop properly
if __name__ == "__main__":
    extracted_text = asyncio.run(extract_text_async())
    print("--- EXTRACTED TEXT ---")
    print(extracted_text[0:500])
