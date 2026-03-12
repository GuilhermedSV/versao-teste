import sys
try:
    from pypdf import PdfReader
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf"])
    from pypdf import PdfReader

print("Extracting text from PDF...")
reader = PdfReader('sistema de gerenciamento.pdf')
text = ""
for page in reader.pages:
    extracted = page.extract_text()
    if extracted:
        text += extracted + "\n"

with open('pdf_text.txt', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done! Text saved to pdf_text.txt")
