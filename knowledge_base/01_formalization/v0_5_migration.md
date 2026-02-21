# SPIR v0.5 Migration Notes

## Scope
This release is strict-breaking относительно v0.4: old SPIR payloads are not accepted by `validate`.

## Breaking Changes
1. `meta.version` must be `0.5.0`.
2. Clause span policy changed to half-open: `token_span = [start, end)`.
3. Enhanced UD references now allow token ids (`int`) and empty-node ids (`str` in `i.j` format).
4. `syntax.ud.empty_nodes[].id` must be UD-compatible (`i.j`), not legacy `E1`.
5. `ud_mode` default changed to `head_rules` (legacy projection remains via `ud_mode=projected`).

## Validation
`validate` now runs two layers:
1. JSON Schema (draft 2020-12) for SPIR/UD/EUD/clauses/KAG.
2. Procedural semantic checks (tree invariants, node reference consistency, KAG provenance cross-links).

## Export
`l0_export` / `export_artifacts` produce enhanced CoNLL-U with:
1. empty node rows (`i.j`);
2. `HEAD`/`DEPREL` set to `_` for empty nodes;
3. enhanced dependencies in `DEPS`.

## Pipeline Ordering
`analyze` now applies overrides before building downstream layers.  
If overrides modify Paninian/UD, clauses, enhanced UD, and KAG are built from updated graph state.
