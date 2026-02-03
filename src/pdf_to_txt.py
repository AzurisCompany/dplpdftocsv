import argparse
import logging
from pathlib import Path
from datetime import datetime
import PyPDF2

def setup_logger(pdf_name):
    """Configura logger para registrar operações"""
    log_dir = Path(__file__).parent.parent / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"{pdf_name.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True
    )
    return logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path):
    """Extrai texto do PDF"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text if text.strip() else None
    except Exception as e:
        raise Exception(f"Erro ao extrair texto: {str(e)}")

def process_pdf(input_path, output_dir):
    """Processa PDF e salva texto extraído"""
    pdf_path = Path(input_path)
    
    if not pdf_path.exists():
        print(f"❌ Erro: Arquivo não encontrado: {input_path}")
        return 1
    
    logger = setup_logger(pdf_path)
    logger.info(f"Iniciando processamento: {pdf_path.name}")
    
    try:
        print(f"\n📖 Lendo PDF: {pdf_path.name}")
        text = extract_text_from_pdf(pdf_path)
        
        if not text:
            print(f"⚠️  PDF vazio ou sem texto extraído")
            logger.warning("PDF vazio ou sem texto extraído")
            return 1
        
        print(f"✓ Texto extraído ({len(text)} caracteres)")
        logger.info(f"Texto extraído com sucesso ({len(text)} caracteres)")
        
        # Salva arquivo TXT
        print(f"💾 Salvando arquivo TXT...")
        output_path = Path(output_dir) / f"{pdf_path.stem}.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        print(f"✓ TXT gerado: {output_path.name}")
        logger.info(f"TXT gerado com sucesso: {output_path.absolute()}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        logger.error(f"Erro no processamento: {str(e)}")
        return 1

def main():
    parser = argparse.ArgumentParser(
        description='Extrai texto de PDF e gera arquivo TXT'
    )
    parser.add_argument('--input', required=True, help='Caminho do PDF de entrada')
    parser.add_argument('--output', required=True, help='Diretório de saída para TXT')
    
    args = parser.parse_args()
    status = process_pdf(args.input, args.output)
    exit(status)

if __name__ == "__main__":
    main()