# NLP/RAG Lab Plan

This document is an implementation plan only. It does not add RAG, vector databases,
LLM APIs, LangChain, LlamaIndex, or app behavior changes.

## Current Repository Snapshot

Hub_ML is already a local Streamlit learning workstation with:

- Obsidian Theory Hub
- Theory Audit and Theory Quality reports
- Learning Coverage Matrix
- Practice cards
- Mentor Tasks with assert checks
- Datasets
- Notebook with a live Jupyter kernel
- Data Lab Projects
- Classic ML Baseline Project
- Portfolio Exporter

Current dependencies already support a safe first NLP step:

- `pandas`
- `matplotlib`
- `scikit-learn`
- `jupyter_client`
- `ipykernel`
- `streamlit`

No NLP-specific dependencies are currently required for phase 1.

## Evidence From Reports

The current real-vault theory audit reports 207 notes. NLP/RAG-related notes exist,
but many of them are thin or mostly theory-only.

Relevant notes and scores from `content/reports/theory_audit.json`:

- `00_Graph/40_NLP_Path.md` - score 0, 37 words
- `00_Graph/41_Text_Pipeline.md` - score 0, 19 words
- `00_Graph/42_Text_Representations.md` - score 0, 21 words
- `04_NLP/00_Index.md` - score 35, 111 words
- `04_NLP/01_NLP_Basics.md` - score 50, 133 words
- `04_NLP/02_Text_Preprocessing.md` - score 50, 127 words
- `04_NLP/03_Bag_of_Words.md` - score 50, 159 words
- `04_NLP/04_Word_Embeddings.md` - score 55, 129 words
- `04_NLP/06_Transformers_Intro.md` - score 50, 139 words
- `04_NLP/10_NLP_Theory_Deep_Dive.md` - score 65, 649 words
- `04_NLP/14_NLP_Tasks_Course_Article.md` - score 70, 273 words

Relevant coverage statuses from `content/reports/coverage_report.json`:

- `nlp.preprocessing` - partial, theory quality 24, one practice card
- `nlp.vectorization` - partial, theory quality 23, two practice matches
- `nlp.transformers` - theory_only
- `genai.prompting` - theory_only
- `genai.embeddings_search` - covered, but mostly by theory and weak evidence
- `genai.rag` - theory_only
- `genai.evaluation_agents` - theory_only

Existing practice signal:

- `practice/nlp_text_classifier_baseline.md` exists and asks for a manual NLP
  baseline design, but there is no full NLP project yet.

Existing interview signal:

- `content/interview_questions/ml_ds_interview_questions.json` includes RAG, LLM,
  semantic search, chunking, and evaluation questions. These are useful for later
  interview review, but they are not a hands-on NLP/RAG project.

## Why Not Start With Full RAG Immediately

Full RAG would be the wrong first implementation step because Hub_ML is not ready
for it yet:

- The NLP foundations are still partial: preprocessing and vectorization have weak
  theory quality scores.
- RAG is currently theory-only. There is no hands-on retrieval project, no citation
  format, and no evaluation set.
- Adding a vector database would increase architecture complexity before proving
  that local retrieval is useful.
- Adding an LLM API would create privacy and key-management risks before local
  retrieval quality is measurable.
- LangChain or LlamaIndex would hide too much of the learning path. The user needs
  to understand chunking, vectorization, retrieval, evaluation, and citations first.
- The app already has a live Notebook and project milestone runner. The first NLP
  lab should reuse those simple local tools instead of introducing a second stack.

The safe route is: text analysis -> classical retrieval -> semantic search ->
cited RAG -> evaluated AI mentor.

## Phase 1 - Local Text Analysis Mini-Lab

### Goal

Build a local, understandable NLP mini-lab using classical NLP. The user learns
text cleaning, tokenization tradeoffs, bag-of-words, TF-IDF, train/test split,
baseline metrics, and error analysis.

### Inputs

- `practice/nlp_text_classifier_baseline.md`
- `content/interview_questions/ml_ds_interview_questions.json`
- Existing Obsidian NLP notes:
  - `04_NLP/01_NLP_Basics.md`
  - `04_NLP/02_Text_Preprocessing.md`
  - `04_NLP/03_Bag_of_Words.md`
  - `04_NLP/13_Text_Representations_Course_Article.md`
- Optional local text CSV later, if a real dataset is added.

### Dependencies

Use existing dependencies only:

- `pandas`
- `scikit-learn`
- `matplotlib`

Useful `scikit-learn` tools:

- `CountVectorizer`
- `TfidfVectorizer`
- `train_test_split`
- `LogisticRegression`
- `MultinomialNB`
- `classification_report`
- `confusion_matrix`

### App Changes

Recommended implementation later:

- Add `content/projects/nlp_lab/local_text_analysis_mini_lab.json`.
- Reuse the existing Data Lab / ML Lab project UI and milestone runner.
- Do not add a new tab yet unless Projects cannot group NLP projects clearly.
- Add a small local text dataset only if it is public, small, and documented.
- Keep execution inside the existing Jupyter kernel path.

### Tests

- Recipe loading test.
- Project milestone normalization test.
- No new execution engine test.
- Smoke test that the starter code imports `TfidfVectorizer`.

### Portfolio Output

- A short text classification baseline report.
- A confusion matrix.
- A small error-analysis table with real examples.
- A model-card style section explaining limitations.

### Risks

- Small or artificial text data can teach the wrong lessons.
- Russian/English mixed text can make tokenization look worse than it is.
- Users may overfit to one metric without reading errors.

### What Not To Do Yet

- Do not use LLM APIs.
- Do not add embeddings models.
- Do not add vector databases.
- Do not build chat UI.

## Phase 2 - Embeddings / Semantic Search

### Goal

Teach retrieval before generation. Start with transparent search methods and only
then consider embeddings.

### Inputs

- Obsidian markdown notes from the real vault.
- Interview questions JSON.
- Output from Phase 1.

### Dependencies

Start with existing dependencies:

- `TfidfVectorizer`
- cosine similarity from `scikit-learn`
- simple JSON or CSV index files in ignored user workspace folders

Optional later, only after phase 1 succeeds:

- `sentence-transformers` for local embeddings

### App Changes

Recommended implementation later:

- Add a guided project recipe: `content/projects/nlp_lab/semantic_search_prototype.json`.
- Milestones:
  - collect documents;
  - split into passages;
  - build TF-IDF index;
  - search top-k passages;
  - inspect failures;
  - write retrieval report.
- Store generated indexes in `user_projects/`, not in tracked source files.

### Tests

- Passage splitting helper tests.
- Search result schema tests.
- Retrieval smoke test on a tiny fixture corpus.

### Portfolio Output

- Semantic search prototype report.
- Example queries with top-k retrieved passages.
- Failure analysis: missed synonyms, noisy chunks, overly long passages.

### Risks

- TF-IDF search may look weak on semantic queries.
- Local embedding libraries can be heavy.
- Generated indexes may accidentally include private notes if committed.

### What Not To Do Yet

- Do not add Chroma, FAISS, Qdrant, Pinecone, or other vector DBs.
- Do not add LangChain or LlamaIndex.
- Do not generate answers. Retrieve passages only.

## Phase 3 - Obsidian RAG With Citations

### Goal

Turn retrieval into cited answer support over the Obsidian vault, while keeping the
system local-first and inspectable.

### Inputs

- Cleaned Obsidian markdown notes.
- A local retrieval index from Phase 2.
- A small set of user-written questions.

### Dependencies

Preferred first version:

- Existing Python stack.
- No external APIs.
- Retrieval-only UI that shows cited passages.

Optional later:

- A local embedding model if phase 2 proves value.
- An LLM API only after explicit approval and evaluation rules are in place.

### App Changes

Recommended implementation later:

- Add an Obsidian Retrieval project, not a general chat assistant first.
- Show query, retrieved note path, heading, snippet, and score.
- Link results back to Theory when possible.
- Keep generated indexes outside git-tracked content.

### Tests

- Citation path formatting tests.
- Query result ordering tests on a fixture corpus.
- Hidden folder ignore tests.

### Portfolio Output

- Cited knowledge retrieval case study.
- Screenshots or markdown examples of query -> cited passages.
- A limitations section about stale notes, missing notes, and retrieval misses.

### Risks

- Without citations, RAG can look convincing but be unverifiable.
- Thin notes reduce retrieval quality.
- Vault content may be private and should not be exported.

### What Not To Do Yet

- Do not implement a generative AI mentor in this phase.
- Do not auto-rewrite notes.
- Do not push indexes or private snippets to the repo.

## Phase 4 - RAG Evaluation Set

### Goal

Create a small, honest evaluation set before adding generation. Measure whether
retrieval returns the right sources and whether answers are grounded.

### Inputs

- 30-50 manually written questions.
- Expected source notes or passages.
- Existing interview RAG questions as inspiration, not as auto-labeled truth.

### Dependencies

Use standard library plus existing stack.

Optional later:

- LLM-as-judge only after a manual baseline exists and only with explicit approval.

### App Changes

Recommended implementation later:

- Add `content/evals/rag_eval_set.json`.
- Add a report generator or a small read-only app section.
- Track retrieval metrics:
  - recall@k;
  - citation hit rate;
  - no-answer handling;
  - duplicate source rate.

### Tests

- Eval record schema tests.
- Metric calculation tests.
- Report generation tests.

### Portfolio Output

- RAG evaluation report.
- Table of failure cases.
- Clear next-step backlog.

### Risks

- Evaluation questions can be too easy.
- Expected citations may become stale when notes move.
- LLM judging can hide errors if introduced too early.

### What Not To Do Yet

- Do not optimize prompts before retrieval quality is measured.
- Do not claim answer quality without citation and retrieval metrics.

## Phase 5 - AI Mentor Integration

### Goal

Add an AI mentor only after local retrieval, citations, and evaluation are stable.
The mentor should answer with sources, suggest next learning steps, and never hide
whether it is using retrieved context.

### Inputs

- Phase 3 retrieval results.
- Phase 4 evaluation set.
- Portfolio/project state.

### Dependencies

Possible later options:

- OpenAI API or another LLM provider, only after explicit approval.
- No dependency should be added until the prompt, citation, privacy, and eval
  contract is written.

### App Changes

Recommended implementation later:

- Add an AI Mentor section only after RAG evaluation passes a minimum bar.
- Require citations in every answer.
- Add a "show retrieved context" expander.
- Store API keys outside the repo.

### Tests

- Prompt construction tests.
- Citation required tests.
- No-context fallback tests.
- Secrets-not-logged checks.

### Portfolio Output

- AI mentor demo with grounded answers.
- Evaluation summary.
- Safety and privacy notes.

### Risks

- API costs and key handling.
- Hallucinated answers if citations are weak.
- Over-reliance on framework abstractions.

### What Not To Do Yet

- Do not add agents.
- Do not add tool calling.
- Do not add autonomous note editing.
- Do not add production deployment.

## First 3 NLP/RAG Practice Cards

These should be added later as guided `practice/*.md` cards, not in this planning
task.

### 1. Text Preprocessing Audit

- Section: NLP
- Difficulty: easy
- Goal: compare raw text, lowercased text, punctuation removal, and simple token
  filtering on interview questions.
- Output: preprocessing decisions table.
- Portfolio artifact: short note explaining what cleaning was kept or rejected.

### 2. TF-IDF Retrieval Baseline

- Section: NLP
- Difficulty: medium
- Goal: build a TF-IDF search over a small local corpus and inspect top-k results.
- Output: query -> retrieved documents table.
- Portfolio artifact: retrieval baseline report with failure examples.

### 3. RAG Citation Checklist

- Section: GenAI and RAG
- Difficulty: medium
- Goal: design a manual rubric for whether a retrieved answer is grounded in
  sources.
- Output: checklist with examples of good and bad citations.
- Portfolio artifact: RAG evaluation rubric.

## First 2 NLP/RAG Projects

### 1. Local Text Analysis Mini-Lab

Recommended first project.

- Track: NLP
- Level: junior
- Inputs: interview questions or a small documented local text dataset.
- Skills:
  - text cleaning;
  - TF-IDF;
  - train/test split;
  - baseline classifier;
  - error analysis;
  - model-card style reporting.
- Why first: it uses existing dependencies and teaches the mechanics needed before
  embeddings or RAG.

### 2. Obsidian Semantic Search Prototype

- Track: GenAI and RAG
- Level: junior/middle
- Inputs: Obsidian markdown notes.
- Skills:
  - chunking;
  - lexical retrieval;
  - optional local embeddings later;
  - citation formatting;
  - retrieval evaluation.
- Why second: it bridges the Theory Hub with retrieval without adding generation.

## Minimal Dependency Strategy

Phase 1 dependency policy:

- Add no dependencies.
- Use existing `scikit-learn`.
- Prefer `TfidfVectorizer` and simple baselines.

Phase 2 dependency policy:

- Start with TF-IDF and cosine similarity.
- Consider `sentence-transformers` only after a local lexical baseline exists.
- Do not add vector DBs.

Phase 3-5 dependency policy:

- Do not add OpenAI API, LangChain, LlamaIndex, Chroma, FAISS, or agents until
  retrieval and evaluation are proven useful.
- If an LLM provider is later added, isolate provider code and require explicit
  API key configuration outside git.

## Privacy and Local-First Rules

- Never send Obsidian notes to external APIs by default.
- Never commit generated indexes from private vault content.
- Store user-generated indexes, reports, and experiments under ignored user output
  folders such as `user_projects/`.
- Do not include raw datasets in exported portfolio artifacts.
- Every RAG answer must show source note paths and snippets.
- If a note is missing or weak, report that limitation instead of inventing an
  answer.
- Any future API usage must be opt-in and documented.

## Recommended First Implementation Prompt

```text
You are working inside Hub_ML.

Goal:
Implement Phase 1 of the NLP/RAG Lab plan: Local Text Analysis Mini-Lab.

Constraints:
- Do not add RAG.
- Do not add vector databases.
- Do not add OpenAI API.
- Do not add LangChain or LlamaIndex.
- Do not create a second execution engine.
- Reuse the existing Project recipe and Project Milestone Runner patterns.
- Use existing dependencies only: pandas, scikit-learn, matplotlib, Streamlit,
  Jupyter kernel.

Task:
1. Add a guided NLP project recipe under content/projects/nlp_lab/.
2. Use a small local text source already in the repo, preferably interview
   questions, or stop and report if no suitable local source exists.
3. Milestones should cover:
   - inspect text data;
   - clean text minimally;
   - build TF-IDF features;
   - train a baseline classifier or retrieval baseline if labels are unavailable;
   - evaluate honestly;
   - write error analysis;
   - produce portfolio output.
4. Add pure tests for recipe loading and milestone normalization.
5. Do not change Notebook, Tasks, Datasets, or existing project behavior.

Return:
- Files changed
- Project recipe added
- Learning goals
- Tests run
- Manual test checklist
- Known limitations
```
