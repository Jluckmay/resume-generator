"""Modelos de Currículo LaTeX integrados (Bilíngues: pt-BR e en-US) e motor de renderização determinístico.

Ao renderizar os templates integrados localmente a partir do JSON compacto gerado
pela API NVIDIA NIM, economizamos ~1.800 tokens de preâmbulo LaTeX por chamada
e garantimos compilação 100% livre de erros de sintaxe no `pdflatex`.
"""

from __future__ import annotations

import re
import unicodedata
import urllib.parse
from typing import Any, Dict, List, Sequence, Tuple

from .i18n import LATEX_I18N, normalize_lang
from .text_utils import finalize_project_description, truncate_at_clause_boundary
from .extractors import (
    parse_github_input,
    parse_lattes_input,
    parse_linkedin_input,
    parse_orcid_input,
    sanitize_project_description,
    sanitize_experience_description,
)

BUILTIN_TEMPLATES: Dict[str, Dict[str, str]] = {
    "modern_pro": {
        "id": "modern_pro",
        "name": "Moderno Executivo (Profissional & Tech) / Executive Modern",
        "recommended_for": "profissional",
        "description": (
            "Layout executivo moderno em coluna única com destaques em azul-petróleo, "
            "cabeçalho com foto opcional e links clicáveis (LinkedIn, GitHub, ORCID, Lattes)."
        ),
    },
    "academic_classic": {
        "id": "academic_classic",
        "name": "Acadêmico Clássico (Pesquisador / Pós-Graduação) / Academic Classic",
        "recommended_for": "academico",
        "description": (
            "Estrutura acadêmica formal com foco em Formação, Produção Bibliográfica (DOI), "
            "Projetos de Pesquisa, Docência, Prêmios, Lattes e ORCID."
        ),
    },
    "bubble": {
        "id": "bubble",
        "name": "Bubble CV",
        "recommended_for": "profissional",
        "url": "https://www.overleaf.com/latex/templates/bubblecv/bcynnjktwqsx",
        "description": (
            "Modelo Overleaf BubbleCV (por Mateusz Baran) com linha do tempo vertical em segundo plano, "
            "bolhas circulares TikZ para datas e seções, barras de progresso na coluna lateral e layout de página única."
        ),
    },
    "tech_sidebar": {
        "id": "tech_sidebar",
        "name": "Tech & Engenharia Duas Colunas (Barra Lateral) / Tech Sidebar",
        "recommended_for": "profissional",
        "description": (
            "Design assimétrico de duas colunas com foto, contatos, stack técnica e idiomas "
            "na coluna lateral e experiências/projetos na coluna principal."
        ),
    },
    "overleaf_russell_ti": {
        "id": "overleaf_russell_ti",
        "name": "Russel CV",
        "recommended_for": "profissional",
        "url": "https://www.overleaf.com/read/rgfqqnnynrmv#d5b171",
        "description": (
            "Modelo Overleaf Russell CV (Currículo T.I.) com foto lateral no cabeçalho, ícones FontAwesome 5, "
            "títulos com destaque nas 3 primeiras letras, tabela de habilidades e níveis de idiomas em círculos."
        ),
    },
    "minimal_ats": {
        "id": "minimal_ats",
        "name": "Minimalista ATS-Friendly (Alta Densidade) / Minimalist ATS",
        "recommended_for": "profissional",
        "description": (
            "Tipografia clássica de alto contraste otimizada para sistemas corporativos ATS "
            "e leitura rápida por recrutadores."
        ),
    },
    "overleaf_awesome_cv": {
        "id": "overleaf_awesome_cv",
        "name": "Awesome CV (Jason Richards) / Awesome CV",
        "recommended_for": "profissional",
        "url": "https://www.overleaf.com/articles/jason-richards-resume/chbxgnfyyvfc",
        "description": (
            "Modelo Overleaf Jason Richards' Résumé baseado no clássico Awesome-CV com cabeçalho centralizado, "
            "tipografia Roboto + Source Sans Pro, destaque de 3 letras nas seções e rodapé executivo."
        ),
    },
    "overleaf_single_page_keywords": {
        "id": "overleaf_single_page_keywords",
        "name": "Single Page + Keywords / Single Page + Keywords",
        "recommended_for": "profissional",
        "url": "https://www.overleaf.com/latex/templates/sample-single-page-resume-with-keywords/wmcxcgmtkxzk",
        "description": (
            "Modelo Overleaf de página única em duas colunas (Primož Godec & Salman Maqbool) com fonte Raleway, "
            "ícones circulares TikZ, seção de Resumo e palavras-chave (Keywords) de stack por experiência."
        ),
    },
    "nico_krieger": {
        "id": "nico_krieger",
        "name": "Krieger CV",
        "recommended_for": "profissional",
        "url": "https://www.overleaf.com/latex/templates/my-resume/rqzfybxqvpny",
        "description": (
            "Modelo baseado no my-resume de Nico Krieger com cabeçalho escuro de largura total, "
            "barra lateral destacada para contatos, habilidades avaliadas em 5 pontos e idiomas, e coluna principal para realizações."
        ),
    },
    "google_standard": {
        "id": "google_standard",
        "name": "Padrão Google (Big Tech / SWE) / Google Standard",
        "recommended_for": "profissional",
        "description": (
            "Modelo padrão de recrutamento Big Tech (Google SWE / Gayle Laakmann McDowell). "
            "Página única densa, margens de 0.5 polegadas, estrutura XYZ de realizações e formatação clean."
        ),
    },
    "ai_ats_max": {
        "id": "ai_ats_max",
        "name": "Otimizado para IA & ATS (Máxima Legibilidade) / AI & ATS Max-Readability",
        "recommended_for": "profissional",
        "description": (
            "Desenvolvido especificamente para triagem automatizada por LLMs (Gemini, Claude, GPT) e sistemas ATS. "
            "Fluxo textual 100% linear, metadados semânticos, matriz de competências e compatibilidade Unicode nativa."
        ),
    },
}


def escape_latex(text: Any) -> str:
    """Escapa caracteres especiais do LaTeX preservando acentuação UTF-8."""
    if text is None:
        return ""
    s = str(text).strip()
    if not s:
        return ""
    s = (
        s.replace("\u2013", "--")
        .replace("\u2014", "---")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", "``")
        .replace("\u201d", "''")
        .replace("\u2026", "...")
        .replace("\u00a0", " ")
    )
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    pattern = re.compile("|".join(re.escape(k) for k in replacements.keys()))
    return pattern.sub(lambda m: replacements[m.group(0)], s)


def escape_url(url: str) -> str:
    """Prepara uma URL para uso seguro dentro de \\href{url}{label}."""
    if not url:
        return ""
    u = url.strip()
    if not u.startswith(("http://", "https://", "mailto:")):
        if "@" in u and "/" not in u:
            return u.replace("%", r"\%").replace("#", r"\#").replace("&", r"\&")
        u = "https://" + u
    return u.replace("%", r"\%").replace("#", r"\#").replace("&", r"\&")



def abbreviate_researcher_name(name: str) -> str:
    """Abrevia o nome do pesquisador no formato acadêmico padrão (ex: 'João Lucas Mayrinck' -> 'J. L. Mayrinck')."""
    if not name or not str(name).strip():
        return ""
    parts = str(name).strip().split()
    if len(parts) <= 1:
        return parts[0]

    preps = {"de", "da", "do", "das", "dos", "e", "van", "von", "del", "di"}
    last = parts[-1]
    first_parts = parts[:-1]

    initials: List[str] = []
    for p in first_parts:
        clean = p.strip()
        if clean.lower() in preps:
            continue
        if clean.endswith("."):
            initials.append(clean)
        else:
            initials.append(f"{clean[0].upper()}.")

    if initials:
        return f"{' '.join(initials)} {last}"
    return last


def _get_platform_display(links: Dict[str, str], platform: str, candidate_name: str = "") -> str:
    """Retorna o nick (GitHub/LinkedIn), ID (Lattes/ORCID) ou nome abreviado (Scholar) para exibição ao lado do ícone."""
    if platform == "github":
        if links.get("github_nick"):
            return str(links["github_nick"]).strip()
        val = str(links.get("github") or "").strip()
        if val:
            _, nick = parse_github_input(val)
            return nick or val
        return "GitHub"

    if platform == "linkedin":
        if links.get("linkedin_nick"):
            return str(links["linkedin_nick"]).strip()
        val = str(links.get("linkedin") or "").strip()
        if val:
            _, nick = parse_linkedin_input(val)
            return nick or val
        return "LinkedIn"

    if platform == "orcid":
        if links.get("orcid_id"):
            return str(links["orcid_id"]).strip()
        val = str(links.get("orcid") or "").strip()
        if val:
            _, oid = parse_orcid_input(val)
            return oid or val
        return "ORCID"

    if platform == "lattes":
        if links.get("lattes_id"):
            return str(links["lattes_id"]).strip()
        val = str(links.get("lattes") or "").strip()
        if val:
            _, lid = parse_lattes_input(val)
            return lid or val
        return "Lattes"

    if platform == "scholar":
        # Utiliza o nome abreviado do pesquisador (ex: 'J. L. Mayrinck') ao invés do ID enigmático do Google Scholar
        sc_name = str(links.get("scholar_name") or links.get("scholar_author") or candidate_name or links.get("candidate_name") or "").strip()
        if sc_name:
            abbr = abbreviate_researcher_name(sc_name)
            if abbr:
                return abbr
        return "Google Scholar"

    return ""

def simplify_url_display(url: str) -> str:
    """Retorna uma versão amigável e simplificada da URL (remove protocolo http/https, www e barra final)."""
    if not url:
        return ""
    u = str(url).strip()
    u = re.sub(r"^https?://", "", u, flags=re.IGNORECASE)
    u = re.sub(r"^www\.", "", u, flags=re.IGNORECASE)
    u = u.rstrip("/")
    return u or url.strip()


def _build_contact_links(links: Dict[str, str], email: str, phone: str, location: str, candidate_name: str = "") -> List[str]:
    items: List[str] = []
    clean_em = (email or links.get("email") or "").strip()
    if clean_em:
        items.append(rf"\mbox{{\href{{mailto:{escape_url(clean_em)}}}{{\faIcon{{envelope}}\ {escape_latex(clean_em)}}}}}")
    if phone:
        items.append(rf"\mbox{{\faIcon{{phone}}\ {escape_latex(phone.strip())}}}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        items.append(rf"\mbox{{\href{{{escape_url(links['portfolio'])}}}{{\faIcon{{globe}}\ \textbf{{{port_disp}}}}}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=candidate_name))
        items.append(rf"\mbox{{\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{{li_disp}}}}}}}")
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=candidate_name))
        items.append(rf"\mbox{{\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{{gh_disp}}}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=candidate_name))
        items.append(rf"\mbox{{\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{{orcid_disp}}}}}}}")
    if links.get("scholar"):
        scholar_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=candidate_name))
        items.append(rf"\mbox{{\href{{{escape_url(links['scholar'])}}}{{\faIcon{{google}}\ \textbf{{{scholar_disp}}}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=candidate_name))
        items.append(rf"\mbox{{\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{{lattes_disp}}}}}}}")
    if location:
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(location.strip())
        items.append(rf"\mbox{{\href{{{escape_url(maps_url)}}}{{\faIcon{{map-marker-alt}}\ {escape_latex(location.strip())}}}}}")
    return items


ORCID_PATTERN = re.compile(
    r"\borcid\b|\b000[0-9]-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9Xx]\b|\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b",
    re.IGNORECASE,
)
PROFILE_LINK_PATTERN = re.compile(
    r"\b(?:lattes|orcid|github|linkedin)\.com\b|\blattes\.cnpq\.br\b|^\s*(?:id\s+)?lattes[:\s]|^\s*orcid[:\s]",
    re.IGNORECASE,
)
PLACEHOLDER_PATTERN = re.compile(
    r"^(?:none|n/a|na|nil|null|nenhum|nenhuma|sem prêmios|sem certificações|no awards|empty|-)$",
    re.IGNORECASE,
)


def normalize_text_for_cmp(text: str) -> str:
    no_diacritics = "".join(
        c for c in unicodedata.normalize("NFKD", str(text or ""))
        if unicodedata.category(c) != "Mn"
    ).lower()
    clean = re.sub(r"[^\w\s]", " ", no_diacritics)
    return re.sub(r"\s+", " ", clean).strip()


def clean_doi(doi: str) -> str:
    d = str(doi or "").strip().lower()
    d = re.sub(r"^(?:https?://)?(?:dx\.)?doi\.org/", "", d)
    d = re.sub(r"^doi:\s*", "", d)
    return d.strip("/")


def normalize_period(per: str, lang: str = "pt-br") -> str:
    s = str(per or "").strip()
    if not s:
        return ""
    # Normaliza hífens, en-dashes, em-dashes e pontos médios
    s = re.sub(r"[\u2013\u2014\u2212·]", "-", s)
    s = re.sub(r"\s*-\s*", " - ", s).strip()

    # Se YYYY - YYYY com anos idênticos (ex: 2025 - 2025) -> simplifica para o ano único 2025
    m = re.match(r"^(\d{4})\s*-\s*(\d{4})$", s)
    if m and m.group(1) == m.group(2):
        return m.group(1)

    is_en = lang.lower().startswith("en")
    curr_label = "Present" if is_en else "Atual"
    s = re.sub(r"(?i)\b(?:atual|presente|present)\b", curr_label, s)
    return s


def extract_period_sort_key(per: str) -> Tuple[int, int]:
    s = str(per or "").strip().lower()
    if any(k in s for k in ("atual", "present")):
        end_yr = 9999
    else:
        yrs = re.findall(r"\b(20\d\d|19\d\d)\b", s)
        end_yr = int(yrs[-1]) if yrs else 0
    yrs = re.findall(r"\b(20\d\d|19\d\d)\b", s)
    start_yr = int(yrs[0]) if yrs else 0
    return (end_yr, start_yr)


def extract_pub_year_sort_key(pub: Dict[str, Any]) -> Tuple[int, str]:
    y = str(pub.get("year") or "").strip()
    m = re.search(r"\b(20\d\d|19\d\d)\b", y)
    yr_int = int(m.group(1)) if m else 0
    return (yr_int, str(pub.get("title") or ""))


def extract_award_year_sort_key(aw: str) -> Tuple[int, str]:
    yrs = [int(y) for y in re.findall(r"\b(20\d\d|19\d\d)\b", str(aw))]
    return (max(yrs) if yrs else 0, str(aw))


def are_bullets_duplicate(b1: str, b2: str) -> bool:
    n1 = normalize_text_for_cmp(b1)
    n2 = normalize_text_for_cmp(b2)
    if not n1 or not n2:
        return False
    if n1 == n2 or n1 in n2 or n2 in n1:
        return True

    sem_groups = [
        {"geogebra", "dinamicas", "dynamic"},
        {"wordpress", "figma"},
        {"eleicao", "election", "caposcomp"},
        {"jogos", "game", "mentoring", "orientacao", "didaticos"},
        {"redes", "network", "seguranca", "security", "machine learning"},
        {"informatica", "office", "computing essentials"},
        {"programacao", "programming"},
    ]
    for grp in sem_groups:
        if any(k in n1 for k in grp) and any(k in n2 for k in grp):
            return True

    stop_words = {"de", "da", "do", "das", "dos", "em", "e", "a", "o", "as", "os", "ao", "aos", "para", "com", "por", "in", "of", "and", "the", "to", "for", "at", "on"}
    w1 = {w for w in n1.split() if w not in stop_words and len(w) > 2}
    w2 = {w for w in n2.split() if w not in stop_words and len(w) > 2}
    if w1 and w2:
        overlap = len(w1 & w2) / min(len(w1), len(w2))
        if overlap >= 0.5:
            return True
    return False


def is_bullet_english(b: str) -> bool:
    b_norm = normalize_text_for_cmp(b)
    en_words = {"the", "in", "and", "of", "to", "with", "for", "research", "coursework", "development", "investigation", "volunteer", "guidance", "mentoring", "student", "learning", "networks", "security", "election", "academic", "graduate", "teaching", "hands"}
    if any(c in b for c in "áàâãéêíóôõúç"):
        return False
    words = set(b_norm.split())
    return len(words & en_words) >= 1


def standardize_experience_entry(item: Dict[str, Any], lang: str = "pt-br") -> Dict[str, Any]:
    c_item = dict(item)
    is_en = str(lang).lower().startswith("en")
    c_item["period"] = normalize_period(c_item.get("period", ""), lang)
    role = str(c_item.get("role") or "").strip()
    org = str(c_item.get("organization") or "").strip()
    r_norm = normalize_text_for_cmp(role)
    o_norm = normalize_text_for_cmp(org)

    if is_en:
        if "eleitoral" in r_norm or "comissao" in r_norm:
            c_item["role"] = "Electoral Committee"
        elif any(k in r_norm for k in ("monitor de desenvolvimento de jogos", "jogos")) and ("monitor" in r_norm or "ta" in r_norm or "teaching" in r_norm):
            c_item["role"] = "Game Development Teaching Assistant"
        elif "bolsista" in r_norm and "pesquisa" in r_norm:
            c_item["role"] = "Research Fellow"
        elif "pesquisador" in r_norm or "mestrando" in r_norm:
            c_item["role"] = "Graduate Researcher / M.Sc. Student"
        elif "tutor de introducao" in r_norm or "informatica" in r_norm:
            c_item["role"] = "Introduction to Computer Science Tutor"
        elif "monitor de programacao" in r_norm:
            c_item["role"] = "Programming Teaching Assistant"
        elif "tutor de programacao" in r_norm:
            c_item["role"] = "Programming Tutor"
        elif "voluntario" in r_norm and "frontend" in r_norm:
            c_item["role"] = "Frontend Developer (Volunteer)"

        if "caposcomp" in o_norm or "caposcomp" in r_norm:
            c_item["organization"] = "CAPosComp/UFMG"
        elif any(k in o_norm for k in ("ufmg", "minas gerais")):
            c_item["organization"] = "Federal University of Minas Gerais (DCC / UFMG)"
        elif "funarben" in o_norm or "arthur bernardes" in o_norm:
            c_item["organization"] = "Arthur Bernardes Foundation (FUNARBEN / UFV)"
        elif any(k in o_norm for k in ("ufv", "vicosa", "paranaiba")):
            if "game" in c_item["role"].lower() or "jogo" in c_item["role"].lower():
                c_item["organization"] = "Federal University of Viçosa (UFV · Game Dev)"
            else:
                c_item["organization"] = "Federal University of Viçosa"
        elif "health lake" in o_norm:
            c_item["organization"] = "Health Lake Institute"

        raw_bullets = c_item.get("bullets") or []
        std_bullets = []
        for b in raw_bullets:
            b_s = str(b).strip()
            b_norm = normalize_text_for_cmp(b_s)
            if "eleicao da representacao discente" in b_norm or ("eleicao" in b_norm and "caposcomp" in b_norm):
                std_bullets.append("Participation in the student representation election process for the Graduate Student Academic Center (CAPosComp/UFMG).")
            elif "historia da computacao" in b_norm or "nocoes de informatica" in b_norm:
                std_bullets.append("Instruction in computer science history, computing essentials, office productivity tools, online security, copyright, and digital citizenship.")
            elif "orientacao pratica" in b_norm and ("jogos" in b_norm or "materiais" in b_norm):
                std_bullets.append("Hands-on guidance and student mentoring, supporting the development and review of course materials in Digital Game Development.")
            elif "figuras dinamicas no geogebra" in b_norm:
                std_bullets.append("Investigation of dynamic GeoGebra figures applied to mathematics education and educational technology.")
            elif "trabalho voluntario" in b_norm or "atuacao voluntaria" in b_norm:
                std_bullets.append("Volunteer work (Dec 2021 – Mar 2023) in Science and Technology: migrating website to WordPress, creating wireframes using Figma, website administration and maintenance.")
            else:
                std_bullets.append(sanitize_experience_description(b_s, lang=lang))

        clean_bullets = []
        for b in std_bullets:
            matched = False
            for idx, ex in enumerate(clean_bullets):
                if are_bullets_duplicate(b, ex):
                    matched = True
                    if is_bullet_english(b) and not is_bullet_english(ex):
                        clean_bullets[idx] = b
                    elif len(b) > len(ex):
                        clean_bullets[idx] = b
                    break
            if not matched:
                clean_bullets.append(b)
        c_item["bullets"] = clean_bullets

    else:
        if "eleitoral" in r_norm or "comissao" in r_norm:
            c_item["role"] = "Comissão eleitoral"
        elif "introducao ao desenvolvimento de jogos" in r_norm or "introduction to game development" in r_norm:
            c_item["role"] = "Monitor de Introdução ao Desenvolvimento de Jogos"
        elif r_norm == "monitor de jogos":
            c_item["role"] = "Monitor de Jogos"
        elif "game development teaching assistant" in r_norm or ("jogos" in r_norm and "monitor" in r_norm):
            c_item["role"] = "Monitor de Desenvolvimento de Jogos"
        elif "research fellow" in r_norm or ("bolsista" in r_norm and "pesquisa" in r_norm):
            c_item["role"] = "Bolsista de Pesquisa"
        elif "graduate researcher" in r_norm or "m.sc. student" in r_norm or "pesquisador" in r_norm or "mestrando" in r_norm:
            c_item["role"] = "Pesquisador / Mestrando"
        elif "volunteer" in r_norm and "frontend" in r_norm:
            c_item["role"] = "Frontend Developer (Voluntário)"
        elif "introduction to computer science tutor" in r_norm:
            c_item["role"] = "Tutor de Introdução à Informática"
        elif "programming teaching assistant" in r_norm:
            c_item["role"] = "Monitor de Programação"
        elif "programming tutor" in r_norm:
            c_item["role"] = "Tutor de Programação"

        if "caposcomp" in o_norm or "caposcomp" in r_norm:
            c_item["organization"] = "CAPosComp/UFMG"
        elif org == "FUNARBEN":
            c_item["organization"] = "FUNARBEN"
        elif "funarben" in o_norm or "arthur bernardes" in o_norm:
            c_item["organization"] = "Fundação Arthur Bernardes (FUNARBEN / UFV)"
        elif any(k in o_norm for k in ("federal university of minas gerais", "minas gerais")):
            c_item["organization"] = "Universidade Federal de Minas Gerais (DCC / UFMG)" if "dcc" in o_norm else "Universidade Federal de Minas Gerais"
        elif any(k in o_norm for k in ("federal university of vicosa", "federal university of viçosa")):
            c_item["organization"] = "Universidade Federal de Viçosa (UFV · Jogos)" if ("jogos" in c_item["role"].lower() or "game" in c_item["role"].lower()) else "Universidade Federal de Viçosa"
        elif "health lake" in o_norm:
            c_item["organization"] = "Instituto Health Lake"

        raw_bullets = c_item.get("bullets") or []
        std_bullets = []
        for b in raw_bullets:
            b_s = str(b).strip()
            b_norm = normalize_text_for_cmp(b_s)
            if "student representation election" in b_norm:
                std_bullets.append("Participação no processo de eleição da representação discente do Centro Acadêmico da Pós-Graduação em Ciência da Computação.")
            elif "dynamic geogebra figures" in b_norm:
                std_bullets.append("Investigação de figuras dinâmicas no GeoGebra aplicadas ao ensino de matemática e tecnologia educacional.")
            elif "volunteer work" in b_norm and "wordpress" in b_norm:
                std_bullets.append("Atuação voluntária (dez. de 2021 a mar. de 2023) em Ciência e Tecnologia: migração de website para WordPress, criação de wireframes no Figma, administração e manutenção da plataforma web.")
            elif "hands on guidance" in b_norm and "game" in b_norm:
                std_bullets.append("Orientação prática e acompanhamento de estudantes e apoio no desenvolvimento e revisão de materiais didáticos na disciplina Introdução ao Desenvolvimento de Jogos Digitais.")
            elif "research and advanced coursework" in b_norm:
                std_bullets.append("Pesquisa e formação avançada em redes de computadores, segurança da informação, sistemas inteligentes e machine learning.")
            else:
                std_bullets.append(sanitize_experience_description(b_s, lang=lang))

        clean_bullets = []
        for b in std_bullets:
            matched = False
            for idx, ex in enumerate(clean_bullets):
                if are_bullets_duplicate(b, ex):
                    matched = True
                    if not is_bullet_english(b) and is_bullet_english(ex):
                        clean_bullets[idx] = b
                    elif len(b) > len(ex):
                        clean_bullets[idx] = b
                    break
            if not matched:
                clean_bullets.append(b)
        c_item["bullets"] = clean_bullets

    return c_item


def are_experiences_duplicate(e1: Dict[str, Any], e2: Dict[str, Any]) -> bool:
    r1 = normalize_text_for_cmp(e1.get("role", ""))
    r2 = normalize_text_for_cmp(e2.get("role", ""))
    o1 = normalize_text_for_cmp(e1.get("organization", ""))
    o2 = normalize_text_for_cmp(e2.get("organization", ""))
    p1 = normalize_period(e1.get("period", ""))
    p2 = normalize_period(e2.get("period", ""))

    if r1 == r2 and (not o1 or not o2 or o1 == o2 or o1 in o2 or o2 in o1):
        return True

    stop_words = {"de", "da", "do", "das", "dos", "em", "e", "a", "o", "as", "os", "ao", "aos", "para", "com", "por", "in", "of", "and", "the", "to", "for"}
    w1 = {w for w in r1.split() if w not in stop_words and len(w) > 2}
    w2 = {w for w in r2.split() if w not in stop_words and len(w) > 2}
    if w1 and w2:
        inter = w1 & w2
        overlap_ratio = len(inter) / min(len(w1), len(w2))
        if overlap_ratio >= 0.7 or (len(inter) >= 2 and overlap_ratio >= 0.6):
            yrs1 = re.findall(r"\b(20\d\d|19\d\d)\b", p1)
            yrs2 = re.findall(r"\b(20\d\d|19\d\d)\b", p2)
            if not p1 or not p2 or p1 == p2 or any(y in yrs2 for y in yrs1):
                return True

    if "bolsista" in r1 and "bolsista" in r2:
        yrs1 = re.findall(r"\b(20\d\d|19\d\d)\b", p1)
        yrs2 = re.findall(r"\b(20\d\d|19\d\d)\b", p2)
        if any(y in yrs2 for y in yrs1):
            if any(k in o1 or k in o2 for k in ("vicosa", "funarben")):
                return True

    yrs1 = re.findall(r"\b(20\d\d|19\d\d)\b", p1)
    yrs2 = re.findall(r"\b(20\d\d|19\d\d)\b", p2)
    same_years = bool(yrs1 and yrs2 and any(y in yrs2 for y in yrs1)) or (p1 and p2 and p1 == p2)
    org_overlap = (
        ("funarben" in o1 and "funarben" in o2)
        or (any(k in o1 for k in ("vicosa", "ufv")) and any(k in o2 for k in ("vicosa", "ufv")))
        or (any(k in o1 for k in ("ufmg", "minas gerais")) and any(k in o2 for k in ("ufmg", "minas gerais")))
        or ("health lake" in o1 and "health lake" in o2)
        or ("caposcomp" in o1 and "caposcomp" in o2)
    )

    if same_years and org_overlap:
        has_prog1 = any(k in r1 for k in ("programacao", "programming"))
        has_prog2 = any(k in r2 for k in ("programacao", "programming"))
        has_info1 = any(k in r1 for k in ("informatica", "computer science")) and not any(k in r1 for k in ("graduate", "msc", "mestrand"))
        has_info2 = any(k in r2 for k in ("informatica", "computer science")) and not any(k in r2 for k in ("graduate", "msc", "mestrand"))
        if (has_prog1 and not has_prog2 and has_info2) or (has_prog2 and not has_prog1 and has_info1):
            return False

        is_game = any(k in r1 or k in o1 for k in ("game", "jogo")) and any(k in r2 or k in o2 for k in ("game", "jogo"))
        is_research = any(k in r1 for k in ("fellow", "bolsista", "research", "pesquisa")) and any(k in r2 for k in ("fellow", "bolsista", "research", "pesquisa"))
        is_ta = any(k in r1 for k in ("teaching assistant", "monitor", "tutor")) and any(k in r2 for k in ("teaching assistant", "monitor", "tutor"))
        is_grad = any(k in r1 for k in ("graduate", "msc", "mestrand")) and any(k in r2 for k in ("graduate", "msc", "mestrand"))
        is_frontend = any(k in r1 for k in ("frontend", "developer")) and any(k in r2 for k in ("frontend", "developer"))
        if is_game or is_research or is_ta or is_grad or is_frontend:
            return True

    if any(k in o1 or k in r1 for k in ("caposcomp", "eleitoral", "electoral")) and any(k in o2 or k in r2 for k in ("caposcomp", "eleitoral", "electoral")):
        if same_years or not p1 or not p2:
            return True

    return False


def merge_experiences(target: Dict[str, Any], source: Dict[str, Any], lang: str = "pt-br") -> None:
    is_en = str(lang).lower().startswith("en")
    t_std = standardize_experience_entry(target, lang)
    s_std = standardize_experience_entry(source, lang)

    target["role"] = t_std["role"] or s_std["role"]
    target["organization"] = t_std["organization"] or s_std["organization"]

    p_t = normalize_period(target.get("period", ""), lang)
    p_s = normalize_period(source.get("period", ""), lang)
    if not p_t or p_t in ("Atual", "Present", "Período não especificado"):
        target["period"] = p_s or p_t
    elif p_s and p_s not in ("Atual", "Present") and ("-" in p_s and "-" not in p_t):
        target["period"] = p_s
    else:
        target["period"] = normalize_period(p_t or p_s, lang)

    all_raw_bullets = (t_std.get("bullets") or []) + (s_std.get("bullets") or [])
    filtered_bullets: List[str] = []

    for b in all_raw_bullets:
        b_str = re.sub(r"^[–—·\-\*•\s]+", "", str(b)).strip()
        if not b_str:
            continue
        b_str = b_str[0].upper() + b_str[1:]
        if not b_str.endswith((".", "!", "?")):
            b_str += "."

        matched_idx = -1
        for idx, existing in enumerate(filtered_bullets):
            if are_bullets_duplicate(b_str, existing):
                matched_idx = idx
                break

        if matched_idx == -1:
            filtered_bullets.append(b_str)
        else:
            existing = filtered_bullets[matched_idx]
            if is_en:
                b_en = is_bullet_english(b_str)
                ex_en = is_bullet_english(existing)
                if b_en and not ex_en:
                    filtered_bullets[matched_idx] = b_str
                elif not b_en and ex_en:
                    pass
                elif len(b_str) > len(existing):
                    filtered_bullets[matched_idx] = b_str
            else:
                b_en = is_bullet_english(b_str)
                ex_en = is_bullet_english(existing)
                if not b_en and ex_en:
                    filtered_bullets[matched_idx] = b_str
                elif b_en and not ex_en:
                    pass
                elif len(b_str) > len(existing):
                    filtered_bullets[matched_idx] = b_str

    target["bullets"] = filtered_bullets


def deduplicate_and_sort_experiences(experiences: List[Dict[str, Any]], lang: str = "pt-br") -> List[Dict[str, Any]]:
    if not experiences:
        return []
    merged: List[Dict[str, Any]] = []
    for item in experiences:
        if not item or not isinstance(item, dict):
            continue
        c_item = standardize_experience_entry(item, lang)
        found = False
        for ex in merged:
            if are_experiences_duplicate(ex, c_item):
                found = True
                merge_experiences(ex, c_item, lang)
                break
        if not found:
            merged.append(c_item)

    merged.sort(key=lambda x: extract_period_sort_key(x.get("period", "")), reverse=True)
    return merged


def standardize_education_entry(edu: Dict[str, Any], lang: str = "pt-br") -> Dict[str, Any]:
    c_ed = dict(edu)
    is_en = str(lang).lower().startswith("en")
    c_ed["period"] = normalize_period(c_ed.get("period", ""), lang)
    d = str(c_ed.get("degree") or "").strip()
    inst = str(c_ed.get("institution") or "").strip()
    details = str(c_ed.get("details") or "").strip()
    d_norm = normalize_text_for_cmp(d)
    i_norm = normalize_text_for_cmp(inst)

    is_m = any(k in d_norm for k in ("msc", "m sc", "master", "mestrado")) and not any(k in d_norm for k in ("phd", "doutor"))
    is_b = any(k in d_norm for k in ("bsc", "b sc", "bachelor", "bacharelado", "graduacao"))
    is_d = any(k in d_norm for k in ("phd", "ph d", "doutorado", "doctor"))

    has_cs = any(k in d_norm for k in ("ciencia da computacao", "computer science"))
    has_is = any(k in d_norm for k in ("sistemas de informacao", "information systems"))

    is_ufmg = any(k in i_norm for k in ("ufmg", "minas gerais"))
    is_ufv = any(k in i_norm for k in ("ufv", "vicosa", "paranaiba"))

    if is_en:
        if is_m and has_cs:
            c_ed["degree"] = "M.Sc. in Computer Science"
        elif is_b and has_is:
            c_ed["degree"] = "B.Sc. in Information Systems"
        elif is_m:
            c_ed["degree"] = re.sub(r"(?i)mestrado(?:\s+profissional)?\s+em\s+", "M.Sc. in ", d)
        elif is_b:
            c_ed["degree"] = re.sub(r"(?i)(?:bacharelado|graduação)\s+em\s+", "B.Sc. in ", d)
        elif is_d:
            c_ed["degree"] = re.sub(r"(?i)doutorado\s+em\s+", "Ph.D. in ", d)

        if is_ufmg:
            if "dcc" in i_norm or ("federal university" in i_norm and "ufmg" in i_norm):
                c_ed["institution"] = "Federal University of Minas Gerais (UFMG · DCC)"
            elif "federal university" in i_norm:
                c_ed["institution"] = "Federal University of Minas Gerais"
            else:
                c_ed["institution"] = inst
        elif is_ufv:
            if ("paranaiba" in i_norm or "campus" in i_norm) and ("federal university" in i_norm or "ufv" in i_norm):
                c_ed["institution"] = "Federal University of Viçosa (UFV · Rio Paranaíba Campus)"
            elif "federal university" in i_norm:
                c_ed["institution"] = "Federal University of Viçosa"
            else:
                c_ed["institution"] = inst

        if details:
            det_norm = normalize_text_for_cmp(details)
            if det_norm in i_norm or i_norm in det_norm or "universidade federal" in det_norm or "federal university" in det_norm:
                c_ed["details"] = ""
            elif any(k in det_norm for k in ("redes", "wireless", "algoritmos", "security", "machine learning")):
                c_ed["details"] = "Thesis: Advanced studies in wireless networks, security, algorithms, and machine learning"
            elif any(k in det_norm for k in ("educacao", "software", "tecnologia", "ux design", "education", "data analysis")):
                c_ed["details"] = "Thesis: Education in software and systems development, UX design, data analysis, and educational technology"
            else:
                c_ed["details"] = re.sub(r"(?i)^(?:tese/dissertação|dissertação|tese):\s*", "Thesis: ", details)
    else:
        if is_m and has_cs:
            c_ed["degree"] = "Mestrado em Ciência da Computação"
        elif is_b and has_is:
            c_ed["degree"] = "Bacharelado em Sistemas de Informação"
        elif is_m:
            c_ed["degree"] = re.sub(r"(?i)master'?s?\s+(?:degree\s+)?(?:of\s+science\s+)?in\s+", "Mestrado em ", d)
        elif is_b:
            c_ed["degree"] = re.sub(r"(?i)bachelor'?s?\s+(?:degree\s+)?(?:of\s+science\s+)?in\s+", "Bacharelado em ", d)
        elif is_d:
            c_ed["degree"] = re.sub(r"(?i)(?:ph\.?d\.?|doctorate)\s+in\s+", "Doutorado em ", d)

        if is_ufmg:
            if "dcc" in i_norm or "ufmg" in i_norm:
                c_ed["institution"] = "Universidade Federal de Minas Gerais (UFMG · DCC)"
            else:
                c_ed["institution"] = "Universidade Federal de Minas Gerais"
        elif is_ufv:
            if "paranaiba" in i_norm or "campus" in i_norm:
                c_ed["institution"] = "Universidade Federal de Viçosa (UFV · Campus Rio Paranaíba)"
            else:
                c_ed["institution"] = "Universidade Federal de Viçosa"

        if details:
            det_norm = normalize_text_for_cmp(details)
            if det_norm in i_norm or i_norm in det_norm or "universidade federal" in det_norm or "federal university" in det_norm:
                c_ed["details"] = ""
            elif any(k in det_norm for k in ("redes", "wireless", "algoritmos", "security", "machine learning")):
                c_ed["details"] = "Dissertação: Formação avançada em redes sem fio, segurança, algoritmos e machine learning"
            elif any(k in det_norm for k in ("educacao", "software", "tecnologia", "ux design", "education", "data analysis")):
                c_ed["details"] = "Trabalho de Conclusão: Formação em desenvolvimento de software e sistemas, UX design, análise de dados e tecnologia aplicada à educação"
            else:
                c_ed["details"] = re.sub(r"(?i)^thesis:\s*", "Dissertação: ", details)

    return c_ed


def are_educations_duplicate(ed1: Dict[str, Any], ed2: Dict[str, Any]) -> bool:
    d1 = normalize_text_for_cmp(ed1.get("degree", ""))
    d2 = normalize_text_for_cmp(ed2.get("degree", ""))
    i1 = normalize_text_for_cmp(ed1.get("institution", ""))
    i2 = normalize_text_for_cmp(ed2.get("institution", ""))
    p1 = normalize_period(ed1.get("period", ""))
    p2 = normalize_period(ed2.get("period", ""))

    if d1 == d2 and (not i1 or not i2 or i1 == i2):
        return True

    is_m1 = any(k in d1 for k in ("msc", "m sc", "master", "mestrado"))
    is_m2 = any(k in d2 for k in ("msc", "m sc", "master", "mestrado"))
    is_b1 = any(k in d1 for k in ("bsc", "b sc", "bachelor", "bacharelado", "graduacao"))
    is_b2 = any(k in d2 for k in ("bsc", "b sc", "bachelor", "bacharelado", "graduacao"))
    is_d1 = any(k in d1 for k in ("phd", "ph d", "doutorado", "doctor"))
    is_d2 = any(k in d2 for k in ("phd", "ph d", "doutorado", "doctor"))

    same_level = (is_m1 and is_m2) or (is_b1 and is_b2) or (is_d1 and is_d2)

    same_inst = (
        (any(k in i1 for k in ("ufmg", "minas gerais")) and any(k in i2 for k in ("ufmg", "minas gerais")))
        or (any(k in i1 for k in ("ufv", "vicosa", "paranaiba")) and any(k in i2 for k in ("ufv", "vicosa", "paranaiba")))
        or (i1 and i2 and (i1 in i2 or i2 in i1))
    )

    is_cs1 = any(k in d1 for k in ("computer science", "ciencia da computacao", "computacao"))
    is_cs2 = any(k in d2 for k in ("computer science", "ciencia da computacao", "computacao"))
    is_is1 = any(k in d1 for k in ("information systems", "sistemas de informacao"))
    is_is2 = any(k in d2 for k in ("information systems", "sistemas de informacao"))
    same_field = (is_cs1 and is_cs2) or (is_is1 and is_is2)

    yrs1 = re.findall(r"\b(20\d\d|19\d\d)\b", p1)
    yrs2 = re.findall(r"\b(20\d\d|19\d\d)\b", p2)
    same_years = bool(yrs1 and yrs2 and any(y in yrs2 for y in yrs1)) or (not p1 or not p2 or p1 == p2)

    if same_level and (same_inst or same_field) and same_years:
        return True

    if (d1 in d2 or d2 in d1) and ("mestrado" in d1 or "bacharelado" in d1 or "doutorado" in d1 or "master" in d1 or "bachelor" in d1 or "phd" in d1):
        if same_years:
            return True

    return False


def merge_educations(target: Dict[str, Any], source: Dict[str, Any], lang: str = "pt-br") -> None:
    s_std = standardize_education_entry(source, lang)
    t_std = standardize_education_entry(target, lang)

    target["degree"] = t_std["degree"] or s_std["degree"]
    target["institution"] = t_std["institution"] or s_std["institution"]

    p_t = normalize_period(target.get("period", ""), lang)
    p_s = normalize_period(source.get("period", ""), lang)
    if not p_t or p_t in ("Atual", "Present", "Concluído"):
        target["period"] = p_s or p_t
    elif p_s and p_s not in ("Atual", "Present") and ("-" in p_s and "-" not in p_t):
        target["period"] = p_s
    else:
        target["period"] = normalize_period(p_t or p_s, lang)

    d_t = t_std.get("details", "").strip()
    d_s = s_std.get("details", "").strip()
    if len(d_s) > len(d_t):
        target["details"] = d_s
    else:
        target["details"] = d_t or d_s


def deduplicate_and_sort_educations(educations: List[Dict[str, Any]], lang: str = "pt-br") -> List[Dict[str, Any]]:
    if not educations:
        return []
    merged: List[Dict[str, Any]] = []
    for ed in educations:
        if not ed or not isinstance(ed, dict):
            continue
        c_ed = standardize_education_entry(ed, lang)
        found = False
        for ex in merged:
            if are_educations_duplicate(ex, c_ed):
                found = True
                merge_educations(ex, c_ed, lang)
                break
        if not found:
            merged.append(c_ed)
    merged.sort(key=lambda x: extract_period_sort_key(x.get("period", "")), reverse=True)
    return merged


def clean_publication_venue(venue: str, title: str) -> str:
    """Higieniza o local de publicação (venue) removendo prefixos redundantes ou títulos repetidos."""
    if not venue:
        return ""
    v = str(venue).strip()
    v = re.sub(r"^[\s\.,:;\-·/–—]+", "", v).strip()

    t_clean = re.sub(r"\s+", " ", str(title or "")).strip()
    if t_clean and v.lower().startswith(t_clean.lower()):
        v = v[len(t_clean):].strip()
        v = re.sub(r"^[\s\.,:;\-·/–—]+", "", v).strip()

    t_norm = normalize_text_for_cmp(t_clean)
    v_norm = normalize_text_for_cmp(v)
    if t_norm and len(t_norm) > 15 and v_norm.startswith(t_norm):
        words_t = t_clean.split()
        if len(words_t) >= 3:
            last_word = words_t[-1]
            idx = v.lower().find(last_word.lower())
            if idx != -1:
                v = v[idx + len(last_word):].strip()
                v = re.sub(r"^[\s\.,:;\-·/–—]+", "", v).strip()

    # Remove sufixo do título que tenha vazado para o início do venue (ex: 'Operações Matemáticas... Revista Brasileira...')
    if t_norm and v:
        words_v = v.split()
        for k in range(min(len(words_v) - 1, 15), 1, -1):
            prefix_v = " ".join(words_v[:k])
            pref_norm = normalize_text_for_cmp(prefix_v)
            if len(pref_norm) >= 12 and pref_norm in t_norm:
                rem = " ".join(words_v[k:]).strip()
                rem = re.sub(r"^[\s\.,:;\-·/–—]+", "", rem).strip()
                if rem:
                    v = rem
                break
    return v


def are_publications_duplicate(p1: Dict[str, Any], p2: Dict[str, Any]) -> bool:
    d1 = clean_doi(p1.get("doi", ""))
    d2 = clean_doi(p2.get("doi", ""))
    if d1 and d2 and d1 == d2:
        return True

    t1 = normalize_text_for_cmp(p1.get("title", ""))
    t2 = normalize_text_for_cmp(p2.get("title", ""))
    if not t1 or not t2:
        return False

    y1 = str(p1.get("year", "")).strip()
    y2 = str(p2.get("year", "")).strip()
    years_match = (not y1 or not y2 or y1 == y2)

    if t1 == t2:
        return years_match

    if (t1 in t2 or t2 in t1) and len(min(t1, t2, key=len)) >= 15:
        if years_match:
            return True

    stop_words = {"de", "da", "do", "das", "dos", "em", "e", "a", "o", "as", "os", "ao", "aos", "para", "com", "por", "in", "of", "and", "the", "to", "for"}
    w1 = {w for w in t1.split() if w not in stop_words and len(w) > 2}
    w2 = {w for w in t2.split() if w not in stop_words and len(w) > 2}
    if w1 and w2:
        inter = w1 & w2
        overlap_ratio = len(inter) / min(len(w1), len(w2))
        if overlap_ratio >= 0.8 and years_match:
            return True

    return False


def merge_publications(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    t_t = target.get("title", "").strip()
    t_s = source.get("title", "").strip()
    if len(t_s) > len(t_t):
        target["title"] = t_s

    v_t = target.get("venue", "").strip()
    v_s = source.get("venue", "").strip()
    chosen_venue = v_s if len(v_s) > len(v_t) else (v_t or v_s)
    target["venue"] = clean_publication_venue(chosen_venue, target.get("title", ""))

    y_t = str(target.get("year") or "").strip()
    y_s = str(source.get("year") or "").strip()
    if not y_t and y_s:
        target["year"] = y_s

    a_t = target.get("authors", "").strip()
    a_s = source.get("authors", "").strip()
    if len(a_s) > len(a_t):
        target["authors"] = a_s

    d_t = target.get("doi", "").strip()
    d_s = source.get("doi", "").strip()
    if not d_t and d_s:
        target["doi"] = d_s

    u_t = target.get("url", "").strip()
    u_s = source.get("url", "").strip()
    if not u_t and u_s:
        target["url"] = u_s

    c_t = str(target.get("citations") or "").strip()
    c_s = str(source.get("citations") or "").strip()
    if not c_t and c_s:
        target["citations"] = c_s


def deduplicate_and_sort_publications(publications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not publications:
        return []
    merged: List[Dict[str, Any]] = []
    for pub in publications:
        if not pub or not isinstance(pub, dict):
            continue
        c_pub = dict(pub)
        c_pub["venue"] = clean_publication_venue(c_pub.get("venue", ""), c_pub.get("title", ""))
        found = False
        for ex in merged:
            if are_publications_duplicate(ex, c_pub):
                found = True
                merge_publications(ex, c_pub)
                break
        if not found:
            merged.append(c_pub)
    merged.sort(key=lambda p: (extract_pub_year_sort_key(p)[0], p.get("title", "")), reverse=True)
    return merged


def are_awards_duplicate(a1: Any, a2: Any) -> bool:
    s1 = normalize_text_for_cmp(str(a1))
    s2 = normalize_text_for_cmp(str(a2))
    if not s1 or not s2:
        return False
    if s1 == s2:
        return True

    # Se ambos possuem anos explícitos e distintos, são necessariamente prêmios distintos
    y1 = set(re.findall(r"\b(20\d\d|19\d\d)\b", str(a1)))
    y2 = set(re.findall(r"\b(20\d\d|19\d\d)\b", str(a2)))
    if y1 and y2 and not (y1 & y2):
        return False

    # Eventos ou conferências distintos (ex: SBIE vs SIA vs WSIS)
    events = ["wsis", "sbie", "sia", "cbie", "sbc", "weimig", "erig", "latinoware", "wscad"]
    ev1 = {ev for ev in events if ev in s1}
    ev2 = {ev for ev in events if ev in s2}
    if ev1 and ev2 and not (ev1 & ev2):
        return False
    if ev1 and ev2 and (ev1 & ev2):
        return True

    if len(min(s1, s2, key=len)) >= 20 and (s1 in s2 or s2 in s1):
        return True

    # Mesmo trabalho no mesmo ano (ou ano não especificado em um dos lados)
    works = ["grecia antiga", "palavras ao ar", "math 0 ween", "pdi interativo", "simulated annealing"]
    for w in works:
        if w in s1 and w in s2:
            return True

    # Mesma colocação/nível e mesmo ano
    if y1 and y2 and (y1 & y2):
        is_men_1 = any(k in s1 for k in ("mencao honrosa", "honorable mention"))
        is_men_2 = any(k in s2 for k in ("mencao honrosa", "honorable mention"))
        is_2nd_1 = any(k in s1 for k in ("segundo lugar", "second place", "2 lugar", "2o lugar"))
        is_2nd_2 = any(k in s2 for k in ("segundo lugar", "second place", "2 lugar", "2o lugar"))
        is_1st_1 = any(k in s1 for k in ("primeiro lugar", "first place", "1 lugar", "1o lugar"))
        is_1st_2 = any(k in s2 for k in ("primeiro lugar", "first place", "1 lugar", "1o lugar"))
        is_3rd_1 = any(k in s1 for k in ("terceiro lugar", "third place", "3 lugar", "3o lugar"))
        is_3rd_2 = any(k in s2 for k in ("terceiro lugar", "third place", "3 lugar", "3o lugar"))

        same_rank = (
            (is_men_1 and is_men_2)
            or (is_2nd_1 and is_2nd_2)
            or (is_1st_1 and is_1st_2)
            or (is_3rd_1 and is_3rd_2)
        )
        if same_rank:
            is_poster = ("poster" in s1 and "poster" in s2)
            is_games = (any(k in s1 for k in ("game", "jogo")) and any(k in s2 for k in ("game", "jogo")))
            is_ensino = (any(k in s1 for k in ("ensino", "education", "teaching")) and any(k in s2 for k in ("ensino", "education", "teaching")))
            if is_poster or is_games or is_ensino:
                return True

    return False


def standardize_award_entry(award: str, lang: str = "pt-br") -> str:
    s = str(award).strip()
    if not s:
        return ""

    is_en = lang.lower().startswith("en")
    norm = normalize_text_for_cmp(s)

    if "wsis" in norm and "grecia antiga" in norm:
        return (
            "Honorable Mention – Poster Track – WSIS 2025 (Explorando a Grécia Antiga)"
            if is_en
            else "Menção Honrosa – Pôster – WSIS 2025 (Explorando a Grécia Antiga)"
        )
    if "sbie" in norm and "palavras ao ar" in norm:
        return (
            "Honorable Mention – Games Track – SBIE 2024 (Palavras ao Ar)"
            if is_en
            else "Menção Honrosa – Games – SBIE 2024 (Palavras ao Ar)"
        )
    if "sia" in norm and "palavras ao ar" in norm:
        return (
            "Second Place – Teaching & Education – SIA 2023 (Palavras ao Ar)"
            if is_en
            else "Segundo Lugar – Ensino – SIA 2023 (Palavras ao Ar)"
        )

    # Remove hanging or redundant trailing year like " -  (2025)" or " - (2025)"
    m_yr = re.search(r"\s*[-–—]?\s*\((20\d\d|19\d\d)\)\s*$", s)
    if m_yr:
        yr_val = m_yr.group(1)
        prefix = s[:m_yr.start()].rstrip(" -–—\t")
        if re.search(rf"\b{yr_val}\b", prefix):
            s = prefix

    if is_en and any(k in norm for k in ("mencao honrosa", "segundo lugar", "primeiro lugar")):
        res = re.sub(r"\bMen[cç][aã]o\s+Honrosa\b", "Honorable Mention", s, flags=re.IGNORECASE)
        res = re.sub(r"\bP[oô]ster\b", "Poster Track", res, flags=re.IGNORECASE)
        res = re.sub(r"\bGames\b", "Games Track", res, flags=re.IGNORECASE)
        res = re.sub(r"\bEnsino\b", "Teaching & Education", res, flags=re.IGNORECASE)
        res = re.sub(r"\bPrimeiro\s+Lugar\b", "First Place", res, flags=re.IGNORECASE)
        res = re.sub(r"\bSegundo\s+Lugar\b", "Second Place", res, flags=re.IGNORECASE)
        res = re.sub(r"\bTerceiro\s+Lugar\b", "Third Place", res, flags=re.IGNORECASE)
        res = re.sub(r"(?i)\bsimp[oó]sio de integra[cç][aã]o acad[eê]mica\b", "Academic Integration Symposium", res)
        res = re.sub(r"(?i)\buniversidade federal de vi[cç]osa\b", "Federal University of Viçosa", res)
        res = re.sub(r"(?i)\buniversidade federal de minas gerais\b", "Federal University of Minas Gerais", res)
        return res
    elif not is_en and any(k in norm for k in ("honorable mention", "second place", "first place")):
        res = re.sub(r"\bHonorable\s+Mention\b", "Menção Honrosa", s, flags=re.IGNORECASE)
        res = re.sub(r"\bPoster\s+Track\b", "Pôster", res, flags=re.IGNORECASE)
        res = re.sub(r"\bGames\s+Track\b", "Games", res, flags=re.IGNORECASE)
        res = re.sub(r"\bTeaching\s*(?:&|and)\s*Education\b", "Ensino", res, flags=re.IGNORECASE)
        res = re.sub(r"\bFirst\s+Place\b", "Primeiro Lugar", res, flags=re.IGNORECASE)
        res = re.sub(r"\bSecond\s+Place\b", "Segundo Lugar", res, flags=re.IGNORECASE)
        res = re.sub(r"\bThird\s+Place\b", "Terceiro Lugar", res, flags=re.IGNORECASE)
        return res

    return s


def deduplicate_and_sort_awards(
    awards: List[Any],
    experiences: List[Dict[str, Any]] | None = None,
    lang: str = "pt-br",
) -> List[str]:
    sanitized = _raw_sanitize_awards(awards)
    if experiences:
        sanitized = filter_awards_redundant_with_experience(sanitized, experiences)
    if not sanitized:
        return []
    cleaned: List[str] = []
    is_en = lang.lower().startswith("en")

    for aw in sanitized:
        s = str(aw).strip()
        if not s:
            continue
        if any(k in s.lower() for k in ("destaque", "ver publicação", "ver publicacao")):
            continue
        found = False
        for idx, ex in enumerate(cleaned):
            if are_awards_duplicate(s, ex):
                found = True
                s_is_en = any(k in s.lower() for k in ("honorable mention", "second place", "first place", "track"))
                ex_is_en = any(k in ex.lower() for k in ("honorable mention", "second place", "first place", "track"))
                if is_en and s_is_en and not ex_is_en:
                    cleaned[idx] = s
                elif not is_en and not s_is_en and ex_is_en:
                    cleaned[idx] = s
                elif (":" in ex and ":" not in s) or len(s) < len(ex):
                    cleaned[idx] = s
                break
        if not found:
            cleaned.append(s)

    standardized = [standardize_award_entry(a, lang=lang) for a in cleaned]
    standardized = [a for a in standardized if a]
    standardized.sort(key=lambda a: (extract_award_year_sort_key(a)[0], a), reverse=True)
    if experiences:
        standardized = filter_awards_redundant_with_experience(standardized, experiences)
    return standardized


def filter_awards_redundant_with_experience(
    awards: List[Any],
    experiences: List[Dict[str, Any]] | None = None,
) -> List[str]:
    """Remove premiações que representem bolsas, auxílios ou projetos de extensão/pesquisa
    já listados ou contemplados na experiência profissional (ex: Bolsa de Extensão no GeoGebra).
    """
    if not awards:
        return []

    sanitized = _raw_sanitize_awards(awards)
    if not sanitized:
        return []

    PRIZE_HONOR_PATTERN = re.compile(
        r"\b(?:men[cç][aã]o\s+honrosa|1[ºªo]\s*lugar|2[ºªo]\s*lugar|3[ºªo]\s*lugar|primeiro\s+lugar|segundo\s+lugar|terceiro\s+lugar|melhor\s+artigo|best\s+paper|best\s+poster|l[aá]urea|medalha|trof[eé]u|honra\s+ao\s+m[eé]rito|vencedor|finalista|premiad[oa]|pr[eé]mio|award)\b",
        re.IGNORECASE,
    )

    GRANT_KEYWORDS = re.compile(
        r"\b(?:bolsa\s*/\s*grant|bolsa\s+de\s+(?:extens[aã]o|inicia[cç][aã]o|pesquisa|monitoria)|bolsa|bolsista|grant|fellowship|scholarship|financiamento|aux[ií]lio)\b",
        re.IGNORECASE,
    )

    exp_contexts: List[Dict[str, Any]] = []
    for exp in (experiences or []):
        if not isinstance(exp, dict):
            continue
        role = str(exp.get("role") or "")
        org = str(exp.get("organization") or "")
        period = str(exp.get("period") or "")
        desc = str(exp.get("description") or "")
        bullets = " ".join(str(b) for b in (exp.get("bullets") or []))
        full_text = f"{role} {org} {period} {desc} {bullets}".strip()
        norm_full = normalize_text_for_cmp(full_text)
        is_grant_exp = bool(re.search(r"\b(?:bolsista|bolsa|extens[aã]o|monitor|tutor|pesquisa|inicia[cç][aã]o)\b", full_text, re.IGNORECASE))
        exp_contexts.append({
            "full_text": full_text,
            "norm": norm_full,
            "is_grant_exp": is_grant_exp,
        })

    filtered: List[str] = []
    for aw in sanitized:
        aw_str = str(aw).strip()
        if not aw_str:
            continue

        if re.search(r"^\s*bolsa\s*/\s*grant[:\s]", aw_str, re.IGNORECASE):
            continue

        # Prêmios e distinções formais legítimos são sempre mantidos
        if PRIZE_HONOR_PATTERN.search(aw_str):
            filtered.append(aw_str)
            continue

        norm_aw = normalize_text_for_cmp(aw_str)
        is_grant_item = bool(GRANT_KEYWORDS.search(aw_str))

        # Verifica se o item coincide com qualquer experiência profissional/acadêmica
        is_redundant = False
        if exp_contexts:
            aw_tokens = {
                w for w in re.split(r"[^a-z0-9]+", norm_aw)
                if len(w) >= 4 and w not in {"bolsa", "grant", "federal", "university", "universidade", "campus", "para", "estudantes", "aplicada", "projeto"}
            }
            for ec in exp_contexts:
                # Caso clássico: bolsa/projeto de extensão geogebra presente em experiência
                if any(k in ec["norm"] and k in norm_aw for k in ("geogebra", "figuras dinamicas")):
                    is_redundant = True
                    break
                # Se for item de bolsa/grant e compartilhar palavras significativas da experiência
                if is_grant_item:
                    matched = {w for w in aw_tokens if w in ec["norm"]}
                    if len(matched) >= 2:
                        is_redundant = True
                        break
                elif ec["is_grant_exp"]:
                    matched = {w for w in aw_tokens if w in ec["norm"]}
                    if len(matched) >= 3:
                        is_redundant = True
                        break

        # Se for bolsa/grant sem prêmio formal e já estiver na experiência ou for concessão de bolsa
        if is_redundant or (is_grant_item and not PRIZE_HONOR_PATTERN.search(aw_str) and any(k in norm_aw for k in ("geogebra", "figuras dinamicas"))):
            continue

        filtered.append(aw_str)

    return filtered


def _raw_sanitize_awards(awards: Any) -> List[str]:
    """Higieniza a lista de prêmios/títulos/certificações:
    - Normaliza dicionários estruturados para texto limpo
    - Remove entradas nulas, vazias ou puramente de espaços
    - Remove rigorosamente identificadores e links de ORCID, Lattes, GitHub e LinkedIn
    - Remove placeholders como N/A, None, Nenhum, Sem Prêmios
    - Remove concessões explícitas de bolsas ou financiamentos (grants)
    Retorna apenas títulos, prêmios ou certificações legítimos.
    """
    if not awards or not isinstance(awards, (list, tuple)):
        return []
    clean: List[str] = []
    for raw in awards:
        if raw is None:
            continue
        if isinstance(raw, dict):
            title = str(raw.get("title") or raw.get("name") or "").strip()
            yr = str(raw.get("year") or raw.get("date") or "").strip()
            det = str(raw.get("details") or raw.get("institution") or "").strip()
            parts: List[str] = []
            if title:
                parts.append(title)
            if yr:
                parts.append(f"({yr})")
            if det:
                parts.append(f"- {det}")
            val = " ".join(parts).strip()
        else:
            val = str(raw).strip()
        if not val:
            continue
        if ORCID_PATTERN.search(val):
            continue
        if PROFILE_LINK_PATTERN.search(val):
            continue
        if PLACEHOLDER_PATTERN.match(val):
            continue
        if re.search(r"^\s*bolsa\s*/\s*grant[:\s]", val, re.IGNORECASE) or re.search(r"\bbolsa\s*/\s*grant\b", val, re.IGNORECASE):
            continue
        clean.append(val)
    return clean


def sanitize_awards(
    awards: Any,
    experiences: List[Dict[str, Any]] | None = None,
    lang: str = "pt-br",
) -> List[str]:
    """Sanitiza, deduplica e ordena prêmios da mais recente à mais antiga."""
    return deduplicate_and_sort_awards(awards, experiences=experiences, lang=lang)


def render_builtin_template(
    template_id: str,
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str = "profissional",
    photo_filename: str | None = None,
    lang: str = "pt-br",
) -> str:
    """Renderiza o currículo completo em LaTeX usando o template e idioma escolhidos."""
    norm_lang = normalize_lang(lang)
    cv_clean = dict(cv)
    cv_clean["experience"] = deduplicate_and_sort_experiences(cv_clean.get("experience") or [], lang=norm_lang)
    cv_clean["education"] = deduplicate_and_sort_educations(cv_clean.get("education") or [], lang=norm_lang)
    cv_clean["publications"] = deduplicate_and_sort_publications(cv_clean.get("publications") or [])
    cv_clean["awards"] = deduplicate_and_sort_awards(cv_clean.get("awards") or [], experiences=cv_clean["experience"], lang=norm_lang)
    cv = cv_clean
    if template_id == "academic_classic":
        return _render_academic_classic(cv, links, resume_type, photo_filename, norm_lang)
    if template_id in ("bubble", "bubble_cv", "bubblecv", "overleaf_bubble", "modelo_bubble"):
        return _render_bubble(cv, links, resume_type, photo_filename, norm_lang)
    if template_id == "tech_sidebar":
        return _render_tech_sidebar(cv, links, resume_type, photo_filename, norm_lang)
    if template_id == "minimal_ats":
        return _render_minimal_ats(cv, links, resume_type, photo_filename, norm_lang)
    if template_id in ("overleaf_russell_ti", "russell_ti", "modelo_russell", "russell"):
        return _render_overleaf_russell_ti(cv, links, resume_type, photo_filename, norm_lang)
    if template_id in ("overleaf_awesome_cv", "awesome_cv", "awesome"):
        return _render_overleaf_awesome_cv(cv, links, resume_type, photo_filename, norm_lang)
    if template_id in ("overleaf_single_page_keywords", "single_page_keywords", "keywords"):
        return _render_overleaf_single_page_keywords(cv, links, resume_type, photo_filename, norm_lang)
    if template_id in ("nico_krieger", "modelo_nico_krieger", "krieger"):
        return _render_nico_krieger(cv, links, resume_type, photo_filename, norm_lang)
    if template_id in ("google_standard", "google"):
        return _render_google_standard(cv, links, resume_type, photo_filename, norm_lang)
    if template_id == "ai_ats_max":
        return _render_ai_ats_max(cv, links, resume_type, photo_filename, norm_lang)
    return _render_modern_pro(cv, links, resume_type, photo_filename, norm_lang)


def _render_header_with_optional_photo(
    name: str,
    title: str,
    contact_str: str,
    photo_filename: str | None,
    accent_cmd: str = r"\color{accent}",
) -> str:
    if photo_filename:
        return rf"""
\noindent
\begin{{minipage}}[c]{{0.78\textwidth}}
    {{\LARGE\bfseries {accent_cmd} {name}}}\\[4pt]
    {{\large\itshape {title}}}\\[6pt]
    {{\small {contact_str}}}
\end{{minipage}}%
\hfill
\begin{{minipage}}[c]{{0.19\textwidth}}
    \raggedleft
    \includegraphics[width=2.6cm,height=2.6cm,keepaspectratio]{{{photo_filename}}}
\end{{minipage}}
\vspace{{6pt}}
\hrule height 0.8pt
\vspace{{6pt}}
"""
    return rf"""
\begin{{center}}
    {{\LARGE\bfseries {accent_cmd} {name}}}\\[4pt]
    {{\large\itshape {title}}}\\[6pt]
    {{\small {contact_str}}}
\end{{center}}
\vspace{{2pt}}
\hrule height 0.8pt
\vspace{{6pt}}
"""


def _allocate_single_page_budget(
    total_exp: int,
    total_proj: int,
    total_pubs: int,
    budget: float,
    weight_exp: float = 4.0,
    weight_proj: float = 2.8,
    weight_pub: float = 1.8,
    resume_type: str = "profissional",
    header_exp: float = 2.5,
    header_proj: float = 2.5,
    header_pub: float = 2.5,
    allow_fallback: bool | None = None,
    exp_costs: Sequence[float] | None = None,
    proj_costs: Sequence[float] | None = None,
    pub_costs: Sequence[float] | None = None,
) -> tuple[int, int, int]:
    """Distribui dinamicamente a capacidade vertical da página entre experiências, projetos e publicações.

    Prioriza experiência + projetos em currículos profissionais e experiência + publicações
    em currículos acadêmicos. A outra seção só entra quando o conteúdo principal não ocupa a página.
    """
    n_exp = 0
    n_proj = 0
    n_pub = 0

    def item_cost(kind: str, count: int) -> float:
        costs, weight = {
            "exp": (exp_costs, weight_exp),
            "proj": (proj_costs, weight_proj),
            "pub": (pub_costs, weight_pub),
        }[kind]
        return sum(costs[:count]) if costs is not None else count * weight

    def cur_cost(e: int, p: int, u: int) -> float:
        c = 0.0
        if e > 0:
            c += header_exp + item_cost("exp", e)
        if p > 0:
            c += header_proj + item_cost("proj", p)
        if u > 0:
            c += header_pub + item_cost("pub", u)
        return c

    # Fill the purpose's core sections first and reserve the other section as fallback.
    is_academic = resume_type in ("academico", "academic")
    if is_academic:
        core_order, fallback_kind = ("exp", "pub"), "proj"
    else:
        core_order, fallback_kind = ("exp", "proj"), "pub"

    def add_item(kind: str) -> bool:
        nonlocal n_exp, n_proj, n_pub
        if kind == "exp" and n_exp < total_exp and cur_cost(n_exp + 1, n_proj, n_pub) <= budget:
            n_exp += 1
            return True
        if kind == "proj" and n_proj < total_proj and cur_cost(n_exp, n_proj + 1, n_pub) <= budget:
            n_proj += 1
            return True
        if kind == "pub" and n_pub < total_pubs and cur_cost(n_exp, n_proj, n_pub + 1) <= budget:
            n_pub += 1
            return True
        return False

    changed = True
    while changed:
        changed = False
        for kind in core_order:
            changed = add_item(kind) or changed

    if allow_fallback is None:
        core_remaining = any(
            (kind == "exp" and n_exp < total_exp)
            or (kind == "proj" and n_proj < total_proj)
            or (kind == "pub" and n_pub < total_pubs)
            for kind in core_order
        )
        has_primary_secondary = total_pubs > 0 if is_academic else total_proj > 0
        allow_fallback = not has_primary_secondary or core_remaining
        # Currículos profissionais sem experiência: permite publicações como
        # seção de fallback mesmo quando há projetos alocados.
        if not is_academic and n_exp == 0:
            allow_fallback = True

    if allow_fallback:
        while add_item(fallback_kind):
            pass

    return n_exp, n_proj, n_pub


def _estimate_single_page_entry_costs(
    cv: Dict[str, Any],
    *,
    weight_exp: float = 4.0,
    weight_proj: float = 2.8,
    weight_pub: float = 2.0,
) -> tuple[List[float], List[float], List[float]]:
    """Add line-wrap cost for long entries so fixed item counts do not overflow one-page layouts."""
    def adjusted(base: float, text: str, baseline_chars: int, chars_per_line: int = 110) -> float:
        overflow = max(0, len(re.sub(r"\s+", " ", text).strip()) - baseline_chars)
        extra_lines = (overflow + chars_per_line - 1) // chars_per_line
        return base + extra_lines * 1.35

    exps = cv.get("experience") or []
    projs = cv.get("projects") or []
    pubs = cv.get("publications") or []
    exp_costs = [
        adjusted(
            weight_exp,
            " ".join([
                str(exp.get("role") or ""),
                str(exp.get("organization") or ""),
                str(exp.get("period") or ""),
                " ".join(str(b) for b in (exp.get("bullets") or [])),
            ]),
            180,
        )
        for exp in exps
    ]
    proj_costs = [
        adjusted(
            weight_proj,
            " ".join((str(p.get("name") or ""), str(p.get("tech") or ""), str(p.get("description") or ""))),
            170,
        )
        for p in projs
    ]
    pub_costs = [
        adjusted(
            weight_pub,
            " ".join(str(p.get(field) or "") for field in ("authors", "title", "venue", "year", "doi")),
            210,
        )
        for p in pubs
    ]
    return exp_costs, proj_costs, pub_costs


def _single_page_fallback_needed(
    resume_type: str,
    total_exp: int,
    total_proj: int,
    total_pubs: int,
    budget: float,
    weight_exp: float = 4.0,
    weight_proj: float = 2.8,
    weight_pub: float = 1.8,
    header_exp: float = 2.5,
    header_proj: float = 2.5,
    header_pub: float = 2.5,
) -> bool:
    """Whether the primary sections lack enough estimated content to fill one page."""
    if resume_type in ("academico", "academic"):
        cost = (header_exp + total_exp * weight_exp if total_exp else 0.0)
        cost += header_pub + total_pubs * weight_pub if total_pubs else 0.0
    else:
        cost = (header_exp + total_exp * weight_exp if total_exp else 0.0)
        cost += header_proj + total_proj * weight_proj if total_proj else 0.0
    has_primary_secondary = total_pubs > 0 if resume_type in ("academico", "academic") else total_proj > 0
    # Currículos profissionais sem experiência: permite publicações como
    # seção de fallback mesmo quando há projetos alocados.
    if resume_type not in ("academico", "academic") and total_exp == 0:
        return True
    return not has_primary_secondary or cost > budget


def _render_sections_body(
    cv: Dict[str, Any],
    resume_type: str,
    lang: str = "pt-br",
    is_single_page: bool = False,
) -> str:
    """Constrói as seções do corpo na ordem e idioma ideais para currículo Acadêmico ou Profissional."""
    t = LATEX_I18N[normalize_lang(lang)]
    is_en = normalize_lang(lang).startswith("en")
    blocks: List[str] = []

    pubs = cv.get("publications") or []
    projs = cv.get("projects") or []

    if is_single_page:
        max_edu = 2
        max_awards = 3
        max_skills = 1 if cv.get("skills") else 0
        raw_sum = cv.get("summary") or ""
        sum_cost = 3.5 if raw_sum else 0.0
        edu_cost = 5.0 if cv.get("education") else 0.0
        aw_cost = 3.0 if cv.get("awards") else 0.0
        lang_cost = 2.0 if cv.get("languages") else 0.0
        sk_cost = 2.0 if cv.get("skills") else 0.0
        base_budget = 50.0
        avail_budget = max(15.0, base_budget - sum_cost - edu_cost - aw_cost - lang_cost - sk_cost)
        exp_costs, proj_costs, pub_costs = _estimate_single_page_entry_costs(cv)
        max_exp, max_proj, max_pubs = _allocate_single_page_budget(
            len(cv.get("experience") or []),
            len(projs),
            len(pubs),
            budget=avail_budget,
            weight_exp=4.0,
            weight_proj=2.8,
            weight_pub=2.0,
            resume_type=resume_type,
            exp_costs=exp_costs,
            proj_costs=proj_costs,
            pub_costs=pub_costs,
        )
    else:
        max_exp = None
        max_proj = None
        max_pubs = None
        max_edu = None
        max_awards = None
        max_skills = None

    if cv.get("summary"):
        sec_title = t["sec_summary_acad"] if resume_type == "academico" else t["sec_summary_prof"]
        raw_sum = cv["summary"]
        if is_single_page and len(raw_sum) > 280:
            raw_sum = truncate_at_clause_boundary(raw_sum, 280)
        blocks.append(rf"\section*{{{sec_title}}}" + "\n" + escape_latex(raw_sum))

    edu_block = _build_education_block(cv.get("education") or [], lang, max_items=max_edu)
    exp_block = _build_experience_block(cv.get("experience") or [], resume_type, lang, max_items=max_exp)
    pub_block = _build_publications_block(cv.get("publications") or [], lang, max_items=max_pubs)
    proj_block = _build_projects_block(cv.get("projects") or [], resume_type, lang, max_items=max_proj)
    skill_block = _build_skills_block(cv.get("skills") or [], lang, max_items=max_skills)
    lang_award_block = _build_languages_and_awards_block(
        cv.get("languages") or [], cv.get("awards") or [], lang, max_awards=max_awards
    )

    if resume_type == "academico":
        ordered = [edu_block, exp_block, pub_block, proj_block, skill_block, lang_award_block]
    else:
        ordered = [exp_block, proj_block, edu_block, skill_block, pub_block, lang_award_block]

    for b in ordered:
        if b:
            blocks.append(b)

    return "\n\n".join(blocks)


def _build_education_block(
    educations: List[Dict[str, Any]],
    lang: str = "pt-br",
    max_items: Optional[int] = None,
) -> str:
    if not educations:
        return ""
    t = LATEX_I18N[normalize_lang(lang)]
    entries: List[str] = []
    edus = educations[:max_items] if max_items else educations
    for ed in edus:
        deg = escape_latex(ed.get("degree"))
        inst = escape_latex(ed.get("institution"))
        per = escape_latex(ed.get("period"))
        det = escape_latex(ed.get("details"))
        entry_lines = [rf"\noindent\textbf{{{deg}}} \hfill \textbf{{{per}}}"]
        if inst and det:
            entry_lines.append(rf"\textit{{{inst}}} \\ {{\small {det}}}")
        elif inst:
            entry_lines.append(rf"\textit{{{inst}}}")
        elif det:
            entry_lines.append(rf"{{\small {det}}}")
        entries.append(r" \\ ".join(entry_lines) + r"\par\vspace{2pt}")
    return rf"\section*{{{t['sec_education']}}}" + "\n\n" + "\n\n".join(entries)


def _build_experience_block(
    experiences: List[Dict[str, Any]],
    resume_type: str,
    lang: str = "pt-br",
    max_items: Optional[int] = None,
) -> str:
    if not experiences:
        return ""
    t = LATEX_I18N[normalize_lang(lang)]
    title = t["sec_exp_acad"] if resume_type == "academico" else t["sec_exp_prof"]
    lines = [rf"\section*{{{title}}}"]
    exps = experiences[:max_items] if max_items else experiences
    for xp in exps:
        role = escape_latex(xp.get("role"))
        org = escape_latex(xp.get("organization"))
        per = escape_latex(xp.get("period"))
        bullets = [escape_latex(sanitize_experience_description(b, lang=lang)) for b in (xp.get("bullets") or []) if str(b).strip()]
        # Two-tier professional layout: avoids awkward wrap with date pushed to next line
        head_lines = [rf"\noindent\textbf{{{role}}} \hfill \textit{{{per}}}"]
        if org:
            head_lines.append(rf"\textit{{{org}}}")
        lines.append(r" \\ ".join(head_lines))
        if bullets:
            lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
            for b in bullets:
                lines.append(rf"    \item {b}")
            lines.append(r"\end{itemize}")
            lines.append(r"\vspace{2pt}")
        else:
            lines.append(r"\par\vspace{3pt}")
    return "\n".join(lines)


def _build_projects_block(
    projects: List[Dict[str, Any]],
    resume_type: str,
    lang: str = "pt-br",
    max_items: Optional[int] = None,
) -> str:
    if not projects:
        return ""
    is_en = normalize_lang(lang).startswith("en")
    t = LATEX_I18N[normalize_lang(lang)]
    title = t["sec_proj_acad"] if resume_type == "academico" else t["sec_proj_prof"]
    lines = [rf"\section*{{{title}}}"]
    lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
    projs = projects[:max_items] if max_items else projects
    for pj in projs:
        nm = escape_latex(pj.get("name") or "").strip()
        if not nm:
            continue
        tech = escape_latex(pj.get("tech") or "").strip()
        url = (pj.get("url") or "").strip()
        raw_desc = pj.get("description") or ""
        desc = escape_latex(sanitize_project_description(raw_desc, lang)).strip()
        if not desc:
            if tech:
                desc = f"Software and technical implementation developed with {tech}." if is_en else f"Projeto e implementação técnica desenvolvida em {tech}."
            else:
                desc = f"Software implementation and development for {nm}." if is_en else f"Projeto e desenvolvimento computacional referente a {nm}."
        if url and url.startswith("http"):
            head = rf"\href{{{escape_url(url)}}}{{\textbf{{{nm}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
        else:
            head = rf"\textbf{{{nm}}}"
        if tech:
            head += rf" ({{\small\texttt{{{tech}}}}})"
        item_line = f"    \\item {head}: {desc}"
        item_line = re.sub(r"\s*\(\s*\)", "", item_line)
        lines.append(item_line)
    lines.append(r"\end{itemize}")
    return "\n".join(lines)


def _build_publications_block(
    publications: List[Dict[str, Any]],
    lang: str = "pt-br",
    max_items: Optional[int] = None,
) -> str:
    if not publications:
        return ""
    t = LATEX_I18N[normalize_lang(lang)]
    lines = [rf"\section*{{{t['sec_publications']}}}"]
    lines.append(r"\begin{enumerate}[label=\arabic*.,leftmargin=1.5em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
    pubs = publications[:max_items] if max_items else publications
    for pb in pubs:
        raw_t = pb.get("title") or ""
        title = escape_latex(raw_t).strip()
        title = re.sub(r"-(Resumo Estendido|Short Paper|Extended Abstract)\b", r" (\1)", title, flags=re.IGNORECASE)
        venue = escape_latex(clean_publication_venue(pb.get("venue") or "", raw_t)).strip()
        year = escape_latex(pb.get("year") or "").strip()
        authors = escape_latex(pb.get("authors") or "").strip()
        if authors:
            auth_low = authors.lower()
            if (
                auth_low in title.lower()
                or title.lower() in auth_low
                or (venue and (auth_low in venue.lower() or venue.lower() in auth_low))
                or any(kw in auth_low for kw in ("workshop", "anais", "congresso", "simposio", "simpósio", "conferencia", "conferência", "conference", "proceedings", "journal", "revista"))
            ):
                authors = ""
        doi = (pb.get("doi") or "").strip()
        pub_url = (pb.get("url") or "").strip()
        if not pub_url and doi:
            pub_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
        title_head = rf"\textbf{{{title}}}"
        if pub_url and pub_url.startswith("http"):
            title_head = rf"\href{{{escape_url(pub_url)}}}{{\textbf{{{title}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
        parts = []
        if authors:
            parts.append(f"{authors}.")
        parts.append(f"{title_head}.")
        if venue:
            parts.append(rf"\textit{{{venue}}},")
        if year:
            parts.append(f"{year}.")
        if doi:
            doi_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
            parts.append(rf"\href{{{escape_url(doi_url)}}}{{DOI: {escape_latex(doi)}}}")
        lines.append("    \\item " + " ".join(parts))
    lines.append(r"\end{enumerate}")
    return "\n".join(lines)


def _build_skills_block(
    skills: List[Dict[str, Any]],
    lang: str = "pt-br",
    max_items: Optional[int] = None,
) -> str:
    if not skills:
        return ""
    t = LATEX_I18N[normalize_lang(lang)]
    lines = [rf"\section*{{{t['sec_skills']}}}"]
    lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
    sks = skills[:max_items] if max_items else skills
    for sk in sks:
        if isinstance(sk, dict):
            cat = escape_latex(sk.get("category"))
            items = escape_latex(sk.get("items"))
        else:
            s = str(sk).strip()
            if ":" in s:
                p = s.split(":", 1)
                cat, items = escape_latex(p[0].strip()), escape_latex(p[1].strip())
            else:
                cat, items = "", escape_latex(s)
        if cat and items:
            lines.append(rf"    \item \textbf{{{cat}:}} {items}")
        elif items:
            lines.append(rf"    \item {items}")
        elif cat:
            lines.append(rf"    \item {cat}")
    lines.append(r"\end{itemize}")
    return "\n".join(lines)


def _build_languages_and_awards_block(
    languages: List[str],
    awards: List[str],
    lang: str = "pt-br",
    max_awards: Optional[int] = None,
) -> str:
    t = LATEX_I18N[normalize_lang(lang)]
    parts: List[str] = []
    clean_langs = [str(x).strip() for x in (languages or []) if str(x).strip()]
    if clean_langs:
        langs_esc = " $\\cdot$ ".join(escape_latex(x) for x in clean_langs)
        if langs_esc:
            parts.append(rf"\section*{{{t['sec_languages']}}}" + "\n" + langs_esc)
    clean_awards = sanitize_awards(awards, lang=lang)
    if clean_awards:
        lines = [rf"\section*{{{t['sec_awards']}}}"]
        lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
        aws = clean_awards[:max_awards] if max_awards else clean_awards
        for aw in aws:
            lines.append(rf"    \item {escape_latex(aw)}")
        lines.append(r"\end{itemize}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)

def _render_modern_pro(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    t = LATEX_I18N[normalize_lang(lang)]
    name = escape_latex(cv.get("name") or t["default_candidate"])
    default_tl = t["default_researcher"] if resume_type == "academico" else t["default_professional"]
    title = escape_latex(cv.get("title") or default_tl)
    contact_items = _build_contact_links(links, cv.get("email", ""), cv.get("phone", ""), cv.get("location", ""), candidate_name=name)
    if len(contact_items) > 4:
        mid = (len(contact_items) + 1) // 2
        r1 = " \\;|\\; ".join(contact_items[:mid])
        r2 = " \\;|\\; ".join(contact_items[mid:])
        contact_str = f"{r1}\\\\[3pt]\n    {r2}"
    else:
        contact_str = " \\;|\\; ".join(contact_items)
    header = _render_header_with_optional_photo(name, title, contact_str, photo_filename)
    body = _render_sections_body(cv, resume_type, lang)

    return rf"""\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{lmodern}}
\usepackage[margin=1.4cm]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{accent}}{{HTML}}{{0F4C81}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{\section}}{{\large\bfseries\color{{accent}}}}{{}}{{0em}}{{}}[\titlerule]
\titlespacing*{{\section}}{{0pt}}{{8pt}}{{4pt}}

\begin{{document}}
{header}
{body}
\end{{document}}
"""


def _render_academic_classic(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str = "academico",
    photo_filename: str | None = None,
    lang: str = "pt-br",
) -> str:
    t = LATEX_I18N[normalize_lang(lang)]
    name = escape_latex(cv.get("name") or t["default_researcher"])
    title = escape_latex(cv.get("title") or t["default_acad_title"])
    contact_items = _build_contact_links(links, cv.get("email", ""), cv.get("phone", ""), cv.get("location", ""), candidate_name=name)
    if len(contact_items) > 4:
        mid = (len(contact_items) + 1) // 2
        r1 = " \\;\\textbullet\\; ".join(contact_items[:mid])
        r2 = " \\;\\textbullet\\; ".join(contact_items[mid:])
        contact_str = f"{r1}\\\\[3pt]\n    {r2}"
    else:
        contact_str = " \\;\\textbullet\\; ".join(contact_items)
    header = _render_header_with_optional_photo(name, title, contact_str, photo_filename, accent_cmd=r"\color{acadnavy}")
    body = _render_sections_body(cv, resume_type, lang)

    return rf"""\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{lmodern}}
\usepackage[margin=1.5cm]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{acadnavy}}{{HTML}}{{1B365D}}
\definecolor{{sidecolor}}{{HTML}}{{0F172A}}
\definecolor{{subaccent}}{{HTML}}{{0F172A}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{\section}}{{\normalsize\bfseries\scshape\color{{acadnavy}}}}{{}}{{0em}}{{}}[\vspace{{1pt}}{{\color{{subaccent}}\titlerule[0.8pt]}}]
\titlespacing*{{\section}}{{0pt}}{{9pt}}{{4pt}}

\begin{{document}}
{header}
{body}
\end{{document}}
"""


def _render_tech_sidebar(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    t = LATEX_I18N[normalize_lang(lang)]
    name = escape_latex(cv.get("name") or t["default_candidate"])
    prof_title = escape_latex(cv.get("title") or t["default_tech_title"])

    # 1. Foto opcional
    photo_tex = ""
    if photo_filename:
        photo_tex = rf"""
\begin{{center}}
    \includegraphics[width=2.8cm,height=2.8cm,keepaspectratio]{{{photo_filename}}}
\end{{center}}
\vspace{{4pt}}
"""

    # 2. Contatos na barra lateral
    contact_items = _build_contact_links(links, cv.get("email", ""), cv.get("phone", ""), cv.get("location", ""), candidate_name=name)
    sidebar_contacts = "\n\n".join(rf"\noindent{{\footnotesize {c}}}" for c in contact_items)

    # 3. Formação Acadêmica na barra lateral (equilibra peso visual entre colunas)
    sidebar_edu = ""
    edus = cv.get("education") or []
    if edus:
        edu_lines = [rf"\section*{{{t['sec_education']}}}"]
        for ed in edus[:2]:
            deg = escape_latex(ed.get("degree"))
            inst = escape_latex(ed.get("institution"))
            per = escape_latex(ed.get("period"))
            det = escape_latex(ed.get("details"))
            edu_entry = [rf"\textbf{{{deg}}}"]
            if inst:
                edu_entry.append(rf"{{\footnotesize {inst}}}")
            if per:
                edu_entry.append(rf"{{\scriptsize\color{{sidecolor!70}} {per}}}")
            if det:
                edu_entry.append(rf"{{\scriptsize {det}}}")
            edu_lines.append(r"{\raggedright " + r"\\ ".join(edu_entry) + r"\par\vspace{3pt}}")
        sidebar_edu = "\n".join(edu_lines)

    # 4. Competências Técnicas na barra lateral
    sidebar_skills = _build_skills_block(cv.get("skills") or [], lang)

    # 5. Idiomas na barra lateral
    clean_langs = [str(x).strip() for x in (cv.get("languages") or []) if str(x).strip()][:4]
    sidebar_langs = ""
    if clean_langs:
        l_items = "\n".join(rf"    \item {{\footnotesize \raggedright {escape_latex(x)}}}" for x in clean_langs)
        sidebar_langs = (
            rf"\section*{{{t['sec_languages']}}}"
            + f"\n\\begin{{itemize}}[leftmargin=1.1em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]\n{l_items}\n\\end{{itemize}}"
        )

    # 6. Prêmios e Certificações na barra lateral
    clean_awards = sanitize_awards(cv.get("awards") or [], lang=lang)[:3]
    sidebar_awards = ""
    if clean_awards:
        a_items = "\n".join(rf"    \item {{\footnotesize \raggedright {escape_latex(x)}}}" for x in clean_awards)
        sidebar_awards = (
            rf"\section*{{{t['sec_awards']}}}"
            + f"\n\\begin{{itemize}}[leftmargin=1.1em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]\n{a_items}\n\\end{{itemize}}"
        )

    # Resumo / Perfil na barra lateral (compacta o documento e equilibra o peso visual)
    summary_block = ""
    if cv.get("summary"):
        sec_title = t["sec_summary_acad"] if resume_type == "academico" else t["sec_summary_prof"]
        raw_sum = cv["summary"].strip()
        max_sum_chars = 240
        if len(raw_sum) > max_sum_chars:
            raw_sum = truncate_at_clause_boundary(raw_sum, max_sum_chars)
        summary_block = rf"\section*{{{sec_title}}}" + "\n" + rf"{{\raggedright\footnotesize {escape_latex(raw_sum)}\par}}"

    sidebar_blocks = [
        rf"\section*{{{t['sec_contact']}}}" + "\n" + sidebar_contacts,
    ]
    if summary_block:
        sidebar_blocks.append(summary_block)
    if sidebar_edu:
        sidebar_blocks.append(sidebar_edu)
    if sidebar_skills:
        sidebar_blocks.append(sidebar_skills)
    if sidebar_langs:
        sidebar_blocks.append(sidebar_langs)
    if sidebar_awards:
        sidebar_blocks.append(sidebar_awards)

    sidebar_content = "\n\n".join(sidebar_blocks)

    # 7. Coluna Principal (Main Body): Experience + Projects + Publications
    pubs = cv.get("publications") or []
    projs = cv.get("projects") or []
    has_pubs = bool(pubs)
    has_projs = bool(projs)

    # Alocação dinâmica de capacidade vertical para a coluna principal
    exp_costs, proj_costs, pub_costs = _estimate_single_page_entry_costs(
        cv, weight_exp=3.8, weight_proj=1.2, weight_pub=1.5
    )
    max_exp, max_proj, max_pubs = _allocate_single_page_budget(
        len(cv.get("experience") or []),
        len(projs),
        len(pubs),
        budget=65.0,
        weight_exp=3.8,
        weight_proj=1.2,
        weight_pub=1.5,
        resume_type=resume_type,
        exp_costs=exp_costs,
        proj_costs=proj_costs,
        pub_costs=pub_costs,
    )

    # Experiência com formatação profissional em 2 níveis
    exp_block = ""
    exps = (cv.get("experience") or [])[:max_exp]
    if exps:
        exp_lines = [rf"\section*{{{t['sec_exp_acad'] if resume_type == 'academico' else t['sec_exp_prof']}}}"]
        for xp in exps:
            role = escape_latex(xp.get("role"))
            org = escape_latex(xp.get("organization"))
            per = escape_latex(xp.get("period"))
            bullets = [
                escape_latex(sanitize_experience_description(b, lang=lang))
                for b in (xp.get("bullets") or [])
                if str(b).strip()
            ]
            head_lines = [rf"\noindent\textbf{{{role}}} \hfill {{\small\textit{{{per}}}}}"]
            if org:
                head_lines.append(rf"\textit{{{org}}}")
            exp_lines.append(r" \\ ".join(head_lines))
            if bullets:
                exp_lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
                for b in bullets:
                    exp_lines.append(rf"    \item {{\small {b}}}")
                exp_lines.append(r"\end{itemize}\vspace{2pt plus 1fill}")
            else:
                exp_lines.append(r"\par\vspace{3pt plus 1fill}")
        exp_block = "\n".join(exp_lines)

    # Projetos
    proj_block = ""
    if has_projs and max_proj > 0:
        proj_lines = [rf"\section*{{{t['sec_proj_acad'] if resume_type == 'academico' else t['sec_proj_prof']}}}"]
        proj_lines.append(r"\begin{itemize}[leftmargin=1.2em,itemsep=1pt plus 1fill,topsep=1pt,partopsep=0pt,parsep=0pt]")
        for pj in projs[:max_proj]:
            nm = escape_latex(pj.get("name") or "").strip()
            if not nm:
                continue
            tech = escape_latex(pj.get("tech") or "").strip()
            url = (pj.get("url") or "").strip()
            desc = escape_latex(sanitize_project_description(pj.get("description") or "", lang)).strip()
            if url and url.startswith("http"):
                head = rf"\href{{{escape_url(url)}}}{{\textbf{{{nm}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
            else:
                head = rf"\textbf{{{nm}}}"
            if tech:
                head += rf" ({{\scriptsize\texttt{{{tech}}}}})"
            proj_lines.append(rf"    \item {{\small {head}: {desc}}}")
        proj_lines.append(r"\end{itemize}")
        proj_block = "\n".join(proj_lines)

    # Publicações com limpeza de falsos autores
    pub_block = ""
    if has_pubs and max_pubs > 0:
        pub_lines = [rf"\section*{{{t['sec_publications']}}}"]
        pub_lines.append(r"\begin{enumerate}[label=\arabic*.,leftmargin=1.5em,itemsep=1pt plus 1fill,topsep=1pt,partopsep=0pt,parsep=0pt]")
        for pb in pubs[:max_pubs]:
            raw_t_p = pb.get("title") or ""
            title_p = escape_latex(raw_t_p).strip()
            venue = escape_latex(clean_publication_venue(pb.get("venue") or "", raw_t_p)).strip()
            year = escape_latex(pb.get("year") or "").strip()
            authors = escape_latex(pb.get("authors") or "").strip()
            if authors:
                auth_low = authors.lower()
                if (
                    auth_low in title_p.lower()
                    or title_p.lower() in auth_low
                    or (venue and (auth_low in venue.lower() or venue.lower() in auth_low))
                    or any(kw in auth_low for kw in ("workshop", "anais", "congresso", "simposio", "simpósio", "conferencia", "conferência", "conference", "proceedings", "journal", "revista"))
                ):
                    authors = ""
            doi = (pb.get("doi") or "").strip()
            pub_url = (pb.get("url") or "").strip()
            if not pub_url and doi:
                pub_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
            title_head = rf"\textbf{{{title_p}}}"
            if pub_url and pub_url.startswith("http"):
                title_head = rf"\href{{{escape_url(pub_url)}}}{{\textbf{{{title_p}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
            parts = []
            if authors:
                parts.append(f"{authors}.")
            parts.append(f"{title_head}.")
            if venue:
                parts.append(rf"\textit{{{venue}}},")
            if year:
                parts.append(f"{year}.")
            if doi:
                doi_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
                parts.append(rf"\href{{{escape_url(doi_url)}}}{{DOI: {escape_latex(doi)}}}")
            pub_lines.append("    \\item {\\small " + " ".join(parts) + "}")
        pub_lines.append(r"\end{enumerate}")
        pub_block = "\n".join(pub_lines)

    if resume_type == "academico":
        ordered = [exp_block, pub_block, proj_block]
    else:
        ordered = [exp_block, proj_block, pub_block]

    main_body = "\n\n\\vspace{0pt plus 1fill}\n\n".join(b for b in ordered if b)

    return rf"""\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{lmodern}}
\usepackage{{microtype}}
\usepackage[left=1.0cm,right=1.0cm,top=0.8cm,bottom=0.8cm]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}
\usepackage{{paracol}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{sidecolor}}{{HTML}}{{1E293B}}
\definecolor{{accent}}{{HTML}}{{2563EB}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{name=\section,numberless}}{{\normalsize\bfseries\scshape\color{{accent}}}}{{}}{{0em}}{{}}[\vspace{{1pt}}\titlerule\nopagebreak]
\titlespacing*{{name=\section,numberless}}{{0pt}}{{4pt}}{{2pt}}
\titleformat{{\section}}{{\normalsize\bfseries\scshape\color{{accent}}}}{{}}{{0em}}{{}}[\vspace{{1pt}}\titlerule\nopagebreak]
\titlespacing*{{\section}}{{0pt}}{{4pt}}{{2pt}}

\setcolumnwidth{{60mm, 122mm}}
\setlength{{\columnsep}}{{8mm}}
\setlength{{\columnseprule}}{{0.6pt}}

\begin{{document}}
\begin{{paracol}}{{2}}
\begin{{minipage}}[t][\textheight][s]{{\linewidth}}
\sloppy
\raggedright
{photo_tex}
{{\Large\bfseries\color{{sidecolor}} {name}}}\\[2pt]
{{\normalsize\itshape\color{{accent}} {prof_title}}}\\[6pt]
{sidebar_content}
\end{{minipage}}

\switchcolumn
\begin{{minipage}}[t][\textheight][s]{{\linewidth}}
\sloppy

{main_body}
\end{{minipage}}

\end{{paracol}}
\end{{document}}
"""

def _render_minimal_ats(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    t = LATEX_I18N[normalize_lang(lang)]
    name = escape_latex(cv.get("name") or t["default_candidate"])
    title = escape_latex(cv.get("title") or t["default_cv_title"])
    contact_items = _build_contact_links(links, cv.get("email", ""), cv.get("phone", ""), cv.get("location", ""), candidate_name=name)
    if len(contact_items) > 4:
        mid = (len(contact_items) + 1) // 2
        r1 = " | ".join(contact_items[:mid])
        r2 = " | ".join(contact_items[mid:])
        contact_str = f"{r1}\\\\[3pt]\n    {r2}"
    else:
        contact_str = " | ".join(contact_items)
    header = _render_header_with_optional_photo(name, title, contact_str, photo_filename, accent_cmd="")
    # Minimal ATS is strictly a single-page template
    body = _render_sections_body(cv, resume_type, lang, is_single_page=True)

    return rf"""\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{lmodern}}
\usepackage[left=1.0cm,right=1.0cm,top=0.6cm,bottom=0.6cm]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{name=\section,numberless}}{{\normalsize\bfseries\scshape}}{{}}{{0em}}{{}}[\vspace{{1pt}}\titlerule]
\titlespacing*{{name=\section,numberless}}{{0pt}}{{4.5pt}}{{1.5pt}}
\titleformat{{\section}}{{\normalsize\bfseries\scshape}}{{}}{{0em}}{{}}[\vspace{{1pt}}\titlerule]
\titlespacing*{{\section}}{{0pt}}{{4.5pt}}{{1.5pt}}

\begin{{document}}
{header}
{body}
\end{{document}}
"""

def _split_first_last_name(raw_name: str) -> tuple[str, str]:
    """Divide o nome completo em (Primeiro(s) Nome(s), Sobrenome(s)) no estilo Russell / Awesome-CV / my_cv."""
    cleaned = (raw_name or "").strip()
    parts = cleaned.split()
    if not parts:
        return ("Candidato", "")
    if len(parts) == 1:
        return (escape_latex(parts[0]), "")
    if len(parts) == 2:
        return (escape_latex(parts[0]), escape_latex(parts[1]))
    # Para 3+ palavras, usa as duas primeiras no primeiro bloco e o restante no segundo
    return (escape_latex(" ".join(parts[:2])), escape_latex(" ".join(parts[2:])))


def _acv_sec_cmd(raw_title: str) -> str:
    """Formata comando \\cvsection{título} garantindo que nenhuma linha horizontal engula o parágrafo seguinte."""
    clean = escape_latex((raw_title or "").replace(r"\&", "&").strip())
    return rf"\cvsection{{{clean}}}"


def get_language_proficiency_score_6(lg_str: str, default_first: bool = False) -> Tuple[str, int]:
    """Retorna (nome_limpo_idioma, score_de_1_a_6) para a escala CEFR de 6 níveis (A1=1, A2=2, B1=3, B2=4, C1=5, C2=6).

    Mapeamento:
    - 6 (C2): Nativo / Native, Fluente / Fluent, Domínio Pleno, Bilíngue, C2
    - 5 (C1): Avançado / Advanced, Operacional Eficaz, C1
    - 4 (B2): Intermediário Superior / Upper Intermediate, Independente, B2
    - 3 (B1): Intermediário / Intermediate, Limiar, B1
    - 2 (A2): Elementar / Elementary, Básico / Basic, A2
    - 1 (A1): Iniciante / Beginner, Básico Inicial, Pouco, A1
    """
    s = str(lg_str or "").strip()
    if not s:
        return ("", 3)

    m = re.match(r"^([^\(\[]+)(?:\s*[\(\[](.*?)[\)\]])?$", s)
    clean_name = m.group(1).strip() if m else s
    prof_note = m.group(2).strip().lower() if m and m.group(2) else ""
    full_low = s.lower()

    # Heurística prioritária para Libras: deve possuir sempre 1 bullet (A1 / nível introdutório)
    norm_name = "".join(
        c for c in unicodedata.normalize("NFKD", clean_name) if unicodedata.category(c) != "Mn"
    ).lower()
    if "libra" in norm_name:
        return (clean_name, 1)

    # 1. Checagem explícita de códigos CEFR (A1, A2, B1, B2, C1, C2)
    if re.search(r"\b(?:c2|c-2)\b", prof_note) or re.search(r"\b(?:c2|c-2)\b", full_low):
        return (clean_name, 6)
    if re.search(r"\b(?:c1|c-1)\b", prof_note) or re.search(r"\b(?:c1|c-1)\b", full_low):
        return (clean_name, 5)
    if re.search(r"\b(?:b2|b-2)\b", prof_note) or re.search(r"\b(?:b2|b-2)\b", full_low):
        return (clean_name, 4)
    if re.search(r"\b(?:b1|b-1)\b", prof_note) or re.search(r"\b(?:b1|b-1)\b", full_low):
        return (clean_name, 3)
    if re.search(r"\b(?:a2|a-2)\b", prof_note) or re.search(r"\b(?:a2|a-2)\b", full_low):
        return (clean_name, 2)
    if re.search(r"\b(?:a1|a-1)\b", prof_note) or re.search(r"\b(?:a1|a-1)\b", full_low):
        return (clean_name, 1)

    # 2. Termos descritivos mapeados para a escala CEFR (1..6)
    if any(k in prof_note for k in ("nativo", "native", "materno", "mother tongue", "bilíngue", "bilingual")):
        return (clean_name, 6)
    if any(k in prof_note for k in ("fluente", "fluent", "proficiente", "proficient", "domínio pleno", "dominio pleno", "pleno")):
        return (clean_name, 6)
    if any(k in prof_note for k in ("avançado", "avancado", "advanced", "operacional")):
        return (clean_name, 5)
    if any(k in prof_note for k in ("intermediário superior", "intermediario superior", "upper intermediate", "upper-intermediate", "independente")):
        return (clean_name, 4)
    if any(k in prof_note for k in ("intermediário", "intermediario", "intermediate")):
        return (clean_name, 3)
    if any(k in prof_note for k in ("básico", "basico", "basic", "elementar", "elementary")):
        return (clean_name, 2)
    if any(k in prof_note for k in ("iniciante", "beginner", "pouco", "introdutório", "introdutorio")):
        return (clean_name, 1)

    # 3. Heurísticas baseadas no nome do idioma quando não há especificação de nível
    if "portugu" in norm_name or default_first:
        return (clean_name, 6)
    if "ingl" in norm_name or "engl" in norm_name:
        return (clean_name, 3)
    if any(k in norm_name for k in ("espanh", "span")):
        return (clean_name, 2)

    return (clean_name, 3)


def _build_acv_sections(
    cv: Dict[str, Any],
    resume_type: str,
    lang: str = "pt-br",
    skills_first: bool = False,
    with_lang_circles: bool = True,
) -> str:
    """Constrói seções no estilo Russell CV / Awesome-CV (\\cvsection, \\cventries, \\cvskills, \\cvhonors)."""
    t = LATEX_I18N[normalize_lang(lang)]
    is_en = normalize_lang(lang).startswith("en")
    blocks: List[str] = []

    if cv.get("summary"):
        sec_title = t["sec_profile"] if with_lang_circles else (
            t["sec_summary_acad"] if resume_type == "academico" else t["sec_summary_prof"]
        )
        blocks.append(
            _acv_sec_title_with_body(
                sec_title,
                rf"{{\small\color{{sidecolor}} {escape_latex(cv['summary'])}}}\par\vspace{{4pt}}",
            )
        )

    # Skills block (tabular style \cvskills)
    sk_lines: List[str] = []
    for sk in (cv.get("skills") or []):
        if isinstance(sk, dict):
            cat = escape_latex(sk.get("category"))
            items = escape_latex(sk.get("items"))
        else:
            s = str(sk).strip()
            cat = ""
            items = escape_latex(s)
        if items:
            label = rf"\textbf{{\color{{sidecolor}} {cat}}}" if cat else ""
            sk_lines.append(rf"    {label} & {{\small {items}}} \\")
    skill_block = ""
    if sk_lines:
        skill_body = (
            r"\noindent\begin{tabular}{@{} r p{0.78\textwidth} @{}}"
            + "\n"
            + "\n".join(sk_lines)
            + "\n"
            + r"\end{tabular}\par\vspace{4pt}"
        )
        skill_block = _acv_sec_title_with_body(t["sec_skills"], skill_body)

    # Experience block (\cventries)
    xp_entries: List[str] = []
    for xp in (cv.get("experience") or []):
        role = escape_latex(xp.get("role"))
        org = escape_latex(xp.get("organization"))
        per = escape_latex(xp.get("period"))
        bullets = [escape_latex(sanitize_experience_description(b, lang=lang)) for b in (xp.get("bullets") or []) if str(b).strip()]
        b_tex = ""
        if bullets:
            items_str = "\n".join(rf"    \item {b}" for b in bullets)
            b_tex = (
                r"\begin{itemize}[leftmargin=1.3em,nosep,topsep=2pt]"
                + "\n"
                + items_str
                + "\n"
                + r"\end{itemize}"
            )
        xp_entries.append(rf"\cventry{{{role}}}{{{org}}}{{}}{{{per}}}{{{b_tex}}}")
    exp_title = t["sec_exp_acad"] if resume_type == "academico" else t["sec_exp_prof"]
    exp_block = _acv_sec_title_with_body(exp_title, "\n\n".join(xp_entries)) if xp_entries else ""

    # Education block (\cventries)
    ed_entries: List[str] = []
    for ed in (cv.get("education") or []):
        deg = escape_latex(ed.get("degree"))
        inst = escape_latex(ed.get("institution"))
        per = escape_latex(ed.get("period"))
        det = escape_latex(ed.get("details"))
        det_tex = rf"{{\small {det}}}" if det else ""
        ed_entries.append(rf"\cventry{{{deg}}}{{{inst}}}{{}}{{{per}}}{{{det_tex}}}")
    edu_block = _acv_sec_title_with_body(t["sec_education"], "\n\n".join(ed_entries)) if ed_entries else ""

    # Projects block (\cventries)
    pj_entries: List[str] = []
    lbl_tech = t.get("lbl_tech_stack", "Ferramentas & Tecnologias")
    for pj in (cv.get("projects") or []):
        nm = escape_latex(pj.get("name") or "").strip()
        if not nm:
            continue
        tech = escape_latex(pj.get("tech") or "").strip()
        url = (pj.get("url") or "").strip()
        raw_desc = pj.get("description") or ""
        desc = escape_latex(sanitize_project_description(raw_desc, lang)).strip()
        if not desc:
            if tech:
                desc = f"Software and technical implementation developed with {tech}." if is_en else f"Projeto e implementação técnica desenvolvida em {tech}."
            else:
                desc = f"Software implementation and development for {nm}." if is_en else f"Projeto e desenvolvimento computacional referente a {nm}."
        if url and url.startswith("http"):
            nm_tex = rf"\href{{{escape_url(url)}}}{{\textbf{{{nm}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
        else:
            nm_tex = rf"\textbf{{{nm}}}"
        b_items: List[str] = []
        if desc:
            b_items.append(rf"    \item {desc}")
        if tech:
            b_items.append(rf"    \item \textbf{{{lbl_tech}:}} {tech}")
        b_tex = (
            r"\begin{itemize}[leftmargin=1.3em,nosep,topsep=2pt]"
            + "\n"
            + "\n".join(b_items)
            + "\n"
            + r"\end{itemize}"
            if b_items
            else ""
        )
        pj_entries.append(rf"\cventry{{}}{{{nm_tex}}}{{}}{{}}{{{b_tex}}}")
    proj_title = t["sec_proj_acad"] if resume_type == "academico" else t["sec_proj_prof"]
    proj_block = _acv_sec_title_with_body(proj_title, "\n\n".join(pj_entries)) if pj_entries else ""

    # Publications block
    pub_block = ""
    pubs = cv.get("publications") or []
    if pubs:
        pb_lines = [r"\begin{enumerate}[label=\arabic*.,leftmargin=1.5em,itemsep=2pt,topsep=2pt]"]
        for pb in pubs:
            raw_t_acv = pb.get("title") or ""
            title = escape_latex(raw_t_acv).strip()
            title = re.sub(r"-(Resumo Estendido|Short Paper|Extended Abstract)\b", r" (\1)", title, flags=re.IGNORECASE)
            venue = escape_latex(clean_publication_venue(pb.get("venue") or "", raw_t_acv)).strip()
            year = escape_latex(pb.get("year") or "").strip()
            authors = escape_latex(pb.get("authors") or "").strip()
            if authors and (authors.lower() in title.lower() or title.lower() in authors.lower()):
                authors = ""
            doi = (pb.get("doi") or "").strip()
            pub_url = (pb.get("url") or "").strip()
            if not pub_url and doi:
                pub_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
            title_head = rf"\textbf{{{title}}}"
            if pub_url and pub_url.startswith("http"):
                title_head = rf"\href{{{escape_url(pub_url)}}}{{\textbf{{{title}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
            parts = []
            if authors:
                parts.append(f"{authors}.")
            parts.append(f"{title_head}.")
            if venue:
                parts.append(rf"\textit{{{venue}}},")
            if year:
                parts.append(f"{year}.")
            if doi:
                doi_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
                parts.append(rf"\href{{{escape_url(doi_url)}}}{{\color{{accent}}DOI: {escape_latex(doi)}}}")
            pb_lines.append("    \\item {\\small " + " ".join(parts) + "}")
        pb_lines.append(r"\end{enumerate}")
        pub_block = _acv_sec_title_with_body(t["sec_publications"], "\n".join(pb_lines))

    # Languages & Awards block
    langs = [str(x).strip() for x in (cv.get("languages") or []) if str(x).strip()]
    lang_block = ""
    if langs:
        if with_lang_circles:
            l_rows: List[str] = []
            for idx, lg in enumerate(langs):
                clean_name, filled = get_language_proficiency_score_6(lg, default_first=(idx == 0))
                full_circle = r"\faIcon[solid]{circle}"
                empty_circle = r"\faIcon[regular]{circle}"
                dots = " ".join([full_circle] * filled + [empty_circle] * (6 - filled))
                l_rows.append(rf"    \textbf{{\color{{sidecolor}} {escape_latex(clean_name)}}} & {{\color{{accent}} {dots}}} \\")
            l_body = (
                r"\noindent\begin{tabular}{@{} p{0.50\textwidth} >{\raggedleft\arraybackslash}p{0.45\textwidth} @{}}"
                + "\n"
                + "\n".join(l_rows)
                + "\n"
                + r"\end{tabular}\par\vspace{3pt}"
            )
            lang_block = _acv_sec_title_with_body(t["sec_languages"], l_body)
        else:
            langs_esc = " $\\cdot$ ".join(escape_latex(x) for x in langs)
            lang_block = _acv_sec_title_with_body(t["sec_languages"], rf"{{\small {langs_esc}}}\par\vspace{{3pt}}")

    clean_awards = sanitize_awards(cv.get("awards"), lang=lang)
    award_block = ""
    if clean_awards:
        aw_lines = [r"\begin{itemize}[leftmargin=1.3em,nosep,topsep=2pt]"]
        for aw in clean_awards:
            aw_lines.append(rf"    \item {{\small {escape_latex(aw)}}}")
        aw_lines.append(r"\end{itemize}")
        award_block = _acv_sec_title_with_body(t["sec_awards"], "\n".join(aw_lines))

    if resume_type == "academico":
        ordered = [edu_block, exp_block, pub_block, proj_block, skill_block, award_block, lang_block]
    elif skills_first:
        # Ordem do Jason Richards' Résumé (Awesome-CV): Skills -> Education -> Experience -> Projects -> Pubs -> Languages
        ordered = [skill_block, edu_block, exp_block, proj_block, pub_block, award_block, lang_block]
    else:
        # Ordem do Currículo T.I. (Russell CV): Skills -> Experience -> Education -> Projects -> Pubs -> Languages
        ordered = [skill_block, exp_block, edu_block, proj_block, pub_block, award_block, lang_block]

    for b in ordered:
        if b:
            blocks.append(b)

    return "\n\n".join(blocks)


def _acv_sec_title_with_body(title: str, body: str) -> str:
    return _acv_sec_cmd(title) + "\n" + body


def _render_overleaf_russell_ti(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    """Renderiza o modelo Overleaf 'Currículo - T.I.' (Russell CV — https://www.overleaf.com/read/rgfqqnnynrmv#d5b171)."""
    t = LATEX_I18N[normalize_lang(lang)]
    raw_name = cv.get("name") or t["default_candidate"]
    first_nm, last_nm = _split_first_last_name(raw_name)
    default_tl = t["default_researcher"] if resume_type == "academico" else t["default_tech_title"]
    role = escape_latex(cv.get("title") or default_tl)

    row1_links: List[str] = []
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=raw_name))
        row1_links.append(rf"\mbox{{\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{{gh_disp}}}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=raw_name))
        row1_links.append(rf"\mbox{{\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{{orcid_disp}}}}}}}")
    if links.get("scholar"):
        sc_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=raw_name))
        row1_links.append(rf"\mbox{{\href{{{escape_url(links['scholar'])}}}{{\faIcon{{google}}\ \textbf{{{sc_disp}}}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=raw_name))
        row1_links.append(rf"\mbox{{\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{{lattes_disp}}}}}}}")

    row2_links: List[str] = []
    clean_em = (cv.get("email") or links.get("email") or "").strip()
    if clean_em:
        row2_links.append(rf"\mbox{{\href{{mailto:{escape_url(clean_em)}}}{{\faIcon[regular]{{envelope}}\ {escape_latex(clean_em)}}}}}")
    if cv.get("phone"):
        row2_links.append(rf"\mbox{{\faIcon{{whatsapp}}\ {escape_latex(cv['phone'])}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=raw_name))
        row2_links.append(rf"\mbox{{\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{{li_disp}}}}}}}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        row2_links.append(rf"\mbox{{\href{{{escape_url(links['portfolio'])}}}{{\faIcon{{globe}}\ \textbf{{{port_disp}}}}}}}")
    if cv.get("location"):
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(cv["location"].strip())
        row2_links.append(rf"\mbox{{\href{{{escape_url(maps_url)}}}{{\faIcon{{map-marker-alt}}\ {escape_latex(cv['location'].strip())}}}}}")

    r1_str = " \\quad | \\quad ".join(row1_links)
    r2_str = " \\quad | \\quad ".join(row2_links)
    contacts_combined = "\\\\[3pt]\n    ".join(x for x in (r1_str, r2_str) if x)

    if photo_filename:
        header_tex = rf"""\begin{{center}}
\begin{{tabular}}{{@{{}} c l @{{}}}}
  \adjustbox{{valign=c}}{{\includegraphics[width=2.3cm,height=2.3cm,keepaspectratio]{{{photo_filename}}}}} &
  \hspace{{2mm}}\begin{{minipage}}[c]{{0.82\linewidth}}
    \centering
    {{\fontsize{{22pt}}{{26pt}}\selectfont\color{{graytext}} {first_nm}}} {{\fontsize{{22pt}}{{26pt}}\selectfont\bfseries\color{{sidecolor}} {last_nm}}}\\[3pt]
    {{\large\itshape\color{{accent}} {role}}}\\[4pt]
    {{\small {contacts_combined}}}
  \end{{minipage}}
\end{{tabular}}
\end{{center}}"""
    else:
        header_tex = rf"""\begin{{center}}
    {{\fontsize{{24pt}}{{28pt}}\selectfont\color{{graytext}} {first_nm}}} {{\fontsize{{24pt}}{{28pt}}\selectfont\bfseries\color{{sidecolor}} {last_nm}}}\\[3pt]
    {{\large\itshape\color{{accent}} {role}}}\\[5pt]
    {{\small {contacts_combined}}}
\end{{center}}"""

    body = _build_acv_sections(cv, resume_type, lang, skills_first=False, with_lang_circles=True)

    return rf"""% Template Overleaf: Currículo - T.I. (Russell CV) — https://www.overleaf.com/read/rgfqqnnynrmv#d5b171
\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{roboto}}
\usepackage[default]{{sourcesanspro}}
\usepackage{{fontawesome5}}
\usepackage{{adjustbox}}
\usepackage{{array}}
\usepackage[left=1.4cm,top=0.9cm,right=1.4cm,bottom=1.5cm,footskip=0.5cm]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{accent}}{{HTML}}{{0F4C81}}
\definecolor{{sidecolor}}{{HTML}}{{1E293B}}
\definecolor{{graytext}}{{HTML}}{{5D5D5D}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\newcommand{{\vhrulefill}}[1]{{\leavevmode\leaders\hrule height #1\hfill\kern0pt}}
\newcommand{{\cvsection}}[1]{{%
  \vspace{{7pt}}%
  \noindent{{\Large\bfseries\color{{accent}}#1}}\hspace{{4pt}}{{\color{{graytext}}\vhrulefill{{0.9pt}}}}\par\vspace{{4pt}}%
}}
\newcommand{{\cventry}}[5]{{%
  \noindent\begin{{tabular*}}{{\textwidth}}{{@{{\extracolsep{{\fill}}}} p{{0.74\textwidth}} r @{{}}}}
    \textbf{{\color{{sidecolor}} #2}} & {{\small\itshape\color{{accent}} #3}} \\
    \ifstrempty{{#1#4}}{{}}{{\small\scshape #1 & \small\itshape\color{{graytext}} #4 \\}}%
  \end{{tabular*}}\par
  #5\vspace{{4pt}}\par
}}

\begin{{document}}
{header_tex}
{body}
\end{{document}}
"""


def _render_overleaf_awesome_cv(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    """Renderiza o modelo Overleaf 'Jason Richards' Résumé' (Awesome-CV — https://www.overleaf.com/articles/jason-richards-resume/chbxgnfyyvfc)."""
    t = LATEX_I18N[normalize_lang(lang)]
    raw_name = cv.get("name") or t["default_candidate"]
    first_nm, last_nm = _split_first_last_name(raw_name)
    full_nm_esc = escape_latex(raw_name)
    default_tl = t["default_researcher"] if resume_type == "academico" else t["default_professional"]
    role = escape_latex(cv.get("title") or default_tl)

    social_items: List[str] = []
    if cv.get("phone"):
        social_items.append(rf"\mbox{{\faIcon{{mobile-alt}}\ {escape_latex(cv['phone'])}}}")
    clean_em = (cv.get("email") or links.get("email") or "").strip()
    if clean_em:
        social_items.append(rf"\mbox{{\href{{mailto:{escape_url(clean_em)}}}{{\faIcon[regular]{{envelope}}\ {escape_latex(clean_em)}}}}}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        social_items.append(rf"\mbox{{\href{{{escape_url(links['portfolio'])}}}{{\faIcon{{globe}}\ \textbf{{{port_disp}}}}}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=raw_name))
        social_items.append(rf"\mbox{{\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{{li_disp}}}}}}}")
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=raw_name))
        social_items.append(rf"\mbox{{\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{{gh_disp}}}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=raw_name))
        social_items.append(rf"\mbox{{\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{{orcid_disp}}}}}}}")
    if links.get("scholar"):
        sc_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=raw_name))
        social_items.append(rf"\mbox{{\href{{{escape_url(links['scholar'])}}}{{\faIcon{{google}}\ \textbf{{{sc_disp}}}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=raw_name))
        social_items.append(rf"\mbox{{\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{{lattes_disp}}}}}}}")
    if cv.get("location"):
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(cv["location"].strip())
        social_items.append(rf"\mbox{{\href{{{escape_url(maps_url)}}}{{\faIcon{{map-marker-alt}}\ {escape_latex(cv['location'].strip())}}}}}")

    if len(social_items) > 4:
        mid = (len(social_items) + 1) // 2
        r1 = " \\quad\\textbar\\quad ".join(social_items[:mid])
        r2 = " \\quad\\textbar\\quad ".join(social_items[mid:])
        social_str = f"{r1}\\\\[3pt]\n    {r2}"
    else:
        social_str = " \\quad\\textbar\\quad ".join(social_items)

    if photo_filename:
        header_tex = rf"""\noindent
\begin{{minipage}}[c]{{0.80\textwidth}}
    {{\fontsize{{26pt}}{{30pt}}\selectfont\color{{graytext}} {first_nm}}} {{\fontsize{{26pt}}{{30pt}}\selectfont\bfseries\color{{sidecolor}} {last_nm}}}\\[4pt]
    {{\large\itshape\color{{accent}} {role}}}\\[5pt]
    {{\footnotesize\color{{graytext}} {social_str}}}
\end{{minipage}}%
\hfill
\begin{{minipage}}[c]{{0.18\textwidth}}
    \raggedleft
    \includegraphics[width=2.4cm,height=2.4cm,keepaspectratio]{{{photo_filename}}}
\end{{minipage}}
\vspace{{4pt}}"""
    else:
        header_tex = rf"""\begin{{center}}
    {{\fontsize{{28pt}}{{32pt}}\selectfont\color{{graytext}} {first_nm}}} {{\fontsize{{28pt}}{{32pt}}\selectfont\bfseries\color{{sidecolor}} {last_nm}}}\\[4pt]
    {{\large\itshape\color{{accent}} {role}}}\\[5pt]
    {{\footnotesize\color{{graytext}} {social_str}}}
\end{{center}}
\vspace{{2pt}}"""

    body = _build_acv_sections(cv, resume_type, lang, skills_first=True, with_lang_circles=False)
    footer_lbl = "Résumé" if normalize_lang(lang) == "en-us" else "Currículo"

    return rf"""% Template Overleaf: Jason Richards' Résumé (Awesome-CV) — https://www.overleaf.com/articles/jason-richards-resume/chbxgnfyyvfc
\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{roboto}}
\usepackage[default]{{sourcesanspro}}
\usepackage{{fontawesome5}}
\usepackage{{fancyhdr}}
\usepackage{{array}}
\usepackage[left=1.4cm,top=1.1cm,right=1.4cm,bottom=1.8cm,footskip=0.5cm]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{accent}}{{HTML}}{{0395DE}}
\definecolor{{sidecolor}}{{HTML}}{{333333}}
\definecolor{{graytext}}{{HTML}}{{5D5D5D}}

\pagestyle{{fancy}}
\fancyhf{{}}
\renewcommand{{\headrulewidth}}{{0pt}}
\fancyfoot[L]{{\footnotesize\color{{graytext}}\today}}
\fancyfoot[C]{{\footnotesize\color{{graytext}}{full_nm_esc}\ ~~~\textperiodcentered~~~\ {footer_lbl}}}
\fancyfoot[R]{{\footnotesize\color{{graytext}}\thepage}}
\setlength{{\parindent}}{{0pt}}

\newcommand{{\vhrulefill}}[1]{{\leavevmode\leaders\hrule height #1\hfill\kern0pt}}
\newcommand{{\cvsection}}[1]{{%
  \vspace{{7pt}}%
  \noindent{{\Large\bfseries\color{{accent}}#1}}\hspace{{4pt}}{{\color{{graytext}}\vhrulefill{{0.9pt}}}}\par\vspace{{4pt}}%
}}
\newcommand{{\cventry}}[5]{{%
  \noindent\begin{{tabular*}}{{\textwidth}}{{@{{\extracolsep{{\fill}}}} p{{0.74\textwidth}} r @{{}}}}
    \textbf{{\color{{sidecolor}} #2}} & {{\small\itshape\color{{accent}} #3}} \\
    \ifstrempty{{#1#4}}{{}}{{\small\scshape #1 & \small\itshape\color{{graytext}} #4 \\}}%
  \end{{tabular*}}\par
  #5\vspace{{4pt}}\par
}}

\begin{{document}}
{header_tex}
{body}
\end{{document}}
"""


def _render_overleaf_single_page_keywords(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    """Renderiza o modelo Overleaf 'Sample single page resume with keywords' (https://www.overleaf.com/latex/templates/sample-single-page-resume-with-keywords/wmcxcgmtkxzk).

    Garante formato estrito de página única através de curadoria balanceada de itens,
    espaçamento compacto e cabeçalho harmônico com contatos distribuídos em duas subcolunas.
    """
    t = LATEX_I18N[normalize_lang(lang)]
    is_en = normalize_lang(lang) == "en-us"
    raw_name = cv.get("name") or t["default_candidate"]
    first_nm, last_nm = _split_first_last_name(raw_name)
    default_tl = t["default_researcher"] if resume_type == "academico" else t["default_professional"]
    role = escape_latex(cv.get("title") or default_tl)

    # Coleta keywords de skills para destacar nas experiências caso necessário
    all_skill_items: List[str] = []
    for sk in (cv.get("skills") or []):
        if isinstance(sk, dict) and sk.get("items"):
            all_skill_items.append(escape_latex(sk["items"]))
        elif isinstance(sk, str) and sk.strip():
            all_skill_items.append(escape_latex(sk.strip()))
    fallback_kw = ", ".join(all_skill_items)[:85]

    # Contatos organizados em grid harmônico de 2 colunas para layout estético e compacto
    col_left: List[str] = []
    col_right: List[str] = []

    clean_em = (cv.get("email") or links.get("email") or "").strip()
    if clean_em:
        col_left.append(rf"\faIcon{{envelope}}\ \href{{mailto:{escape_url(clean_em)}}}{{\textbf{{{escape_latex(clean_em)}}}}}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        col_left.append(rf"\faIcon{{globe}}\ \href{{{escape_url(links['portfolio'])}}}{{\textbf{{{port_disp}}}}}")
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=raw_name))
        col_left.append(rf"\faIcon{{github}}\ \href{{{escape_url(links['github'])}}}{{\textbf{{{gh_disp}}}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=raw_name))
        col_left.append(rf"\faIcon{{linkedin}}\ \href{{{escape_url(links['linkedin'])}}}{{\textbf{{{li_disp}}}}}")

    if cv.get("phone"):
        col_right.append(rf"\faIcon{{phone}}\ \textbf{{{escape_latex(cv['phone'])}}}")
    if links.get("scholar"):
        sc_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=raw_name))
        col_right.append(rf"\faIcon{{google}}\ \href{{{escape_url(links['scholar'])}}}{{\textbf{{{sc_disp}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=raw_name))
        col_right.append(rf"\faIcon{{orcid}}\ \href{{{escape_url(links['orcid'])}}}{{\textbf{{{orcid_disp}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=raw_name))
        col_right.append(rf"\faIcon{{graduation-cap}}\ \href{{{escape_url(links['lattes'])}}}{{\textbf{{{lattes_disp}}}}}")
    if cv.get("location"):
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(cv["location"].strip())
        col_right.append(rf"\faIcon{{map-marker-alt}}\ \href{{{escape_url(maps_url)}}}{{\textbf{{{escape_latex(cv['location'].strip())}}}}}")

    all_contacts = col_left + col_right
    if len(all_contacts) <= 3:
        right_contact_tex = "\\\\n    ".join(all_contacts)
    else:
        half = (len(all_contacts) + 1) // 2
        c1 = all_contacts[:half]
        c2 = all_contacts[half:]
        tbl_rows = []
        for i in range(half):
            left_item = c1[i]
            right_item = c2[i] if i < len(c2) else ""
            if right_item:
                tbl_rows.append(rf"  {left_item} & {right_item} \\")
            else:
                tbl_rows.append(rf"  \multicolumn{{2}}{{l}}{{{left_item}}} \\")
        right_contact_tex = (
            r"\begin{tabular}[c]{@{} l @{\hspace{14pt}} l @{}}" + "\n"
            + "\n".join(tbl_rows) + "\n"
            + r"\end{tabular}"
        )

    photo_inline = (
        rf"\includegraphics[width=1.9cm,height=1.9cm,keepaspectratio]{{{photo_filename}}}\hspace{{6pt}}"
        if photo_filename
        else ""
    )

    summary_tex = ""
    if cv.get("summary"):
        sum_lbl = "SUMMARY" if is_en else "RESUMO"
        summary_tex = rf"""\cvsec{{\faIcon{{file-alt}}}}{{{sum_lbl}}}
{{\small {escape_latex(cv['summary'])}}}
\vspace{{3pt}}"""

    pubs = cv.get("publications") or []
    projs = cv.get("projects") or []
    clean_awards = sanitize_awards(cv.get("awards"), lang=lang)
    langs = [str(x).strip() for x in (cv.get("languages") or []) if str(x).strip()]

    # Alocação dinâmica para Coluna 1 (Work + Education + Awards)
    n_edu = min(2, len(cv.get("education") or []))
    n_aw = min(4, len(clean_awards))
    cost_other_left = (n_edu * 3.2 + (2.0 if n_edu else 0.0)) + (n_aw * 1.4 + (1.8 if n_aw else 0.0))
    left_budget = 36.0
    avail_work = max(10.0, left_budget - cost_other_left)
    max_work = min(len(cv.get("experience") or []), max(1, int((avail_work - 2.0) / 3.4)))

    # Alocação dinâmica para Coluna 2 (Projects + Publications + Skills + Languages)
    lang_cost = 2.0 if langs else 0.0
    n_sk = min(2, len(cv.get("skills") or []))
    skill_cost = (n_sk * 2.2 + 2.0) if n_sk else 0.0
    right_budget = 36.0
    avail_proj_pub = max(10.0, right_budget - lang_cost - skill_cost)
    available_page_budget = max(
        0.0,
        left_budget + right_budget - cost_other_left - lang_cost - skill_cost - (3.5 if cv.get("summary") else 0.0),
    )
    allow_fallback = _single_page_fallback_needed(
        resume_type,
        0,
        len(projs),
        len(pubs),
        avail_proj_pub,
        weight_exp=0.0,
        weight_proj=2.5,
        weight_pub=1.8,
    )
    _, max_proj, max_pubs = _allocate_single_page_budget(
        0,
        len(projs),
        len(pubs),
        budget=avail_proj_pub,
        weight_proj=2.5,
        weight_pub=1.8,
        resume_type=resume_type,
        allow_fallback=allow_fallback,
    )

    # Coluna 1: WORK + EDUCATION + AWARDS
    work_lbl = "WORK" if is_en else "EXPERIÊNCIA"
    work_items: List[str] = []
    for xp in (cv.get("experience") or [])[:max_work]:
        r_txt = escape_latex(xp.get("role"))
        p_txt = escape_latex(xp.get("period"))
        o_txt = escape_latex(xp.get("organization"))
        raw_bullets = [sanitize_experience_description(b, lang=lang) for b in (xp.get("bullets") or []) if str(b).strip()]
        desc_txt = escape_latex(truncate_at_clause_boundary("; ".join(raw_bullets), 160)) if raw_bullets else ""
        head_rp = f"{r_txt} / {p_txt}" if p_txt else r_txt
        work_items.append(rf"\work{{{head_rp}}}{{{o_txt}}}{{{desc_txt}}}{{{fallback_kw}}}")
    work_sec = (rf"\cvsec{{\faIcon{{pencil-alt}}}}{{{work_lbl}}}" + "\n" + "\n\n".join(work_items)) if work_items else ""

    edu_lbl = "EDUCATION" if is_en else "FORMAÇÃO ACADÊMICA"
    edu_rows: List[str] = []
    for ed in (cv.get("education") or [])[:2]:
        deg = escape_latex(ed.get("degree"))
        per = escape_latex(ed.get("period"))
        inst = escape_latex(ed.get("institution"))
        det = escape_latex(ed.get("details"))
        head_ed = f"{deg} - {per}" if per else deg
        edu_rows.append(rf"\school{{{head_ed}}}{{{inst}}}{{{det}}}")
    edu_sec = (rf"\cvsec{{\faIcon{{graduation-cap}}}}{{{edu_lbl}}}" + "\n" + "\n\n".join(edu_rows)) if edu_rows else ""

    aw_sec = ""
    if clean_awards:
        aw_lbl = "AWARDS" if is_en else r"PRÊMIOS \& CERTIFICAÇÕES"
        a_rows = [rf"    \item {escape_latex(a)}" for a in clean_awards[:n_aw]]
        aw_sec = (
            rf"\cvsec{{\faIcon{{star}}}}{{{aw_lbl}}}"
            + "\n\\begin{itemize}[leftmargin=1.1em,noitemsep,topsep=1pt]\n"
            + "\n".join(a_rows)
            + "\n\\end{itemize}"
        )

    # Coluna 2: OTHER PROJECTS + SKILLS + PUBLICATIONS + LANGUAGES
    proj_lbl = "OTHER PROJECTS" if is_en else "PROJETOS DE DESTAQUE"
    proj_rows: List[str] = []
    for pj in (cv.get("projects") or [])[:max_proj]:
        nm = escape_latex(pj.get("name"))
        tech = escape_latex(pj.get("tech"))
        url = (pj.get("url") or "").strip()
        raw_d = sanitize_project_description(pj.get("description"), lang)
        desc = escape_latex(finalize_project_description(truncate_at_clause_boundary(raw_d, 130)))
        if url and url.startswith("http"):
            nm_head = rf"\href{{{escape_url(url)}}}{{\textbf{{{nm}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
        else:
            nm_head = rf"\textbf{{{nm}}}"
        kw_suffix = rf" --- \textbf{{{tech}}}" if tech else ""
        body_p = f"{desc}{kw_suffix}" if desc else kw_suffix.lstrip(" -")
        proj_rows.append(rf"    \item {nm_head}: {body_p}")
    proj_sec = ""
    if proj_rows:
        proj_sec = (
            rf"\cvsec{{\faIcon{{paint-brush}}}}{{{proj_lbl}}}"
            + "\n\\begin{itemize}[leftmargin=1.1em,noitemsep,topsep=1pt]\n"
            + "\n".join(proj_rows)
            + "\n\\end{itemize}"
        )

    sk_lbl = "SKILLS" if is_en else "COMPETÊNCIAS"
    sk_rows: List[str] = []
    for sk in (cv.get("skills") or []):
        if isinstance(sk, dict):
            cat = escape_latex(sk.get("category"))
            items = escape_latex(sk.get("items"))
        else:
            cat = ""
            items = escape_latex(str(sk).strip())
        if items:
            row = rf"\noindent\textbf{{{cat}:}} {{\small {items}}}" if cat else rf"\noindent{{\small {items}}}"
            sk_rows.append(row + r"\par\vspace{1pt}")
    sk_sec = (rf"\cvsec{{\faIcon{{list}}}}{{{sk_lbl}}} " + "\n" + "\n".join(sk_rows)) if sk_rows else ""

    pub_sec = ""
    if max_pubs > 0 and pubs:
        pub_lbl = "PUBLICATIONS" if is_en else "PUBLICAÇÕES"
        p_rows: List[str] = []
        for pb in pubs[:max_pubs]:
            pt = escape_latex(truncate_at_clause_boundary(pb.get("title") or "", 85))
            pv = escape_latex(truncate_at_clause_boundary(pb.get("venue") or "", 45))
            py = escape_latex(pb.get("year"))
            pub_url = (pb.get("url") or "").strip()
            doi = (pb.get("doi") or "").strip()
            if not pub_url and doi:
                pub_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
            if pub_url and pub_url.startswith("http"):
                pt_head = rf"\href{{{escape_url(pub_url)}}}{{\textbf{{{pt}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
            else:
                pt_head = rf"\textbf{{{pt}}}"
            meta_str = f"{pv}, {py}" if (pv and py) else (pv or py)
            p_rows.append(rf"    \item {pt_head}" + (rf" ({meta_str})" if meta_str else ""))
        pub_sec = (
            rf"\cvsec{{\faIcon{{book}}}}{{{pub_lbl}}}"
            + "\n\\begin{itemize}[leftmargin=1.1em,noitemsep,topsep=1pt]\n"
            + "\n".join(p_rows)
            + "\n\\end{itemize}"
        )

    lg_sec = ""
    if langs:
        lg_lbl = "LANGUAGES / INTERESTS" if is_en else "IDIOMAS"
        lg_sec = rf"\cvsec{{\faIcon{{globe}}}}{{{lg_lbl}}}" + "\n{\\small " + " $\\cdot$ ".join(escape_latex(x) for x in langs) + "}"

    if resume_type == "academico":
        col1_body = "\n\n".join(x for x in (edu_sec, work_sec, aw_sec) if x)
        col2_body = "\n\n".join(x for x in (pub_sec, proj_sec, sk_sec, lg_sec) if x)
    else:
        col1_body = "\n\n".join(x for x in (work_sec, edu_sec, aw_sec) if x)
        col2_body = "\n\n".join(x for x in (proj_sec, sk_sec, pub_sec, lg_sec) if x)

    return rf"""% Template Overleaf: Sample single page resume with keywords — https://www.overleaf.com/latex/templates/sample-single-page-resume-with-keywords/wmcxcgmtkxzk
\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage[default]{{raleway}}
\usepackage{{fontawesome5}}
\usepackage{{tikz}}
\usepackage{{multicol}}
\usepackage[skins]{{tcolorbox}}
\usepackage[left=0.8cm,right=0.8cm,top=0.7cm,bottom=0.7cm,footskip=0.15in]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{accent}}{{HTML}}{{52ADE3}}
\definecolor{{sidecolor}}{{HTML}}{{111827}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\columnsep}}{{0.8cm}}

\newcommand*{{\circled}}[1]{{%
  \tikz[baseline=(char.base)]{{%
    \node[shape=circle,fill=sidecolor,inner sep=1.8pt,minimum size=17pt] (char) {{\textcolor{{white}}{{\footnotesize #1}}}};%
  }}%
}}
\newcommand*{{\cvsec}}[2]{{%
  \vspace{{4pt}}\noindent\circled{{#1}}\hspace{{4pt}}{{\large\bfseries\color{{accent}} #2}}\par\vspace{{2pt}}%
}}
\newcommand*{{\work}}[4]{{%
  \noindent{{\normalsize\bfseries\color{{sidecolor}} #1}}\par
  \ifx&#2&\else\noindent{{\small\bfseries\color{{accent}} #2}}\par\fi
  \ifx&#3&\else\noindent{{\small #3}}\par\fi
  \ifx&#4&\else\noindent{{\footnotesize\textbf{{Keywords:}} \textit{{#4}}}}\par\fi
  \vspace{{3pt}}
}}
\newcommand*{{\school}}[3]{{%
  \noindent{{\normalsize\bfseries\color{{sidecolor}} #1}}\par
  \ifx&#2&\else\noindent{{\small\bfseries\color{{accent}} #2}}\par\fi
  \ifx&#3&\else\noindent{{\footnotesize\textit{{#3}}}}\par\fi
  \vspace{{2.5pt}}
}}

\begin{{document}}
\noindent
\begin{{minipage}}[c]{{0.40\textwidth}}
    {photo_inline}\begin{{minipage}}[c]{{0.92\linewidth}}
        {{\fontsize{{24}}{{26}}\selectfont\bfseries\color{{sidecolor}} {first_nm}}}\\[2pt]
        {{\fontsize{{26}}{{28}}\selectfont\mdseries\color{{accent}} {last_nm}}}\\[3pt]
        {{\small\itshape\color{{sidecolor}} {role}}}
    \end{{minipage}}
\end{{minipage}}%
\hfill
\begin{{minipage}}[c]{{0.58\textwidth}}
    \footnotesize\raggedleft
    {right_contact_tex}
\end{{minipage}}
\vspace{{3pt}}
\hrule height 0.6pt
\vspace{{3pt}}

{summary_tex}

\begin{{multicols}}{{2}}
{col1_body}
\columnbreak
{col2_body}
\end{{multicols}}
\end{{document}}
"""

def _render_google_standard(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    """Renderiza o modelo Padrão Google (Big Tech / Software Engineer) — baseado em Gayle Laakmann McDowell.

    Layout em página única densa, margens de 0.5 polegadas, estrutura XYZ de realizações,
    divisórias horizontais limpas e total conformidade com triagem humana e automatizada.
    """
    t = LATEX_I18N[normalize_lang(lang)]
    is_en = normalize_lang(lang) == "en-us"
    name = escape_latex(cv.get("name") or t["default_candidate"])
    default_tl = t["default_researcher"] if resume_type == "academico" else t["default_tech_title"]
    title = escape_latex(cv.get("title") or default_tl)

    contact_parts: List[str] = []
    clean_em = (cv.get("email") or links.get("email") or "").strip()
    if clean_em:
        contact_parts.append(rf"\mbox{{\href{{mailto:{escape_url(clean_em)}}}{{\faIcon{{envelope}}\ {escape_latex(clean_em)}}}}}")
    if cv.get("phone"):
        contact_parts.append(rf"\mbox{{\faIcon{{phone}}\ {escape_latex(cv['phone'].strip())}}}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['portfolio'])}}}{{\faIcon{{globe}}\ \textbf{{{port_disp}}}}}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{{li_disp}}}}}}}")
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{{gh_disp}}}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{{orcid_disp}}}}}}}")
    if links.get("scholar"):
        sc_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['scholar'])}}}{{\faIcon{{google}}\ \textbf{{{sc_disp}}}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{{lattes_disp}}}}}}}")
    if cv.get("location"):
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(cv["location"].strip())
        contact_parts.append(rf"\mbox{{\href{{{escape_url(maps_url)}}}{{\faIcon{{map-marker-alt}}\ {escape_latex(cv['location'].strip())}}}}}")

    if len(contact_parts) > 4:
        mid = (len(contact_parts) + 1) // 2
        r1 = " \\quad | \\quad ".join(contact_parts[:mid])
        r2 = " \\quad | \\quad ".join(contact_parts[mid:])
        contacts_str = f"{r1}\\\\[2pt]\n    {r2}"
    else:
        contacts_str = " \\quad | \\quad ".join(contact_parts)

    if photo_filename:
        header_tex = rf"""\noindent
\begin{{minipage}}[c]{{0.80\textwidth}}
    {{\fontsize{{20pt}}{{24pt}}\selectfont\bfseries\color{{sidecolor}} {name}}}\\[2pt]
    {{\normalsize\bfseries\color{{accent}} {title}}}\\[3pt]
    {{\footnotesize {contacts_str}}}
\end{{minipage}}%
\hfill
\begin{{minipage}}[c]{{0.18\textwidth}}
    \raggedleft
    \includegraphics[width=2.2cm,height=2.2cm,keepaspectratio]{{{photo_filename}}}
\end{{minipage}}
\vspace{{2pt}}
{{\color{{accent}}\hrule height 0.8pt}}
\vspace{{3pt}}"""
    else:
        header_tex = rf"""\begin{{center}}
    {{\fontsize{{20pt}}{{24pt}}\selectfont\bfseries\color{{sidecolor}} {name}}}\\[2pt]
    {{\normalsize\bfseries\color{{accent}} {title}}}\\[3pt]
    {{\footnotesize {contacts_str}}}
\end{{center}}
\vspace{{-2pt}}
{{\color{{accent}}\hrule height 0.8pt}}
\vspace{{3pt}}"""

    # Alocação dinâmica de capacidade vertical para página única estrita
    pubs = cv.get("publications") or []
    projs = cv.get("projects") or []
    max_sum_chars = 200 if resume_type == "academico" else 220
    max_edu = 2
    max_skills = 2 if resume_type == "academico" else 3
    max_awards = 3

    raw_sum = cv.get("summary") or ""
    sum_cost = 3.5 if raw_sum else 0.0
    edu_cost = 5.0 if cv.get("education") else 0.0
    skill_cost = 3.0 if cv.get("skills") else 0.0
    aw_cost = 3.0 if cv.get("awards") else 0.0
    lang_cost = 2.0 if cv.get("languages") else 0.0
    base_budget = 50.0
    avail_budget = max(15.0, base_budget - sum_cost - edu_cost - skill_cost - aw_cost - lang_cost)
    exp_costs, proj_costs, pub_costs = _estimate_single_page_entry_costs(cv)

    max_exp, max_proj, max_pubs = _allocate_single_page_budget(
        len(cv.get("experience") or []),
        len(projs),
        len(pubs),
        budget=avail_budget,
        weight_exp=4.0,
        weight_proj=2.8,
        weight_pub=2.0,
        resume_type=resume_type,
        exp_costs=exp_costs,
        proj_costs=proj_costs,
        pub_costs=pub_costs,
    )

    # Summary
    sum_block = ""
    if cv.get("summary"):
        sec_sum = "SUMMARY" if is_en else "RESUMO PROFISSIONAL"
        raw_sum = cv["summary"]
        if len(raw_sum) > max_sum_chars:
            raw_sum = truncate_at_clause_boundary(raw_sum, max_sum_chars)
        sum_block = rf"\section*{{{sec_sum}}}" + "\n" + rf"{{\small {escape_latex(raw_sum)}}}"

    # Experience
    xp_block = ""
    xp_list = (cv.get("experience") or [])[:max_exp]
    if xp_list:
        sec_xp = "WORK EXPERIENCE" if is_en else (t["sec_exp_acad"] if resume_type == "academico" else t["sec_exp_prof"])
        xp_lines = [rf"\section*{{{sec_xp}}}"]
        for xp in xp_list:
            role = escape_latex(xp.get("role"))
            org = escape_latex(xp.get("organization"))
            per = escape_latex(xp.get("period"))
            bullets = [escape_latex(sanitize_experience_description(b, lang=lang)) for b in (xp.get("bullets") or []) if str(b).strip()]
            head_l = f"\\textbf{{{org}}}" if org else f"\\textbf{{{role}}}"
            sub_l = f"\\textit{{{role}}}" if org else ""
            item_lines = [rf"\noindent{head_l} \hfill \textbf{{{per}}}"]
            if sub_l:
                item_lines.append(rf"\\ {sub_l}")
            if bullets:
                item_lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
                for b in bullets:
                    item_lines.append(rf"    \item {b}")
                item_lines.append(r"\end{itemize}")
                item_lines.append(r"\vspace{2pt}")
            else:
                item_lines.append(r"\par\vspace{2pt}")
            xp_lines.append("\n".join(item_lines))
        xp_block = "\n".join(xp_lines)

    # Education
    edu_block = ""
    edu_list = (cv.get("education") or [])[:max_edu]
    if edu_list:
        sec_edu = "EDUCATION" if is_en else t["sec_education"]
        ed_lines = [rf"\section*{{{sec_edu}}}"]
        for ed in edu_list:
            deg = escape_latex(ed.get("degree"))
            inst = escape_latex(ed.get("institution"))
            per = escape_latex(ed.get("period"))
            det = escape_latex(ed.get("details"))
            head_i = f"\\textbf{{{inst}}}" if inst else f"\\textbf{{{deg}}}"
            sub_d = f"\\textit{{{deg}}}" if inst else ""
            item_lines = [rf"\noindent{head_i} \hfill \textbf{{{per}}}"]
            if sub_d and det:
                item_lines.append(rf"\\ {sub_d} \hfill {{\small {det}}}\par\vspace{{2pt}}")
            elif sub_d:
                item_lines.append(rf"\\ {sub_d}\par\vspace{{2pt}}")
            elif det:
                item_lines.append(rf"\\ {{\small {det}}}\par\vspace{{2pt}}")
            else:
                item_lines.append(r"\par\vspace{2pt}")
            ed_lines.append("\n".join(item_lines))
        edu_block = "\n".join(ed_lines)

    # Projects
    pj_block = ""
    pj_list = (cv.get("projects") or [])[:max_proj]
    if pj_list:
        sec_pj = "KEY PROJECTS" if is_en else (t["sec_proj_acad"] if resume_type == "academico" else t["sec_proj_prof"])
        pj_lines = [rf"\section*{{{sec_pj}}}"]
        for pj in pj_list:
            nm = escape_latex(pj.get("name"))
            tech = escape_latex(pj.get("tech"))
            url = (pj.get("url") or "").strip()
            desc = escape_latex(sanitize_project_description(pj.get("description"), lang))
            if url and url.startswith("http"):
                nm_head = rf"\href{{{escape_url(url)}}}{{\textbf{{{nm}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
            else:
                nm_head = rf"\textbf{{{nm}}}"
            tech_str = rf" \textbar{{}} \textit{{{tech}}}" if tech else ""
            pj_lines.append(rf"\noindent{nm_head}{tech_str}")
            if desc:
                pj_lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
                pj_lines.append(rf"    \item {desc}")
                pj_lines.append(r"\end{itemize}")
                pj_lines.append(r"\vspace{1pt}")
            else:
                pj_lines.append(r"\par\vspace{1pt}")
        pj_block = "\n".join(pj_lines)

    # Skills
    sk_block = ""
    sk_list = (cv.get("skills") or [])[:max_skills]
    if sk_list:
        sec_sk = "TECHNICAL SKILLS" if is_en else t["sec_skills"]
        sk_lines = [rf"\section*{{{sec_sk}}}", r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]"]
        for sk in sk_list:
            if isinstance(sk, dict):
                cat = escape_latex(sk.get("category"))
                items = escape_latex(sk.get("items"))
            else:
                s = str(sk).strip()
                if ":" in s:
                    p = s.split(":", 1)
                    cat, items = escape_latex(p[0].strip()), escape_latex(p[1].strip())
                else:
                    cat, items = "", escape_latex(s)
            if items:
                sk_lines.append(rf"    \item \textbf{{{cat}:}} {items}" if cat else rf"    \item {items}")
        sk_lines.append(r"\end{itemize}")
        sk_block = "\n".join(sk_lines)

    # Publications & Awards & Languages
    pub_block = _build_publications_block(pubs, lang, max_items=max_pubs)
    lg_aw_block = _build_languages_and_awards_block(cv.get("languages") or [], cv.get("awards") or [], lang, max_awards=max_awards)

    if resume_type == "academico":
        ordered = [sum_block, edu_block, pub_block, pj_block, xp_block, sk_block, lg_aw_block]
    else:
        ordered = [sum_block, xp_block, pj_block, edu_block, sk_block, pub_block, lg_aw_block]

    body_tex = "\n\n".join(b for b in ordered if b)

    return rf"""% Template Google Standard (Big Tech / Software Engineer) — Gayle Laakmann McDowell Standard
\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{lmodern}}
\usepackage[left=1.0cm,right=1.0cm,top=0.6cm,bottom=0.6cm]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{accent}}{{HTML}}{{0B57D0}}
\definecolor{{sidecolor}}{{HTML}}{{1F1F1F}}
\definecolor{{graytext}}{{HTML}}{{444746}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{\section}}{{\normalsize\bfseries\scshape\color{{accent}}}}{{}}{{0em}}{{}}[\vspace{{1pt}}{{\color{{accent}}\titlerule}}]
\titlespacing*{{\section}}{{0pt}}{{4pt}}{{1.5pt}}

\begin{{document}}
{header_tex}
{body_tex}
\end{{document}}
"""


def _render_ai_ats_max(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    """Renderiza o modelo Otimizado para IA & ATS (Máxima Legibilidade por LLMs e Parsers Neurais).

    Características arquiteturais essenciais:
    - Fluxo textual 100% linear em coluna única (sem colunas paralelas que quebram o fluxo de leitura de parsers de PDF).
    - Metadados semânticos explícitos (TAGS textuais ASCII: LOCATION, EMAIL, PHONE, GITHUB, LINKEDIN).
    - Mapeamento nativo Unicode (glyphtounicode e pdfgentounicode=1).
    - Matriz de Competências e Palavras-Chave (Core Competencies & Keywords) dedicada para match semântico em embeddings.
    - Seções padrão em caixa alta universalmente indexadas por ATS (Workday, Greenhouse, Lever, Taleo) e LLMs.
    """
    t = LATEX_I18N[normalize_lang(lang)]
    is_en = normalize_lang(lang) == "en-us"
    name = escape_latex(cv.get("name") or t["default_candidate"])
    default_tl = t["default_researcher"] if resume_type == "academico" else t["default_professional"]
    title = escape_latex(cv.get("title") or default_tl)

    contact_parts: List[str] = []
    clean_em = (cv.get("email") or links.get("email") or "").strip()
    if clean_em:
        contact_parts.append(rf"\mbox{{\href{{mailto:{escape_url(clean_em)}}}{{\faIcon{{envelope}}\ {escape_latex(clean_em)}}}}}")
    if cv.get("phone"):
        contact_parts.append(rf"\mbox{{\faIcon{{phone}}\ {escape_latex(cv['phone'].strip())}}}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['portfolio'])}}}{{\faIcon{{globe}}\ \textbf{{{port_disp}}}}}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{{li_disp}}}}}}}")
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{{gh_disp}}}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{{orcid_disp}}}}}}}")
    if links.get("scholar"):
        sc_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['scholar'])}}}{{\faIcon{{google}}\ \textbf{{{sc_disp}}}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{{lattes_disp}}}}}}}")
    if cv.get("location"):
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(cv["location"].strip())
        contact_parts.append(rf"\mbox{{\href{{{escape_url(maps_url)}}}{{\faIcon{{map-marker-alt}}\ {escape_latex(cv['location'].strip())}}}}}")

    if len(contact_parts) > 4:
        mid = (len(contact_parts) + 1) // 2
        row1 = " \\quad | \\quad ".join(contact_parts[:mid])
        row2 = " \\quad | \\quad ".join(contact_parts[mid:])
        contact_str = f"{row1}\\\\[3pt]\n    {row2}"
    else:
        contact_str = " \\quad | \\quad ".join(contact_parts)

    header_tex = rf"""\begin{{center}}
    {{\LARGE\bfseries\color{{sidecolor}} {name}}}\\[3pt]
    {{\large\bfseries\color{{accent}} {title}}}\\[5pt]
    {{\footnotesize {contact_str}}}
\end{{center}}
\vspace{{2pt}}
\hrule height 0.75pt
\vspace{{5pt}}"""

    blocks: List[str] = []

    # 1. Summary
    if cv.get("summary"):
        sum_title = "PROFESSIONAL SUMMARY" if is_en else "RESUMO PROFISSIONAL"
        blocks.append(
            rf"\section*{{{sum_title}}}"
            + "\n"
            + rf"{{\normalsize {escape_latex(cv['summary'])}}}"
        )

    # 2. Dedicated Core Competencies & Keywords (Crucial for AI screening / ATS matching)
    skills = cv.get("skills") or []
    if skills:
        kw_title = r"CORE COMPETENCIES \& KEYWORDS" if is_en else r"COMPETÊNCIAS PRINCIPAIS \& PALAVRAS-CHAVE"
        kw_lines = [rf"\section*{{{kw_title}}}", r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]"]
        for sk in skills:
            if isinstance(sk, dict):
                cat = escape_latex(sk.get("category"))
                items = escape_latex(sk.get("items"))
            else:
                cat = ""
                items = escape_latex(str(sk).strip())
            if items:
                kw_lines.append(rf"    \item \textbf{{{cat}:}} {items}" if cat else rf"    \item {items}")
        kw_lines.append(r"\end{itemize}")
        blocks.append("\n".join(kw_lines))

    # 3. Experience
    exps = cv.get("experience") or []
    if exps:
        exp_title = "PROFESSIONAL EXPERIENCE" if is_en else "EXPERIÊNCIA PROFISSIONAL"
        xp_lines = [rf"\section*{{{exp_title}}}"]
        for xp in exps:
            role = escape_latex(xp.get("role"))
            org = escape_latex(xp.get("organization"))
            per = escape_latex(xp.get("period"))
            bullets = [escape_latex(sanitize_experience_description(b, lang=lang)) for b in (xp.get("bullets") or []) if str(b).strip()]
            head_txt = f"{role} | {org}" if org else role
            xp_lines.append(rf"\noindent\textbf{{{head_txt}}} \hfill \textbf{{{per}}}")
            if bullets:
                xp_lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
                for b in bullets:
                    xp_lines.append(rf"    \item {b}")
                xp_lines.append(r"\end{itemize}")
                xp_lines.append(r"\vspace{3pt}")
            else:
                xp_lines.append(r"\par\vspace{3pt}")
        blocks.append("\n".join(xp_lines))

    # 4. Education
    edus = cv.get("education") or []
    if edus:
        edu_title = "EDUCATION" if is_en else "FORMAÇÃO ACADÊMICA"
        ed_lines = [rf"\section*{{{edu_title}}}"]
        for ed in edus:
            deg = escape_latex(ed.get("degree"))
            inst = escape_latex(ed.get("institution"))
            per = escape_latex(ed.get("period"))
            det = escape_latex(ed.get("details"))
            inst_txt = f" --- {inst}" if inst else ""
            ed_lines.append(rf"\noindent\textbf{{{deg}}}{inst_txt} \hfill \textbf{{{per}}}")
            if det:
                ed_lines.append(rf"\par{{\small {det}}}\par\vspace{{4pt}}")
            else:
                ed_lines.append(r"\par\vspace{4pt}")
        blocks.append("\n\n".join(ed_lines))

    # 5. Projects & 6. Publications (priorizados conforme finalidade)
    proj_block_ai = ""
    projs = cv.get("projects") or []
    if projs:
        proj_title = "TECHNICAL PROJECTS" if is_en else "PROJETOS TÉCNICOS"
        pj_lines = [rf"\section*{{{proj_title}}}"]
        for pj in projs:
            nm = escape_latex(pj.get("name"))
            tech = escape_latex(pj.get("tech"))
            url = (pj.get("url") or "").strip()
            desc = escape_latex(sanitize_project_description(pj.get("description"), lang))
            if url and url.startswith("http"):
                nm_head = rf"\href{{{escape_url(url)}}}{{\textbf{{{nm}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
            else:
                nm_head = rf"\textbf{{{nm}}}"
            tech_txt = f" [Stack: {tech}]" if tech else ""
            pj_lines.append(rf"\noindent{nm_head}{tech_txt}")
            if desc:
                pj_lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
                pj_lines.append(rf"    \item {desc}")
                pj_lines.append(r"\end{itemize}")
                pj_lines.append(r"\vspace{2pt}")
            else:
                pj_lines.append(r"\par\vspace{2pt}")
        proj_block_ai = "\n".join(pj_lines)

    pub_block_ai = ""
    pubs = cv.get("publications") or []
    if pubs:
        pub_title = "PUBLICATIONS" if is_en else "PUBLICAÇÕES"
        pub_block_ai = rf"\section*{{{pub_title}}}" + "\n" + _build_publications_block(pubs, lang).replace(rf"\section*{{{t['sec_publications']}}}", "").strip()

    if resume_type == "academico":
        for b in (pub_block_ai, proj_block_ai):
            if b:
                blocks.append(b)
    else:
        for b in (proj_block_ai, pub_block_ai):
            if b:
                blocks.append(b)

    # 7. Certifications & Awards
    clean_awards = sanitize_awards(cv.get("awards"), lang=lang)
    if clean_awards:
        aw_title = r"CERTIFICATIONS \& AWARDS" if is_en else r"CERTIFICAÇÕES \& PRÊMIOS"
        aw_lines = [rf"\section*{{{aw_title}}}", r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]"]
        for aw in clean_awards:
            aw_lines.append(rf"    \item {escape_latex(aw)}")
        aw_lines.append(r"\end{itemize}")
        blocks.append("\n".join(aw_lines))

    # 8. Languages
    langs = cv.get("languages") or []
    if langs:
        lg_title = "LANGUAGES" if is_en else "IDIOMAS"
        lg_str = " $\\cdot$ ".join(escape_latex(x) for x in langs if str(x).strip())
        blocks.append(rf"\section*{{{lg_title}}}" + "\n" + lg_str)

    body_tex = "\n\n".join(b for b in blocks if b)

    return rf"""% Template AI & ATS Max-Readability (LLM & Neural ATS Evaluators)
\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{lmodern}}
\usepackage[margin=0.6in]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{accent}}{{HTML}}{{1E293B}}
\definecolor{{sidecolor}}{{HTML}}{{0F172A}}
\definecolor{{graytext}}{{HTML}}{{334155}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{\section}}{{\normalsize\bfseries\scshape\color{{sidecolor}}}}{{}}{{0em}}{{}}[\vspace{{1pt}}\titlerule]
\titlespacing*{{\section}}{{0pt}}{{8pt}}{{3pt}}

\begin{{document}}
{header_tex}
{body_tex}
\end{{document}}
"""


def _render_nico_krieger(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    """Renderiza o modelo 'Modelo Nico Krieger' (https://www.overleaf.com/latex/templates/my-resume/rqzfybxqvpny)."""
    t = LATEX_I18N[normalize_lang(lang)]
    is_en = normalize_lang(lang) == "en-us"
    raw_name = cv.get("name") or t["default_candidate"]
    default_tl = t["default_researcher"] if resume_type == "academico" else t["default_tech_title"]
    role = escape_latex(cv.get("title") or default_tl)

    # 1. Header (Name, Title, Tagline, optional Photo)
    tagline_raw = cv.get("summary") or ""
    tagline_short = escape_latex(truncate_at_clause_boundary(tagline_raw, 180)) if tagline_raw else ""

    if photo_filename:
        header_tex = rf"""\begin{{tcolorbox}}[
    enhanced,
    colback=headerbg,
    colframe=headerbg,
    arc=0mm,
    left=10mm,
    right=10mm,
    top=4mm,
    bottom=4mm,
    boxrule=0mm,
    width=\paperwidth
]
\begin{{minipage}}[c]{{0.78\linewidth}}
    {{\LARGE\bfseries\color{{white}} {escape_latex(raw_name)}}}\\[2pt]
    {{\normalsize\color{{white!90}} {role}}}\\[2pt]
    {{\small\color{{white!75}} {tagline_short}}}
\end{{minipage}}%
\hfill
\begin{{minipage}}[c]{{0.18\linewidth}}
    \raggedleft
    \includegraphics[width=2.2cm,height=2.2cm,keepaspectratio]{{{photo_filename}}}
\end{{minipage}}
\end{{tcolorbox}}"""
    else:
        header_tex = rf"""\begin{{tcolorbox}}[
    enhanced,
    colback=headerbg,
    colframe=headerbg,
    arc=0mm,
    left=10mm,
    right=10mm,
    top=4mm,
    bottom=4mm,
    boxrule=0mm,
    width=\paperwidth
]
\begin{{minipage}}[c]{{\linewidth}}
    {{\LARGE\bfseries\color{{white}} {escape_latex(raw_name)}}}\\[2pt]
    {{\normalsize\color{{white!90}} {role}}}\\[2pt]
    {{\small\color{{white!75}} {tagline_short}}}
\end{{minipage}}
\end{{tcolorbox}}"""

    # 2. Contacts (Strictly: email -> phone -> location -> portfolio -> linkedin -> github -> orcid -> lattes)
    sidebar_contacts: List[str] = []
    clean_em = (cv.get("email") or links.get("email") or "").strip()
    if clean_em:
        sidebar_contacts.append(rf"\faIcon{{envelope}}\ \href{{{escape_url('mailto:' + clean_em)}}}{{{escape_latex(clean_em)}}}")
    if cv.get("phone"):
        sidebar_contacts.append(rf"\faIcon{{phone}}\ {escape_latex(cv['phone'])}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        sidebar_contacts.append(rf"\href{{{escape_url(links['portfolio'])}}}{{\faIcon{{globe}}\ \textbf{{{port_disp}}}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=raw_name))
        sidebar_contacts.append(rf"\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{{li_disp}}}}}")
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=raw_name))
        sidebar_contacts.append(rf"\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{{gh_disp}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=raw_name))
        sidebar_contacts.append(rf"\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{{orcid_disp}}}}}")
    if links.get("scholar"):
        sc_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=raw_name))
        sidebar_contacts.append(rf"\href{{{escape_url(links['scholar'])}}}{{\faIcon{{google}}\ \textbf{{{sc_disp}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=raw_name))
        sidebar_contacts.append(rf"\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{{lattes_disp}}}}}")
    if cv.get("location"):
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(cv["location"].strip())
        sidebar_contacts.append(rf"\href{{{escape_url(maps_url)}}}{{\faIcon{{map-marker-alt}}\ {escape_latex(cv['location'].strip())}}}")

    contact_lbl = "CONTACT" if is_en else "CONTATO"
    contact_body = "\\\\[3pt]\n    ".join(sidebar_contacts) if sidebar_contacts else ""
    contact_block = rf"""{{\large\bfseries\color{{accent}} {contact_lbl}}}\\[-3pt]
\rule{{\linewidth}}{{0.8pt}}\nopagebreak\\[3pt]
\small
{contact_body}"""

    # 3. Education in Sidebar (transferred to left column for visual balance)
    edus = (cv.get("education") or [])[:3]
    if edus:
        edu_lbl = "EDUCATION" if is_en else "FORMAÇÃO ACADÊMICA"
        ed_lines = [rf"{{\large\bfseries\color{{accent}} {edu_lbl}}}\\[-3pt]", r"\rule{\linewidth}{0.8pt}\nopagebreak\\[3pt]"]
        for ed in edus:
            deg = escape_latex(ed.get("degree"))
            inst = escape_latex(ed.get("institution"))
            per_ed = escape_latex(ed.get("period"))
            det = escape_latex(ed.get("details"))
            date_tex = rf"{{\footnotesize\color{{graytext}}\faIcon{{calendar-alt}}\ {per_ed}}}" if per_ed else ""
            if deg:
                ed_lines.append(rf"\textbf{{\small {deg}}}\\[0.5pt]")
            if inst:
                ed_lines.append(rf"{{\small\color{{darktext}} {inst}}}\\[0.5pt]")
            if date_tex:
                ed_lines.append(rf"{date_tex}\\[1.5pt]")
            if det:
                ed_lines.append(rf"{{\footnotesize {det}}}\\[2pt]")
            else:
                ed_lines.append(r"\vspace{1.5pt}")
        edu_block = "\n".join(ed_lines)
    else:
        edu_block = ""

    # 4. Skills with 5-dot rating (or About Me summary fallback to utilize sidebar space richly)
    skill_lbl = "SKILLS" if is_en else "HABILIDADES"
    skill_lines: List[str] = [rf"{{\large\bfseries\color{{accent}} {skill_lbl}}}\\[-3pt]", r"\rule{\linewidth}{0.8pt}\nopagebreak\\[3pt]"]
    skills = cv.get("skills") or []
    if skills:
        for sk in skills:
            if isinstance(sk, dict):
                cat = escape_latex(sk.get("category"))
                raw_items = str(sk.get("items") or "")
                parts = [p.strip() for p in raw_items.split(",") if p.strip()]
                if parts:
                    if cat:
                        skill_lines.append(rf"{{\small\bfseries\color{{darktext}} {cat}}}\\[1.5pt]")
                    skill_lines.append(rf"{{\small {', '.join(escape_latex(p) for p in parts)}}}\par\vspace{{2pt}}")
                    skill_lines.append(r"\vspace{2pt}")
            elif isinstance(sk, str) and sk.strip():
                parts = [p.strip() for p in sk.split(",") if p.strip()]
                skill_lines.append(rf"{{\small {', '.join(escape_latex(p) for p in parts)}}}\par\vspace{{2pt}}")
        skill_block = "\n".join(skill_lines)
    elif cv.get("summary"):
        sum_lbl = "ABOUT ME" if is_en else "SOBRE MIM"
        sum_raw = escape_latex(cv["summary"].strip())
        if len(sum_raw) > 320:
            sum_raw = escape_latex(truncate_at_clause_boundary(cv["summary"].strip(), 320))
        skill_block = rf"""{{\large\bfseries\color{{accent}} {sum_lbl}}}\\[-3pt]
\rule{{\linewidth}}{{0.8pt}}\nopagebreak\\[3pt]
{{\small {sum_raw}}}"""
    else:
        skill_block = ""

    # 5. Languages with 6-dot CEFR rating (A1 to C2)
    lang_lbl = "LANGUAGES" if is_en else "IDIOMAS"
    lang_lines: List[str] = [rf"{{\large\bfseries\color{{accent}} {lang_lbl}}}\\[-3pt]", r"\rule{\linewidth}{0.8pt}\nopagebreak\\[3pt]"]
    languages = cv.get("languages") or []
    if languages:
        for idx, lg in enumerate(languages):
            lg_str = str(lg).strip()
            if not lg_str:
                continue
            clean_name, rating = get_language_proficiency_score_6(lg_str, default_first=(idx == 0))
            lang_lines.append(rf"{{\small\textbf{{{escape_latex(clean_name)}}}}} \hfill \langdots{{{rating}}}\\[2.5pt]")
        lang_block = "\n".join(lang_lines)
    else:
        lang_block = ""

    # 6. Certifications & Awards in Sidebar
    clean_awards = sanitize_awards(cv.get("awards"), lang=lang)
    aw_lbl = r"AWARDS \& HONORS" if is_en else r"PRÊMIOS \& DESTAQUES"
    if clean_awards:
        aw_lines = [rf"{{\large\bfseries\color{{accent}} {aw_lbl}}}\\[-3pt]", r"\rule{\linewidth}{0.8pt}\nopagebreak\\[3pt]"]
        for aw in clean_awards[:6]:
            aw_lines.append(rf"{{\small $\cdot$ {escape_latex(aw)}}}\\[2pt]")
        awards_block = "\n".join(aw_lines)
    else:
        awards_block = ""

    sidebar_sections = [s for s in (contact_block, edu_block, skill_block, lang_block, awards_block) if s]
    sidebar_gap = r"\vspace{6pt}" if len(sidebar_sections) <= 4 else r"\vspace{4pt}"
    sidebar_content = f"\n\n{sidebar_gap}\n\n".join(sidebar_sections)

    # 7. Main Column: Experience, Projects, Publications (Education moved to sidebar)
    pubs_all = cv.get("publications") or []
    projs_all = cv.get("projects") or []

    # Alocação dinâmica de capacidade vertical para a coluna principal
    max_exp, max_proj, max_pubs = _allocate_single_page_budget(
        len(cv.get("experience") or []),
        len(projs_all),
        len(pubs_all),
        budget=44.0,
        weight_exp=4.0,
        weight_proj=2.8,
        weight_pub=2.2,
        resume_type=resume_type,
    )

    main_sections: List[str] = []

    # Experience
    exps = (cv.get("experience") or [])[:max_exp]
    total_main_items = len(exps) + min(len(projs_all), max_proj) + min(len(pubs_all), max_pubs)
    is_sparse = total_main_items <= 10
    xp_gap = r"\vspace{2.5pt}" if is_sparse else r"\vspace{2pt}"
    pub_gap = r"\par\vspace{2pt}" if is_sparse else r"\par\vspace{1.5pt}"
    sec_gap = r"\vspace{4.5pt}" if is_sparse else r"\vspace{2.5pt}"

    if exps:
        exp_title = "PROFESSIONAL EXPERIENCE" if is_en else "EXPERIÊNCIA PROFISSIONAL"
        xp_lines = [rf"{{\large\bfseries\color{{accent}} {exp_title}}}\\[-3pt]", r"\rule{\linewidth}{0.8pt}\nopagebreak\\[3pt]"]
        for xp in exps:
            role_xp = escape_latex(xp.get("role"))
            org_xp = escape_latex(xp.get("organization"))
            per_xp = escape_latex(xp.get("period"))
            raw_bullets = xp.get("bullets") or []
            if not raw_bullets and xp.get("description"):
                raw_bullets = [xp["description"]]
            bullets = [escape_latex(sanitize_experience_description(b, lang=lang)) for b in raw_bullets if str(b).strip()]
            date_tex = rf"{{\footnotesize\color{{graytext}}\faIcon{{calendar-alt}}\ {per_xp}}}" if per_xp else ""
            if org_xp:
                xp_lines.append(rf"\textbf{{{role_xp}}} \hfill {date_tex}\\[0.5pt]")
                xp_lines.append(rf"{{\color{{accent}}\textbf{{{org_xp}}}}}")
            else:
                xp_lines.append(rf"\textbf{{{role_xp}}} \hfill {date_tex}")
            if bullets:
                xp_lines.append(r"\begin{itemize}[leftmargin=1.1em,noitemsep,topsep=0pt,partopsep=0pt,parsep=0pt,before=\vspace{-2.5pt}]")
                for b in bullets:
                    xp_lines.append(rf"    \item {b}")
                xp_lines.append(r"\end{itemize}")
            else:
                xp_lines.append(r"\vspace{1.5pt}")
            if xp != exps[-1]:
                xp_lines.append(xp_gap)
        main_sections.append("\n".join(xp_lines))

    # Projects
    proj_sec_nico = ""
    projs = projs_all[:max_proj]
    if projs:
        proj_title = "TECHNICAL PROJECTS" if is_en else "PROJETOS TÉCNICOS"
        pj_lines = [rf"{{\large\bfseries\color{{accent}} {proj_title}}}\\[-3pt]", r"\rule{\linewidth}{0.8pt}\nopagebreak\\[3pt]"]
        for pj in projs:
            nm = escape_latex(pj.get("name"))
            tech = escape_latex(pj.get("tech"))
            url = (pj.get("url") or "").strip()
            desc = escape_latex(sanitize_project_description(pj.get("description"), lang))
            if len(desc) > 130:
                desc = escape_latex(finalize_project_description(truncate_at_clause_boundary(sanitize_project_description(pj.get("description"), lang), 130)))
            if url and url.startswith("http"):
                nm_head = rf"\textbf{{\href{{{escape_url(url)}}}{{{nm}\ \footnotesize\faIcon{{external-link-alt}}}}}}"
            else:
                nm_head = rf"\textbf{{{nm}}}"
            pj_lines.append(rf"{nm_head}\\[0.5pt]")
            if tech:
                pj_lines.append(rf"{{\small\color{{graytext}}\textbf{{Stack:}} {tech}}}\\[0.5pt]")
            if desc:
                pj_lines.append(rf"{{\small {desc}}}\par\vspace{{1.5pt}}")
            else:
                pj_lines.append(r"\vspace{1.5pt}")
            if pj != projs[-1]:
                pj_lines.append(r"\vspace{1.5pt}")
        proj_sec_nico = "\n".join(pj_lines)

    # Publications
    pub_sec_nico = ""
    pubs = pubs_all[:max_pubs]
    if max_pubs > 0 and pubs:
        pub_title = "PUBLICATIONS" if is_en else "PUBLICAÇÕES"
        pb_lines = [rf"{{\large\bfseries\color{{accent}} {pub_title}}}\\[-3pt]", r"\rule{\linewidth}{0.8pt}\nopagebreak\\[3pt]"]
        for idx, pb in enumerate(pubs):
            raw_t_pb = pb.get("title") or ""
            title_pb = escape_latex(raw_t_pb)
            auth_pb = escape_latex(pb.get("authors"))
            venue_pb = escape_latex(clean_publication_venue(pb.get("venue") or "", raw_t_pb))
            yr_pb = escape_latex(pb.get("year"))
            doi_pb = (pb.get("doi") or "").strip()

            meta_items = []
            if auth_pb:
                meta_items.append(auth_pb)
            if venue_pb and yr_pb:
                meta_items.append(f"{venue_pb} ({yr_pb})")
            elif venue_pb or yr_pb:
                meta_items.append(venue_pb or yr_pb)
            if doi_pb:
                clean_doi = doi_pb.replace("https://doi.org/", "").replace("http://dx.doi.org/", "").strip()
                doi_url = f"https://doi.org/{clean_doi}"
                meta_items.append(rf"\href{{{escape_url(doi_url)}}}{{\faIcon{{link}}\ DOI: {escape_latex(clean_doi)}}}")
            meta_str = ", ".join(meta_items)
            is_last = (idx == len(pubs) - 1)
            trail = "" if is_last else pub_gap
            pb_lines.append(rf"\textbf{{{title_pb}}}\\[0.5pt]" + (rf"{{\small {meta_str}}}{trail}" if meta_str else trail))
        pub_sec_nico = "\n".join(pb_lines)

    if resume_type == "academico":
        for sec_s in (pub_sec_nico, proj_sec_nico):
            if sec_s:
                main_sections.append(sec_s)
    else:
        for sec_s in (proj_sec_nico, pub_sec_nico):
            if sec_s:
                main_sections.append(sec_s)

    main_content = f"\n\n{sec_gap}\n\n".join(main_sections)

    return rf"""% Template Nico Krieger (my-resume) - Full-Width Dark Header & Two-Column Highlight Sidebar
\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage[left=0cm,right=0.9cm,top=0cm,bottom=0.45cm,noheadfoot]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{paracol}}
\usepackage{{tikz}}
\usepackage[skins]{{tcolorbox}}
\usepackage{{fontawesome5}}
\usepackage{{enumitem}}
\usepackage[default]{{sourcesanspro}}
\usepackage[hidelinks]{{hyperref}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\definecolor{{headerbg}}{{HTML}}{{212529}}
\definecolor{{sidebg}}{{HTML}}{{F8F9FA}}
\definecolor{{accent}}{{HTML}}{{DC3545}}
\definecolor{{darktext}}{{HTML}}{{212529}}
\definecolor{{graytext}}{{HTML}}{{6C757D}}
\definecolor{{lightgray}}{{HTML}}{{DEE2E6}}

\renewcommand{{\familydefault}}{{\sfdefault}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\newcommand{{\skilldots}}[1]{{%
  \begin{{tikzpicture}}[baseline=-0.35ex]%
    \foreach \x in {{1,...,5}}{{%
      \ifnum\x>#1\relax%
        \fill[lightgray] (\x*0.28cm,0) circle (2.2pt);%
      \else%
        \fill[accent] (\x*0.28cm,0) circle (2.2pt);%
      \fi%
    }}%
  \end{{tikzpicture}}%
}}

\newcommand{{\langdots}}[1]{{%
  \begin{{tikzpicture}}[baseline=-0.35ex]%
    \foreach \x in {{1,...,6}}{{%
      \ifnum\x>#1\relax%
        \fill[lightgray] (\x*0.24cm,0) circle (2.0pt);%
      \else%
        \fill[accent] (\x*0.24cm,0) circle (2.0pt);%
      \fi%
    }}%
  \end{{tikzpicture}}%
}}

\begin{{document}}
\noindent
\makebox[\textwidth][l]{{%
{header_tex}
}}

\vspace{{1.5mm}}

\setcolumnwidth{{68mm, 130mm}}
\setlength{{\columnsep}}{{5mm}}
\backgroundcolor{{c[0]}}{{sidebg}}

\begin{{paracol}}{{2}}
\hskip 6mm
\begin{{minipage}}{{58mm}}
\vspace{{1mm}}
{sidebar_content}
\end{{minipage}}

\switchcolumn

\vspace{{1mm}}
{main_content}

\end{{paracol}}

\end{{document}}
"""


def _extract_bubble_initials(name: str) -> str:
    """Extrai até 2 iniciais maiúsculas para o nó circular do cabeçalho."""
    parts = [p for p in name.split() if p]
    if not parts:
        return "CV"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _parse_bubble_dates(period_str: str) -> tuple[str, str]:
    """Separa período em data inicial e final para alinhamento na linha do tempo."""
    if not period_str:
        return "", ""
    parts = re.split(r"\s*(?:--|—|–|-|\ba\b|\bto\b)\s*", str(period_str).strip())
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()
    return parts[0].strip(), ""


def _parse_bubble_language(lg: Any, idx: int = 0, is_en: bool = False) -> tuple[str, str, float]:
    """Extrai (nome_limpo, nivel_formatado, fracao_barra) para idiomas no BubbleCV."""
    if isinstance(lg, dict):
        raw_name = str(lg.get("language") or lg.get("name") or "").strip()
        raw_lvl = str(lg.get("level") or "").strip()
        combined = f"{raw_name} ({raw_lvl})" if raw_lvl else raw_name
    else:
        combined = str(lg or "").strip()
    if not combined:
        return ("", "", 0.50)

    clean_name, score_6 = get_language_proficiency_score_6(combined, default_first=(idx == 0))
    low = combined.lower()
    is_native = any(k in low for k in ("nativo", "native", "materno", "mother tongue"))

    level_map_pt = {
        6: "Nativo" if is_native else "Fluente",
        5: "Avançado",
        4: "Intermediário Sup.",
        3: "Intermediário",
        2: "Básico",
        1: "Iniciante",
    }
    level_map_en = {
        6: "Native" if is_native else "Fluent",
        5: "Advanced",
        4: "Upper Interm.",
        3: "Intermediate",
        2: "Basic",
        1: "Beginner",
    }
    frac_map = {
        6: 1.00,
        5: 0.83,
        4: 0.67,
        3: 0.50,
        2: 0.33,
        1: 0.18,
    }
    lvl_label = (level_map_en if is_en else level_map_pt).get(score_6, "Intermediário" if not is_en else "Intermediate")
    frac = frac_map.get(score_6, 0.50)
    return (clean_name, lvl_label, frac)


def _render_bubble(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str = "profissional",
    photo_filename: str | None = None,
    lang: str = "pt-br",
) -> str:
    """Renderiza o modelo 'BubbleCV' (https://www.overleaf.com/latex/templates/bubblecv/bcynnjktwqsx).

    Baseado no design de Mateusz Baran com linha do tempo contínua em segundo plano,
    bolhas circulares TikZ para eventos e seções, barras de progresso para competências/idiomas
    e alocação dinâmica estrita para preservação de página única.
    """
    t = LATEX_I18N[normalize_lang(lang)]
    is_en = normalize_lang(lang) == "en-us"
    raw_name = cv.get("name") or t["default_candidate"]
    default_tl = t["default_researcher"] if resume_type == "academico" else t["default_tech_title"]
    role = escape_latex(cv.get("title") or default_tl)

    # 1. Header (exibe círculo de foto SOMENTE se photo_filename for fornecido)
    if photo_filename:
        avatar_tikz = rf"""\begin{{tikzpicture}}[baseline=-0.5ex]%
    \draw[draw=cvbordercolor, fill=accent, line width=\cvavatarborderwidth mm] (0,0) circle (\dimexpr\cvavatarradius mm - \cvavatarborderwidth mm / 2\relax);%
    \clip (0,0) circle (\dimexpr\cvavatarradius mm - \cvavatarborderwidth mm\relax);%
    \node at (0,0) {{\includegraphics[width=\dimexpr\cvavatarradius mm * 2\relax,height=\dimexpr\cvavatarradius mm * 2\relax,keepaspectratio]{{{photo_filename}}}}};%
  \end{{tikzpicture}}%"""
        header_tex = rf"""\vspace*{{-4mm}}%
\noindent%
\hspace{{-\timelinespace mm}}%
\hspace{{-\cvavatarradius mm}}%
\begin{{minipage}}[c]{{\dimexpr(\cvavatarradius mm * 2)}}%
  {avatar_tikz}
\end{{minipage}}%
\hspace{{5mm}}%
\begin{{minipage}}[c]{{\dimexpr(\linewidth + \timelinespace mm - \cvavatarradius mm - 5mm)}}%
  {{\fontsize{{20pt}}{{23pt}}\bfseries\color{{accent}} {escape_latex(raw_name)}}}\\[3pt]%
  {{\fontsize{{11pt}}{{13pt}}\itshape\color{{subaccent}} {role}}}%
\end{{minipage}}%"""
        timeline_height_mm = 258
    else:
        header_tex = rf"""\vspace*{{-2mm}}%
\noindent%
\hspace{{-\timelinespace mm}}%
\hspace{{-\cvmainbubbleradius mm}}%
\begin{{minipage}}[c]{{\dimexpr(\linewidth + \timelinespace mm + \cvmainbubbleradius mm)}}%
  {{\fontsize{{22pt}}{{25pt}}\bfseries\color{{accent}} {escape_latex(raw_name)}}}\\[3pt]%
  {{\fontsize{{11pt}}{{13pt}}\itshape\color{{subaccent}} {role}}}%
\end{{minipage}}%
\vspace{{2mm}}%"""
        timeline_height_mm = 251

    # 2. Main Column: Experience, Education, Projects/Publications
    exps = cv.get("experience") or []
    projs = cv.get("projects") or []
    pubs = cv.get("publications") or []
    edus = cv.get("education") or []

    n_exp, n_proj, n_pub = _allocate_single_page_budget(
        len(exps), len(projs), len(pubs), budget=44.0, weight_exp=5.0, weight_proj=4.5, weight_pub=2.2, resume_type=resume_type
    )

    exp_sec_items: List[str] = []
    if n_exp > 0:
        exp_lbl = "EXPERIENCE" if is_en else "EXPERIÊNCIA PROFISSIONAL"
        exp_sec_items.append(rf"\bubblemaintitle{{\faBriefcase}}{{{exp_lbl}}}")
        for exp in exps[:n_exp]:
            r_txt = escape_latex(exp.get("role") or "")
            c_txt = escape_latex(exp.get("company") or exp.get("organization") or "")
            start_d, end_d = _parse_bubble_dates(exp.get("period") or "")
            raw_bullets = exp.get("bullets") or []
            if not raw_bullets and exp.get("description"):
                raw_bullets = [l.strip(" \t•-*") for l in str(exp["description"]).splitlines() if l.strip(" \t•-*")]
            clean_bullets = [
                escape_latex(sanitize_experience_description(b, lang=lang))
                for b in raw_bullets
                if str(b).strip()
            ]
            if clean_bullets:
                body = "\\begin{itemize}\n" + "\n".join(rf"  \item {b}" for b in clean_bullets) + "\n\\end{itemize}"
            else:
                body = ""
            exp_sec_items.append(rf"\bubbleevent{{{escape_latex(start_d)}}}{{{escape_latex(end_d)}}}{{{r_txt}}}{{{c_txt}}}{{{body}}}")

    edu_sec_items: List[str] = []
    if edus:
        edu_lbl = "EDUCATION" if is_en else "FORMAÇÃO ACADÊMICA"
        edu_sec_items.append(rf"\bubblemaintitle{{\faGraduationCap}}{{{edu_lbl}}}")
        for ed in edus[:2]:
            deg = escape_latex(ed.get("degree") or "")
            inst = escape_latex(ed.get("institution") or "")
            det = escape_latex(ed.get("details") or "")
            start_d, end_d = _parse_bubble_dates(ed.get("period") or "")
            body = rf"\textit{{{det}}}" if det else ""
            edu_sec_items.append(rf"\bubbleevent{{{escape_latex(start_d)}}}{{{escape_latex(end_d)}}}{{{deg}}}{{{inst}}}{{{body}}}")

    proj_sec_items: List[str] = []
    if n_proj > 0:
        proj_lbl = "KEY PROJECTS" if is_en else "PROJETOS RELEVANTES"
        proj_sec_items.append(rf"\bubblemaintitle{{\faRocket}}{{{proj_lbl}}}")
        for p in projs[:n_proj]:
            p_name = escape_latex(p.get("name") or "")
            p_url = (p.get("url") or "").strip()
            if p_url and p_url.startswith("http"):
                p_head = rf"\href{{{escape_url(p_url)}}}{{{p_name}\ \footnotesize\faIcon{{external-link-alt}}}}"
            else:
                p_head = p_name
            p_tech = p.get("technologies") or p.get("tech") or ""
            if isinstance(p_tech, list):
                tech_str = ", ".join(p_tech)
            else:
                tech_str = str(p_tech)
            tech_disp = rf"\textbf{{Stack:}} {escape_latex(tech_str)}" if tech_str else ""
            p_desc = escape_latex(sanitize_project_description(p.get("description") or "", lang))
            if len(p_desc) > 130:
                p_desc = escape_latex(finalize_project_description(truncate_at_clause_boundary(sanitize_project_description(p.get("description") or "", lang), 130)))
            proj_sec_items.append(rf"\bubbleevent{{\faCode}}{{}}{{{p_head}}}{{{tech_disp}}}{{{p_desc}}}")

    pub_sec_items: List[str] = []
    if n_pub > 0:
        pub_lbl = "PUBLICATIONS" if is_en else "PUBLICAÇÕES CIENTÍFICAS"
        pub_sec_items.append(rf"\bubblemaintitle{{\faBook}}{{{pub_lbl}}}")
        for pb in pubs[:n_pub]:
            raw_t_pub = pb.get("title") or ""
            t_pub = escape_latex(raw_t_pub).strip()
            t_pub = re.sub(r"-(Resumo Estendido|Short Paper|Extended Abstract)\b", r" (\1)", t_pub, flags=re.IGNORECASE)
            v_pub = escape_latex(clean_publication_venue(pb.get("venue") or "", raw_t_pub)).strip()
            y_pub = escape_latex(str(pb.get("year") or ""))
            doi_pub = (pb.get("doi") or "").strip()
            pub_url = (pb.get("url") or "").strip()
            if not pub_url and doi_pub:
                pub_url = doi_pub if doi_pub.startswith("http") else f"https://doi.org/{doi_pub}"
            if pub_url and pub_url.startswith("http"):
                t_head = rf"\href{{{escape_url(pub_url)}}}{{{t_pub}\ \footnotesize\faIcon{{external-link-alt}}}}"
            else:
                t_head = t_pub
            pub_sec_items.append(rf"\bubbleevent{{{y_pub}}}{{}}{{{t_head}}}{{{v_pub}}}{{}}")

    main_items: List[str] = []
    if resume_type == "academico":
        for sec_group in (edu_sec_items, exp_sec_items, pub_sec_items, proj_sec_items):
            main_items.extend(sec_group)
    else:
        for sec_group in (exp_sec_items, edu_sec_items, proj_sec_items, pub_sec_items):
            main_items.extend(sec_group)

    main_content = "\n\n".join(main_items)

    # 3. Sidebar Column: Contact, Profile, Skills, Languages, Awards
    side_items: List[str] = []

    # Contacts
    cnt_lbl = "CONTACT" if is_en else "CONTATO"
    side_items.append(rf"\bubblesidebartitle{{\faAddressCard}}{{{cnt_lbl}}}")
    clean_em = (cv.get("email") or links.get("email") or "").strip()
    if clean_em:
        side_items.append(rf"\bubblesideitem{{\faEnvelope}}{{\href{{{escape_url('mailto:' + clean_em)}}}{{{escape_latex(clean_em)}}}}}")
    if cv.get("phone"):
        side_items.append(rf"\bubblesideitem{{\faPhone}}{{{escape_latex(cv['phone'])}}}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        side_items.append(rf"\bubblesideitem{{\faGlobe}}{{\href{{{escape_url(links['portfolio'])}}}{{\textbf{{{port_disp}}}}}}}")
    if cv.get("location"):
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(cv["location"].strip())
        side_items.append(rf"\bubblesideitem{{\faMapMarker*}}{{\href{{{escape_url(maps_url)}}}{{{escape_latex(cv['location'])}}}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=raw_name))
        side_items.append(rf"\bubblesideitem{{\faLinkedin}}{{\href{{{escape_url(links['linkedin'])}}}{{\textbf{{{li_disp}}}}}}}")
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=raw_name))
        side_items.append(rf"\bubblesideitem{{\faGithub}}{{\href{{{escape_url(links['github'])}}}{{\textbf{{{gh_disp}}}}}}}")
    if links.get("scholar"):
        scholar_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=raw_name))
        side_items.append(rf"\bubblesideitem{{\faIcon{{google}}}}{{\href{{{escape_url(links['scholar'])}}}{{\textbf{{{scholar_disp}}}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=raw_name))
        side_items.append(rf"\bubblesideitem{{\faOrcid}}{{\href{{{escape_url(links['orcid'])}}}{{\textbf{{{orcid_disp}}}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=raw_name))
        side_items.append(rf"\bubblesideitem{{\faGraduationCap}}{{\href{{{escape_url(links['lattes'])}}}{{\textbf{{{lattes_disp}}}}}}}")

    # Summary in Sidebar if present
    summary_raw = cv.get("summary") or ""
    if summary_raw.strip():
        prof_lbl = "PROFILE" if is_en else "PERFIL"
        sum_disp = escape_latex(summary_raw.strip())
        if len(sum_disp) > 220:
            sum_disp = escape_latex(truncate_at_clause_boundary(summary_raw.strip(), 220))
        side_items.append(rf"\bubblesidebartitle{{\faUser}}{{{prof_lbl}}}")
        side_items.append(rf"\noindent{{\raggedright\small\color{{black!85}} {sum_disp}\par}}\vspace{{2mm}}")

    # Skills with progress bars
    skills = cv.get("skills") or []
    if skills:
        sk_lbl = "SKILLS" if is_en else "COMPETÊNCIAS"
        side_items.append(rf"\bubblesidebartitle{{\faCogs}}{{{sk_lbl}}}")
        count_sk = 0
        for sk in skills:
            if isinstance(sk, dict):
                raw_items = str(sk.get("items") or "")
                parts = [p.strip() for p in raw_items.split(",") if p.strip()]
                for idx, p in enumerate(parts):
                    if count_sk >= 6:
                        break
                    frac = 0.95 if idx == 0 else (0.85 if idx < 3 else 0.70)
                    lvl_txt = "Avançado" if frac >= 0.85 else "Intermediário"
                    if is_en:
                        lvl_txt = "Advanced" if frac >= 0.85 else "Intermediate"
                    side_items.append(rf"\bubbleskill{{{escape_latex(p)}}}{{{lvl_txt}}}{{{frac:.2f}}}")
                    count_sk += 1
            elif isinstance(sk, str) and sk.strip():
                parts = [p.strip() for p in sk.split(",") if p.strip()]
                for idx, p in enumerate(parts):
                    if count_sk >= 6:
                        break
                    frac = 0.95 if idx == 0 else (0.85 if idx < 3 else 0.70)
                    lvl_txt = "Avançado" if frac >= 0.85 else "Intermediário"
                    if is_en:
                        lvl_txt = "Advanced" if frac >= 0.85 else "Intermediate"
                    side_items.append(rf"\bubbleskill{{{escape_latex(p)}}}{{{lvl_txt}}}{{{frac:.2f}}}")
                    count_sk += 1

    # Languages (parsed accurately for level label and progress bar width)
    langs = cv.get("languages") or []
    if langs:
        lang_lbl = "LANGUAGES" if is_en else "IDIOMAS"
        side_items.append(rf"\bubblesidebartitle{{\faLanguage}}{{{lang_lbl}}}")
        for idx, lg in enumerate(langs[:4]):
            clean_lname, lvl_label, frac = _parse_bubble_language(lg, idx=idx, is_en=is_en)
            if clean_lname:
                side_items.append(rf"\bubbleskill{{{escape_latex(clean_lname)}}}{{{escape_latex(lvl_label)}}}{{{frac:.2f}}}")

    # Awards
    clean_awards = sanitize_awards(cv.get("awards"), lang=lang)
    if clean_awards:
        aw_lbl = "AWARDS" if is_en else "PRÊMIOS"
        side_items.append(rf"\bubblesidebartitle{{\faTrophy}}{{{aw_lbl}}}")
        for aw in clean_awards[:3]:
            aw_txt = escape_latex(str(aw))
            if len(aw_txt) > 95:
                aw_txt = escape_latex(truncate_at_clause_boundary(str(aw), 95))
            side_items.append(rf"\bubblesideitem{{\faAward}}{{{aw_txt}}}")

    sidebar_content = "\n\n".join(side_items)

    tex = rf"""\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[a4paper,top=10mm,bottom=10mm,left=35mm,right=10mm]{{geometry}}
\setlength{{\topskip}}{{0mm}}
\setlength{{\parindent}}{{0mm}}
\pagenumbering{{gobble}}
\usepackage{{xcolor}}
\usepackage{{tikz}}
\usepackage{{paracol}}
\usepackage{{enumitem}}
\usepackage{{tabularx}}
\usepackage{{etoolbox}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\setlist[itemize]{{noitemsep, nolistsep, leftmargin=1.1em, topsep=1pt, parsep=0pt, partopsep=0pt}}

\definecolor{{accent}}{{HTML}}{{1A365D}}
\definecolor{{subaccent}}{{HTML}}{{2B6CB0}}
\definecolor{{cvbordercolor}}{{HTML}}{{FFFFFF}}
\definecolor{{cvlightcolor}}{{HTML}}{{EDF2F7}}

\newcommand\cvavatarradius{{16}}
\newcommand\cvavatarborderwidth{{0.8}}
\newcommand\cvmainbubbleradius{{5}}
\newcommand\cvmainbubbleborderwidth{{0.8}}
\newcommand\cveventdatewidth{{16}}
\newcommand\cveventbubbleradius{{2.5}}
\newcommand\cveventbubbleborderwidth{{0.7}}
\newcommand\cvsidebarbubbleradius{{5}}
\newcommand\cvsidebarbubbleborderwidth{{0.8}}
\newcommand\cvsidebaroffset{{2}}
\newcommand\timelinespace{{10}}

\AddToHook{{shipout/background}}{{%
  \put(24.7mm,-285mm){{\color{{accent!25}}\rule{{0.6mm}}{{{timeline_height_mm}mm}}}}%
}}

\newcommand{{\drawbubble}}[5]{{%
  \begin{{tikzpicture}}[baseline=-0.5ex]%
    \draw[draw=#4, fill=#3, line width=#2mm] (0,0) circle (\dimexpr#1mm-#2mm/2\relax);%
    \node at (0,0) {{#5}};%
  \end{{tikzpicture}}%
}}

\newcommand{{\bubblemaintitle}}[2]{{%
  \vspace{{2.5mm}}%
  \noindent\leavevmode%
  \hspace{{-\timelinespace mm}}%
  \hspace{{-\cvmainbubbleradius mm}}%
  \makebox[\dimexpr\cvmainbubbleradius mm * 2\relax][c]{{%
    \drawbubble{{\cvmainbubbleradius}}{{\cvmainbubbleborderwidth}}{{accent}}{{cvbordercolor}}{{\color{{white}}\fontsize{{8pt}}{{8pt}}\selectfont #1}}%
  }}%
  \hspace{{\dimexpr\timelinespace mm - \cvmainbubbleradius mm\relax}}%
  \parbox[c]{{\linewidth}}{{\raggedright\fontsize{{11.5pt}}{{13.5pt}}\bfseries\textcolor{{accent}}{{#2}}}}%
  \vspace{{1.8mm}}\par%
}}

\newcommand{{\bubblesidebartitle}}[2]{{%
  \vspace{{2.5mm}}%
  \noindent\leavevmode%
  \makebox[\dimexpr\cvsidebarbubbleradius mm * 2\relax][c]{{%
    \drawbubble{{\cvsidebarbubbleradius}}{{\cvsidebarbubbleborderwidth}}{{accent}}{{cvbordercolor}}{{\color{{white}}\fontsize{{8pt}}{{8pt}}\selectfont #1}}%
  }}%
  \hspace{{\cvsidebaroffset mm}}%
  \parbox[c]{{\dimexpr\linewidth - \cvsidebarbubbleradius mm * 2 - \cvsidebaroffset mm\relax}}{{\raggedright\fontsize{{11pt}}{{13pt}}\bfseries\textcolor{{accent}}{{#2}}}}%
  \vspace{{1.8mm}}\par%
}}

\newcommand{{\bubbleevent}}[5]{{%
  \noindent\leavevmode%
  \hspace{{-\cveventbubbleradius mm}}%
  \hspace{{-\timelinespace mm}}%
  \hspace{{-\cveventdatewidth mm}}%
  \parbox[t]{{\cveventdatewidth mm}}{{%
    \centering\leavevmode\footnotesize\bfseries\textcolor{{gray!80!black}}{{%
      \ifstrempty{{#2}}{{#1}}{{#2\\[-1pt]$\uparrow$\\[-1pt]#1}}%
    }}%
  }}%
  \makebox[\dimexpr\cveventbubbleradius mm * 2\relax][c]{{%
    \drawbubble{{\cveventbubbleradius}}{{\cveventbubbleborderwidth}}{{subaccent}}{{cvbordercolor}}{{}}%
  }}%
  \hspace{{\dimexpr\timelinespace mm - \cveventbubbleradius mm\relax}}%
  \parbox[t]{{\linewidth}}{{%
    \raggedright\leavevmode%
    {{\bfseries\fontsize{{9.8pt}}{{11.8pt}}\selectfont\textcolor{{accent!90!black}}{{#3}}}}%
    \ifstrempty{{#4}}{{}}{{\par\vspace{{1pt}}{{\small\itshape\textcolor{{black!75}}{{#4}}}}}}%
    \ifstrempty{{#5}}{{}}{{\par\vspace{{1.5pt}}{{\small #5}}}}%
  }}%
  \vspace{{2.2mm}}\par%
}}

\newcommand{{\bubblesideitem}}[2]{{%
  \noindent\leavevmode%
  \makebox[5mm][c]{{\textcolor{{subaccent}}{{\small #1}}}}%
  \hspace{{1.5mm}}%
  \parbox[t]{{\dimexpr\linewidth - 6.5mm\relax}}{{\raggedright\leavevmode\small\strut #2\strut}}%
  \vspace{{1.6mm}}\par%
}}

\newcommand{{\bubbleskill}}[3]{{%
  \noindent\leavevmode%
  \begin{{tabularx}}{{\linewidth}}{{@{{}}X>{{\raggedleft\arraybackslash}}r@{{}}}}%
    \textbf{{\small #1}} & {{\footnotesize\textcolor{{gray!75!black}}{{#2}}}}%
  \end{{tabularx}}\\[-3pt]%
  \begin{{tikzpicture}}[scale=1,rounded corners=0.8mm]%
    \fill [accent!12] (0,0) rectangle (\linewidth, 3.5pt);%
    \fill [subaccent] (0,0) rectangle (#3\linewidth, 3.5pt);%
  \end{{tikzpicture}}%
  \vspace{{1.8mm}}\par%
}}

\begin{{document}}

{header_tex}

\vspace{{2mm}}%
\columnratio{{0.62}}%
\setlength{{\columnsep}}{{9mm}}%

\begin{{paracol}}{{2}}
\sloppy
{main_content}

\switchcolumn
\sloppy

{sidebar_content}

\end{{paracol}}

\end{{document}}
"""
    return tex

