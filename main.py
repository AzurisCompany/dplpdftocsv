import os
import re
import json
import glob
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

import pandas as pd
from pydantic import BaseModel
from openai import OpenAI

# Carrega variáveis de ambiente
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"
USE_OPENAI_FOR_IMPORTANCE = True

BASE_CANDIDATES = ["data", "Data"]
OUTPUT_CSV_NAME = "curriculos.csv"
CACHE_JSONL_NAME = "cache.jsonl"


class Participant(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    linkedin: Optional[str] = None
    empresa_atual: Optional[str] = None
    cargo: Optional[str] = None
    headline: Optional[str] = None
    nivel_importancia: Optional[int] = None


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


def ensure_dirs() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)


def list_txt_files() -> List[str]:
    files = sorted(glob.glob(TXT_GLOB))
    print("TXT_DIR:", TXT_DIR)
    print("Procurando:", TXT_GLOB)
    print("Encontrados:", len(files), "arquivos .txt")
    if not files:
        raise SystemExit(f"Nenhum TXT encontrado em {TXT_DIR}")
    return files


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


def norm_linkedin(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = str(s).strip().rstrip(".,;")
    m = re.search(r"(https?://(www\.)?linkedin\.com/[^\s)>\]]+)", s, re.I)
    if m:
        s = m.group(1).rstrip(".,;")
    if s.startswith("linkedin.com/"):
        s = "https://www." + s
    elif s.startswith("www.linkedin.com/"):
        s = "https://" + s
    s = re.sub(r"^https?://(www\.)?linkedin\.com", "https://www.linkedin.com", s, flags=re.I)
    s = s.split("?", 1)[0].split("#", 1)[0]
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
    return digits if len(digits) >= 8 else None


def clean_company(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*[-|•]\s*[A-ZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ].{0,40}$", "", s).strip()
    s = re.sub(r"(?i)\b(at|em|na|no)\s+", "", s).strip()
    return s or None


def finalize(p: Participant) -> Participant:
    d = p.model_dump()
    d["email"] = norm_email(d.get("email"))
    d["telefone"] = norm_phone(d.get("telefone"))
    d["linkedin"] = norm_linkedin(d.get("linkedin"))
    d["empresa_atual"] = clean_company(d.get("empresa_atual"))

    for k, v in list(d.items()):
        if isinstance(v, str) and not v.strip():
            d[k] = None

    ni = d.get("nivel_importancia")
    if ni is not None:
        try:
            ni = int(ni)
            ni = max(1, min(5, ni))
            d["nivel_importancia"] = ni
        except Exception:
            d["nivel_importancia"] = None

    return Participant(**d)


def normalize_key(k: str) -> str:
    k = k.lower().strip()
    k = k.replace("linked-in", "linkedin").replace("linked in", "linkedin")
    k = k.replace("e-mail", "email")
    k = k.replace("head line", "headline").replace("head-line", "headline")
    k = k.replace("empresa atual", "empresa_atual")
    k = k.replace("current company", "empresa_atual")
    k = k.replace("company", "empresa_atual")
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
        empresa_atual=kv.get("empresa_atual") or kv.get("empresa") or kv.get("company"),
        cargo=kv.get("cargo") or kv.get("role") or kv.get("position") or kv.get("posicao"),
        headline=kv.get("headline") or kv.get("resumo"),
    )


def kv_score(kv: Dict[str, str]) -> int:
    keys = ["nome", "email", "telefone", "linkedin", "empresa_atual", "cargo", "headline"]
    return sum(1 for k in keys if kv.get(k))


def norm_text(s: Optional[str]) -> str:
    if not s:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def classify_importance_local_1to5(empresa: str, cargo: str, headline: str) -> int:
    text = norm_text(f"{empresa or ''} {cargo or ''} {headline or ''}")

    if any(x in text for x in [
        "ceo", "cfo", "cto", "cio", "cmo", "coo", "chief",
        "president", "presidente", "vp", "vice president",
        "diretor", "director", "founder", "co-founder", "cofounder",
        "owner", "proprietario", "proprietário", "socio", "sócio"
    ]):
        return 5

    if any(x in text for x in [
        "gerente", "manager", "head of", "head",
        "coord", "coordenador", "coordinator",
        "supervisor", "supervisao", "supervisão",
        "lead", "lider", "líder", "team lead", "people manager"
    ]):
        return 4

    if any(x in text for x in [
        "estagi", "intern", "trainee",
        "aprendiz", "jovem aprendiz",
        "assistente", "assistant"
    ]):
        return 1

    if any(x in text for x in [
        "senior", "sênior", "sr",
        "specialist", "especialista",
        "consultor", "consultant", "pleno"
    ]):
        return 3

    if any(x in text for x in ["junior", "júnior", "jr"]):
        return 2

    return 2


def importance_needs_openai(empresa: str, cargo: str, headline: str, base_level: int) -> bool:
    if not USE_OPENAI_FOR_IMPORTANCE:
        return False
    if not OPENAI_API_KEY or not OPENAI_API_KEY.strip().startswith("sk-"):
        return False
    if base_level not in (2, 3):
        return False

    t = norm_text(f"{cargo} {headline}")
    ambiguous_terms = [
        "partner", "principal", "board", "advisor", "adviser", "strategic",
        "investor", "mentor", "managing", "executive", "owner"
    ]
    return any(x in t for x in ambiguous_terms)


def classify_importance_openai_1to5(client: OpenAI, empresa: str, cargo: str, headline: str) -> int:
    system_prompt = (
        "Classifique o nível hierárquico de 1 a 5.\n"
        "1=Entrada, 2=Operacional, 3=Especialista, 4=Liderança, 5=Executivo.\n"
        "Retorne APENAS o número."
    )
    user = f"Empresa: {empresa}\nCargo: {cargo}\nHeadline: {headline}"

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user},
            ],
        )

        text = resp.choices[0].message.content.strip()
        m = re.findall(r"\d+", text)
        if not m:
            return 2
        n = int(m[0])
        return max(1, min(5, n))
    except Exception as e:
        print(f"Erro ao chamar OpenAI para importância: {e}")
        return 2


def extract_with_openai(client: OpenAI, text: str) -> Participant:
    system_prompt = (
        "Extraia do texto em formato JSON os campos:\n"
        "nome, email, telefone, linkedin, empresa_atual, cargo, headline.\n"
        "Regras: retorne null se não existir; não invente; "
        "linkedin com URL; cargo sem cidade; empresa atual da experiência mais recente."
    )

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0,
        )

        content = resp.choices[0].message.content.strip()
        
        # Tenta extrair JSON do conteúdo
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return Participant(**data)
        else:
            return Participant()
    except Exception as e:
        print(f"Erro ao extrair com OpenAI: {e}")
        return Participant()


def extract_empresa_only(client: OpenAI, text: str) -> Optional[str]:
    system_prompt = (
        "Do texto, extraia APENAS a empresa atual/mais recente.\n"
        "Retorne um JSON com field 'empresa_atual' ou null."
    )

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0,
        )

        content = resp.choices[0].message.content.strip()
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return data.get("empresa_atual")
        return None
    except Exception as e:
        print(f"Erro ao extrair empresa: {e}")
        return None


def main():
    if not OPENAI_API_KEY or not OPENAI_API_KEY.strip().startswith("sk-"):
        raise RuntimeError(
            "OPENAI_API_KEY inválida.\n"
            "Adicione em .env: OPENAI_API_KEY=sk-..."
        )

    ensure_dirs()
    files = list_txt_files()

    client = OpenAI(api_key=OPENAI_API_KEY)
    cache = load_cache()

    rows: List[Dict[str, Any]] = []
    openai_calls = 0
    cache_hits = 0
    kv_only = 0
    empresa_fallback = 0
    importance_openai_calls = 0

    for path in files:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        sha = sha1_text(text)
        base_name = os.path.basename(path)

        if sha in cache:
            p = Participant(**cache[sha])
            cache_hits += 1
        else:
            kv = parse_kv(text)
            score = kv_score(kv)

            if score >= 4:
                p = kv_to_participant(kv)
                kv_only += 1
            else:
                p = extract_with_openai(client, text)
                openai_calls += 1

            p = finalize(p)

            if not p.empresa_atual and (p.cargo or p.headline):
                emp = extract_empresa_only(client, text)
                openai_calls += 1
                empresa_fallback += 1
                if emp:
                    p.empresa_atual = clean_company(emp)

            base_level = classify_importance_local_1to5(
                p.empresa_atual or "", p.cargo or "", p.headline or ""
            )
            if importance_needs_openai(p.empresa_atual or "", p.cargo or "", p.headline or "", base_level):
                p.nivel_importancia = classify_importance_openai_1to5(
                    client, p.empresa_atual or "", p.cargo or "", p.headline or ""
                )
                importance_openai_calls += 1
            else:
                p.nivel_importancia = base_level

            p = finalize(p)
            save_cache(sha, p.model_dump())

        p = finalize(p)

        if p.nivel_importancia is None:
            base_level = classify_importance_local_1to5(
                p.empresa_atual or "", p.cargo or "", p.headline or ""
            )
            if importance_needs_openai(p.empresa_atual or "", p.cargo or "", p.headline or "", base_level):
                p.nivel_importancia = classify_importance_openai_1to5(
                    client, p.empresa_atual or "", p.cargo or "", p.headline or ""
                )
                importance_openai_calls += 1
            else:
                p.nivel_importancia = base_level
            p = finalize(p)

        rows.append({
            "Nome": p.nome,
            "Email": p.email,
            "Telefone": p.telefone,
            "Linked-in": p.linkedin,
            "Empresa": p.empresa_atual,
            "Cargo": p.cargo,
            "HeadLine": p.headline,
            "Nivel_Importancia": p.nivel_importancia,
        })

        print(f"✓ {base_name} | empresa: {p.empresa_atual} | nível: {p.nivel_importancia}")

    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    print(f"\n✅ CSV gerado em: {OUT_CSV}")
    print(f"📊 Registros: {len(df)}")
    print(f"📦 Cache hits: {cache_hits}")
    print(f"🔄 OpenAI calls: {openai_calls} | KV-only: {kv_only} | Empresa fallback: {empresa_fallback}")
    print(f"⭐ Importance OpenAI calls: {importance_openai_calls}")


if __name__ == "__main__":
    main()