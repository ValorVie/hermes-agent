# Visual/OCR Automation State Machine Debugging

Use this reference when a screen-automation bot loops, times out, or sends inputs repeatedly after OCR/template recognition partially succeeds.

## Durable lesson

Do not let enrichment quality block control-flow liveness.

A common failure pattern:

1. The bot enters a result/settlement state.
2. OCR or template matching extracts partial evidence, such as a weight, score, button, or result text.
3. A secondary enrichment step fails, such as catalog-name matching or canonicalization.
4. The state machine treats enrichment failure as result failure.
5. The bot times out, resets to idle, and misclassifies the still-blocking screen as ready for input.
6. It repeatedly sends the next action while the prior result screen is unresolved.

## Debug checks

- Trace the exact gate that prevents state transition.
- Separate these questions:
  - Is there enough evidence to safely advance the state machine?
  - Is there enough evidence to accurately enrich the record?
- Check whether downstream storage supports degraded data, such as unknown labels, raw OCR candidates, or partial measurements.
- Check whether timeout recovery closes the blocking screen or merely re-enters idle.
- Inspect logs for the sequence: partial extraction succeeded → canonical match failed → timeout → repeated input.

## Safer fallback pattern

Use guarded degradation instead of hard failure:

```text
advance_result =
  in_result_state
  AND prior_round_reached_action_phase
  AND no_strong_failure_signal
  AND (
    known_catalog_match
    OR strong_partial_result_evidence
  )
```

Where `strong_partial_result_evidence` can be a valid measurement plus stable result-screen context, not arbitrary OCR noise.

Record lower-confidence data explicitly:

- canonical label: known value or unknown bucket
- raw OCR text: preserve for later reconciliation
- measurement: preserve if valid
- fallback source: log the reason, such as weight-based fallback

## Regression tests

Add paired tests:

- Unknown/canonical-miss + strong partial evidence advances and closes the result screen.
- Unknown/canonical-miss + weak/no measurement does not advance.
- Known/canonical match still follows the original successful path.
- Blocking result screens prevent idle/cast actions.

## Pitfalls

- Do not fix liveness by training OCR first; recognition will always remain probabilistic.
- Do not use a bare positive number as success evidence. Require state context and failure-signal exclusion.
- Do not let fuzzy matching silently rewrite records without preserving raw OCR text.
