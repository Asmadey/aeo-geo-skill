# Answer Engine Optimization (AEO) & Generative Engine Optimization (GEO)

> **The Definitive Autonomous Agent Skill & Engineering Framework for AI Search Visibility (2026 Edition)**  
> *Engineered for ChatGPT Instant (`labrador`), ChatGPT Thinking / Atlas, Perplexity, Google AI Overviews, and Gemini.*

[![Standard](https://img.shields.io/badge/Standard-Agent%20Skills%201.0-blue.svg)]()
[![Python](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)]()
[![Architecture](https://img.shields.io/badge/Architecture-Stdlib%20Only%20(Zero%20Dependency)-success.svg)]()
[![Research](https://img.shields.io/badge/Knowledge%20Base-247%20SearchEngineLand%20Studies-orange.svg)]()
[![Playbook](https://img.shields.io/badge/Playbook-21%20Priorities%20%7C%20140%2B%20Techniques-purple.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()

---

## 🎯 Executive Overview

**Answer Engine Optimization (AEO)** and **Generative Engine Optimization (GEO)** represent a paradigm shift from traditional search engine optimization. Rather than competing for 10 blue links on a results page, AEO/GEO is the disciplined discipline of engineering content, technical infrastructure, semantic accessibility, and third-party consensus so that **autonomous AI retrieval models directly extract, cite, and attribute your brand in synthesized answers.**

This repository is an **exhaustive knowledge base and executable tool suite** synthesized from **247 empirical research studies published by [SearchEngineLand](https://searchengineland.com/) (August 2026)**, encompassing **21 strategic priorities and 140+ concrete technical mechanisms**.

### Why This Framework is Radically Different
Traditional SEO relies on crawling full HTML pages, calculating PageRank, and optimizing for 60-character meta tags. In contrast, modern AI search engines operate on multi-tiered, asynchronous retrieval architectures:
- **OpenAI strips all JSON-LD schemas** when converting crawled HTML into its internal Markdown Reading Cache. If your structured facts are not embedded in visible copy and image `alt` attributes, the model never sees them.
- **OpenAI’s `labrador` discovery index** preserves titles up to **289 characters** (vs. 60–75 in Google/Bing). Short titles waste critical dense semantic retrieval opportunities.
- **Google utilizes an Image-First Matching retrieval pipeline** (published patent, 2026): it matches user intent to image embeddings first, then pulls surrounding text blocks into Google AI Overviews.
- **Autonomous browser agents (ChatGPT Atlas, WebMCP, Playwright)** do not parse visual pixels or raw DOMs; they navigate websites via the **Accessibility Tree** (ARIA landmarks, roles, and accessible names).
- **Over 40% of AI citations suffer from "Ghost Citations"**: the model extracts your factual data or benchmark, but drops your brand attribution entirely unless syntactically bound.
- **22.4% of AI search referrals are hidden in GA4 Dark Funnel** (misclassified as `Direct / None`), detectable only through URL Scroll-to-Text Fragments (`#:~:text=`).

This framework elevates AI search optimization from speculative keyword stuffing to **rigorous software and information engineering**.

---

## 🏗️ The 5-Phase Launch & Refresh Lifecycle

The framework follows a proven, 5-phase operational pipeline designed to take any digital property from day zero to category-dominant citation share:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 0: Field Selection & Funnel Research (Days 1–7)                      │
│  - Unowned category discovery (53.7% of AI search demand has no topic owner)│
│  - Full-funnel query mapping: ToFU (Discovery), MoFU (Comparison), BoFU     │
│  - Competitor benchmark asset gap analysis & prompt formulation             │
├─────────────────────────────────────────────────────────────────────────────┤
│  PHASE 1: Technical Foundation, Cache & Accessibility (Weeks 1–2)           │
│  - Raw HTML payload optimization (< 4 MB payload constraint)                │
│  - Accessibility Tree structuring (<main>, <article>, ARIA landmarks)       │
│  - AI bot permissions (GPTBot, ClaudeBot, PerplexityBot) & robots.txt       │
│  - Domain-root semantic mapping via standard llms.txt & llms-full.txt       │
├─────────────────────────────────────────────────────────────────────────────┤
│  PHASE 2: Passage Architecture & Multimodal Engineering (Weeks 2–4)         │
│  - Labrador H1 Title engineering (self-contained, entity-rich sentence)     │
│  - ChatGPT Instant 200-char grounding lede immediately below H1            │
│  - 117-word atomic passage modularization (question H2s, zero cross-refs)   │
│  - Multimodal image denotation & fact-rich alt attributes                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  PHASE 3: Production, 3-Agent Gate & Brand Binding (Weeks 3–10)             │
│  - In-sentence syntactic brand binding to prevent Ghost Citations           │
│  - Proprietary named asset creation (Indexes, Benchmarks, Frameworks)       │
│  - 3-Agent Verification Gate: Editor, Fact-Checker, Anti-AI-Tells Auditor   │
├─────────────────────────────────────────────────────────────────────────────┤
│  PHASE 4: 85% Third-Party Earned Footprint & Dark Funnel (Weeks 4–12+)      │
│  - Reddit authority engineering (mining 35M+ AI Overview triggering terms)  │
│  - YouTube long-form transcript seeding & authoritative review aggregators  │
│  - GA4 Text Fragment tracking (#:~:text=) to recover 22.4% Dark Funnel      │
├─────────────────────────────────────────────────────────────────────────────┤
│  PHASE 5: 56-Day GSC Refresh Matrix & 4-State Monitoring (Continuous)       │
│  - 56-Day GSC baseline tracking & 3-Step Page Independence Testing          │
│  - Keep / Fix / Remove (301) / Add protocol (zero URL history disruption)   │
│  - Continuous 4-state citation ledger (both / ghost / mention / neither)    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔬 Core Engineering Techniques: Priorities #12 – #21

Below is a detailed engineering breakdown of the latest core technical priorities from the August 2026 SearchEngineLand Playbook V2, detailing the internal mechanics of search engines and AI agents:

| Priority # | Priority Name | Techniques | Core Technical Discovery & Mechanism | Operational Implementation & Tooling |
|:---|:---|:---:|:---|:---|
| **#12** | **ChatGPT Retrieval Internals** | **8 Techniques** | **3-Tier Architecture:** (1) Discovery index (`labrador`), (2) Reading cache (Markdown), (3) Live opens (`ChatGPT-User`). Only 1.5% of `labrador` URLs match Bing top-20. Instant mode (~90% users) synthesizes answers solely from title + first 200 chars without opening the page. Thinking mode opens live pages (74% citation rate for opened pages vs. 7% for unopened). **Reading Cache:** strips scripts, iframes, and JSON-LD; preserves alt-text; caches for up to 30 days. `labrador` supports up to 289-character titles. | • Formulate complete-sentence H1 titles (up to 250 chars) via `aeo_optimizer.py`.<br>• Eliminate navigation noise in the first 200 characters below H1.<br>• Never rely solely on JSON-LD; replicate entities in visible text and image `alt` attributes.<br>• Force cache refresh using `Last-Modified` headers and IndexNow pings.<br>• Reference: `references/openai_markdown_cache_and_rendering.md`. |
| **#13** | **Accessibility Tree for AI Agents** | **4 Techniques** | **Agent DOM Navigation:** Autonomous AI agents (ChatGPT Atlas, WebMCP, Microsoft Playwright MCP) do not process raw CSS pixels or full DOM trees. Instead, they navigate websites through the **Accessibility Tree** (the semantic ARIA abstraction layer constructed by the browser). If a conversion button or critical fact lacks an accessible name or role, AI agents fail to perceive or interact with it. | • Implement `<main>`, `<article>`, `<nav>`, `<aside>` landmark hierarchy.<br>• Enforce explicit accessible names (`aria-label`, button text) without vague anchors like *"click here"*.<br>• Integrate AXray / Playwright accessibility snapshots into CI/CD for automated regression diffs.<br>• Reference: `references/accessibility_tree_for_ai_agents.md`. |
| **#14** | **Multimodal Image GEO** | **3 Techniques** | **Image as Retrieval Doorway:** 20 billion Google Lens searches/month. In April 2026, Google published a core patent detailing **Image-First Matching**: retrieval algorithms match queries to image visual embeddings first, and then extract surrounding textual passages to build the AI Overview. Stock photos are ignored; denotative images (diagrams, workflows, charts) dominate. | • Perform Co-Occurrence Visual Audits (Denotation vs. Connotation).<br>• Embed machine-readable infographic data directly into visible text and image `alt` attributes.<br>• Tailor visual assets per page type (OCR-legible packaging on product pages, architecture schematics on technical blogs).<br>• Reference: `references/multimodal_image_geo.md`. |
| **#15** | **Local SEO for AI Search** | **8 Techniques** | **Local 5.0 Context Intelligence:** AI shifts verification burden from user to model. In local search, ~60% of Gemini citations link to primary business websites, while Reddit is #2 (13.7%), beating all directory aggregators. **Grounding Drift:** repeated identical queries yield source overlap only ~40% of the time (vs. 90% for local packs). In 1.8M Google Business Profiles, specific subcategories boost rankings by +17 positions, while address changes create historical algorithmic ghost penalties. | • Build Context Memory Graphs (location data + customer reviews + intent).<br>• Digitize real-time local product inventories via GBP Products for agentic purchase bots.<br>• Validate physical coordinates using Google Geocoding API before submitting GBP address changes.<br>• Apply the Query Deserves a Page (QDP) topical authority framework.<br>• Reference: `references/aeo_eeat_canon.md`. |
| **#16** | **Reddit Strategies for AI Visibility** | **3 Techniques** | **Third-Party Consensus Engine:** Reddit ranks for ~166M keywords, with 35M+ queries triggering AI Overviews (where Reddit is cited in 15M+ cases, a 46% citation rate). However, Reddit share in ChatGPT citations dropped by 86% over a 4-day span during retrieval fan-out tuning, proving extreme platform volatility. | • Mine high-yield AI Overview topics using Semrush Keyword Gap against `reddit.com`.<br>• Implement the 5-Step Reddit Authority Framework (e.g., Kumon case study: 5% → 18.13% ChatGPT visibility).<br>• Track citations on a per-platform basis to hedge against platform volatility.<br>• Reference: `references/third_party_ugc_footprint.md`. |
| **#17** | **MCP Servers and AI Tooling** | **3 Techniques** | **Model Context Protocol (MCP):** Connects AI agents directly to live search and marketing data layers (Semrush MCP, Ahrefs, DataForSEO, GSC). Chaining multiple tools allows agents to bypass traditional export limits (e.g., GA4 5,000-row limit) to instantly correlate traffic drops with SERP shifts. Density-based clustering algorithms (TF-IDF + HDBSCAN) group 12,000+ keywords into semantic topic clusters without arbitrary cluster counts. | • Connect command-line agents to live SERP feeds via MCP servers.<br>• Execute data chaining pipelines: GA4 traffic drops + ranking drops → automated refresh brief.<br>• Cluster keyword maps using unsupervised Python density clustering (HDBSCAN).<br>• Reference: `references/api_configuration.md`. |
| **#18** | **AI Content Workflows** | **2 Techniques** | **7-Loop Self-Improving Pipeline:** (1) Upstream strategist filter, (2) Retrieval mapping, (3) Quality gate with 2-revision cap, (4) Rubric scoring, (5) Adversarial challenge agent, (6) Diff-and-learn agent (comparing published DOCX to raw markdown), (7) Weekly GSC performance feedback loop. Architected around separate, isolated context windows for each agent to achieve 95% publication readiness. | • Implement 3-Agent Review Gate: Editorial Style Agent, Adversarial Fact-Checker, and Anti-AI-Tells Detection Agent.<br>• Hardcode static brand constants (ICP, voice guidelines, verified facts) while keeping topic variables modular.<br>• Reference: `references/content_verification_pipeline.md`. |
| **#19** | **AI Search Behavioral Data** | **6 Techniques** | **Brand Favoritism & Memory Advantage:** AI models search for familiar brands **3.2× more frequently** (55.7% vs. 17.4%). 63% of brand-specific fan-out searches involve top-5 familiar brands. 88% of adult users accept AI Mode product recommendations as the "best" option. **53.7% of categories have no established topic owner**, representing open greenfield opportunities. Once earned, topic ownership exhibits extreme multi-month durability. | • Focus on category leadership to enter the model's top-5 parametric consideration set.<br>• Prioritize high-volume greenfield categories where no topic owner has locked in citation dominance.<br>• Optimize product landing pages directly (the most cited page type in AI search, accounting for >50% of citations).<br>• Reference: `references/llm_citation_patterns.md`. |
| **#20** | **AI Visibility as an Org Problem** | **3 Techniques** | **The Coordination Dilemma:** Because 82% to 85% of citations point to earned media (Reddit, YouTube, review sites, industry blogs), AI visibility cannot be solved within an isolated SEO silo. It requires cross-functional coordination across PR, social, product marketing, affiliate, and creator partnerships. Uncoordinated outreach leads to companies paying multiple times for the same creator relationship. | • Establish a centralized cross-functional AI Visibility council.<br>• Implement incremental attribution modeling for creator and review content (measuring causation, not mere affiliate participation).<br>• Align PR and SEO KPIs around third-party entity consensus metrics.<br>• Reference: `references/third_party_ugc_footprint.md`. |
| **#21** | **Google AI Overviews & AI Mode Dynamics** | **4 Techniques** | **Dynamic SERP Expansion & Zero-Click:** Google dynamically expands AI Overviews into full-page responses for complex queries, pushing organic blue links entirely below the fold. Trending topics trigger interactive Link Carousels. Across 51,200 tracked events, AI Overviews drove 7.53% of total organic sessions, with extreme Pareto distribution (top snippet drove 2,276 events vs. average of 31). Rollout of Gemini 3.7 Flash accelerates synthesis latency. | • Monitor trending topics to capture transient Link Carousel placements in AI Mode.<br>• Focus optimization on high-leverage atomic pages that represent top traffic nodes.<br>• Monitor AI Overview snippet lifecycles (peak and decay curves) to schedule timely content refreshes.<br>• Reference: `references/page_refresh_and_cannibalization.md`. |

---

## 🛠️ Executable Tool Suite (`scripts/`)

The repository includes a production-grade, modular CLI tool suite built entirely with the **Python Standard Library (`stdlib-only`)**. No external dependencies or virtual environments are required for full out-of-the-box operation.

```text
scripts/
├── aeo_audit.py          # Comprehensive E-E-A-T, Labrador Title & Image-Alt Auditor
├── aeo_optimizer.py      # Content Restructuring, Labrador Title & Brand-Binding Engine
├── citation_tracker.py   # 4-State Visibility Matrix & Ghost Citation Ratio Ledger
├── llms_txt_generator.py # Specification Builder & Validator for standard llms.txt
├── query_researcher.py   # Funnel Query Research & Dark Funnel (#:~:text=) Guide
├── report_generator.py   # Executive Deliverables, Diff Reports & Refresh Matrix
├── success_patterns.py   # Adaptive Semantic Pattern Library & Snippet Catalog
├── api_manager.py        # Optional External API Connector (OpenAI, Perplexity, Ahrefs)
└── utils.py              # Shared Parsing, Readability & HTML Extraction Utilities
```

### 1. Comprehensive Auditor (`aeo_audit.py`)
Scores content against the 5 E-E-A-T dimensions, the ChatGPT Instant 200-char grounding budget, Labrador title self-containment, image alt-text survival for Markdown caches, and passage independence:
```bash
# Audit local markdown article
python3 scripts/aeo_audit.py --input post.md --industry saas

# Audit live URL with JSON output
python3 scripts/aeo_audit.py --url https://example.com/guide --output json

# Run built-in sample audit
python3 scripts/aeo_audit.py --sample
```

### 2. Semantic Content Optimizer (`aeo_optimizer.py`)
Transforms raw text into citation-ready passages: expands H1 titles for OpenAI's `labrador` retriever (up to 250 characters), enriches image `alt` tags for Markdown Cache survival, injects Schema.org JSON-LD, formats question subheadings, and syntactically fuses facts to your brand:
```bash
# Optimize article in balanced mode with brand binding
python3 scripts/aeo_optimizer.py --input article.md --brand "CloudMetrics" --mode balanced --output article-aeo.md

# Conservative mode (touches <10% of text, adds schema & disclosure footers)
python3 scripts/aeo_optimizer.py --input article.md --mode conservative --output article-safe.md

# Test with built-in sample
python3 scripts/aeo_optimizer.py --sample --brand "AcmeCorp"
```

### 3. Visibility & Ghost Citation Tracker (`citation_tracker.py`)
Maintains an append-only ledger tracking query performance across the 4-state visibility matrix (`both`, `ghost`, `mention`, `neither`), calculating the crucial **Ghost Citation Ratio**:
```bash
# Log observed query result
python3 scripts/citation_tracker.py add --url https://example.com/post \
  --llm perplexity --query "best observability tools" --status both --brand "CloudMetrics"

# Generate URL visibility report
python3 scripts/citation_tracker.py report --url https://example.com/post

# View global summary across all tracked assets
python3 scripts/citation_tracker.py summary
```

### 4. `llms.txt` Builder & Validator (`llms_txt_generator.py`)
Generates and validates domain documentation according to the official `llms.txt` semantic standard:
```bash
# Generate tailored llms.txt from preset template (saas, publisher, docs, ecommerce)
python3 scripts/llms_txt_generator.py generate --template saas --name "CloudMetrics" --url "https://cloudmetrics.io"

# Validate existing llms.txt syntax and link formatting
python3 scripts/llms_txt_generator.py validate --file llms.txt

# Concatenate markdown files into full context bundle (llms-full.txt)
python3 scripts/llms_txt_generator.py dump --input-dir ./docs --output llms-full.txt
```

### 5. Funnel Query Researcher (`query_researcher.py`)
Maps high-probability citation prompts across the funnel (ToFU Discovery, MoFU Comparison, BoFU Vendor Decision) and generates GA4 Dark Funnel recovery directives:
```bash
# Analyze citation query targets
python3 scripts/query_researcher.py --topic "Enterprise Observability" --region US

# Analyze with competitors
python3 scripts/query_researcher.py --topic "Kubernetes Monitoring" --competitors "https://datadog.com,https://dynatrace.com"
```

### 6. Strategic Report & Refresh Generator (`report_generator.py`)
Generates executive dashboards, before/after optimization score diffs, and Keep / Fix / Remove / Add page refresh matrices:
```bash
# Generate executive summary from audit JSON
python3 scripts/report_generator.py --project "SaaS Migration" --audit-json audit.json --output executive_report.md

# Generate Keep / Fix / Remove / Add refresh matrix
python3 scripts/report_generator.py --project "Enterprise Portal" --refresh-matrix
```

---

## 📚 Specialized Knowledge Base (`references/`)

The repository contains 17 exhaustive reference manuals offering deep, progressive disclosure for every technical dimension:

| Guide File | Focus & Strategic Domain |
|:---|:---|
| [openai_markdown_cache_and_rendering.md](references/openai_markdown_cache_and_rendering.md) | OpenAI Markdown Cache mechanics, JSON-LD stripping, alt-text survival, 289-char Labrador titles, stale-while-revalidate. |
| [multimodal_image_geo.md](references/multimodal_image_geo.md) | Google Image-First Matching patent, 20B Google Lens queries, denotation vs. connotation visual co-occurrence audits. |
| [accessibility_tree_for_ai_agents.md](references/accessibility_tree_for_ai_agents.md) | Accessibility Tree optimization for AI browser agents (Atlas, WebMCP, Playwright), semantic landmarks, accessible names. |
| [page_refresh_and_cannibalization.md](references/page_refresh_and_cannibalization.md) | 56-day GSC baseline analysis, Keep/Fix/Remove/Add framework, 3-step Page Independence Test, URL history preservation. |
| [chatgpt_instant_vs_thinking.md](references/chatgpt_instant_vs_thinking.md) | Deep breakdown of OpenAI `labrador` index vs. `ChatGPT-User` live opens, 200-char post-H1 budget, `/en/` multiplier. |
| [third_party_ugc_footprint.md](references/third_party_ugc_footprint.md) | Engineering the 85% third-party consensus moat across Reddit, long-form YouTube, and verified review aggregators. |
| [anti_ghost_citation_guide.md](references/anti_ghost_citation_guide.md) | Syntactic in-sentence brand binding formulas, Named Indices, and proprietary benchmark asset design. |
| [content_verification_pipeline.md](references/content_verification_pipeline.md) | 3-Agent review gate (Editorial Agent, Fact-Checker, Anti-AI-Tells Auditor) to eliminate AI slop patterns. |
| [llms_txt_guide.md](references/llms_txt_guide.md) | Complete standard specification, file architecture, and production templates for `llms.txt` and `llms-full.txt`. |
| [geo_entity_optimization.md](references/geo_entity_optimization.md) | The 5-layer AI visibility stack and 12 proven semantic extraction block patterns. |
| [bot_access_and_monitoring.md](references/bot_access_and_monitoring.md) | Comprehensive AI crawler user-agent registry (`GPTBot`, `ClaudeBot`, `PerplexityBot`), robots.txt directives, and verification. |
| [extractable_content_patterns.md](references/extractable_content_patterns.md) | 7 copy-ready structural snippet templates optimized for high LLM extraction probability. |
| [llm_citation_patterns.md](references/llm_citation_patterns.md) | Specific ranking and citation heuristics of Perplexity, ChatGPT, Claude, and Google Gemini. |
| [aeo_eeat_canon.md](references/aeo_eeat_canon.md) | Rigorous algorithmic E-E-A-T scoring criteria, industry thresholds, and compliance guidelines. |
| [aeo_vs_seo.md](references/aeo_vs_seo.md) | Strategic resource allocation guide comparing traditional search algorithms and generative AI engines. |
| [success_patterns_guide.md](references/success_patterns_guide.md) | Operational guide for utilizing the adaptive semantic pattern library. |
| [api_configuration.md](references/api_configuration.md) | Configuration manual for optional external APIs (OpenAI, Anthropic, Gemini, Perplexity, Ahrefs, SEMrush). |

---

## 📋 Pre-Flight Publication Checklist

Before publishing or updating any digital asset, verify compliance against the operational checklist:

- [ ] **Technical Payload:** Raw HTML payload is `< 4 MB` (zero client-side JS link injection).
- [ ] **Labrador Title Self-Containment:** H1 title is an entity-dense, complete sentence (up to 250–289 characters) providing maximum dense retrieval signals.
- [ ] **ChatGPT Instant Grounding Budget:** First 200 characters immediately below H1 deliver a definitive, factual answer (zero navigation noise or breadcrumbs).
- [ ] **OpenAI Markdown Cache Survival:** All key factual claims, data points, and author credentials exist in visible text (never rely exclusively on JSON-LD).
- [ ] **Multimodal Image Denotation:** All imagery features informative diagrams or charts with descriptive, fact-rich `alt` text attributes.
- [ ] **Accessibility Tree Landmarks:** Correct semantic landmarks (`<main>`, `<article>`, `<nav>`, `<aside aria-label="disclaimer">`) with zero unlabelled interactive controls.
- [ ] **Passage Independence:** Every H2 section answers a single query completely and functions in isolation (zero cross-references like *"as mentioned above"*).
- [ ] **Anti-Ghost Citation Binding:** Key numerical data and benchmark findings are syntactically fused to the brand or a named proprietary study.
- [ ] **Comparison Matrices:** Comparative evaluations are formatted as standard native Markdown or HTML tables.
- [ ] **Dark Funnel Tracking:** GA4 configured with custom dimension capturing URL text fragments (`location.hash` containing `#:~:text=`).
- [ ] **URL Immutability:** Existing high-performing URLs maintain their original URL slug and primary H1 to preserve LLM retrieval history.
- [ ] **llms.txt:** Domain root serves a valid `llms.txt` referencing the new or updated asset.

---

## ⚡ Quick Start (5 Minutes)

```bash
# 1. Audit content readiness
python3 scripts/aeo_audit.py --input my_article.md --industry saas

# 2. Optimize passages and bind brand claims
python3 scripts/aeo_optimizer.py --input my_article.md --brand "MyBrand" --mode balanced --output my_article_aeo.md

# 3. Generate domain llms.txt
python3 scripts/llms_txt_generator.py generate --template saas --name "MyBrand" --url "https://mybrand.com"

# 4. Log citations in the 4-state ledger
python3 scripts/citation_tracker.py add --url https://mybrand.com/my_article \
  --llm perplexity --query "what is my topic" --status both --brand "MyBrand"

# 5. Generate executive refresh report
python3 scripts/report_generator.py --project "MyPortal" --refresh-matrix
```

---

## 🏛️ Research Provenance & Primary Literature Base

This skill is not theoretical speculation; it is an algorithmic synthesis built upon empirical search intelligence published by **[SearchEngineLand](https://searchengineland.com/)** across **247 analyzed research articles (August 2026, Playbook V2)**, combined with foundational agent skills from the open-source community.

### Key SearchEngineLand Research Studies:
1. **ChatGPT Retrieval Stack:** [Inside ChatGPT's retrieval stack: Discovery index, reading cache, and live opens](https://searchengineland.com/chatgpt-retrieval-stack-index-cache-pages-485036) — *Empirical breakdown of `labrador`, markdown caching, JSON-LD stripping, and routing economics.*
2. **AI Mode Citations Study:** [What 15.7 million AI Mode citations reveal about AI search](https://searchengineland.com/what-15-7-million-ai-mode-citations-reveal-483393) — *Citation volume distribution, median passage lengths (117 words), and source concentration.*
3. **Local 5.0 Evolution:** [Local 5.0: The next evolution of local SEO in AI search](https://searchengineland.com/local-5-ai-search-seo-485160) — *Shift to Context Intelligence, Context Memory Graphs, and AI-mediated discovery.*
4. **Multimodal Visual Retrieval:** [Your images have a new job in AI search](https://searchengineland.com/images-new-job-ai-search-485840) — *Google Image-First matching patent, 20B Google Lens searches, and denotation audits.*
5. **Accessibility Tree Auditing:** [10 SEO use cases for auditing your Accessibility Tree](https://searchengineland.com/accessibility-tree-seo-use-cases-484338) — *Agent navigation mechanics, ARIA landmarks, and CI regression snapshots.*
6. **AI Visibility Index:** [The AI Visibility Index: Why top brands vanish from AI answers](https://searchengineland.com/ai-visibility-index-brands-vanishing-from-ai-search-485057) — *Fractl study on the 5% high-DR brands missing in AI answers and default brands per sector.*
7. **1.8M Google Business Profiles:** [What 1.8M Google Business Profiles tell us](https://searchengineland.com/google-business-profiles-local-seo-success-data-485727) — *Category specificity, completeness index rank correlations, and address change ghost penalties.*
8. **Reddit Authority Framework:** [5 steps to building Reddit authority](https://searchengineland.com/building-reddit-authority-visibility-486084) & [Reddit is the keyword research tool you're probably not using](https://searchengineland.com/reddit-keyword-research-tool-485859) — *Mining 35M+ AI Overview triggering keywords.*
9. **Platform Citation Volatility:** [Reddit's ChatGPT Search citations fell 86%](https://searchengineland.com/reddit-chatgpt-search-citations-fall-report-485473) — *Dynamic fan-out shifting and per-engine risk mitigation.*
10. **Model Brand Familiarity:** [AI models favor familiar brands in search](https://searchengineland.com/ai-models-favor-familiar-brands-search-study-484054) — *3,960 responses showing 3.2× preference for known brand entities.*
11. **MCP for SEO Research:** [How to use MCP Servers to speed up SEO research](https://searchengineland.com/guide/use-mcp-servers-speed-up-seo-research) & [MCP data tools](https://searchengineland.com/mcp-data-tools-484650) — *Model Context Protocol integration with Semrush, Ahrefs, and GSC.*
12. **Self-Improving Content Workflows:** [7 feedback loops for self-improving AI content workflows](https://searchengineland.com/self-improving-ai-content-workflows-483404) & [How to build an AI content workflow from the ground up](https://searchengineland.com/build-ai-content-workflow-from-ground-up-485565).
13. **Local Citation Breakdown:** [Business websites dominate Gemini local AI search citations](https://searchengineland.com/business-websites-gemini-citations-local-ai-search-study-485506) — *60% business site dominance and Grounding Drift metrics.*
14. **Dynamic AI Overviews:** [Google is dynamically expanding AI Overviews](https://searchengineland.com/google-is-dynamically-expanding-ai-overviews-for-some-queries-486200) & [Google adds link carousels for developing topics](https://searchengineland.com/google-adds-link-carousels-for-developing-topics-in-ai-mode-485884).

### Open-Source Lineage & Predecessors:
- **`alirezarezvani/claude-skills` & `alirezarezvani/aeo-box`:** Original foundational Answer Engine Optimization definitions and passage extractability heuristics.
- **`rampstackco/claude-skills` (seo-aeo-geo):** Standard `llms.txt` integration, curated documentation standards, and multi-engine optimization logic.
- **Industry Standards:** [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) by Anthropic, [Schema.org](https://schema.org/) structured data by W3C, and the [llms.txt standard](https://llmstxt.org/) by Answer.ai.

---

## 📄 License & Community

Distributed under the **MIT License**. Created for autonomous agents, technical SEOs, prompt engineers, and marketing technologists scaling digital presence across generative search systems.
