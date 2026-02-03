import os
import re
import json
import glob
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
from pydantic import BaseModel
from openai import OpenAI


# ======================================================
# COLE SUA CHAVE DA OPENAI AQUI
# ======================================================
OPENAI_API_KEY = "SUA_CHAVE_AQUI"
OPENAI_MODEL = "gpt-4o-mini"
# ======================================================


# =========================
# CONFIG
# =========================
DATABASE_CSV = os.path.join("docs", "database.csv")
BASE_CANDIDATES = ["data", "Data"]

# Pastas de saída/cache dentro da base detectada (data ou Data)
MATCH_REPORT_CSV_NAME = "match_report.csv"
OUTPUT_CSV_NAME = "participantes.csv"
CACHE_JSONL_NAME = "cache.jsonl"


# =========================
# SCHEMA
# =========================
class Participant(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    linkedin: Optional[str] = None
    empresa_atual: Optional[str] = None
    cargo: Optional[str] = None
    headline: Optional[str] = None


# =========================
# PATHS / IO
# =========================
def pick_base_dir() -> str:
    for b in BASE_CANDIDATES:
        if os.path.isdir(b):
            return b
    return "data"


BASE_DIR = pick_base_dir()
TXT_DIR = os.path.join(BASE_DIR, "txt")
TXT_GLOB = os.path.join(TXT_DIR, "*.txt")

OUT_DIR = os.path.join(BASE_DIR, "output")
OUT_CSV = os.path.join(OUT_DIR, OUTPUT_CSV_NAME)

CACHE_DIR = os.path.join(BASE_DIR, "cache")
CACHE_JSONL = os.path.join(CACHE_DIR, CACHE_JSONL_NAME)

MATCH_REPORT_CSV = os.path.join(OUT_DIR, MATCH_REPORT_CSV_NAME)


def ensure_dirs() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)


def list_txt_files() -> List[str]:
    files = sorted(glob.glob(TXT_GLOB))
    print("TXT_DIR:", TXT_DIR)
    print("Procurando:", TXT_GLOB)
    print("Encontrados:", len(files), "arquivos .txt")

    if not files:
        print("Nenhum TXT encontrado. Confirme se os arquivos estao em:", TXT_DIR)
        if os.path.isdir(TXT_DIR):
            print("Conteudo da pasta (primeiros 30):", os.listdir(TXT_DIR)[:30])
        raise SystemExit(1)

    return files


# =========================
# CACHE
# =========================
def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def load_cache() -> Dict[str, Dict]:
    cache: Dict[str, Dict] = {}
    if not os.path.exists(CACHE_JSONL):
        return cache

    with open(CACHE_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                sha = obj.get("sha")
                data = obj.get("data")
                if sha and isinstance(data, dict):
                    cache[sha] = data
            except Exception:
                continue
    return cache


def save_cache(sha: str, data: Dict) -> None:
    with open(CACHE_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "sha": sha,
            "data": data,
            "ts": datetime.utcnow().isoformat()
        }, ensure_ascii=False) + "\n")


# =========================
# TXT PARSING
# =========================
def normalize_key(k: str) -> str:
    k = k.lower().strip()
    k = k.replace("linked-in", "linkedin").replace("linked in", "linkedin")
    k = k.replace("empresa atual", "empresa_atual")
    k = k.replace("e-mail", "email")
    k = k.replace("head line", "headline").replace("head-line", "headline")
    k = re.sub(r"[^a-z0-9_]+", "", k)
    return k


def parse_kv(text: str) -> Dict[str, str]:
    kv = {}
    for line in text.splitlines():
        m = re.match(r"^\s*([^:]{2,120})\s*:\s*(.+)$", line)
        if m:
            kv[normalize_key(m.group(1))] = m.group(2).strip()
    return kv


def kv_to_participant(kv: Dict[str, str]) -> Participant:
    return Participant(
        nome=kv.get("nome") or kv.get("name"),
        telefone=kv.get("telefone") or kv.get("celular") or kv.get("phone"),
        email=kv.get("email") or kv.get("mail") or kv.get("email_pessoal"),
        linkedin=kv.get("linkedin"),
        empresa_atual=kv.get("empresa_atual") or kv.get("empresaatual") or kv.get("empresa") or kv.get("company"),
        cargo=kv.get("cargo") or kv.get("role") or kv.get("position") or kv.get("posicao"),
        headline=kv.get("headline") or kv.get("resumo"),
    )


def is_complete_for_openai(p: Participant) -> bool:
    # se pelo menos linkedin, nome, empresa_atual, cargo, headline estiverem presentes,
    # a gente ainda usa DB para email/telefone.
    return all([p.nome, p.linkedin, p.empresa_atual, p.cargo, p.headline])


# =========================
# NORMALIZERS (LinkedIn / Email / Phone)
# =========================
def norm_linkedin(s: Optional[str]) -> Optional[str]:
    if not s:
        return None

    s = str(s).strip().rstrip(".,;")

    # extrai url dentro de texto, se existir
    m = re.search(r"(https?://(www\.)?linkedin\.com/[^\s)>\]]+)", s, re.I)
    if m:
        s = m.group(1).rstrip(".,;")

    # adiciona esquema se faltar
    if s.startswith("linkedin.com/"):
        s = "https://www." + s
    elif s.startswith("www.linkedin.com/"):
        s = "https://" + s

    # padroniza host
    s = re.sub(r"^https?://(www\.)?linkedin\.com", "https://www.linkedin.com", s, flags=re.I)

    # remove query e fragment
    s = s.split("?", 1)[0].split("#", 1)[0]

    # remove trailing slash
    if s.endswith("/"):
        s = s[:-1]

    return s


def norm_email(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = str(s).strip().lower()
    return s if "@" in s else None


def norm_phone(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    digits = re.sub(r"\D+", "", str(s))
    if len(digits) < 8:
        return None
    return digits


# =========================
# DATABASE CSV INDEX (LinkedIn-only)
# =========================
def pick_col_contains(df: pd.DataFrame, options: List[str]) -> Optional[str]:
    # match exato primeiro
    for opt in options:
        if opt in df.columns:
            return opt
    # match por substring
    for c in df.columns:
        for opt in options:
            if opt in c:
                return c
    return None


def load_database_index_by_linkedin(path: str) -> Dict[str, Dict[str, Optional[str]]]:
    if not os.path.exists(path):
        print("database.csv nao encontrado em:", path, "(enriquecimento desativado)")
        return {}

    df = pd.read_csv(path, dtype=str).fillna("")

    # normaliza colunas
    cols = {c: normalize_key(c) for c in df.columns}
    df = df.rename(columns=cols)

    print("Colunas normalizadas em database.csv:", list(df.columns))

    col_li = pick_col_contains(df, ["linkedin", "perfil_linkedin", "url_linkedin", "link_linkedin"])
    col_email = pick_col_contains(df, ["email_pessoal", "email", "mail"])
    col_tel = pick_col_contains(df, ["celular_com_ddd", "telefone", "celular", "phone"])
    col_nome = pick_col_contains(df, ["nome", "name"])

    if not col_li:
        print("database.csv sem coluna de linkedin detectavel. Enriquecimento por linkedin nao sera aplicado.")
        return {}

    idx: Dict[str, Dict[str, Optional[str]]] = {}

    for _, row in df.iterrows():
        li = norm_linkedin(row[col_li])
        if not li:
            continue

        rec = {
            "nome": (str(row[col_nome]).strip() if col_nome else "") or None,
            "email": norm_email(row[col_email]) if col_email else None,
            "telefone": norm_phone(row[col_tel]) if col_tel else None,
            "linkedin": li,
        }

        prev = idx.get(li)
        if not prev:
            idx[li] = rec
        else:
            if not prev.get("email") and rec.get("email"):
                prev["email"] = rec["email"]
            if not prev.get("telefone") and rec.get("telefone"):
                prev["telefone"] = rec["telefone"]
            if not prev.get("nome") and rec.get("nome"):
                prev["nome"] = rec["nome"]
            idx[li] = prev

    print("database.csv carregado:", len(df), "linhas | idx_linkedin:", len(idx))
    return idx


def enrich_only_by_linkedin(p: Participant, idx_linkedin: Dict[str, Dict[str, Optional[str]]]) -> Tuple[Participant, str]:
    li = norm_linkedin(p.linkedin) if p.linkedin else None
    if not li:
        return p, "no_linkedin"

    rec = idx_linkedin.get(li)
    if not rec:
        # ainda normaliza linkedin no output
        data = p.model_dump()
        data["linkedin"] = li
        return Participant(**data), "no_match"

    data = p.model_dump()

    # normaliza linkedin
    data["linkedin"] = li

    if (not data.get("email")) and rec.get("email"):
        data["email"] = rec["email"]

    if (not data.get("telefone")) and rec.get("telefone"):
        data["telefone"] = rec["telefone"]

    return Participant(**data), "matched"


# =========================
# OPENAI EXTRACTION (Structured output)
# =========================
def extract_with_openai(client: OpenAI, text: str) -> Participant:
    system_prompt = (
        "Extraia do texto os campos:\n"
        "nome, telefone, email, linkedin, empresa_atual, cargo, headline.\n\n"
        "Regras:\n"
        "- Retorne null se nao existir\n"
        "- Cargo SEM cidade ou pais\n"
        "- Nao invente dados\n"
        "- linkedin deve ser URL, se existir\n"
    )

    response = client.responses.parse(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        text_format=Participant,
    )
    return response.output_parsed


# =========================
# MAIN
# =========================
def main():
    print("API Key set?", bool(OPENAI_API_KEY))
    print("API Key prefix:", (OPENAI_API_KEY[:7] + "...") if OPENAI_API_KEY else "NONE")

    if not OPENAI_API_KEY or not OPENAI_API_KEY.strip().startswith("sk-"):
        raise RuntimeError("OPENAI_API_KEY invalida. Cole uma chave que comece com 'sk-'.")

    ensure_dirs()
    files = list_txt_files()

    client = OpenAI(api_key=OPENAI_API_KEY)
    cache = load_cache()

    # index por linkedin (para preencher email/telefone com 100% de certeza)
    idx_linkedin = load_database_index_by_linkedin(DATABASE_CSV)

    rows: List[Dict[str, Any]] = []
    match_rows: List[Dict[str, Any]] = []

    matched = 0
    no_linkedin = 0
    no_match = 0
    openai_calls = 0
    cache_hits = 0

    for path in files:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        sha = sha1_text(text)
        base_name = os.path.basename(path)

        # 1) cache
        if sha in cache:
            p = Participant(**cache[sha])
            cache_hits += 1
        else:
            # 2) KV
            kv = parse_kv(text)
            p = kv_to_participant(kv)

            # 3) OpenAI só se precisar (otimização)
            # Se o KV já trouxe o linkedin, a gente pode tentar enriquecer do DB sem chamar OpenAI.
            # Só chamamos OpenAI se faltar coisas importantes (ex: linkedin, empresa, cargo, headline, nome).
            if not is_complete_for_openai(p):
                p = extract_with_openai(client, text)
                openai_calls += 1

            save_cache(sha, p.model_dump())

        # 4) Enriquecimento por LinkedIn (garantia)
        p2, status = enrich_only_by_linkedin(p, idx_linkedin)

        if status == "matched":
            matched += 1
        elif status == "no_linkedin":
            no_linkedin += 1
        else:
            no_match += 1

        rows.append({
            "arquivo": base_name,
            **p2.model_dump()
        })

        match_rows.append({
            "arquivo": base_name,
            "linkedin_txt": p.linkedin,
            "linkedin_norm": norm_linkedin(p.linkedin) if p.linkedin else None,
            "status": status,
            "email_final": p2.email,
            "telefone_final": p2.telefone,
        })

        print("Processado:", base_name, "| status:", status)

    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    df_match = pd.DataFrame(match_rows)
    df_match.to_csv(MATCH_REPORT_CSV, index=False, encoding="utf-8-sig")

    print("CSV gerado em:", OUT_CSV)
    print("Match report gerado em:", MATCH_REPORT_CSV)
    print("Registros:", len(df))
    print("Matched:", matched, "| No LinkedIn:", no_linkedin, "| No match:", no_match)
    print("Cache hits:", cache_hits, "| OpenAI calls:", openai_calls)


if __name__ == "__main__":
    main()
