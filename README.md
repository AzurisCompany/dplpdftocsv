# 📄 Currículo PDF → CSV com IA

Sistema automatizado para extrair informações de currículos em **PDF**, converter em **TXT** e gerar um **CSV estruturado** usando **OpenAI**.

## 🎯 Fluxo do Projeto

```
PDFs (raw_pdfs/)
    ↓
Extração de Texto → TXT
    ↓
Processamento com IA → JSON estruturado
    ↓
Classificação de Importância (1-5)
    ↓
CSV Final (curriculos.csv)
```

---

## ⚡ Quick Start (5 minutos)

### 1️⃣ Clone o Repositório

```bash
git clone <seu_repositorio>
cd dplpdftocsv
```

### 2️⃣ Crie a Estrutura de Diretórios

Execute o comando abaixo para criar automaticamente todas as pastas necessárias:

**Windows (PowerShell):**
```powershell
$dirs = @('data\comp_pdfs', 'data\logs', 'data\output', 'data\quarantine', 'data\raw_pdfs', 'data\txt')
$dirs | ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }
Write-Host "✓ Diretórios criados com sucesso!"
```

**Linux/Mac:**
```bash
mkdir -p data/{comp_pdfs,logs,output,quarantine,raw_pdfs,txt}
echo "✓ Diretórios criados com sucesso!"
```

### 3️⃣ Configure o Arquivo `.env`

Crie um arquivo `.env` na raiz do projeto com sua chave da OpenAI:

**Windows (PowerShell):**
```powershell
@"
OPENAI_API_KEY=seu_token
"@ | Out-File -Encoding UTF8 .env
```

**Linux/Mac:**
```bash
cat > .env << EOF
OPENAI_API_KEY=seu_token
EOF
```

Ou crie manualmente um arquivo `.env`:
```env
OPENAI_API_KEY=seu_token
```

⚠️ **Substitua `seu_token` pela sua chave real**

Obtenha uma chave em: https://platform.openai.com/api-keys

### 4️⃣ Instale as Dependências

```bash
pip install -r requirements.txt
```

Ou manualmente:
```bash
pip install python-dotenv openai pandas pydantic PyPDF2
```

### 5️⃣ Adicione seus PDFs

Copie seus currículos em PDF para a pasta `data/raw_pdfs/`:

```bash
# Windows
copy seu_curriculo.pdf data\raw_pdfs\

# Linux/Mac
cp seu_curriculo.pdf data/raw_pdfs/
```

### 6️⃣ Execute o Processamento

**Opção A: Processar um PDF individual**

```bash
python src/pdf_to_txt.py --input data/raw_pdfs/nome-do-pdf.pdf --output data/txt
```

**Opção B: Processar todos os PDFs em lote**

```bash
python src/batch_processor.py
```

**Opção C: Gerar CSV final com IA**

```bash
python main.py
```

---

## 📊 Fluxo Completo em Detalhes

### Passo 1: Extração de PDF → TXT

```bash
python src/batch_processor.py
```

**O que acontece:**
1. Lê todos os PDFs em `data/raw_pdfs/`
2. Extrai o texto automaticamente
3. Salva em `data/txt/` com mesmo nome
4. Arquivos com sucesso → `data/comp_pdfs/`
5. Arquivos com erro → `data/quarantine/`
6. Logs salvos em `data/logs/`

**Exemplo de saída:**
```
Processando: joao-silva.pdf
✓ joao-silva.pdf → comp_pdfs
  → data/txt/joao-silva.txt criado

Processando: maria-santos.pdf
✗ maria-santos.pdf → quarantine
  (erro na extração de texto)
```

### Passo 2: Processamento com IA → CSV

```bash
python main.py
```

**O que acontece:**
1. Lê todos os TXTs em `data/txt/`
2. Tenta extrair via parse KV (rápido, grátis)
3. Se necessário, usa OpenAI (mais preciso)
4. Classifica importância (1-5)
5. Salva cache para evitar duplicatas
6. Gera `data/output/curriculos.csv`

**Exemplo de saída:**
```
TXT_DIR: data/txt
Encontrados: 5 arquivos .txt

✓ joao-silva.txt | empresa: Tech Corp | nível: 4
✓ maria-santos.txt | empresa: Finance Inc | nível: 5
✓ pedro-oliveira.txt | empresa: None | nível: 2

✅ CSV gerado em: data/output/curriculos.csv
📊 Registros: 3
📦 Cache hits: 0
🔄 OpenAI calls: 2 | KV-only: 1 | Empresa fallback: 0
⭐ Importance OpenAI calls: 1
```

---

## 📁 Estrutura do Projeto

```
dplpdftocsv/
├── data/                          # Dados (NÃO será commitado)
│   ├── raw_pdfs/                  # 📄 Adicione seus PDFs aqui
│   ├── comp_pdfs/                 # ✅ PDFs processados com sucesso
│   ├── quarantine/                # ⚠️  PDFs com erro de extração
│   ├── txt/                       # 📝 Arquivos TXT extraídos
│   ├── output/                    # 📊 CSV gerado
│   │   └── curriculos.csv
│   └── logs/                      # 📋 Logs de processamento
│
├── src/                           # Scripts Python
│   ├── pdf_to_txt.py              # Extrator individual de PDF
│   └── batch_processor.py         # Processador em lote
│
├── .env                           # 🔑 Suas credenciais (NUNCA commitar!)
├── .gitignore                     # 🚫 Arquivos ignorados
├── main.py                        # 🤖 Processador com IA
├── requirements.txt               # 📦 Dependências
├── LICENSE
└── ReadMe.md                      # 📖 Este arquivo
```

---

## 📄 Arquivos CSV Gerado

O arquivo `data/output/curriculos.csv` contém:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `Nome` | string | Nome completo |
| `Email` | string | Email validado |
| `Telefone` | string | Apenas dígitos (≥8) |
| `Linked-in` | string | URL do LinkedIn normalizada |
| `Empresa` | string | Empresa atual |
| `Cargo` | string | Cargo/Posição |
| `HeadLine` | string | Resumo profissional |
| `Nivel_Importancia` | int | 1-5 (escalão hierárquico) |

**Exemplo:**
```csv
Nome,Email,Telefone,Linked-in,Empresa,Cargo,HeadLine,Nivel_Importancia
João Silva,joao@example.com,11987654321,https://www.linkedin.com/in/joaosilva,Tech Corp,Senior Developer,Especialista em Python,3
Maria Santos,maria@example.com,21987654321,https://www.linkedin.com/in/mariasantos,Finance Inc,CFO,Executive de Finanças,5
```

---

## ⭐ Escala de Importância (1-5)

### 1️⃣ **Entrada**
Estágio, Trainee, Assistente, Jovem Aprendiz

### 2️⃣ **Operacional**
Junior, Analista, Técnico, Executor

### 3️⃣ **Especialista**
Senior, Sênior, Pleno, Especialista, Consultor

### 4️⃣ **Liderança**
Gerente, Manager, Coordenador, Head, Lead, Supervisor

### 5️⃣ **Executivo**
CEO, CTO, Diretor, VP, Founder, Owner, Sócio

---

## 🔧 Referência de Comandos

### Processar um PDF específico

```bash
python src/pdf_to_txt.py --input data/raw_pdfs/meu_pdf.pdf --output data/txt
```

**Argumentos:**
- `--input` (obrigatório): Caminho do PDF
- `--output` (obrigatório): Diretório de saída

### Processar todos os PDFs

```bash
python src/batch_processor.py
```

Processa automaticamente:
- Todos os PDFs em `data/raw_pdfs/`
- Move PDFs com sucesso para `data/comp_pdfs/`
- Move PDFs com erro para `data/quarantine/`
- Gera TXTs em `data/txt/`
- Logs em `data/logs/`

### Converter TXT para CSV com IA

```bash
python main.py
```

Processa:
- Todos os TXTs em `data/txt/`
- Extrai dados com IA (se necessário)
- Classifica importância
- Gera CSV em `data/output/curriculos.csv`

---

## 🤖 Como Funciona a Extração

### Estratégia 1: Parse KV (Rápido, Grátis)

Se o TXT tem formato estruturado:
```
Nome: João Silva
Email: joao@example.com
Telefone: 11 98765-4321
LinkedIn: https://www.linkedin.com/in/joaosilva
Cargo: Senior Developer
Empresa: Tech Corp
```

**Resultado:** ✅ Extração sem usar IA

### Estratégia 2: OpenAI (Preciso, Com Custo)

Se o TXT é texto livre:
```
João Silva é um desenvolvedor com 10 anos de experiência...
Trabalhou na Tech Corp como Senior Developer...
Especialista em Python, Cloud e arquitetura de sistemas...
```

**Resultado:** 🤖 OpenAI extrai e estrutura (usa tokens)

---

## 📋 Logs de Processamento

Cada PDF processado gera um log em `data/logs/`:

```
Formato: {nome_pdf}_{timestamp}.log
Exemplo: joao-silva_20260303_143025.log
```

**Conteúdo:**
```
2026-03-03 14:30:25 - INFO - Iniciando processamento: joao-silva.pdf
2026-03-03 14:30:26 - INFO - Texto extraído com sucesso (2847 caracteres)
2026-03-03 14:30:27 - INFO - TXT gerado com sucesso: data/txt/joao-silva.txt
```

Visualizar logs:
```bash
# Windows
type data\logs\joao-silva_*.log

# Linux/Mac
cat data/logs/joao-silva_*.log
```

---

## ⚙️ Configuração Avançada

### Desabilitar OpenAI para Importância

No arquivo `main.py`, altere:

```python
USE_OPENAI_FOR_IMPORTANCE = False  # Usa apenas classificação local
```

### Trocar Modelo OpenAI

```python
OPENAI_MODEL = "gpt-4"        # Mais preciso (mais caro)
OPENAI_MODEL = "gpt-4o-mini"  # Padrão (equilibrado)
```

### Limpar Cache

Se quiser reprocessar tudo:

```bash
# Windows
del data\cache\cache.jsonl

# Linux/Mac
rm data/cache/cache.jsonl
```

---

## 🐛 Troubleshooting

### ❌ Erro: `OPENAI_API_KEY inválida`

**Solução:**
1. Verifique se `.env` existe na raiz
2. Confirme a chave começa com `sk-`
3. Teste em https://platform.openai.com/api-keys

```bash
# Verificar .env
# Windows
type .env

# Linux/Mac
cat .env
```

### ❌ Erro: `Nenhum TXT encontrado`

**Solução:**
```bash
# Crie a pasta
mkdir data\txt

# Adicione arquivos TXT
copy seu_arquivo.txt data\txt\
```

### ❌ Erro: `ModuleNotFoundError`

**Solução:**
```bash
pip install -r requirements.txt
```

### ⚠️ PDF não extrai texto

**Causa:** PDF com imagem (scanned)

**Solução:** Use OCR antes (fora do escopo deste projeto)

### ❌ CSV vazio ou poucas linhas

**Verificar:**
1. Quantidade de PDFs em `data/raw_pdfs/`
2. Se estão em `data/quarantine/` (erro de extração)
3. Logs em `data/logs/` para erros específicos

---

## 🔒 Segurança

### ✅ Boas Práticas

- Sempre use `.env` para chaves
- `.env` está em `.gitignore` (não será commitado)
- Revogue chaves em https://platform.openai.com/api-keys
- Rotacione chaves regularmente

### ❌ Nunca

- Commitar `.env` no Git
- Incluir chave no código
- Compartilhar chave em Slack/Email

---

## 📦 requirements.txt

```
python-dotenv==1.0.0
openai==1.3.5
pandas==2.0.3
pydantic==2.4.2
PyPDF2==4.0.1
```

---

## 📈 Exemplo Completo

### Cenário: 3 currículos em PDF

**1. Crie a estrutura:**
```bash
# Windows PowerShell
$dirs = @('data\comp_pdfs', 'data\logs', 'data\output', 'data\quarantine', 'data\raw_pdfs', 'data\txt')
$dirs | ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }

# Configure .env
@"
OPENAI_API_KEY=sk-proj-xxxxxx
"@ | Out-File -Encoding UTF8 .env

# Instale dependências
pip install -r requirements.txt
```

**2. Adicione PDFs:**
```bash
copy curriculo_joao.pdf data\raw_pdfs\
copy curriculo_maria.pdf data\raw_pdfs\
copy curriculo_pedro.pdf data\raw_pdfs\
```

**3. Processe PDFs:**
```bash
python src\batch_processor.py
```

**4. Gere CSV:**
```bash
python main.py
```

**5. Resultado:**
```
✓ data/output/curriculos.csv gerado com 3 registros!
```

---

## 📊 Estatísticas de Processamento

Ao executar `main.py`, você verá:

```
TXT_DIR: data/txt
Encontrados: 3 arquivos .txt

✓ joao-silva.txt | empresa: Tech Corp | nível: 4
✓ maria-santos.txt | empresa: Finance Inc | nível: 5
✓ pedro-oliveira.txt | empresa: None | nível: 2

✅ CSV gerado em: data/output/curriculos.csv
📊 Registros: 3
📦 Cache hits: 0
🔄 OpenAI calls: 2          (chamadas de extração)
   KV-only: 1               (extraídos sem IA)
   Empresa fallback: 0      (fallback para empresa)
⭐ Importance OpenAI calls: 1 (classificação com IA)
```

---

## 🔍 Verificação Pós-Execução

```bash
# Verificar PDFs processados
ls data/comp_pdfs/      # PDFs com sucesso
ls data/quarantine/     # PDFs com erro

# Verificar TXTs gerados
ls data/txt/

# Verificar CSV final
cat data/output/curriculos.csv

# Verificar logs
ls data/logs/
```

---

## 📞 Suporte

Se encontrar problemas:

1. Verifique o `.env` está correto
2. Confirme chave OpenAI em https://platform.openai.com/api-keys
3. Revise logs em `data/logs/`
4. Verifique se PDFs estão em `data/raw_pdfs/`

---

## 📜 Licença

Este projeto é fornecido como está.

**Última atualização:** Março 2026