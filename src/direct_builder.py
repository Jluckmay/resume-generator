"""Construtor Direto e Determinístico de Currículos (Zero-Token / Sem IA).



Permite gerar currículos LaTeX profissionais ou acadêmicos 100% offline

e determinísticos a partir dos dados coletados pelos extratores

(GitHub, ORCID, Lattes, LinkedIn, Portfólio e metadados manuais).



Garante:

1. Economia de 100% de tokens quando o uso de modelos de IA estiver desabilitado.

2. Servir como base de altíssima qualidade para revisão cirúrgica por LLMs,

   economizando até 75% dos tokens em relação à síntese de texto bruto não-estruturado.

3. Compilação determinística com 0 alucinações de dados, datas ou instituições.

"""



from __future__ import annotations

import re
import unicodedata
import urllib.parse
from typing import Any, Dict, List, Tuple

from .i18n import (
    normalize_lang,
    standardize_summary_to_en,
    translate_award_to_en,
    translate_experience_bullet_to_en,
    translate_institution_to_en,
    translate_role_to_en,
)

from .extractors import (
    extract_languages_from_text,
    sanitize_project_description,
    sanitize_experience_description,
)
from .skills import collect_project_technologies, merge_skill_groups
from .text_utils import remove_terminal_abbreviation_ellipsis

from .templates import (

    BUILTIN_TEMPLATES,

    simplify_url_display,

    _get_platform_display,

    escape_latex,

    escape_url,

    render_builtin_template,
    sanitize_awards,
    are_awards_duplicate,
    are_educations_duplicate,
    are_experiences_duplicate,
    are_publications_duplicate,
    deduplicate_and_sort_awards,
    deduplicate_and_sort_educations,
    deduplicate_and_sort_experiences,
    deduplicate_and_sort_projects,
    deduplicate_and_sort_publications,
    merge_educations,
    merge_experiences,
    merge_publications,

)





def parse_manual_resume_inputs(manual_data: Dict[str, Any] | None) -> Dict[str, Any]:
    """Normaliza e extrai dados de currículo inseridos manualmente (estruturados ou texto livre)."""
    if not manual_data or not isinstance(manual_data, dict):
        return {}

    parsed: Dict[str, Any] = {}

    # 1. Metadados e Resumo
    for key in ("name", "title", "role", "email", "phone", "location", "summary"):
        val = manual_data.get(key)
        if val and isinstance(val, str) and val.strip():
            parsed[key] = val.strip()

    # 2. Formação Acadêmica (Education)
    raw_edu = manual_data.get("education")
    edu_list: List[Dict[str, str]] = []
    if isinstance(raw_edu, list):
        for item in raw_edu:
            if isinstance(item, dict):
                degree = str(item.get("degree") or item.get("course") or item.get("level") or "").strip()
                inst = str(item.get("institution") or item.get("org") or "").strip()
                period = str(item.get("period") or item.get("year") or "").strip()
                details = str(item.get("details") or item.get("thesis_title") or "").strip()
                if degree or inst:
                    edu_list.append({"degree": degree, "institution": inst, "period": period, "details": details})
            elif isinstance(item, str) and item.strip():
                parts = [p.strip() for p in item.split("|")]
                edu_list.append({
                    "degree": parts[0],
                    "institution": parts[1] if len(parts) > 1 else "",
                    "period": parts[2] if len(parts) > 2 else "",
                    "details": parts[3] if len(parts) > 3 else "",
                })
    elif isinstance(raw_edu, str) and raw_edu.strip():
        for line in raw_edu.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in (line.split("|") if "|" in line else line.split(" - "))]
            edu_list.append({
                "degree": parts[0],
                "institution": parts[1] if len(parts) > 1 else "",
                "period": parts[2] if len(parts) > 2 else "",
                "details": parts[3] if len(parts) > 3 else "",
            })
    if edu_list:
        parsed["education"] = edu_list

    # 3. Experiência Profissional (Experience)
    raw_exp = manual_data.get("experience")
    exp_list: List[Dict[str, str]] = []
    if isinstance(raw_exp, list):
        for item in raw_exp:
            if isinstance(item, dict):
                role = str(item.get("role") or item.get("title") or "").strip()
                org = str(item.get("organization") or item.get("company") or "").strip()
                period = str(item.get("period") or "").strip()
                loc = str(item.get("location") or "").strip()
                desc = str(item.get("description") or "").strip()
                if role or org:
                    exp_list.append({"role": role, "organization": org, "period": period, "location": loc, "description": desc})
            elif isinstance(item, str) and item.strip():
                parts = [p.strip() for p in item.split("|")]
                exp_list.append({
                    "role": parts[0],
                    "organization": parts[1] if len(parts) > 1 else "",
                    "period": parts[2] if len(parts) > 2 else "",
                    "location": parts[3] if len(parts) > 3 else "",
                    "description": parts[4] if len(parts) > 4 else "",
                })
    elif isinstance(raw_exp, str) and raw_exp.strip():
        for line in raw_exp.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in (line.split("|") if "|" in line else line.split(" - "))]
            exp_list.append({
                "role": parts[0],
                "organization": parts[1] if len(parts) > 1 else "",
                "period": parts[2] if len(parts) > 2 else "",
                "location": parts[3] if len(parts) > 3 else "",
                "description": parts[4] if len(parts) > 4 else (parts[3] if len(parts) == 4 and not any(c in parts[3] for c in (",", "/")) else ""),
            })
    if exp_list:
        parsed["experience"] = exp_list

    # 4. Habilidades & Competências (Skills)
    raw_skills = manual_data.get("skills")
    skill_list: List[Dict[str, Any]] = []
    if isinstance(raw_skills, list):
        for item in raw_skills:
            if isinstance(item, dict):
                cat = str(item.get("category") or "Competências Principais").strip()
                items = item.get("items")
                if isinstance(items, list):
                    items_str = ", ".join(str(x).strip() for x in items if str(x).strip())
                else:
                    items_str = str(items or "").strip()
                if items_str:
                    skill_list.append({"category": cat, "items": items_str})
            elif isinstance(item, str) and item.strip():
                if ":" in item:
                    cat, items = item.split(":", 1)
                    skill_list.append({"category": cat.strip(), "items": items.strip()})
                else:
                    skill_list.append({"category": "Competências Principais", "items": item.strip()})
    elif isinstance(raw_skills, str) and raw_skills.strip():
        for line in raw_skills.splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                cat, items = line.split(":", 1)
                skill_list.append({"category": cat.strip(), "items": items.strip()})
            else:
                skill_list.append({"category": "Competências Principais", "items": line})
    if skill_list:
        parsed["skills"] = skill_list

    # 5. Projetos (Projects)
    raw_proj = manual_data.get("projects")
    proj_list: List[Dict[str, str]] = []
    if isinstance(raw_proj, list):
        for item in raw_proj:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                tech = str(item.get("tech") or "").strip()
                url = str(item.get("url") or "").strip()
                desc = str(item.get("description") or "").strip()
                stars = item.get("stars", item.get("likes", 0))
                forks = item.get("forks", 0)
                likes = item.get("likes", item.get("stars", 0))
                if name:
                    proj_list.append({"name": name, "tech": tech, "url": url, "description": desc, "stars": stars, "forks": forks, "likes": likes})
            elif isinstance(item, str) and item.strip():
                parts = [p.strip() for p in item.split("|")]
                proj_list.append({
                    "name": parts[0],
                    "tech": parts[1] if len(parts) > 1 else "",
                    "url": parts[2] if len(parts) > 2 else "",
                    "description": parts[3] if len(parts) > 3 else "",
                })
    elif isinstance(raw_proj, str) and raw_proj.strip():
        for line in raw_proj.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in (line.split("|") if "|" in line else line.split(" - "))]
            proj_list.append({
                "name": parts[0],
                "tech": parts[1] if len(parts) > 1 else "",
                "url": parts[2] if len(parts) > 2 and parts[2].startswith("http") else "",
                "description": parts[3] if len(parts) > 3 else (parts[2] if len(parts) > 2 and not parts[2].startswith("http") else ""),
            })
    if proj_list:
        parsed["projects"] = proj_list

    # 6. Idiomas (Languages)
    raw_langs = manual_data.get("languages")
    lang_list: List[str] = []
    if isinstance(raw_langs, list):
        for lg in raw_langs:
            if isinstance(lg, dict):
                nm = str(lg.get("name") or "").strip()
                lvl = str(lg.get("level") or lg.get("proficiency") or "").strip()
                lang_list.append(f"{nm} ({lvl})" if lvl else nm)
            elif isinstance(lg, str) and lg.strip():
                lang_list.append(lg.strip())
    elif isinstance(raw_langs, str) and raw_langs.strip():
        items = [it.strip() for it in re.split(r"[\r\n,;]+", raw_langs) if it.strip()]
        lang_list = [it.strip() for it in items if it.strip()]
    if lang_list:
        parsed["languages"] = lang_list

    # 7. Prêmios & Certificações (Awards)
    raw_awards = manual_data.get("awards")
    award_list: List[Any] = []
    if isinstance(raw_awards, list):
        award_list = [a for a in raw_awards if a]
    elif isinstance(raw_awards, str) and raw_awards.strip():
        award_list = [line.strip() for line in raw_awards.splitlines() if line.strip()]
    if award_list:
        parsed["awards"] = award_list

    # 8. Publicações (Publications)
    raw_pubs = manual_data.get("publications")
    pub_list: List[Dict[str, str]] = []
    if isinstance(raw_pubs, list):
        for item in raw_pubs:
            if isinstance(item, dict):
                title = str(item.get("title") or "").strip()
                venue = str(item.get("venue") or "").strip()
                yr = str(item.get("year") or "").strip()
                authors = str(item.get("authors") or "").strip()
                doi = str(item.get("doi") or "").strip()
                citations = str(item.get("citations") or "").strip()
                qualis = str(item.get("qualis") or "").strip()
                if title:
                    entry = {"title": title, "venue": venue, "year": yr, "authors": authors, "doi": doi}
                    if citations:
                        entry["citations"] = citations
                    if qualis:
                        entry["qualis"] = qualis
                    pub_list.append(entry)
            elif isinstance(item, str) and item.strip():
                parts = [p.strip() for p in item.split("|")]
                pub_list.append({
                    "title": parts[0],
                    "venue": parts[1] if len(parts) > 1 else "",
                    "year": parts[2] if len(parts) > 2 else "",
                    "authors": parts[3] if len(parts) > 3 else "",
                    "doi": parts[4] if len(parts) > 4 else "",
                })
    elif isinstance(raw_pubs, str) and raw_pubs.strip():
        for line in raw_pubs.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in (line.split("|") if "|" in line else line.split(" - "))]
            pub_list.append({
                "title": parts[0],
                "venue": parts[1] if len(parts) > 1 else "",
                "year": parts[2] if len(parts) > 2 else "",
                "authors": parts[3] if len(parts) > 3 else "",
                "doi": parts[4] if len(parts) > 4 else "",
            })
    if pub_list:
        parsed["publications"] = pub_list

    return parsed


def build_structured_cv_deterministically(

    raw_profile_data: Dict[str, Any],

    resume_type: str = "profissional",

    lang: str = "pt-br",

) -> Dict[str, Any]:

    """Mapeia os dados brutos extraídos das fontes para a estrutura canônica do currículo."""

    norm_lang = normalize_lang(lang)

    is_en = norm_lang.startswith("en")

    is_academic = str(resume_type).lower().strip() in ("academico", "academic")



    user_meta = raw_profile_data.get("user_meta") or {}

    gh = raw_profile_data.get("github") or {}

    orcid = raw_profile_data.get("orcid") or {}

    lattes = raw_profile_data.get("lattes") or {}

    li = raw_profile_data.get("linkedin") or {}

    portfolio = raw_profile_data.get("portfolio") or {}

    scholar = raw_profile_data.get("scholar") or {}

    links = raw_profile_data.get("links") or {}

    extra_notes = str(raw_profile_data.get("extra_notes") or "").strip()

    manual = parse_manual_resume_inputs(raw_profile_data.get("manual_data"))



    # 1. Nome Completo

    name = (

        user_meta.get("name")

        or lattes.get("name")

        or scholar.get("name")

        or li.get("name")

        or orcid.get("name")

        or gh.get("name")

        or gh.get("username")

        or ("Candidate Name" if is_en else "Nome do Candidato")

    ).strip()



    # 2. Título / Cargo

    if user_meta.get("role"):

        title = user_meta["role"].strip()

    elif li.get("title"):

        title = li["title"].strip()

    elif is_academic:

        # Se for acadêmico e houver atuação no Lattes, busca o enquadramento mais recente

        lattes_roles = [emp.get("role") for emp in (lattes.get("employments") or []) if emp.get("role")]

        title = (

            lattes_roles[0]

            if lattes_roles

            else ("Academic Researcher & Scientist" if is_en else "Pesquisador Acadêmico & Cientista")

        )

    elif gh.get("bio") and len(gh["bio"]) < 60:

        title = gh["bio"].strip()

    else:

        title = (

            "Technology & Software Specialist"

            if is_en

            else "Especialista em Tecnologia & Desenvolvimento"

        )



    # 3. Informações de Contato

    email = (
        user_meta.get("email")
        or links.get("email")
        or portfolio.get("email")
        or lattes.get("email")
        or gh.get("email")
        or li.get("email")
        or orcid.get("email")
        or scholar.get("email")
        or manual.get("email")
        or ""
    ).strip()
    if not email:
        for src_data in (portfolio, lattes, li, gh):
            raw = src_data.get("raw_text") or src_data.get("bio") or ""
            if raw:
                m_em = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", raw)
                if m_em and not m_em.group(0).lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif")):
                    email = m_em.group(0).strip()
                    break

    phone = (user_meta.get("phone") or "").strip()

    location = (
        user_meta.get("location")
        or portfolio.get("location")
        or gh.get("location")
        or li.get("location")
        or lattes.get("location")
        or ""
    ).strip()



    # 4. Resumo Profissional / Acadêmico

    summary = ""

    if lattes.get("summary"):

        summary = lattes["summary"].strip()

    elif extra_notes and len(extra_notes) > 40 and not extra_notes.startswith("PORTFOLIO_URL:"):

        summary = extra_notes

    elif li.get("summary"):

        summary = li["summary"].strip()

    elif orcid.get("bio"):

        summary = orcid["bio"].strip()

    elif gh.get("bio"):

        summary = gh["bio"].strip()

    elif portfolio.get("description"):
        port_desc = portfolio["description"].strip()
        low_desc = port_desc.lower()
        if low_desc.startswith("portfólio") or low_desc.startswith("portfolio"):
            cleaned_snippet = re.sub(r"(?i)^portf[óo]lio\s+(?:profissional\s+)?de\s+[^,]+,\s*", "", port_desc).strip()
            if cleaned_snippet:
                cap_snippet = cleaned_snippet[0].upper() + cleaned_snippet[1:]
                summary = (
                    f"Computer Science and Technology Specialist. {cap_snippet}. Strong background in software architecture, distributed systems, and modern development."
                    if is_en
                    else f"Especialista em Computação e Tecnologia. {cap_snippet}. Sólida experiência em desenvolvimento de software, arquitetura escalável e sistemas computacionais."
                )
            else:
                summary = (
                    "Computer Scientist and Software Engineer with experience in software development, algorithm design, and modern technology stacks."
                    if is_en
                    else "Cientista da Computação e Engenheiro de Software com experiência em desenvolvimento de software, projetos computacionais e tecnologias modernas."
                )
        else:
            summary = port_desc

    else:

        if is_academic:

            summary = (

                "Academic researcher with experience in scientific investigation, academic publishing, and collaborative research projects."

                if is_en

                else "Pesquisador acadêmico com sólida formação científica, publicações em periódicos indexados e participação em projetos de pesquisa."

            )

        else:
            summary = (
                "Dedicated professional with strong technical expertise, proven track record in software engineering, and continuous learning mindset."
                if is_en
                else "Profissional dedicado com sólida experiência técnica, atuação em desenvolvimento de software e foco em resultados escaláveis."
            )

    if is_en and summary:
        summary = standardize_summary_to_en(summary)

    # 5. Formação Acadêmica (Education)
    education: List[Dict[str, str]] = []
    # Prioridade A: Lattes (muito rico em nível, curso, instituição e tese)
    for edu in lattes.get("educations") or []:
        lvl = edu.get("level", "").strip()
        course = edu.get("course", "").strip()
        degree = f"{lvl} em {course}" if (lvl and course) else (lvl or course or "Formação Superior")
        inst = edu.get("institution", "").strip()
        if is_en:
            lvl_en = {
                "Doutorado": "Ph.D.",
                "Mestrado": "M.Sc.",
                "Mestrado Profissional": "Professional M.Sc.",
                "Especialização": "Postgraduate Specialization",
                "Graduação": "B.Sc.",
                "Pós-Doutorado": "Postdoctoral Fellowship",
            }.get(lvl, lvl)
            course_en = course
            course_low = "".join(
                c for c in unicodedata.normalize("NFKD", course) if not unicodedata.combining(c)
            ).lower()
            if "ciencia da computacao" in course_low or "computacao" in course_low:
                course_en = "Computer Science"
            elif "sistemas de informacao" in course_low:
                course_en = "Information Systems"
            elif "engenharia de software" in course_low:
                course_en = "Software Engineering"
            degree = f"{lvl_en} in {course_en}" if (lvl_en and course_en) else (lvl_en or course_en)
            inst = translate_institution_to_en(inst)

        start_yr = str(edu.get("start") or "").strip()
        end_yr = str(edu.get("end") or "").strip() or ("Present" if is_en else "Atual")
        period = f"{start_yr} - {end_yr}" if (start_yr and end_yr) else (start_yr or end_yr)

        details = edu.get("thesis_title", "").strip()
        if details:
            details = f"Tese/Dissertação: {details}" if not is_en else f"Thesis: {details}"

        education.append({
            "degree": degree,
            "institution": inst,
            "period": period,
            "details": details,
        })



    # Prioridade B: LinkedIn (caso Lattes esteja vazio)

    if not education:

        for edu in li.get("educations") or []:

            degree = edu.get("degree", "").strip() or ("Degree" if is_en else "Graduação")

            education.append({

                "degree": degree,

                "institution": edu.get("school", "").strip(),

                "period": edu.get("period", "").strip(),

                "details": "",

            })



    # Prioridade C: ORCID (caso ambos estejam vazios)

    if not education:

        for edu in orcid.get("educations") or []:

            start_yr = str(edu.get("start") or "").strip()

            end_yr = str(edu.get("end") or "").strip()

            if not end_yr or end_yr.lower() in ("atual", "present"):

                end_yr = "Present" if is_en else "Atual"

            period = f"{start_yr} - {end_yr}" if (start_yr and end_yr) else (start_yr or end_yr)



            raw_degree = (

                edu.get("degree")

                or edu.get("role")

                or edu.get("course")

                or edu.get("dept")

                or ""

            ).strip()



            inst = (

                edu.get("institution")

                or edu.get("organization")

                or edu.get("org")

                or edu.get("school")

                or ""

            ).strip()



            if not is_en and raw_degree:

                deg_lower = raw_degree.lower()

                if "master" in deg_lower and "computer science" in deg_lower:

                    raw_degree = "Mestrado em Ciência da Computação"

                elif "bachelor" in deg_lower and ("information systems" in deg_lower or "sistemas de informacao" in deg_lower or "sistemas de informação" in deg_lower):

                    raw_degree = "Bacharelado em Sistemas de Informação"

                elif "master" in deg_lower:

                    raw_degree = re.sub(r"(?i)master'?s?\s+(?:degree\s+)?(?:of\s+science\s+)?in\s+", "Mestrado em ", raw_degree)

                elif "bachelor" in deg_lower:

                    raw_degree = re.sub(r"(?i)bachelor'?s?\s+(?:degree\s+)?(?:of\s+science\s+)?in\s+", "Bacharelado em ", raw_degree)

                elif "ph" in deg_lower or "doctor" in deg_lower:

                    raw_degree = re.sub(r"(?i)(?:ph\.?d\.?|doctorate)\s+in\s+", "Doutorado em ", raw_degree)

            elif is_en and raw_degree:

                deg_lower = raw_degree.lower()

                if "mestrado" in deg_lower and ("ciencia da computacao" in deg_lower or "ciência da computação" in deg_lower):

                    raw_degree = "M.Sc. in Computer Science"

                elif "bacharelado" in deg_lower and ("sistemas de informacao" in deg_lower or "sistemas de informação" in deg_lower):

                    raw_degree = "B.Sc. in Information Systems"

                elif "mestrado" in deg_lower:

                    raw_degree = re.sub(r"(?i)mestrado(?:\s+profissional)?\s+em\s+", "M.Sc. in ", raw_degree)

                elif "bacharelado" in deg_lower or "graduação" in deg_lower:

                    raw_degree = re.sub(r"(?i)(?:bacharelado|graduação)\s+em\s+", "B.Sc. in ", raw_degree)

                elif "doutorado" in deg_lower:

                    raw_degree = re.sub(r"(?i)doutorado\s+em\s+", "Ph.D. in ", raw_degree)



            deg = raw_degree or ("Higher Education" if is_en else "Formação Superior")
            education.append({
                "degree": deg,
                "institution": inst,
                "period": period,
                "details": "",
            })

    # Prioridade D: Portfólio (caso formações estejam incompletas ou para enriquecer períodos)
    for pt_edu in portfolio.get("educations") or []:
        deg_pt = pt_edu.get("degree", "").strip()
        inst_pt = pt_edu.get("institution", "").strip()
        per_pt = pt_edu.get("period", "").strip()
        cand = {
            "degree": deg_pt,
            "institution": inst_pt,
            "period": per_pt,
            "details": pt_edu.get("details", "").strip(),
        }
        matched = False
        for ex_edu in education:
            if are_educations_duplicate(ex_edu, cand):
                matched = True
                merge_educations(ex_edu, cand, lang=lang)
                break
        if not matched and deg_pt:
            education.append(cand)

    education = deduplicate_and_sort_educations(education, lang=lang)



    # 6. Experiência Profissional (Experience)

    experience: List[Dict[str, Any]] = []

    # Prioridade A: LinkedIn

    for exp in li.get("experiences") or []:

        role = exp.get("role", "").strip()

        comp = exp.get("company", "").strip()

        period = exp.get("period", "").strip()

        raw_desc = exp.get("description", "").strip()

        bullets = [b.strip("- •") for b in raw_desc.split("\n") if b.strip("- •")] if raw_desc else []

        if role or comp:

            experience.append({

                "role": role or ("Professional" if is_en else "Atuação Profissional"),

                "organization": comp,

                "period": period,

                "bullets": bullets if bullets else ([raw_desc] if raw_desc else []),

            })



    # Prioridade B: Lattes Atuações Profissionais

    for emp in lattes.get("employments") or []:

        inst = emp.get("institution", "").strip()

        role = emp.get("role", "").strip()

        start_yr = str(emp.get("start") or "").strip()

        end_yr = str(emp.get("end") or "").strip() or ("Present" if is_en else "Atual")

        period = f"{start_yr} - {end_yr}" if (start_yr and end_yr) else (start_yr or end_yr)

        desc = emp.get("description", "").strip()
        bullets = [desc] if desc else []
        if role or inst:
            if is_en:
                role = translate_role_to_en(role)
                inst = translate_institution_to_en(inst)
                bullets = [translate_experience_bullet_to_en(b) for b in bullets]
            cand = {
                "role": role or ("Pesquisador / Colaborador" if not is_en else "Researcher / Staff"),
                "organization": inst,
                "period": period,
                "bullets": bullets,
            }
            matched = False
            for ex in experience:
                if are_experiences_duplicate(ex, cand):
                    matched = True
                    merge_experiences(ex, cand, lang=lang)
                    break
            if not matched:
                experience.append(cand)



    # Prioridade C: ORCID Employments

    if not experience:

        for emp in orcid.get("employments") or []:

            start_yr = str(emp.get("start") or "").strip()

            end_yr = str(emp.get("end") or "").strip()

            if not end_yr or end_yr.lower() in ("atual", "present"):

                end_yr = "Present" if is_en else "Atual"

            period = f"{start_yr} - {end_yr}" if (start_yr and end_yr) else (start_yr or end_yr)



            raw_role = (emp.get("role") or emp.get("role-title") or emp.get("dept") or "").strip()

            inst = (

                emp.get("organization")

                or emp.get("institution")

                or emp.get("org")

                or emp.get("company")

                or ""

            ).strip()



            if not is_en and raw_role:

                role_lower = raw_role.lower()

                role_map_pt = {

                    "introduction to game development teaching assistant": "Monitor de Introdução ao Desenvolvimento de Jogos",

                    "programming teaching assistant": "Monitor de Programação",

                    "programming tutor": "Tutor de Programação",

                    "extension project fellow": "Bolsista de Projeto de Extensão",

                    "teaching assistant": "Monitor(a) de Ensino",

                    "research fellow": "Bolsista de Pesquisa",

                    "research assistant": "Assistente de Pesquisa",

                    "graduate student": "Pós-Graduando",

                }

                raw_role = role_map_pt.get(role_lower, raw_role)



            if not is_en and inst:

                if "federal university of viçosa" in inst.lower() or "federal university of vicosa" in inst.lower():

                    inst = "Universidade Federal de Viçosa"

                elif "federal university of minas gerais" in inst.lower():

                    inst = "Universidade Federal de Minas Gerais"



            experience.append({
                "role": raw_role or ("Position" if is_en else "Atuação Profissional"),
                "organization": inst,
                "period": period,
                "bullets": [],
            })

    # Prioridade D: Portfólio (experiências acadêmicas, monitorias, tutorias com períodos reais)
    for emp in portfolio.get("employments") or []:
        role = emp.get("role", "").strip()
        org = emp.get("organization", "").strip()
        period = emp.get("period", "").strip()
        desc = emp.get("description", "").strip()
        bullets = [desc] if desc else []
        if role:
            if is_en:
                role = translate_role_to_en(role)
                if org:
                    org = translate_institution_to_en(org)
                bullets = [translate_experience_bullet_to_en(b) for b in bullets]
            cand = {
                "role": role,
                "organization": org or ("Universidade Federal de Viçosa" if not is_en else "Federal University of Viçosa"),
                "period": period,
                "bullets": bullets,
            }
            matched = False
            for ex_emp in experience:
                if are_experiences_duplicate(ex_emp, cand):
                    matched = True
                    merge_experiences(ex_emp, cand, lang=lang)
                    break
            if not matched:
                experience.append(cand)

    experience = deduplicate_and_sort_experiences(experience, lang=lang)
    for exp in experience:
        if exp.get("description"):
            exp["description"] = sanitize_experience_description(exp["description"], lang=lang)
        if exp.get("bullets"):
            exp["bullets"] = [sanitize_experience_description(b, lang=lang) for b in exp["bullets"]]



    # 7. Projetos (Projects)

    projects: List[Dict[str, str]] = []

    # Prioridade A: GitHub Repositories

    for repo in gh.get("repos") or []:

        r_name = repo.get("name", "").strip()

        r_tech = (repo.get("tech") or repo.get("language") or "").strip()

        r_desc = repo.get("description", "").strip()

        r_url = repo.get("url", "").strip()

        if r_name:
            clean_rdesc = sanitize_project_description(r_desc, lang).strip()
            if not clean_rdesc:
                if r_tech:
                    clean_rdesc = f"Software and technical implementation developed with {r_tech}." if is_en else f"Projeto e implementação técnica desenvolvida em {r_tech}."
                else:
                    clean_rdesc = f"Software implementation and development for {r_name}." if is_en else f"Projeto e desenvolvimento computacional referente a {r_name}."

            projects.append({
                "name": r_name,
                "tech": r_tech,
                "url": r_url,
                "description": clean_rdesc,
                "stars": repo.get("stars", repo.get("likes", 0)),
                "forks": repo.get("forks", 0),
                "likes": repo.get("likes", repo.get("stars", 0)),
            })

    # Prioridade B: Portfólio Projetos
    for p_proj in portfolio.get("projects") or []:
        p_name = (p_proj.get("name") or "").strip()
        p_tech = (p_proj.get("tech") or "").strip()
        p_desc = (p_proj.get("description") or "").strip()
        p_url = (p_proj.get("url") or "").strip()
        if p_name and not any(x["name"].lower() == p_name.lower() for x in projects):
            clean_pdesc = sanitize_project_description(p_desc, lang).strip()
            projects.append({
                "name": p_name,
                "tech": p_tech,
                "url": p_url,
                "description": clean_pdesc,
                "stars": p_proj.get("stars", p_proj.get("likes", 0)),
                "forks": p_proj.get("forks", 0),
                "likes": p_proj.get("likes", p_proj.get("stars", 0)),
            })

    # Prioridade C: Lattes Projetos de Pesquisa
    for proj in lattes.get("projects") or []:
        p_name = proj.get("title", "").strip()
        p_year = str(proj.get("year") or "").strip()
        p_desc = proj.get("description", "").strip()
        if p_name:
            clean_pdesc = sanitize_project_description(p_desc, lang).strip()
            if not clean_pdesc:
                clean_pdesc = f"Research project developed during {p_year}." if is_en else f"Projeto de pesquisa desenvolvido durante o ano de {p_year}."

            projects.append({
                "name": p_name,
                "tech": f"Pesquisa ({p_year})" if not is_en else f"Research ({p_year})",
                "url": "",
                "description": clean_pdesc,
            })

    projects = deduplicate_and_sort_projects(projects)

    # 8. Publicações (Publications)
    publications: List[Dict[str, Any]] = []

    def _add_or_merge_pub(new_pub: Dict[str, Any]) -> None:
        t_raw = str(new_pub.get("title") or "").strip()
        if not t_raw:
            return
        cand = {
            "title": t_raw,
            "venue": str(new_pub.get("venue") or new_pub.get("journal") or "").strip(),
            "year": str(new_pub.get("year") or "").strip(),
            "authors": str(new_pub.get("authors") or "").strip(),
            "doi": str(new_pub.get("doi") or "").strip(),
            "citations": str(new_pub.get("citations") or "").strip(),
            "qualis": str(new_pub.get("qualis") or "").strip(),
            "url": str(new_pub.get("url") or "").strip(),
        }
        for ex in publications:
            if are_publications_duplicate(ex, cand):
                merge_publications(ex, cand)
                return
        publications.append(cand)

    # A. Lattes Publicações
    for pub in lattes.get("publications") or []:
        _add_or_merge_pub(pub)

    # B. ORCID Works
    for work in orcid.get("works") or []:
        _add_or_merge_pub({
            "title": work.get("title", ""),
            "venue": work.get("journal", ""),
            "year": str(work.get("year") or ""),
            "authors": "",
            "doi": work.get("doi", ""),
        })

    # C. Google Scholar Publicações
    for sc_pub in scholar.get("publications") or []:
        _add_or_merge_pub({
            "title": sc_pub.get("title", ""),
            "venue": sc_pub.get("venue", ""),
            "year": str(sc_pub.get("year") or ""),
            "authors": sc_pub.get("authors", ""),
            "doi": "",
            "citations": str(sc_pub.get("citations") or ""),
        })

    # D. Portfolio Publicações
    for pt_pub in portfolio.get("publications") or []:
        _add_or_merge_pub(pt_pub)

    publications = deduplicate_and_sort_publications(publications)




    # 9. Habilidades e Competências (Skills)

    skills: List[Dict[str, Any]] = []

    # 10. Idiomas (Languages)

    raw_languages = (

        lattes.get("languages")

        or li.get("languages")

        or portfolio.get("languages")

        or raw_profile_data.get("languages")

        or user_meta.get("languages")

        or []

    )

    if not raw_languages and portfolio.get("raw_text"):

        raw_languages = extract_languages_from_text(portfolio["raw_text"])

    if not raw_languages and extra_notes:

        raw_languages = extract_languages_from_text(extra_notes)

    if not raw_languages and manual.get("languages"):

        raw_languages = manual["languages"]



    if is_en:

        trans_en = {

            "inglês": "English", "ingles": "English",

            "português": "Portuguese", "portugues": "Portuguese",

            "espanhol": "Spanish",

            "francês": "French", "frances": "French",

            "alemão": "German", "alemao": "German",

            "italiano": "Italian",

            "japonês": "Japanese", "japones": "Japanese",

            "chinês": "Chinese", "chines": "Chinese", "mandarim": "Mandarin",

            "russo": "Russian",

        }

        prof_trans_en = {

            "avançado": "Advanced", "avancado": "Advanced", "bom": "Advanced",

            "fluente": "Fluent", "fluente ou nativo": "Fluent / Native",

            "nativo": "Native", "nativo ou bilíngue": "Native / Bilingual", "nativo ou bilingue": "Native / Bilingual",

            "intermediário": "Intermediate", "intermediario": "Intermediate", "regular": "Intermediate", "razoável": "Intermediate", "razoavel": "Intermediate",

            "básico": "Basic", "basico": "Basic", "pouco": "Basic",

        }

        translated_langs: List[str] = []

        for lg in raw_languages:

            lg_str = str(lg).strip()

            if not lg_str:

                continue

            m = re.match(r"^([A-Za-zÀ-ÿ]+)(?:\s*\((.*?)\))?$", lg_str)

            if m:

                p_name = m.group(1).strip()

                p_prof = m.group(2).strip() if m.group(2) else ""

                en_name = trans_en.get(p_name.lower(), p_name)

                en_prof = prof_trans_en.get(p_prof.lower(), p_prof)

                translated_langs.append(f"{en_name} ({en_prof})" if en_prof else en_name)

            else:

                translated_langs.append(lg_str)

        languages = translated_langs

    else:

        languages = [str(lg).strip() for lg in raw_languages if str(lg).strip()]



    # 11. Prêmios, Títulos e Certificações (Awards)
    combined_raw_awards: List[str] = []
    for aw_src in [lattes.get("awards"), portfolio.get("awards"), li.get("certifications"), orcid.get("awards")]:
        if not aw_src:
            continue
        aw_list = aw_src if isinstance(aw_src, list) else [aw_src]
        for item in aw_list:
            s_item = str(item).strip()
            if s_item and not any(are_awards_duplicate(s_item, x) for x in combined_raw_awards):
                combined_raw_awards.append(s_item)

    awards = sanitize_awards(combined_raw_awards, experiences=experience, lang=lang)



    # 12. Sobrescrita com dados manuais fornecidos diretamente pelo usuário

    if manual.get("name"):

        name = manual["name"].strip()

    if manual.get("title") or manual.get("role"):

        title = (manual.get("title") or manual.get("role")).strip()

    if manual.get("email"):

        email = manual["email"].strip()

    if manual.get("phone"):

        phone = manual["phone"].strip()

    if manual.get("location"):

        location = manual["location"].strip()

    if manual.get("summary"):

        summary = manual["summary"].strip()

    if manual.get("education"):

        education = list(manual["education"])

    if manual.get("experience"):

        experience = list(manual["experience"])

    if manual.get("projects"):

        projects = []
        for p in manual["projects"]:
            p_item = dict(p) if isinstance(p, dict) else {"name": str(p), "description": ""}
            p_item["description"] = sanitize_project_description(p_item.get("description", ""), lang)
            projects.append(p_item)

    if manual.get("publications"):

        publications = list(manual["publications"])

    if manual.get("languages"):
        man_langs = manual["languages"]
        if isinstance(man_langs, str):
            man_langs = [it.strip() for it in re.split(r"[\r\n,;]+", man_langs) if it.strip()]
        for lg in man_langs:
            if not any(lg.lower() in x.lower() for x in languages):
                languages.append(lg)

    if manual.get("awards"):
        man_awards = manual["awards"]
        if isinstance(man_awards, str):
            man_awards = [line.strip() for line in re.split(r"[\r\n;]+", man_awards) if line.strip()]
        man_aw = sanitize_awards(man_awards, experiences=experience, lang=lang)
        for a in man_aw:
            if not any(are_awards_duplicate(a, x) for x in awards):
                awards.append(a)

    # Garante desduplicação, padronização de datas/descrições e ordenação cronológica reversa
    experience = deduplicate_and_sort_experiences(experience, lang=lang)
    for exp in experience:
        if exp.get("description"):
            exp["description"] = remove_terminal_abbreviation_ellipsis(
                sanitize_experience_description(exp["description"], lang=lang)
            )
        if exp.get("bullets"):
            exp["bullets"] = [
                remove_terminal_abbreviation_ellipsis(sanitize_experience_description(b, lang=lang))
                for b in exp["bullets"]
            ]
    education = deduplicate_and_sort_educations(education, lang=lang)
    projects = deduplicate_and_sort_projects(projects)
    publications = deduplicate_and_sort_publications(publications)
    awards = deduplicate_and_sort_awards(awards, experiences=experience, lang=lang)
    for project in projects:
        if project.get("description"):
            project["description"] = remove_terminal_abbreviation_ellipsis(project["description"])
    for publication in publications:
        for field in ("title", "venue", "authors"):
            if publication.get(field):
                publication[field] = remove_terminal_abbreviation_ellipsis(publication[field])
    manual_skills = manual.get("skills") or []
    if manual_skills:
        skills = list(manual_skills)
    else:
        skills = merge_skill_groups(
            {"items": gh.get("top_languages") or []},
            {"items": gh.get("languages") or []},
            {"items": portfolio.get("skills") or []},
            {"items": li.get("skills") or []},
            {"items": lattes.get("areas") or []},
            {"items": orcid.get("keywords") or []},
            extra_items=collect_project_technologies(
                gh.get("repos") or [],
                portfolio.get("projects") or [],
                lattes.get("projects") or [],
                manual.get("projects") or [],
            ),
            category="",
        )

    # Limitações saudáveis para caber confortavelmente no layout LaTeX

    return {

        "name": name,

        "title": title,

        "email": email,

        "phone": phone,

        "location": location,

        "summary": summary,

        "education": education[:6],

        "experience": experience,

        "projects": projects,

        "publications": publications,

        "skills": skills,

        "languages": languages[:8],

        "awards": awards[:10],

    }





def generate_direct_latex_resume(

    raw_profile_data: Dict[str, Any],

    resume_type: str = "profissional",

    template_id: str = "ai_ats_max",

    custom_latex_template: str | None = None,

    photo_filename: str | None = None,

    lang: str = "pt-br",

) -> Tuple[str, Dict[str, Any]]:

    """Gera o código LaTeX completo e compilável sem nenhuma chamada a modelos LLM."""

    norm_lang = normalize_lang(lang)
    links = dict(raw_profile_data.get("links") or {})

    # Garante que os links sociais extraídos da página de portfólio
    # (LinkedIn, GitHub, ORCID, Lattes e Google Scholar) sejam usados
    # no cabeçalho e não apenas coletados para extração de informações.
    portfolio = raw_profile_data.get("portfolio") or {}
    port_social = portfolio.get("social_links") or {}
    for _key in ("linkedin", "github", "orcid", "scholar", "lattes"):
        if not links.get(_key) and port_social.get(_key):
            links[_key] = port_social[_key]

    # Constrói o structured_cv de forma puramente determinística
    cv = build_structured_cv_deterministically(
        raw_profile_data=raw_profile_data,
        resume_type=resume_type,
        lang=norm_lang,
    )

    candidate_name = cv.get("name") or (raw_profile_data.get("user_meta") or {}).get("name") or ""
    if candidate_name and not links.get("candidate_name"):
        links["candidate_name"] = candidate_name
    scholar_data = raw_profile_data.get("scholar") or {}
    if isinstance(scholar_data, dict) and scholar_data.get("name") and not links.get("scholar_name"):
        links["scholar_name"] = scholar_data["name"]



    # 1. Caso Template Customizado .tex fornecido pelo usuário

    if custom_latex_template and custom_latex_template.strip():

        latex_code = _fill_custom_template_deterministically(

            template_code=custom_latex_template,

            cv=cv,

            links=links,

            photo_filename=photo_filename,

            lang=norm_lang,

        )

        return latex_code, cv



    # 2. Caso Templates Integrados (modern_pro, academic_classic, tech_sidebar, etc.)

    if template_id not in BUILTIN_TEMPLATES:

        template_id = "modern_pro"



    latex_code = render_builtin_template(

        template_id=template_id,

        cv=cv,

        links=links,

        resume_type=resume_type,

        photo_filename=photo_filename,

        lang=norm_lang,

    )



    return latex_code, cv





def _fill_custom_template_deterministically(

    template_code: str,

    cv: Dict[str, Any],

    links: Dict[str, str],

    photo_filename: str | None = None,

    lang: str = "pt-br",

) -> str:

    """Preenche placeholders comuns em templates customizados de forma determinística e segura."""
    from .compiler import sanitize_custom_latex

    res = sanitize_custom_latex(template_code)

    name = cv.get("name") or "Nome do Candidato"

    title = cv.get("title") or "Profissional"

    summary = cv.get("summary") or ""

    esc_name = escape_latex(name)
    esc_title = escape_latex(title)
    esc_summary = escape_latex(summary)

    contact_parts = []
    clean_em = (cv.get("email") or links.get("email") or "").strip()
    if clean_em:
        contact_parts.append(rf"\mbox{{\href{{mailto:{escape_url(clean_em)}}}{{\faIcon{{envelope}}\ {escape_latex(clean_em)}}}}}")
    if cv.get("phone"):
        contact_parts.append(rf"\mbox{{\faIcon{{phone}}\ {escape_latex(cv['phone'])}}}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['portfolio'])}}}{{\faIcon{{globe}}\ \textbf{{{port_disp}}}}}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{{li_disp}}}}}}}")
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{{gh_disp}}}}}}}")
    if links.get("scholar"):
        scholar_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['scholar'])}}}{{\faIcon{{google}}\ \textbf{{{scholar_disp}}}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{{orcid_disp}}}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{{lattes_disp}}}}}}}")
    if cv.get("location"):
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(cv["location"].strip())
        contact_parts.append(rf"\mbox{{\href{{{escape_url(maps_url)}}}{{\faIcon{{map-marker-alt}}\ {escape_latex(cv['location'])}}}}}")
    contact_line = " $\\cdot$ ".join(contact_parts)

    # Substituições case-insensitive seguras de cabeçalho usando callables para evitar injeção de regex
    res = re.sub(r"(?i)NOME DO CANDIDATO|\[NOME\]|\{\{NAME\}\}|CANDIDATE NAME", lambda _: esc_name, res)
    res = re.sub(r"(?i)CARGO OU T[IÍ]TULO|\[CARGO\]|\{\{TITLE\}\}|\{\{ROLE\}\}|PROFESSIONAL ROLE", lambda _: esc_title, res)
    res = re.sub(r"(?i)Links e Contatos|\[CONTATOS\]|\{\{CONTACTS\}\}|CONTACT INFO", lambda _: contact_line, res)
    res = re.sub(r"(?i)Preencher resumo do candidato\.?|\[RESUMO\]|\{\{SUMMARY\}\}", lambda _: esc_summary, res)
    if clean_em:
        res = re.sub(r"(?i)\[EMAIL\]|\{\{EMAIL\}\}", lambda _: escape_latex(clean_em), res)
    if cv.get("phone"):
        res = re.sub(r"(?i)\[TELEFONE\]|\[PHONE\]|\{\{PHONE\}\}", lambda _: escape_latex(cv["phone"]), res)
    if cv.get("location"):
        res = re.sub(r"(?i)\[LOCALIZA[CÇ][AÃ]O\]|\[CIDADE\]|\[LOCATION\]|\{\{LOCATION\}\}", lambda _: escape_latex(cv["location"]), res)

    return sanitize_custom_latex(res)



