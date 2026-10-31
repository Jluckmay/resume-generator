"""Extratores automáticos de dados para GitHub, ORCID, Lattes, LinkedIn, Google Scholar e Portfólio com proteção anti-SSRF e anti-DoS."""

from __future__ import annotations

import io
import ipaddress
import re
import socket
import unicodedata
import urllib.parse
import defusedxml.ElementTree as defused_ET
import xml.etree.ElementTree as ET  # fallback apenas se defusedxml não estiver disponível
import zipfile
from collections import Counter
from typing import Any, Dict, List, Tuple

import requests
from bs4 import BeautifulSoup
from .i18n import translate_experience_bullet_to_en
from .text_utils import finalize_project_description, remove_terminal_abbreviation_ellipsis, truncate_at_clause_boundary

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

_MAX_HTTP_BYTES = 1_500_000  # 1.5 MB max download size for external pages
_MAX_UPLOAD_FILE_BYTES = 10 * 1024 * 1024  # 10 MB max upload size
_MAX_UNCOMPRESSED_XML_BYTES = 15 * 1024 * 1024  # 15 MB max uncompressed Lattes XML
_MAX_ZIP_ENTRIES = 100  # Limite máximo de entradas em arquivos ZIP
_MAX_ZIP_COMPRESSION_RATIO = 100  # Razão máxima de compressão permitida (anti-ZIP bomb)

def parse_linkedin_input(val: str) -> Tuple[str, str]:
    """Normaliza o input do LinkedIn para (url_completa, nick).
    Aceita URL completa (https://linkedin.com/in/nick), in/nick, @nick ou apenas nick.
    """
    v = str(val or "").strip().lstrip("@")
    if not v:
        return "", ""
    m = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in/)?([a-zA-Z0-9_\-%]+)", v, re.IGNORECASE)
    if m:
        nick = m.group(1).strip("/")
        return f"https://www.linkedin.com/in/{nick}", nick
    if v.lower().startswith("in/"):
        nick = v[3:].strip("/")
        return f"https://www.linkedin.com/in/{nick}", nick
    if v.startswith(("http://", "https://")):
        clean_v = v.rstrip("/")
        parts = clean_v.split("/")
        nick = parts[-1] if parts else clean_v
        return clean_v, nick
    nick = v.strip("/")
    return f"https://www.linkedin.com/in/{nick}", nick


def parse_lattes_input(val: str) -> Tuple[str, str]:
    """Normaliza o input do Lattes para (url_completa, id_lattes).
    Aceita ID de 16 dígitos, ID alfanumérico K-code, URL lattes.cnpq.br ou buscatextual.
    """
    v = str(val or "").strip()
    if not v:
        return "", ""
    m16 = re.search(r"\b(\d{16})\b", v)
    if m16:
        lid = m16.group(1)
        return f"http://lattes.cnpq.br/{lid}", lid
    m_id = re.search(r"[?&]id=([A-Za-z0-9]+)", v)
    if m_id:
        lid = m_id.group(1)
        u = v if v.startswith(("http://", "https://")) else f"http://{v}"
        return u, lid
    if v.startswith(("http://", "https://")):
        parts = v.rstrip("/").split("/")
        lid = parts[-1] if parts else v
        return v, lid
    if "lattes.cnpq.br" in v.lower():
        parts = v.rstrip("/").split("/")
        lid = parts[-1] if parts else v
        return f"http://{v}", lid
    lid = v.strip("/")
    return f"http://lattes.cnpq.br/{lid}", lid


def parse_github_input(val: str) -> Tuple[str, str]:
    """Normaliza o input do GitHub para (url_completa, username_nick)."""
    v = str(val or "").strip().lstrip("@")
    if not v:
        return "", ""
    m = re.search(r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_\-%]+)", v, re.IGNORECASE)
    if m:
        nick = m.group(1).strip("/")
        return f"https://github.com/{nick}", nick
    if v.startswith(("http://", "https://")):
        parts = v.rstrip("/").split("/")
        nick = parts[-1] if parts else v
        return v, nick
    nick = v.strip("/")
    return f"https://github.com/{nick}", nick


def parse_orcid_input(val: str) -> Tuple[str, str]:
    """Normaliza o input do ORCID para (url_completa, orcid_id)."""
    v = str(val or "").strip()
    if not v:
        return "", ""
    m = re.search(r"\b(\d{4}-\d{4}-\d{4}-\d{3}[\dX])\b", v, re.IGNORECASE)
    if m:
        oid = m.group(1).upper()
        return f"https://orcid.org/{oid}", oid
    if v.startswith(("http://", "https://")):
        parts = v.rstrip("/").split("/")
        oid = parts[-1] if parts else v
        return v, oid
    oid = v.strip("/")
    return f"https://orcid.org/{oid}", oid


def parse_scholar_input(val: str) -> Tuple[str, str]:
    """Normaliza o input do Google Scholar para (url_completa, scholar_user_id).
    Aceita URL completa do Google Scholar, query string com user= ou apenas o ID do usuário.
    """
    v = str(val or "").strip()
    if not v:
        return "", ""
    m_user = re.search(r"[?&]user=([a-zA-Z0-9_\-]+)", v)
    if m_user:
        sid = m_user.group(1)
        return f"https://scholar.google.com/citations?user={sid}", sid
    if re.match(r"^[a-zA-Z0-9_\-]{8,20}$", v):
        return f"https://scholar.google.com/citations?user={v}", v
    if v.startswith(("http://", "https://")):
        clean_v = v.rstrip("/")
        return clean_v, ""
    return f"https://scholar.google.com/citations?user={v}", v



def _is_safe_public_url(url: str, allowed_domain_suffixes: tuple[str, ...] | None = None) -> tuple[bool, str]:
    """Valida URL contra ataques de SSRF (bloqueia loopback, redes privadas, link-local/metadata AWS/GCP)."""
    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception:
        return False, "URL malformada"

    if parsed.scheme not in ("http", "https"):
        return False, "Esquema de URL não permitido (use http ou https)"

    hostname = (parsed.hostname or "").strip().lower().rstrip(".")
    if not hostname or hostname in ("localhost", "0.0.0.0", "broadcasthost") or hostname.endswith(".local") or hostname.endswith(".internal"):
        return False, "Host local ou interno bloqueado por política anti-SSRF"

    if allowed_domain_suffixes:
        if not any(hostname == d or hostname.endswith("." + d) for d in allowed_domain_suffixes):
            return False, "Domínio não pertence à lista permitida para esta fonte"

    try:
        addr_infos = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except Exception:
        return False, "Não foi possível resolver o DNS do domínio informado"

    if not addr_infos:
        return False, "Sem endereço IP público associado ao domínio"

    for info in addr_infos:
        ip_str = info[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, "Endereço IP inválido"
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
            or not ip_obj.is_global
        ):
            return False, "Endereço IP privado/interno bloqueado por política anti-SSRF"

    return True, parsed.geturl()


def _safe_http_get(
    url: str,
    timeout: int = 8,
    allowed_domain_suffixes: tuple[str, ...] | None = None,
    max_redirects: int = 3,
) -> Tuple[int, str, str]:
    """Executa GET HTTP validando cada redirecionamento contra SSRF e limitando o tamanho da resposta."""
    current_url = url.strip()
    session = requests.Session()
    session.trust_env = False

    try:
        for _ in range(max_redirects + 1):
            ok, checked_or_err = _is_safe_public_url(current_url, allowed_domain_suffixes)
            if not ok:
                return 0, "", checked_or_err

            with session.get(
                checked_or_err,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
                allow_redirects=False,
                stream=True,
            ) as resp:
                if resp.status_code in (301, 302, 303, 307, 308):
                    loc = resp.headers.get("Location")
                    if not loc:
                        return resp.status_code, "", "Redirecionamento inválido"
                    current_url = urllib.parse.urljoin(checked_or_err, loc)
                    continue

                chunks: list[bytes] = []
                total = 0
                for chunk in resp.iter_content(chunk_size=16384):
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > _MAX_HTTP_BYTES:
                        break
                    chunks.append(chunk)
                raw_bytes = b"".join(chunks)
                enc = resp.encoding or "utf-8"
                text = raw_bytes.decode(enc, errors="ignore")
                return resp.status_code, text, ""
        return 0, "", "Número máximo de redirecionamentos excedido"
    except Exception as exc:
        return 0, "", f"Erro de conexão ({type(exc).__name__})"
    finally:
        session.close()


TECH_PATTERNS = [
    # Languages
    (r"\bPython(?:\s*3(?:\.\d+)?)?\b", "Python"),
    (r"\bTypeScript\b", "TypeScript"),
    (r"\bJavaScript\b|\bES6\b", "JavaScript"),
    (r"\bC\+\+\b", "C++"),
    (r"\bC#\b", "C#"),
    (r"\bRust\b", "Rust"),
    (r"\bGolang\b|\bGo\s+language\b", "Go"),
    (r"\bKotlin\b", "Kotlin"),
    (r"\bSwift\b", "Swift"),
    (r"\bPHP\b", "PHP"),
    (r"\bRuby\b", "Ruby"),
    (r"\bJava\b(?!\s*Script)", "Java"),
    (r"\b(?:linguagem C|linguagem de programa[çc][aã]o C|cabe[çc]alhos em C|c\s+codes|C99|ANSI C|\bC\b\s+(?:standards?|compiler|libraries|bibliotecas?))\b", "C"),
    (r"\bLaTeX\b|\bpdflatex\b", "LaTeX"),
    (r"\bHTML5?\b", "HTML5"),
    (r"\bCSS3?\b", "CSS3"),
    (r"\bBash\b|\bShell script\b|\bPowerShell\b", "Bash"),
    (r"\bSQL\b|\bPostgreSQL\b|\bMySQL\b|\bSQLite\b|\bMongoDB\b|\bRedis\b", "SQL"),
    
    # Frameworks & Libraries
    (r"\bFlask\b", "Flask"),
    (r"\bFastAPI\b", "FastAPI"),
    (r"\bDjango\b", "Django"),
    (r"\bReact(?:\.js)?\b", "React"),
    (r"\bVue(?:\.js)?\b", "Vue"),
    (r"\bAngular\b", "Angular"),
    (r"\bNode(?:\.js)?\b", "Node.js"),
    (r"\bExpress(?:\.js)?\b", "Express"),
    (r"\bJinja(?:2)?\b", "Jinja2"),
    (r"\bPygame\b", "Pygame"),
    (r"\bNumPy\b", "NumPy"),
    (r"\bPandas\b", "Pandas"),
    (r"\bPyTorch\b", "PyTorch"),
    (r"\bTensorFlow\b", "TensorFlow"),
    (r"\bOpenCV\b", "OpenCV"),
    (r"\bScikit-Learn\b", "Scikit-Learn"),
    
    # Tools & Infra
    (r"\bDocker\b", "Docker"),
    (r"\bKubernetes\b", "Kubernetes"),
    (r"\bGitHub Pages\b", "GitHub Pages"),
    (r"\bGitHub Actions\b", "GitHub Actions"),
    (r"\bGit\b", "Git"),
    (r"\bWebSocket(?:s)?\b", "WebSockets"),
    (r"\bTailwind(?:CSS)?\b", "Tailwind CSS"),
    (r"\bBootstrap\b", "Bootstrap"),
]

KNOWN_TECH_TOPICS = {
    "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
    "c": "C", "cpp": "C++", "csharp": "C#", "java": "Java", "html": "HTML5",
    "html5": "HTML5", "css": "CSS3", "css3": "CSS3", "latex": "LaTeX",
    "flask": "Flask", "fastapi": "FastAPI", "django": "Django", "react": "React",
    "vue": "Vue", "angular": "Angular", "nodejs": "Node.js", "node": "Node.js",
    "docker": "Docker", "kubernetes": "Kubernetes", "git": "Git", "bash": "Bash",
    "sql": "SQL", "postgresql": "PostgreSQL", "mysql": "MySQL", "sqlite": "SQLite",
    "mongodb": "MongoDB", "redis": "Redis", "github-pages": "GitHub Pages",
    "github-actions": "GitHub Actions", "websocket": "WebSockets", "websockets": "WebSockets",
    "tailwind": "Tailwind CSS", "bootstrap": "Bootstrap", "pygame": "Pygame",
    "pandas": "Pandas", "numpy": "NumPy", "pytorch": "PyTorch", "tensorflow": "TensorFlow"
}


def clean_markdown_text(raw: str) -> str:
    """Remove marcações de formatação markdown, links e badges preservando o conteúdo textual."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", raw)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def sanitize_project_description(desc: str, lang: str = "pt-br") -> str:
    """Padroniza descrições de projetos para iniciarem com substantivos descritivos.

    Elimina verbos no passado (ex: 'Desenvolveu', 'Criou', 'Implementou', 'Reuniu')
    e converte para substantivos diretos (ex: 'Gerador', 'Aplicação', 'Utilitário', 'Portfólio').
    """
    if not desc or not desc.strip():
        return ""
    text = remove_terminal_abbreviation_ellipsis(desc.strip())
    text = finalize_project_description(text)
    is_en = str(lang).lower().startswith("en")

    # Detecta se a frase está em inglês mesmo se lang não foi especificado
    if not is_en and re.match(r"^(?:Developed|Created|Implemented|Built|Designed|Engineered)", text, re.IGNORECASE):
        is_en = True

    if not is_en:
        # Padrão: 'Desenvolvido em Python para automação...' -> 'Ferramenta para automação... desenvolvida em Python.'
        m_dev_em = re.match(r"^(?:Desenvolvido|Criado|Constru[ií]do)\s+em\s+([^,]+?)\s+para\s+(.*)$", text, re.IGNORECASE)
        if m_dev_em:
            tech_part, rest = m_dev_em.group(1), m_dev_em.group(2)
            clean_rest = rest.rstrip(".")
            return finalize_project_description(f"Ferramenta para {clean_rest} desenvolvida em {tech_part}.")

        # Padrão: 'Desenvolvido para automação...' -> 'Ferramenta para automação...'
        m_dev_para = re.match(r"^(?:Desenvolvido|Criado|Constru[ií]do)\s+para\s+(.*)$", text, re.IGNORECASE)
        if m_dev_para:
            return finalize_project_description(f"Ferramenta para {m_dev_para.group(1)}")

        # Padrão: 'Desenvolveu gerador...', 'Criou portfólio...', 'Implementou utilitário...', 'Reuniu implementações...'
        pt_verbs = r"(?:Desenvolveu|Criou|Implementou|Reuniu|Construiu|Elaborou|Projetou|Estruturou|Idealizou|Programou|Confeccionou|Organizou)"
        m_verb = re.match(rf"^{pt_verbs}\s+(?:(?:um|uma|o|a|os|as)\s+)?([A-Za-zÀ-ÖØ-öø-ÿ].*)$", text, re.IGNORECASE)
        if m_verb:
            noun_rest = m_verb.group(1).strip()
            return finalize_project_description(noun_rest[0].upper() + noun_rest[1:])

    else:
        # Padrões em inglês
        m_dev_in = re.match(r"^(?:Developed|Created|Built)\s+in\s+([^,]+?)\s+for\s+(.*)$", text, re.IGNORECASE)
        if m_dev_in:
            tech_part, rest = m_dev_in.group(1), m_dev_in.group(2)
            clean_rest = rest.rstrip(".")
            return finalize_project_description(f"Tool for {clean_rest} developed in {tech_part}.")

        m_dev_for = re.match(r"^(?:Developed|Created|Built)\s+for\s+(.*)$", text, re.IGNORECASE)
        if m_dev_for:
            return finalize_project_description(f"Tool for {m_dev_for.group(1)}")

        en_verbs = r"(?:Developed|Created|Implemented|Built|Designed|Engineered|Crafted|Constructed|Programmed|Gathered|Assembled|Authored)"
        m_verb_en = re.match(rf"^{en_verbs}\s+(?:(?:a|an|the)\s+)?([A-Za-z].*)$", text, re.IGNORECASE)
        if m_verb_en:
            noun_rest = m_verb_en.group(1).strip()
            return finalize_project_description(noun_rest[0].upper() + noun_rest[1:])

    return finalize_project_description(text)


def sanitize_experience_description(desc: str, lang: str = "pt-br") -> str:
    """Padroniza descrições e bullet points de experiências profissionais para iniciarem com substantivos e não verbos no passado.

    Exemplos:
    - 'Participou do processo...' -> 'Participação no processo...'
    - 'Orientou estudantes e apoiou...' -> 'Orientação a estudantes e apoio...'
    - 'Acompanhou estudantes e apoiou...' -> 'Acompanhamento de estudantes e apoio...'
    - 'Desenvolveu figuras...' -> 'Desenvolvimento de figuras...'
    - 'Ensinou conceitos...' -> 'Ensino de conceitos...'
    - 'Realizou trabalho voluntário...' -> 'Realização de trabalho voluntário...'
    """
    if not desc or not desc.strip():
        return ""
    text = remove_terminal_abbreviation_ellipsis(desc.strip())
    is_en = str(lang).lower().startswith("en")

    # Detecta se a frase está em inglês mesmo se lang não foi especificado
    if not is_en and re.match(r"^(?:Led|Managed|Developed|Designed|Implemented|Created|Taught|Mentored|Guided|Participated|Assisted|Conducted|Coordinated|Collaborated|Organized|Engineered)\b", text, re.IGNORECASE):
        is_en = True

    if not is_en:
        conversions = [
            # Participou
            (r"^\s*participou\s+no\b", "Participação no"),
            (r"^\s*participou\s+na\b", "Participação na"),
            (r"^\s*participou\s+nos\b", "Participação nos"),
            (r"^\s*participou\s+nas\b", "Participação nas"),
            (r"^\s*participou\s+do\b", "Participação no"),
            (r"^\s*participou\s+da\b", "Participação na"),
            (r"^\s*participou\s+dos\b", "Participação nos"),
            (r"^\s*participou\s+das\b", "Participação nas"),
            (r"^\s*participou\s+de\b", "Participação em"),
            (r"^\s*participou\s+em\b", "Participação em"),
            (r"^\s*participou\b", "Participação em"),

            # Orientou / Acompanhou / Ensinou / Desenvolveu
            (r"^\s*orientou\s+(?:a\s+|de\s+)?", "Orientação a "),
            (r"^\s*acompanhou\s+(?:de\s+)?", "Acompanhamento de "),
            (r"^\s*ensinou\s+(?:de\s+)?", "Ensino de "),
            (r"^\s*desenvolveu\s+(?:de\s+)?", "Desenvolvimento de "),

            # Realizou
            (r"^\s*realizou\s+trabalho\s+volunt[aá]rio\b", "Realização de trabalho voluntário"),
            (r"^\s*realizou\s+(?:de\s+)?", "Realização de "),

            # Liderou / Coordenou / Gerenciou
            (r"^\s*liderou\s+(?:de\s+)?", "Liderança de "),
            (r"^\s*coordenou\s+(?:de\s+)?", "Coordenação de "),
            (r"^\s*(?:gerenciou|geriu)\s+(?:de\s+)?", "Gerenciamento de "),

            # Implementou / Criou / Elaborou / Ministrou
            (r"^\s*implementou\s+(?:de\s+)?", "Implementação de "),
            (r"^\s*criou\s+(?:de\s+)?", "Criação de "),
            (r"^\s*elaborou\s+(?:de\s+)?", "Elaboração de "),
            (r"^\s*ministrou\s+(?:de\s+)?", "Ministração de "),

            # Apoiou / Atuou
            (r"^\s*apoiou\s+no\b", "Apoio ao"),
            (r"^\s*apoiou\s+na\b", "Apoio à"),
            (r"^\s*apoiou\s+nos\b", "Apoio aos"),
            (r"^\s*apoiou\s+nas\b", "Apoio às"),
            (r"^\s*apoiou\s+(?:a\s+)?", "Apoio a "),
            (r"^\s*atuou\s+como\b", "Atuação como"),
            (r"^\s*atuou\s+na\b", "Atuação na"),
            (r"^\s*atuou\s+no\b", "Atuação no"),
            (r"^\s*atuou\s+nos\b", "Atuação nos"),
            (r"^\s*atuou\s+nas\b", "Atuação nas"),
            (r"^\s*atuou\s+em\b", "Atuação em"),
            (r"^\s*atuou\b", "Atuação em"),

            # Prestou / Colaborou / Conduziu / Executou / Planejou
            (r"^\s*prestou\s+assessoria\s+(?:a\s+)?", "Assessoria a "),
            (r"^\s*prestou\s+apoio\s+(?:a\s+)?", "Apoio a "),
            (r"^\s*prestou\s+suporte\s+(?:a\s+)?", "Suporte a "),
            (r"^\s*prestou\s+(?:de\s+)?", "Prestação de "),
            (r"^\s*colaborou\s+com\b", "Colaboração com"),
            (r"^\s*colaborou\s+(?:em\s+)?", "Colaboração em "),
            (r"^\s*conduziu\s+(?:de\s+)?", "Condução de "),
            (r"^\s*executou\s+(?:de\s+)?", "Execução de "),
            (r"^\s*planejou\s+(?:de\s+)?", "Planejamento de "),

            # Auxiliou / Supervisionou / Construiu / Estruturou / Projetou
            (r"^\s*auxiliou\s+no\b", "Auxílio no"),
            (r"^\s*auxiliou\s+na\b", "Auxílio na"),
            (r"^\s*auxiliou\s+nos\b", "Auxílio nos"),
            (r"^\s*auxiliou\s+nas\b", "Auxílio nas"),
            (r"^\s*auxiliou\s+(?:em\s+)?", "Auxílio em "),
            (r"^\s*supervisionou\s+(?:de\s+)?", "Supervisão de "),
            (r"^\s*construiu\s+(?:de\s+)?", "Construção de "),
            (r"^\s*estruturou\s+(?:de\s+)?", "Estruturação de "),
            (r"^\s*projetou\s+(?:de\s+)?", "Projeto de "),

            # Pesquisou / Investigou / Organizou / Administrou / Otimizou / Automatizou
            (r"^\s*pesquisou\s+(?:de\s+|sobre\s+)?", "Pesquisa sobre "),
            (r"^\s*investigou\s+(?:de\s+|sobre\s+)?", "Investigação de "),
            (r"^\s*organizou\s+(?:de\s+)?", "Organização de "),
            (r"^\s*administrou\s+(?:de\s+)?", "Administração de "),
            (r"^\s*otimizou\s+(?:de\s+)?", "Otimização de "),
            (r"^\s*automatizou\s+(?:de\s+)?", "Automatização de "),
            (r"^\s*publicou\s+(?:de\s+)?", "Publicação de "),
            (r"^\s*apresentou\s+(?:de\s+)?", "Apresentação de "),
            (r"^\s*redigiu\s+(?:de\s+)?", "Redação de "),
            (r"^\s*revisou\s+(?:de\s+)?", "Revisão de "),
            (r"^\s*produziu\s+(?:de\s+)?", "Produção de "),
            (r"^\s*integrou\s+(?:de\s+)?", "Integração de "),
            (r"^\s*configurou\s+(?:de\s+)?", "Configuração de "),
            (r"^\s*instalou\s+(?:de\s+)?", "Instalação de "),
            (r"^\s*facilitou\s+(?:de\s+)?", "Facilitação de "),
            (r"^\s*articulou\s+(?:de\s+)?", "Articulação de "),
            (r"^\s*promoveu\s+(?:de\s+)?", "Promoção de "),
            (r"^\s*assessorou\s+(?:a\s+)?", "Assessoria a "),
            (r"^\s*treinou\s+(?:de\s+)?", "Treinamento de "),
            (r"^\s*capacitou\s+(?:de\s+)?", "Capacitação de "),
            (r"^\s*tutelou\s+(?:de\s+)?", "Tutoria de "),
            (r"^\s*migrou\s+(?:de\s+)?", "Migração de "),
            (r"^\s*analisou\s+(?:de\s+)?", "Análise de "),
            (r"^\s*gerou\s+(?:de\s+)?", "Geração de "),
        ]
        for pat, repl in conversions:
            if re.search(pat, text, re.IGNORECASE):
                text = re.sub(pat, repl, text, count=1, flags=re.IGNORECASE)
                break

        # Normaliza conjunções com verbos internos: 'e apoiou no' -> 'e apoio no'
        text = re.sub(r"\be apoiou no\b", "e apoio no", text, flags=re.IGNORECASE)
        text = re.sub(r"\be apoiou na\b", "e apoio na", text, flags=re.IGNORECASE)
        text = re.sub(r"\be apoiou o\b", "e apoio ao", text, flags=re.IGNORECASE)
        text = re.sub(r"\be apoiou a\b", "e apoio à", text, flags=re.IGNORECASE)
        text = re.sub(r"\be apoiou\b", "e apoio a", text, flags=re.IGNORECASE)
        text = re.sub(r"\be acompanhou\b", "e acompanhamento de", text, flags=re.IGNORECASE)
        text = re.sub(r"\be auxiliou\b", "e auxílio em", text, flags=re.IGNORECASE)
    else:
        text = translate_experience_bullet_to_en(text)
        conversions_en = [
            (r"^\s*led\s+(?:in\s+|the\s+)?", "Leadership of "),
            (r"^\s*managed\s+(?:the\s+)?", "Management of "),
            (r"^\s*developed\s+(?:the\s+)?", "Development of "),
            (r"^\s*designed\s+(?:the\s+)?", "Design of "),
            (r"^\s*implemented\s+(?:the\s+)?", "Implementation of "),
            (r"^\s*created\s+(?:the\s+)?", "Creation of "),
            (r"^\s*taught\s+(?:the\s+)?", "Instruction in "),
            (r"^\s*mentored\s+(?:the\s+)?", "Mentorship of "),
            (r"^\s*guided\s+(?:the\s+)?", "Guidance of "),
            (r"^\s*participated\s+in\b", "Participation in"),
            (r"^\s*participated\b", "Participation in"),
            (r"^\s*assisted\s+with\b", "Assistance with"),
            (r"^\s*assisted\s+in\b", "Assistance in"),
            (r"^\s*assisted\b", "Assistance in"),
            (r"^\s*conducted\s+(?:the\s+)?", "Conduction of "),
            (r"^\s*coordinated\s+(?:the\s+)?", "Coordination of "),
            (r"^\s*collaborated\s+with\b", "Collaboration with"),
            (r"^\s*collaborated\b", "Collaboration in"),
            (r"^\s*organized\s+(?:the\s+)?", "Organization of "),
            (r"^\s*engineered\s+(?:the\s+)?", "Engineering of "),
            (r"^\s*built\s+(?:the\s+)?", "Construction of "),
            (r"^\s*optimized\s+(?:the\s+)?", "Optimization of "),
            (r"^\s*automated\s+(?:the\s+)?", "Automation of "),
            (r"^\s*analyzed\s+(?:the\s+)?", "Analysis of "),
        ]
        for pat, repl in conversions_en:
            if re.search(pat, text, re.IGNORECASE):
                text = re.sub(pat, repl, text, count=1, flags=re.IGNORECASE)
                break

    text = text.strip()
    if text:
        text = text[0].upper() + text[1:]
    return text


def extract_project_info_from_readme(
    readme_text: str,
    repo_lang: str = "",
    topics: List[str] | None = None,
    target_lang: str = "pt-br",
    fallback_desc: str = "",
) -> Tuple[str, str]:
    """Extrai um resumo conciso (1-2 frases) baseado no README do projeto e identifica todas as ferramentas utilizadas."""
    if not readme_text or not readme_text.strip():
        primary = repo_lang.strip()
        if primary.lower() == "html": primary = "HTML5"
        elif primary.lower() == "css": primary = "CSS3"
        return sanitize_project_description(fallback_desc, target_lang), primary

    is_en = target_lang.lower().startswith("en")

    # 1. Identifica seção de idioma preferencial se o README for multilíngue
    section_text = readme_text
    if not is_en:
        m_pt = re.search(r"##+\s*(?:🇧🇷\s*)?Portugu[eê]s.*?(?=(?:##+\s*(?:🇺🇸\s*)?English|\Z))", readme_text, re.IGNORECASE | re.DOTALL)
        if m_pt:
            section_text = m_pt.group(0)
    else:
        m_en = re.search(r"##+\s*(?:🇺🇸\s*)?English.*?(?=(?:##+\s*(?:🇧🇷\s*)?Portugu[eê]s|\Z))", readme_text, re.IGNORECASE | re.DOTALL)
        if m_en:
            section_text = m_en.group(0)

    # 2. Extrai o melhor parágrafo descritivo
    paragraphs = section_text.split("\n\n")
    candidate_paras = []
    for p in paragraphs:
        lines = [line.strip() for line in p.splitlines() if line.strip()]
        cleaned_lines = []
        for line in lines:
            if line.startswith(("#", ">", "|", "-", "*", "1.", "2.", "3.", "---", "===")):
                continue
            cleaned_lines.append(line)
        para = clean_markdown_text(" ".join(cleaned_lines))
        if len(para) < 25:
            continue
        if re.match(r"^(?:read in|leia em|idioma|language|aplica[çc][aã]o|live application|table of contents|sum[aá]rio)", para, re.IGNORECASE):
            continue
        candidate_paras.append(para)

    best_summary = ""
    for para in candidate_paras:
        if re.match(r"^desenvolvido por\b", para, re.IGNORECASE):
            parts = re.split(r"(?<=[.!?])\s+", para)
            if len(parts) > 1 and len(" ".join(parts[1:])) > 30:
                best_summary = " ".join(parts[1:])
                break
            continue
        best_summary = para
        break

    if not best_summary and fallback_desc:
        best_summary = fallback_desc
    elif not best_summary and candidate_paras:
        best_summary = candidate_paras[0]

    # Trunca no limite de frase (~160-200 caracteres)
    if best_summary:
        sentences = re.split(r"(?<=[.!?])\s+", best_summary)
        if sentences:
            accum = sentences[0]
            for s in sentences[1:]:
                if len(accum) + len(s) + 1 <= 190:
                    accum = f"{accum} {s}"
                else:
                    break
            if len(accum) > 210:
                accum = truncate_at_clause_boundary(accum, 205)
            best_summary = accum

    # 3. Detecta ferramentas e linguagens (Tech Stack completa)
    detected_tech = []
    seen = set()

    # Prioridade A: Linguagem principal informada pelo GitHub
    if repo_lang:
        primary = repo_lang.strip()
        if primary.lower() == "html": primary = "HTML5"
        elif primary.lower() == "css": primary = "CSS3"
        detected_tech.append(primary)
        seen.add(primary.lower())

    # Prioridade B: Tópicos técnicos do repositório
    for t in (topics or []):
        t_low = t.strip().lower()
        if t_low in KNOWN_TECH_TOPICS:
            name = KNOWN_TECH_TOPICS[t_low]
            if name.lower() not in seen:
                detected_tech.append(name)
                seen.add(name.lower())

    # Prioridade C: Varredura de tecnologias no README
    for pat, name in TECH_PATTERNS:
        if name.lower() in seen:
            continue
        if re.search(pat, readme_text, re.IGNORECASE):
            detected_tech.append(name)
            seen.add(name.lower())

    return sanitize_project_description(best_summary, target_lang), ", ".join(detected_tech)


def extract_github(github_input: str, target_lang: str = "pt-br") -> Dict[str, Any]:
    """Extrai perfil, linguagens e principais repositórios públicos via API do GitHub."""
    if not github_input or not github_input.strip():
        return {}

    cleaned = github_input.strip().rstrip("/")
    match = re.search(r"github\.com/([A-Za-z0-9_.-]+)", cleaned, re.IGNORECASE)
    username = match.group(1) if match else cleaned.lstrip("@").split("/")[0]
    username = re.sub(r"[^A-Za-z0-9-]", "", username)[:39]
    if not username:
        return {"error": "Usuário GitHub inválido"}

    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    result: Dict[str, Any] = {
        "username": username,
        "url": f"https://github.com/{username}",
    }

    try:
        r_user = requests.get(f"https://api.github.com/users/{username}", headers=headers, timeout=10)
        if r_user.status_code != 200:
            result["error"] = f"HTTP {r_user.status_code}"
            # Resilient HTML fallback: when unauthenticated API hits rate limit (HTTP 403 on Render), scrape public HTML
            try:
                r_html = requests.get(f"https://github.com/{username}", headers={"User-Agent": USER_AGENT}, timeout=10)
                if r_html.status_code == 200:
                    soup_gh = BeautifulSoup(r_html.text, "html.parser")
                    name_el = soup_gh.find(itemprop="name") or soup_gh.find(class_=re.compile(r"p-name|vcard-fullname"))
                    if name_el and name_el.get_text(strip=True):
                        result["name"] = name_el.get_text(strip=True)
                    loc_el = soup_gh.find(itemprop="homeLocation") or soup_gh.find(class_=re.compile(r"p-label"))
                    if loc_el and loc_el.get_text(strip=True):
                        result["location"] = loc_el.get_text(strip=True)
                    bio_el = soup_gh.find(class_=re.compile(r"user-profile-bio|p-note"))
                    if bio_el and bio_el.get_text(strip=True):
                        result["bio"] = bio_el.get_text(strip=True)

                r_repos_html = requests.get(
                    f"https://github.com/{username}?tab=repositories",
                    headers={"User-Agent": USER_AGENT},
                    timeout=10,
                )
                if r_repos_html.status_code == 200:
                    soup_repos = BeautifulSoup(r_repos_html.text, "html.parser")
                    fb_repos: List[Dict[str, Any]] = []
                    fb_langs: Counter[str] = Counter()
                    for li in soup_repos.select("#user-repositories-list li, li.source"):
                        a_name = li.find("a", itemprop=re.compile(r"codeRepository"))
                        if not a_name:
                            continue
                        r_name = a_name.get_text(strip=True)
                        if not r_name:
                            continue
                        p_desc = li.find("p", itemprop="description")
                        r_desc = p_desc.get_text(" ", strip=True) if p_desc else ""
                        sp_lang = li.find("span", itemprop="programmingLanguage")
                        r_lang = sp_lang.get_text(strip=True) if sp_lang else ""
                        if r_lang:
                            fb_langs[r_lang] += 1
                        r_tech = r_lang
                        if len(fb_repos) < 6:
                            try:
                                readme_url = f"https://raw.githubusercontent.com/{username}/{r_name}/HEAD/README.md"
                                r_rm = requests.get(readme_url, headers={"User-Agent": USER_AGENT}, timeout=3)
                                if r_rm.status_code == 200 and r_rm.text:
                                    ext_desc, ext_tech = extract_project_info_from_readme(
                                        r_rm.text,
                                        repo_lang=r_lang,
                                        topics=[],
                                        target_lang=target_lang,
                                        fallback_desc=r_desc,
                                    )
                                    if ext_desc:
                                        r_desc = ext_desc
                                    if ext_tech:
                                        r_tech = ext_tech
                            except Exception:
                                pass
                        fb_repos.append({
                            "name": r_name,
                            "description": sanitize_project_description(r_desc, target_lang),
                            "language": r_lang,
                            "tech": r_tech,
                            "stars": 0,
                            "url": f"https://github.com/{username}/{r_name}",
                            "topics": [],
                        })
                        if len(fb_repos) >= 10:
                            break
                    if fb_repos:
                        result["repos"] = fb_repos
                    top_l = [lg for lg, _ in fb_langs.most_common(8)]
                    result["top_languages"] = top_l
                    result["languages"] = top_l
            except Exception:
                pass
            return result

        u = r_user.json()
        result.update(
            {
                "name": u.get("name") or "",
                "bio": u.get("bio") or "",
                "company": u.get("company") or "",
                "location": u.get("location") or "",
                "blog": u.get("blog") or "",
                "email": u.get("email") or "",
                "avatar_url": u.get("avatar_url") or "",
                "public_repos": u.get("public_repos") or 0,
                "followers": u.get("followers") or 0,
            }
        )
        if not result["email"] and u.get("bio"):
            m_em = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", u["bio"])
            if m_em and not m_em.group(0).lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif")):
                result["email"] = m_em.group(0).strip()

        r_repos = requests.get(
            f"https://api.github.com/users/{username}/repos?sort=updated&per_page=30",
            headers=headers,
            timeout=10,
        )
        repos_data = r_repos.json() if r_repos.status_code == 200 and isinstance(r_repos.json(), list) else []

        own_repos = [r for r in repos_data if isinstance(r, dict) and not r.get("fork")]
        own_repos.sort(
            key=lambda x: (x.get("stargazers_count", 0), x.get("updated_at", "")),
            reverse=True,
        )

        lang_counter: Counter[str] = Counter()
        repos_summary: List[Dict[str, Any]] = []
        for repo in own_repos[:10]:
            lang = repo.get("language") or ""
            if lang:
                lang_counter[lang] += 1
            repo_name = repo.get("name") or ""
            fallback_desc = repo.get("description") or ""
            topics = (repo.get("topics") or [])[:5]

            # Consulta README para extrair resumo contextual e todas as ferramentas utilizadas
            desc = fallback_desc
            tech = lang
            if repo_name and len(repos_summary) < 6:
                try:
                    readme_url = f"https://raw.githubusercontent.com/{username}/{repo_name}/HEAD/README.md"
                    r_readme = requests.get(readme_url, headers={"User-Agent": USER_AGENT}, timeout=3)
                    if r_readme.status_code == 200 and r_readme.text:
                        ext_desc, ext_tech = extract_project_info_from_readme(
                            r_readme.text,
                            repo_lang=lang,
                            topics=topics,
                            target_lang=target_lang,
                            fallback_desc=fallback_desc,
                        )
                        if ext_desc:
                            desc = ext_desc
                        if ext_tech:
                            tech = ext_tech
                except Exception:
                    pass

            repos_summary.append(
                {
                    "name": repo_name,
                    "description": sanitize_project_description(desc, target_lang),
                    "language": lang,
                    "tech": tech,
                    "stars": repo.get("stargazers_count") or 0,
                    "url": repo.get("html_url") or "",
                    "topics": topics,
                }
            )

        top_langs = [lang for lang, _ in lang_counter.most_common(8)]
        result["top_languages"] = top_langs
        result["languages"] = top_langs
        result["repos"] = repos_summary
    except Exception as exc:
        result["error"] = f"Falha ao consultar GitHub ({type(exc).__name__})"

    return result


def extract_orcid(orcid_input: str) -> Dict[str, Any]:
    """Extrai dados públicos do pesquisador via API v3.0 do ORCID."""
    if not orcid_input or not orcid_input.strip():
        return {}

    match = re.search(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", orcid_input.upper())
    if not match:
        return {"raw_input": orcid_input.strip(), "error": "Formato ORCID inválido"}

    orcid_id = match.group(1)
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    result: Dict[str, Any] = {
        "orcid_id": orcid_id,
        "url": f"https://orcid.org/{orcid_id}",
        "educations": [],
        "employments": [],
        "works": [],
        "awards": [],
        "fundings": [],
    }

    try:
        r = requests.get(f"https://pub.orcid.org/v3.0/{orcid_id}/record", headers=headers, timeout=12)
        if r.status_code != 200:
            result["error"] = f"HTTP {r.status_code}"
            return result

        data = r.json()
        person = data.get("person") or {}
        name_obj = person.get("name") or {}
        given = (name_obj.get("given-names") or {}).get("value") or ""
        family = (name_obj.get("family-name") or {}).get("value") or ""
        credit = (name_obj.get("credit-name") or {}).get("value") or ""
        result["name"] = credit or f"{given} {family}".strip()
        result["bio"] = ((person.get("biography") or {}).get("content")) or ""

        activities = data.get("activities-summary") or {}

        # Educations
        edu_groups = ((activities.get("educations") or {}).get("affiliation-group")) or []
        for grp in edu_groups:
            for s in grp.get("summaries") or []:
                ed = s.get("education-summary") or {}
                result["educations"].append(_parse_orcid_affiliation(ed))

        # Employments
        emp_groups = ((activities.get("employments") or {}).get("affiliation-group")) or []
        for grp in emp_groups:
            for s in grp.get("summaries") or []:
                em = s.get("employment-summary") or {}
                result["employments"].append(_parse_orcid_affiliation(em))

        # Works / Publications
        work_groups = ((activities.get("works") or {}).get("group")) or []
        for grp in work_groups[:20]:
            summaries = grp.get("work-summary") or []
            if not summaries:
                continue
            w = summaries[0]
            title = (((w.get("title") or {}).get("title") or {}).get("value")) or ""
            journal = ((w.get("journal-title") or {}).get("value")) or ""
            pub_date = w.get("publication-date") or {}
            year = ((pub_date.get("year") or {}).get("value")) or ""
            doi = ""
            ext_ids = ((w.get("external-ids") or {}).get("external-id")) or []
            for eid in ext_ids:
                if (eid.get("external-id-type") or "").lower() == "doi":
                    doi = eid.get("external-id-value") or ""
                    break
            if title:
                result["works"].append(
                    {"title": title, "journal": journal, "year": year, "doi": doi}
                )

        # Fundings (Grants, Bolsas, Financiamentos - não devem poluir premiações/distinções)
        for fund_grp in (activities.get("fundings") or {}).get("group") or []:
            for f_sum in fund_grp.get("funding-summary") or []:
                f_title = (((f_sum.get("title") or {}).get("title") or {}).get("value")) or ""
                f_type = f_sum.get("type") or ""
                f_org = ((f_sum.get("organization") or {}).get("name")) or ""
                f_start = (((f_sum.get("start-date") or {}).get("year") or {}).get("value")) or ""
                f_end = (((f_sum.get("end-date") or {}).get("year") or {}).get("value")) or ""
                yr_str = f"({f_start} - {f_end})" if f_start and f_end and f_start != f_end else (f"({f_start})" if f_start else "")
                if f_title:
                    type_prefix = "Bolsa / Grant: " if f_type == "grant" else ""
                    org_str = f" - {f_org}" if f_org else ""
                    result["fundings"].append(f"{type_prefix}{f_title}{org_str} {yr_str}".strip())

        for dist_grp in ((activities.get("distinctions") or {}).get("affiliation-group") or []):
            for s in dist_grp.get("summaries") or []:
                d_sum = s.get("distinction-summary") or {}
                d_role = d_sum.get("role-title") or ""
                d_org = ((d_sum.get("organization") or {}).get("name")) or ""
                d_yr = (((d_sum.get("start-date") or {}).get("year") or {}).get("value")) or ""
                if d_role:
                    org_s = f" - {d_org}" if d_org else ""
                    yr_s = f" ({d_yr})" if d_yr else ""
                    result["awards"].append(f"{d_role}{org_s}{yr_s}".strip())
    except Exception as exc:
        result["error"] = f"Falha ao consultar ORCID ({type(exc).__name__})"

    return result


def _parse_orcid_affiliation(item: Dict[str, Any]) -> Dict[str, str]:
    role = item.get("role-title") or ""
    dept = item.get("department-name") or ""
    deg = role or dept or ""
    org = ((item.get("organization") or {}).get("name")) or ""
    start_yr = (((item.get("start-date") or {}).get("year") or {}).get("value")) or ""
    end_yr = (((item.get("end-date") or {}).get("year") or {}).get("value")) or "Atual"
    return {
        "role": role,
        "dept": dept,
        "degree": deg,
        "course": deg,
        "org": org,
        "organization": org,
        "institution": org,
        "school": org,
        "company": org,
        "start": start_yr,
        "end": end_yr,
    }


def _strip_accents(s: str) -> str:
    """Remove acentos para comparação robusta de strings insensível a diacríticos."""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if unicodedata.category(c) != "Mn").lower()


_KNOWN_LANGS_CANONICAL: Dict[str, str] = {
    "ingles": "Inglês",
    "english": "English",
    "portugues": "Português",
    "portuguese": "Portuguese",
    "espanhol": "Espanhol",
    "spanish": "Spanish",
    "frances": "Francês",
    "french": "French",
    "alemao": "Alemão",
    "german": "German",
    "italiano": "Italiano",
    "italian": "Italian",
    "japones": "Japonês",
    "japanese": "Japanese",
    "chines": "Chinês",
    "chinese": "Chinese",
    "mandarim": "Mandarim",
    "mandarin": "Mandarin",
    "russo": "Russo",
    "russian": "Russian",
    "arabe": "Árabe",
    "arabic": "Arabic",
    "coreano": "Coreano",
    "korean": "Korean",
    "holandes": "Holandês",
    "dutch": "Dutch",
    "sueco": "Sueco",
    "swedish": "Swedish",
    "polones": "Polonês",
    "polish": "Polish",
    "hebraico": "Hebraico",
    "hebrew": "Hebrew",
    "grego": "Grego",
    "greek": "Greek",
    "latim": "Latim",
    "latin": "Latin",
}


def extract_languages_from_text(text: str) -> List[str]:
    """Extrai idiomas estruturados com proficiência de textos livres (LinkedIn PDF, Lattes texto/PDF, anotações)."""
    if not text:
        return []

    results: List[str] = []
    candidate_lines: List[str] = []

    # 1. Seção estruturada de Idiomas / Languages
    sec_match = re.search(
        r"(?:^|\n)\s*(?:Idiomas|Languages|Línguas|Lingua|Idioma)\s*[:\n](.+?)(?=(?:\n\s*(?:Formação|Educação|Education|Atuação|Experiência|Experience|Projetos|Projects|Publicações|Publications|Produção|Prêmios|Premios|Awards|Certificados|Certifications|Competências|Skills)\b|\Z))",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if sec_match:
        sec_text = sec_match.group(1).strip()
        candidate_lines.extend([l.strip() for l in sec_text.splitlines() if l.strip()])

    # 2. Linha inline 'Idiomas: Inglês (Fluente), Espanhol...'
    for m in re.finditer(r"(?:Idiomas|Languages|Línguas)\s*:\s*([^\n\r]+)", text, re.IGNORECASE):
        items = re.split(r"[,;]\s*", m.group(1))
        candidate_lines.extend(items)

    for line in candidate_lines:
        line_clean = re.sub(r"^[•\-\*,]\s*", "", line).strip()
        if not line_clean:
            continue
        first_token = line_clean.split()[0].rstrip(":,;()")
        first_norm = _strip_accents(first_token)
        if first_norm in _KNOWN_LANGS_CANONICAL:
            lang_label = _KNOWN_LANGS_CANONICAL[first_norm]
            low = line_clean.lower()
            if "compreende" in low:
                prof = (
                    "Avançado"
                    if ("bem" in low or "fluente" in low)
                    else ("Intermediário" if "razoavel" in low else "Básico")
                )
                results.append(f"{lang_label} ({prof})")
            elif "(" in line_clean and ")" in line_clean:
                paren_part = line_clean[line_clean.find("(") : line_clean.rfind(")") + 1]
                results.append(f"{lang_label} {paren_part}")
            elif " - " in line_clean or ": " in line_clean:
                sep = " - " if " - " in line_clean else ": "
                parts = line_clean.split(sep, 1)
                results.append(f"{lang_label} ({parts[1].strip()})")
            else:
                rem = line_clean[len(first_token) :].strip()
                if rem:
                    results.append(f"{lang_label} ({rem})")
                else:
                    results.append(lang_label)

    # Deduplica preservando ordem de aparição
    seen: set[str] = set()
    dedup: List[str] = []
    for r in results:
        key = _strip_accents(r.split()[0])
        if key not in seen:
            seen.add(key)
            dedup.append(r)
    return dedup


def extract_lattes(
    lattes_url: str = "",
    file_bytes: bytes | None = None,
    filename: str = "",
    pasted_text: str = "",
) -> Dict[str, Any]:
    """Extrai dados do Currículo Lattes a partir de XML/ZIP oficial, PDF/HTML, URL ou texto."""
    norm_url, lid = parse_lattes_input(lattes_url)
    result: Dict[str, Any] = {
        "url": norm_url,
        "lattes_id": lid,
        "educations": [],
        "employments": [],
        "publications": [],
        "projects": [],
        "languages": [],
        "awards": [],
    }

    # 1. Se o usuário enviou XML ou ZIP exportado do Lattes (com proteção contra ZIP Bomb e XXE)
    if file_bytes:
        if len(file_bytes) > _MAX_UPLOAD_FILE_BYTES:
            result["parse_warning"] = "Arquivo Lattes excede o limite de 10 MB."
            return result
        fname_lower = (filename or "").lower()
        try:
            if fname_lower.endswith(".zip") or file_bytes[:2] == b"PK":
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                    # Anti-ZIP bomb: limita número de entradas
                    entries = zf.infolist()
                    if len(entries) > _MAX_ZIP_ENTRIES:
                        raise ValueError(f"Arquivo ZIP excede o limite máximo de {_MAX_ZIP_ENTRIES} entradas.")
                    # Anti-ZIP bomb: verifica razão de compressão
                    for info in entries:
                        if info.compress_size > 0:
                            ratio = info.file_size / info.compress_size
                            if ratio > _MAX_ZIP_COMPRESSION_RATIO:
                                raise ValueError(
                                    f"Arquivo ZIP excede a razão máxima de compressão ({_MAX_ZIP_COMPRESSION_RATIO}x). "
                                    "Possível ZIP bomb detectado."
                                )
                    xml_infos = [i for i in entries if i.filename.lower().endswith(".xml")]
                    if xml_infos:
                        info = xml_infos[0]
                        if info.file_size > _MAX_UNCOMPRESSED_XML_BYTES:
                            raise ValueError("Arquivo XML descompactado excede o limite de segurança (15 MB).")
                        xml_bytes = zf.read(info.filename)
                        _parse_lattes_xml(xml_bytes, result)
            elif fname_lower.endswith(".xml") or b"<CURRICULO-VITAE" in file_bytes[:1000]:
                _parse_lattes_xml(file_bytes, result)
            elif fname_lower.endswith(".pdf") or file_bytes[:4] == b"%PDF":
                result["raw_text"] = _extract_pdf_text(file_bytes)
            else:
                soup = BeautifulSoup(file_bytes.decode("utf-8", errors="ignore"), "html.parser")
                result["raw_text"] = soup.get_text(" ", strip=True)[:5000]
        except Exception as exc:
            result["parse_warning"] = f"Aviso ao ler arquivo Lattes ({type(exc).__name__})"

    # 2. Se há texto colado
    if pasted_text and pasted_text.strip():
        existing = result.get("raw_text", "")
        result["raw_text"] = (existing + "\n" + pasted_text.strip()[:8000]).strip()

    # 3. Se informou apenas URL e ainda não há dados extraídos, tenta buscar página pública do CNPq
    if norm_url and not result["educations"] and not result.get("raw_text"):
        status_code, html_text, _ = _safe_http_get(
            norm_url,
            timeout=8,
            allowed_domain_suffixes=("cnpq.br",),
        )
        if status_code == 200 and html_text and "captcha" not in html_text.lower():
            soup = BeautifulSoup(html_text, "html.parser")
            txt = soup.get_text(" ", strip=True)
            if len(txt) > 200:
                result["raw_text"] = txt[:4000]

    if not result["languages"] and result.get("raw_text"):
        result["languages"] = extract_languages_from_text(result["raw_text"])

    if not result.get("email") and result.get("raw_text"):
        for cand in re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", result["raw_text"]):
            if not cand.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif")) and "example.com" not in cand.lower():
                result["email"] = cand.strip()
                break

    return result


def _parse_lattes_xml(xml_bytes: bytes, out: Dict[str, Any]) -> None:
    """Faz o parse estruturado do XML oficial da Plataforma Lattes (`CURRICULO-VITAE`) com bloqueio de DTD/Entities."""
    if len(xml_bytes) > _MAX_UNCOMPRESSED_XML_BYTES:
        raise ValueError("XML excede o tamanho máximo permitido.")
    # Detecta codificação a partir da declaração XML ou tenta UTF-8 e ISO-8859-1
    encoding_match = re.search(rb'encoding=["\']([a-zA-Z0-9_\-]+)["\']', xml_bytes[:200])
    declared_enc = encoding_match.group(1).decode("ascii", errors="ignore").lower() if encoding_match else ""
    if declared_enc in ("iso-8859-1", "latin-1", "latin1"):
        text = xml_bytes.decode("iso-8859-1", errors="replace")
    else:
        try:
            text = xml_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = xml_bytes.decode("iso-8859-1", errors="replace")

    if re.search(r"<!\s*(ENTITY|DOCTYPE)\b", text[:4096], flags=re.IGNORECASE):
        raise ValueError("Declarações DTD/ENTITY bloqueadas por segurança (anti-XXE).")

    try:
        root = defused_ET.fromstring(text)
    except Exception:
        # Fallback com ET apenas se defusedxml falhar (defusedxml já bloqueia XXE/DTD por padrão)
        root = ET.fromstring(text)
    id_lattes = root.attrib.get("NUMERO-IDENTIFICADOR", "")
    if id_lattes:
        out["lattes_id"] = id_lattes
        if not out.get("url"):
            out["url"] = f"http://lattes.cnpq.br/{id_lattes}"

    for node in root.iter():
        for attr_key in ("E-MAIL", "EMAIL", "E-MAIL-INSTITUCIONAL"):
            em_val = node.attrib.get(attr_key)
            if em_val and "@" in em_val and "." in em_val:
                out["email"] = em_val.strip()
                break
        if out.get("email"):
            break

    dados_gerais = root.find("DADOS-GERAIS")
    if dados_gerais is not None:
        out["name"] = dados_gerais.attrib.get("NOME-COMPLETO", "")
        resumo = dados_gerais.find("RESUMO-CV")
        if resumo is not None:
            out["summary"] = resumo.attrib.get("TEXTO-RESUMO-CV-RH", "")

        # Formação acadêmica
        formacao = dados_gerais.find("FORMACAO-ACADEMICA-TITULACAO")
        if formacao is not None:
            level_map = {
                "DOUTORADO": "Doutorado",
                "MESTRADO": "Mestrado",
                "MESTRADO-PROFISSIONALIZANTE": "Mestrado Profissional",
                "ESPECIALIZACAO": "Especialização",
                "GRADUACAO": "Graduação",
                "POS-DOUTORADO": "Pós-Doutorado",
            }
            for tag, label in level_map.items():
                for node in formacao.findall(tag):
                    out["educations"].append(
                        {
                            "level": label,
                            "course": node.attrib.get("NOME-CURSO", ""),
                            "institution": node.attrib.get("NOME-INSTITUICAO", ""),
                            "start": node.attrib.get("ANO-DE-INICIO", ""),
                            "end": node.attrib.get("ANO-DE-CONCLUSAO", "") or "Atual",
                            "thesis_title": (
                                node.attrib.get("TITULO-DA-DISSERTACAO-TESE", "")
                                or node.attrib.get("TITULO-DO-TRABALHO-DE-CONCLUSAO-DE-CURSO", "")
                            ),
                        }
                    )

        # Atuações profissionais
        atuacoes = dados_gerais.find("ATUACOES-PROFISSIONAIS")
        if atuacoes is not None:
            for ap in atuacoes.findall("ATUACAO-PROFISSIONAL"):
                inst = ap.attrib.get("NOME-INSTITUICAO", "")
                for vinc in ap.findall(".//VINCULOS"):
                    out["employments"].append(
                        {
                            "institution": inst,
                            "role": (
                                vinc.attrib.get("OUTRO-ENQUADRAMENTO-FUNCIONAL-INFORMADO", "")
                                or vinc.attrib.get("ENQUADRAMENTO-FUNCIONAL", "")
                            ),
                            "start": vinc.attrib.get("ANO-INICIO", ""),
                            "end": vinc.attrib.get("ANO-FIM", "") or "Atual",
                            "description": sanitize_experience_description(vinc.attrib.get("OUTRAS-INFORMACOES", "")),
                        }
                    )

                # Projetos de pesquisa
                for proj in ap.findall(".//PROJETO-DE-PESQUISA"):
                    out["projects"].append(
                        {
                            "title": proj.attrib.get("NOME-DO-PROJETO", ""),
                            "year": proj.attrib.get("ANO-INICIO", ""),
                            "description": proj.attrib.get("DESCRICAO-DO-PROJETO", ""),
                        }
                    )

        # Idiomas (suporte completo a IDIOMA e DESCRICAO-DO-IDIOMA do CNPq)
        idiomas = dados_gerais.find("IDIOMAS")
        if idiomas is not None:
            prof_map = {
                "bom": "Avançado",
                "lê bem": "Avançado",
                "fala bem": "Avançado",
                "muito_bom": "Fluente",
                "excelente": "Fluente",
                "fluente": "Fluente",
                "regular": "Intermediário",
                "razoavel": "Intermediário",
                "lê razoavel": "Intermediário",
                "fala razoavel": "Intermediário",
                "intermediário": "Intermediário",
                "intermediario": "Intermediário",
                "pouco": "Básico",
                "lê pouco": "Básico",
                "fala pouco": "Básico",
                "iniciante": "Básico",
                "básico": "Básico",
                "basico": "Básico",
                "nenhum": "",
            }
            for idm in idiomas.findall("IDIOMA"):
                raw_name = (
                    idm.attrib.get("DESCRICAO-DO-IDIOMA", "").strip()
                    or idm.attrib.get("IDIOMA", "").strip()
                    or idm.attrib.get("NOME-DO-IDIOMA", "").strip()
                )
                if not raw_name:
                    continue
                norm_key = _strip_accents(raw_name)
                if norm_key == "outro":
                    raw_name = idm.attrib.get("DESCRICAO-DO-IDIOMA", "").strip() or "Outro"
                    norm_key = _strip_accents(raw_name)
                display_name = _KNOWN_LANGS_CANONICAL.get(norm_key, raw_name)

                leit = prof_map.get(idm.attrib.get("PROFICIENCIA-DE-LEITURA", "").strip().lower(), "")
                fala = prof_map.get(idm.attrib.get("PROFICIENCIA-DE-FALA", "").strip().lower(), "")
                comp = prof_map.get(idm.attrib.get("PROFICIENCIA-DE-COMPREENSAO", "").strip().lower(), "")

                if leit and fala and leit == fala:
                    prof_str = leit
                elif fala:
                    prof_str = fala
                elif leit:
                    prof_str = f"Leitura: {leit}"
                elif comp:
                    prof_str = comp
                else:
                    prof_str = ""

                entry = f"{display_name} ({prof_str})" if prof_str else display_name
                out["languages"].append(entry)

        # Prêmios e títulos
        premios = dados_gerais.find("PREMIOS-TITULOS")
        if premios is not None:
            for pr in premios.findall("PREMIO-TITULO"):
                nome_pr = pr.attrib.get("NOME-DO-PREMIO-OU-TITULO", "").strip()
                ano_pr = pr.attrib.get("ANO-DA-PREMIACAO", "").strip()
                ent_pr = pr.attrib.get("NOME-DA-ENTIDADE-PROMOTORA", "").strip()
                if nome_pr:
                    clean_name = re.sub(r"\s*--\s*", " – ", nome_pr).strip()
                    parts = [clean_name]
                    if ent_pr:
                        parts.append(ent_pr)
                    base_str = " – ".join(parts)
                    if ano_pr and not re.search(rf"\b{ano_pr}\b", clean_name):
                        out["awards"].append(f"{base_str} ({ano_pr})")
                    else:
                        out["awards"].append(base_str)

    # Produção bibliográfica
    prod = root.find("PRODUCAO-BIBLIOGRAFICA")
    if prod is not None:
        for art in prod.findall(".//ARTIGO-PUBLICADO"):
            basico = art.find("DADOS-BASICOS-DO-ARTIGO")
            det = art.find("DETALHAMENTO-DO-ARTIGO")
            autores = [
                a.attrib.get("NOME-PARA-CITACAO", "")
                for a in art.findall("AUTORES")
                if a.attrib.get("NOME-PARA-CITACAO")
            ]
            if basico is not None:
                out["publications"].append(
                    {
                        "title": basico.attrib.get("TITULO-DO-ARTIGO", ""),
                        "year": basico.attrib.get("ANO-DO-ARTIGO", ""),
                        "doi": basico.attrib.get("DOI", ""),
                        "venue": det.attrib.get("TITULO-DO-PERIODICO-OU-REVISTA", "") if det is not None else "",
                        "authors": "; ".join(autores[:5]),
                    }
                )

        for trab in prod.findall(".//TRABALHO-EM-EVENTOS")[:10]:
            basico = trab.find("DADOS-BASICOS-DO-TRABALHO")
            det = trab.find("DETALHAMENTO-DO-TRABALHO")
            if basico is not None:
                out["publications"].append(
                    {
                        "title": basico.attrib.get("TITULO-DO-TRABALHO", ""),
                        "year": basico.attrib.get("ANO-DO-TRABALHO", ""),
                        "doi": basico.attrib.get("DOI", ""),
                        "venue": det.attrib.get("NOME-DO-EVENTO", "") if det is not None else "",
                        "authors": "",
                    }
                )


def extract_linkedin_skills(raw_text: str) -> List[str]:
    """Extract a LinkedIn Skills section from an exported profile or pasted text."""
    if not raw_text:
        return []

    heading = re.compile(r"^(?:top\s+skills|skills|compet[eê]ncias|habilidades|principais\s+compet[eê]ncias)\s*:?\s*(.*)$", re.I)
    stop_heading = re.compile(
        r"^(?:about|summary|experience|work experience|education|languages?|licenses?(?:\s+(?:and|&)\s+certifications?)?|certifications?|"
        r"publications?|projects?|volunteering|honors?(?:\s+and\s+awards?)?|recommendations?|references?|interests?|courses?|organizations?|activity|contact|contato|sobre|resumo|"
        r"experi[eê]ncia(?:\s+profissional)?|forma[cç][aã]o(?:\s+acad[eê]mica)?|idiomas|certifica[cç][oõ]es?|"
        r"publica[cç][oõ]es|projetos|voluntariado|pr[eê]mios|recomenda[cç][oõ]es|refer[eê]ncias|interesses|cursos|organiza[cç][oõ]es|atividade|contato)\s*:?[\s]*$",
        re.I,
    )
    found: List[str] = []
    seen: set[str] = set()
    in_skills = False

    def add_line(value: str) -> None:
        for item in re.split(r"\s*(?:[,;|•·]|\s{2,})\s*", value):
            clean = re.sub(r"\s+", " ", item).strip(" \t•·-–")
            clean = re.sub(r"\s*\(?\d+\s+endorsements?\)?$", "", clean, flags=re.I).strip()
            if clean and len(clean) <= 100 and not clean.endswith(":"):
                key = clean.casefold()
                if key not in seen:
                    seen.add(key)
                    found.append(clean)

    for raw_line in raw_text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" \t•·-–")
        if not line:
            continue
        match = heading.match(line)
        if match:
            in_skills = True
            add_line(match.group(1))
            continue
        if in_skills and stop_heading.match(line):
            break
        if in_skills:
            add_line(line)

    if not found:
        for match in re.finditer(
            r"(?im)\b(?:top\s+skills|skills|compet[eê]ncias|habilidades|principais\s+compet[eê]ncias)\s*[:\-]\s*([^\r\n]+)",
            raw_text,
        ):
            add_line(match.group(1))

    return found


def extract_linkedin(
    linkedin_url: str = "",
    file_bytes: bytes | None = None,
    pasted_text: str = "",
) -> Dict[str, Any]:
    """Extrai dados do LinkedIn a partir de URL, PDF exportado ('Salvar como PDF') ou texto."""
    norm_url, li_nick = parse_linkedin_input(linkedin_url)
    result: Dict[str, Any] = {"url": norm_url, "linkedin_nick": li_nick, "languages": [], "skills": []}

    if file_bytes:
        if len(file_bytes) > _MAX_UPLOAD_FILE_BYTES:
            result["error"] = "Arquivo PDF excede o limite de 10 MB."
            return result
        result["raw_text"] = _extract_pdf_text(file_bytes)

    if pasted_text and pasted_text.strip():
        existing = result.get("raw_text", "")
        result["raw_text"] = (existing + "\n" + pasted_text.strip()[:8000]).strip()

    if norm_url and not result.get("raw_text"):
        status_code, html_text, _ = _safe_http_get(
            norm_url,
            timeout=6,
            allowed_domain_suffixes=("linkedin.com",),
        )
        if status_code == 200 and html_text:
            soup = BeautifulSoup(html_text, "html.parser")
            title_meta = soup.find("meta", property="og:title")
            desc_meta = soup.find("meta", property="og:description")
            if title_meta and title_meta.get("content"):
                result["headline"] = title_meta["content"]
            if desc_meta and desc_meta.get("content"):
                result["summary"] = desc_meta["content"]
            result["skills"] = extract_linkedin_skills(soup.get_text("\n", strip=True))

    if result.get("raw_text"):
        result["skills"] = extract_linkedin_skills(result["raw_text"])

    if not result.get("languages") and result.get("raw_text"):
        result["languages"] = extract_languages_from_text(result["raw_text"])

    if not result.get("email") and result.get("raw_text"):
        for cand in re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", result["raw_text"]):
            if not cand.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif")) and "example.com" not in cand.lower():
                result["email"] = cand.strip()
                break

    return result


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extrai texto de um arquivo PDF usando pypdf/PyPDF2 se disponível ou fallback de streams."""
    if len(pdf_bytes) > _MAX_UPLOAD_FILE_BYTES:
        return ""
    for mod_name in ("pypdf", "PyPDF2"):
        try:
            mod = __import__(mod_name)
            reader = mod.PdfReader(io.BytesIO(pdf_bytes))
            pages = [p.extract_text() or "" for p in reader.pages[:25]]
            text = "\n".join(pages).strip()
            if text:
                return text[:6000]
        except Exception:
            continue

    # Fallback leve: extrai strings legíveis entre parênteses em fluxos PDF descomprimidos
    import zlib

    extracted: List[str] = []
    for match in re.finditer(rb"stream[\r\n]+(.*?)[\r\n]+endstream", pdf_bytes, re.DOTALL):
        chunk = match.group(1)
        try:
            decomp = zlib.decompress(chunk)
        except Exception:
            decomp = chunk
        for txt_match in re.finditer(rb"\(([^()]{2,200})\)", decomp):
            piece = txt_match.group(1).decode("latin-1", errors="ignore")
            if any(c.isalpha() for c in piece):
                extracted.append(piece)
    return " ".join(extracted)[:5000]


def extract_portfolio(portfolio_url: str = "") -> Dict[str, Any]:
    """Extrai projetos, bio, habilidades, idiomas, premiações e publicações de uma página web de portfólio pessoal (com proteção anti-SSRF)."""
    if not portfolio_url or not portfolio_url.strip():
        return {}

    url = portfolio_url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed_host = urllib.parse.urlparse(url).netloc or urllib.parse.urlparse(url).path
    if "." not in parsed_host:
        # e.g. "jluckmay" -> "jluckmay.github.io"
        clean_user = parsed_host.strip("/")
        if clean_user:
            url = f"https://{clean_user}.github.io"

    result: Dict[str, Any] = {
        "url": url,
        "languages": [],
        "awards": [],
        "publications": [],
        "educations": [],
        "employments": [],
    }
    try:
        status_code, html_text, err_msg = _safe_http_get(url, timeout=10)
        if status_code != 200 or not html_text:
            result["error"] = err_msg or f"HTTP {status_code}"
            return result

        soup = BeautifulSoup(html_text, "html.parser")

        title = (soup.title.string or "").strip() if soup.title else ""
        meta_desc = ""
        for meta_attr in ({"name": "description"}, {"property": "og:description"}):
            m = soup.find("meta", attrs=meta_attr)
            if m and m.get("content"):
                meta_desc = m["content"].strip()
                break

        # 0. Extração de Email
        for a_mail in soup.find_all("a", href=True):
            hr = a_mail["href"].strip()
            if hr.lower().startswith("mailto:"):
                cand_mail = re.sub(r"^mailto:", "", hr, flags=re.I).split("?")[0].strip()
                if "@" in cand_mail and "." in cand_mail.split("@")[-1]:
                    result["email"] = cand_mail
                    break
        if not result.get("email"):
            for cand in re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", html_text):
                c_low = cand.strip().lower()
                if not c_low.endswith((".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".css", ".js")) and "example.com" not in c_low and "domain.com" not in c_low:
                    result["email"] = cand.strip()
                    break

        # 1. Extração estruturada de Idiomas antes de decompor elementos
        languages: List[str] = []
        for art in soup.find_all(["article", "section", "div"]):
            h = art.find(["h2", "h3", "h4", "h5"])
            if h and any(k in h.get_text().lower() for k in ("idioma", "language", "língua")):
                for label_div in art.find_all(class_=re.compile(r"language-label|lang-item|language-item", re.I)):
                    spans = label_div.find_all(["span", "strong", "b"])
                    if len(spans) >= 2:
                        lg_name = spans[0].get_text(strip=True).rstrip(":")
                        lg_prof = spans[1].get_text(strip=True)
                        languages.append(f"{lg_name} ({lg_prof})")
                    elif spans:
                        languages.append(spans[0].get_text(strip=True))
                if not languages:
                    for li in art.find_all("li"):
                        txt = li.get_text(" ", strip=True)
                        if txt and len(txt) < 50:
                            languages.append(txt)

        # 2. Extração estruturada de Publicações (artigos com DOI ou cards científicos)
        publications: List[Dict[str, Any]] = []
        for art in soup.find_all(["article", "div", "li"]):
            doi_a = art.find("a", href=re.compile(r"doi\.org/|dx\.doi\.org/", re.I))
            if doi_a:
                h_el = art.find(["h3", "h4", "h5", "strong"])
                pub_title = h_el.get_text(" ", strip=True) if h_el else ""
                if not pub_title or len(pub_title) < 10 or "publicaç" in pub_title.lower() or "destaque" in pub_title.lower():
                    txt_lines = [l.strip() for l in art.get_text("\n").split("\n") if l.strip() and not l.strip().isdigit()]
                    for line in txt_lines:
                        if len(line) > 15 and "doi" not in line.lower() and "ver publicação" not in line.lower():
                            pub_title = line
                            break
                doi = doi_a["href"].split("doi.org/")[-1].strip() if "doi.org/" in doi_a["href"] else ""
                yr_m = re.search(r"\b(20\d\d|19\d\d)\b", art.get_text(" "))
                year = yr_m.group(1) if yr_m else ""
                clean_pub_title = re.sub(r"\s+", " ", pub_title).strip()
                venue = ""
                full_txt_lines = art.get_text("\n", strip=True)
                for part in re.split(r"·|\n| - ", full_txt_lines):
                    p = part.strip()
                    if clean_pub_title and (p.lower() in clean_pub_title.lower() or clean_pub_title.lower() in p.lower()):
                        continue
                    if any(k in p.lower() for k in ("revista", "workshop", "simpósio", "simposio", "journal", "proceedings", "conference", "anais")):
                        venue = p
                        break
                authors = ""
                for part in re.split(r"[·\n]", full_txt_lines):
                    p_pt = part.strip()
                    if p_pt.lower().startswith("com ") or p_pt.lower().startswith("with "):
                        authors = re.sub(r"(?i)^(?:com|with)\s+", "", p_pt).strip()
                        break
                if clean_pub_title and not any(p["title"].lower() == clean_pub_title.lower() or (doi and p.get("doi") == doi) for p in publications):
                    publications.append({
                        "title": clean_pub_title,
                        "venue": venue,
                        "year": year,
                        "authors": authors,
                        "doi": doi,
                        "url": doi_a["href"],
                    })

        # 2b. Extração estruturada de Projetos (cards de projeto ou links para repositórios GitHub)
        projects: List[Dict[str, Any]] = []
        for art in soup.find_all(["article", "div", "li"], class_=re.compile(r"\bproject\b|\bprojeto\b|\brepo\b|\bportfolio-item\b", re.I)):
            h_el = art.find(["h3", "h4", "h5", "strong"])
            if not h_el:
                continue
            p_name = h_el.get_text(" ", strip=True)
            if not p_name or len(p_name) > 80 or any(k in p_name.lower() for k in ("projetos", "projects", "publicações", "formação", "experiência")):
                continue
            p_desc = ""
            for p_tag in art.find_all("p"):
                t = p_tag.get_text(" ", strip=True)
                if t and len(t) > 15 and t != p_name:
                    p_desc = t
                    break
            p_url = ""
            for a_tag in art.find_all("a", href=True):
                hr = a_tag["href"].strip()
                if hr.startswith("http") and "doi.org" not in hr.lower():
                    p_url = hr
                    if "github.com/" in hr.lower():
                        break
            art_txt = art.get_text(" ", strip=True)
            p_techs: List[str] = []
            for pat, tname in TECH_PATTERNS:
                if re.search(pat, art_txt, re.I) and tname not in p_techs:
                    p_techs.append(tname)
            if not any(x["name"].lower() == p_name.lower() for x in projects):
                projects.append({
                    "name": p_name,
                    "description": sanitize_project_description(p_desc),
                    "tech": ", ".join(p_techs),
                    "url": p_url,
                })

        # 3. Extração estruturada de Premiações / Honrarias (Menção Honrosa, Prêmios, Títulos)
        awards: List[str] = []
        for aw_el in soup.find_all(class_=re.compile(r"\baward\b|\bpremiacao\b|\bpremio\b", re.I)):
            st = aw_el.find(["strong", "b", "h3", "h4"])
            title_aw = st.get_text(" ", strip=True) if st else ""
            full_t = aw_el.get_text(" ", strip=True)
            clean_t = re.sub(r"\s+", " ", full_t).strip()
            if any(k in clean_t.lower() for k in ("destaque", "ver publicação", "ver publicacao")):
                continue
            if title_aw and clean_t:
                detail = clean_t.replace(title_aw, "").strip(": -·\n")
                formatted = f"{title_aw}: {detail}" if detail else title_aw
                if 15 < len(formatted) < 300 and not any(formatted in a or a in formatted for a in awards):
                    awards.append(formatted)

        for el in soup.find_all(["article", "div", "li"]):
            if el.find_parent(class_=re.compile(r"\baward\b|\bpremiacao\b|\bpremio\b", re.I)):
                continue
            txt = el.get_text(" ", strip=True)
            if any(k in txt.lower() for k in ("destaque", "ver publicação", "ver publicacao")):
                continue
            if any(k in txt.lower() for k in ("menção honrosa", "mencao honrosa", "prêmio", "premio", "award", "honor", "distinção", "distincao", "segundo lugar", "primeiro lugar")):
                if 20 < len(txt) < 250:
                    clean_aw = re.sub(r"\s+", " ", txt).strip()
                    if not any(clean_aw in a or a in clean_aw for a in awards):
                        awards.append(clean_aw)

        # 4. Extração estruturada de Formação Acadêmica com Períodos
        educations: List[Dict[str, Any]] = []
        for art in soup.find_all(["article", "div", "li"], class_=re.compile(r"\bevent\b|\beducation\b|\bformacao\b", re.I)):
            h_el = art.find(["h3", "h4", "h5", "strong"])
            deg_title = h_el.get_text(" ", strip=True) if h_el else ""
            if not deg_title or not any(k in deg_title.lower() for k in ("mestrado", "bacharelado", "doutorado", "graduação", "graduacao", "especialização", "especializacao", "master", "bachelor", "phd", "ciência", "ciencia", "sistemas")):
                continue
            tm = art.find("time")
            period = tm.get_text(" ", strip=True) if tm else ""
            if not period:
                yr_match = re.search(r"\b(20\d\d|19\d\d)(?:\s*[-–—·]\s*(?:20\d\d|19\d\d|atual|presente))?\b", art.get_text(" "), re.I)
                period = yr_match.group(0) if yr_match else ""
            clean_period = re.sub(r"[–—·]", "-", period).strip()
            if "atual" in clean_period.lower():
                clean_period = re.sub(r"(?i)atual", "Atual", clean_period)

            st = art.find(["strong", "b", "h4", "h5"])
            inst = ""
            if st and st != h_el:
                inst = st.get_text(" ", strip=True)
            if not inst:
                for p_tag in art.find_all("p"):
                    p_txt = p_tag.get_text(" ", strip=True)
                    if any(k in p_txt.lower() for k in ("universidade", "ufmg", "ufv", "faculdade", "instituto", "campus")):
                        inst = p_txt
                        break
            inst = re.sub(r"\s*[–—·]\s*", " - ", inst).strip()

            p_desc = art.find_all("p")
            edu_desc = ""
            for p in p_desc:
                t = p.get_text(" ", strip=True)
                if t and t != inst:
                    edu_desc = t
                    break

            if not any(e["degree"].lower() == deg_title.lower() for e in educations):
                educations.append({
                    "degree": deg_title,
                    "institution": inst,
                    "period": clean_period,
                    "details": edu_desc,
                })

        # 5. Extração estruturada de Experiências Profissionais e Acadêmicas com Períodos
        employments: List[Dict[str, Any]] = []
        for art in soup.find_all(["article", "div", "li"], class_=re.compile(r"\bexperience\b|\batuacao\b|\btrabalho\b|\btrajetoria\b", re.I)):
            h_el = art.find(["h3", "h4", "h5", "strong"])
            if not h_el:
                continue
            htxt = h_el.get_text(" ", strip=True)
            if not htxt or any(k in htxt.lower() for k in ("experiência", "trajetória", "formação", "sobre")):
                continue

            parts = re.split(r"\s+[·\-\–\—\|]\s+", htxt, maxsplit=1)
            role = parts[0].strip()
            org = parts[1].strip() if len(parts) > 1 else ""

            tm = art.find("time")
            period = tm.get_text(" ", strip=True) if tm else ""
            if not period:
                yr_match = re.search(r"\b(20\d\d|19\d\d)(?:\s*[-–—·]\s*(?:20\d\d|19\d\d|atual|presente))?\b", art.get_text(" "), re.I)
                period = yr_match.group(0) if yr_match else ""
            clean_period = re.sub(r"[–—·]", "-", period).strip()
            if "atual" in clean_period.lower():
                clean_period = re.sub(r"(?i)atual", "Atual", clean_period)

            p_tag = art.find("p")
            emp_desc = p_tag.get_text(" ", strip=True) if p_tag else ""

            if not org and any(k in role.lower() for k in ("monitor", "tutor", "bolsista", "extensão", "extensao")):
                org = "Universidade Federal de Viçosa"

            if role and not any(e["role"].lower() == role.lower() for e in employments):
                employments.append({
                    "role": role,
                    "organization": org,
                    "period": clean_period,
                    "description": sanitize_experience_description(emp_desc),
                })

        for tag in soup(["script", "style", "svg", "noscript", "iframe"]):
            tag.decompose()

        headings = [
            h.get_text(" ", strip=True)
            for h in soup.find_all(["h1", "h2", "h3"])
            if h.get_text(" ", strip=True)
        ][:15]

        body_text = soup.get_text(" ", strip=True)
        body_text = re.sub(r"\s+", " ", body_text).strip()[:3500]

        portfolio_skills: List[str] = []
        for pat, tname in TECH_PATTERNS:
            if re.search(pat, body_text, re.I) and tname not in portfolio_skills:
                portfolio_skills.append(tname)

        if not languages:
            languages = extract_languages_from_text(body_text)

        # 6. Extração estruturada de Localização do Portfólio
        portfolio_loc = ""
        meta_loc = soup.find("meta", attrs={"name": re.compile(r"location|geo\.placename", re.I)})
        if meta_loc and meta_loc.get("content"):
            portfolio_loc = meta_loc["content"].strip()
        if not portfolio_loc:
            m_loc = re.search(r"\b([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*\s*[·,\-]\s*(?:Minas Gerais|MG|São Paulo|SP|Rio de Janeiro|RJ|Brasília|DF|Paraná|PR|Santa Catarina|SC|Rio Grande do Sul|RS|Bahia|BA|Ceará|CE|Pernambuco|PE|Brasil|Brazil))\b", body_text)
            if m_loc:
                cand = m_loc.group(1).strip()
                cand = re.sub(r"\s*[·–—]\s*", ", ", cand)
                cand = re.sub(r",\s*,+", ", ", cand).strip(", ")
                if 4 < len(cand) < 60:
                    portfolio_loc = cand

        result.update(
            {
                "title": title,
                "description": meta_desc,
                "location": portfolio_loc,
                "headings": headings,
                "raw_text": body_text,
                "languages": languages,
                "awards": awards,
                "publications": publications,
                "projects": projects,
                "skills": portfolio_skills,
                "educations": educations,
                "employments": employments,
            }
        )
    except Exception as exc:
        result["error"] = f"Falha ao extrair portfólio ({type(exc).__name__})"

    return result


def extract_scholar(scholar_input: str = "") -> Dict[str, Any]:
    """Extrai publicações, citações, índices e afiliação de perfil público do Google Scholar."""
    norm_url, sid = parse_scholar_input(scholar_input)
    if not norm_url:
        return {}

    fetch_url = f"https://scholar.google.com/citations?user={sid}&cstart=0&pagesize=100&hl=en" if sid else norm_url
    result: Dict[str, Any] = {
        "url": norm_url,
        "scholar_id": sid,
        "name": "",
        "affiliation": "",
        "interests": [],
        "metrics": {},
        "publications": [],
    }

    try:
        status_code, html_text, err_msg = _safe_http_get(
            fetch_url,
            timeout=10,
            allowed_domain_suffixes=("google.com", "google.com.br"),
        )
        if status_code != 200 or not html_text:
            result["error"] = err_msg or f"HTTP {status_code}"
            return result

        soup = BeautifulSoup(html_text, "html.parser")

        # Nome
        name_el = soup.find(id="gsc_prf_in")
        if name_el:
            result["name"] = name_el.get_text(" ", strip=True)

        # Afiliação
        aff_el = soup.find("div", class_="gsc_prf_il")
        if aff_el:
            result["affiliation"] = aff_el.get_text(" ", strip=True)

        # Áreas de interesse
        int_div = soup.find(id="gsc_prf_int")
        if int_div:
            result["interests"] = [a.get_text(" ", strip=True) for a in int_div.find_all("a") if a.get_text(strip=True)]

        # Métricas (Citações, h-index, i10-index)
        table_metrics = soup.find(id="gsc_rsb_st")
        if table_metrics:
            rows = table_metrics.find_all("tr")
            for tr in rows[1:]:
                cols = tr.find_all("td")
                if len(cols) >= 2:
                    m_label = tr.find("a").get_text(strip=True) if tr.find("a") else cols[0].get_text(strip=True)
                    result["metrics"][m_label] = cols[1].get_text(strip=True)

        # Publicações
        pub_rows = soup.find_all("tr", class_="gsc_a_tr")
        for r in pub_rows:
            title_el = r.find("a", class_="gsc_a_at")
            if not title_el:
                continue
            title = title_el.get_text(" ", strip=True)
            if not title:
                continue
            pub_link = ""
            if "href" in title_el.attrs:
                href = title_el["href"]
                pub_link = f"https://scholar.google.com{href}" if href.startswith("/") else href

            gray_els = r.find_all("div", class_="gs_gray")
            authors = gray_els[0].get_text(" ", strip=True) if len(gray_els) > 0 else ""
            venue_field = gray_els[1].get_text(" ", strip=True) if len(gray_els) > 1 else ""

            year_el = r.find("span", class_="gsc_a_h")
            year = year_el.get_text(strip=True) if year_el else ""

            cites_el = r.find("a", class_="gsc_a_ac")
            cites = cites_el.get_text(strip=True) if cites_el else ""

            result["publications"].append({
                "title": title,
                "authors": authors,
                "venue": venue_field,
                "year": year,
                "citations": cites,
                "url": pub_link,
            })
    except Exception as exc:
        result["error"] = f"Falha ao consultar Google Scholar ({type(exc).__name__})"

    return result




