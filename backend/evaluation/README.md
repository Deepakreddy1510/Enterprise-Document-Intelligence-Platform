# Offline evaluation

This framework deliberately has two layers: deterministic retrieval metrics answer “did the correct document page rank highly?”, while optional RAGAS judge metrics assess whether the generated answer is grounded and relevant. RAGAS is offline only; it is never imported or invoked by normal chat requests.

## Build a real dataset

Create 25–30 cases from PDFs uploaded by one evaluation user. Include easy fact lookup, synthesis across pages, similarly worded distractors, and genuinely unanswerable questions. For each answerable case, write a concise reference answer using only the source document, then record the one-based PDF page numbers containing sufficient evidence. Verify pages in a PDF viewer rather than using extracted chunk ordinals. Include several unanswerable cases with an explicit refusal expectation. Do not put secrets or private production content in Git.

The JSONL schema is strict. Each line needs `id`, `question`, `selected_documents`, `relevant_pages`, `reference_answer`, `answerable`, and `expected_behavior`; `tags` and `notes` are optional. Answerable cases require both a reference answer and positive relevant pages. Duplicate IDs, blank questions, absent selected documents, and non-positive pages are rejected.

## Run

Retrieval-only (no Gemini or RAGAS calls):

```bash
cd backend
python -m app.evaluation.cli --dataset evaluation/cases.jsonl --user-email user@example.com --top-k 5 --mode retrieval --output evaluation/results.json
```

Full generation and RAGAS:

```bash
RAGAS_ENABLED=true python -m app.evaluation.cli --dataset evaluation/cases.jsonl --user-email user@example.com --top-k 5 --mode all --max-concurrency 2 --output evaluation/results-ragas.json --fail-on-error
```

Set `GEMINI_API_KEY` for generation/judging and `RAGAS_EVALUATOR_MODEL` to a Gemini model available to that key. Each evaluator request consumes API quota. Concurrency, timeouts, one retry, and a local response cache bound cost and failure impact; partial per-case results are always saved; `--fail-on-error` makes the command exit non-zero after writing them.

## Interpreting results

Retrieval computes Hit@1/3/5, MRR, Recall@5, and retrieval latency. Relevance requires both exact document filename and labelled page. Cosine similarity is only a ranking signal, never confidence. RAGAS 0.4.3 collections metrics compute faithfulness, answer relevancy, context precision/recall, and factual correctness for answerable cases only. Unanswerable cases instead report correct refusals and hallucinated answers.

LLM judges are nondeterministic, can share biases with the generator, and consume API quota. Retain deterministic retrieval results and perform manual review using `manual_answer_review.csv`. Preserve timestamped JSON/CSV baselines. To compare configurations fairly, keep the dataset, uploaded document versions, evaluator/generator models, and concurrency fixed; change one retrieval/chunking/model variable at a time and retain both result files.

## Tests

Unit tests mock evaluator calls. The pgvector ownership/filtering integration test is opt-in and requires a migrated disposable database:

```bash
RUN_INTEGRATION_TESTS=1 pytest tests/test_retrieval_integration.py
```
