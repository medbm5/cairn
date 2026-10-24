# 0003 Boundaries for the language model

- Status: accepted
- Date: 2026-10-24

## Context

Cairn uses a language model so Pebble can explain projections, allocations, rebalances, stress
tests and ledger lines in everyday French or English. Language models write fluent text, but
they can also invent figures, do arithmetic wrong, or slip into advice ("you should invest
more") and promises ("you will reach your goal"). In a product about money, a wrong number in a
friendly sentence is worse than no explanation at all.

## Decision

The model **explains and never computes.**

1. **Numbers come from code.** The deterministic engine (simulation, glide path, rebalancing,
   ledger, stress tests) produces every figure. For each topic a typed *facts* object
   (`explain/facts.py`) holds exactly the numbers an explanation may mention.
2. **The model only rewrites facts.** The request to the model contains the facts, the relevant
   glossary entries, the language and a word limit. The system prompt forbids calculating,
   adding numbers, advising and promising returns. Output is parsed into a Pydantic model
   (structured outputs), never free text.
3. **A number guard checks every answer.** Every number in the generated title, body and
   analogy must match a value derived from the facts (euros for cents, percentages for
   fractions, years for months, rounding, "12k"). One unknown number and the answer is
   discarded and logged.
4. **Templates are the floor.** Each topic has a human-written template in both languages,
   filled with the same facts. It is used without an API key, on timeout (10 s, one retry), on
   API errors, on answers over the word limit, and when the guard rejects an answer. The UI
   cannot tell the difference except for the `source` field, so the app is complete without
   the model.
5. **Cost is bounded.** Answers are cached by a hash of topic, facts, level and language; output
   tokens are capped; `/explain` is rate-limited per client IP.

## Consequences

- Explanations can never introduce a figure the engine did not compute, which makes them safe
  to show next to exact numbers.
- Some good model answers are rejected (for example "three in four" written as "3 in 4" when the
  probability is 0.74). That is the intended trade-off: a template is always a correct answer.
- The glossary is written without digits so it cannot leak numbers into answers; a test
  enforces this.
- Tests mock the OpenAI client, so CI never needs a key or network access.
