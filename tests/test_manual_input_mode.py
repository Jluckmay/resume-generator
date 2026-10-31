"""Testes automatizados para a seleção entre importação de informações e inserção manual em todas as interfaces e pipelines."""

from __future__ import annotations

from pathlib import Path


from src.direct_builder import (
    build_structured_cv_deterministically,
    parse_manual_resume_inputs,
)
from src.manual_editor import manual_editor_state_from_cv
from src.pipeline import build_resume_pipeline


def test_generated_cv_populates_editable_manual_fields():
    """Garante que os dados estruturados gerados apareçam nos campos manuais."""
    cv = {
        "name": "Ana Clara Santos",
        "title": "Engenheira de Machine Learning",
        "email": "ana@example.com",
        "phone": "+55 11 99999-9999",
        "location": "Campinas, SP",
        "summary": "Especialista em modelos de linguagem.",
        "education": [
            {"degree": "Mestrado", "institution": "UNICAMP", "period": "2022 - 2024", "details": "IA"},
            {"degree": "Graduação", "institution": "USP", "period": "2018 - 2022", "details": ""},
        ],
        "experience": [
            {
                "role": "Engenheira",
                "organization": "Tech Corp",
                "period": "2022 - Atual",
                "location": "Remoto",
                "bullets": ["Desenvolvimento de modelos.", "Liderança técnica."],
            }
        ],
        "skills": [{"category": "IA", "items": "Python, PyTorch"}],
        "projects": [{"name": "Resume AI", "tech": "Python", "url": "https://example.com", "description": "Automação."}],
        "languages": ["Português (Nativo)", "Inglês (Fluente)"],
        "publications": [{"title": "Artigo", "venue": "IEEE", "year": "2024", "authors": "Santos", "doi": "10.1/abc"}],
        "awards": ["Prêmio de Inovação (2023)"],
    }

    values = manual_editor_state_from_cv(
        cv,
        {"links": {"github": "https://github.com/anaclara", "portfolio": "https://anaclara.dev"}},
    )

    assert values["manual_user_name"] == "Ana Clara Santos"
    assert values["manual_user_role"] == "Engenheira de Machine Learning"
    assert values["manual_user_email"] == "ana@example.com"
    assert values["man_summary"] == "Especialista em modelos de linguagem."
    assert values["man_edu_count"] == 2
    assert values["edu_inst_1"] == "USP"
    assert values["man_exp_count"] == 1
    assert values["exp_desc_0"] == "Desenvolvimento de modelos.\nLiderança técnica."
    assert values["man_skills"] == "IA: Python, PyTorch"
    assert values["man_languages"] == "Português (Nativo), Inglês (Fluente)"
    assert values["proj_url_0"] == "https://example.com"
    assert values["pub_doi_0"] == "10.1/abc"
    assert values["award_title_0"] == "Prêmio de Inovação (2023)"
    assert values["man_gh"] == "https://github.com/anaclara"


def test_parse_manual_resume_inputs_with_structured_dicts():
    """Valida a normalização de dados manuais quando fornecidos como dicionários e listas."""
    raw_manual = {
        "name": "Ana Clara Santos",
        "title": "Engenheira de Machine Learning Sênior",
        "email": "ana.clara@tech.ai",
        "phone": "+55 (11) 98765-4321",
        "location": "Campinas, SP, Brasil",
        "summary": "Especialista em LLMs, visão computacional e deploy de modelos escaláveis em Kubernetes.",
        "education": [
            {
                "degree": "Doutorado em Ciência da Computação",
                "institution": "UNICAMP",
                "period": "2020 - 2024",
                "details": "Tese: Otimização de Inferência em Redes Neurais Profundas",
            },
            {
                "degree": "Bacharelado em Engenharia de Computação",
                "institution": "USP",
                "period": "2015 - 2019",
                "details": "",
            },
        ],
        "experience": [
            {
                "role": "Lead ML Engineer",
                "organization": "AI Solutions Corp",
                "period": "2022 - Atual",
                "location": "São Paulo, SP",
                "description": "Liderança técnica na arquitetura de microsserviços de inferência com Triton e PyTorch.",
            }
        ],
        "skills": [
            {"category": "Machine Learning", "items": "PyTorch, TensorFlow, Triton, vLLM"},
            {"category": "Cloud & DevOps", "items": "AWS, GCP, Docker, Kubernetes, Terraform"},
        ],
        "projects": [
            {
                "name": "Neural ATS Parser",
                "tech": "Python, FastAPI, Transformers",
                "url": "https://github.com/anaclara/neural-ats",
                "description": "Parser neural com 99% de acurácia em extração de entidades técnicas.",
            }
        ],
        "languages": ["Português (Nativo)", "Inglês (Fluente)", "Francês (Básico)"],
        "awards": [
            {"title": "Melhor Artigo em IA Aplicada", "year": "2023", "details": "Conferência Brasileira de IA"}
        ],
        "publications": [
            {
                "title": "Efficient Inference in Transformers",
                "venue": "IEEE Access",
                "year": "2023",
                "authors": "Santos, A. C.; Pereira, F.",
                "doi": "10.1109/ACCESS.2023.1000",
            }
        ],
    }

    parsed = parse_manual_resume_inputs(raw_manual)
    assert parsed["name"] == "Ana Clara Santos"
    assert parsed["title"] == "Engenheira de Machine Learning Sênior"
    assert len(parsed["education"]) == 2
    assert parsed["education"][0]["degree"] == "Doutorado em Ciência da Computação"
    assert len(parsed["experience"]) == 1
    assert parsed["experience"][0]["organization"] == "AI Solutions Corp"
    assert len(parsed["skills"]) == 2
    assert len(parsed["projects"]) == 1
    assert len(parsed["languages"]) == 3
    assert len(parsed["awards"]) == 1
    assert len(parsed["publications"]) == 1


def test_parse_manual_resume_inputs_with_raw_text_areas():
    """Valida a capacidade de processar entradas de texto livre com pipes e quebras de linha vindas dos textareas."""
    raw_manual_text = {
        "name": "Carlos Eduardo",
        "title": "Arquiteto Cloud & DevOps",
        "summary": "Profissional certificado AWS com vasta experiência em infraestrutura resiliente.",
        "education": "Mestrado em Engenharia | USP | 2020 - 2022 | Computação em Nuvem\nGraduação em Redes | FATEC | 2016 - 2019",
        "experience": "Arquiteto Cloud Sênior | CloudOps Inc | 2021 - Atual | Remoto | Modernização de pipelines CI/CD.\nEngenheiro DevOps | InfraTech | 2019 - 2021 | Curitiba | Automação Ansible e Terraform.",
        "skills": "Linguagens: Go, Python, Bash\nCloud & Containers: AWS, Docker, Kubernetes, Helm\nBancos de Dados: PostgreSQL, Redis",
        "projects": "DevOps Pipeline Toolkit | Go, Docker | https://github.com/carlos/toolkit | Ferramentas CLI para automação de deploy.",
        "languages": "Português (Nativo), Inglês (Avançado), Espanhol (Intermediário)",
        "awards": "AWS Solutions Architect Professional | 2022 | Amazon Web Services\nCertified Kubernetes Administrator (CKA) | 2023 | Linux Foundation",
        "publications": "Resilient Microservices in Hybrid Clouds | Cloud Summit | 2022 | Eduardo, C. | 10.1000/cloud.2022",
    }

    parsed = parse_manual_resume_inputs(raw_manual_text)
    assert parsed["name"] == "Carlos Eduardo"
    assert len(parsed["education"]) == 2
    assert parsed["education"][0]["degree"] == "Mestrado em Engenharia"
    assert parsed["education"][0]["institution"] == "USP"
    assert len(parsed["experience"]) == 2
    assert parsed["experience"][0]["role"] == "Arquiteto Cloud Sênior"
    assert len(parsed["skills"]) == 3
    assert parsed["skills"][0]["category"] == "Linguagens"
    assert len(parsed["projects"]) == 1
    assert len(parsed["languages"]) == 3
    assert len(parsed["awards"]) == 2
    assert len(parsed["publications"]) == 1


def test_build_structured_cv_with_manual_data_overrides():
    """Valida que dados manuais fornecidos têm precedência absoluta na montagem do currículo determinístico."""
    raw_profile = {
        "user_meta": {"name": "Nome Meta Antigo", "role": "Cargo Meta Antigo"},
        "manual_data": {
            "name": "Juliana Martins",
            "title": "Diretora de Engenharia",
            "summary": "Líder técnica executiva focada em transformação digital e produtos de alta escala.",
            "education": [
                {"degree": "MBA em Gestão Estratégica", "institution": "FGV", "period": "2021", "details": ""}
            ],
            "experience": [
                {
                    "role": "VP de Engenharia",
                    "organization": "Fintech Alpha",
                    "period": "2020 - Atual",
                    "location": "São Paulo",
                    "description": "Liderança de 120 engenheiros e crescimento de 300% em transações.",
                }
            ],
            "skills": [{"category": "Liderança", "items": "Gestão de Pessoas, OKRs, Orçamento, Estratégia"}],
            "languages": ["Português (Nativo)", "Inglês (Fluente)"],
        },
    }

    cv = build_structured_cv_deterministically(raw_profile, resume_type="profissional", lang="pt-br")
    assert cv["name"] == "Juliana Martins"
    assert cv["title"] == "Diretora de Engenharia"
    assert "transformação digital" in cv["summary"]
    assert len(cv["education"]) == 1
    assert cv["education"][0]["institution"] == "FGV"
    assert cv["experience"][0]["organization"] == "Fintech Alpha"
    assert cv["skills"][0]["category"] == "Liderança"


def test_pipeline_manual_data_zero_token_generation(tmp_path):
    """Executa o pipeline completo no modo manual e sem IA (0 tokens), gerando LaTeX e PDF válidos."""
    manual_info = {
        "name": "Mariana Ribeiro",
        "title": "Arquiteta de Soluções",
        "email": "mariana.ribeiro@exemplo.com",
        "phone": "+55 11 91234-5678",
        "location": "Belo Horizonte, MG, Brasil",
        "summary": "Arquiteta de software com vasta experiência em sistemas distribuídos e microsserviços.",
        "education": "Engenharia de Software | PUC Minas | 2017 - 2021 | Ênfase em Sistemas Críticos",
        "experience": "Arquiteta Sênior | Tech Corp | 2022 - Atual | BH | Arquitetura de mensageria Kafka.",
        "skills": "Backend: Java, Spring Boot, Go\nMensageria: Apache Kafka, RabbitMQ\nCloud: AWS, Kubernetes",
        "projects": "Event Stream Platform | Go, Kafka | https://github.com/mariana/events | Broker resiliente",
        "languages": "Português (Nativo), Inglês (Fluente)",
    }

    res = build_resume_pipeline(
        resume_type="profissional",
        template_id="ai_ats_max",
        data_source_mode="manual",
        manual_data=manual_info,
        provider="none",
        use_ai=False,
        build_dir=tmp_path,
        lang="pt-br",
    )

    assert res.success is True
    assert res.structured_cv["name"] == "Mariana Ribeiro"
    assert res.structured_cv["title"] == "Arquiteta de Soluções"
    assert "Tech Corp" in res.latex_code
    assert "PUC Minas" in res.latex_code
    assert res.token_metrics["total_tokens_actual"] == 0


def test_server_api_generate_with_manual_data(client):
    """Testa o endpoint /api/generate recebendo requisição com modo manual."""
    manual_data = {
        "name": "Roberto Albuquerque",
        "role": "Pesquisador em Computação Quântica",
        "email": "roberto@quantum.org",
        "location": "Rio de Janeiro, RJ, Brasil",
        "summary": "Pesquisador dedicado ao desenvolvimento de algoritmos para computação quântica ruidosa (NISQ).",
        "education": "Doutorado em Física | UFRJ | 2019 - 2023 | Algoritmos Quânticos VQE",
        "experience": "Pesquisador Pós-Doc | Laboratório Nacional | 2023 - Atual | RJ | Simulação quântica com Qiskit.",
        "skills": "Quântica: Qiskit, Cirq, PennyLane\nProgramação: Python, C++, Julia",
        "languages": "Português (Nativo), Inglês (Avançado)",
    }

    payload = {
        "provider": "none",
        "resume_type": "academico",
        "template_id": "academic_classic",
        "lang": "pt-br",
        "data_source_mode": "manual",
        "manual_data": manual_data,
        "name": manual_data["name"],
        "role": manual_data["role"],
        "email": manual_data["email"],
        "location": manual_data["location"],
    }

    resp = client.post("/api/generate", json=payload, headers={"Origin": "https://jluckmay.github.io"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["structured_cv"]["name"] == "Roberto Albuquerque"
    assert "Qiskit" in data["latex_code"]


def test_ui_elements_for_manual_and_import_mode():
    """Valida se as interfaces index.html e app.py possuem os seletores e campos de importação vs manual."""
    html = Path("index.html").read_text(encoding="utf-8")
    assert 'id="btn-data-mode-toggle"' in html
    assert 'onclick="toggleDataMode()"' in html
    assert 'id="btn-mode-import"' not in html
    assert 'id="btn-mode-manual"' not in html
    assert 'id="container-data-import"' in html
    assert 'id="container-data-manual"' in html
    assert 'dataMode: "manual"' in html
    assert 'style="display:none;">' in html[html.index('id="container-data-import"'):html.index('id="container-data-import"') + 100]
    assert 'function toggleDataMode()' in html
    assert 'Importação ou Manual' not in html
    assert 'id="inp-man-summary"' in html
    assert 'id="inp-man-education"' in html
    assert 'id="inp-man-experience"' in html
    assert 'id="inp-man-skills"' in html
    assert 'id="inp-man-projects"' in html
    assert 'id="inp-man-languages"' in html
    assert 'id="inp-man-awards"' in html
    assert 'id="inp-man-publications"' in html
    assert 'function setDataMode(mode)' in html
    assert 'data_source_mode: state.dataMode' in html
    assert 'function populateManualEditor(cv)' in html
    assert 'populateManualEditor(data.structured_cv)' in html

    app_py = Path("app.py").read_text(encoding="utf-8")
    assert 'st.session_state["data_mode"] = "manual"' in app_py
    assert 'st.button(toggle_mode_label' in app_py
    assert 'st.session_state["data_mode"] = "import" if is_manual_mode else "manual"' in app_py
    assert 'st.rerun()' in app_py
    assert 'txt["mode_import_label"]' in app_py
    assert 'txt["mode_manual_label"]' in app_py
    assert 'is_manual_mode = st.session_state["data_mode"] == "manual"' in app_py
    assert 'man_summary = st.text_area' in app_py
    assert 'man_edu = st.text_area' in app_py
    assert 'man_exp = st.text_area' in app_py
    assert 'man_skills = st.text_area' in app_py
    assert 'man_proj = st.text_area' in app_py
    assert 'data_source_mode="manual" if is_manual_mode else "import"' in app_py
    assert 'st.session_state["pending_manual_editor"]' in app_py
    assert 'manual_editor_state_from_cv(' in app_py
    assert 'st.session_state["data_mode"] = "manual"' in app_py


def test_server_rate_limiter_allows_multiple_generations_and_exempts_local_dev():
    """Garante que requisições locais não sofram rate limit e que a cota seja de no mínimo 40 requisições."""
    from server import _MAX_REQUESTS_PER_WINDOW, _is_rate_limited
    assert _MAX_REQUESTS_PER_WINDOW >= 40
    # Loopback e local dev nunca devem ser bloqueados
    assert _is_rate_limited("127.0.0.1") is False
    assert _is_rate_limited("localhost") is False
    assert _is_rate_limited("::1") is False


def test_multiple_generation_memory_cleanup_and_dom_isolation():
    """Valida garantias contra vazamento de memória e interferência de extensões em múltiplas gerações."""
    html = Path("index.html").read_text(encoding="utf-8")
    # Blob URL com revogação explícita
    assert "URL.revokeObjectURL(state.activePdfBlobUrl)" in html
    assert "URL.revokeObjectURL(state.activeTexBlobUrl)" in html
    # Substituição limpa do iframe no DOM para isolamento de frames de extensões
    assert "replaceChild(newIframe, oldIframe)" in html
    # Proteção contra requisições concorrentes ou duplo-clique
    assert "state.isGenerating" in html
    # Badge informativo de status do motor de IA / Fallback
    assert 'id="m-model-badge"' in html
    assert 'id="m-model-name"' in html
    # Atributos de supressão de observadores de formulário de extensões nos campos manuais
    assert 'id="inp-man-summary" class="form-control" rows="3" placeholder="Ex: Especialista em tecnologia com sólida trajetória..." oninput="renderLivePreview()" autocomplete="off" data-lpignore="true"' in html
    assert 'id="inp-man-education" class="form-control" rows="3" placeholder="Bacharelado em Ciência da Computação | USP | 2018 - 2022 | Foco em IA&#10;Mestrado em Engenharia | UNICAMP | 2022 - 2024" oninput="renderLivePreview()" autocomplete="off" data-lpignore="true"' in html

def test_structured_manual_inputs_ui_components():
    """Valida a presença de componentes estruturados de formulário com botões de adicionar e campos individuais."""
    html = Path("index.html").read_text(encoding="utf-8")
    
    # 1. Containers de listas dinâmicas e botões de adicionar
    assert 'id="list-struct-education"' in html
    assert 'id="btn-add-education"' in html
    assert 'id="list-struct-experience"' in html
    assert 'id="btn-add-experience"' in html
    assert 'id="list-struct-projects"' in html
    assert 'id="btn-add-project"' in html
    assert 'id="list-struct-publications"' in html
    assert 'id="btn-add-publication"' in html
    assert 'id="list-struct-awards"' in html
    assert 'id="btn-add-award"' in html

    # 2. Funções JavaScript para gerenciamento dinâmico de cards estruturados
    assert "function addStructuredEducation" in html
    assert "function removeStructuredEducation" in html
    assert "function addStructuredExperience" in html
    assert "function removeStructuredExperience" in html
    assert "function addStructuredProject" in html
    assert "function removeStructuredProject" in html
    assert "function addStructuredPublication" in html
    assert "function removeStructuredPublication" in html
    assert "function addStructuredAward" in html
    assert "function removeStructuredAward" in html
    assert "function collectStructuredEducation" in html
    assert "function collectStructuredExperience" in html
    assert "function collectStructuredProjects" in html
    assert "function collectStructuredPublications" in html
    assert "function collectStructuredAwards" in html
    assert "function initStructuredManualInputs" in html

    # 3. Streamlit app.py: contadores de session state e botões de adicionar/remover
    app_py = Path("app.py").read_text(encoding="utf-8")
    assert "man_edu_count" in app_py
    assert "btn_add_edu" in app_py
    assert "man_exp_count" in app_py
    assert "btn_add_exp" in app_py
    assert "man_proj_count" in app_py
    assert "btn_add_proj" in app_py
    assert "man_pubs_count" in app_py
    assert "btn_add_pub" in app_py
    assert "man_awards_count" in app_py
    assert "btn_add_award" in app_py


def test_sanitize_awards_with_structured_dictionaries():
    """Garante que a higienização de premiações converte dicionários estruturados em strings limpas formatadas."""
    from src.templates import sanitize_awards
    
    raw_awards = [
        {"title": "Melhor Artigo em IA Aplicada", "year": "2023", "details": "Conferência Brasileira de IA"},
        {"title": "AWS Certified Solutions Architect", "year": "2024", "details": "Amazon Web Services"},
        {"title": "1º Lugar Hackathon", "details": "Tech Challenge"},
        "Prêmio Mérito Acadêmico - USP (2022)",
        None,
        "",
        {"title": "N/A"},
    ]
    
    clean = sanitize_awards(raw_awards)
    assert len(clean) == 4
    # Ordenados da mais recente à mais antiga
    assert clean[0] == "AWS Certified Solutions Architect (2024) - Amazon Web Services"
    assert clean[1] == "Melhor Artigo em IA Aplicada (2023) - Conferência Brasileira de IA"
    assert clean[2] == "Prêmio Mérito Acadêmico - USP (2022)"
    assert clean[3] == "1º Lugar Hackathon - Tech Challenge"
