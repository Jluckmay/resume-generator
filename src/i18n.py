"""Internacionalização (i18n) bilíngue (pt-BR e en-US) para Interface Web, CLI e Templates LaTeX."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List

SUPPORTED_LANGS = ("pt-br", "en-us")


def normalize_lang(lang: str | None) -> str:
    if not lang:
        return "pt-br"
    cleaned = lang.strip().lower().replace("_", "-")
    if cleaned.startswith("en"):
        return "en-us"
    return "pt-br"


LATEX_I18N: Dict[str, Dict[str, str]] = {
    "pt-br": {
        "babel": "brazil",
        "present": "Atual",
        "default_candidate": "Candidato",
        "default_researcher": "Pesquisador Acadêmico",
        "default_professional": "Profissional",
        "default_acad_title": "Currículo Acadêmico & Científico",
        "default_tech_title": "Engenharia & Tecnologia",
        "default_cv_title": "Currículo",
        "sec_summary_acad": "Síntese Acadêmica e Linha de Pesquisa",
        "sec_summary_prof": "Resumo Profissional",
        "sec_profile": "Perfil",
        "sec_contact": r"Contato \& Perfis",
        "sec_education": "Formação Acadêmica",
        "sec_exp_acad": "Atuação Acadêmica e Profissional",
        "sec_exp_prof": "Experiência Profissional",
        "sec_proj_acad": "Projetos de Pesquisa e Desenvolvimento",
        "sec_proj_prof": "Projetos de Destaque e Open Source",
        "sec_publications": "Produção Científica e Publicações",
        "sec_skills": "Competências Técnicas e Metodológicas",
        "sec_languages": "Idiomas",
        "sec_awards": "Prêmios, Títulos e Certificações",
        "sec_competencies": "Competências Principais e Palavras-Chave",
        "sec_tech_stack": "Stack Tecnológica e Ferramentas",
        "lbl_tech_stack": r"Ferramentas \& Tecnologias",
        "default_skill_cat": "Habilidades",
        "link_label": "Link",
    },
    "en-us": {
        "babel": "english",
        "present": "Present",
        "default_candidate": "Candidate",
        "default_researcher": "Academic Researcher",
        "default_professional": "Professional",
        "default_acad_title": "Academic & Scientific Curriculum Vitae",
        "default_tech_title": "Engineering & Technology",
        "default_cv_title": "Curriculum Vitae",
        "sec_summary_acad": r"Academic Summary \& Research Focus",
        "sec_summary_prof": "Professional Summary",
        "sec_profile": "Profile",
        "sec_contact": r"Contact \& Profiles",
        "sec_education": "Education",
        "sec_exp_acad": r"Academic \& Professional Appointments",
        "sec_exp_prof": "Professional Experience",
        "sec_proj_acad": r"Research \& Development Projects",
        "sec_proj_prof": r"Featured \& Open Source Projects",
        "sec_publications": "Scientific Publications",
        "sec_skills": r"Technical \& Methodological Skills",
        "sec_languages": "Languages",
        "sec_awards": r"Awards, Honors \& Certifications",
        "sec_competencies": "Core Competencies & Keywords",
        "sec_tech_stack": "Technical Stack & Tools",
        "lbl_tech_stack": r"Technologies \& Tools",
        "default_skill_cat": "Skills",
        "link_label": "Link",
    },
}


TEMPLATES_I18N: Dict[str, Dict[str, Dict[str, str]]] = {
    "pt-br": {
        "modern_pro": {
            "name": "Moderno Executivo (Profissional & Tech)",
            "description": (
                "Layout executivo moderno em coluna única com destaques em azul-petróleo, "
                "cabeçalho com foto opcional e links clicáveis (LinkedIn, GitHub, ORCID, Lattes)."
            ),
        },
        "academic_classic": {
            "name": "Acadêmico Clássico (Pesquisador / CNPq / Pós-Graduação)",
            "description": (
                "Estrutura acadêmica formal com foco em Formação, Produção Bibliográfica (DOI), "
                "Projetos de Pesquisa, Docência, Prêmios, Lattes e ORCID."
            ),
        },
        "bubble": {
            "name": "Bubble CV",
            "description": (
                "Modelo Overleaf BubbleCV (https://www.overleaf.com/latex/templates/bubblecv/bcynnjktwqsx) com linha do tempo vertical contínua, "
                "bolhas TikZ para datas e cabeçalho, barras de progresso para competências/idiomas e design de alto impacto visual."
            ),
        },
        "tech_sidebar": {
            "name": "Tech & Engenharia Duas Colunas (Barra Lateral)",
            "description": (
                "Design assimétrico de duas colunas com foto, contatos, stack técnica e idiomas "
                "na coluna lateral e experiências/projetos na coluna principal."
            ),
        },
        "overleaf_russell_ti": {
            "name": "Russel CV",
            "description": (
                "Modelo Overleaf Russell CV (https://www.overleaf.com/read/rgfqqnnynrmv#d5b171) com foto lateral "
                "no cabeçalho, ícones FontAwesome 5, títulos com destaque nas 3 primeiras letras e níveis de idiomas em círculos."
            ),
        },
        "minimal_ats": {
            "name": "Minimalista ATS-Friendly (Alta Densidade)",
            "description": (
                "Tipografia clássica de alto contraste otimizada para sistemas corporativos ATS "
                "e leitura rápida por recrutadores."
            ),
        },
        "overleaf_awesome_cv": {
            "name": "Awesome CV",
            "description": (
                "Modelo Overleaf Jason Richards' Résumé (https://www.overleaf.com/articles/jason-richards-resume/chbxgnfyyvfc) "
                "baseado no clássico Awesome-CV com cabeçalho centralizado, destaque de 3 letras nas seções e rodapé executivo."
            ),
        },
        "overleaf_single_page_keywords": {
            "name": "Single Page + Keywords",
            "description": (
                "Modelo Overleaf de página única em duas colunas (https://www.overleaf.com/latex/templates/sample-single-page-resume-with-keywords/wmcxcgmtkxzk) "
                "com fonte Raleway, ícones circulares TikZ, Resumo e Keywords de stack por experiência."
            ),
        },
        "nico_krieger": {
            "name": "Krieger CV",
            "description": (
                "Modelo de página única com cabeçalho escuro de largura total, "
                "barra lateral destacada para contatos, habilidades avaliadas em 5 pontos e idiomas, e coluna principal clara."
            ),
        },
        "google_standard": {
            "name": "Padrão Google (Big Tech / Software Engineer)",
            "description": (
                "Modelo padrão de recrutamento Big Tech (Google SWE / Gayle Laakmann McDowell). "
                "Página única densa, margens de 0.5 polegadas, estrutura XYZ de realizações e formatação clean."
            ),
        },
        "ai_ats_max": {
            "name": "Otimizado para IA & ATS (Máxima Legibilidade)",
            "description": (
                "Desenvolvido especificamente para triagem automatizada por LLMs (Gemini, Claude, GPT) e sistemas ATS. "
                "Fluxo textual 100% linear, metadados semânticos, matriz de competências e compatibilidade Unicode nativa."
            ),
        },
    },
    "en-us": {
        "modern_pro": {
            "name": "Executive Modern (Professional & Tech)",
            "description": (
                "Single-column modern executive layout with teal-blue accents, "
                "optional header photo, and clickable links (LinkedIn, GitHub, ORCID, Lattes)."
            ),
        },
        "academic_classic": {
            "name": "Academic Classic (Researcher / Post-Grad / Faculty)",
            "description": (
                "Formal academic CV structure highlighting Education, Peer-Reviewed Publications (DOI), "
                "Research Projects, Teaching, Awards, Lattes, and ORCID."
            ),
        },
        "bubble": {
            "name": "Bubble CV",
            "description": (
                "Overleaf BubbleCV template (https://www.overleaf.com/latex/templates/bubblecv/bcynnjktwqsx) featuring continuous vertical timeline, "
                "TikZ circular nodes for dates and sections, progress bars for skills/languages, and striking high-density single-page layout."
            ),
        },
        "tech_sidebar": {
            "name": "Tech & Engineering Two-Column (Sidebar)",
            "description": (
                "Asymmetric two-column layout with photo, contacts, tech stack, and languages "
                "in the sidebar and experience/projects in the main column."
            ),
        },
        "overleaf_russell_ti": {
            "name": "Russel CV",
            "description": (
                "Overleaf Russell CV template (https://www.overleaf.com/read/rgfqqnnynrmv#d5b171) featuring left header photo, "
                "FontAwesome 5 icons, 3-letter colored section titles, skill tables, and 6-dot language proficiency bars."
            ),
        },
        "minimal_ats": {
            "name": "Minimalist ATS-Friendly (High Density)",
            "description": (
                "High-contrast classic typography optimized for corporate ATS parsers "
                "and rapid recruiter scanning."
            ),
        },
        "overleaf_awesome_cv": {
            "name": "Awesome CV",
            "description": (
                "Overleaf Jason Richards' Résumé template (https://www.overleaf.com/articles/jason-richards-resume/chbxgnfyyvfc) "
                "built on Awesome-CV with centered header, Roboto + Source Sans Pro typography, and 3-column executive footer."
            ),
        },
        "overleaf_single_page_keywords": {
            "name": "Single Page + Keywords",
            "description": (
                "Overleaf two-column single-page template (https://www.overleaf.com/latex/templates/sample-single-page-resume-with-keywords/wmcxcgmtkxzk) "
                "by Primož Godec & Salman Maqbool with Raleway font, TikZ circled icons, Summary, and per-job stack Keywords."
            ),
        },
        "nico_krieger": {
            "name": "Krieger CV",
            "description": (
                "Nico Krieger resume template featuring a full-width dark top header, "
                "highlight sidebar with 5-dot skill ratings and 6-dot languages, and clean main column."
            ),
        },
        "google_standard": {
            "name": "Google Standard (Big Tech / Software Engineer)",
            "description": (
                "Big Tech standard recruitment layout (Google SWE / Gayle Laakmann McDowell). "
                "Dense single-page design, 0.5-inch margins, XYZ accomplishment bullets, and clean horizontal lines."
            ),
        },
        "ai_ats_max": {
            "name": "AI & ATS Max-Readability (LLM Evaluators)",
            "description": (
                "Engineered specifically for automated screening by LLMs (Gemini, Claude, GPT) and neural ATS parsers. "
                "Strict single-column text stream, semantic metadata tags, core competencies matrix, and native Unicode mapping."
            ),
        },
    },
}


MODELS_I18N: Dict[str, Dict[str, Dict[str, str]]] = {
    "pt-br": {
        "nvidia/nemotron-3.5-super-vl-120b-a12b": {
            "name": "NVIDIA Nemotron 3.5 Super VL 120B (A12B MoE) — Recomendado",
            "description": "Melhor equilíbrio entre inteligência (120B), velocidade (<1s) e economia (0 reasoning tokens).",
        },
        "stepfun-ai/step-5-preview": {
            "name": "StepFun Step-5 Preview — Alta Velocidade",
            "description": "Baixa latência (~1s) e excelente formatação LaTeX/JSON sem desperdício de tokens.",
        },
        "google/gemma-4-31b-it": {
            "name": "Google Gemma 4 31B Instruct — Econômico",
            "description": "Modelo 31B direto sem tokens de raciocínio ocultos.",
        },
        "z-ai/glm-5.3": {
            "name": "Z-AI GLM 5.3 — Raciocínio Avançado",
            "description": "Alta capacidade analítica para templates LaTeX customizados complexos.",
        },
    },
    "en-us": {
        "nvidia/nemotron-3.5-super-vl-120b-a12b": {
            "name": "NVIDIA Nemotron 3.5 Super VL 120B (A12B MoE) — Recommended",
            "description": "Best balance of intelligence (120B), speed (<1s), and token economy (0 reasoning tokens).",
        },
        "stepfun-ai/step-5-preview": {
            "name": "StepFun Step-5 Preview — High Speed",
            "description": "Low latency (~1s) and accurate LaTeX/JSON formatting without token waste.",
        },
        "google/gemma-4-31b-it": {
            "name": "Google Gemma 4 31B Instruct — Economical",
            "description": "Direct 31B model with zero hidden reasoning token overhead.",
        },
        "z-ai/glm-5.3": {
            "name": "Z-AI GLM 5.3 — Advanced Reasoning",
            "description": "High analytical capacity for complex custom LaTeX templates.",
        },
    },
}


UI_TEXT: Dict[str, Dict[str, Any]] = {
    "pt-br": {
        "page_title": "Gerador de Currículos LaTeX — NVIDIA AI",
        "app_title": "Gerador de Currículo",
        "app_caption": (
            "Extração automática de GitHub, ORCID, Lattes e LinkedIn • Compilação PDF via LaTeX • "
            "Otimizado com Plugins de Economia de Tokens (Caveman + TOON + 0-Reasoning)"
        ),
        "lang_selector_label": "🌐 Idioma da Interface e do Currículo",
        "resume_lang_label": "📝 Idioma do Currículo PDF",
        "sidebar_header": "⚙️ Motor de IA & Economia de Tokens",
        "model_select_label": "Modelo de IA",
        "model_select_help": (
            "Selecione o modelo do provedor escolhido. Modelos recomendados foram validados para alta precisão sintática "
            "e economia de tokens."
        ),
        "custom_key_label": "Chave de API do Provedor (Opcional)",
        "custom_key_placeholder": "Chave padrão do servidor ativa",
        "cache_checkbox": "Ativar Cache Local SHA-256 (0 tokens em reuso)",
        "plugins_header": "🔌 Plugins de Economia Ativos",
        "plugins_md": (
            "- **CavemanPromptPlugin**: diretivas ultra-concisas sem preâmbulo (~65% menos tokens)\n"
            "- **ThinkingSuppressionPlugin**: `enable_thinking=False` (0 tokens gastos em CoT oculto)\n"
            "- **TOONContextPrunerPlugin**: minificação tabular e deduplicação local ORCID/Lattes\n"
            "- **ShortKeySchemaPlugin**: chaves JSON de 1–2 letras na geração\n"
            "- **LaTeXPreambleSplitPlugin**: separa preâmbulo fixo de templates `.tex`"
        ),
        "plugins_toggle_label": "🔌 Habilitar plugins de economia de token",
        "plugins_toggle_help": (
            "Desativar para gerar o currículo sem compressão de prompts, chaves JSON curtas ou supressão de raciocínio oculto."
        ),
        "plugin_caveman": "CavemanPrompt (diretivas ultra-concisas)",
        "plugin_thinking": "ThinkingSuppression (0 tokens de raciocínio oculto)",
        "plugin_toon": "TOONContextPruner (minificação de perfis)",
        "plugin_shortkey": "ShortKeySchema (chaves JSON curtas)",
        "plugin_preamble": "LaTeXPreambleSplit (separar preâmbulo)",
        "plugin_cache": "SHA256Cache (cache local de tokens)",
        "sec1_title": "1. Perfil, Modalidade e Modelo LaTeX",
        "resume_type_label": "Finalidade do Currículo",
        "resume_type_prof": "Profissional (Mercado / Indústria / Tech)",
        "resume_type_acad": "Acadêmico (Pesquisa / Pós-Graduação / Docência)",
        "tpl_mode_label": "Origem do Modelo LaTeX",
        "tpl_mode_builtin": "Escolher modelo integrado",
        "tpl_mode_custom": "Fornecer meu próprio modelo LaTeX (.tex)",
        "tpl_select_label": "Selecione o Modelo de Currículo",
        "upload_tex_label": "Envie seu arquivo de template `.tex`",
        "paste_tex_label": "Ou cole o código LaTeX do seu modelo abaixo",
        "sec2_title": "2. Informações do Currículo",
        "header_personal_caption": "Dados Pessoais do Cabeçalho (opcional — sobrescreve extração automática)",
        "data_mode_label": "Método de Entrada das Informações",
        "mode_import_label": "📥 Importar Dados",
        "mode_manual_label": "✍️ Inserir Manualmente",
        "manual_sec_title": "2. Preenchimento Manual do Currículo",
        "manual_summary_label": "Resumo Profissional / Perfil",
        "manual_summary_ph": "Ex: Especialista em desenvolvimento de software com mais de 5 anos de atuação...",
        "manual_edu_label": "Formação Acadêmica (Grau/Curso | Instituição | Período | Detalhes)",
        "manual_edu_ph": "Bacharelado em Ciência da Computação | USP | 2018 - 2022 | Ênfase em IA\nMestrado em Engenharia | UNICAMP | 2022 - 2024",
        "manual_exp_label": "Experiência Profissional (Cargo | Empresa | Período | Localização | Descrição)",
        "manual_exp_ph": "Engenheiro de Software Sênior | Tech Corp | 2022 - Atual | São Paulo | Arquitetura de microsserviços e redução de latência em 40%.",
        "manual_skills_label": "Habilidades & Competências (Categoria: Tecnologias / Itens)",
        "manual_skills_ph": "Linguagens: Python, Go, TypeScript\nCloud & DevOps: Docker, Kubernetes, AWS\nBancos de Dados: PostgreSQL, Redis",
        "manual_projects_label": "Projetos Relevantes (Nome | Tecnologias | Link | Descrição)",
        "manual_projects_ph": "LaTeX Resume Enclave | Python, Flask, LaTeX | https://github.com/usuario/latex-resume | Plataforma zero-storage com criptografia.",
        "manual_languages_label": "Idiomas (Idioma e Nível, separados por vírgula ou linha)",
        "manual_languages_ph": "Português (Nativo), Inglês (Fluente), Espanhol (Intermediário)",
        "manual_awards_label": "Prêmios & Certificações (Título | Ano | Detalhes)",
        "manual_awards_ph": "AWS Certified Solutions Architect | 2023 | Amazon Web Services\n1º Lugar no Hackathon Nacional | 2022 | Desafio Tech",
        "manual_pubs_label": "Publicações & Artigos (Título | Periódico/Conferência | Ano | Autores | DOI)",
                "manual_pubs_ph": "Neural Parsing of Technical Resumes | IEEE Conference | 2023 | Silva, L.; Santos, A. | 10.1109/CVPR.2023.1001",
        "struct_edu_title": "🎓 Formação Acadêmica",
        "struct_exp_title": "💼 Experiência Profissional",
        "struct_proj_title": "🚀 Projetos Relevantes",
        "struct_pubs_title": "📄 Publicações & Artigos",
        "struct_awards_title": "🏆 Prêmios & Certificações",
        "btn_add_edu": "Adicionar Formação",
        "btn_add_exp": "Adicionar Experiência",
        "btn_add_proj": "Adicionar Projeto",
        "btn_add_pub": "Adicionar Publicação",
        "btn_add_award": "Adicionar Prêmio / Certificação",
        "btn_rem_item": "Remover",
        "struct_degree_lbl": "Grau / Curso",
        "struct_degree_ph": "Bacharelado em Ciência da Computação",
        "struct_inst_lbl": "Instituição de Ensino",
        "struct_inst_ph": "Universidade de São Paulo (USP)",
        "struct_period_lbl": "Período",
        "struct_period_ph": "2018 - 2022",
        "struct_details_lbl": "Detalhes / Ênfase / Tese",
        "struct_details_ph": "Foco em Inteligência Artificial e Compiladores",
        "struct_role_lbl": "Cargo / Título Profissional",
        "struct_role_ph": "Engenheiro de Software Sênior",
        "struct_org_lbl": "Empresa / Organização",
        "struct_org_ph": "Tech Solutions Corp",
        "struct_loc_lbl": "Localização",
        "struct_loc_ph": "São Paulo, SP (ou Remoto)",
        "struct_desc_lbl": "Descrição / Realizações",
        "struct_desc_ph": "Liderança técnica de microsserviços e redução de latência em 40%.",
        "struct_proj_name_lbl": "Nome do Projeto",
        "struct_proj_name_ph": "LaTeX Resume Enclave",
        "struct_proj_tech_lbl": "Tecnologias Utilizadas",
        "struct_proj_tech_ph": "Python, Flask, Docker, LaTeX",
        "struct_proj_url_lbl": "Link / Repositório (URL)",
        "struct_proj_url_ph": "https://github.com/usuario/projeto",
        "struct_proj_desc_lbl": "Descrição do Projeto",
        "struct_proj_desc_ph": "Plataforma de alta precisão com compilação determinística.",
        "struct_pub_title_lbl": "Título da Publicação",
        "struct_pub_title_ph": "Neural Parsing of Technical Resumes",
        "struct_pub_venue_lbl": "Periódico / Conferência",
        "struct_pub_venue_ph": "IEEE Transactions on AI",
        "struct_pub_year_lbl": "Ano",
        "struct_pub_year_ph": "2023",
        "struct_pub_authors_lbl": "Autores",
        "struct_pub_authors_ph": "Silva, L.; Santos, M.",
        "struct_pub_doi_lbl": "DOI ou Link",
        "struct_pub_doi_ph": "10.1109/CVPR.2023.1001",
        "struct_award_title_lbl": "Título / Certificação",
        "struct_award_title_ph": "AWS Certified Solutions Architect",
        "struct_award_year_lbl": "Ano",
        "struct_award_year_ph": "2023",
        "struct_award_det_lbl": "Instituição / Detalhes",
        "struct_award_det_ph": "Amazon Web Services",
        "manual_raw_text_expander": "📝 Modo Texto Rápido / Colar em Lote (Opcional / Legado)",
        "manual_raw_caption": "Cole informações em formato texto com separador pipe '|' se preferir não usar os campos estruturados acima.",
        "optional_links_title": "🔗 Links de Perfis Opcionais e Foto:",
        "github_label": "GitHub (usuário ou URL)",
        "github_ph": "ex: torvalds ou https://github.com/usuario",
        "orcid_label": "ORCID (ID ou URL)",
        "orcid_ph": "ex: 0000-0002-1825-0097",
        "linkedin_label": "LinkedIn (nick ou URL)",
        "linkedin_ph": "ex: seu-nick ou https://www.linkedin.com/in/seu-perfil/",
        "lattes_label": "Currículo Lattes (ID de 16 dígitos ou URL)",
        "lattes_ph": "ex: 1234567890123456 ou http://lattes.cnpq.br/0000000000000000",
        "photo_label": "Foto de Perfil (opcional — PNG/JPG)",
        "expander_extra": "📎 Complementar LinkedIn / Lattes (Upload XML/ZIP/PDF ou Texto)",
        "expander_caption": (
            "Como o LinkedIn exige login e o Lattes possui CAPTCHA para acesso externo, "
            "você pode anexar o XML/ZIP exportado do Lattes ou o PDF salvo do LinkedIn para extração 100% completa."
        ),
        "lattes_file_label": "Arquivo do Lattes (XML, ZIP ou PDF exportado do CNPq)",
        "linkedin_pdf_label": "PDF do LinkedIn ('Salvar como PDF' no perfil do LinkedIn)",
        "extra_text_label": "Experiências / Publicações / Resumo complementar (opcional)",
        "extra_text_ph": "Cole aqui informações extras do LinkedIn/Lattes, certificações ou descrição da vaga/edital...",
        "sec3_title": "3. Dados Pessoais de Cabeçalho (Opcional — sobrescreve extração)",
        "name_label": "Nome Completo",
        "name_ph": "Detectado automaticamente se vazio",
        "role_label": "Cargo / Título Principal",
        "role_ph": "Ex: Engenheiro de Software Sênior / Doutorando em IA",
        "email_label": "E-mail",
        "email_ph": "seu.email@dominio.com",
        "phone_label": "Telefone / WhatsApp",
        "phone_ph": "+55 (11) 99999-9999",
        "loc_label": "Cidade / Estado / País",
        "loc_ph": "São Paulo, SP, Brasil",
        "gender_label": "Gênero",
        "gender_options": ["Não informado", "Masculino", "Feminino", "Não binário", "Outro"],
        "gen_btn": "🚀 Gerar Currículo",
        "res_header": "📑 Resultado, Preview PDF e Métricas de Tokens",
        "spinner_msg": "Extraindo perfis, otimizando tokens (Caveman + TOON) e compilando PDF via pdflatex...",
        "metric_total": "Tokens Totais API",
        "metric_reasoning": "Reasoning Tokens",
        "metric_saved": "Tokens Economizados",
        "metric_pct": "Economia Estimada",
        "model_used_lbl": "Modelo utilizado",
        "cache_hit_lbl": "Cache Hit",
        "yes_zero_tokens": "Sim (0 tokens gastos)",
        "no_lbl": "Não",
        "pdf_ok_msg": "Currículo PDF compilado com sucesso",
        "dl_pdf_btn": "⬇️ Baixar Currículo (.PDF)",
        "dl_tex_btn": "⬇️ Baixar Código LaTeX (.TEX)",
        "pdf_warn_msg": "O código LaTeX foi gerado, mas houve um alerta na compilação PDF",
        "view_tex_exp": "🔍 Ver Código-Fonte LaTeX Gerado",
        "view_audit_exp": "📊 Ver Auditoria dos Plugins de Economia de Tokens e Dados Extraídos",
        "err_msg": "Erro ao gerar currículo",
        "latex_ok_lbl": "✅ Compilador LaTeX ativo",
        "latex_missing_lbl": "⚠️ Compilador LaTeX (`pdflatex`) não encontrado — instale TeX Live ou MiKTeX",
        "theme_label": "🎨 Tema da Interface",
        "theme_light": "☀️ Modo Claro",
        "theme_dark": "🌙 Modo Escuro",
        "auto_detected_badge": "Detectado automaticamente do seu sistema/navegador",
        "portfolio_label": "Página de Portfólio / Website Pessoal (URL)",
        "portfolio_ph": "https://meuportfolio.dev ou https://seusite.com.br",
        "color_sec_title": "🎨 Cores do Currículo & Preview ao Vivo do Modelo",
        "color_preset_label": "Paleta de Cores Predefinida",
        "color_custom_opt": "✨ Personalizado (Escolher cores manualmente)",
        "primary_color_label": "Cor Principal (Títulos, Linhas & Destaques)",
        "secondary_color_label": "Cor Secundária (Subtítulos & Barra Lateral)",
        "preview_card_title": "👁️ Preview Visual do Modelo LaTeX (Atualiza em Tempo Real)",
        "preview_card_caption": "Representação visual fiel da estrutura tipográfica e das cores selecionadas.",
        "idle_info": (
            "Configure seu perfil, escolha o modelo e as cores à esquerda e clique em "
            "**Gerar Currículo** para compilar o documento final."
        ),
    },
    "en-us": {
        "page_title": "LaTeX Resume Generator — NVIDIA AI",
        "app_title": "Resume Generator",
        "app_caption": (
            "Automatic extraction from GitHub, ORCID, Lattes, LinkedIn & Portfolio • PDF compilation via LaTeX • "
            "Optimized with Token-Saving Plugins (Caveman + TOON + 0-Reasoning)"
        ),
        "lang_selector_label": "🌐 Interface & Resume Language",
        "resume_lang_label": "📝 Resume Output Language",
        "sidebar_header": "⚙️ AI Engine & Token Economy",
        "model_select_label": "AI Model",
        "model_select_help": (
            "Select the model for your chosen provider. Recommended models are validated for high syntactic accuracy "
            "and token efficiency."
        ),
        "custom_key_label": "Provider API Key (Optional)",
        "custom_key_placeholder": "Server default key active",
        "cache_checkbox": "Enable Local SHA-256 Cache (0 tokens on reuse)",
        "plugins_header": "🔌 Active Token-Saving Plugins",
        "plugins_md": (
            "- **CavemanPromptPlugin**: ultra-terse directives with zero preamble (~65% fewer tokens)\n"
            "- **ThinkingSuppressionPlugin**: `enable_thinking=False` (0 tokens spent on hidden CoT)\n"
            "- **TOONContextPrunerPlugin**: tabular minification & local ORCID/Lattes deduplication\n"
            "- **ShortKeySchemaPlugin**: 1–2 char JSON keys during generation\n"
            "- **LaTeXPreambleSplitPlugin**: splits static preamble from `.tex` templates"
        ),
        "plugins_toggle_label": "🔌 Enable token-saving plugins",
        "plugins_toggle_help": (
            "Disable to generate the resume without prompt compression, short JSON keys, or hidden reasoning suppression."
        ),
        "plugin_caveman": "CavemanPrompt (ultra-concise directives)",
        "plugin_thinking": "ThinkingSuppression (0 hidden reasoning tokens)",
        "plugin_toon": "TOONContextPruner (profile minification)",
        "plugin_shortkey": "ShortKeySchema (short JSON keys)",
        "plugin_preamble": "LaTeXPreambleSplit (split static preamble)",
        "plugin_cache": "SHA256Cache (local token cache)",
        "sec1_title": "1. Profile, Mode & LaTeX Template",
        "resume_type_label": "Resume Purpose",
        "resume_type_prof": "Professional (Industry / Corporate / Tech)",
        "resume_type_acad": "Academic (Research / Post-Grad / Faculty)",
        "tpl_mode_label": "LaTeX Template Source",
        "tpl_mode_builtin": "Choose built-in template",
        "tpl_mode_custom": "Provide my own custom LaTeX template (.tex)",
        "tpl_select_label": "Select Resume Template",
        "upload_tex_label": "Upload your `.tex` template file",
        "paste_tex_label": "Or paste your custom LaTeX template code below",
        "sec2_title": "2. Resume Information",
        "header_personal_caption": "Personal Header Details (optional — overrides automatic extraction)",
        "data_mode_label": "Information Input Method",
        "mode_import_label": "📥 Import Data",
        "mode_manual_label": "✍️ Enter Manually",
        "manual_sec_title": "2. Manual Resume Entry",
        "manual_summary_label": "Professional Summary / Bio",
        "manual_summary_ph": "Ex: Dedicated software engineer with 5+ years of experience building scalable systems...",
        "manual_edu_label": "Education (Degree/Course | Institution | Period | Details)",
        "manual_edu_ph": "B.Sc. in Computer Science | MIT | 2018 - 2022 | Focus on Systems and AI\nM.Sc. in Data Science | Stanford | 2022 - 2024",
        "manual_exp_label": "Work Experience (Role | Organization | Period | Location | Description)",
        "manual_exp_ph": "Senior Software Engineer | Tech Corp | 2022 - Present | San Francisco, CA | Led microservices refactoring reducing query latency by 40%.",
        "manual_skills_label": "Skills & Competencies (Category: Technologies / Items)",
        "manual_skills_ph": "Languages: Python, Go, TypeScript\nCloud & DevOps: Docker, Kubernetes, AWS\nDatabases: PostgreSQL, Redis",
        "manual_projects_label": "Relevant Projects (Name | Technologies | URL | Description)",
        "manual_projects_ph": "LaTeX Resume Enclave | Python, Flask, LaTeX | https://github.com/user/latex-resume | Zero-storage encrypted resume synthesis platform.",
        "manual_languages_label": "Languages (Language and Proficiency, comma or line separated)",
        "manual_languages_ph": "English (Native), Portuguese (Fluent), Spanish (Intermediate)",
        "manual_awards_label": "Awards & Certifications (Title | Year | Details)",
        "manual_awards_ph": "AWS Certified Solutions Architect | 2023 | Amazon Web Services\n1st Place National Hackathon | 2022 | Tech Challenge",
        "manual_pubs_label": "Publications & Articles (Title | Venue | Year | Authors | DOI)",
                "manual_pubs_ph": "Neural Parsing of Technical Resumes | IEEE Conference | 2023 | Silva, L.; Santos, A. | 10.1109/CVPR.2023.1001",
        "struct_edu_title": "🎓 Education",
        "struct_exp_title": "💼 Work Experience",
        "struct_proj_title": "🚀 Relevant Projects",
        "struct_pubs_title": "📄 Publications & Papers",
        "struct_awards_title": "🏆 Awards & Certifications",
        "btn_add_edu": "Add Education",
        "btn_add_exp": "Add Experience",
        "btn_add_proj": "Add Project",
        "btn_add_pub": "Add Publication",
        "btn_add_award": "Add Award / Certification",
        "btn_rem_item": "Remove",
        "struct_degree_lbl": "Degree / Course",
        "struct_degree_ph": "B.Sc. in Computer Science",
        "struct_inst_lbl": "Institution",
        "struct_inst_ph": "MIT / Stanford",
        "struct_period_lbl": "Period",
        "struct_period_ph": "2018 - 2022",
        "struct_details_lbl": "Details / Thesis / Honors",
        "struct_details_ph": "Focus on Systems and Machine Learning",
        "struct_role_lbl": "Role / Title",
        "struct_role_ph": "Senior Software Engineer",
        "struct_org_lbl": "Company / Organization",
        "struct_org_ph": "Tech Solutions Corp",
        "struct_loc_lbl": "Location",
        "struct_loc_ph": "San Francisco, CA (or Remote)",
        "struct_desc_lbl": "Description / Achievements",
        "struct_desc_ph": "Led microservices refactoring reducing query latency by 40%.",
        "struct_proj_name_lbl": "Project Name",
        "struct_proj_name_ph": "LaTeX Resume Enclave",
        "struct_proj_tech_lbl": "Technologies Used",
        "struct_proj_tech_ph": "Python, Flask, Docker, LaTeX",
        "struct_proj_url_lbl": "Link / Repository (URL)",
        "struct_proj_url_ph": "https://github.com/user/project",
        "struct_proj_desc_lbl": "Project Description",
        "struct_proj_desc_ph": "Zero-storage encrypted resume synthesis platform.",
        "struct_pub_title_lbl": "Publication Title",
        "struct_pub_title_ph": "Neural Parsing of Technical Resumes",
        "struct_pub_venue_lbl": "Journal / Conference",
        "struct_pub_venue_ph": "IEEE Transactions on AI",
        "struct_pub_year_lbl": "Year",
        "struct_pub_year_ph": "2023",
        "struct_pub_authors_lbl": "Authors",
        "struct_pub_authors_ph": "Silva, L.; Santos, M.",
        "struct_pub_doi_lbl": "DOI or Link",
        "struct_pub_doi_ph": "10.1109/CVPR.2023.1001",
        "struct_award_title_lbl": "Title / Certification",
        "struct_award_title_ph": "AWS Certified Solutions Architect",
        "struct_award_year_lbl": "Year",
        "struct_award_year_ph": "2023",
        "struct_award_det_lbl": "Institution / Details",
        "struct_award_det_ph": "Amazon Web Services",
        "manual_raw_text_expander": "📝 Quick Mode / Paste Raw Text (Optional / Legacy)",
        "manual_raw_caption": "Paste info in text format with pipe '|' separator if you prefer not to use the structured cards above.",
        "optional_links_title": "🔗 Optional Profile Links and Photo:",
        "github_label": "GitHub (username or URL)",
        "github_ph": "e.g. torvalds or https://github.com/username",
        "orcid_label": "ORCID (ID or URL)",
        "orcid_ph": "e.g. 0000-0002-1825-0097",
        "linkedin_label": "LinkedIn (username or URL)",
        "linkedin_ph": "e.g. your-username or https://www.linkedin.com/in/your-profile/",
        "lattes_label": "Lattes CV (16-digit ID or URL)",
        "lattes_ph": "e.g. 1234567890123456 or http://lattes.cnpq.br/0000000000000000",
        "photo_label": "Profile Photo (optional — PNG/JPG)",
        "expander_extra": "📎 Supplement LinkedIn / Lattes (Upload XML/ZIP/PDF or Text)",
        "expander_caption": (
            "Since LinkedIn requires login and Lattes uses CAPTCHA for external access, "
            "you can attach your exported Lattes XML/ZIP or saved LinkedIn PDF for 100% complete extraction."
        ),
        "lattes_file_label": "Lattes File (XML, ZIP, or PDF exported from CNPq)",
        "linkedin_pdf_label": "LinkedIn PDF ('Save to PDF' from your LinkedIn profile)",
        "extra_text_label": "Additional Experience / Publications / Summary (optional)",
        "extra_text_ph": "Paste extra LinkedIn/Lattes details, certifications, or target job/grant description here...",
        "sec3_title": "3. Personal Header Details (Optional — overrides auto-extraction)",
        "name_label": "Full Name",
        "name_ph": "Auto-detected if left blank",
        "role_label": "Primary Role / Headline",
        "role_ph": "e.g. Senior Software Engineer / Ph.D. Researcher in AI",
        "email_label": "E-mail",
        "email_ph": "your.email@domain.com",
        "phone_label": "Phone / Mobile",
        "phone_ph": "+1 (555) 000-0000",
        "loc_label": "City / State / Country",
        "loc_ph": "San Francisco, CA, USA",
        "gender_label": "Gender",
        "gender_options": ["Prefer not to say", "Male", "Female", "Non-binary", "Other"],
        "gen_btn": "🚀 Generate Resume",
        "res_header": "📑 Result, PDF Preview & Token Metrics",
        "spinner_msg": "Extracting profiles & portfolio, optimizing tokens (Caveman + TOON), and compiling PDF via pdflatex...",
        "metric_total": "Total API Tokens",
        "metric_reasoning": "Reasoning Tokens",
        "metric_saved": "Tokens Saved",
        "metric_pct": "Estimated Savings",
        "model_used_lbl": "Model used",
        "cache_hit_lbl": "Cache Hit",
        "yes_zero_tokens": "Yes (0 tokens spent)",
        "no_lbl": "No",
        "pdf_ok_msg": "PDF Resume successfully compiled",
        "dl_pdf_btn": "⬇️ Download Resume (.PDF)",
        "dl_tex_btn": "⬇️ Download LaTeX Source (.TEX)",
        "pdf_warn_msg": "LaTeX code was generated, but PDF compilation reported a warning",
        "view_tex_exp": "🔍 View Generated LaTeX Source Code",
        "view_audit_exp": "📊 View Token-Saving Plugin Audit & Extracted Data",
        "err_msg": "Error generating resume",
        "latex_ok_lbl": "✅ LaTeX Compiler active",
        "latex_missing_lbl": "⚠️ LaTeX Compiler (`pdflatex`) not found — install TeX Live or MiKTeX",
        "theme_label": "🎨 Interface Theme",
        "theme_light": "☀️ Light Mode",
        "theme_dark": "🌙 Dark Mode",
        "auto_detected_badge": "Auto-detected from your OS/Browser",
        "portfolio_label": "Portfolio Page / Personal Website (URL)",
        "portfolio_ph": "https://myportfolio.dev or https://yourwebsite.com",
        "color_sec_title": "🎨 Resume Color Customization & Live Template Preview",
        "color_preset_label": "Color Palette Preset",
        "color_custom_opt": "✨ Custom (Pick colors manually)",
        "primary_color_label": "Primary Color (Headings, Rules & Accents)",
        "secondary_color_label": "Secondary Color (Subtitles & Sidebar)",
        "preview_card_title": "👁️ Live Visual Preview of LaTeX Template",
        "preview_card_caption": "Real-time visual representation of the layout structure and selected colors.",
        "idle_info": (
            "Configure your profile, choose your template and colors on the left, and click "
            "**Generate Resume** to compile the final document."
        ),
    },
}


def translate_institution_to_en(inst: str) -> str:
    """Padroniza e traduz nomes de instituições acadêmicas e de pesquisa para o inglês."""
    if not inst:
        return ""
    s = inst.strip()
    low = "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    ).lower()

    if any(k in low for k in ("vicosa", "ufv")):
        return "Federal University of Viçosa (UFV)"
    if any(k in low for k in ("minas gerais", "ufmg")):
        return "Federal University of Minas Gerais (UFMG)"
    if any(k in low for k in ("sao paulo", "usp")):
        return "University of São Paulo (USP)"
    if "campinas" in low or "unicamp" in low:
        return "State University of Campinas (UNICAMP)"
    if "rio de janeiro" in low or "ufrj" in low:
        return "Federal University of Rio de Janeiro (UFRJ)"
    if "santa catarina" in low or "ufsc" in low:
        return "Federal University of Santa Catarina (UFSC)"
    if "rio grande do sul" in low or "ufrgs" in low:
        return "Federal University of Rio Grande do Sul (UFRGS)"
    if "funarben" in low:
        return "FUNARBEN / Federal University of Viçosa"
    return s


def translate_role_to_en(role: str) -> str:
    """Traduz e padroniza cargos, monitorias, bolsas e atuações profissionais para o inglês."""
    if not role:
        return ""
    r = role.strip()
    norm = "".join(
        c for c in unicodedata.normalize("NFKD", r) if not unicodedata.combining(c)
    ).lower()

    if "jogo" in norm or "game" in norm:
        if any(k in norm for k in ("monitor", "teaching assistant", "ta", "tutor")):
            return "Introduction to Game Development Teaching Assistant"
    if "programacao" in norm or "programming" in norm:
        if any(k in norm for k in ("monitor", "teaching assistant", "ta")):
            return "Programming Teaching Assistant"
        if "tutor" in norm:
            return "Programming Tutor"
    if any(k in norm for k in ("monitor", "monitoria")):
        return "Teaching Assistant"
    if any(k in norm for k in ("tutor", "tutoria")):
        return "Tutor"

    if "extensao" in norm or "extension" in norm:
        if any(k in norm for k in ("bolsista", "fellow")):
            return "Extension Project Fellow"
    if "pesquisa" in norm or "iniciacao cientifica" in norm or "research" in norm:
        if any(k in norm for k in ("bolsista", "fellow")):
            return "Research Fellow"
    if "bolsista" in norm:
        return "Project Fellow"

    if "comissao eleitoral" in norm or "electoral committee" in norm:
        return "Student Electoral Board Member"

    if "desenvolvedor" in norm:
        if "full stack" in norm or "fullstack" in norm:
            return "Full-Stack Software Developer"
        return "Software Developer"
    if "engenheiro de software" in norm:
        return "Software Engineer"
    if "pesquisador" in norm:
        return "Researcher"

    return r


def translate_award_to_en(award: str) -> str:
    """Padroniza e traduz menções, colocações e simpósios em prêmios para o inglês."""
    if not award:
        return ""
    s = str(award).strip()
    replacements = [
        (r"(?i)\bmen[cç][aã]o honrosa\b", "Honorable Mention"),
        (r"(?i)\bprimeiro lugar\b", "First Place"),
        (r"(?i)\b1[ºªo]\s*lugar\b", "First Place"),
        (r"(?i)\bsegundo lugar\b", "Second Place"),
        (r"(?i)\b2[ºªo]\s*lugar\b", "Second Place"),
        (r"(?i)\bterceiro lugar\b", "Third Place"),
        (r"(?i)\b3[ºªo]\s*lugar\b", "Third Place"),
        (r"(?i)\bp[oô]ster\b", "Poster Presentation"),
        (r"(?i)\bensino\b", "Teaching"),
        (r"(?i)\bpesquisa\b", "Research"),
        (r"(?i)\bextens[aã]o\b", "Extension"),
        (r"(?i)\bapresenta[cç][aã]o oral\b", "Oral Presentation"),
        (r"(?i)\bmelhor artigo\b", "Best Paper Award"),
        (r"(?i)\bmelhor trabalho\b", "Best Work Award"),
        (r"(?i)\bmelhor tese\b", "Best Doctoral Thesis Award"),
        (r"(?i)\bmelhor disserta[cç][aã]o\b", "Best Master's Dissertation Award"),
        (r"(?i)\bsimp[oó]sio de integra[cç][aã]o acad[eê]mica\b", "Academic Integration Symposium"),
        (r"(?i)\buniversidade federal de vi[cç]osa\b", "Federal University of Viçosa"),
        (r"(?i)\buniversidade federal de minas gerais\b", "Federal University of Minas Gerais"),
    ]
    for pat, repl in replacements:
        s = re.sub(pat, repl, s)
    return s


def translate_experience_bullet_to_en(bullet: str) -> str:
    """Traduz descrições e bullets de experiências em português para o inglês formal."""
    if not bullet:
        return ""
    s = bullet.strip()
    if re.match(
        r"^(?:Leadership|Management|Development|Design|Implementation|Creation|Instruction|Teaching|Mentorship|Guidance|Participation|Assistance|Conduction|Coordination|Collaboration|Organization|Engineering|Research|Volunteer)\b",
        s,
        re.IGNORECASE,
    ):
        return s

    norm = "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    ).lower()

    if "orientacao pratica" in norm or ("estudantes" in norm and ("desenvolvimento de jogos" in norm or "jogos" in norm)):
        return "Practical guidance and technical mentoring for students in the game development course."
    if "geogebra" in norm and ("figuras dinamicas" in norm or "ensino de matematica" in norm):
        return "Development of dynamic interactive figures in GeoGebra for mathematics education and academic outreach."
    if "trabalho voluntario" in norm or "ciencia e tecnologia" in norm:
        return "Volunteer work in Science and Technology, supporting academic events and educational workshops."
    if "processo eleitoral" in norm or "membro discente" in norm or "comissao eleitoral" in norm:
        return "Participation in the academic election process as student committee representative."
    if "ensino de conceitos" in norm and "historia da computacao" in norm:
        return "Instruction in fundamental concepts of computing history and digital game development."

    phrase_maps = [
        (r"(?i)^\s*(?:orienta[cç][aã]o(?:\s+[aà])?|orientou)\s+estudantes\b", "Guidance and mentorship of students"),
        (r"(?i)^\s*(?:acompanhamento(?:\s+de)?|acompanhou)\s+estudantes\b", "Mentoring and technical support for students"),
        (r"(?i)^\s*(?:desenvolvimento(?:\s+de)?|desenvolveu)\s+", "Development of "),
        (r"(?i)^\s*(?:ensino(?:\s+de)?|ensinou)\s+", "Instruction in "),
        (r"(?i)^\s*(?:participa[cç][aã]o(?:\s+(?:no|na|em))?|participou(?:\s+(?:no|na|em))?)\s+", "Participation in "),
        (r"(?i)^\s*(?:realiza[cç][aã]o(?:\s+de)?|realizou)\s+", "Execution and conduction of "),
        (r"(?i)^\s*(?:colabora[cç][aã]o(?:\s+(?:com|em))?|colaborou(?:\s+(?:com|em))?)\s+", "Collaboration on "),
        (r"(?i)^\s*(?:coordena[cç][aã]o(?:\s+de)?|coordenou)\s+", "Coordination of "),
        (r"(?i)^\s*(?:implementa[cç][aã]o(?:\s+de)?|implementou)\s+", "Implementation of "),
        (r"(?i)^\s*(?:cria[cç][aã]o(?:\s+de)?|criou)\s+", "Creation of "),
        (r"(?i)^\s*(?:pesquisa(?:\s+(?:sobre|em))?|pesquisou)\s+", "Research on "),
        (r"(?i)^\s*(?:apoio(?:\s+[aào])?|apoiou)\s+", "Support for "),
        (r"(?i)^\s*(?:atua[cç][aã]o(?:\s+(?:como|no|na|em))?|atuou)\s+", "Work as "),
    ]
    for pat, repl in phrase_maps:
        if re.search(pat, s):
            s = re.sub(pat, repl, s, count=1)
            break

    vocab = [
        (r"(?i)\be apoio no\b", "and support in"),
        (r"(?i)\be apoio [aà]\b", "and support for"),
        (r"(?i)\be apoio ao\b", "and support for"),
        (r"(?i)\be apoio aos\b", "and support for"),
        (r"(?i)\be acompanhamento de\b", "and mentoring of"),
        (r"(?i)\bdisciplina de desenvolvimento de jogos\b", "game development course"),
        (r"(?i)\bdesenvolvimento de jogos\b", "game development"),
        (r"(?i)\bensino de matem[aá]tica\b", "mathematics education"),
        (r"(?i)\beduca[cç][aã]o b[aá]sica\b", "basic education"),
        (r"(?i)\batividades de extens[aã]o\b", "extension outreach activities"),
        (r"(?i)\beventos acad[eê]micos\b", "academic events"),
        (r"(?i)\boficinas educacionais\b", "educational workshops"),
        (r"(?i)\bmembro discente\b", "student representative"),
        (r"(?i)\bcomiss[aã]o eleitoral\b", "electoral committee"),
    ]
    for pat, repl in vocab:
        s = re.sub(pat, repl, s)

    return s


def standardize_summary_to_en(summary: str, cv: Dict[str, Any] | None = None) -> str:
    """Converte e padroniza o resumo profissional/acadêmico em português para o inglês."""
    if not summary:
        return ""
    s = summary.strip()
    norm = "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    ).lower()

    pt_markers = (
        "ensino", "pesquisa", "atuacao", "desenvolvimento", "projetos",
        "sistemas", "computacao", "ciencia", "membro", "orientacao",
        "bolsista", "extensao", "graduado", "mestrando", "especialista",
    )
    if not any(m in norm for m in pt_markers):
        return s

    if "ensino de conceitos" in norm and "computacao" in norm:
        return (
            "Computer Science researcher and software developer with expertise in educational technologies, "
            "computing history, and digital game development. Experience with university extension programs, "
            "interactive mathematical tools, and full-stack software engineering."
        )

    s_en = s
    terms = [
        (r"(?i)\bensino de conceitos relacionados [aà] hist[oó]ria da computa[cç][aã]o e jogos digitais\b", "instruction in concepts related to the history of computing and digital game development"),
        (r"(?i)\batua[cç][aã]o em projetos de extens[aã]o universit[aá]ria\b", "experience in university extension projects"),
        (r"(?i)\bpesquisa acad[eê]mica e desenvolvimento de software\b", "academic research and software development"),
        (r"(?i)\bmestrando em ci[eê]ncia da computa[cç][aã]o\b", "M.Sc. student in Computer Science"),
        (r"(?i)\bbacharel em sistemas de informa[cç][aã]o\b", "B.Sc. graduate in Information Systems"),
        (r"(?i)\bci[eê]ncia da computa[cç][aã]o\b", "Computer Science"),
        (r"(?i)\bsistemas de informa[cç][aã]o\b", "Information Systems"),
        (r"(?i)\bdesenvolvimento de software\b", "software development"),
        (r"(?i)\bintelig[eê]ncia artificial\b", "artificial intelligence"),
        (r"(?i)\baprendizado de m[aá]quina\b", "machine learning"),
        (r"(?i)\bcomputa[cç][aã]o gr[aá]fica\b", "computer graphics"),
        (r"(?i)\bjogos digitais\b", "digital games"),
        (r"(?i)\bprojetos de extens[aã]o\b", "extension outreach projects"),
    ]
    for pat, repl in terms:
        s_en = re.sub(pat, repl, s_en)

    norm_res = "".join(
        c for c in unicodedata.normalize("NFKD", s_en) if not unicodedata.combining(c)
    ).lower()
    if any(k in norm_res for k in ("ensino", "atuacao", "pesquisa", "projetos", "desenvolvimento", "voltados para")):
        return (
            "Computer Scientist and Software Engineer with experience in software development, "
            "academic research, and educational technology. Strong foundation in algorithms, "
            "interactive systems, and modern software architecture."
        )

    return s_en
