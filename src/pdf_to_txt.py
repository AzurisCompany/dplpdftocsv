import argparse
import os
import shutil
import logging
import re
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

def extract_text_from_pdf(pdf_path, encoding='utf-8'):
    """Extrai texto do PDF"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num, page in enumerate(reader.pages):
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text if text.strip() else None
    except Exception as e:
        raise Exception(f"Erro ao extrair texto: {str(e)}")

def extract_main_info(text):
    """Extrai informações principais do texto"""
    info = {
        'nome': None,
        'email': None,
        'telefone': None,
        'linkedin': None,
        'headline': None,
        'localizacao': None,
    }
    
    # Extrai email
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    if emails:
        info['email'] = emails[0]
    
    # Extrai telefone
    phone_pattern = r'\+?55\s?\d{2}\s?\d{4,5}\s?\d{4}|\+?\d{10,}'
    phones = re.findall(phone_pattern, text)
    if phones:
        info['telefone'] = phones[0]
    
    # Extrai LinkedIn (versão melhorada para pegar o link completo)
    linkedin_pattern = r'(?:linkedin\.com/in/|www\.linkedin\.com/in/)([a-zA-Z0-9-]+)'
    linkedin = re.search(linkedin_pattern, text, re.IGNORECASE)
    if linkedin:
        info['linkedin'] = f"linkedin.com/in/{linkedin.group(1)}"
    else:
        # Tenta encontrar URLs de LinkedIn no texto
        url_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9-]+'
        url_match = re.search(url_pattern, text, re.IGNORECASE)
        if url_match:
            url = url_match.group(0)
            # Remove https:// e www. se existirem
            url = re.sub(r'^(?:https?://)?(?:www\.)?', '', url)
            info['linkedin'] = url
    
    # Extrai nome e headline
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_clean = line.strip()
        
        # Procura por padrão de nome + headline (ex: "Alessandro Kulitch\nCoordenador de Engenharia...")
        if any(title in line for title in ['Coordenador', 'Engenheiro', 'Gerente', 'Analista', 'Professor', 'Consultor', 'Diretor', 'Especialista']):
            # Pega o próximo padrão de cargo/headline
            if not info['headline']:
                info['headline'] = line_clean
            
            # Nome está poucas linhas antes
            if not info['nome']:
                for j in range(max(0, i-3), i):
                    candidate = lines[j].strip()
                    if candidate and len(candidate.split()) >= 2 and len(candidate) < 80:
                        if not any(char.isdigit() for char in candidate) and not any(kw in candidate for kw in ['Contato', 'Email', 'Phone', 'Mobile', 'LinkedIn']):
                            info['nome'] = candidate
                            break
    
    # Extrai localização
    city_pattern = r'(?:Curitiba|São Paulo|Rio de Janeiro|Belo Horizonte|Brasília|Salvador|Fortaleza|Manaus|Recife|Porto Alegre|Goiânia|Belém|Guarulhos|Campinas|São Bernardo do Campo|Santo André|Osasco|Mauá|São Caetano do Sul|Diadema|Sorocaba|Jundiaí|Piracicaba|Ribeirão Preto|Araraquara|Bauru|Presidente Prudente|Marília|Barueri|Maringá|Londrina|Cascavel|Foz do Iguaçu|Ponta Grossa|Paranaguá|Blumenau|Brusque|Joinville|Florianópolis|Lages|Chapecó|Criciúma|Itajaí|Pelotas|Rio Grande|Santa Maria|Novo Hamburgo|Gramado|Canoas|Caxias do Sul|Viamão|Alvorada|Sapucaia do Sul|Campo Bom|Cachoeirinha|Esteio|Gravataí|São Leopoldo)\s*,\s*(?:Paraná|São Paulo|Rio de Janeiro|Minas Gerais|Bahia|Ceará|Amazonas|Pernambuco|Rio Grande do Sul|Goiás|Pará|Maranhão|Santa Catarina|Paraíba|Espírito Santo|Piauí|Rio Grande do Norte|Alagoas|Mato Grosso|Mato Grosso do Sul|Distrito Federal|Acre|Amapá|Rondônia|Roraima|Tocantins)'
    loc_match = re.search(city_pattern, text, re.IGNORECASE)
    if loc_match:
        info['localizacao'] = loc_match.group(0)
    
    return info

def validate_content(text):
    """Valida se o PDF contém informações relevantes"""
    keywords = ['linkedin', 'email', 'telefone', 'experiência', 'habilidades', 'name', 'phone', 'profissional', 'skills', 'enginee', 'coordena', 'cargo']
    found_keywords = [kw for kw in keywords if kw.lower() in text.lower()]
    return len(found_keywords) > 0, found_keywords

def extract_relevant_experience(text):
    """Extrai apenas as experiências profissionais (até 2 primeiras)"""
    # Tenta encontrar a seção de experiência
    exp_section = re.search(r'Experiência(.*?)(?:Formação|Educação|Skills|Competências|$)', text, re.DOTALL | re.IGNORECASE)
    
    if exp_section:
        exp_text = exp_section.group(1)
        # Limita para evitar muita informação
        lines = exp_text.split('\n')
        # Retorna até 30 linhas (aproximadamente 2 experiências)
        relevant = '\n'.join(lines[:30])
        return relevant.strip()
    return ""

def format_output(pdf_name, info, full_text):
    """Formata as informações extraídas para saída limpa e estruturada"""
    
    # Extrai seção de experiências
    experience_section = extract_relevant_experience(full_text)
    
    output = f"""╔═══════════════════════════════════════════════════════════╗
║ RESUMO - INFORMAÇÕES DO CANDIDATO
║ {pdf_name}
╚═══════════════════════════════════════════════════════════╝

📋 DADOS PESSOAIS
─────────────────────────────────────────────────────────────
Nome: {info['nome'] or 'Não identificado'}
Email: {info['email'] or 'Não identificado'}
Telefone: {info['telefone'] or 'Não identificado'}
LinkedIn: {info['linkedin'] or 'Não identificado'}
Localização: {info['localizacao'] or 'Não identificado'}

💼 HEADLINE PROFISSIONAL
─────────────────────────────────────────────────────────────
{info['headline'] or 'Não identificado'}

═══════════════════════════════════════════════════════════

📄 EXPERIÊNCIA PROFISSIONAL
─────────────────────────────────────────────────────────────

{experience_section if experience_section else 'Não encontrado'}

═══════════════════════════════════════════════════════════

📋 CONTEÚDO COMPLETO DO CURRÍCULO
─────────────────────────────────────────────────────────────

{full_text}

═══════════════════════════════════════════════════════════
Processado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
"""
    
    return output

def process_pdf(input_path, output_dir, encoding='utf-8'):
    """Processa um PDF: extrai texto, valida e organiza arquivos"""
    pdf_path = Path(input_path)
    
    # Valida se arquivo existe
    if not pdf_path.exists():
        print(f"❌ Erro: Arquivo não encontrado: {input_path}")
        return 1
    
    logger = setup_logger(pdf_path)
    
    logger.info(f"{'='*60}")
    logger.info(f"Iniciando processamento: {pdf_path.name}")
    logger.info(f"Caminho: {pdf_path.absolute()}")
    logger.info(f"Encoding: {encoding}")
    
    try:
        # Extrai texto
        print(f"\n📖 Lendo PDF: {pdf_path.name}")
        text = extract_text_from_pdf(pdf_path, encoding)
        
        if not text:
            print(f"⚠️  PDF vazio ou sem texto extraído")
            logger.warning("PDF vazio ou sem texto extraído")
            return 1
        
        print(f"✓ Texto extraído ({len(text)} caracteres)")
        logger.info(f"Texto extraído com sucesso ({len(text)} caracteres)")
        
        # Valida conteúdo
        print(f"🔍 Validando conteúdo...")
        is_valid, keywords_found = validate_content(text)
        
        if not is_valid:
            print(f"⚠️  PDF não contém informações relevantes")
            logger.warning(f"PDF não contém informações relevantes. Nenhuma palavra-chave encontrada.")
            return 1
        
        print(f"✓ Palavras-chave encontradas: {', '.join(keywords_found)}")
        logger.info(f"Validação bem-sucedida. Palavras-chave: {keywords_found}")
        
        # Extrai informações principais
        print(f"📊 Extraindo informações principais...")
        info = extract_main_info(text)
        logger.info(f"Informações extraídas: Nome={info['nome']}, Email={info['email']}, LinkedIn={info['linkedin']}")
        
        # Formata saída
        formatted_output = format_output(pdf_path.stem, info, text)
        
        # Salva arquivo TXT
        print(f"💾 Salvando arquivo TXT...")
        output_path = Path(output_dir) / f"{pdf_path.stem}.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding=encoding) as f:
            f.write(formatted_output)
        
        print(f"✓ TXT gerado: {output_path.name}")
        logger.info(f"TXT gerado com sucesso: {output_path.name}")
        logger.info(f"Caminho de saída: {output_path.absolute()}")
        logger.info(f"{'='*60}\n")
        
        return 0
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        logger.error(f"Erro no processamento: {str(e)}")
        logger.info(f"{'='*60}\n")
        return 1

def main():
    parser = argparse.ArgumentParser(
        description='Extrai informações de PDF e gera arquivo TXT estruturado',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python pdf_to_txt.py --input data/raw_pdfs/arquivo.pdf --output data/txt
  python pdf_to_txt.py --input data/raw_pdfs/arquivo.pdf --output data/txt --encoding utf-8
        """
    )
    parser.add_argument('--input', required=True, help='Caminho do PDF de entrada')
    parser.add_argument('--output', required=True, help='Diretório de saída para TXT')
    parser.add_argument('--encoding', default='utf-8', help='Codificação do arquivo (padrão: utf-8)')
    
    args = parser.parse_args()
    
    status = process_pdf(args.input, args.output, args.encoding)
    exit(status)

if __name__ == "__main__":
    main()