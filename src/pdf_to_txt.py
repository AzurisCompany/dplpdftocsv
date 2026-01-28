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
    
    # Divide o texto em linhas uma única vez
    lines = text.split('\n')
    
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
    
    # Extrai LinkedIn - Busca no texto original com quebras de linha
    linkedin_with_break = re.search(r'linkedin\.com/in/([a-zA-Z0-9-]+)\s*\n\s*([a-zA-Z0-9-]+)', text, re.IGNORECASE)
    if linkedin_with_break:
        username = linkedin_with_break.group(1) + linkedin_with_break.group(2)
        info['linkedin'] = f"linkedin.com/in/{username}"
    else:
        text_normalized = text.replace('\n', ' ')
        linkedin_url_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9-]+)'
        linkedin_match = re.search(linkedin_url_pattern, text_normalized, re.IGNORECASE)
        
        if linkedin_match:
            username = linkedin_match.group(1).strip()
            info['linkedin'] = f"linkedin.com/in/{username}"
    
    # Extrai NOME - Usa o username do LinkedIn como referência
    if info['linkedin']:
        username = info['linkedin'].replace('linkedin.com/in/', '').lower()
        username_parts = username.split('-')
        
        if len(username_parts) >= 2:
            first_name = username_parts[0].capitalize()
            last_name = username_parts[1].capitalize()
            
            # Procura por esse padrão no texto
            name_pattern = rf'{first_name}\s+{last_name}'
            name_match = re.search(name_pattern, text, re.IGNORECASE)
            
            if name_match:
                info['nome'] = name_match.group(0)
            else:
                # Fallback: procura por qualquer combinação
                name_pattern = rf'{first_name}.*?{last_name}'
                name_match = re.search(name_pattern, text, re.IGNORECASE | re.DOTALL)
                if name_match:
                    found_name = name_match.group(0).replace('\n', ' ').strip()
                    if len(found_name) < 80:
                        info['nome'] = found_name
    
    # Se não conseguiu pelo LinkedIn, tenta buscar manualmente
    if not info['nome']:
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Procura por primeira linha com 2-4 palavras capitalizadas após "Languages"
            if i > 0 and 'Languages' in lines[i-1]:
                words = line_clean.split()
                if 2 <= len(words) <= 4 and line_clean and '(' not in line_clean:
                    is_name = all(w[0].isupper() and w.replace('-', '').isalpha() for w in words if w)
                    if is_name:
                        info['nome'] = line_clean
                        break
    
    # Extrai HEADLINE - Procura por linhas com pipes (|) que indicam múltiplos cargos
    # O headline pode ocupar múltiplas linhas
    for i, line in enumerate(lines):
        if '|' in line or any(title in line for title in ['Coordenador', 'Engenheiro', 'Gerente', 'Analista', 'Professor', 'Consultor', 'Diretor', 'Especialista', 'Mestre']):
            if not info['headline']:
                # Junta linhas consecutivas que fazem parte do headline
                headline_lines = [line.strip()]
                
                # Verifica próximas linhas se continuam o headline
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    
                    # Para se encontrar palavras-chave que indicam fim do headline
                    if next_line and not ('|' in next_line or any(title in next_line for title in ['Coordenador', 'Engenheiro', 'Gerente', 'Analista', 'Professor', 'Consultor', 'Diretor', 'Especialista', 'Mestre', 'Automotiva', 'Elétricos', 'Híbridos'])):
                        break
                    
                    # Se linha está vazia ou tem "Curitiba" (localização), para
                    if not next_line or 'Curitiba' in next_line or 'Brasil' in next_line or 'São Paulo' in next_line:
                        break
                    
                    headline_lines.append(next_line)
                    j += 1
                
                # Junta as linhas do headline
                info['headline'] = ' '.join(headline_lines)
                
                # Remove múltiplos espaços
                info['headline'] = re.sub(r'\s+', ' ', info['headline']).strip()
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
    """Extrai o resumo profissional com quebra de linha a cada 12 palavras"""
    # Tenta encontrar a seção "Resumo"
    resumo_section = re.search(r'Resumo\s*(.*?)(?:\nExperiência|\nFormação|\nEducação|\nSkills|\nCompetências|$)', text, re.DOTALL | re.IGNORECASE)
    
    if resumo_section:
        resumo_text = resumo_section.group(1).strip()
        
        # Divide por parágrafos (duas ou mais quebras de linha)
        paragraphs = re.split(r'\n\s*\n+', resumo_text)
        
        if paragraphs:
            # Processa cada parágrafo
            processed_paragraphs = []
            for para in paragraphs:
                para = para.strip()
                if para:  # Se parágrafo não está vazio
                    # Remove quebras de linha internas e normaliza espaços
                    para = re.sub(r'\n+', ' ', para)
                    para = re.sub(r'\s+', ' ', para).strip()
                    
                    # Adiciona quebra de linha a cada 12 palavras
                    words = para.split()
                    lines = []
                    for i in range(0, len(words), 12):
                        lines.append(' '.join(words[i:i+12]))
                    
                    processed_paragraphs.append('\n'.join(lines))
            
            # Junta parágrafos com quebra de linha dupla
            return '\n\n'.join(processed_paragraphs)
    
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
Cargo: {info['headline'] or 'Não identificado'}
Localização: {info['localizacao'] or 'Não identificado'}

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