"""Compilador LaTeX (pdflatex) com blindagem de segurança, preparação de foto e auto-reparo de erros."""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path
from typing import List, Tuple

from PIL import Image

from .config import OUTPUT_DIR

# Proteção contra Image Decompression Bomb (DoS)
Image.MAX_IMAGE_PIXELS = 25_000_000

# Primitivas LaTeX perigosas bloqueadas em templates customizados (prevenção de RCE e leitura de arquivos)
_FORBIDDEN_LATEX_PATTERNS = (
    r"\\write\s*18\b",
    r"\\immediate\s*\\write\s*18\b",
    r"\\openin\b",
    r"\\openout\b",
    r"\\read\b",
    r"\\input\s*\{[^}]*(?:/|\\\\|\.\./|\.\.\\)",  # Bloqueia path traversal em \\input
    r"\\include\s*\{[^}]*(?:/|\\\\|\.\./|\.\.\\)",  # Bloqueia path traversal em \\include
    r"\\verbatiminput\b",
    r"\\lstinputlisting\b",
    r"\\import\s*\{",
    r"\\subimport\s*\{",
    r"\\catcode\b",
    r"\\csname\s*write",
    r"\\pdfprimitive\b",
    r"\\directlua\b",
)

_PDFLATEX_UNSUPPORTED_UNICODE = re.compile(
    r"[\U00010000-\U0010FFFF\u200B-\u200F\u202A-\u202E\u2060-\u206F"
    r"\uFE0E\uFE0F\uFEFF\u20E3\u2600-\u27BF\u2B00-\u2BFF]"
)


def sanitize_latex_for_pdflatex(latex_code: str) -> str:
    """Remove emoji and invisible format characters unsupported by pdfLaTeX."""
    if not latex_code:
        return ""
    normalized = unicodedata.normalize("NFC", latex_code)
    return _PDFLATEX_UNSUPPORTED_UNICODE.sub(" ", normalized)


def sanitize_custom_latex(latex_code: str) -> str:
    """Inspeciona e bloqueia primitivas LaTeX perigosas (RCE / Path Traversal / File Read)."""
    if not latex_code:
        return ""
    if len(latex_code) > 250_000:
        raise ValueError("Template LaTeX excede o tamanho máximo permitido (250 KB).")
    for pat in _FORBIDDEN_LATEX_PATTERNS:
        if re.search(pat, latex_code, flags=re.IGNORECASE):
            raise ValueError(
                "Template LaTeX bloqueado por segurança: contém comando de sistema ou leitura externa não permitido."
            )
    return latex_code


def _build_safe_tex_env() -> dict[str, str]:
    """Cria um ambiente isolado para o subprocesso pdflatex, sem vazar variáveis de ambiente do servidor."""
    safe_keys = (
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "HOME",
        "USERPROFILE",
        "TEMP",
        "TMP",
        "TMPDIR",
        "LANG",
        "LC_ALL",
        "TEXMFMAIN",
        "TEXMFDIST",
        "TEXMFLOCAL",
        "TEXMFHOME",
        "TEXMFVAR",
        "TEXMFCONFIG",
    )
    env: dict[str, str] = {}
    for k in safe_keys:
        val = os.environ.get(k)
        if val:
            env[k] = val
    # Modo paranóico do Web2C/TeX Live: proíbe leitura/escrita fora do diretório de compilação e desativa shell_escape
    env["openin_any"] = "p"
    env["openout_any"] = "p"
    env["shell_escape"] = "f"
    return env


def prepare_photo_for_latex(
    build_dir: Path,
    photo_bytes: bytes | None = None,
    photo_path: str | Path | None = None,
    target_stem: str = "profile_photo",
) -> str | None:
    """Converte e salva a foto do usuário em PNG RGB compatível com pdflatex."""
    raw_bytes: bytes | None = photo_bytes
    if not raw_bytes and photo_path:
        p = Path(photo_path)
        if p.exists() and p.is_file():
            raw_bytes = p.read_bytes()

    if not raw_bytes:
        return None

    if len(raw_bytes) > 6 * 1024 * 1024:
        raise ValueError("A imagem de perfil excede o limite máximo de 6 MB.")

    build_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", target_stem).strip("_") or "profile_photo"
    out_filename = f"{safe_stem}.png"
    out_path = build_dir / out_filename

    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img.verify()
        img = Image.open(io.BytesIO(raw_bytes))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        # Redimensiona mantendo proporção para evitar PDFs pesados
        img.thumbnail((600, 600))
        img.save(out_path, format="PNG")
        return out_filename
    except Exception:
        return None


def extract_concise_latex_error(log_text: str) -> str:
    """Extrai apenas as linhas decisivas de erro do log do pdflatex (economia de tokens)."""
    lines = log_text.splitlines()
    err_lines = []
    for idx, line in enumerate(lines):
        if line.startswith("!"):
            snippet = lines[max(0, idx - 1) : min(len(lines), idx + 6)]
            err_lines.extend(snippet)
            break
    if err_lines:
        return "\n".join(err_lines)
    return "\n".join(lines[-20:])


def get_pdflatex_path() -> str | None:
    """Localiza o executável `pdflatex` no PATH ou em instalações padrão do TeX Live / MiKTeX."""
    found = shutil.which("pdflatex")
    if found:
        return found
    candidates = [
        "/usr/bin/pdflatex",
        "/usr/local/bin/pdflatex",
        r"C:\texlive\2025\bin\windows\pdflatex.exe",
        r"C:\texlive\2024\bin\windows\pdflatex.exe",
        r"C:\texlive\2023\bin\windows\pdflatex.exe",
        str(Path.home() / r"AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"),
        r"C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def check_latex_compiler() -> Tuple[bool, str]:
    """Verifica se o compilador LaTeX (`pdflatex`) obrigatório está instalado e funcional."""
    bin_path = get_pdflatex_path()
    if not bin_path:
        return (
            False,
            "pdflatex não encontrado (instale TeX Live ou MiKTeX) / pdflatex not found (install TeX Live or MiKTeX).",
        )
    try:
        proc = subprocess.run(
            [bin_path, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            env=_build_safe_tex_env(),
        )
        first_line = (proc.stdout or "").splitlines()[0].strip() if proc.stdout else "pdflatex"
        # Remove o trecho entre parênteses com distribuição (ex: "(TeX Live 2022/Debian)")
        import re as _re
        first_line = _re.sub(r"\s*\(TeX Live[^)]*\)", "", first_line).strip()
        return True, first_line
    except Exception:
        return False, "Erro ao verificar pdflatex / Error checking pdflatex"


def sanitize_latex_layout(tex: str) -> str:
    """Higieniza o layout do LaTeX garantindo separação visual de parágrafos entre entradas estruturadas.

    Previne que linhas de instituições, empresas ou subtítulos se fundam na mesma linha
    que a próxima formação acadêmica ou cargo com `\\hfill`.
    """
    if not tex or not tex.strip():
        return tex

    lines = tex.splitlines()
    fixed_lines: List[str] = []

    # Detecta linhas de início de entrada (Grau, Cargo, Projeto) geralmente acompanhadas de \\hfill ou traço
    entry_header_pattern = re.compile(
        r"^\s*(?:\\noindent\s*)?\\textbf\{[^\}]+\}(?:\s*\\hfill|\s*---|---|\s*--|--)",
        re.IGNORECASE,
    )

    safe_end_pattern = re.compile(
        r"(\\par(?:\s*\\vspace\{[^\}]*\})?|\\end\{(?:itemize|enumerate|tabular|tabular\*|minipage)\})\s*$",
        re.IGNORECASE,
    )
    sec_header_pattern = re.compile(
        r"^\s*(?:\\(?:section|subsection|subsubsection|cvsection|cventry|resumeSubHeadingListStart|rule|switchcolumn)\b|\{\s*\\(?:large|Large|LARGE|normalsize)\b|\\(?:large|Large|LARGE)\b)",
        re.IGNORECASE,
    )

    for line in lines:
        stripped = line.strip()
        if entry_header_pattern.match(stripped) and fixed_lines:
            prev_idx = len(fixed_lines) - 1
            while prev_idx >= 0 and not fixed_lines[prev_idx].strip():
                prev_idx -= 1

            if prev_idx >= 0:
                prev = fixed_lines[prev_idx].strip()
                if prev and not prev.startswith("%") and not sec_header_pattern.match(prev):
                    if prev.endswith(r"\\"):
                        fixed_lines[prev_idx] = fixed_lines[prev_idx][:-2].rstrip() + r"\par\vspace{3pt}"
                        if not any(not l.strip() for l in fixed_lines[prev_idx + 1:]):
                            fixed_lines.append("")
                    elif not safe_end_pattern.search(prev):
                        fixed_lines[prev_idx] = fixed_lines[prev_idx] + r"\par\vspace{3pt}"
                        if not any(not l.strip() for l in fixed_lines[prev_idx + 1:]):
                            fixed_lines.append("")
                    elif not any(not l.strip() for l in fixed_lines[prev_idx + 1:]):
                        fixed_lines.append("")

        fixed_lines.append(line)

    cleaned = "\n".join(fixed_lines)
    cleaned = clean_latex_project_verbs(cleaned)
    cleaned = clean_latex_experience_verbs(cleaned)
    cleaned = sanitize_publications_layout(cleaned)
    return cleaned


def clean_latex_project_verbs(tex: str) -> str:
    """Higieniza itens na seção de projetos para iniciarem com substantivos e não verbos no passado."""
    if not tex or not tex.strip():
        return tex

    proj_sec_pattern = re.compile(
        r"(\\section\*?\{[^}]*(?:Projetos|Projects)[^}]*\}|"
        r"\\cvsection\{[^}]*(?:Projetos|Projects)[^}]*\}|"
        r"\\textbf\{[^}]*(?:Projetos|Projects)[^}]*\}|"
        r"\{\\large\\bfseries\\color\{accent\}\s*(?:TECHNICAL PROJECTS|PROJETOS TÉCNICOS|PROJETOS)[^}]*\})"
        r"(.*?)"
        r"(?=(\\(?:section\*?|cvsection|subsection)\b|\{\\large\\bfseries|\\end\{document\}|\Z))",
        re.IGNORECASE | re.DOTALL,
    )

    pt_verbs = r"(?:Desenvolveu|Criou|Implementou|Reuniu|Construiu|Elaborou|Projetou|Estruturou|Idealizou|Programou|Confeccionou|Organizou)"
    en_verbs = r"(?:Developed|Created|Implemented|Built|Designed|Engineered|Crafted|Constructed|Programmed|Gathered|Assembled|Authored)"

    item_pattern_pt = re.compile(rf"(\\item\s+)(?:{pt_verbs})\s+(?:(?:um|uma|o|a|os|as)\s+)?([A-Za-zÀ-ÖØ-öø-ÿ])", re.IGNORECASE)
    colon_pattern_pt = re.compile(rf"(:\s+)(?:{pt_verbs})\s+(?:(?:um|uma|o|a|os|as)\s+)?([A-Za-zÀ-ÖØ-öø-ÿ])", re.IGNORECASE)
    small_pattern_pt = re.compile(rf"(\{{\\small\s+)(?:{pt_verbs})\s+(?:(?:um|uma|o|a|os|as)\s+)?([A-Za-zÀ-ÖØ-öø-ÿ])", re.IGNORECASE)

    item_pattern_en = re.compile(rf"(\\item\s+)(?:{en_verbs})\s+(?:(?:a|an|the)\s+)?([A-Za-z])", re.IGNORECASE)
    colon_pattern_en = re.compile(rf"(:\s+)(?:{en_verbs})\s+(?:(?:a|an|the)\s+)?([A-Za-z])", re.IGNORECASE)
    small_pattern_en = re.compile(rf"(\{{\\small\s+)(?:{en_verbs})\s+(?:(?:a|an|the)\s+)?([A-Za-z])", re.IGNORECASE)

    def repl_sec(match):
        header = match.group(1)
        body = match.group(2)
        b = item_pattern_pt.sub(lambda m: f"{m.group(1)}{m.group(2).upper()}", body)
        b = colon_pattern_pt.sub(lambda m: f"{m.group(1)}{m.group(2).upper()}", b)
        b = small_pattern_pt.sub(lambda m: f"{m.group(1)}{m.group(2).upper()}", b)
        b = item_pattern_en.sub(lambda m: f"{m.group(1)}{m.group(2).upper()}", b)
        b = colon_pattern_en.sub(lambda m: f"{m.group(1)}{m.group(2).upper()}", b)
        b = small_pattern_en.sub(lambda m: f"{m.group(1)}{m.group(2).upper()}", b)
        return f"{header}{b}"

    return proj_sec_pattern.sub(repl_sec, tex)


def clean_latex_experience_verbs(tex: str) -> str:
    """Higieniza itens na seção de experiência profissional para iniciarem com substantivos e não verbos no passado."""
    if not tex or not tex.strip():
        return tex

    exp_sec_pattern = re.compile(
        r"(\\section\*?\{[^}]*(?:Experiência|Experience|Atuação|Histórico)[^}]*\}|"
        r"\\cvsection\{[^}]*(?:Experiência|Experience)[^}]*\}|"
        r"\\textbf\{[^}]*(?:Experiência|Experience)[^}]*\}|"
        r"\{\\large\\bfseries\\color\{accent\}\s*(?:EXPERIÊNCIA PROFISSIONAL|PROFESSIONAL EXPERIENCE|WORK EXPERIENCE|EXPERIÊNCIA|EXPERIENCE)[^}]*\})"
        r"(.*?)"
        r"(?=(\\(?:section\*?|cvsection|subsection)\b|\{\\large\\bfseries|\\end\{document\}|\Z))",
        re.IGNORECASE | re.DOTALL,
    )

    pt_verb_conversions = [
        (r"(\\item\s+)Participou\s+no\b", r"\1Participação no"),
        (r"(\\item\s+)Participou\s+na\b", r"\1Participação na"),
        (r"(\\item\s+)Participou\s+nos\b", r"\1Participação nos"),
        (r"(\\item\s+)Participou\s+nas\b", r"\1Participação nas"),
        (r"(\\item\s+)Participou\s+do\b", r"\1Participação no"),
        (r"(\\item\s+)Participou\s+da\b", r"\1Participação na"),
        (r"(\\item\s+)Participou\s+dos\b", r"\1Participação nos"),
        (r"(\\item\s+)Participou\s+das\b", r"\1Participação nas"),
        (r"(\\item\s+)Participou\s+de\b", r"\1Participação em"),
        (r"(\\item\s+)Participou\s+em\b", r"\1Participação em"),
        (r"(\\item\s+)Participou\b", r"\1Participação em"),
        (r"(\\item\s+)Orientou\s+(?:a\s+|de\s+)?", r"\1Orientação a "),
        (r"(\\item\s+)Acompanhou\s+(?:de\s+)?", r"\1Acompanhamento de "),
        (r"(\\item\s+)Ensinou\s+(?:de\s+)?", r"\1Ensino de "),
        (r"(\\item\s+)Desenvolveu\s+(?:de\s+)?", r"\1Desenvolvimento de "),
        (r"(\\item\s+)Realizou\s+trabalho\s+volunt[aá]rio\b", r"\1Realização de trabalho voluntário"),
        (r"(\\item\s+)Realizou\s+(?:de\s+)?", r"\1Realização de "),
        (r"(\\item\s+)Liderou\s+(?:de\s+)?", r"\1Liderança de "),
        (r"(\\item\s+)Coordenou\s+(?:de\s+)?", r"\1Coordenação de "),
        (r"(\\item\s+)(?:Gerenciou|Geriu)\s+(?:de\s+)?", r"\1Gerenciamento de "),
        (r"(\\item\s+)Implementou\s+(?:de\s+)?", r"\1Implementação de "),
        (r"(\\item\s+)Criou\s+(?:de\s+)?", r"\1Criação de "),
        (r"(\\item\s+)Elaborou\s+(?:de\s+)?", r"\1Elaboração de "),
        (r"(\\item\s+)Ministrou\s+(?:de\s+)?", r"\1Ministração de "),
        (r"(\\item\s+)Apoiou\s+no\b", r"\1Apoio ao"),
        (r"(\\item\s+)Apoiou\s+na\b", r"\1Apoio à"),
        (r"(\\item\s+)Apoiou\s+nos\b", r"\1Apoio aos"),
        (r"(\\item\s+)Apoiou\s+nas\b", r"\1Apoio às"),
        (r"(\\item\s+)Apoiou\s+(?:a\s+)?", r"\1Apoio a "),
        (r"(\\item\s+)Atuou\s+como\b", r"\1Atuação como"),
        (r"(\\item\s+)Atuou\s+na\b", r"\1Atuação na"),
        (r"(\\item\s+)Atuou\s+no\b", r"\1Atuação no"),
        (r"(\\item\s+)Atuou\s+em\b", r"\1Atuação em"),
        (r"(\\item\s+)Atuou\b", r"\1Atuação em"),
        (r"(\\item\s+)Prestou\s+assessoria\s+(?:a\s+)?", r"\1Assessoria a "),
        (r"(\\item\s+)Prestou\s+apoio\s+(?:a\s+)?", r"\1Apoio a "),
        (r"(\\item\s+)Prestou\s+suporte\s+(?:a\s+)?", r"\1Suporte a "),
        (r"(\\item\s+)Prestou\s+(?:de\s+)?", r"\1Prestação de "),
        (r"(\\item\s+)Colaborou\s+com\b", r"\1Colaboração com"),
        (r"(\\item\s+)Colaborou\s+(?:em\s+)?", r"\1Colaboração em "),
        (r"(\\item\s+)Conduziu\s+(?:de\s+)?", r"\1Condução de "),
        (r"(\\item\s+)Executou\s+(?:de\s+)?", r"\1Execução de "),
        (r"(\\item\s+)Planejou\s+(?:de\s+)?", r"\1Planejamento de "),
        (r"(\\item\s+)Auxiliou\s+no\b", r"\1Auxílio no"),
        (r"(\\item\s+)Auxiliou\s+na\b", r"\1Auxílio na"),
        (r"(\\item\s+)Auxiliou\s+(?:em\s+)?", r"\1Auxílio em "),
        (r"(\\item\s+)Supervisionou\s+(?:de\s+)?", r"\1Supervisão de "),
        (r"(\\item\s+)Construiu\s+(?:de\s+)?", r"\1Construção de "),
        (r"(\\item\s+)Estruturou\s+(?:de\s+)?", r"\1Estruturação de "),
        (r"(\\item\s+)Projetou\s+(?:de\s+)?", r"\1Projeto de "),
        (r"(\\item\s+)Pesquisou\s+(?:de\s+|sobre\s+)?", r"\1Pesquisa sobre "),
        (r"(\\item\s+)Investigou\s+(?:de\s+|sobre\s+)?", r"\1Investigação de "),
        (r"(\\item\s+)Organizou\s+(?:de\s+)?", r"\1Organização de "),
        (r"(\\item\s+)Administrou\s+(?:de\s+)?", r"\1Administração de "),
        (r"(\\item\s+)Otimizou\s+(?:de\s+)?", r"\1Otimização de "),
        (r"(\\item\s+)Automatizou\s+(?:de\s+)?", r"\1Automatização de "),
        (r"(\\item\s+)Publicou\s+(?:de\s+)?", r"\1Publicação de "),
        (r"(\\item\s+)Apresentou\s+(?:de\s+)?", r"\1Apresentação de "),
        (r"(\\item\s+)Redigiu\s+(?:de\s+)?", r"\1Redação de "),
        (r"(\\item\s+)Revisou\s+(?:de\s+)?", r"\1Revisão de "),
        (r"(\\item\s+)Produziu\s+(?:de\s+)?", r"\1Produção de "),
        (r"(\\item\s+)Integrou\s+(?:de\s+)?", r"\1Integração de "),
        (r"(\\item\s+)Configurou\s+(?:de\s+)?", r"\1Configuração de "),
        (r"(\\item\s+)Instalou\s+(?:de\s+)?", r"\1Instalação de "),
        (r"(\\item\s+)Facilitou\s+(?:de\s+)?", r"\1Facilitação de "),
        (r"(\\item\s+)Articulou\s+(?:de\s+)?", r"\1Articulação de "),
        (r"(\\item\s+)Promoveu\s+(?:de\s+)?", r"\1Promoção de "),
        (r"(\\item\s+)Assessorou\s+(?:a\s+)?", r"\1Assessoria a "),
        (r"(\\item\s+)Treinou\s+(?:de\s+)?", r"\1Treinamento de "),
        (r"(\\item\s+)Capacitou\s+(?:de\s+)?", r"\1Capacitação de "),
        (r"(\\item\s+)Tutelou\s+(?:de\s+)?", r"\1Tutoria de "),
        (r"(\\item\s+)Migrou\s+(?:de\s+)?", r"\1Migração de "),
        (r"(\\item\s+)Analisou\s+(?:de\s+)?", r"\1Análise de "),
        (r"(\\item\s+)Gerou\s+(?:de\s+)?", r"\1Geração de "),
    ]

    en_verb_conversions = [
        (r"(\\item\s+)Led\s+(?:in\s+|the\s+)?", r"\1Leadership of "),
        (r"(\\item\s+)Managed\s+(?:the\s+)?", r"\1Management of "),
        (r"(\\item\s+)Developed\s+(?:the\s+)?", r"\1Development of "),
        (r"(\\item\s+)Designed\s+(?:the\s+)?", r"\1Design of "),
        (r"(\\item\s+)Implemented\s+(?:the\s+)?", r"\1Implementation of "),
        (r"(\\item\s+)Created\s+(?:the\s+)?", r"\1Creation of "),
        (r"(\\item\s+)Taught\s+(?:the\s+)?", r"\1Instruction in "),
        (r"(\\item\s+)Mentored\s+(?:the\s+)?", r"\1Mentorship of "),
        (r"(\\item\s+)Guided\s+(?:the\s+)?", r"\1Guidance of "),
        (r"(\\item\s+)Participated\s+in\b", r"\1Participation in"),
        (r"(\\item\s+)Participated\b", r"\1Participation in"),
        (r"(\\item\s+)Assisted\s+with\b", r"\1Assistance with"),
        (r"(\\item\s+)Assisted\s+in\b", r"\1Assistance in"),
        (r"(\\item\s+)Assisted\b", r"\1Assistance in"),
        (r"(\\item\s+)Conducted\s+(?:the\s+)?", r"\1Conduction of "),
        (r"(\\item\s+)Coordinated\s+(?:the\s+)?", r"\1Coordination of "),
        (r"(\\item\s+)Collaborated\s+with\b", r"\1Collaboration with"),
        (r"(\\item\s+)Collaborated\b", r"\1Collaboration in"),
        (r"(\\item\s+)Organized\s+(?:the\s+)?", r"\1Organization of "),
        (r"(\\item\s+)Engineered\s+(?:the\s+)?", r"\1Engineering of "),
        (r"(\\item\s+)Built\s+(?:the\s+)?", r"\1Construction of "),
    ]

    def repl_sec(match):
        header = match.group(1)
        body = match.group(2)
        b = body
        for pat, rep in pt_verb_conversions:
            b = re.sub(pat, rep, b, flags=re.IGNORECASE)
        for pat, rep in en_verb_conversions:
            b = re.sub(pat, rep, b, flags=re.IGNORECASE)

        # Conjunções internas com verbos comuns
        b = re.sub(r"\be apoiou no\b", "e apoio no", b, flags=re.IGNORECASE)
        b = re.sub(r"\be apoiou na\b", "e apoio na", b, flags=re.IGNORECASE)
        b = re.sub(r"\be apoiou o\b", "e apoio ao", b, flags=re.IGNORECASE)
        b = re.sub(r"\be apoiou a\b", "e apoio à", b, flags=re.IGNORECASE)
        b = re.sub(r"\be apoiou\b", "e apoio a", b, flags=re.IGNORECASE)
        b = re.sub(r"\be acompanhou\b", "e acompanhamento de", b, flags=re.IGNORECASE)
        b = re.sub(r"\be auxiliou\b", "e auxílio em", b, flags=re.IGNORECASE)
        return f"{header}{b}"

    return exp_sec_pattern.sub(repl_sec, tex)


def is_venue_continuation(item_text: str) -> bool:
    """Verifica se um \\item em publicações é apenas a continuação (venue, data, DOI) de um título anterior."""
    clean = item_text.strip()
    if r"\textbf{" in clean:
        return False
    low = clean.lower()
    venue_markers = [
        "doi:", "doi.org", "revista", "anais", "workshop", "journal", "proceedings",
        "conference", "editora", "symposium", "simpósio", "isbn", "issn", "vol.", "pp.", "págs."
    ]
    return any(k in low for k in venue_markers) or clean.startswith(r"\textit{") or clean.startswith(r"{\small \textit{")


def sanitize_publications_layout(tex: str) -> str:
    """Garante numeração sequencial estrita (1, 2, 3...) na seção de publicações e produção científica.

    Corrige saídas de LLM que geram múltiplos ambientes \\begin{enumerate} separados por publicação
    ou dividem o título e o local/DOI da mesma publicação em dois \\item separados.
    """
    if not tex or not tex.strip():
        return tex

    pub_sec_pattern = re.compile(
        r"(\\cvsection\{[^}]*(?:Publica|Produção Científica|Publications)[^}]*\}|"
        r"\\section\*?\{[^}]*(?:Publica|Produção Científica|Publications)[^}]*\}|"
        r"\{\\large\\bfseries\\color\{accent\}\s*(?:PUBLICATIONS|PUBLICAÇÕES|PRODUÇÃO CIENTÍFICA)[^}]*\})"
        r"(.*?)"
        r"(?=(\\(?:section\*?|cvsection|subsection)\b|\{\\large\\bfseries|\\end\{document\}|\Z))",
        re.IGNORECASE | re.DOTALL,
    )

    def fix_pub_section(match):
        header = match.group(1)
        body = match.group(2)

        enum_blocks = re.findall(r"\\begin\{enumerate\}(?:\[[^\]]*\])?(.*?)\\end\{enumerate\}", body, re.DOTALL)
        if not enum_blocks:
            return match.group(0)

        raw_items: List[str] = []
        for b in enum_blocks:
            its = [it.strip() for it in re.split(r"\\item\b", b) if it.strip()]
            raw_items.extend(its)

        if not raw_items:
            return match.group(0)

        merged_items: List[str] = []
        for it in raw_items:
            if merged_items and is_venue_continuation(it):
                merged_items[-1] = merged_items[-1].rstrip() + " " + it.lstrip()
            else:
                merged_items.append(it)

        new_enum = "\\begin{enumerate}[label=\\arabic*.,leftmargin=1.5em,itemsep=2pt,topsep=2pt]\n"
        for it in merged_items:
            new_enum += f"    \\item {it}\n"
        new_enum += "\\end{enumerate}\n"

        first_enum = body.find(r"\begin{enumerate}")
        last_enum = body.rfind(r"\end{enumerate}")
        if first_enum != -1 and last_enum != -1:
            last_enum += len(r"\end{enumerate}")
            cleaned_body = body[:first_enum] + new_enum + body[last_enum:]
        else:
            cleaned_body = body
        return f"{header}{cleaned_body}"

    return pub_sec_pattern.sub(fix_pub_section, tex)


def compile_latex_to_pdf(
    latex_code: str,
    output_stem: str = "curriculo",
    build_dir: Path | None = None,
) -> Tuple[bool, Path | None, Path, str]:
    """Compila código LaTeX em PDF usando pdflatex em ambiente restrito (-no-shell-escape).

    Retorna: (sucesso, caminho_pdf, caminho_tex, log_resumido)
    """
    latex_code = sanitize_latex_for_pdflatex(latex_code)
    latex_code = sanitize_custom_latex(latex_code)
    latex_code = sanitize_latex_layout(latex_code)

    target_dir = (build_dir or OUTPUT_DIR).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", output_stem).strip("_") or "curriculo"
    tex_path = target_dir / f"{safe_stem}.tex"
    pdf_path = target_dir / f"{safe_stem}.pdf"

    tex_path.write_text(latex_code, encoding="utf-8")

    pdflatex_bin = get_pdflatex_path()
    if not pdflatex_bin:
        return (
            False,
            None,
            tex_path,
            "Requisito ausente: compilador `pdflatex` (TeX Live / MiKTeX) não encontrado no sistema.",
        )

    cmd = [
        pdflatex_bin,
        "-no-shell-escape",
        "-interaction=nonstopmode",
        "-halt-on-error",
        tex_path.name,
    ]

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(target_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            env=_build_safe_tex_env(),
        )
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            return True, pdf_path, tex_path, "Compilado com sucesso via pdflatex."
        err_msg = extract_concise_latex_error(proc.stdout + "\n" + proc.stderr)
        return False, None, tex_path, err_msg
    except Exception as exc:
        return False, None, tex_path, f"Falha na compilação LaTeX ({type(exc).__name__})."


def secure_wipe_and_remove_dir(dir_path: Path | str | None) -> None:
    """Sobrescreve com bytes nulos e remove com segurança todos os arquivos de um diretório efêmero.

    Garante a política de Zero-Storage no servidor: documentos recebidos (fotos, PDFs, XMLs)
    e gerados (.tex, .pdf, .aux, .log) são destruídos imediatamente após a requisição.
    """
    if not dir_path:
        return
    try:
        p = Path(dir_path).resolve()
        if not p.exists() or not p.is_dir():
            return
        for item in p.iterdir():
            try:
                if item.is_file():
                    size = item.stat().st_size
                    if size > 0:
                        with open(item, "wb") as f:
                            f.write(b"\x00" * min(size, 65536))
                    item.unlink(missing_ok=True)
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
            except Exception:
                pass
        shutil.rmtree(p, ignore_errors=True)
    except Exception:
        pass



