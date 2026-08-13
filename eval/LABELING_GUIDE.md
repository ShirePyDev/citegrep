# Gold set labeling guide

Goal: ~100 question→page pairs across the 8 papers (~12-13 each) to measure
retrieval quality honestly. The quality of these labels determines the quality
of every metric, so label carefully.

## Format (eval/gold.jsonl — one JSON object per line)

```
{"id": "q001", "doc_id": "GuardAgent paper", "question": "...", "answer_pages": [14, 15], "type": "keyword", "split": "dev"}
```

- `doc_id`: the exact filename stem as it appears in Qdrant (e.g. "GuardAgent paper", "AgentSpec").
- `question`: natural language, how a real user would ask. NOT the paper's exact wording.
- `answer_pages`: the page(s) that genuinely answer it. 1-3 pages. Use eval/find_page.py to locate them.
- `type`: "keyword" (rare terms/acronyms — BM25 should win) or "semantic" (conceptual — dense should win). Aim ~50/50.
- `split`: "dev" or "test". Assign later with eval/make_split.py (70/30). Leave blank for now.

## Rules for good questions

1. **Answerable from a specific page by a specific fact.** Good: "How many examples are in EICU-AC?" Bad: "What is this paper about?" (answerable everywhere — useless for measuring).
2. **Natural phrasing, not the paper's words.** If you copy the paper's sentence, you only test keyword matching and bias the whole eval. Ask like a curious researcher, then find the answering page.
3. **Mix types ~50/50.** Keyword questions (acronyms, dataset names, specific numbers) AND semantic questions (mechanisms, comparisons, "how does X work"). This is what lets the final table show hybrid beats either arm alone.
4. **Unambiguous answer page.** If you can't point to THE page(s), the question is too vague — skip it.

## Workflow

1. Skim a paper. Think of ~12 things a reader would want to know.
2. For each, phrase it naturally, then run: `uv run python eval/find_page.py "some phrase from the answer" --doc "GuardAgent paper"` to get the page.
3. Write the line into eval/gold.jsonl.
4. Tag each as keyword or semantic.
5. When all ~100 are done, run eval/make_split.py to assign dev/test 70/30.

## Honesty

- Tune (chunk size, k, candidates) on DEV only. Report final numbers on TEST.
- If reranking doesn't help on some metric, report that. A negative result with an explanation reads better than a suspiciously perfect table.
- Page-level labels slightly over-count (any chunk from a gold page counts as a hit). This is the accepted cost of labels that survive re-chunking; note it in the README.
