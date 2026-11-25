# JSON Schema Infer — Day 24 (Day C: community / open-source)

A stdlib-only CLI that infers a JSON Schema (draft 2020-12) from
sample JSON — and can then validate new data against the schema it
inferred.

## The problem

You have an API, a webhook, or a pile of log lines, and you need a
schema for them: to document the response, to validate new payloads,
or to generate types. Writing the schema by hand means reading
dozens of examples and guessing which fields are always present,
which are optional, and which values are a closed set. Existing
schema generators are usually a dependency install or a web form
that uploads your data somewhere.

## What it does

    python schema_infer.py infer sample.json [more.json ...] [-o schema.json]
    python schema_infer.py infer --jsonl samples.jsonl [-o schema.json]
    cat sample.json | python schema_infer.py infer -
    python schema_infer.py validate schema.json data.json

From the samples it infers:

- **Types** — `integer` vs `number` (a field that is sometimes `92`
  and sometimes `87.5` is a `number`, not an either/or), `string`,
  `boolean`, `null`, `array`, `object`. Booleans are never mistaken
  for integers.
- **Required fields** — a key is `required` only if it appears in
  *every* sample; anything rarer is optional.
- **Nested objects and arrays** — item schemas are merged across
  all array elements, so `[{"a": 1}, {"a": 2, "b": "x"}]` yields one
  item schema with `a` required and `b` optional.
- **Mixed types** — a field that is sometimes a number and sometimes
  a string becomes `anyOf`.
- **Formats, as heuristics** — `date-time`, `date`, `email`, `uri`
  are added only when *every* sample matches; one odd value removes
  the format instead of guessing.
- **Enums, as heuristics** — a field with 2–5 distinct values across
  at least 3 samples gets an `enum` (`--no-enum` turns this off).
- **`--strict`** adds `additionalProperties: false` to every object,
  for when the samples are meant to be the whole contract.

`validate` checks data against a schema (type, enum, required,
properties, `additionalProperties`, array items, `anyOf`) and exits
`1` with a list of errors, so it works as a CI gate. `format` is
annotation-only and is deliberately *not* enforced by `validate` —
a string that looks like an email is not proof it is one.

## Example input / output

`examples/api-response.json` and `examples/api-response-2.json`
are two synthetic user records (demo data only, nothing real). The
second one has no `tags`, an extra `address.landmark`, and a
`status` of `paused` instead of `active`:

```
$ python schema_infer.py infer examples/api-response.json \
      examples/api-response-2.json -o examples/api-response.schema.json
wrote examples/api-response.schema.json (2 samples)
```

The generated schema (committed as `examples/api-response.schema.json`)
says, among other things: `id` is an integer, `score` is a number,
`created_at` is a `date-time` string, `email` is an `email` string,
`address.pin` is required but `address.landmark` is not, and `tags`
is optional because only one sample has it.

Validating the first example against its own schema passes; a
record with a string `id` and five missing fields fails clearly:

```
$ python schema_infer.py validate examples/api-response.schema.json bad.json
invalid (6 errors):
  - $: missing required property 'address'
  - $: missing required property 'created_at'
  - $: missing required property 'email'
  - $: missing required property 'score'
  - $: missing required property 'status'
  - $.id: expected integer, got string
```

## Who would use it, and why

Anyone integrating an undocumented API or webhook: point it at a
few captured responses and you get a schema to document the payload,
validate future responses, or feed into a code generator — without
installing anything or uploading data anywhere. It is also the
quick check before writing a hand-made schema: infer first, then
edit the result, instead of starting from a blank file.

## Install / run

No dependencies — Python 3.8+ standard library only.

    git clone <this repo>
    cd day-24-json-schema-infer
    python schema_infer.py infer examples/api-response.json examples/api-response-2.json
    python -m unittest test_schema_infer -v

## Tests

23 tests pass (`python -m unittest test_schema_infer -v`): scalar
types (including bool-not-int and int/float collapsing to number),
format detection (only when all samples agree), enum thresholds,
required-as-intersection, nested objects, merged array items,
mixed-type `anyOf`, `--strict`, validation (missing required, wrong
type, wrong array item, `anyOf` acceptance), and the CLI itself
(stdout output, `--jsonl`, stdin, validate exit codes 0 and 1).

## 2-minute explainer

**Problem:** writing a JSON Schema for an API or webhook by hand
means reading many examples and guessing which fields are required,
which are optional, and which values form a closed set.

**Approach:** infer the schema from the samples themselves — merge
schemas across samples recursively, so `required` is the
intersection of keys, array item schemas are the merge of all
elements, and a field that varies in type becomes `anyOf`. Formats
and enums are added only when every sample (or a small closed set
of values) agrees, so the schema describes what was seen rather
than guessing. A small validator for the emitted subset lets the
same schema gate new data in CI.

**Results:** on the two synthetic example records it infers a
schema that marks `tags` and `address.landmark` optional, `score`
a number, and `created_at`/`email` as `date-time`/`email` strings;
validating a bad record reports all 6 errors with paths and exits
1. 23/23 tests pass.

**Limits:** the schema describes the samples it was shown — a field
that never varied in the samples looks fixed even if the API can
vary it, and a rare optional field may be missing from the schema
entirely if no sample had it. It infers no numeric ranges, string
lengths, or patterns; `format` is a hint, not a check. Feed it
representative samples, then review and edit the result before
treating it as a contract.

## Open source

MIT licensed (see `LICENSE`). Contributions welcome: `minimum` /
`maximum` and `minLength` / `maxLength` inference, `pattern`
detection for ID-like strings, and a `--from-url` mode that fetches
a live endpoint's response would be the obvious next issues.
