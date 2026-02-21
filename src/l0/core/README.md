# sprs-l0

Deterministic L0 core for SPIR v0.5.0:
1. `analyze` -> syntax (Paninian + UD basic/enhanced + clause/discourse) + semantics (KAG event+deontic).
2. `validate` -> JSON Schema + semantic checks for SPIR v0.5.0.
3. `query_understand` -> KAG query + retrieval plan.
4. `retrieve_candidates` -> tiered retrieval (`baseline|hybrid_prod` with fallback metadata).
5. `export_artifacts` -> sidecars (`conllu_basic`, `conllu_enhanced`, `kag_jsonl`, `align_json`).

SPIR v0.5.0 core fields:
1. `syntax.paninian_edges`
2. `syntax.ud.basic_edges`
3. `syntax.ud.enhanced_edges`
4. `syntax.ud.empty_nodes`
5. `syntax.clauses`
6. `syntax.discourse_links`
7. `semantics.kag`

Key v0.5 changes:
1. `token_span` is half-open: `[start, end)`.
2. Enhanced UD empty nodes use UD-compatible ids: `i.j`.
3. Default `ud_mode=head_rules`, with `projected` as debug fallback.
4. Canonical schemas live in `sprs_l0/schemas/*.schema.json`.
