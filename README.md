# 📄 Automatic LaTeX Resume Generator / Gerador Automático de Currículos LaTeX

> 🌐 **Language / Idioma:** [🇺🇸 English (en-US)](#-english-en-us) | [🇧🇷 Português (pt-BR)](#-português-pt-br)

---

## 🇺🇸 English (`en-US`)

Automatic generator for **Academic** and **Professional** resumes in **LaTeX + PDF** (supporting both `en-US` and `pt-BR`), powered by **Multiple AI Providers** (**NVIDIA NIM**, **Google Gemini**, **Anthropic Claude**, **OpenAI**, **DeepSeek**) with a modular **Token-Saving Plugin Architecture**, **In-Browser Ephemeral Encryption (AES-256-GCM)**, and a **Task-Bound Cryptographic Zero-Storage Enclave Vault**.

### 📋 Project Requirements

To run the generator and compile resumes into PDF, your environment must meet the following mandatory requirements:

1. **LaTeX Compiler (`pdflatex`) — Mandatory**:
   - **TeX Live** (2023+ recommended) or **MiKTeX** distribution installed and available on your system `PATH`.
   - Standard LaTeX packages used by the built-in templates (included in TeX Live / MiKTeX): `babel` (`brazil` and `english`), `lmodern`, `roboto`, `sourcesanspro`, `raleway`, `fontawesome5`, `tikz`, `multicol`, `tcolorbox`, `adjustbox`, `array`, `fancyhdr`, `geometry`, `xcolor`, `graphicx`, `enumitem`, `titlesec`, and `hyperref`.
   - **Quick LaTeX compiler installation**:
     - **Windows (TeX Live or MiKTeX via Winget)**:
       ```powershell
       winget install -e --id MiKTeX.MiKTeX
       # or full TeX Live: https://www.tug.org/texlive/
       ```
     - **Linux (Ubuntu / Debian)**:
       ```bash
       sudo apt update && sudo apt install -y texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-lang-portuguese texlive-fonts-recommended texlive-fonts-extra
       ```
     - **macOS (Homebrew)**:
       ```bash
       brew install --cask mactex-no-gui
       ```
   - **Verify compiler installation**:
     ```powershell
     pdflatex --version
     # or via the project CLI:
     python cli.py --lang en-us --check-deps
     ```

2. **Python (`>= 3.10`) & Python Dependencies (`requirements.txt`)**:
   - `requests >= 2.31.0`
   - `beautifulsoup4 >= 4.12.0`
   - `Pillow >= 10.0.0`
   - `streamlit >= 1.32.0`
   - `pypdf >= 4.0.0`
   - `flask >= 3.0.0`
   - `cryptography >= 41.0.0`
   - **Installation**:
     ```powershell
     pip install -r requirements.txt
     ```

### Key Features

1. **Two Full-Featured Web Interfaces (Standalone HTML5 `index.html` + `server.py` and Streamlit `app.py`) with Auto Theme & Language Detection**:
   - **100% Fluid Responsive & Mobile-First Layouts**: optimized across smartphones, tablets, and high-DPI desktop viewports with adaptive column wrapping, touch-friendly interactive targets (min 44px), and fluid PDF viewport scaling (`clamp()`).
   - **Official Project Brand & Browser Tab Favicon**: high-definition vector logo provided in `SVG`, `PNG` (512x512, 192x192, 32x32, 16x16), and multi-frame `ICO` formats, appearing in the browser tab (`favicon`), sidebar, and page headers.
   - **Full Feature Parity**: both the standalone HTML5 web interface (`index.html` served via `python server.py`) and the Streamlit interface (`streamlit run app.py`) share a clean, pleasant, and intuitive visual design with identical capabilities.
   - **Automatic Detection**: automatically detects your **default language** (`navigator.language` / `Accept-Language` or OS locale) and **default color scheme** (`prefers-color-scheme` / OS registry theme) on startup and adopts them seamlessly.
   - **Instant Switching**: includes a one-click switcher between **☀️ Light Mode** and **🌙 Dark Mode**, plus instant toggling between **English (`en-US`)** and **Portuguese (`pt-BR`)**.
2. **Real-Time Visual LaTeX Template Preview & Color Customization**:
   - **Interactive Template Preview**: renders a live visual preview of your chosen LaTeX template (`modern_pro`, `academic_classic`, `tech_sidebar`, `minimal_ats`, `overleaf_russell_ti`, `overleaf_awesome_cv`, `overleaf_single_page_keywords`, `nico_krieger`, `google_standard`, `ai_ats_max`) that updates immediately as you tweak colors or switch languages prior to compiling the PDF.
   - **Curated Palettes & `HEX` Color Pickers**: choose from 6 executive/academic presets (*Minimalist Charcoal (ATS Default)*, *Ocean Blue*, *Academic Navy*, *Emerald Tech*, *Royal Indigo*, *Classic Burgundy*) or pick custom **Primary** and **Secondary** colors injected directly into LaTeX (`\definecolor`).
3. **Dual Data Input Modes: Automated Multi-Source Profile Import & Structured Manual Entry**:
   - **Flexible UI Mode Switcher**: easily toggle between **Import Information** and **Enter Manually** in both the Web interface and Streamlit app.
   - **Import Mode (Online Profiles & Files)**:
     - **Personal Portfolio (`URL`)**: scrapes title, meta description, section headings (`h1`/`h2`/`h3`), bio, and project highlights from your portfolio website and injects a clean clickable link in the resume header.
     - **GitHub**: fetches bio, location, top programming languages, and top repositories via the public GitHub REST API (supports full URL or username), featuring automated README analysis to extract contextual summaries and detect all tools and languages used.
     - **ORCID**: fetches biography, education history (`educations`), employment affiliations (`employments`), and published works (`works` with DOIs) via the ORCID Public API v3.0 (supports numeric ID or URL).
     - **Lattes**: native parser for official CNPq `XML`/`ZIP` exports (`CURRICULO-VITAE`), plus PDF, HTML, URL or 16-digit ID / supplementary text.
     - **LinkedIn**: supports profile URLs or usernames, official LinkedIn exported PDFs (*Save to PDF*), and supplementary text.
     - **Profile Photo**: automatic image normalization (`PNG`/`JPG`/`WebP`) via Pillow for seamless LaTeX inclusion (`\includegraphics`).
   - **Manual Entry Mode (Direct Structured Inputs & Dynamic Cards)**:
     - Allows candidates without external profiles or who prefer full editorial control to type data directly into structured form cards.
     - **Dynamic Cards with Add/Remove Buttons**: dedicated cards with `+ Add` and `Remove` buttons containing individual input fields for:
       - **Education**: Degree/Major, Institution, Period, and Details/Honors/Thesis.
       - **Work Experience**: Role/Title, Company/Organization, Period, Location, and Description/Achievements.
       - **Relevant Projects**: Project Name, Technologies Used, Link/Repository (URL), and Description.
       - **Publications & Papers**: Publication Title, Journal/Conference, Year, Authors, and DOI/URL.
       - **Awards & Certifications**: Title/Certification, Year, and Issuing Institution/Details.
     - **Quick Mode / Batch Paste (Collapsible)**: preserves optional support for line-by-line pipe-delimited syntax (`|`) or structured JSON to paste multiple items at once.
     - Preserves optional header profile links (GitHub, LinkedIn, Portfolio, ORCID, Lattes, and photo).
4. **10 Built-in LaTeX Templates (including Google Standard, AI/ATS-Optimized, Modelo Russell, Awesome CV, Single Page + Keywords, and Modelo Nico Krieger) + Custom `.tex` Template Support**:
   - `ai_ats_max`: **AI & ATS Max-Readability (LLM & Neural ATS Evaluators)** — Engineered specifically for automated screening by LLMs (Gemini, Claude, GPT) and neural ATS parsers (Workday, Greenhouse, Lever). Strict 100% linear single-column text stream, explicit semantic metadata tags, dedicated Core Competencies & Keywords matrix, and native Unicode mapping (`glyphtounicode`). Full multi-page capable for maximum keyword coverage.
   - `google_standard`: **Google Standard (Big Tech / Software Engineer)** — Built upon Big Tech recruitment guidelines (Google SWE / Gayle Laakmann McDowell). Guaranteed dense single-page layout (0.5-inch / 1.0 cm margins), Google Blue (`#0B57D0`) accents, XYZ accomplishment format ("Accomplished [X] as measured by [Y], by doing [Z]"), clean horizontal rules, and classic hierarchy (Company on top, italic role underneath).
   - `overleaf_russell_ti`: **Modelo Russell (IT Resume)** — Based on the Russell CV template ([view on Overleaf](https://www.overleaf.com/read/rgfqqnnynrmv#d5b171)). Features left header photo, FontAwesome 5 icons, 3-letter colored section titles, skill category tables, and 6-dot language proficiency bars (CEFR A1 to C2).
   - `overleaf_awesome_cv`: **Awesome CV (Jason Richards)** — Based on the Jason Richards Résumé ([view on Overleaf](https://www.overleaf.com/articles/jason-richards-resume/chbxgnfyyvfc)) derived from Awesome-CV. Roboto + Source Sans Pro typography, centered header, 3-letter colored section titles, and 3-column executive footer.
   - `overleaf_single_page_keywords`: **Single Page + Keywords** — Based on Primož Godec and Salman Maqbool's template ([view on Overleaf](https://www.overleaf.com/latex/templates/sample-single-page-resume-with-keywords/wmcxcgmtkxzk)). Strictly single-page, Raleway font, 2-column header, TikZ circled FontAwesome 5 section icons, full-width Summary, and 2-column body with per-role `Keywords` lines.
   - `nico_krieger`: **Modelo Nico Krieger (`my-resume.cls`)** — Based on Dr. Nico Krieger's design ([view on Overleaf](https://www.overleaf.com/latex/templates/my-resume/rqzfybxqvpny) and [GitHub](https://github.com/GiantMolecularCloud/my-resume)). Features a full-width dark top header (name, title, tagline, optional photo), a highlight sidebar for contact info, 5-dot skill ratings (`\skilldots`), 6-level CEFR languages (`\langdots`), and certifications, paired with an elegant main column for experience and education.
   - `modern_pro`: Executive Modern (Professional & Tech)
   - `academic_classic`: Academic Classic (Researcher / Post-Grad / Faculty)
   - `tech_sidebar`: Tech & Engineering Two-Column (Sidebar) — Strictly single-page with balanced columns (no blank page)
   - `minimal_ats`: Minimalist ATS-Friendly (High Density) — Strictly single-page
   - **Custom Template (`.tex`)**: upload or paste your own `.tex` template and the engine populates the document body while preserving your custom preamble and macros.
5. **Multi-Provider AI Engine with Optional Custom API Keys & Zero-Storage In-Browser Encryption**:
   - **6 Supported AI Providers**: choose between **NVIDIA NIM** (secure server default or custom key), **Google Gemini**, **Anthropic Claude**, **OpenAI**, and **DeepSeek**, featuring state-of-the-art models and automated fallback resilience.
   - **In-Browser Ephemeral Encryption (`SECKEY_V1`)**: custom API keys entered into the web interface are encrypted and obfuscated on-the-fly using the **Web Crypto API (AES-256-GCM)** with a dynamic timestamp-derived key and random IV prior to network transit.
   - **RAM Enclave & Immediate Zeroing (Zero-Storage)**: the backend opens the cryptographic envelope solely within volatile RAM bytearray buffers (`src/_vault.py`), dispatches via pinned TLS 1.3, overwrites memory with null bytes (`0x00`) in `finally:` blocks, and scrubs environment variables with `os.environ.pop` to protect credentials against child processes (such as `pdflatex`).
6. **Strict Zero-Storage Policy for Received and Generated Documents (Volatile In-Memory Session)**:
   - **Zero Disk Retention**: the server never retains generated resumes (`.pdf`, `.tex`), uploaded profile photos, LinkedIn PDFs, or Lattes XMLs on disk. All documents exist strictly in volatile RAM during the active session.
   - **Guaranteed Destruction (`finally`)**: LaTeX compilation executes inside an isolated ephemeral temporary directory (`tempfile.mkdtemp`). As soon as binary assets are read into memory (base64 / bytes), all intermediate files are zero-fill shredded (`0x00`) and unlinked via `secure_wipe_and_remove_dir` in a guaranteed `finally:` block.
   - **Volatile Token Cache (RAM-Only)**: token metrics and caching run exclusively in volatile process memory (`in_memory_only=True`), never written to disk files on the server.
7. **Zero-Token Offline Engine & Surgical AI Review Mode (Maximum Token Efficiency)**:
   - **Deterministic Direct Generation (0 Tokens)**: generate professional resumes in sub-second time with zero LLM API calls and zero token consumption (`--no-ai` in CLI, `provider="none"` in web/backend, or standalone script `python scripts/generate_direct_resume.py`). Data from GitHub, Lattes, ORCID, LinkedIn, and Portfolio is mapped deterministically into all 9 built-in or custom LaTeX templates with strict special character escaping and zero hallucinations.
   - **Surgical Review-Only Mode**: saves up to 75% of LLM tokens compared to standard end-to-end synthesis. The direct engine builds the complete LaTeX document structure deterministically and submits only the document body (`\begin{document}` to `\end{document}`) to the chosen AI model for stylistic polish, action-verb enhancement, and syntax verification, bypassing heavy preamble overhead entirely.

### 📂 Project File & Directory Structure

The repository adheres to clean software engineering practices with strict modular separation:

```
resume-generator/
├── .github/
│   └── workflows/
│       ├── ci.yml              # Automated CI matrix test suite (Python 3.10, 3.11, 3.12)
│       └── deploy-pages.yml    # Continuous build & deployment to GitHub Pages (index.html + assets)
├── assets/                     # Official visual identity, SVG/PNG logos, and browser favicons
│   ├── icons/                  # Organized icon and favicon variants
│   │   ├── favicon.svg         # High-definition SVG vector logo (512x512)
│   │   ├── favicon.png         # 512x512 PNG icon
│   │   ├── favicon-192.png     # PWA / Android 192x192 variant
│   │   ├── favicon-32.png      # Desktop browser tab icon (32x32)
│   │   ├── favicon-16.png      # Compact tab icon (16x16)
│   │   ├── apple-touch-icon.png # iOS Safari / Apple Home Screen icon (180x180)
│   │   └── favicon.ico         # Multi-resolution ICO
│   └── README.md               # Technical branding specifications & color tokens
├── examples/                   # Sample profile data and reference templates
│   ├── sample_lattes.xml       # Official CNPq-compliant test XML
│   ├── sample_photo.png        # Neutral profile avatar for normalization testing
│   ├── custom_template_example.tex # Custom .tex template demonstration
│   ├── custom_template_example.pdf # Precompiled reference PDF
│   └── README.md               # Guide for experimenting with sample assets
├── scripts/                    # Maintenance & generation developer utilities
│   ├── generate_direct_resume.py # Deterministic zero-token direct resume generator
│   ├── generate_icons.py       # Official icon & favicon generator
│   ├── clean_artifacts.py      # Temporary build artifact and cache cleaner
│   └── README.md               # Utility scripts documentation
├── src/                        # Core application package
│   ├── _vault.py               # Volatile RAM enclave (ENC_PAYLOAD_V1 / SECKEY_V1) & key scrubber
│   ├── compiler.py             # Secure sandboxed LaTeX compilation with pdflatex
│   ├── config.py               # Project constants, directories, and AI provider configurations
│   ├── direct_builder.py       # Deterministic direct builder (0 tokens) from extractors
│   ├── extractors.py           # Multi-source parsers (GitHub, Google Scholar, ORCID, Lattes, LinkedIn, Portfolio)
│   ├── i18n.py                 # Multi-language dictionary strings (pt-BR and en-US)
│   ├── llm_client.py           # Multi-provider LLM coordinator (NVIDIA, Gemini, Claude, OpenAI, DeepSeek)
│   ├── nvidia_client.py        # NVIDIA NIM backward-compatibility adapter
│   ├── pipeline.py             # Full end-to-end synthesis and compilation pipeline
│   ├── templates.py            # 10 built-in LaTeX templates and custom template processor
│   ├── token_plugins.py        # Token-saving plugins (Caveman, TOON, ShortKey, Cache)
│   ├── ui_theme.py             # Dynamic themes, responsive CSS, and color palettes for Streamlit
│   ├── py.typed                # PEP 561 static typing compliance marker
│   └── README.md               # Comprehensive module architecture documentation
├── tests/                      # Automated test suite (Pytest - 214+ tests with 100% pass rate)
│   ├── conftest.py             # Global Pytest configuration and shared test fixtures
│   ├── test_academic_mode_and_colors.py # Academic mode, section completeness and custom color tests
│   ├── test_awards_and_orcid.py# Awards sanitization, redundant grant scrubbing and ORCID placement
│   ├── test_chronological_ordering_and_deduplication.py # Reverse chronological ordering & deduplication
│   ├── test_direct_builder.py  # Zero-token offline generator (0 tokens) and surgical review tests
│   ├── test_encrypted_comm.py  # End-to-end AES-256-GCM encryption & anti-key-leakage tests
│   ├── test_english_standardization_and_dedup.py # English standardization and cross-language dedup tests
│   ├── test_experience_nouns_and_email.py # Role noun sanitization and email formatting tests
│   ├── test_generation_resilience_and_ui_polish.py # Pipeline resilience & UI consistency tests
│   ├── test_latex_formatting.py# LaTeX syntax, security audits and compiler auto-repair tests
│   ├── test_manual_input_mode.py # Dual input mode (automated import vs structured manual entry) tests
│   ├── test_platform_display.py# Clean social and academic handle display formatting tests
│   ├── test_projects_enrichment.py # Project tech stack enrichment and description tests
│   ├── test_scholar_and_publications.py # Smart publication merging across Scholar, ORCID & Lattes
│   ├── test_single_page_template.py # Strictly single-page compilation tests (Google, Tech Sidebar, Minimal ATS, Keywords)
│   ├── test_ui_assets.py       # Icon integrity, favicons, WCAG accessibility and light/dark theme tests
│   ├── test_zero_storage.py    # Strict Zero-Storage, 0x00 memory shredding and RAM-only tests
│   └── README.md               # Comprehensive documentation of all 16 test modules and invariants
├── app.py                      # Interactive visual Streamlit application
├── server.py                   # Production API backend server (Flask / Gunicorn) for GitHub Pages & Render
├── cli.py                      # Command-line interface (CLI)
├── index.html                  # Standalone client web application for GitHub Pages & local server
├── pyproject.toml              # Modern project metadata, CLI entrypoints, linters & Pytest
├── requirements.txt            # Pip dependency declarations
├── Dockerfile                  # Production Docker container with full TeX Live & pdflatex
├── render.yaml                 # Infrastructure-as-code specification for Render
├── .gitignore                  # Strict exclusion rules for build artifacts, secrets, and caches
├── .dockerignore              # Lean build context exclusions for Docker
└── README.md                   # Comprehensive bilingual documentation
```

### 🚀 Publishing to GitHub, GitHub Pages & Render Backend

The project is architected for strict separation between the Static Frontend (GitHub Pages) and the LaTeX Compilation Backend (Render):

```mermaid
flowchart LR
    A["🌐 Official Web Frontend<br>(https://jluckmay.github.io/resume-generator/)"] -- "1. POST /api/generate<br>(Origin: https://jluckmay.github.io<br>+ Optional SECKEY_V1 Envelope)" --> B["🛡️ Render Backend<br>(Docker + pdflatex + Gunicorn)"]
    B -- "2. Token-Saving LLM Synthesis<br>(TLS 1.3 + Zero-Storage Vault)" --> C["⚡ Multi-Provider AI Engine<br>(NVIDIA NIM / Gemini / Claude / OpenAI / DeepSeek)"]
    C -- "3. Structured JSON / TOON" --> B
    B -- "4. Sandboxed LaTeX Compilation<br>(-no-shell-escape + openin_any=p)" --> B
    B -- "5. Compiled PDF (Base64) + X-Backend-Attestation" --> A
```

#### 1. Frontend Hosting on GitHub Pages (`https://jluckmay.github.io/resume-generator/`)
- Pushing to the `main` branch triggers GitHub Actions (`.github/workflows/deploy-pages.yml`) to automatically publish the standalone web UI (`index.html`) to GitHub Pages.
- The frontend enforces a strict **Content Security Policy (CSP)** and mutual client attestation headers (`X-Resume-Client: jluckmay-github-pages-v1`).

#### 2. Backend Deployment on Render (`Dockerfile` + `render.yaml`)
1. In the [Render Dashboard](https://dashboard.render.com/), choose **New +** -> **Blueprint** and connect the repository (or create a **Web Service** selecting the **Docker** runtime).
2. The `render.yaml` specification automatically builds the service with the production `Dockerfile` (containing full TeX Live with `pdflatex` and typography packages).
3. Under the service's **Environment** tab on Render, add the environment variable:
   - `NVIDIA_API_KEY`: your NVIDIA API key (`nvapi-...`).
4. The service exposes the `/healthz` endpoint for zero-downtime health checking.

#### 3. Strict Mutual Communication Lockdown (Exclusive to `https://jluckmay.github.io/`)
- The backend (`server.py`) rejects **any connection** whose `Origin` or `Referer` does not originate from `https://jluckmay.github.io/` (returning `403 Forbidden`).
- **Direct Integration from Authorized Page**:
  Any script hosted on `https://jluckmay.github.io/` can request resume compilation directly via standard `fetch`:
  ```javascript
  const formData = new FormData();
  formData.append("resume_type", "professional"); // or "academic"
  formData.append("template_id", "google_standard"); // or "ai_ats_max", "modern_pro", etc.
  formData.append("github", "octocat");
  formData.append("portfolio", "https://jluckmay.github.io/");

  const response = await fetch("https://<your-backend-service>.onrender.com/api/generate", {
    method: "POST",
    headers: {
      "X-Resume-Client": "jluckmay-github-pages-v1",
      "X-Client-Timestamp": Date.now().toString()
    },
    body: formData
  });
  const data = await response.json();
  // data.pdf_base64 contains the generated PDF in base64
  ```

### 🔒 Project Security Audit & Applied Hardening

| Audited Vector | Production Risk | Applied Countermeasure |
| :--- | :--- | :--- |
| **Credential Exposure on Public Git Repo** | Bots/scrapers or repository users extracting credentials from source code, documents, or Git commits. | **Zero-Secret Git Policy & Decoupled Ephemeral Vault**: The public Git repository, commit history, documentation, and distributed files contain **zero credentials, zero shards, and zero embedded keys**. The production API key is configured solely within the Render backend's private environment variables (`NVIDIA_API_KEY`), entirely decoupled from Git. Upon initialization, `_vault.py` purges the variable from `os.environ` immediately (`os.environ.pop`), enforces call-stack attestation (`src/nvidia_client.py` and `src/llm_client.py`), dispatches via strict pinned TLS 1.3, and overwrites all volatile memory buffers with zeros (`0x00`) in a `finally:` block. End users on GitHub Pages compile resumes through the backend without ever having access to or the ability to retrieve the default API key. Custom keys provided in the web interface are encrypted on the client side with Web Crypto AES-256-GCM (`SECKEY_V1`) and are immediately zeroed out in RAM post-generation. For independent local usage, users can supply their own keys via environment variables, the `--api-key` flag, or the UI. |
| **LaTeX Arbitrary Code Execution (RCE)** | `\write18` or `\directlua` primitives inside custom templates. | **Upstream Sanitization + TeX Sandbox**: regex blocking of system commands (`\write18`, `\csname`, `\catcode`, `\input{/`). `pdflatex` runs with `-no-shell-escape`, a sanitized environment, and Web2C parameters `openin_any=p` and `openout_any=p` (preventing file reads outside the ephemeral build directory). |
| **SSRF (Server-Side Request Forgery)** | Malicious URLs targeting cloud metadata (`169.254.169.254`) or internal networks (`127.0.0.1`, `10.0.0.0/8`). | **Public IP Validator (`_safe_http_get`)**: DNS resolution asserting `ip.is_global == True`. Rejection of loopback, private, and link-local ranges, with a 1.5 MB response download cap and safe redirect evaluation. |
| **ZIP Bomb / XXE Bomb (Billion Laughs)** | Malicious ZIP or recursive entity XML uploads via Lattes. | Strict uncompressed size ceiling (15 MB), regex rejection of `<!DOCTYPE` and `<!ENTITY` declarations prior to XML parsing, and 25 MP image cap in Pillow (`Image.MAX_IMAGE_PIXELS`). |
| **Unauthorized Backend Abuse** | Third parties abusing the Render endpoint to drain API tokens. | **Strict Origin & Referer Gate**: CORS restricted exclusively to `https://jluckmay.github.io`, mutual attestation verification (`X-Resume-Client`, `X-Backend-Attestation`), and in-memory sliding-window IP rate limiting (max 15 generations / 10 min). |
| **Network Eavesdropping & Snooping** | Packet sniffing or browser DevTools Network tab inspection exposing resume parameters, personal data, or credentials in transit. | **End-to-End Application-Layer Encryption (`ENC_PAYLOAD_V1`)**: all communication between the frontend (`index.html`) and backend (`server.py`) travels inside an **AES-256-GCM** cryptographic envelope with dynamic timestamp salt and random IV (`crypto.subtle`). Any network inspection tool (DevTools Network panel, Wireshark, proxy) observes exclusively opaque `ciphertext`, rendering traffic completely unreadable in transit. |
| **Console & API Key Probing Attacks** | Users running scripts in the browser DevTools Console (`window.apiKey`, probing `/api/status`) or command-line tools (curl/Postman) trying to exfiltrate the server's default API key. | **Console Lockdown & Zero-Leak Defense**: The backend's default API key lives strictly in volatile memory within the Render Enclave and is **never** transmitted to the client in any response or header. The `/api/status` endpoint is sanitized with all internal variable names (`env_vars`) stripped. All endpoints and error handlers (`400`, `403`, `404`, `500`) pass through the recursive `scrub_sensitive_api_keys` filter, ensuring any active secret key pattern is redacted to `[REDACTED_API_KEY]`. In the browser, global namespace variables are frozen (`window.apiKey = undefined`), preventing console exfiltration. |

### 🧠 Supported AI Providers & Model Selection

The generator supports multiple leading AI providers, accommodating the default server infrastructure as well as user-supplied custom API keys:

| Provider | Recommended Primary Model | Alternative / Fallback Models | Key Characteristics |
| :--- | :--- | :--- | :--- |
| **NVIDIA NIM** *(Default / Custom Key)* | `nvidia/nemotron-3.5-super-vl-120b-a12b` | `stepfun-ai/step-5-preview`, `google/gemma-4-31b-it`, `z-ai/glm-5.3` | 120B MoE (12B active), latency < 1.0s, native `enable_thinking: False` (0 hidden tokens). Backend default. |
| **Google Gemini** *(Custom Key)* | `gemini-2.5-flash` | `gemini-2.5-pro`, `gemini-1.5-pro`, `gemini-1.5-flash` | Ultra-fast throughput, enhanced reasoning, strict adherence to structured JSON schemas. |
| **Anthropic Claude** *(Custom Key)* | `claude-3-7-sonnet-20250219` | `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022` | Flawless executive and academic synthesis, high-precision phrasing, and polished formal prose. |
| **OpenAI** *(Custom Key)* | `gpt-4o` | `gpt-4o-mini`, `o3-mini`, `gpt-4-turbo` | Flagship multimodal model, deterministic consistency for XYZ impact bullet points and metrics. |
| **DeepSeek** *(Custom Key)* | `deepseek-chat` (DeepSeek V3) | `deepseek-reasoner` (DeepSeek R1) | Highly cost-effective, exceptional performance on technical coding backgrounds and structured summaries. |

### Token-Saving Plugins (`src/token_plugins.py`)

| Plugin | Function & Token Economy Impact |
| :--- | :--- |
| **`CavemanPromptPlugin`** | Applies `caveman` skill directives (zero preamble, zero markdown fences, ultra-dense instructions) while keeping final resume prose in polished formal `en-US` or `pt-BR` (~65% verbosity reduction). |
| **`ThinkingSuppressionPlugin`** | Injects `chat_template_kwargs={"enable_thinking": False}`, cutting hidden `reasoning_tokens` overhead down to **0 tokens**. |
| **`TOONContextPrunerPlugin`** | Compresses raw GitHub, ORCID, Lattes, LinkedIn, and Portfolio payloads into **TOON (Token-Oriented Object Notation)** and deduplicates publications locally before calling the API. |
| **`ShortKeySchemaPlugin`** | Uses 1–2 character JSON keys (`nm`, `tl`, `xp`, `ed`, `pb`, `sk`) during LLM generation and expands them locally in Python (~40% fewer structural output tokens). |
| **`LaTeXPreambleSplitPlugin`** | Splits static preambles (`\documentclass`...`\begin{document}`) from custom `.tex` templates so the LLM never spends tokens reading or regenerating package declarations. |
| **`SHA256DiskCachePlugin`** | Local SHA-256 disk cache at `.cache/nvidia_token_cache.json` (**0 API tokens** on repeated runs). |

### 💻 Full Local Execution Guide (`en-US`)

You can run the entire resume generator and compile PDFs locally on your workstation with maximum speed, full privacy, and without cloud deployment:

#### 1. Local Environment Setup
```powershell
# 1. Clone the repository
git clone https://github.com/Jluckmay/resume-generator.git
cd resume-generator

# 2. Create and activate a Python virtual environment (recommended)
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Verify local LaTeX compiler installation
python cli.py --lang en-us --check-deps
```

#### 2. Configure API Keys (Multi-Provider)
Set the API key for your desired provider in your terminal before launching (or input it interactively/via the web UI without saving to disk):
```powershell
# NVIDIA NIM (Default for local NVIDIA execution):
$env:NVIDIA_API_KEY = "nvapi-your-key-here"

# Google Gemini:
$env:GEMINI_API_KEY = "AIzaSy-your-key-here"

# Anthropic Claude:
$env:ANTHROPIC_API_KEY = "sk-ant-your-key-here"

# OpenAI:
$env:OPENAI_API_KEY = "sk-your-key-here"

# DeepSeek:
$env:DEEPSEEK_API_KEY = "sk-your-key-here"
```
*(On Linux or macOS, replace `$env:NAME = "..."` with `export NAME="..."`)*

#### 3. Available Execution Modes

##### Mode A: Native Standalone HTML5 Web Server (`server.py`) — Recommended
Launches the local compilation server with the bundled HTML5 web app:
```powershell
python server.py
```
- Open in your browser: `http://127.0.0.1:5000`
- Runs in local development mode with direct compilation via your local `pdflatex`, eliminating network latency.
- Supports live multi-provider switching and custom client-side API keys with Web Crypto AES-256-GCM encryption.

##### Mode B: Interactive Streamlit Web UI (`app.py`)
Launches the rich Streamlit dashboard with light/dark theme toggling and live template previews:
```powershell
streamlit run app.py
```
- Open in your browser: `http://localhost:8501`
- Includes sidebar provider selection (`NVIDIA`, `Google`, `Claude`, `OpenAI`, `DeepSeek`), corresponding models, secure key input, and interactive live previews for all 9 LaTeX templates.

##### Mode C: Command-Line Interface / CLI (`cli.py`)
Fast, scriptable resume generation directly from the terminal, with full multi-provider support:
```powershell
# List all supported AI providers and models:
python cli.py --list-providers

# Example 1: Google Standard Resume with the default provider (NVIDIA NIM)
python cli.py --lang en-us --type professional --template google_standard --github octocat --linkedin "https://linkedin.com/in/example" --portfolio "https://jluckmay.github.io/" --output resume_google

# Example 2: AI & ATS-Optimized Resume using Google Gemini (key read from $env:GEMINI_API_KEY)
python cli.py --lang en-us --type professional --template ai_ats_max --provider google --github octocat --primary-color "#0F4C81" --secondary-color "#1E293B" --output resume_gemini

# Example 3: Academic CV using Anthropic Claude with key supplied via secure parameter
python cli.py --lang en-us --type academic --template academic_classic --provider claude --api-key "sk-ant-..." --orcid 0000-0002-1825-0097 --lattes-file examples/sample_lattes.xml --output resume_claude

# Example 4: Resume using OpenAI prompting for the API key via hidden password prompt
python cli.py --lang en-us --type professional --template modern_pro --provider openai --github octocat --output resume_openai
```

##### Mode D: Zero-Token Offline Mode & Surgical Review Mode
Generate resumes instantly without spending tokens, or use AI strictly for stylistic polish:
```powershell
# 1. 100% deterministic direct generation without AI (0 tokens) via CLI:
python cli.py --lang en-us --type professional --template google_standard --github octocat --no-ai --output resume_offline

# 2. Standalone direct resume builder utility:
python scripts/generate_direct_resume.py --lang en-us --template modern_pro --github octocat --lattes-file examples/sample_lattes.xml --output resume_direct

# 3. Surgical review-only mode (builds deterministic skeleton and submits only document body to AI, saving ~75% tokens):
python cli.py --lang en-us --type professional --template ai_ats_max --github octocat --review-only --output resume_reviewed
```

### 🌐 Web Interface & Repository Usage Guide (`https://github.com/Jluckmay/latex-resume`)

The web application can be used directly in the cloud through GitHub Pages paired with your Render backend:

#### 1. Official Access Points
- **Official GitHub Repository:** [`https://github.com/Jluckmay/latex-resume`](https://github.com/Jluckmay/latex-resume)
- **Official Web Page (GitHub Pages):** [`https://jluckmay.github.io/latex-resume/`](https://jluckmay.github.io/latex-resume/) (or integrated via [`https://jluckmay.github.io/`](https://jluckmay.github.io/))

#### 2. Connecting the Web Interface to your Render Backend
1. Open the official web app in any modern browser.
2. In the settings panel (gear icon or footer), check the **Backend URL (Render)** field:
   - The frontend automatically connects to the default Render server via an obfuscated, encrypted runtime enclave (or you can specify your own Render deployment: `https://<your-service>.onrender.com` or local server: `http://127.0.0.1:5000`).
3. The web app automatically performs health probes (`/healthz` and `/api/status`), accounting for Render free instance cold starts (~30-50s) with automatic polling retries, pulsing visual indicators, and transparent compile retries, displaying a green badge indicating the live status and TeX Live compiler version.
4. **Review-Only Mode Enabled by Default**: The "Review-Only Mode (~75% Token Savings)" comes pre-enabled across web and local interfaces, building the deterministic resume first from extractors and using AI strictly for phrasing refinement and syntax polishing.

#### 3. Optional Custom API Keys & Ephemeral In-Memory Encryption (Zero-Storage Policy)
Users can choose between the secure server-provided default or **provide their own optional API keys**, with multi-provider architecture:
- **⚡ NVIDIA NIM (Server Default)**: Uses the secure server-configured key, no user credential required.
- **🟢 NVIDIA NIM (Own key)**: `nvapi-...`
- **🔵 Google Gemini (Own key)**: `AIzaSy...` (Gemini 2.0 Flash, 1.5 Pro, 1.5 Flash)
- **🟣 Anthropic Claude (Own key)**: `sk-ant-...` (Claude 3.5 Sonnet, 3.5 Haiku)
- **🟢 OpenAI (Own key)**: `sk-...` (GPT-4o, GPT-4o Mini, o3-mini)
- **🔷 DeepSeek (Own key)**: `sk-...` (DeepSeek V3, DeepSeek R1)

##### Cryptographic Protection & Zero-Storage Protocol:
1. **In-Browser Encryption (`SECKEY_V1`):** When entering a custom key in the web interface, it is encrypted and obfuscated in real time via **Web Crypto API (AES-256-GCM)** using an ephemeral dynamic key derived from timestamp and random IV (`SECKEY_V1:...`). Plaintext keys **never** travel exposed and are **never** stored in `localStorage`, `sessionStorage`, cookies, or browser logs.
2. **Strict Volatile RAM Enclave (`src/_vault.py`):** On the backend and in local environments, the cryptographic envelope is unpacked strictly in volatile RAM into zeroable `bytearray` buffers.
3. **Immediate Memory Zeroing (Zero-Storage):** Following the pinned TLS 1.3 HTTPS dispatch, the memory buffer is immediately overwritten with null bytes (`0x00`) in `finally:` blocks. Environment variables (`NVIDIA_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`) are scrubbed with `os.environ.pop` to prevent child processes (such as `pdflatex`) from accessing any credentials.

#### 4. Step-by-Step Resume Generation Workflow
1. **Personal Information & Input Mode**: Input your name, target role, contact info, location (with clickable Google Maps integration), and select your data input mode:
   - **Import Information**: provide profile URLs or upload files (GitHub, LinkedIn, ORCID, Lattes, Portfolio Website, Photo).
   - **Manual Entry**: fill in your summary, education, experience, skills, projects, languages, awards, and publications directly.
2. **Choose AI Provider & Model**: Select your preferred provider (Server Default NVIDIA, Custom NVIDIA, Google Gemini, Anthropic Claude, OpenAI, or DeepSeek) and corresponding model. Optionally enter your own API key with complete cryptographic security.
3. **Choose a LaTeX Template**: Select from the 10 available built-in templates:
   - **`ai_ats_max`**: Maximum readability for AI screeners (Claude/Gemini/GPT) and neural ATS filters (Interface Default).
   - **`google_standard`**: Google Software Engineer recruitment standard (high-density XYZ accomplishment bullet points).
   - **`overleaf_russell_ti`**: Modelo Russell with circular icons and skill rating bars.
   - **`overleaf_awesome_cv`**: Awesome CV with centered header and executive footer.
   - **`overleaf_single_page_keywords`**: Single Page + Keywords with per-position stack keywords.
   - **`nico_krieger`**: Modelo Nico Krieger with dark top header and 5-dot skill ratings.
   - **`modern_pro`**, **`academic_classic`**, **`tech_sidebar`**, **`minimal_ats`** or your own uploaded `.tex` file.
4. **Color Customization**: Choose a curated executive palette or input custom HEX colors for primary and secondary accents.
5. **Generate**: Click **"Generate Resume"**.
6. **Preview & Download**: The generated PDF renders in the embedded interactive viewer, alongside tabs to inspect or copy the raw `.tex` source code and download the `.pdf` file with a single click.

#### 5. Strict Communication Lockdown
For end-to-end security, the Render backend strictly permits incoming connections and compilation requests **only** from:
- `https://jluckmay.github.io/`

Any unauthorized request from other origins, third-party sites, or scrapers is immediately rejected with HTTP `403 Forbidden`.

#### 6. LaTeX Template Credits & Open-Source References

This project gratefully acknowledges and attributes the original designers and authors across the Overleaf and LaTeX open-source community:

| Template | Original Author / Project | Overleaf / GitHub Reference | License / Origin |
| :--- | :--- | :--- | :--- |
| **Modelo Russell** | Russell | [Overleaf `rgfqqnnynrmv`](https://www.overleaf.com/read/rgfqqnnynrmv#d5b171) | Overleaf Community |
| **Awesome CV** | Jason Richards & Claud D. Park (posquit0) | [Overleaf `chbxgnfyyvfc`](https://www.overleaf.com/articles/jason-richards-resume/chbxgnfyyvfc) · [GitHub `posquit0/Awesome-CV`](https://github.com/posquit0/Awesome-CV) | LaTeX Project Public License / MIT |
| **Single Page + Keywords** | Primož Godec & Salman Maqbool | [Overleaf `wmcxcgmtkxzk`](https://www.overleaf.com/latex/templates/sample-single-page-resume-with-keywords/wmcxcgmtkxzk) | Overleaf Community |
| **Modelo Nico Krieger** | Dr. Nico Krieger | [Overleaf `rqzfybxqvpny`](https://www.overleaf.com/latex/templates/my-resume/rqzfybxqvpny) · [GitHub `GiantMolecularCloud/my-resume`](https://github.com/GiantMolecularCloud/my-resume) | GNU General Public License v3.0 |
| **Google Standard (SWE)** | Gayle Laakmann McDowell / Big Tech | Official SWE recruitment guidelines (Google / Cracking the Coding Interview) | Open Industry Standard |
| **AI & ATS Max-Readability** | LaTeX Resume Core Team | Deterministic LLM parser and neural ATS layout engineering | MIT |
| **Executive Modern / Academic / Tech / Minimalist** | LaTeX Resume Core Team | Native single and two-column corporate & academia resume layouts | MIT |

### 📄 License

This project is released under the [MIT License](LICENSE).

Copyright (c) 2026 João Lucas Mayrinck.

---

## 🇧🇷 Português (`pt-BR`)

Gerador automático de currículos **Acadêmicos** e **Profissionais** em **LaTeX + PDF** (nos idiomas `pt-BR` e `en-US`), alimentado por **Múltiplos Provedores de IA** (**NVIDIA NIM**, **Google Gemini**, **Anthropic Claude**, **OpenAI**, **DeepSeek**) com arquitetura modular de **Plugins de Economia de Tokens**, **Criptografia Efêmera em Navegador (AES-256-GCM)** e **Cofre de Memória Zero-Storage (Task-Bound Enclave)**.

### 📋 Requisitos do Projeto

Para executar o gerador e compilar os currículos em PDF, o ambiente deve atender aos seguintes requisitos obrigatórios:

1. **Compilador LaTeX (`pdflatex`) — Obrigatório**:
   - Distribuição **TeX Live** (2023 ou superior recomendado) ou **MiKTeX** instalada e disponível no `PATH` do sistema.
   - Pacotes LaTeX utilizados pelos templates integrados (incluídos no TeX Live / MiKTeX): `babel` (`brazil` e `english`), `lmodern`, `roboto`, `sourcesanspro`, `raleway`, `fontawesome5`, `tikz`, `multicol`, `tcolorbox`, `adjustbox`, `array`, `fancyhdr`, `geometry`, `xcolor`, `graphicx`, `enumitem`, `titlesec` e `hyperref`.
   - **Instalação rápida do compilador LaTeX**:
     - **Windows (TeX Live ou MiKTeX via Winget)**:
       ```powershell
       winget install -e --id MiKTeX.MiKTeX
       # ou TeX Live completo: https://www.tug.org/texlive/
       ```
     - **Linux (Ubuntu / Debian)**:
       ```bash
       sudo apt update && sudo apt install -y texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-lang-portuguese texlive-fonts-recommended texlive-fonts-extra
       ```
     - **macOS (Homebrew)**:
       ```bash
       brew install --cask mactex-no-gui
       ```
   - **Verificação do compilador**:
     ```powershell
     pdflatex --version
     # ou via CLI do projeto:
     python cli.py --lang pt-br --check-deps
     ```

2. **Python (`>= 3.10`) e Dependências Python (`requirements.txt`)**:
   - `requests >= 2.31.0`
   - `beautifulsoup4 >= 4.12.0`
   - `Pillow >= 10.0.0`
   - `streamlit >= 1.32.0`
   - `pypdf >= 4.0.0`
   - `flask >= 3.0.0`
   - `cryptography >= 41.0.0`
   - **Instalação**:
     ```powershell
     pip install -r requirements.txt
     ```

### Principais Recursos

1. **Duas Interfaces Web Completas (HTML5 `index.html` + `server.py` e Streamlit `app.py`) com Detecção Automática de Tema e Idioma**:
   - **Design 100% Responsivo & Mobile-First**: interfaces otimizadas para smartphones, tablets e monitores desktop com breakpoints fluidos, ajuste adaptativo de grades (`grid-template-columns`), áreas de toque acessíveis (min 44px) e visualizador de PDF redimensionável dinamicamente (`clamp()`).
   - **Identidade Visual & Ícone Oficial**: logotipo vetorial moderno nos formatos `SVG`, `PNG` (512x512, 192x192, 32x32, 16x16) e `ICO` multi-resolução, integrado na guia do navegador (`favicon`), barra de navegação e cabeçalhos de ambas as interfaces.
   - **Paridade Total de Recursos**: tanto a interface web HTML nativa (`index.html` servida por `python server.py`) quanto a interface Streamlit (`streamlit run app.py`) compartilham um design limpo, agradável e intuitivo com exatamente os mesmos recursos.
   - **Detecção Automática**: detectam automaticamente na inicialização o **idioma padrão** (`navigator.language` / `Accept-Language` ou idioma do SO) e o **tema visual padrão** (`prefers-color-scheme` / registro do SO), adotando-os sem necessidade de configuração manual.
   - **Alternância Instantânea**: incluem seletor rápido entre **☀️ Modo Claro** e **🌙 Modo Escuro** e alternância instantânea entre **Português (`pt-BR`)** e **Inglês (`en-US`)**.
2. **Preview Visual em Tempo Real dos Modelos LaTeX e Customização de Cores**:
   - **Preview Interativo**: exibe uma prévia visual fiel do layout do modelo LaTeX escolhido (`modern_pro`, `academic_classic`, `tech_sidebar`, `minimal_ats`, `overleaf_russell_ti`, `overleaf_awesome_cv`, `overleaf_single_page_keywords`, `nico_krieger`, `google_standard`, `ai_ats_max`) que reflete instantaneamente as cores e o idioma selecionados antes mesmo de compilar o PDF.
   - **Paletas e Seletor de Cores (`HEX`)**: escolha entre 6 paletas executivas/acadêmicas predefinidas (*Grafite ATS (Padrão)*, *Azul Oceano*, *Azul Marinho Acadêmico*, *Verde Esmeralda Tech*, *Índigo Real*, *Bordô Clássico*) ou defina manualmente a **Cor Principal** e a **Cor Secundária** aplicadas ao código LaTeX (`\definecolor`).
3. **Modo Duplo de Entrada de Dados: Importação Automática & Inserção Manual Estruturada**:
   - **Alternância Flexível na Interface**: escolha facilmente entre **Importar Informações** ou **Inserir Manualmente** tanto na aplicação Web quanto no Streamlit.
   - **Modo Importação (Perfis Online & Arquivos)**:
     - **Google Scholar**: extrai nome do pesquisador, filiação institucional, métricas de impacto acadêmico (Total de Citações, h-index, i10-index) e lista completa de publicações com título, autores, conferência/periódico, ano e número de citações (aceita ID de usuário ou URL do perfil público).
     - **Portfólio Pessoal (`URL`)**: extrai título, descrição, seções (`h1`/`h2`/`h3`), bio, projetos, idiomas estruturados com proficiência, premiações/menções honrosas e publicações científicas com link DOI diretamente da página web do usuário, adicionando o link clicável no cabeçalho do PDF.
     - **GitHub**: extrai bio, localização, linguagens principais e repositórios de maior destaque via API REST pública (aceita URL completa ou username), com análise automatizada de README para extração de resumos contextuais e detecção completa de todas as ferramentas e linguagens utilizadas.
     - **ORCID**: extrai biografia, formação (`educations`), vínculos (`employments`), bolsas/auxílios (`fundings`), distinções e artigos publicados (`works` com DOI) via API Pública v3.0 (aceita ID ou URL).
     - **Lattes**: parser nativo para o arquivo oficial `XML`/`ZIP` exportado do CNPq (`CURRICULO-VITAE`), além de suporte a PDF, HTML, URL ou ID de 16 dígitos / texto complementar.
     - **LinkedIn**: suporte a URL do perfil ou username, upload do PDF oficial exportado pelo LinkedIn (*Salvar como PDF*) e texto complementar.
     - **Entrada Suplementar de Idiomas e Premiações**: campos opcionais na interface de importação para enriquecer ou complementar dados ausentes nas plataformas.
     - **Foto de Perfil**: normalização automática de imagem (`PNG`/`JPG`/`WebP`) via Pillow para inclusão no LaTeX (`\includegraphics`).
   - **Modo Inserção Manual (Preenchimento Direto & Cards Estruturados)**:
     - Permite que candidatos sem perfis públicos ou que prefiram controle editorial completo insiram seus dados diretamente em formulários estruturados na interface.
     - **Cards Dinâmicos com Botões de Adicionar/Remover**: formulários estruturados com botões `+ Adicionar` e `Remover` com campos dedicados para:
       - **Formação Acadêmica**: Grau/Curso, Instituição de Ensino, Período e Detalhes/Ênfase/Tese.
       - **Experiência Profissional**: Cargo/Título, Empresa/Organização, Período, Localização e Descrição/Realizações.
       - **Projetos Relevantes**: Nome do Projeto, Tecnologias Utilizadas, Link/Repositório (URL) e Descrição.
       - **Publicações & Artigos**: Título da Publicação, Periódico/Conferência, Ano, Autores e DOI/Link.
       - **Prêmios & Certificações**: Título/Certificação, Ano e Instituição/Detalhes.
     - **Modo Rápido / Texto em Lote (Expansível)**: mantém suporte opcional a sintaxe linha por linha separada por barras verticais (`|`) ou objetos JSON para colar múltiplos itens em bloco.
     - Preserva campos opcionais de links (GitHub, Google Scholar, LinkedIn, Portfólio, ORCID, Lattes e Foto) para enriquecer o cabeçalho do currículo.
4. **10 Modelos LaTeX Integrados (incluindo Padrão Google, Otimizado para IA & ATS, Modelo Russell, Awesome CV, Single Page + Keywords e Modelo Nico Krieger) + Suporte a Template `.tex` Customizado**:
   - `ai_ats_max`: **Otimizado para IA & ATS (Máxima Legibilidade por LLMs & ATS Neurais)** — Desenvolvido especificamente para triagem automatizada por LLMs (Gemini, Claude, GPT) e sistemas ATS neurais (Workday, Greenhouse, Lever). Fluxo textual 100% linear em coluna única, metadados semânticos explícitos, matriz de competências e palavras-chave (Core Competencies & Keywords) dedicada para match semântico e compatibilidade Unicode nativa (`glyphtounicode`). Multi-página abrangente para máxima densidade de indexação.
   - `google_standard`: **Padrão Google (Big Tech / Software Engineer)** — Baseado nas diretrizes de recrutamento Big Tech (Google SWE / Gayle Laakmann McDowell). Página única densa garantida (0.5 polegadas / 1.0 cm de margem), destaque em Google Blue (`#0B57D0`), estrutura XYZ de realizações ("Conquistou [X] medido por [Y], realizando [Z]"), divisórias horizontais limpas e hierarquia clássica (Empresa no topo, cargo em itálico abaixo).
   - `overleaf_russell_ti`: **Modelo Russell (Currículo T.I.)** — Baseado no template Russell CV ([ver no Overleaf](https://www.overleaf.com/read/rgfqqnnynrmv#d5b171)). Cabeçalho com foto à esquerda, ícones FontAwesome 5, títulos com destaque nas 3 primeiras letras, tabela de skills e círculos de proficiência de idiomas em 6 níveis CEFR (A1 a C2).
   - `overleaf_awesome_cv`: **Awesome CV (Jason Richards)** — Baseado no modelo Jason Richards Résumé ([ver no Overleaf](https://www.overleaf.com/articles/jason-richards-resume/chbxgnfyyvfc)) derivado do Awesome-CV. Tipografia Roboto + Source Sans Pro, cabeçalho centralizado, títulos com destaque colorido nas 3 primeiras letras e rodapé executivo de 3 colunas.
   - `overleaf_single_page_keywords`: **Single Page + Keywords** — Baseado no modelo de Primož Godec e Salman Maqbool ([ver no Overleaf](https://www.overleaf.com/latex/templates/sample-single-page-resume-with-keywords/wmcxcgmtkxzk)). Página única estrita, fonte Raleway, cabeçalho em 2 colunas, ícones circulares em TikZ + FontAwesome 5, seção Summary em largura total e corpo em 2 colunas com linha de `Keywords` por cargo.
   - `nico_krieger`: **Modelo Nico Krieger (`my-resume.cls`)** — Baseado no template de Dr. Nico Krieger ([ver no Overleaf](https://www.overleaf.com/latex/templates/my-resume/rqzfybxqvpny) e no [GitHub](https://github.com/GiantMolecularCloud/my-resume)). Cabeçalho escuro de largura total com nome, cargo/tagline e foto opcional; barra lateral destacada (`highlightbar`) para contatos, habilidades avaliadas em 5 pontos (`\skilldots`) e idiomas em 6 níveis CEFR (`\langdots`); e coluna principal para experiência, formação, projetos e publicações.
   - `modern_pro`: Moderno Executivo (Profissional & Tech)
   - `academic_classic`: Acadêmico Clássico (Pesquisador / CNPq / Pós-Graduação)
   - `tech_sidebar`: Tech & Engenharia Duas Colunas (Barra Lateral) — Página única estrita com colunas balanceadas (sem página inicial em branco)
   - `minimal_ats`: Minimalista ATS-Friendly (Alta Densidade) — Página única estrita de alta densidade
   - **Template Customizado (`.tex`)**: envie qualquer arquivo `.tex` próprio e o modelo preencherá a estrutura mantendo o preâmbulo original.
5. **Suporte Multi-Provedor com Chaves Próprias Opcionais e Criptografia em Navegador (Zero-Storage)**:
   - **6 Provedores de IA Suportados**: escolha entre **NVIDIA NIM** (padrão de servidor ou chave própria), **Google Gemini**, **Anthropic Claude**, **OpenAI** e **DeepSeek**, com modelos de última geração e fallback automático.
   - **Criptografia Efêmera no Navegador (`SECKEY_V1`)**: ao inserir uma chave própria na interface web, ela é criptografada e ofuscada em tempo real via **Web Crypto API (AES-256-GCM)** com vetor de inicialização aleatório e derivação dinâmica baseada em timestamp antes de transitar na rede.
   - **Isolamento de Memória & Destruição Imediata (Zero-Storage)**: o backend abre o envelope criptográfico exclusivamente em buffers voláteis na RAM (`src/_vault.py`), despacha a requisição via TLS 1.3 puro e preenche a memória com bytes nulos (`0x00`) no bloco `finally`, expurgando credenciais com `os.environ.pop` para impedir que processos-filhos (como o `pdflatex`) tenham acesso a qualquer segredo.
6. **Política Estrita de Zero-Storage para Documentos Recebidos e Gerados (Sessão Volátil em Memória)**:
   - **Zero Retenção em Disco**: o servidor não armazena currículos gerados (`.pdf`, `.tex`), fotos de perfil enviadas, PDFs do LinkedIn ou arquivos do Lattes. Todos os dados e arquivos são processados exclusivamente na memória volátil durante a requisição ou sessão ativa.
   - **Compilação Efêmera & Destruição Imediata (`finally`)**: a compilação LaTeX ocorre em diretório temporário efêmero isolado (`tempfile.mkdtemp`). Imediatamente após a conversão do PDF para base64/bytes em RAM, todos os arquivos temporários são sobrescritos com bytes nulos (`0x00`) e expurgados via `secure_wipe_and_remove_dir` no bloco `finally:`.
   - **Cache de Tokens Volátil (RAM-Only)**: o cache de tokens opera em memória volátil durante a execução do processo (`in_memory_only=True`), sem gravação de currículos ou prompts em arquivos de disco no servidor.
7. **Modo Offline Zero-Token & Modo de Revisão Cirúrgica (Economia Máxima de Tokens)**:
   - **Geração Direta Determinística (0 Tokens)**: gere currículos completos em menos de 1 segundo sem consumir nenhuma cota ou chamada de IA (`--no-ai` no CLI, `provider="none"` no backend/HTML/Streamlit, ou via `python scripts/generate_direct_resume.py`). Os extratores mapeiam dados reais diretamente para os 10 modelos LaTeX ou template customizado com sanitização rigorosa de caracteres especiais e regras anti-alucinação.
   - **Modo Apenas Revisão (Review-Only)**: economiza até 75% dos tokens comparado à síntese tradicional! O motor gera o esqueleto LaTeX determinístico completo e submete apenas o corpo do documento (`\begin{document}` a `\end{document}`) ao modelo de IA para polimento textual, fortalecimento de verbos de ação e validação de sintaxe, sem gastar tokens com preâmbulos ou cabeçalhos estruturais.

### 📂 Estrutura de Arquivos e Diretórios

O projeto segue padrões modulares da indústria, organizando código, testes, scripts, modelos e assets de forma limpa e intuitiva:

```
latex-resume/
├── .github/
│   └── workflows/
│       ├── ci.yml              # CI automatizado com matriz de testes (Python 3.10, 3.11, 3.12)
│       └── deploy-pages.yml    # Build e deploy contínuo no GitHub Pages (index.html + assets)
├── assets/                     # Identidade visual, logotipos SVG/PNG e favicons do projeto
│   ├── icons/                  # Ícones organizados em múltiplos formatos e resoluções
│   │   ├── favicon.svg         # Vetor SVG de alta definição (512x512)
│   │   ├── favicon.png         # Ícone principal PNG (512x512)
│   │   ├── favicon-192.png     # Variante PWA / Android (192x192)
│   │   ├── favicon-32.png      # Ícone para guias desktop (32x32)
│   │   ├── favicon-16.png      # Ícone compacto (16x16)
│   │   ├── apple-touch-icon.png # Ícone para iOS Safari / Apple Home Screen (180x180)
│   │   └── favicon.ico         # Ícone multi-resolução para navegadores
│   └── README.md               # Especificações técnicas de branding e tokens de cor
├── examples/                   # Dados de exemplo e templates de referência
│   ├── sample_lattes.xml       # Arquivo XML de teste padrão CNPq
│   ├── sample_photo.png        # Foto neutra de perfil para testes
│   ├── custom_template_example.tex # Exemplo de template .tex customizado
│   ├── custom_template_example.pdf # PDF de referência compilado
│   └── README.md               # Guia de utilização dos arquivos de exemplo
├── scripts/                    # Scripts utilitários de manutenção e geração
│   ├── generate_direct_resume.py # Gerador direto determinístico sem IA (Zero-Token)
│   ├── generate_icons.py       # Gerador dos ícones e favicons oficiais
│   ├── clean_artifacts.py      # Script de limpeza de resíduos temporários e caches
│   └── README.md               # Documentação dos scripts utilitários
├── src/                        # Pacote central da aplicação
│   ├── _vault.py               # Enclave criptográfico em memória RAM (ENC_PAYLOAD_V1 / SECKEY_V1)
│   ├── compiler.py             # Validação e compilação LaTeX segura com pdflatex
│   ├── config.py               # Constantes, diretórios e configurações de provedores de IA
│   ├── direct_builder.py       # Construtor determinístico direto (0 tokens) a partir dos extratores
│   ├── extractors.py           # Parsers multi-fonte (GitHub, Google Scholar, ORCID, Lattes, LinkedIn, Portfólio)
│   ├── i18n.py                 # Dicionários de internacionalização (pt-BR e en-US)
│   ├── llm_client.py           # Cliente orquestrador multi-provedor (NVIDIA, Gemini, Claude, OpenAI, DeepSeek)
│   ├── nvidia_client.py        # Adaptador de compatibilidade NVIDIA NIM
│   ├── pipeline.py             # Pipeline completo de síntese e compilação
│   ├── templates.py            # 10 modelos LaTeX integrados e suporte a templates customizados
│   ├── token_plugins.py        # Plugins de economia de tokens (Caveman, TOON, ShortKey, Cache)
│   ├── ui_theme.py             # Temas visuais e CSS responsivo para Streamlit
│   ├── py.typed                # Marcador PEP 561 de tipagem estática
│   └── README.md               # Documentação detalhada da arquitetura de módulos
├── tests/                      # Suíte de testes automatizados com Pytest (214+ testes com 100% de aprovação)
│   ├── conftest.py             # Configurações globais e fixtures compartilhadas do Pytest
│   ├── test_academic_mode_and_colors.py # Testes de modo acadêmico, seções e cores personalizadas
│   ├── test_awards_and_orcid.py# Higienização de prêmios, exclusão de bolsas redundantes e ORCID
│   ├── test_chronological_ordering_and_deduplication.py # Ordenação cronológica e deduplicação
│   ├── test_direct_builder.py  # Testes do modo direto offline (0 tokens) e revisão cirúrgica
│   ├── test_encrypted_comm.py  # Criptografia ponta a ponta AES-256-GCM e blindagem anti-extração
│   ├── test_english_standardization_and_dedup.py # Padronização em inglês e tradução consistente
│   ├── test_experience_nouns_and_email.py # Validação de substantivos de cargo e formato de email
│   ├── test_generation_resilience_and_ui_polish.py # Resiliência de pipeline e polimento de UI
│   ├── test_latex_formatting.py# Formatação LaTeX, auditoria de segurança e reparo automático
│   ├── test_manual_input_mode.py # Modo duplo de entrada (importação vs manual estruturado)
│   ├── test_platform_display.py# Exibição elegante de handles e identificadores sociais/acadêmicos
│   ├── test_projects_enrichment.py # Enriquecimento de stack e links de projetos
│   ├── test_scholar_and_publications.py # Fusão inteligente de artigos entre Scholar, ORCID e Lattes
│   ├── test_single_page_template.py # Compilação estrita em 1 página (Google, Tech Sidebar, Minimal ATS, Keywords)
│   ├── test_ui_assets.py       # Integridade de ícones, favicons, responsividade e acessibilidade
│   ├── test_zero_storage.py    # Garantia de Zero-Storage, sobrescrita binária 0x00 e memória volátil
│   └── README.md               # Documentação detalhada dos 16 módulos de teste e invariantes
├── app.py                      # Interface gráfica interativa em Streamlit
├── server.py                   # Servidor backend de API (Flask / Gunicorn) para GitHub Pages e Render
├── cli.py                      # Interface de linha de comando (CLI)
├── index.html                  # Interface gráfica web nativa para GitHub Pages e servidor local
├── pyproject.toml              # Metadados do projeto, entrypoints CLI, linters e Pytest
├── requirements.txt            # Dependências Python para pip
├── Dockerfile                  # Container Docker de produção com TeX Live e pdflatex
├── render.yaml                 # Especificação de infraestrutura como código para o Render
├── .gitignore                  # Regras estritas de exclusão de artefatos, chaves e caches
├── .dockerignore              # Exclusões para build enxuto do container Docker
└── README.md                   # Documentação completa em Português e Inglês
```

### 🚀 Publicação no GitHub, GitHub Pages e Backend no Render

O projeto foi arquitetado para separação segura entre Frontend Estático (GitHub Pages) e Backend de Compilação (Render):

```mermaid
flowchart LR
    A["🌐 Frontend Web Oficial<br>(https://jluckmay.github.io/latex-resume/)"] -- "1. POST /api/generate<br>(Origin: https://jluckmay.github.io<br>+ Envelope SECKEY_V1 Opcional)" --> B["🛡️ Backend no Render<br>(Docker + pdflatex + Gunicorn)"]
    B -- "2. Síntese com Economia de Tokens<br>(TLS 1.3 + Zero-Storage Vault)" --> C["⚡ Motor de IA Multi-Provedor<br>(NVIDIA NIM / Gemini / Claude / OpenAI / DeepSeek)"]
    C -- "3. JSON Estruturado / TOON" --> B
    B -- "4. Compilação LaTeX Segura<br>(-no-shell-escape + openin_any=p)" --> B
    B -- "5. PDF Compilado (Base64) + X-Backend-Attestation" --> A
```

#### 1. Hospedagem do Frontend no GitHub Pages (`https://jluckmay.github.io/latex-resume/`)
- Ao fazer push para a branch `main`, o GitHub Actions (`.github/workflows/deploy-pages.yml`) publica automaticamente a interface web (`index.html`) no GitHub Pages.
- O frontend aplica **Content Security Policy (CSP)** estrita e cabeçalhos de atestação de cliente (`X-Resume-Client: jluckmay-github-pages-v1`).

#### 2. Criação do Backend no Render (`Dockerfile` + `render.yaml`)
1. No painel do [Render](https://dashboard.render.com/), selecione **New +** -> **Blueprint** e conecte o repositório do GitHub (ou crie um **Web Service** selecionando runtime **Docker**).
2. O arquivo `render.yaml` configura automaticamente o serviço web com o `Dockerfile` (que inclui TeX Live completo com `pdflatex` e pacotes tipográficos).
3. Na aba **Environment** do serviço no Render, defina a variável de ambiente:
   - `NVIDIA_API_KEY`: sua chave de API da NVIDIA (`nvapi-...`).
4. O backend expõe o endpoint de monitoramento de saúde `/healthz`.

#### 3. Bloqueio Estrito de Conexão Mútua (Exclusivo para `https://jluckmay.github.io/`)
- O backend (`server.py`) rejeita **qualquer conexão** cuja origem ou `Referer` não provenha de `https://jluckmay.github.io/` (retornando `403 Forbidden`).
- **Chamada direta a partir da página autorizada**:
  Qualquer script hospedado em `https://jluckmay.github.io/` pode solicitar a criação de currículos diretamente via `fetch`:
  ```javascript
  const formData = new FormData();
  formData.append("resume_type", "profissional"); // ou "academico"
  formData.append("template_id", "google_standard"); // ou "ai_ats_max", "modern_pro", etc.
  formData.append("github", "octocat");
  formData.append("portfolio", "https://jluckmay.github.io/");

  const response = await fetch("https://<seu-servico-backend>.onrender.com/api/generate", {
    method: "POST",
    headers: {
      "X-Resume-Client": "jluckmay-github-pages-v1",
      "X-Client-Timestamp": Date.now().toString()
    },
    body: formData
  });
  const data = await response.json();
  // data.pdf_base64 contém o PDF gerado em base64
  ```

### 🔒 Auditoria de Segurança do Projeto & Correções Aplicadas

| Vulnerabilidade Auditada | Risco em Produção | Correção Aplicada |
| :--- | :--- | :--- |
| **Exposição da Chave em Repositório Público** | Bots/scrapers ou usuários extraírem a credencial do código, documentos ou commits do GitHub. | **Política Zero-Secret no Git & Cofre Efêmero Desacoplado**: O repositório Git, commits, documentos e arquivos distribuídos contêm **zero credenciais, zero shards e zero chaves embutidas**. A chave padrão da API é configurada exclusivamente no ambiente privado do backend no Render (`NVIDIA_API_KEY`), fora do Git. Ao iniciar, o `_vault.py` purga a variável de `os.environ` imediatamente (`os.environ.pop`), valida a atestação de chamada (`src/nvidia_client.py` e `src/llm_client.py`), despacha via TLS 1.3 puro e preenche buffers voláteis na memória RAM com zeros (`0x00`) em bloco `finally:`. Os usuários finais do GitHub Pages utilizam a compilação do backend sem jamais ter acesso ou capacidade de recuperar a chave da API. Chaves próprias informadas na interface web trafegam criptografadas com Web Crypto AES-256-GCM (`SECKEY_V1`) e são igualmente destruídas em RAM após a geração. Para uso local independente, as chaves podem ser informadas pelo usuário via variáveis de ambiente, parâmetro `--api-key` ou na interface. |
| **Execução Arbitrária de Código LaTeX (RCE)** | Primitivas `\write18` ou `\directlua` em templates customizados. | **Sanitização Prévia + Isolamento TeX**: bloqueio por regex de comandos do sistema (`\write18`, `\csname`, `\catcode`, `\input{/`). Execução do `pdflatex` com `-no-shell-escape`, ambiente de subprocesso higienizado e parâmetros Web2C `openin_any=p` e `openout_any=p` (impede leitura/escrita de arquivos fora do diretório de compilação). |
| **SSRF (Server-Side Request Forgery)** | Usuário informar URLs de metadados AWS/GCP (`169.254.169.254`) ou rede interna (`127.0.0.1`, `10.0.0.0/8`). | **Validador de IP Público (`_safe_http_get`)**: resolução DNS com verificação `ip.is_global == True`. Bloqueio de loopback, ranges privados e link-local, além de limite de download de 1.5 MB e validação de redirecionamentos. |
| **ZIP Bomb / XXE Bomb (Billion Laughs)** | Upload de ZIP malicioso ou XML com entidades recursivas do Lattes. | Limite estrito de descompressão (15 MB), bloqueio de declarações `<!DOCTYPE` e `<!ENTITY` antes de invocar o parser XML, e limite de 25 MP para fotos com Pillow (`Image.MAX_IMAGE_PIXELS`). |
| **Acesso Não Autorizado ao Backend** | Terceiros usarem o backend no Render para consumir créditos da API. | **Bloqueio Estrito de Origem e Referer**: CORS restrito exclusivamente a `https://jluckmay.github.io`, validação de cabeçalhos mútuos (`X-Resume-Client`, `X-Backend-Attestation`) e Rate Limiting em memória por IP (máx. 15 gerações / 10 min). |
| **Interceptação e Eavesdropping de Rede** | Sniffing de pacotes ou inspeção na aba Network do DevTools expondo currículos, dados pessoais ou credenciais em trânsito. | **Criptografia Bidirecional de Ponta a Ponta (`ENC_PAYLOAD_V1`)**: toda a comunicação entre o frontend (`index.html`) e o backend (`server.py`) trafega cifrada via envelope **AES-256-GCM** com vetor de inicialização aleatório e chave derivada dinamicamente por timestamp (`crypto.subtle`). Qualquer ferramenta de inspeção de rede (DevTools, Wireshark, proxies) visualiza estritamente texto cifrado (`ciphertext`), tornando ilegível e inacessível qualquer dado em trânsito. |
| **Tentativa de Extração de Chaves via Console / Probing** | Usuários executarem scripts no Console do navegador (`window.apiKey`, `fetch('/api/status')`) ou ferramentas (curl/Postman) para recuperar a chave padrão de API do servidor. | **Blindagem de Console & Defesa Zero-Leak**: A chave padrão do servidor reside exclusivamente em memória volátil de backend (Render Enclave) e **nunca** é transmitida ao cliente em nenhuma circunstância. O endpoint `/api/status` é sanitizado expurgando qualquer nome de variável (`env_vars`). Todos os endpoints e tratadores de erro (`400`, `403`, `404`, `500`) passam pelo filtro recursivo `scrub_sensitive_api_keys`, que detecta e substitui qualquer padrão de chave ou segredo ativo por `[REDACTED_API_KEY]`. No frontend, o escopo `window` possui propriedades congeladas (`window.apiKey = undefined`), impedindo exfiltração via console. |

### 🧠 Provedores de IA Suportados & Seleção de Modelos

O gerador suporta múltiplos provedores de inteligência artificial de ponta, permitindo o uso da infraestrutura padrão do servidor ou chaves de API próprias fornecidas pelo usuário:

| Provedor | Modelo Primário Recomendado | Modelos Alternativos / Fallbacks | Características Principais |
| :--- | :--- | :--- | :--- |
| **NVIDIA NIM** *(Padrão / Chave)* | `nvidia/nemotron-3.5-super-vl-120b-a12b` | `stepfun-ai/step-5-preview`, `google/gemma-4-31b-it`, `z-ai/glm-5.3` | 120B MoE (12B ativos), latência < 1.0s, suporte a `enable_thinking: False` (0 tokens ocultos). Padrão do backend. |
| **Google Gemini** *(Chave própria)* | `gemini-2.5-flash` | `gemini-2.5-pro`, `gemini-1.5-pro`, `gemini-1.5-flash` | Altíssima velocidade, raciocínio aprimorado, conformidade estrita com schemas JSON estruturados. |
| **Anthropic Claude** *(Chave própria)* | `claude-3-7-sonnet-20250219` | `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022` | Síntese de perfil executivo e acadêmico impecável, alta precisão textual e vocabulário formal polido. |
| **OpenAI** *(Chave própria)* | `gpt-4o` | `gpt-4o-mini`, `o3-mini`, `gpt-4-turbo` | Modelo emblemático multimodal, consistência determinística em bullet points XYZ e métricas de impacto. |
| **DeepSeek** *(Chave própria)* | `deepseek-chat` (DeepSeek V3) | `deepseek-reasoner` (DeepSeek R1) | Excelente relação custo-benefício, forte desempenho em codificação técnica e resumo curricular estruturado. |

### Plugins de Economia de Tokens (`src/token_plugins.py`)

| Plugin | Função e Impacto na Economia de Tokens |
| :--- | :--- |
| **`CavemanPromptPlugin`** | Aplica diretivas da skill `caveman` (zero preâmbulo, zero cercas markdown, instruções ultra-densas) preservando 100% da qualidade formal (`pt-BR` ou `en-US`) nos textos do currículo (~65% de redução de verbosidade). |
| **`ThinkingSuppressionPlugin`** | Injeta `chat_template_kwargs={"enable_thinking": False}`, reduzindo o gasto com `reasoning_tokens` ocultos para **0 tokens**. |
| **`TOONContextPrunerPlugin`** | Converte os dados brutos de GitHub, ORCID, Lattes, LinkedIn e Portfólio para **TOON (Token-Oriented Object Notation)** e deduplica publicações localmente antes do envio à API. |
| **`ShortKeySchemaPlugin`** | Solicita chaves JSON de 1–2 caracteres (`nm`, `tl`, `xp`, `ed`, `pb`, `sk`) na saída do LLM e expande localmente em Python (~40% menos tokens estruturais). |
| **`LaTeXPreambleSplitPlugin`** | Em templates `.tex` customizados, separa o preâmbulo estático (`\documentclass`...`\begin{document}`) do corpo, evitando que o LLM consuma tokens lendo e reescrevendo pacotes e macros. |
| **`SHA256DiskCachePlugin`** | Cache local por hash SHA-256 em `.cache/nvidia_token_cache.json` (custo de **0 tokens** em reexecuções idênticas). |

### 💻 Guia Completo de Execução Local (`pt-BR`)

Você pode executar o gerador e compilar seus currículos inteiramente na sua máquina local, com máxima velocidade, privacidade e sem necessidade de deploy prévio:

#### 1. Preparação do Ambiente Local
```powershell
# 1. Clonar o repositório
git clone https://github.com/Jluckmay/resume-generator.git
cd resume-generator

# 2. Criar e ativar ambiente virtual Python (recomendado)
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# 3. Instalar dependências Python
pip install -r requirements.txt

# 4. Validar compilador LaTeX instalado
python cli.py --lang pt-br --check-deps
```

#### 2. Configuração de Chaves de API (Multi-Provedor)
Defina a chave de API do provedor desejado no terminal antes da execução (ou informe-a interativamente/via interface gráfica, sem gravação em disco):
```powershell
# NVIDIA NIM (Padrão para execução local com NVIDIA):
$env:NVIDIA_API_KEY = "nvapi-sua-chave-aqui"

# Google Gemini:
$env:GEMINI_API_KEY = "AIzaSy-sua-chave-aqui"

# Anthropic Claude:
$env:ANTHROPIC_API_KEY = "sk-ant-sua-chave-aqui"

# OpenAI:
$env:OPENAI_API_KEY = "sk-sua-chave-aqui"

# DeepSeek:
$env:DEEPSEEK_API_KEY = "sk-sua-chave-aqui"
```
*(No Linux ou macOS, substitua `$env:NOME = "..."` por `export NOME="..."`)*

#### 3. Modos de Execução Disponíveis

##### Modo A: Servidor Web HTML5 Nativo (`server.py`) — Recomendado
Inicia o servidor de compilação local com a interface web estática integrada:
```powershell
python server.py
```
- Acesse no navegador: `http://127.0.0.1:5000`
- O servidor roda em modo de desenvolvimento local com compilação direta via `pdflatex` da sua máquina, sem latência de rede.
- Suporta alternância dinâmica de provedores e inserção de chave de API própria com criptografia Web Crypto AES-256-GCM.

##### Modo B: Interface Interativa Streamlit (`app.py`)
Inicia a interface visual rica do Streamlit com alternância de temas claro/escuro e preview instantâneo:
```powershell
streamlit run app.py
```
- Acesse no navegador: `http://localhost:8501`
- Possui seletor lateral de provedor (`NVIDIA`, `Google`, `Claude`, `OpenAI`, `DeepSeek`), modelos correspondentes, campo de chave segura e prévia interativa dos 9 modelos LaTeX.

##### Modo C: Linha de Comando / CLI (`cli.py`)
Geração rápida e automatizada via terminal, com suporte a seleção de provedores:
```powershell
# Listar todos os provedores e modelos suportados:
python cli.py --list-providers

# Exemplo 1: Currículo Padrão Google com o provedor padrão (NVIDIA NIM)
python cli.py --lang pt-br --type profissional --template google_standard --github octocat --linkedin "https://linkedin.com/in/exemplo" --portfolio "https://jluckmay.github.io/" --output cv_google

# Exemplo 2: Currículo Otimizado para IA & ATS usando Google Gemini (chave lida de $env:GEMINI_API_KEY)
python cli.py --lang pt-br --type profissional --template ai_ats_max --provider google --github octocat --primary-color "#0F4C81" --secondary-color "#1E293B" --output cv_gemini

# Exemplo 3: Currículo Acadêmico usando Anthropic Claude com chave via parâmetro seguro
python cli.py --lang pt-br --type academic --template academic_classic --provider claude --api-key "sk-ant-..." --orcid 0000-0002-1825-0097 --lattes-file examples/sample_lattes.xml --output cv_claude

# Exemplo 4: Currículo usando OpenAI informando a chave via prompt oculto no terminal
python cli.py --lang pt-br --type profissional --template modern_pro --provider openai --github octocat --output cv_openai
```

##### Modo D: Modo Offline Sem IA (Zero-Token) & Modo de Revisão Cirúrgica
Gere currículos instantaneamente sem gastar tokens ou utilize a IA estritamente para revisão de estilo:
```powershell
# 1. Geração direta 100% determinística sem IA (0 tokens) via CLI:
python cli.py --lang pt-br --type profissional --template google_standard --github octocat --no-ai --output cv_offline

# 2. Geração direta via script utilitário dedicado:
python scripts/generate_direct_resume.py --lang pt-br --template modern_pro --github octocat --lattes-file examples/sample_lattes.xml --output cv_direto

# 3. Modo apenas revisão (gera esqueleto direto e envia apenas o corpo à IA, economizando ~75% dos tokens):
python cli.py --lang pt-br --type profissional --template ai_ats_max --github octocat --review-only --output cv_revisado
```

### 🌐 Guia de Uso da Aplicação Web Online (`https://github.com/Jluckmay/resume-generator`)

A aplicação web pode ser utilizada diretamente pela nuvem através do GitHub Pages e do backend no Render:

#### 1. Acesso à Aplicação Web
- **Repositório Oficial:** [`https://github.com/Jluckmay/resume-generator`](https://github.com/Jluckmay/resume-generator)
- **Página Web Oficial (GitHub Pages):** [`https://jluckmay.github.io/resume-generator/`](https://jluckmay.github.io/resume-generator/) (ou integrada via [`https://jluckmay.github.io/`](https://jluckmay.github.io/))

#### 2. Conectando a Interface Web ao Backend no Render
1. Abra a página web oficial no navegador.
2. No painel de configurações (ícone de engrenagem ou rodapé), verifique o campo **URL do Backend (Render)**:
   - O frontend conecta-se automaticamente ao servidor Render padrão através de um enclave protegido e ofuscado em runtime (ou você pode configurar a URL do seu próprio serviço no Render: `https://<seu-servico>.onrender.com` ou servidor local: `http://127.0.0.1:5000`).
3. A interface verifica automaticamente a saúde do serviço (`/healthz`) e a disponibilidade do compilador LaTeX (`/api/status`), considerando o tempo de despertar de instâncias gratuitas no Render (~30 a 50s) com retentativas automáticas, indicador visual pulsante e retentativas transparentes na compilação, exibindo o selo verde com a versão do TeX Live.
4. **Modo Apenas Revisão Habilitado por Padrão**: O "Modo Apenas Revisão (~75% de Economia de Tokens)" já vem ativado por padrão nas interfaces web e local, gerando primeiro o currículo determinístico via extratores e acionando o modelo de IA estritamente para refinamento e polimento textual.

#### 3. Chaves de API Próprias Opcionais & Criptografia Efêmera (Zero-Storage)
O projeto permite que os usuários utilizem a chave padrão do servidor ou utilizem **suas próprias chaves de API de forma opcional**, com suporte multi-provedor:
- **⚡ NVIDIA NIM (Padrão do Servidor)**: utiliza a credencial do servidor seguro, sem necessidade de chave do usuário.
- **🟢 NVIDIA NIM (Chave própria)**: `nvapi-...`
- **🔵 Google Gemini (Chave própria)**: `AIzaSy...` (Gemini 2.0 Flash, 1.5 Pro, 1.5 Flash)
- **🟣 Anthropic Claude (Chave própria)**: `sk-ant-...` (Claude 3.5 Sonnet, 3.5 Haiku)
- **🟢 OpenAI (Chave própria)**: `sk-...` (GPT-4o, GPT-4o Mini, o3-mini)
- **🔷 DeepSeek (Chave própria)**: `sk-...` (DeepSeek V3, DeepSeek R1)

##### Protocolo de Proteção e Ofuscação Criptográfica:
1. **Criptografia no Navegador (`SECKEY_V1`):** Ao inserir uma chave própria na interface web, ela é criptografada e ofuscada em tempo real via **Web Crypto API (AES-256-GCM)** com vetor de inicialização aleatório e chave efêmera derivada do timestamp (`SECKEY_V1:...`). A chave em texto plano **nunca** trafega exposta e **nunca** é gravada em `localStorage`, `sessionStorage`, cookies ou logs.
2. **Isolamento Estrito em Memória RAM (`src/_vault.py`):** No backend e em execuções locais, o envelope criptográfico é aberto exclusivamente em memória volátil RAM em buffers `bytearray`.
3. **Zeroização Imediata (Zero-Storage):** Após o disparo da requisição via TLS 1.3 puro com pinning de certificado, o buffer de memória é imediatamente sobrescrito com bytes nulos (`0x00`) no bloco `finally`, e as variáveis de ambiente (`NVIDIA_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`) são expurgadas com `os.environ.pop` para impedir que processos-filhos (como o `pdflatex`) tenham acesso a qualquer credencial.

#### 4. Passo a Passo para Geração do Currículo
1. **Dados Pessoais e Modo de Entrada**: Preencha nome, cargo, e-mail, telefone, localização (com link clicável para o Google Maps) e escolha entre:
   - **Importar Informações**: informe links ou envie arquivos de perfis online (GitHub, LinkedIn, ORCID, Lattes, Portfólio Web, Foto).
   - **Inserir Manualmente**: preencha diretamente seus dados estruturados (resumo, formação, experiência, competências, projetos, idiomas, prêmios e publicações).
2. **Escolha do Provedor de IA e Modelo**: Selecione o provedor desejado (NVIDIA Padrão, NVIDIA Própria, Google Gemini, Anthropic Claude, OpenAI ou DeepSeek) e o modelo otimizado correspondente. Se desejar, informe sua chave própria com total segurança criptográfica.
3. **Escolha do Modelo LaTeX**: Selecione um dos 10 templates disponíveis:
   - **`ai_ats_max`**: Otimizado para triagem por IA (Claude/Gemini/GPT) e robôs ATS neurais (Padrão da Interface).
   - **`google_standard`**: Padrão Google SWE (bullet points XYZ de impacto, alta densidade).
   - **`overleaf_russell_ti`**: Modelo Russell com foto lateral, ícones e barra de habilidades.
   - **`overleaf_awesome_cv`**: Awesome CV com cabeçalho centralizado e rodapé executivo.
   - **`overleaf_single_page_keywords`**: Single Page + Keywords com linha de stack técnica por cargo.
   - **`nico_krieger`**: Modelo Nico Krieger com cabeçalho escuro de largura total e barra lateral de habilidades em 5 pontos.
   - **`modern_pro`**, **`academic_classic`**, **`tech_sidebar`**, **`minimal_ats`** ou seu próprio arquivo `.tex`.
4. **Customização de Cores**: Escolha uma paleta executiva ou insira seus códigos HEX para a Cor Principal e Secundária.
5. **Gerar**: Clique no botão **"Gerar Currículo"**.
6. **Visualização e Download**: O PDF compilado é exibido diretamente no visualizador embutido da página, com opção para copiar o código LaTeX fonte ou baixar o arquivo `.pdf` gerado.

#### 5. Restrição Estrita de Comunicação
Por medidas de segurança, o backend no Render aceita conexões e compilações **exclusivamente** da origem:
- `https://jluckmay.github.io/`

Qualquer solicitação proveniente de outros sites, domínios ou scrapers é automaticamente bloqueada com status `403 Forbidden`.

---

### 📄 Licença

Este projeto é distribuído sob a [Licença MIT](LICENSE).

Copyright (c) 2026 João Lucas Mayrinck.
