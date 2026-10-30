"""Interface Web Bilíngue (pt-BR / en-US) com Detecção Automática de Tema/Idioma, Preview de Templates LaTeX, Customização de Cores e Portfólio."""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path

import streamlit as st

from src.compiler import check_latex_compiler, secure_wipe_and_remove_dir
from src.config import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    PROJECT_ROOT,
    PROVIDERS_CONFIG,
    RECOMMENDED_MODELS,
)
from src.i18n import MODELS_I18N, TEMPLATES_I18N, UI_TEXT, normalize_lang
from src.pipeline import build_resume_pipeline
from src.templates import BUILTIN_TEMPLATES
from src.ui_theme import (
    COLOR_PRESETS,
    detect_default_language,
    detect_default_theme,
    get_theme_css,
    render_template_preview_html,
)

FAVICON_PATH = PROJECT_ROOT / "assets" / "icons" / "favicon.png"
FAVICON_ICO_PATH = PROJECT_ROOT / "assets" / "icons" / "favicon.ico"
if not FAVICON_PATH.exists():
    FAVICON_PATH = PROJECT_ROOT / "assets" / "favicon.png"
if not FAVICON_PATH.exists():
    FAVICON_PATH = PROJECT_ROOT / "favicon.png"

st.set_page_config(
    page_title="LaTeX Resume Generator — NVIDIA AI",
    page_icon=str(FAVICON_ICO_PATH) if FAVICON_ICO_PATH.exists() else (str(FAVICON_PATH) if FAVICON_PATH.exists() else "📄"),
    layout="wide",
    initial_sidebar_state="expanded",
)

# 1. Detecção automática de idioma e tema padrão do usuário (Navegador / Sistema Operacional)
headers_dict = {}
try:
    if hasattr(st, "context") and hasattr(st.context, "headers"):
        headers_dict = dict(st.context.headers)
except Exception:
    pass

if "auto_lang" not in st.session_state:
    st.session_state["auto_lang"] = detect_default_language(headers_dict)
if "auto_theme" not in st.session_state:
    st.session_state["auto_theme"] = detect_default_theme(headers_dict)

# Inicializa estado dos botões de toggle (idioma UI, tema, idioma PDF)
if "ui_lang" not in st.session_state:
    st.session_state["ui_lang"] = "en-us" if st.session_state["auto_lang"] == "en-us" else "pt-br"
if "active_theme" not in st.session_state:
    st.session_state["active_theme"] = "light" if st.session_state["auto_theme"] == "light" else "dark"
if "resume_lang" not in st.session_state:
    st.session_state["resume_lang"] = st.session_state["ui_lang"]

default_lang_idx = 1 if st.session_state["auto_lang"] == "en-us" else 0
default_theme_idx = 0 if st.session_state["auto_theme"] == "light" else 1

# Resolve idioma/tema do estado da sessão (usado pelos botões de toggle na sidebar)
ui_lang = st.session_state.get("ui_lang", "en-us" if st.session_state["auto_lang"] == "en-us" else "pt-br")
active_theme = st.session_state.get("active_theme", "light" if st.session_state["auto_theme"] == "light" else "dark")
resume_lang = normalize_lang(st.session_state.get("resume_lang", ui_lang))
txt = UI_TEXT[ui_lang]

with st.sidebar:
    if FAVICON_PATH.exists():
        st.image(str(FAVICON_PATH), width=56)
    st.markdown("### **LaTeX Resume Generator**\n*NVIDIA NIM • Multi-Provider*")
    st.divider()

    # Idioma da interface — botão de toggle único
    st.markdown(f"**{txt['lang_selector_label']}**")
    if st.button(
        ("🇧🇷 Português (pt-BR)" if ui_lang == "pt-br" else "🇺🇸 English (en-US)"),
        key="lang_toggle",
        use_container_width=True,
        type="primary",
    ):
        st.session_state["ui_lang"] = "en-us" if ui_lang == "pt-br" else "pt-br"
        st.rerun()

    # Tema da interface — botão de toggle único
    st.markdown(f"**{txt['theme_label']}**")
    if st.button(
        (txt["theme_light"] if active_theme == "light" else txt["theme_dark"]),
        key="theme_toggle",
        use_container_width=True,
        type="primary",
    ):
        st.session_state["active_theme"] = "dark" if active_theme == "light" else "light"
        st.rerun()

    # Idioma do PDF — botão de toggle único
    st.markdown(f"**{txt.get('resume_lang_label', '📝 Idioma do Currículo PDF / Resume Output Language')}**")
    if st.button(
        ("🇧🇷 Português (pt-BR)" if resume_lang == "pt-br" else "🇺🇸 English (en-US)"),
        key="pdf_lang_toggle",
        use_container_width=True,
        type="primary",
    ):
        st.session_state["resume_lang"] = "en-us" if resume_lang == "pt-br" else "pt-br"
        st.rerun()

    latex_ok, latex_ver = check_latex_compiler()
    if latex_ok:
        st.caption(f"{txt['latex_ok_lbl']}: `{latex_ver}`")
    else:
        st.error(txt["latex_missing_lbl"])

    st.divider()
    generate_btn = st.button(
        txt["gen_btn"],
        type="primary",
        use_container_width=True,
        key="sidebar_generate_btn",
    )
    st.divider()
    st.header(txt["sidebar_header"])

    prov_labels = {}
    for pid, pinfo in PROVIDERS_CONFIG.items():
        label = pinfo["name_en"] if ui_lang == "en-us" else pinfo["name"]
        prov_labels[label] = pid

    prov_title = "🧠 " + ("Provedor de IA" if ui_lang == "pt-br" else "AI Provider")
    # Remove "default" (NVIDIA NIM padrão) from Streamlit UI — only available via CLI/programmatic API
    prov_options = [k for k, v in prov_labels.items() if v != "default"]
    default_prov_idx = prov_options.index(
        next(k for k, v in prov_labels.items() if v == "none")
    ) if "none" in prov_labels.values() else 0
    selected_prov_label = st.selectbox(
        prov_title,
        options=prov_options,
        index=default_prov_idx,
    )
    selected_provider = prov_labels[selected_prov_label]
    prov_data = PROVIDERS_CONFIG[selected_provider]

    model_options = {
        m["name"]: m["id"]
        for m in prov_data.get("models", [])
    }
    selected_model_label = st.selectbox(
        txt["model_select_label"],
        options=list(model_options.keys()),
        index=0,
        help=txt["model_select_help"],
    )
    selected_model = model_options[selected_model_label]

    key_placeholder = prov_data.get("key_placeholder_en" if ui_lang == "en-us" else "key_placeholder", "nvapi-...")
    key_help = (
        "Sua chave é mantida estritamente em memória volátil durante a requisição, "
        "sendo imediatamente destruída com bytes nulos (0x00). Nunca é salva em disco ou persistida."
        if ui_lang == "pt-br"
        else "Your key is kept strictly in volatile RAM during the request, "
        "and immediately wiped with null bytes (0x00). Never written to disk or persisted."
    )
    custom_api_key = st.text_input(
        txt["custom_key_label"],
        value="",
        type="password",
        placeholder=key_placeholder,
        help=key_help,
    )
    use_cache = st.checkbox(txt["cache_checkbox"], value=True)

    st.divider()
    st.subheader(txt["plugins_header"])
    st.caption(txt["plugins_toggle_help"])
    plugin_caveman = st.checkbox(
        f"{txt['plugin_caveman']} — diretivas ultra-concisas sem preâmbulo (~-65% menos tokens)",
        value=True, key="plugin_caveman_cb",
    )
    plugin_thinking = st.checkbox(
        f"{txt['plugin_thinking']} — `enable_thinking=False` (0 tokens gastos em CoT oculto)",
        value=True, key="plugin_thinking_cb",
    )
    plugin_toon = st.checkbox(
        f"{txt['plugin_toon']} — minificação tabular e deduplicação local ORCID/Lattes",
        value=True, key="plugin_toon_cb",
    )
    plugin_shortkey = st.checkbox(
        f"{txt['plugin_shortkey']} — chaves JSON de 1–2 letras na geração",
        value=True, key="plugin_shortkey_cb",
    )
    plugin_preamble = st.checkbox(
        f"{txt['plugin_preamble']} — separa preâmbulo fixo de templates `.tex`",
        value=True, key="plugin_preamble_cb",
    )
    plugin_cache = st.checkbox(
        f"{txt['plugin_cache']} — cache local SHA-256 (0 tokens em reuso)",
        value=True, key="plugin_cache_cb",
    )

    ai_mode = "disabled" if selected_provider == "none" else "auto"
    if selected_provider != "none":
        review_only_cb = st.checkbox(
            "⚡ Modo Apenas Revisão (Economia Máxima de Tokens)" if ui_lang == "pt-br" else "⚡ Review-Only Mode (Maximum Token Savings)",
            value=True,
            help=(
            "Gera o currículo determinístico a partir dos extratores e usa a IA para auditar/revisar tanto o código LaTeX quanto os textos e bullet points, economizando até ~75% de tokens."
            if ui_lang == "pt-br"
            else "Generates a deterministic resume from extractors first, using AI to audit/review both the LaTeX code and the text phrasing, saving up to ~75% tokens."
        ),
        )
        if review_only_cb:
            ai_mode = "review_only"

# Cabeçalho da página com ícone e título (ícone embutido para não ser cortado)
if FAVICON_PATH.exists():
    import base64 as _b64
    _icon_b64 = _b64.b64encode(FAVICON_PATH.read_bytes()).decode("utf-8")
    _icon_mime = "image/png" if FAVICON_PATH.suffix.lower() == ".png" else "image/x-icon"
    st.markdown(
        f'<img src="data:{_icon_mime};base64,{_icon_b64}" '
        f'style="width:32px;height:32px;vertical-align:middle;margin-right:0.5rem;">'
        f'<span style="font-size:1.75rem;font-weight:700;vertical-align:middle;">{txt["app_title"]}</span>',
        unsafe_allow_html=True,
    )
else:
    st.title(txt["app_title"])
st.caption(txt["app_caption"])

# Botão de gerar currículo: aparece na barra lateral quando aberta,
# fixado no canto superior esquerdo quando a barra lateral está oculta.
st.markdown(
    """
    <style>
    .fixed-generate-btn {
        position: fixed;
        top: 1rem;
        left: 1rem;
        z-index: 9999;
        display: none;
    }
    </style>
    <button class="fixed-generate-btn" id="fixed-generate-btn" onclick="clickSidebarGenerate()">🚀 """ + txt["gen_btn"] + """</button>
    <script>
    (function() {
        var btn = document.getElementById('fixed-generate-btn');
        if (!btn) return;
        function isSidebarCollapsed() {
            // Streamlit renders a toggle button when sidebar is collapsed
            var collapsed = document.querySelector('[data-testid="collapsedControl"]');
            if (collapsed && collapsed.offsetParent !== null) return true;
            // Also check if sidebar itself is hidden/collapsed via class
            var sidebar = document.querySelector('[data-testid="stSidebar"]');
            if (sidebar && sidebar.classList.contains('collapsed')) return true;
            return false;
        }
        function check() {
            btn.style.display = isSidebarCollapsed() ? 'inline-flex' : 'none';
        }
        check();
        // Força a barra lateral a abrir no carregamento inicial da página
        setTimeout(function() {
            var collapsed = document.querySelector('[data-testid="collapsedControl"]');
            if (collapsed && collapsed.offsetParent !== null) {
                collapsed.click();
            }
        }, 800);
        setInterval(check, 400);
        // Also react to DOM changes (sidebar toggle)
        var observer = new MutationObserver(check);
        observer.observe(document.body, { childList: true, subtree: true });
    })();
    function clickSidebarGenerate() {
        var buttons = document.querySelectorAll('button:not(.fixed-generate-btn)');
        for (var i = 0; i < buttons.length; i++) {
            var t = buttons[i].textContent || '';
            if (t.includes('Gerar Currículo') || t.includes('Generate Resume')) {
                buttons[i].click();
                break;
            }
        }
    }
    </script>
    """,
    unsafe_allow_html=True,
)

# CSS responsivo: em telas finas, o preview fica acima das configurações
st.markdown(
    """
    <style>
    @media (max-width: 768px) {
        .resume-layout { display: flex; flex-direction: column-reverse; gap: 1.5rem; }
        .resume-layout > div { width: 100% !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="resume-layout">', unsafe_allow_html=True)
col_left, col_right = st.columns([1.08, 0.92], gap="large")

with col_left:
    # Seção 1: Modalidade e Modelo LaTeX
    st.subheader(txt["sec1_title"])
    c1, c2 = st.columns(2)
    with c1:
        resume_type_label = st.radio(
            txt["resume_type_label"],
            options=[txt["resume_type_prof"], txt["resume_type_acad"]],
            index=0,
        )
        resume_type = "academico" if resume_type_label == txt["resume_type_acad"] else "profissional"

    with c2:
        template_mode = st.radio(
            txt["tpl_mode_label"],
            options=[txt["tpl_mode_builtin"], txt["tpl_mode_custom"]],
            index=0,
        )

    custom_latex_str: str | None = None
    selected_template_id = "academic_classic" if resume_type == "academico" else "ai_ats_max"

    if template_mode == txt["tpl_mode_builtin"]:
        tpl_loc = TEMPLATES_I18N[ui_lang]
        tpl_labels = {
            tpl_loc.get(k, {}).get("name", v["name"]): k
            for k, v in BUILTIN_TEMPLATES.items()
            if (k != "academic_classic" or resume_type == "academico")
            and (k != "modern_pro" or resume_type != "academico")
        }
        default_tpl = "academic_classic" if resume_type == "academico" else "ai_ats_max"
        tpl_values = list(tpl_labels.values())
        default_idx = tpl_values.index(default_tpl) if default_tpl in tpl_values else 0
        chosen_label = st.selectbox(
            txt["tpl_select_label"],
            options=list(tpl_labels.keys()),
            index=default_idx,
        )
        selected_template_id = tpl_labels[chosen_label]
        st.info(tpl_loc.get(selected_template_id, {}).get("description", ""))
    else:
        uploaded_tex = st.file_uploader(txt["upload_tex_label"], type=["tex"])
        pasted_tex = st.text_area(
            txt["paste_tex_label"],
            height=160,
            placeholder="\\documentclass{article}\n\\begin{document}\n...\n\\end{document}",
        )
        if uploaded_tex is not None:
            custom_latex_str = uploaded_tex.read().decode("utf-8", errors="ignore")
        elif pasted_tex.strip():
            custom_latex_str = pasted_tex.strip()

    # Seção de Customização de Cores do Currículo
    st.subheader(txt["color_sec_title"])
    preset_map = {v[ui_lang]: k for k, v in COLOR_PRESETS.items()}
    preset_options = list(preset_map.keys()) + [txt["color_custom_opt"]]
    default_preset_idx = 0

    col_preset, col_c1, col_c2 = st.columns([1.6, 0.7, 0.7])
    with col_preset:
        selected_preset_label = st.selectbox(
            txt["color_preset_label"],
            options=preset_options,
            index=default_preset_idx,
        )

    if selected_preset_label != txt["color_custom_opt"]:
        preset_key = preset_map[selected_preset_label]
        default_p_col = COLOR_PRESETS[preset_key]["primary"]
        default_s_col = COLOR_PRESETS[preset_key]["secondary"]
    else:
        default_p_col = "#18181B"
        default_s_col = "#3F3F46"

    with col_c1:
        primary_color = st.color_picker(txt["primary_color_label"], value=default_p_col)
    with col_c2:
        secondary_color = st.color_picker(txt["secondary_color_label"], value=default_s_col)

    # Aplica folha de estilo CSS do tema (Claro / Escuro) com a cor de destaque escolhida
    st.markdown(get_theme_css(active_theme, primary_color), unsafe_allow_html=True)

    # Preview Visual ao Vivo do Modelo LaTeX e das Cores Selecionadas (acima da Seção 2)
    st.subheader(txt["preview_card_title"])
    st.caption(txt["preview_card_caption"])
    preview_html = render_template_preview_html(
        template_id=selected_template_id,
        primary_color=primary_color,
        secondary_color=secondary_color,
        lang=resume_lang,
        has_photo=True,
    )
    preview_label = "Pré-visualização visual do currículo" if resume_lang == "pt-br" else "Resume visual preview"
    preview_markup = f'<div role="region" aria-label="{preview_label}">{preview_html}</div>'
    if hasattr(st, "html"):
        st.html(preview_markup)
    else:
        st.markdown(preview_html, unsafe_allow_html=True)
    st.divider()

    # Seção 2: Informações do Currículo (inclui dados pessoais do cabeçalho)
    st.subheader(txt["sec2_title"])

    # Dados Pessoais do Cabeçalho (unidos da sessão anterior)
    st.caption(txt.get("header_personal_caption", "Dados Pessoais do Cabeçalho (opcional — sobrescreve extração automática)"))
    h1, h2 = st.columns(2)
    with h1:
        user_name = st.text_input(txt["name_label"], placeholder=txt["name_ph"])
        user_role = st.text_input(txt["role_label"], placeholder=txt["role_ph"])
        user_email = st.text_input(txt["email_label"], placeholder=txt["email_ph"])
    with h2:
        user_phone = st.text_input(txt["phone_label"], placeholder=txt["phone_ph"])
        user_location = st.text_input(txt["loc_label"], placeholder=txt["loc_ph"])
        user_gender = st.selectbox(
            txt["gender_label"],
            options=txt["gender_options"],
            index=0,
        )
    st.divider()

    if "data_mode" not in st.session_state:
        st.session_state["data_mode"] = "manual"
    is_manual_mode = st.session_state["data_mode"] == "manual"
    toggle_mode_label = txt["mode_import_label"] if is_manual_mode else txt["mode_manual_label"]
    if st.button(toggle_mode_label, key="data-mode-toggle", use_container_width=True):
        st.session_state["data_mode"] = "import" if is_manual_mode else "manual"
        st.rerun()
    is_manual_mode = st.session_state["data_mode"] == "manual"
    manual_data_dict: dict = {}

    if not is_manual_mode:
        p1, p2 = st.columns(2)
        with p1:
            github_input = st.text_input(txt["github_label"], placeholder=txt["github_ph"])
            orcid_input = st.text_input(txt["orcid_label"], placeholder=txt["orcid_ph"])
            portfolio_url = st.text_input(txt["portfolio_label"], placeholder=txt["portfolio_ph"])
        with p2:
            linkedin_url = st.text_input(txt["linkedin_label"], placeholder=txt["linkedin_ph"])
            lattes_url = st.text_input(txt["lattes_label"], placeholder=txt["lattes_ph"])
            photo_upload = st.file_uploader(
                txt["photo_label"],
                type=["png", "jpg", "jpeg", "webp"],
            )

        with st.expander(txt["expander_extra"]):
            st.caption(txt["expander_caption"])
            lattes_file = st.file_uploader(
                txt["lattes_file_label"],
                type=["xml", "zip", "pdf", "html"],
            )
            linkedin_pdf = st.file_uploader(
                txt["linkedin_pdf_label"],
                type=["pdf"],
            )
            extra_profile_text = st.text_area(
                txt["extra_text_label"],
                height=100,
                placeholder=txt["extra_text_ph"],
            )
    else:
        man_summary = st.text_area(
            txt["manual_summary_label"],
            height=80,
            placeholder=txt["manual_summary_ph"],
        )
        sk_col1, sk_col2 = st.columns(2)
        with sk_col1:
            man_skills = st.text_area(
                txt["manual_skills_label"],
                height=80,
                placeholder=txt["manual_skills_ph"],
            )
        with sk_col2:
            man_languages = st.text_input(
                txt["manual_languages_label"],
                placeholder=txt["manual_languages_ph"],
            )

        # 1. Formação Acadêmica Estruturada
        st.markdown(f"#### {txt.get('struct_edu_title', '🎓 Formação Acadêmica')}")
        if "man_edu_count" not in st.session_state:
            st.session_state.man_edu_count = 1
        structured_edu = []
        for i in range(st.session_state.man_edu_count):
            with st.expander(f"🎓 {txt.get('struct_degree_lbl', 'Formação')} #{i + 1}", expanded=(i == 0)):
                e1, e2 = st.columns(2)
                with e1:
                    deg = st.text_input(txt.get("struct_degree_lbl", "Grau / Curso"), key=f"edu_deg_{i}", placeholder=txt.get("struct_degree_ph", "Bacharelado em Ciência da Computação"))
                    inst = st.text_input(txt.get("struct_inst_lbl", "Instituição"), key=f"edu_inst_{i}", placeholder=txt.get("struct_inst_ph", "USP / UNICAMP"))
                with e2:
                    period = st.text_input(txt.get("struct_period_lbl", "Período"), key=f"edu_period_{i}", placeholder=txt.get("struct_period_ph", "2018 - 2022"))
                    details = st.text_input(txt.get("struct_details_lbl", "Detalhes / Ênfase / Tese"), key=f"edu_det_{i}", placeholder=txt.get("struct_details_ph", "Foco em Inteligência Artificial"))
                if deg or inst:
                    structured_edu.append({"degree": deg, "institution": inst, "period": period, "details": details})
        b_e1, b_e2 = st.columns([0.5, 0.5])
        with b_e1:
            if st.button("➕ " + txt.get("btn_add_edu", "Adicionar Formação"), key="btn_add_edu"):
                st.session_state.man_edu_count += 1
                st.rerun()
        with b_e2:
            if st.session_state.man_edu_count > 1 and st.button("➖ " + txt.get("btn_rem_item", "Remover"), key="btn_rem_edu"):
                st.session_state.man_edu_count -= 1
                st.rerun()

        # 2. Experiência Profissional Estruturada
        st.markdown(f"#### {txt.get('struct_exp_title', '💼 Experiência Profissional')}")
        if "man_exp_count" not in st.session_state:
            st.session_state.man_exp_count = 1
        structured_exp = []
        for i in range(st.session_state.man_exp_count):
            with st.expander(f"💼 {txt.get('struct_role_lbl', 'Experiência')} #{i + 1}", expanded=(i == 0)):
                x1, x2 = st.columns(2)
                with x1:
                    role = st.text_input(txt.get("struct_role_lbl", "Cargo / Título"), key=f"exp_role_{i}", placeholder=txt.get("struct_role_ph", "Engenheiro de Software Sênior"))
                    org = st.text_input(txt.get("struct_org_lbl", "Empresa / Organização"), key=f"exp_org_{i}", placeholder=txt.get("struct_org_ph", "Tech Corp"))
                with x2:
                    period = st.text_input(txt.get("struct_period_lbl", "Período"), key=f"exp_period_{i}", placeholder=txt.get("struct_period_ph", "2022 - Atual"))
                    loc = st.text_input(txt.get("struct_loc_lbl", "Localização"), key=f"exp_loc_{i}", placeholder=txt.get("struct_loc_ph", "São Paulo, SP (ou Remoto)"))
                desc = st.text_area(txt.get("struct_desc_lbl", "Descrição / Realizações"), key=f"exp_desc_{i}", height=70, placeholder=txt.get("struct_desc_ph", "Liderança técnica e arquitetura de microsserviços..."))
                if role or org:
                    structured_exp.append({"role": role, "organization": org, "period": period, "location": loc, "description": desc})
        b_x1, b_x2 = st.columns([0.5, 0.5])
        with b_x1:
            if st.button("➕ " + txt.get("btn_add_exp", "Adicionar Experiência"), key="btn_add_exp"):
                st.session_state.man_exp_count += 1
                st.rerun()
        with b_x2:
            if st.session_state.man_exp_count > 1 and st.button("➖ " + txt.get("btn_rem_item", "Remover"), key="btn_rem_exp"):
                st.session_state.man_exp_count -= 1
                st.rerun()

        # 3. Projetos Relevantes Estruturados
        st.markdown(f"#### {txt.get('struct_proj_title', '🚀 Projetos Relevantes')}")
        if "man_proj_count" not in st.session_state:
            st.session_state.man_proj_count = 1
        structured_proj = []
        for i in range(st.session_state.man_proj_count):
            with st.expander(f"🚀 {txt.get('struct_proj_name_lbl', 'Projeto')} #{i + 1}", expanded=(i == 0)):
                p1, p2 = st.columns(2)
                with p1:
                    pname = st.text_input(txt.get("struct_proj_name_lbl", "Nome do Projeto"), key=f"proj_name_{i}", placeholder=txt.get("struct_proj_name_ph", "LaTeX Resume Enclave"))
                    ptech = st.text_input(txt.get("struct_proj_tech_lbl", "Tecnologias"), key=f"proj_tech_{i}", placeholder=txt.get("struct_proj_tech_ph", "Python, Flask, Docker"))
                with p2:
                    purl = st.text_input(txt.get("struct_proj_url_lbl", "Link / Repositório (URL)"), key=f"proj_url_{i}", placeholder=txt.get("struct_proj_url_ph", "https://github.com/usuario/projeto"))
                pdesc = st.text_area(txt.get("struct_proj_desc_lbl", "Descrição"), key=f"proj_desc_{i}", height=65, placeholder=txt.get("struct_proj_desc_ph", "Plataforma de síntese determinística..."))
                if pname:
                    structured_proj.append({"name": pname, "tech": ptech, "url": purl, "description": pdesc})
        b_p1, b_p2 = st.columns([0.5, 0.5])
        with b_p1:
            if st.button("➕ " + txt.get("btn_add_proj", "Adicionar Projeto"), key="btn_add_proj"):
                st.session_state.man_proj_count += 1
                st.rerun()
        with b_p2:
            if st.session_state.man_proj_count > 1 and st.button("➖ " + txt.get("btn_rem_item", "Remover"), key="btn_rem_proj"):
                st.session_state.man_proj_count -= 1
                st.rerun()

        # 4. Publicações & Artigos Estruturados
        st.markdown(f"#### {txt.get('struct_pubs_title', '📄 Publicações & Artigos')}")
        if "man_pubs_count" not in st.session_state:
            st.session_state.man_pubs_count = 1
        structured_pubs = []
        for i in range(st.session_state.man_pubs_count):
            with st.expander(f"📄 {txt.get('struct_pub_title_lbl', 'Publicação')} #{i + 1}", expanded=(i == 0)):
                pub_title = st.text_input(txt.get("struct_pub_title_lbl", "Título da Publicação"), key=f"pub_title_{i}", placeholder=txt.get("struct_pub_title_ph", "Neural Parsing of Technical Resumes"))
                pu1, pu2 = st.columns(2)
                with pu1:
                    pub_venue = st.text_input(txt.get("struct_pub_venue_lbl", "Periódico / Conferência"), key=f"pub_venue_{i}", placeholder=txt.get("struct_pub_venue_ph", "IEEE Transactions on AI"))
                    pub_year = st.text_input(txt.get("struct_pub_year_lbl", "Ano"), key=f"pub_year_{i}", placeholder=txt.get("struct_pub_year_ph", "2023"))
                with pu2:
                    pub_authors = st.text_input(txt.get("struct_pub_authors_lbl", "Autores"), key=f"pub_authors_{i}", placeholder=txt.get("struct_pub_authors_ph", "Silva, L.; Santos, M."))
                    pub_doi = st.text_input(txt.get("struct_pub_doi_lbl", "DOI ou Link"), key=f"pub_doi_{i}", placeholder=txt.get("struct_pub_doi_ph", "10.1109/CVPR.2023.1001"))
                if pub_title:
                    structured_pubs.append({"title": pub_title, "venue": pub_venue, "year": pub_year, "authors": pub_authors, "doi": pub_doi})
        b_u1, b_u2 = st.columns([0.5, 0.5])
        with b_u1:
            if st.button("➕ " + txt.get("btn_add_pub", "Adicionar Publicação"), key="btn_add_pub"):
                st.session_state.man_pubs_count += 1
                st.rerun()
        with b_u2:
            if st.session_state.man_pubs_count > 1 and st.button("➖ " + txt.get("btn_rem_item", "Remover"), key="btn_rem_pub"):
                st.session_state.man_pubs_count -= 1
                st.rerun()

        # 5. Prêmios & Certificações Estruturados
        st.markdown(f"#### {txt.get('struct_awards_title', '🏆 Prêmios & Certificações')}")
        if "man_awards_count" not in st.session_state:
            st.session_state.man_awards_count = 1
        structured_awards = []
        for i in range(st.session_state.man_awards_count):
            with st.expander(f"🏆 {txt.get('struct_award_title_lbl', 'Premiação')} #{i + 1}", expanded=(i == 0)):
                aw1, aw2 = st.columns(2)
                with aw1:
                    aw_title = st.text_input(txt.get("struct_award_title_lbl", "Título / Certificação"), key=f"award_title_{i}", placeholder=txt.get("struct_award_title_ph", "AWS Certified Solutions Architect"))
                    aw_year = st.text_input(txt.get("struct_award_year_lbl", "Ano"), key=f"award_year_{i}", placeholder=txt.get("struct_award_year_ph", "2023"))
                with aw2:
                    aw_det = st.text_input(txt.get("struct_award_det_lbl", "Instituição / Detalhes"), key=f"award_det_{i}", placeholder=txt.get("struct_award_det_ph", "Amazon Web Services"))
                if aw_title:
                    structured_awards.append({"title": aw_title, "year": aw_year, "details": aw_det})
        b_a1, b_a2 = st.columns([0.5, 0.5])
        with b_a1:
            if st.button("➕ " + txt.get("btn_add_award", "Adicionar Prêmio / Certificação"), key="btn_add_award"):
                st.session_state.man_awards_count += 1
                st.rerun()
        with b_a2:
            if st.session_state.man_awards_count > 1 and st.button("➖ " + txt.get("btn_rem_item", "Remover"), key="btn_rem_award"):
                st.session_state.man_awards_count -= 1
                st.rerun()

        # Modo Texto Rápido / Colar em Lote (Compatibilidade e Entrada em Bloco)
        with st.expander(txt.get("manual_raw_text_expander", "📝 Modo Texto Rápido / Colar em Lote (Opcional / Legado)")):
            st.caption(txt.get("manual_raw_caption", "Cole informações em formato texto com separador pipe '|' se preferir não usar os campos estruturados acima."))
            man_edu = st.text_area(
                txt["manual_edu_label"],
                height=100,
                placeholder=txt["manual_edu_ph"],
            )
            man_exp = st.text_area(
                txt["manual_exp_label"],
                height=100,
                placeholder=txt["manual_exp_ph"],
            )
            man_proj = st.text_area(
                txt["manual_projects_label"],
                height=100,
                placeholder=txt["manual_projects_ph"],
            )
            man_pubs = st.text_area(
                txt["manual_pubs_label"],
                height=70,
                placeholder=txt["manual_pubs_ph"],
            )
            man_awards = st.text_area(
                txt["manual_awards_label"],
                height=70,
                placeholder=txt["manual_awards_ph"],
            )

        st.caption(txt["optional_links_title"])
        ol1, ol2 = st.columns(2)
        with ol1:
            portfolio_url = st.text_input(txt["portfolio_label"], placeholder=txt["portfolio_ph"], key="man_port")
            github_input = st.text_input(txt["github_label"], placeholder=txt["github_ph"], key="man_gh")
            orcid_input = st.text_input(txt["orcid_label"], placeholder=txt["orcid_ph"], key="man_orcid")
        with ol2:
            linkedin_url = st.text_input(txt["linkedin_label"], placeholder=txt["linkedin_ph"], key="man_li")
            lattes_url = st.text_input(txt["lattes_label"], placeholder=txt["lattes_ph"], key="man_lattes")
            photo_upload = st.file_uploader(
                txt["photo_label"],
                type=["png", "jpg", "jpeg", "webp"],
                key="man_photo",
            )

        lattes_file = None
        linkedin_pdf = None
        extra_profile_text = ""

        manual_data_dict = {
            "summary": man_summary,
            "education": structured_edu if structured_edu else man_edu,
            "experience": structured_exp if structured_exp else man_exp,
            "skills": man_skills,
            "projects": structured_proj if structured_proj else man_proj,
            "languages": man_languages,
            "awards": structured_awards if structured_awards else man_awards,
            "publications": structured_pubs if structured_pubs else man_pubs,
        }

with col_right:
    st.subheader(txt["res_header"])
    if generate_btn:
        with st.spinner(txt["spinner_msg"]):
            tmp_build_dir = tempfile.mkdtemp(prefix="st_session_ephemeral_")
            build_path = Path(tmp_build_dir)
            try:
                res = build_resume_pipeline(
                    resume_type=resume_type,
                    linkedin_url=linkedin_url,
                    linkedin_pdf_bytes=linkedin_pdf.read() if linkedin_pdf else None,
                    github_input=github_input,
                    orcid_input=orcid_input,
                    lattes_url=lattes_url,
                    lattes_file_bytes=lattes_file.read() if lattes_file else None,
                    lattes_filename=lattes_file.name if lattes_file else "",
                    portfolio_url=portfolio_url,
                    photo_bytes=photo_upload.read() if photo_upload else None,
                    template_id=selected_template_id,
                    custom_latex_template=custom_latex_str,
                    primary_color=primary_color,
                    secondary_color=secondary_color,
                    user_name=user_name,
                    user_role=user_role,
                    user_email=user_email,
                    user_phone=user_phone,
                    user_location=user_location,
                    user_gender=user_gender,
                    extra_notes=extra_profile_text,
                    provider=selected_provider,
                    api_key=custom_api_key if custom_api_key.strip() else None,
                    model=selected_model,
                    use_cache=False,  # Zero-storage: nenhum documento persistido em disco
                    use_token_plugins={
                        "caveman": plugin_caveman,
                        "thinking": plugin_thinking,
                        "toon": plugin_toon,
                        "shortkey": plugin_shortkey,
                        "preamble": plugin_preamble,
                        "cache": plugin_cache,
                    },
                    output_stem=f"resume_{resume_lang}_{resume_type}_{selected_template_id}",
                    build_dir=build_path,
                    lang=resume_lang,
                    use_ai=(selected_provider != "none"),
                    ai_mode=ai_mode,
                    data_source_mode="manual" if is_manual_mode else "import",
                    manual_data=manual_data_dict if is_manual_mode else None,
                )

                # Armazena os documentos estritamente na memória volátil da sessão (RAM)
                st.session_state["session_has_run"] = True
                st.session_state["session_success"] = res.success
                st.session_state["session_latex_code"] = res.latex_code
                st.session_state["session_token_metrics"] = res.token_metrics
                st.session_state["session_structured_cv"] = res.structured_cv
                st.session_state["session_compiler_message"] = res.compiler_message
                st.session_state["session_tex_name"] = f"resume_{resume_lang}_{resume_type}_{selected_template_id}.tex"

                if res.success and res.pdf_path and res.pdf_path.exists():
                    st.session_state["session_pdf_bytes"] = res.pdf_path.read_bytes()
                    st.session_state["session_pdf_name"] = f"resume_{resume_lang}_{resume_type}_{selected_template_id}.pdf"
                else:
                    st.session_state["session_pdf_bytes"] = None
                    st.session_state["session_pdf_name"] = ""
            except Exception as exc:
                st.error(f"{txt['err_msg']}: {exc}")
            finally:
                # Destrói imediatamente e com segurança o diretório temporário do disco do servidor
                secure_wipe_and_remove_dir(build_path)

    if st.session_state.get("session_has_run"):
        tm = st.session_state.get("session_token_metrics", {})
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(txt["metric_total"], tm.get("total_tokens_actual", 0))
        m2.metric(txt["metric_reasoning"], tm.get("reasoning_tokens_actual", 0))
        m3.metric(txt["metric_saved"], f"~{tm.get('estimated_tokens_saved', 0)}")
        m4.metric(txt["metric_pct"], f"{tm.get('estimated_savings_pct', 0)}%")

        cache_str = txt["yes_zero_tokens"] if tm.get("cache_hit") else txt["no_lbl"]
        st.caption(
            f"**{txt['model_used_lbl']}:** `{tm.get('model_used')}` • "
            f"**{txt['cache_hit_lbl']}:** `{cache_str}`"
        )

        pdf_bytes = st.session_state.get("session_pdf_bytes")
        latex_code = st.session_state.get("session_latex_code", "")
        pdf_name = st.session_state.get("session_pdf_name", "curriculo.pdf")
        tex_name = st.session_state.get("session_tex_name", "curriculo.tex")
        comp_msg = st.session_state.get("session_compiler_message", "")

        if st.session_state.get("session_success") and pdf_bytes:
            st.success(f"{txt['pdf_ok_msg']}: `{pdf_name}`")
            d1, d2 = st.columns(2)
            with d1:
                st.download_button(
                    txt["dl_pdf_btn"],
                    data=pdf_bytes,
                    file_name=pdf_name,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                )
            with d2:
                st.download_button(
                    txt["dl_tex_btn"],
                    data=latex_code.encode("utf-8"),
                    file_name=tex_name,
                    mime="text/plain",
                    use_container_width=True,
                )

            b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
            pdf_iframe = (
                f'<iframe src="data:application/pdf;base64,{b64_pdf}#toolbar=1&navpanes=0&scrollbar=1&page=1&view=FitH" '
                f'width="100%" height="680" type="application/pdf" '
                f'style="border:1px solid #3F3F46;border-radius:8px;"></iframe>'
            )
            st.markdown(pdf_iframe, unsafe_allow_html=True)
        else:
            st.warning(f"{txt['pdf_warn_msg']}:\n\n`{comp_msg}`")
            st.download_button(
                txt["dl_tex_btn"],
                data=latex_code.encode("utf-8"),
                file_name=tex_name,
                mime="text/plain",
            )

        with st.expander(txt["view_tex_exp"]):
            st.code(latex_code, language="latex")

        with st.expander(txt["view_audit_exp"]):
            st.json({
                "token_metrics": tm,
                "structured_cv": st.session_state.get("session_structured_cv", {}),
            })
    else:
        st.info(txt["idle_info"])

st.markdown('</div>', unsafe_allow_html=True)


def main() -> None:
    """Ponto de entrada CLI para iniciar a aplicação Streamlit."""
    import sys
    from streamlit.web import cli as stcli

    sys.argv = ["streamlit", "run", str(Path(__file__).resolve()), *sys.argv[1:]]
    sys.exit(stcli.main())


if __name__ == "__main__":
    try:
        import streamlit.runtime as st_rt

        is_st_running = st_rt.exists()
    except Exception:
        is_st_running = False

    if not is_st_running:
        main()
