"""Cliente multi-provedor (NVIDIA NIM, Google Gemini, Anthropic Claude, OpenAI, DeepSeek)
integrado ao cofre criptográfico efêmero e aos Plugins de Economia de Tokens.
"""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)
from typing import Any, Dict, List, Tuple

from ._vault import dispatch_secure_llm_chat
from .compiler import sanitize_latex_layout
from .extractors import sanitize_project_description, sanitize_experience_description
from .skills import collect_project_technologies, merge_skill_groups
from .text_utils import remove_terminal_abbreviation_ellipsis
from .config import DEFAULT_MODEL, DEFAULT_PROVIDER, PROVIDERS_CONFIG
from .templates import (
    deduplicate_and_sort_awards,
    deduplicate_and_sort_educations,
    deduplicate_and_sort_experiences,
    deduplicate_and_sort_publications,
    render_builtin_template,
    sanitize_awards,
)
from .token_plugins import (
    CavemanPromptPlugin,
    LaTeXPreambleSplitPlugin,
    SHA256DiskCachePlugin,
    ShortKeySchemaPlugin,
    ThinkingSuppressionPlugin,
    TokenMetrics,
    TOONContextPrunerPlugin,
    diagnose_fallback_reason,
    estimate_tokens,
)


class LLMResumeGenerator:
    """Orquestrador multi-provedor para síntese de currículos com isolamento seguro de chaves e economia de tokens."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        api_key: str | None = None,
        model: str | None = None,
        use_cache: bool = False,
        use_token_plugins: Dict[str, bool] | None = None,
    ) -> None:
        self.provider = (provider or DEFAULT_PROVIDER).strip().lower()
        self._custom_key = api_key.strip() if api_key and api_key.strip() else None

        prov_cfg = PROVIDERS_CONFIG.get(self.provider, PROVIDERS_CONFIG["default"])
        self.model = model or prov_cfg.get("default_model") or DEFAULT_MODEL
        self.use_cache = use_cache and (use_token_plugins or {}).get("cache", True)
        self.cache = SHA256DiskCachePlugin()
        self.use_token_plugins = use_token_plugins or {
            "caveman": True,
            "thinking": True,
            "toon": True,
            "shortkey": True,
            "preamble": True,
            "cache": True,
        }

    def _call_llm_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1600,
    ) -> Tuple[str, Dict[str, Any], str, bool]:
        """Executa chamada segura ao provedor selecionado via TLS 1.3 e cofre em memória volátil."""
        cache_key = self.cache.make_key(f"{self.provider}:{self.model}", messages)
        is_latex_call = any(
            "\\begin{document}" in m.get("content", "") or "CAVEMAN_LATEX" in m.get("content", "")
            for m in messages
        )
        if self.use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                if not is_latex_call or r"\end{document}" in cached:
                    return cached, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, self.model, True

        prov_cfg = PROVIDERS_CONFIG.get(self.provider, PROVIDERS_CONFIG["default"])
        available_models = [m["id"] for m in prov_cfg.get("models", []) if m.get("id")]
        fallback_candidates = [m for m in available_models if m != self.model]
        # Limita a no máximo 1 fallback model para evitar tempos excessivos que estourem o gateway do Render (100s)
        models_to_try = [self.model] + fallback_candidates[:1]

        last_err = None
        for idx, candidate_model in enumerate(models_to_try):
            # Modelo primário: até 35s (evita estourar o limite de 100s do gateway Render); fallback: até 20s
            req_timeout = 35 if idx == 0 else 20
            status_code, parsed_data, err_str, usage = dispatch_secure_llm_chat(
                provider=self.provider,
                model=candidate_model,
                messages=messages,
                custom_key=self._custom_key,
                max_tokens=max_tokens,
                timeout=req_timeout,
            )
            if status_code != 200:
                last_err = err_str
                continue

            content = (parsed_data.get("content") or "").strip()
            if not content:
                last_err = f"Modelo {candidate_model} retornou conteúdo vazio"
                continue

            if is_latex_call and r"\end{document}" not in content:
                # Se o modelo gerou a quase totalidade do corpo (>1200 chars) e tem \begin{document}, auto-fecha com segurança
                if r"\begin{document}" in content and len(content) > 1200:
                    content = content.rstrip() + "\n\\end{document}\n"
                else:
                    last_err = f"Modelo {candidate_model} retornou resposta LaTeX truncada (sem \\end{{document}})"
                    continue

            if self.use_cache and content:
                self.cache.set(cache_key, content, candidate_model)
            return content, usage, candidate_model, False

        raise RuntimeError(
            f"Falha ao chamar modelos do provedor '{self.provider}'. Último status: {last_err}"
        )

    def generate_latex_resume(
        self,
        raw_profile_data: Dict[str, Any],
        resume_type: str = "profissional",
        template_id: str = "ai_ats_max",
        custom_latex_template: str | None = None,
        photo_filename: str | None = None,
        lang: str = "pt-br",
    ) -> Tuple[str, Dict[str, Any], TokenMetrics]:
        """Gera o código LaTeX final, o dicionário estruturado do CV e as métricas de tokens."""
        p = self.use_token_plugins
        metrics = TokenMetrics(
            active_plugins=[
                plugin for plugin, enabled in [
                    (CavemanPromptPlugin.name, p.get("caveman", True)),
                    (ThinkingSuppressionPlugin.name, p.get("thinking", True)),
                    (TOONContextPrunerPlugin.name, p.get("toon", True)),
                ] if enabled
            ]
        )

        # 1. Plugin TOON: comprime os dados de entrada (GitHub, ORCID, Lattes, LinkedIn, Portfólio)
        if p.get("toon", True):
            toon_context, raw_in_tok, comp_in_tok = TOONContextPrunerPlugin.compress_profile_data(raw_profile_data)
        else:
            toon_context = json.dumps(raw_profile_data, ensure_ascii=False)
            raw_in_tok = estimate_tokens(toon_context)
            comp_in_tok = raw_in_tok
        metrics.raw_input_tokens_est = raw_in_tok
        metrics.compressed_input_tokens_est = comp_in_tok

        links = raw_profile_data.get("links") or {}

        # 2. Modo Template Customizado (.tex fornecido pelo usuário)
        if custom_latex_template and custom_latex_template.strip():
            if p.get("preamble", True):
                metrics.active_plugins.append(LaTeXPreambleSplitPlugin.name)
            if p.get("cache", True) and self.use_cache:
                metrics.active_plugins.append(SHA256DiskCachePlugin.name)

            if p.get("preamble", True):
                preamble, body_template, custom_cmds = LaTeXPreambleSplitPlugin.split_template(
                    custom_latex_template
                )
            else:
                preamble, body_template, custom_cmds = "", custom_latex_template, []
            preamble_tokens_saved = estimate_tokens(preamble) * 2

            if p.get("caveman", True):
                sys_prompt = CavemanPromptPlugin.build_system_prompt(resume_type, output_mode="latex", lang=lang)
            else:
                sys_prompt = (
                    f"Role: Expert LaTeX Architect & CV Synthesizer. "
                    f"Write resume content in {lang}. "
                    f"Emit ONLY valid compilable LaTeX code."
                )
            photo_instr = (
                f"Foto disponível no arquivo '{photo_filename}' (use \\includegraphics se o template suportar)."
                if photo_filename
                else "Sem foto enviada (remova/comente comandos de foto se houver no template)."
            )
            cmd_hint = f"Macros do preâmbulo: {', '.join(custom_cmds[:15])}\n" if custom_cmds else ""
            user_prompt = (
                f"LANG:{lang.upper()}|TIPO:{resume_type.upper()}\n"
                f"LINKS:LI={links.get('linkedin','')}|GH={links.get('github','')}|"
                f"ORCID={links.get('orcid','')}|LATTES={links.get('lattes','')}\n"
                f"{photo_instr}\n"
                f"{cmd_hint}"
                f"DADOS_PERFIL_TOON:\n{toon_context}\n\n"
                f"CORPO_TEMPLATE_LATEX:\n{body_template}\n\n"
                "Preencha o CORPO_TEMPLATE_LATEX com os DADOS_PERFIL_TOON reais. "
                "Retorne SOMENTE de \\begin{document} até \\end{document}."
            )

            content, usage, used_model, is_cached = self._call_llm_chat(
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=2500,
            )
            clean_body = sanitize_latex_layout(
                CavemanPromptPlugin.strip_code_fences(content) if p.get("caveman", True) else content
            )
            if not clean_body or len(clean_body.strip()) < 30 or r"\end{document}" not in clean_body:
                raise ValueError("Resposta do modelo insuficiente ou incompleta (sem \\end{document}).")
            if p.get("preamble", True):
                final_latex = sanitize_latex_layout(LaTeXPreambleSplitPlugin.reassemble(preamble, clean_body))
            else:
                final_latex = sanitize_latex_layout(clean_body)
            if r"\end{document}" not in final_latex:
                final_latex = final_latex.rstrip() + "\n\\end{document}\n"
            self._populate_metrics(
                metrics,
                usage,
                used_model,
                is_cached,
                extra_saved=max(0, raw_in_tok - comp_in_tok) + preamble_tokens_saved + 600,
            )
            return final_latex, {"custom_template": True, "lang": lang}, metrics

        # 3. Modo Templates Integrados: Usa ShortKeySchemaPlugin + Renderização Local LaTeX
        if p.get("shortkey", True):
            metrics.active_plugins.append(ShortKeySchemaPlugin.name)
        metrics.active_plugins.append("LaTeXLocalSkeletonPlugin (0-token LaTeX Preamble)")
        if p.get("cache", True) and self.use_cache:
            metrics.active_plugins.append(SHA256DiskCachePlugin.name)

        if p.get("caveman", True):
            sys_prompt = CavemanPromptPlugin.build_system_prompt(resume_type, output_mode="json", lang=lang)
        else:
            sys_prompt = (
                f"Role: Senior CV synthesizer. "
                f"Write all resume text values in polished, high-impact {lang}. "
                f"Emit ONLY raw minified JSON matching requested short keys."
            )
        if p.get("toon", True):
            toon_prompt_part = f"DADOS_TOON:\n{toon_context}\n\n"
        else:
            toon_prompt_part = f"DADOS_PERFIL:\n{json.dumps(raw_profile_data, ensure_ascii=False)}\n\n"
        if p.get("shortkey", True):
            schema_part = f"{ShortKeySchemaPlugin.PROMPT_SCHEMA_INSTRUCTION}"
        else:
            schema_part = (
                'Retorne um objeto JSON com os campos: nm, tl, em, ph, lc, sm, ed, xp, pj, pb, sk, lg, aw.\n'
            )
        user_prompt = (
            f"LANG:{lang.upper()}|TIPO:{resume_type.upper()}\n"
            f"{toon_prompt_part}"
            f"{schema_part}"
        )

        content, usage, used_model, is_cached = self._call_llm_chat(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=3000,
        )

        short_dict = self._parse_json_safely(content, raw_profile_data, resume_type)
        structured_cv = ShortKeySchemaPlugin.expand(short_dict)
        self._apply_fallbacks(structured_cv, raw_profile_data, resume_type, lang)

        final_latex = render_builtin_template(
            template_id=template_id,
            cv=structured_cv,
            links=links,
            resume_type=resume_type,
            photo_filename=photo_filename,
            lang=lang,
        )

        extra_saved = max(0, raw_in_tok - comp_in_tok) + 1150
        self._populate_metrics(metrics, usage, used_model, is_cached, extra_saved=extra_saved)
        return final_latex, structured_cv, metrics

    def repair_latex_error(self, broken_latex: str, error_excerpt: str) -> str:
        """Reparo cirúrgico de LaTeX auditando sintaxe, caracteres de escape, ambientes e layout."""
        preamble, body, _ = LaTeXPreambleSplitPlugin.split_template(broken_latex)
        target = body if preamble else broken_latex
        messages = [
            {
                "role": "system",
                "content": (
                    "MODE:CAVEMAN_LATEX_REPAIR. Zero prose, zero fences. "
                    "Role: Senior LaTeX Debugger and Code Architect. "
                    "Analyze pdflatex compiler errors and fix broken LaTeX code. "
                    "1. SYNTAX AUDIT: Fix unclosed braces {}, unclosed environments (itemize, tabular, minipage), and broken macros. "
                    "2. ESCAPING AUDIT: Ensure %, &, $, #, _ in regular text are escaped (e.g. C\\#, R\\&D, 100\\%, PL/SQL). "
                    "3. ENTRY ISOLATION: Ensure every entry (education, experience, project) is cleanly isolated with \\par\\vspace{3pt} or blank lines so items never collide on the same line. "
                    "Output ONLY valid compilable LaTeX code."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"COMPILER_ERROR:\n{error_excerpt[:600]}\n\n"
                    f"BROKEN_LATEX:\n{target}\n\n"
                    "Fix all syntax, escaping, and formatting errors. Return valid compilable LaTeX code."
                ),
            },
        ]
        fixed, _, _, _ = self._call_llm_chat(messages=messages, max_tokens=4096)
        cleaned = sanitize_latex_layout(CavemanPromptPlugin.strip_code_fences(fixed))
        if not cleaned or len(cleaned.strip()) < 30 or r"\end{document}" not in cleaned:
            return broken_latex
        reassembled = LaTeXPreambleSplitPlugin.reassemble(preamble, cleaned) if preamble else cleaned
        if r"\end{document}" not in reassembled:
            reassembled = reassembled.rstrip() + "\n\\end{document}\n"
        return sanitize_latex_layout(reassembled)

    def review_and_enhance_latex(
        self,
        base_latex: str,
        resume_type: str = "profissional",
        instructions: str = "",
        lang: str = "pt-br",
    ) -> Tuple[str, TokenMetrics]:
        """Revisa e aprimora cirurgicamente o código LaTeX existente sem reconstruir do zero.

        Realiza revisão dupla: auditoria completa do código LaTeX (sintaxe, escape, espaçamento)
        e aprimoramento textual (verbos de ação, impacto, síntese de resumo).
        Economiza até ~75% dos tokens comparado com síntese direta a partir de páginas web brutas.
        Envia apenas o corpo do documento (\\begin{document} .. \\end{document}) com split de preâmbulo.
        """
        p = self.use_token_plugins
        metrics = TokenMetrics(
            active_plugins=[
                plugin for plugin, enabled in [
                    ("LaTeXReviewEngine", True),
                    (CavemanPromptPlugin.name, p.get("caveman", True)),
                    (ThinkingSuppressionPlugin.name, p.get("thinking", True)),
                    (LaTeXPreambleSplitPlugin.name, p.get("preamble", True)),
                ] if enabled
            ]
        )
        preamble, body, _ = LaTeXPreambleSplitPlugin.split_template(base_latex) if p.get("preamble", True) else ("", base_latex, [])
        target = body if preamble else base_latex
        preamble_tokens_saved = estimate_tokens(preamble) * 2 if preamble else 0

        instruction_line = f"CUSTOM INSTRUCTION: {instructions.strip()}\n" if instructions.strip() else ""

        if p.get("caveman", True):
            sys_prompt = (
                f"MODE:CAVEMAN_LATEX_CODE_AND_CONTENT_REVIEW. LANG:{lang.upper()}.\n"
                "Role: Senior LaTeX Architect & Executive Technical Resume Editor.\n"
                "Task: Perform a comprehensive dual review of the provided LaTeX resume body (LaTeX code audit + text content optimization).\n\n"
                "PART 1: LATEX CODE & TYPESETTING AUDIT\n"
                "1. SYNTAX & ENVIRONMENTS: Check and ensure all braces {} are balanced. Ensure all environments (\\begin{itemize} ... \\end{itemize}, paracol, minipage, tabular) are properly opened and closed.\n"
                r"2. SPECIAL CHARACTER ESCAPING: Audit all user text, company names, skills, URLs, and descriptions for unescaped reserved LaTeX characters. Ensure '%', '&', '$', '#', and '_' are properly escaped (e.g. C\#, C\texttt{++}, R\&D, PL/SQL, 100\%, \$1M, tech\_stack) while preserving LaTeX commands and math symbols (\cdot, \textbf, \hfill)." "\n"
                "3. ENTRY ISOLATION (ZERO COLLISION): Each education degree, job experience, or project entry MUST be an isolated paragraph block. Conclude each entry with \\par\\vspace{3pt} or a clean blank line. NEVER allow an institution, location, or details line to merge onto the same line as the next entry title or \\hfill.\n"
                "4. LINE BREAK & SPACING DISCIPLINE: Avoid awkward line breaks, overlapping text, or overfull boxes. Ensure clean vertical rhythm and correct use of \\par and \\vspace.\n"
                "5. MACRO PRESERVATION: Preserve existing template structure, commands, and styling macros (e.g. \\switchcolumn, \\cventry, \\cvsection, \\cvskill, \\textbf, \\textit, \\href, \\color). In two-column layouts using paracol (tech_sidebar, nico_krieger), NEVER remove \\switchcolumn or move sidebar sections (Contact, Education, Skills, Languages, Awards) into the main column.\n"
                "6. HEADER CONTACT DISCIPLINE: In contact line / header, NEVER use prefixes 'Local:', 'Location:', 'Portfólio:', or 'Portfolio:'. Location MUST be the last item in the contact list.\n\n"
                "PART 2: TEXT & CONTENT ENHANCEMENT\n"
                "1. NOUN-FIRST EXPERIENCE DESCRIPTIONS (ACTION VERBS & METRICS): Avoid starting experience descriptions with past-tense verbs (participou, orientou, acompanhou, desenvolveu, ensinou, realizou...). Prefer professional nouns (participação, orientação, acompanhamento, desenvolvimento, ensino, realização, liderança, coordenação, implementação...). In English, prefer noun-oriented achievements (Leadership in, Development of, Instruction in, Coordination of, Participation in).\n"
                "2. NOUN-FIRST PROJECT DESCRIPTIONS: Project descriptions MUST start with a descriptive NOUN (e.g., 'Gerador...', 'Aplicação...', 'Página...', 'Implementação...', 'Portfólio...', 'Utilitário...', 'Jogo...', 'Plataforma...', 'Ferramenta...') or in English ('Automated generator...', 'Web application...', 'Personal portfolio...', 'Manual implementations...', 'Utility...', 'Exploration game...'). NEVER begin project descriptions with past-tense action verbs (e.g. NEVER use 'Desenvolveu', 'Criou', 'Implementou', 'Reuniu', 'Construiu', or in English 'Developed', 'Created', 'Implemented', 'Built').\n"
                "3. EXECUTIVE SUMMARY: If the summary/resumo section is sparse, missing, or contains generic website metadata (e.g. starting with 'Portfólio profissional de...'), synthesize a concise 2-3 sentence executive technical overview highlighting candidate's core expertise, academic background, and technical focus based strictly on their actual data.\n"
            "4. STRICT TRUTHFULNESS & ZERO INVENTIONS: Keep all institutions, degrees, dates, metrics, and names 100% truthful to source facts. NEVER invent or hallucinate new projects, external URLs, project links, publications, DOI links, experiences, awards, or credentials not already present in the provided LaTeX code. Only enhance existing entries.\n"
            "5. PUBLICATIONS & AWARDS LISTING: Preserve and list ALL publications and awards individually. NEVER collapse them into a single line or summary. Each publication must include title, authors, venue, year, and DOI link. CRITICAL FOR PUBLICATIONS: All publications must be contained within a SINGLE \\begin{enumerate}[...] ... \\end{enumerate} environment. Each publication MUST be exactly ONE \\item containing authors, title, venue, year, and DOI. NEVER wrap each publication in its own \\begin{enumerate} and NEVER split a publication across multiple \\item elements (e.g. NEVER make venue/year a second item). Sequential numbering (1., 2., 3., ...) across all publications is strictly mandatory. Each award must be an individual item. ACADEMIC GRANTS & EXTENSION FELLOWSHIPS (e.g. Bolsa / Grant in extension or research projects) already present under work experience must NEVER be duplicated or included in awards/premiações.\n"
            "6. EXACT PERIODS: Never change explicit academic or work periods into 'Período não especificado', 'Em andamento', or 'Concluído'. Keep exact years and periods (e.g. 2026 - Atual, 2019 - 2025, 2023 - 2024).\n"
            "7. COMPLETE LANGUAGE STANDARDIZATION: The entire document MUST be 100% in the target language (LANG). If LANG is EN-US (English), ALL summary text, bullet points, titles, descriptions, skills, and awards MUST be translated to English. NEVER leave Portuguese sentences, Portuguese bullets, or Portuguese summaries in an English resume. Conversely, if LANG is PT-BR, ensure Portuguese consistency throughout.\n"
            "8. ZERO DUPLICATE ENTRIES: Eliminate any cross-lingual duplicate entries under Education, Experience, Publications, or Awards. If an entry appears in both languages or multiple times with slight variations (e.g. M.Sc. vs Mestrado, TA vs Monitor, UFV vs FUNARBEN), preserve ONLY ONE single authoritative entry in the target language.\n\n"
            "PART 3: OUTPUT FORMAT\n"
            "Return ONLY the audited, polished LaTeX body from \\begin{document} to \\end{document}. "
            "Zero prose commentary, zero markdown code fences."
        )

        user_prompt = (
            f"{instruction_line}"
            "DUAL REVIEW MANDATE: Review both the LaTeX code (syntax, balanced braces, special character escaping %, &, $, #, _, entry isolation) "
            "and the text content. IMPORTANT: Start experience and project descriptions with NOUNS (Participação, Orientação, Desenvolvimento, Ensino, Gerador, Aplicação, Utilitário...), NEVER action verbs (Participou, Orientou, Desenvolveu, Implementou, Criou).\n"
            "Ensure every education, experience, and project entry is isolated with \\par\\vspace{3pt} or blank lines. Ensure all publications are strictly in a single \\begin{enumerate} with one \\item per publication for continuous sequential numbering (1, 2, 3...).\n\n"
            f"LATEX_BODY_TO_REVIEW:\n{target}\n\n"
            "Return the audited and improved LaTeX body from \\begin{document} to \\end{document}."
        )

        try:
            fixed, usage, used_model, is_cached = self._call_llm_chat(
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4096,
            )
            cleaned = sanitize_latex_layout(CavemanPromptPlugin.strip_code_fences(fixed))
            target_secs = [m.strip() for m in re.findall(r"\\(?:cvsection|section\*?)\{([^}]+)\}", target)]
            cleaned_secs = [m.strip() for m in re.findall(r"\\(?:cvsection|section\*?)\{([^}]+)\}", cleaned)]
            missing_major_secs = [s for s in target_secs if not any(s.lower() in cs.lower() or cs.lower() in s.lower() for cs in cleaned_secs)]
            is_severely_truncated = (
                (len(target) > 600 and len(cleaned.strip()) < int(len(target) * 0.70))
                or (len(target_secs) >= 3 and len(missing_major_secs) > 0)
            )
            has_end_doc = r"\end{document}" in cleaned
            if not cleaned or len(cleaned.strip()) < 30 or is_severely_truncated or not has_end_doc:
                final_latex = base_latex
            else:
                final_latex = sanitize_latex_layout(LaTeXPreambleSplitPlugin.reassemble(preamble, cleaned) if preamble else cleaned)
                if r"\end{document}" not in final_latex:
                    final_latex = final_latex.rstrip() + "\n\\end{document}\n"

            self._populate_metrics(
                metrics,
                usage,
                used_model,
                is_cached,
                extra_saved=preamble_tokens_saved + 1500,
            )
            return final_latex, metrics
        except Exception as exc:
            reason_code, reason_detail = diagnose_fallback_reason(exc)
            metrics.model_used = f"direct_fallback ({reason_code})"
            metrics.fallback_reason = reason_code
            metrics.fallback_detail = reason_detail
            logger.warning(
                "Falha na chamada LLM para review (%s): %s. Usando fallback direto.",
                reason_code,
                reason_detail,
            )
            # Em caso de indisponibilidade de API ou falha, preserva o LaTeX determinístico com segurança
            return base_latex, metrics

    @staticmethod
    def _populate_metrics(
        metrics: TokenMetrics,
        usage: Dict[str, Any],
        used_model: str,
        is_cached: bool,
        extra_saved: int,
    ) -> None:
        metrics.model_used = used_model
        metrics.cache_hit = is_cached
        metrics.prompt_tokens_actual = int(usage.get("prompt_tokens") or 0)
        metrics.completion_tokens_actual = int(usage.get("completion_tokens") or 0)
        details = usage.get("completion_tokens_details") or {}
        metrics.reasoning_tokens_actual = int(details.get("reasoning_tokens") or 0)
        metrics.total_tokens_actual = int(usage.get("total_tokens") or 0)
        metrics.estimated_tokens_saved = extra_saved + (900 if is_cached else 0)

    @staticmethod
    def _parse_json_safely(
        raw_content: str,
        raw_profile_data: Dict[str, Any],
        resume_type: str,
    ) -> Dict[str, Any]:
        cleaned = CavemanPromptPlugin.strip_code_fences(raw_content)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = cleaned[start : end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
                try:
                    return json.loads(fixed)
                except Exception:
                    pass
        return {}

    @staticmethod
    def _apply_fallbacks(
        cv: Dict[str, Any],
        raw_profile_data: Dict[str, Any],
        resume_type: str,
        lang: str = "pt-br",
    ) -> None:
        """Garante que nenhum dado essencial extraído das APIs fique ausente caso o JSON venha parcial."""
        is_en = str(lang).lower().startswith("en")
        meta = raw_profile_data.get("user_meta") or {}
        gh = raw_profile_data.get("github") or {}
        orcid = raw_profile_data.get("orcid") or {}
        lattes = raw_profile_data.get("lattes") or {}

        if not cv.get("name"):
            cv["name"] = (
                meta.get("name")
                or lattes.get("name")
                or orcid.get("name")
                or gh.get("name")
                or gh.get("username")
                or ("Candidate Name" if is_en else "Nome do Candidato")
            )
        if not cv.get("email"):
            cv["email"] = meta.get("email") or gh.get("email") or ""
        if not cv.get("phone"):
            cv["phone"] = meta.get("phone") or ""
        if not cv.get("location"):
            cv["location"] = meta.get("location") or gh.get("location") or ""
        if not cv.get("title"):
            if is_en:
                default_role = "Academic Researcher & Scientist" if resume_type == "academico" else "Technology & Software Specialist"
            else:
                default_role = "Pesquisador Acadêmico & Cientista" if resume_type == "academico" else "Especialista em Tecnologia & Desenvolvimento"
            cv["title"] = meta.get("role") or default_role
        if not cv.get("summary"):
            cv["summary"] = (
                lattes.get("summary")
                or orcid.get("bio")
                or gh.get("bio")
                or (
                    "Professional with a strong technical and analytical background."
                    if is_en
                    else "Profissional com sólida trajetória técnica e analítica."
                )
            )
        # Remove entradas vazias retornadas pelo modelo antes da renderização LaTeX
        cv["education"] = [
            e for e in (cv.get("education") or [])
            if (e.get("degree") or "").strip() or (e.get("institution") or "").strip()
        ]
        cv["experience"] = [
            x for x in (cv.get("experience") or [])
            if (x.get("role") or "").strip() or (x.get("organization") or "").strip()
        ]
        cv["projects"] = [
            p for p in (cv.get("projects") or [])
            if (p.get("name") or "").strip() or (p.get("description") or "").strip()
        ]
        for p in cv["projects"]:
            if "description" in p:
                p["description"] = sanitize_project_description(p["description"], lang)
        cv["publications"] = [
            pb for pb in (cv.get("publications") or [])
            if (pb.get("title") or "").strip()
        ]
        cv["skills"] = [
            s for s in (cv.get("skills") or [])
            if isinstance(s.get("items"), list) and s.get("items") or str(s.get("items") or "").strip()
        ]
        for s in cv["skills"]:
            if isinstance(s.get("items"), list):
                s["items"] = ", ".join(str(i) for i in s["items"] if str(i).strip())
        cv["languages"] = [str(l).strip() for l in (cv.get("languages") or []) if str(l).strip()]
        if not cv["languages"]:
            raw_langs = (
                lattes.get("languages")
                or (raw_profile_data.get("linkedin") or {}).get("languages")
                or raw_profile_data.get("languages")
                or meta.get("languages")
                or []
            )
            cv["languages"] = [str(l).strip() for l in raw_langs if str(l).strip()][:5]
        cv["awards"] = sanitize_awards(cv.get("awards") or [])
        if not cv["awards"] and lattes.get("awards"):
            cv["awards"] = sanitize_awards(lattes["awards"][:5])

        if not cv.get("education"):
            real_edus = (
                lattes.get("educations")
                or (raw_profile_data.get("orcid") or {}).get("educations")
                or (raw_profile_data.get("portfolio") or {}).get("educations")
                or []
            )
            cv["education"] = [
                {
                    "degree": (e.get("degree") or f"{e.get('level', '')} - {e.get('course', '')}".strip(" -") or e.get("course") or "").strip(),
                    "institution": (e.get("institution") or e.get("organization") or e.get("org") or "").strip(),
                    "period": (e.get("period") or f"{e.get('start', '')}-{e.get('end', '')}".strip("-")).strip(),
                    "details": (e.get("details") or e.get("thesis_title") or "").strip(),
                }
                for e in real_edus[:6]
                if (e.get("degree") or e.get("institution") or e.get("level") or e.get("course"))
            ]

        if not cv.get("experience"):
            real_emps = (
                (raw_profile_data.get("portfolio") or {}).get("employments")
                or lattes.get("employments")
                or (raw_profile_data.get("orcid") or {}).get("employments")
                or (raw_profile_data.get("linkedin") or {}).get("experiences")
                or []
            )
            cv["experience"] = [
                {
                    "role": (e.get("role") or e.get("title") or ("Pesquisador / Colaborador" if not is_en else "Researcher / Staff")).strip(),
                    "organization": (e.get("organization") or e.get("company") or e.get("institution") or "").strip(),
                    "period": (e.get("period") or f"{e.get('start', '')}-{e.get('end', '')}".strip("-")).strip(),
                    "bullets": [e.get("description")] if e.get("description") else (e.get("bullets") or []),
                }
                for e in real_emps
                if (e.get("role") or e.get("organization") or e.get("company") or e.get("institution"))
            ]

        if not cv.get("projects") and gh.get("repos"):
            cv["projects"] = [
                {
                    "name": r.get("name", ""),
                    "tech": r.get("tech") or r.get("language", ""),
                    "url": r.get("url", ""),
                    "description": r.get("description", ""),
                }
                for r in gh["repos"]
            ]
        elif not cv.get("projects") and (raw_profile_data.get("portfolio") or {}).get("projects"):
            cv["projects"] = [
                {
                    "name": p.get("name", ""),
                    "tech": p.get("tech", ""),
                    "url": p.get("url", ""),
                    "description": p.get("description", ""),
                }
                for p in (raw_profile_data.get("portfolio") or {})["projects"]
            ]
        elif not cv.get("projects") and lattes.get("projects"):
            cv["projects"] = [
                {
                    "name": p.get("title", ""),
                    "tech": "",
                    "url": str(p.get("year") or ""),
                    "description": p.get("description", ""),
                }
                for p in lattes["projects"]
            ]

        # Enriquecimento de descrições e tecnologias de repositórios caso tenham vindo vazias
        real_repos = {r.get("name", "").lower(): r for r in (gh.get("repos") or []) if r.get("name")}
        for p in cv.get("projects") or []:
            p_name = (p.get("name") or "").lower()
            if p_name in real_repos:
                repo = real_repos[p_name]
                if not (p.get("description") or "").strip() and repo.get("description"):
                    p["description"] = repo["description"]
                if not (p.get("tech") or "").strip() and (repo.get("tech") or repo.get("language")):
                    p["tech"] = repo.get("tech") or repo.get("language")
                if not (p.get("url") or "").strip() and repo.get("url"):
                    p["url"] = repo["url"]
        # Coleta e consolidação de publicações reais das fontes
        all_real_pubs = []
        seen_pub_titles = set()
        for p_src in [
            (raw_profile_data.get("scholar") or {}).get("publications"),
            (raw_profile_data.get("portfolio") or {}).get("publications"),
            lattes.get("publications"),
            orcid.get("works"),
            (raw_profile_data.get("manual_data") or {}).get("publications") if isinstance((raw_profile_data.get("manual_data") or {}).get("publications"), list) else None,
        ]:
            if not p_src:
                continue
            for pb in p_src:
                t = str(pb.get("title") or "").strip()
                t_k = re.sub(r"\W+", "", t.lower())[:35]
                if t and t_k not in seen_pub_titles:
                    seen_pub_titles.add(t_k)
                    all_real_pubs.append({
                        "title": t,
                        "venue": str(pb.get("venue") or pb.get("journal") or "").strip(),
                        "year": str(pb.get("year") or "").strip(),
                        "authors": str(pb.get("authors") or "").strip(),
                        "doi": str(pb.get("doi") or "").strip(),
                    })

        curr_pubs = cv.get("publications") or []
        has_generic_pub = any("trabalhos de pesquisa em computa" in (p.get("title") or "").lower() for p in curr_pubs)
        if not curr_pubs or has_generic_pub or (all_real_pubs and len(curr_pubs) < len(all_real_pubs)):
            for rp in all_real_pubs:
                rp_k = re.sub(r"\W+", "", rp["title"].lower())[:35]
                if not any(re.sub(r"\W+", "", (cp.get("title") or "").lower())[:35] == rp_k for cp in curr_pubs):
                    curr_pubs.append(rp)
            curr_pubs = [p for p in curr_pubs if "trabalhos de pesquisa em computa" not in (p.get("title") or "").lower()]
            cv["publications"] = curr_pubs

        # Consolidação de premiações individuais
        all_real_awards = []
        for aw_src in [
            (raw_profile_data.get("portfolio") or {}).get("awards"),
            lattes.get("awards"),
            (raw_profile_data.get("manual_data") or {}).get("awards"),
        ]:
            if not aw_src:
                continue
            aw_list = aw_src if isinstance(aw_src, list) else [aw_src]
            for a in aw_list:
                sa = str(a).strip()
                if sa and not any(sa.lower() in x.lower() or x.lower() in sa.lower() for x in all_real_awards):
                    all_real_awards.append(sa)

        curr_aw = cv.get("awards") or []
        is_collapsed_aw = any(re.search(r"\b\d+\s+premia[çc][õo]es", str(a), re.I) for a in curr_aw)
        if not curr_aw or is_collapsed_aw or (all_real_awards and len(curr_aw) < len(all_real_awards)):
            curr_aw = [a for a in curr_aw if not re.search(r"\b\d+\s+premia[çc][õo]es", str(a), re.I)]
            for ra in all_real_awards:
                if not any(ra.lower() in str(ca).lower() for ca in curr_aw):
                    curr_aw.append(ra)
            cv["awards"] = sanitize_awards(curr_aw, experiences=cv.get("experience") or [])

        # Atualização e preservação de períodos em formação
        real_edus = (raw_profile_data.get("portfolio") or {}).get("educations") or lattes.get("educations") or orcid.get("educations") or []
        for ed in cv.get("education") or []:
            cur_p = (ed.get("period") or "").strip()
            if cur_p in ("", "Em andamento", "Concluído", "Período não especificado", "Present", "Atual"):
                for red in real_edus:
                    r_deg = red.get("degree") or red.get("course") or ""
                    if r_deg and (r_deg.lower() in ed.get("degree", "").lower() or ed.get("degree", "").lower() in r_deg.lower()):
                        real_p = red.get("period") or f"{red.get('start', '')}-{red.get('end', '')}".strip("-")
                        if real_p:
                            ed["period"] = real_p
                            break

        # Atualização e preservação de períodos em experiência
        real_emps = (raw_profile_data.get("portfolio") or {}).get("employments") or lattes.get("employments") or orcid.get("employments") or []
        for ex in cv.get("experience") or []:
            cur_p = (ex.get("period") or "").strip()
            if cur_p in ("", "Período não especificado"):
                for remp in real_emps:
                    r_role = remp.get("role") or ""
                    if r_role and (r_role.lower() in ex.get("role", "").lower() or ex.get("role", "").lower() in r_role.lower()):
                        real_p = remp.get("period") or f"{remp.get('start', '')}-{remp.get('end', '')}".strip("-")
                        if real_p:
                            ex["period"] = real_p
                            break

        cv["experience"] = deduplicate_and_sort_experiences(cv.get("experience") or [], lang=lang)
        for exp in cv.get("experience") or []:
            if exp.get("description"):
                exp["description"] = remove_terminal_abbreviation_ellipsis(
                    sanitize_experience_description(exp["description"], lang=lang)
                )
            if exp.get("bullets"):
                exp["bullets"] = [
                    remove_terminal_abbreviation_ellipsis(sanitize_experience_description(b, lang=lang))
                    for b in exp["bullets"]
                ]
        for project in cv.get("projects") or []:
            if project.get("description"):
                project["description"] = remove_terminal_abbreviation_ellipsis(
                    sanitize_project_description(project["description"], lang=lang)
                )
        cv["education"] = deduplicate_and_sort_educations(cv.get("education") or [], lang=lang)
        cv["publications"] = deduplicate_and_sort_publications(cv.get("publications") or [])
        for publication in cv.get("publications") or []:
            for field in ("title", "venue", "authors"):
                if publication.get(field):
                    publication[field] = remove_terminal_abbreviation_ellipsis(publication[field])
        cv["awards"] = deduplicate_and_sort_awards(cv.get("awards") or [], experiences=cv.get("experience") or [])

        portfolio = raw_profile_data.get("portfolio") or {}
        linkedin = raw_profile_data.get("linkedin") or {}
        manual = raw_profile_data.get("manual_data") or {}
        project_technologies = collect_project_technologies(
            gh.get("repos") or [],
            portfolio.get("projects") or [],
            lattes.get("projects") or [],
            manual.get("projects") or [],
        )
        cv["skills"] = merge_skill_groups(
            cv.get("skills"),
            {"items": gh.get("top_languages") or []},
            {"items": gh.get("languages") or []},
            {"items": portfolio.get("skills") or []},
            {"items": linkedin.get("skills") or []},
            {"items": lattes.get("areas") or []},
            {"items": orcid.get("keywords") or []},
            manual.get("skills"),
            extra_items=project_technologies,
            category="",
        )
