# sprs-l0

Deterministic L0 core for SPIR v0.4.0:
1. `analyze` -> syntax (Paninian + UD basic/enhanced + clause/discourse) + semantics (KAG event+deontic).
2. `validate` -> strict structural checks for SPIR v0.4.0.
3. `query_understand` -> KAG query + retrieval plan.
4. `retrieve_candidates` -> hybrid BM25+vector+RRF+rerank retrieval.
5. `export_artifacts` -> sidecars (`conllu_basic`, `conllu_enhanced`, `kag_jsonl`, `align_json`).

SPIR v0.4.0 core fields:
1. `syntax.paninian_edges`
2. `syntax.ud.basic_edges`
3. `syntax.ud.enhanced_edges`
4. `syntax.ud.empty_nodes`
5. `syntax.clauses`
6. `syntax.discourse_links`
7. `semantics.kag`

