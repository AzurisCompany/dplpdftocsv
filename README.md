# Estrutura Congresso - Sistema de Processamento de PDFs

## 📋 Descrição

Sistema automatizado para extrair informações de portfolios em PDF de candidatos a um congresso. O sistema valida, processa e organiza os arquivos conforme o status de sucesso ou erro.

## Importante

Adicione a chave API da OPENAI (Meu caso) no código main.py

## 🗂️ Estrutura de Diretórios

```
Estrutura-Congresso/
├── data/
│   ├── raw_pdfs/          # PDFs originais para processar
│   ├── comp_pdfs/         # PDFs processados com sucesso
│   ├── quarantine/        # PDFs com erro no processamento
│   ├── txt/               # Arquivos TXT extraídos
│   └── logs/              # Logs de processamento
├── docs/                  # Documentação adicional (Nesse código é necessário adicionar um CSV com as informações que não foi  possivel obter do txt. Isso caso utilize a main para obter um CSV)
├── src/                   # Scripts Python
│   ├── pdf_to_txt.py      # Processador individual de PDF
│   └── batch_processor.py # Processador em lote
├── .gitignore
├── LICENSE
├── main.py
└── ReadMe.md
```

## 🚀 Instalação

### Pré-requisitos
- Python 3.7+
- pip

### Dependências

Instale as dependências necessárias:

```bash
pip install PyPDF2 openai pandas pydantic
```

## 💻 Uso

### Processar um PDF individual

```bash
python src\pdf_to_txt.py --input data\raw_pdfs\nome-do-pdf.pdf --output data\txt --encoding utf-8
```

**Argumentos:**
- `--input` (obrigatório): Caminho do arquivo PDF
- `--output` (obrigatório): Diretório de saída para o TXT
- `--encoding` (opcional): Codificação do arquivo (padrão: utf-8)

**Retorno:**
- Status 0: Processamento bem-sucedido
- Status 1: Erro no processamento

### Processar múltiplos PDFs (Batch)

```bash
python src\batch_processor.py
```

Este comando:
1. Processa todos os PDFs em `data/raw_pdfs/`
2. Move PDFs com sucesso para `data/comp_pdfs/`
3. Move PDFs com erro para `data/quarantine/`
4. Gera arquivos TXT em `data/txt/`
5. Registra logs em `data/logs/`

### Gerar CSV final (main.py)

```bash
python main.py
```

Este comando:
1. Compara o TXT com o CSV completo, verificando as informações que não vieram corretamente

## 📊 Fluxo de Processamento

```
PDF (raw_pdfs)
    ↓
Extração de Texto
    ↓
Validação de Conteúdo
    ├─ ✓ Sucesso → comp_pdfs + gera TXT
    └─ ✗ Erro → quarantine (sem TXT)
    
Todas as operações → logs/
```

## 📝 Validação de Conteúdo

O sistema verifica a presença de palavras-chave esperadas:
- linkedin, email, telefone
- experiência, habilidades
- name, phone

Se nenhuma palavra-chave for encontrada, o PDF é movido para quarantine.

## 📜 Logs

Cada processamento gera um arquivo de log em `data/logs/`:

```
formato: {nome_pdf}_{timestamp}.log
exemplo: rodrigo-bittencourt_20260128_143025.log
```

**Conteúdo do log:**
- Timestamp de início e fim
- Status de extração
- Erros e avisos
- Arquivo de saída gerado

## 🔧 Estrutura do Código

### pdf_to_txt.py
- `setup_logger()`: Configura logging para cada PDF
- `extract_text_from_pdf()`: Extrai texto do PDF
- `validate_content()`: Valida presença de informações
- `process_pdf()`: Orquestra o processamento
- `main()`: Ponto de entrada com argumentos CLI

### batch_processor.py
- `batch_process_pdfs()`: Processa todos os PDFs em lote

## ⚠️ Tratamento de Erros

Erros comuns e soluções:

| Erro | Causa | Solução |
|------|-------|--------|
| PDF vazio | Arquivo corrompido ou sem texto | Verificar PDF manualmente |
| Sem palavras-chave | PDF não contém dados relevantes | Revisar conteúdo do PDF |
| Erro de codificação | Encoding incorreto | Usar `--encoding latin-1` ou outro |
| Permissão negada | Arquivo aberto em outro programa | Fechar e tentar novamente |

## 📋 Exemplo Prático

```bash
# 1. Colocar PDFs em data/raw_pdfs/
# Exemplo: rodrigo-bittencourt.pdf, maria-silva.pdf

# 2. Executar processamento em lote
python src\batch_processor.py

# 3. Resultado:
# ✓ rodrigo-bittencourt.pdf → data/comp_pdfs/
# ✓ data/txt/rodrigo-bittencourt.txt (gerado)
# ✗ maria-silva.pdf → data/quarantine/
```

## 🔐 Codificação

O padrão é UTF-8, mas você pode usar outras:
- UTF-8 (recomendado)
- latin-1
- cp1252 (Windows)

```bash
python src\pdf_to_txt.py --input data\raw_pdfs\arquivo.pdf --output data\txt --encoding latin-1
```

## 📞 Informações Capturadas

O sistema extrai as seguintes informações dos PDFs:
- Nome completo
- Email
- Telefone
- Perfil LinkedIn
- Experiências profissionais
- Habilidades técnicas
- Educação

## 📄 Licença

Este projeto é parte do sistema de inscrição do Congresso.