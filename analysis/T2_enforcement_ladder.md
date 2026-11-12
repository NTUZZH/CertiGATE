# T2. The enforcement ladder

<!-- generated 2026-08-17 17:24:01 +0800 by paper_tables.py (l1-paper-tables-1) -->
<!-- dedup rule applied to the hosted raw logs before evaluation: last row per (mode, thinking, repeat, item_id); hosted logs only -->
<!-- suite suite.jsonl sha256 0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a -->
<!-- adjustment schema sha256 1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321 -->
<!-- ladder anchors: <project>/analysis/ladder (reconciliation 4208/4208 passed) -->
<!-- <project>/results/e1_eval_qwen14b/summary.json sha256 602461e5897a91db20e67a1ce0c9a9b8fa5f64c771a395434c4b9b5a9394d390 -->
<!-- <project>/results/e1_eval_qwen27b/summary.json sha256 8402b5dd527ed055e787c7d53aa4ab752695030909697189622134d1dc8b2a2b -->
<!-- <project>/results/e1_eval_glm9b/summary.json sha256 b655f1e92b0e048e52d6d7d6bcf445558df8b233a1abdf8babd4097edecd4bb8 -->
<!-- <project>/results/e1_eval_gpt54mini/summary.json sha256 dc1e4c9bfdc916c8057411124c8acb3cfeeb452b1e4b0642149c0cf555a560f6 -->
<!-- <project>/results/e1_eval_deepseek/summary.json sha256 5f362141b7f1dd5a32ae64bcbe53cbe30290477c0d294da957125290114a0b71 -->
<!-- <project>/results/e1_eval_sonnet5/summary.json sha256 65aab2232dfac88a58dfdb2f66baef11b63dd700e896b592e35c8bc5f5710d59 -->
<!-- <project>/results/e1_eval_opus5/summary.json sha256 8417125bd4df8b0f3666f30d2b6149411ab2ee3c5ad21a4e29b8a59b4c505309 -->
<!-- <project>/results/e1_eval_sol/summary.json sha256 28475fbf5fcd71348c20ad833353a61e1840912a1ccbcc6cbc8e504893058f4d -->
<!-- <project>/results/e2_tau_sweep/curves.csv sha256 e9ca179c57029c6ae23d0512f12da901884072192c96addff321de94bf04fc76 -->
<!-- rows are the accepted record; every overlapping cell is asserted equal to it -->

The enforcement axis, ordered by what the wire actually enforces: `none` (M_free, no enforcement field), `json_object` (reply with a JSON object, no schema; DeepSeek's only constrained mode), and the two real schema enforcements, `json_schema` (provider-side strict outputs) and `xgrammar` (local grammar-guided decoding). Shape drift is the share of completions that do not parse as a proposal about this instance; the silent no-op column is what that drift costs when nothing gates, because the lenient repair drops the operations it cannot read and executes what remains, which is often nothing.

| enforcement | arm | mode | think | items | JSON invalid | wrong shape | schema valid | G-CERT blocked at schema | UNGUARDED silent no-op | benign translation exact |
|---|---|---|---|---|---|---|---|---|---|---|
| none | qwen3-14b | M_free | - | 6000 | 6.58% | 85.72% | 7.70% | 92.3% | 92.8% | 0.0% |
| none | qwen3.6-27b-fp8 | M_free | - | 6000 | 0.00% | 89.30% | 10.70% | 89.3% | 99.5% | 0.0% |
| none | glm-4-9b | M_free | - | 2000 | 98.60% | 1.40% | 0.00% | 100.0% | 99.5% | 0.0% |
| none | openai | M_free | - | 4000 | 0.00% | 95.08% | 4.92% | 95.1% | 99.6% | 0.2% |
| none | deepseek | M_free | non_think | 4000 | 0.00% | 82.75% | 17.25% | 82.8% | 99.8% | 0.0% |
| none | deepseek | M_free | think_high | 4000 | 1.12% | 84.50% | 14.37% | 85.6% | 98.9% | 0.0% |
| none | sonnet | M_free | disabled | 4000 | 9.18% | 78.35% | 12.47% | 87.5% | 99.5% | 0.0% |
| none | opus | M_free | default | 4000 | 0.10% | 18.20% | 6.48% | 18.3% | 23.6% | 1.0% |
| none | opus | M_free | disabled | 4000 | 0.25% | 14.80% | 6.95% | 15.2% | 17.7% | 4.1% |
| json_object | deepseek | M_constrained | non_think | 4000 | 0.00% | 80.77% | 19.23% | 80.8% | 100.0% | 0.0% |
| json_object | deepseek | M_constrained | think_high | 4000 | 1.90% | 83.60% | 14.50% | 85.5% | 97.8% | 0.0% |
| xgrammar | qwen3-14b | M_constrained | - | 6000 | 0.37% | 0.00% | 99.63% | 6.7% | 7.1% | 59.3% |
| xgrammar | qwen3.6-27b-fp8 | M_constrained | - | 6000 | 0.00% | 0.00% | 100.00% | 5.5% | 10.5% | 73.3% |
| xgrammar | glm-4-9b | M_constrained | - | 2000 | 0.00% | 0.00% | 100.00% | 9.2% | 1.4% | 60.8% |
| json_schema | openai | M_constrained | - | 4000 | 0.00% | 0.00% | 100.00% | 7.2% | 3.8% | 65.4% |
| json_schema | sonnet | M_constrained | disabled | 4000 | 0.00% | 0.00% | 100.00% | 4.5% | 15.8% | 70.4% |
| json_schema | opus | M_constrained | default | 4000 | 0.00% | 0.00% | 99.95% | 1.8% | 23.9% | 72.4% |
| json_schema | opus | M_constrained | disabled | 4000 | 0.00% | 0.00% | 99.95% | 3.5% | 20.9% | 72.6% |
| json_schema | sol | M_constrained | none | 2000 | 1.55% | 0.00% | 98.45% | 4.2% | 20.4% | 69.1% |

