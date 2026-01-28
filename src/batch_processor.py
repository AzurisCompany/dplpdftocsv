import os
import shutil
from pathlib import Path
import subprocess
import sys

def batch_process_pdfs():
    """Processa todos os PDFs da pasta raw_pdfs"""
    base_dir = Path(__file__).parent.parent / "data"
    raw_pdfs = base_dir / "raw_pdfs"
    comp_pdfs = base_dir / "comp_pdfs"
    quarantine = base_dir / "quarantine"
    txt_dir = base_dir / "txt"
    
    # Cria diretórios se não existirem
    for dir_path in [comp_pdfs, quarantine, txt_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Processa cada PDF
    for pdf_file in raw_pdfs.glob("*.pdf"):
        print(f"Processando: {pdf_file.name}")
        
        status = subprocess.run(
            [sys.executable, "pdf_to_txt.py", 
             "--input", str(pdf_file), 
             "--output", str(txt_dir)],
            cwd=Path(__file__).parent
        ).returncode
        
        if status == 0:
            # Sucesso: move para comp_pdfs
            shutil.move(str(pdf_file), str(comp_pdfs / pdf_file.name))
            print(f"✓ {pdf_file.name} -> comp_pdfs")
        else:
            # Erro: move para quarantine
            shutil.move(str(pdf_file), str(quarantine / pdf_file.name))
            print(f"✗ {pdf_file.name} -> quarantine")

if __name__ == "__main__":
    batch_process_pdfs()