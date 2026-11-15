"""Testes de integridade de layout LaTeX e isolamento de entradas (prevenção de colisões)."""




from src.compiler import sanitize_latex_layout

from src.templates import _build_education_block

from src.token_plugins import CavemanPromptPlugin





def test_sanitize_latex_layout_fixes_colliding_education_entries():

    """Verifica se o sanitizador corrige exatamente o erro reportado (Mestrado + Bacharelado fundidos)."""

    raw_broken = r"""\section*{Formação Acadêmica}

\textbf{Mestrado em Ciência da Computação} \hfill \textbf{2026 - Atual} \\

DCC/UFMG $\cdot$ Belo Horizonte, MG

\textbf{Bacharelado em Sistemas de Informação} \hfill \textbf{2019 - 2025} \\

UFV $\cdot$ Rio Paranaíba, MG"""



    sanitized = sanitize_latex_layout(raw_broken)

    

    # Deve conter \par\vspace{3pt} ou quebra após a primeira instituição

    assert r"DCC/UFMG $\cdot$ Belo Horizonte, MG\par\vspace{3pt}" in sanitized

    

    # As entradas não devem estar no mesmo parágrafo sem quebra

    lines = sanitized.splitlines()

    bach_idx = -1

    dcc_idx = -1

    for idx, l in enumerate(lines):

        if "DCC/UFMG" in l:

            dcc_idx = idx

        if "Bacharelado" in l:

            bach_idx = idx



    assert dcc_idx != -1 and bach_idx != -1

    assert bach_idx > dcc_idx

    # Deve haver pelo menos uma linha em branco ou espaçamento entre eles

    assert any(not l.strip() for l in lines[dcc_idx+1:bach_idx])





def test_sanitize_latex_layout_fixes_trailing_double_backslash_entries():

    """Verifica se converte '\\' soltos no final de uma entrada em '\\par\\vspace{3pt}'."""

    raw_broken = r"""\section*{Formação Acadêmica}

\noindent\textbf{Mestrado em Ciência da Computação} \hfill \textbf{2026 - Atual} \\

DCC/UFMG $\cdot$ Belo Horizonte, MG \\

\noindent\textbf{Bacharelado em Sistemas de Informação} \hfill \textbf{2019 - 2025} \\

UFV $\cdot$ Rio Paranaíba, MG"""



    sanitized = sanitize_latex_layout(raw_broken)

    assert r"DCC/UFMG $\cdot$ Belo Horizonte, MG\par\vspace{3pt}" in sanitized





def test_build_education_block_has_explicit_blank_lines():

    """Garante que a renderização nativa de educação inclui linhas em branco entre entradas."""

    edus = [

        {

            "degree": "Mestrado em Ciência da Computação",

            "institution": "DCC/UFMG",

            "period": "2026 - Atual",

            "details": "Belo Horizonte, MG",

        },

        {

            "degree": "Bacharelado em Sistemas de Informação",

            "institution": "UFV",

            "period": "2019 - 2025",

            "details": "Rio Paranaíba, MG",

        },

    ]

    block = _build_education_block(edus, lang="pt-br")

    assert r"\section*{Formação Acadêmica}" in block

    assert (r"\par\vspace{2pt}" in block or r"\par\vspace{4pt}" in block)

    assert "\n\n" in block





def test_llm_prompts_contain_entry_isolation_rules():

    """Garante que as instruções de isolamento de entradas estão presentes nos prompts do modelo."""

    latex_sys = CavemanPromptPlugin.build_system_prompt("profissional", output_mode="latex", lang="pt-br")

    assert "CRITICAL ENTRY ISOLATION RULE" in latex_sys

    assert "NEVER merge an institution/location line" in latex_sys

    assert r"\par\vspace{3pt}" in latex_sys





def test_index_html_autofill_and_extension_error_suppression():

    """Verifica se index.html suprime ruídos de extensões (Passkey, Autofill, FN_NOT_FOUND) no topo do <head>."""

    from pathlib import Path

    html_content = Path("index.html").read_text(encoding="utf-8")

    assert "FN_NOT_FOUND" in html_content

    assert "closePasskeyConditionalList" in html_content
    assert "callApi" in html_content
    assert "isExtensionNoise" in html_content

    assert "data-lpignore" in html_content

    assert "data-1p-ignore" in html_content

    assert "data-bwignore" in html_content

    assert "masked-key" in html_content
    assert "-webkit-text-security" in html_content



    # Valida que o script de supressão está localizado no <head> antes do corpo da página

    head_part = html_content.split("</head>")[0]

    assert "isExtensionNoise" in head_part

    assert "unhandledrejection" in head_part

    assert "stopImmediatePropagation" in head_part

    assert "console.error" in head_part



def test_review_and_enhance_latex_mandates_dual_latex_code_and_content_review():

    """Valida se o prompt de review_and_enhance_latex instrui expressamente a revisão do código LaTeX e do texto."""

    from unittest.mock import patch

    from src.llm_client import LLMResumeGenerator



    generator = LLMResumeGenerator(provider="default")

    captured_messages = []



    def fake_call(messages, max_tokens):

        captured_messages.extend(messages)

        return (

            "\\begin{document}\nReviewed content\\end{document}",

            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},

            "nvidia/test-model",

            False,

        )



    with patch.object(generator, "_call_llm_chat", side_effect=fake_call):

        base_latex = "\\documentclass{article}\n\\begin{document}\nBase\n\\end{document}"

        generator.review_and_enhance_latex(

            base_latex=base_latex,

            resume_type="profissional",

            instructions="Destacar Python e Docker",

            lang="pt-br",

        )



    sys_msg = captured_messages[0]["content"]

    user_msg = captured_messages[1]["content"]



    # Valida presença das regras de auditoria do código LaTeX

    assert "MODE:CAVEMAN_LATEX_CODE_AND_CONTENT_REVIEW" in sys_msg

    assert "PART 1: LATEX CODE & TYPESETTING AUDIT" in sys_msg

    assert "SYNTAX & ENVIRONMENTS" in sys_msg

    assert "SPECIAL CHARACTER ESCAPING" in sys_msg

    assert "ENTRY ISOLATION (ZERO COLLISION)" in sys_msg

    assert "MACRO PRESERVATION" in sys_msg



    # Valida presença das regras de aprimoramento textual

    assert "PART 2: TEXT & CONTENT ENHANCEMENT" in sys_msg

    assert "ACTION VERBS & METRICS" in sys_msg

    assert "EXECUTIVE SUMMARY" in sys_msg

    assert "STRICT TRUTHFULNESS" in sys_msg



    # Valida mandado de revisão dupla no prompt do usuário

    assert "DUAL REVIEW MANDATE" in user_msg

    assert "Destacar Python e Docker" in user_msg





def test_repair_latex_error_mandates_code_and_syntax_audit():

    """Valida se o método repair_latex_error instrui auditoria de sintaxe, ambientes e layout."""

    from unittest.mock import patch

    from src.llm_client import LLMResumeGenerator



    generator = LLMResumeGenerator(provider="default")

    captured_messages = []



    def fake_call(messages, max_tokens):

        captured_messages.extend(messages)

        return (

            "\\begin{document}\nFixed\n\\end{document}",

            {"total_tokens": 100},

            "nvidia/test-model",

            False,

        )



    with patch.object(generator, "_call_llm_chat", side_effect=fake_call):

        generator.repair_latex_error(

            broken_latex="\\begin{document}\nBroken C# and R&D\n\\end{document}",

            error_excerpt=r"! LaTeX Error: Something's wrong--perhaps a missing \item.",

        )



    sys_msg = captured_messages[0]["content"]

    user_msg = captured_messages[1]["content"]



    assert "MODE:CAVEMAN_LATEX_REPAIR" in sys_msg

    assert "SYNTAX AUDIT" in sys_msg

    assert "ESCAPING AUDIT" in sys_msg

    assert "ENTRY ISOLATION" in sys_msg

    assert "COMPILER_ERROR:" in user_msg





def test_pipeline_triggers_universal_latex_repair_on_compiler_error(tmp_path):

    """Garante que qualquer erro de compilação pdflatex aciona o auto-reparo cirúrgico por IA."""

    from unittest.mock import patch, MagicMock

    from src.pipeline import build_resume_pipeline



    mock_generator = MagicMock()

    mock_generator.repair_latex_error.return_value = (

        r"\documentclass{article}\begin{document}Repaired\end{document}"

    )

    mock_generator.generate_latex_resume.return_value = (

        r"\documentclass{article}\begin{document}Broken Code\end{document}",

        {"name": "Test"},

        MagicMock(to_dict=lambda: {"total_tokens_actual": 100}),

    )



    compile_calls = []



    def fake_compile(latex_code, output_stem, build_dir):

        compile_calls.append(latex_code)

        # Primeira compilação falha, segunda (após reparo) tem sucesso

        if len(compile_calls) == 1:

            return False, None, tmp_path / f"{output_stem}.tex", "Syntax error on line 12"

        return True, tmp_path / f"{output_stem}.pdf", tmp_path / f"{output_stem}.tex", "Success"



    with patch("src.pipeline.LLMResumeGenerator", return_value=mock_generator),          patch("src.pipeline.compile_latex_to_pdf", side_effect=fake_compile):

        

        result = build_resume_pipeline(

            resume_type="profissional",

            user_name="Carlos Dev",

            provider="nvidia",

            template_id="modern_pro",

            output_stem="test_universal_repair",

            build_dir=tmp_path,

        )



        assert mock_generator.repair_latex_error.called

        assert len(compile_calls) == 2

        assert result.success is True



