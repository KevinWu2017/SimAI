# HBF port: official source bases and compatibility

The HBF development branch is `hbf-pp-search`. It contains the official SimAI
master base `a57d765c5478f319c5f5ab6fdc53f9cc7f461743` and uses the AICB fork
based on official master `23eec3c48ca2d2d93dd888a4c7b22ab4421e782f`.
These were the official master heads checked on 2026-11-10. The official SimAI
release notes identify this base as 1.7. The older fork's README entry about
SimAI 2.0 was a roadmap, not a release identifier.

Use a recursive checkout of this branch. The parent records an exact AICB
commit; `.gitmodules` also names its HBF branch. Official SimCCL, ns-3 and CLEM
references remain the ones pinned by the official SimAI base. They are not
independently advanced to potentially incompatible development heads.

```bash
python3 scripts/check_hbf_upstream.py --require-clean
python3 scripts/check_hbf_upstream.py --check-remote --github-ssh --require-clean
```

The second command compares against official master live. It fails if upstream
has advanced, rather than silently reporting an old pinned base as latest.
The check also verifies that official tracked source files are retained:
only `.gitmodules`/the AICB gitlink in SimAI and README integration links
may differ. HBF implementation files are added alongside upstream.

## Migrated functionality

- `run_simai_batch.py` retains the old external-workload batch runner and adds
  cluster parameters. It calls the current analytical binary.
- AICB `estimate_prefill_memory.py`, `estimate_decode_memory.py`,
  `memory_model.py` and `search_parallel_strategy.py` retain the older HBF
  capacity implementation, including its layer-aware PP accounting.
- AICB `evaluate_topk_strategies.py` adds objective selection and fingerprinted
  result reuse to the legacy strategy evaluator.
- AICB `workload_generator/HBF_SimAI_inference_workload_generator.py` retains
  external stage timing input and BF16 communication sizes. Its Python API
  now uses instance arguments, and missing/invalid stage times fail explicitly.
- AICB `scripts/HBF_inference_workload_with_computeCache.sh` retains the HBF
  entry point and restored HBF default configurations, including paths with
  spaces and calls from outside the checkout.
- The PP workload, stage evaluation, forward scheduling and search modules
  are described in `aicb/README_HBF_PP.md`.

The old fork was ported by functionality; it was not merged wholesale.
Consequently the legacy fork commits are not all ancestors of this branch.

## Legacy-only changes retained separately

The old SimAI committed/stashed C++ edits were audited against their common
upstream base. After excluding comments, whitespace and debug output, the only
remaining token change was the distributed-inference event step from 1 to 2
in the old stash. `compat/hbf_legacy_inference_tick.patch` preserves that
one-line experiment as an opt-in source patch. It is not applied by default:
the active core uses official event scheduling. To inspect/apply it in an
isolated checkout:

```bash
git apply --check compat/hbf_legacy_inference_tick.patch
git apply compat/hbf_legacy_inference_tick.patch
# Rebuild the selected backend before running this legacy experiment.
```

The old local build directory override is replaced by current upstream build
scripts; it does not implement an HBF performance feature. Debug prints,
comments, generated topology/output files, dependency symlinks and local
benchmark results remain in the legacy refs or external provenance archive.

The older `HBF_AiobQwen3.py` and `Qwen3moe_235B.py` profiling experiments are
also retained in the legacy AICB history (`d807271`). Their expert gate/up/down
timings were explicitly set to zero, and their imports target old GPU-library
APIs. They are not complete BF16/HBF compute profiles. The external Accel-Sim
timing path is the supported HBF compute source; this port does not re-enable
those incomplete profiling paths or globally disable upstream FP8 support.

Detailed audit patches/results are kept outside the Git repositories under
`experiments/simai_port_audit_20261110`. No experiment result data is included
in the code changes. Functional validation is separate from upstream ancestry;
the PP communication/physical-model limitations in `aicb/README_HBF_PP.md`
still apply.
