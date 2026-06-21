# Hub_ML Resource Registry Schema

`content/resources/ml_ds_resources.json` is a curated registry of external learning sources.

The registry exists to support content quality gates:

- notes cite registered, authoritative URLs;
- practice/tasks/projects can trace back to sources;
- Hub_ML curates and cites sources instead of ingesting and generating bulk content.

## Record Shape

Required fields are marked with `*`.

| Field | Required | Type | Notes |
| --- | --- | --- | --- |
| `id` | * | string | Unique snake_case slug. |
| `title` | * | string | Human-readable title. |
| `track` | * | string | Must exactly match a track in `content/roadmap/coverage_matrix.json`. |
| `subtrack` |  | string | Optional narrower topic. |
| `type` | * | enum | `course`, `guide`, `book`, `interactive`, `video`, `paper`, `docs`, `cheatsheet`. |
| `language` | * | enum | `en`, `ru`, `multi`. |
| `level` |  | enum | `beginner`, `intermediate`, `advanced`. |
| `cost` | * | enum | `free`, `freemium`, `paid`. |
| `access` |  | enum | `open`, `signup`, `trial`. |
| `url` | * | string | Must be a real `http(s)` URL, not a placeholder. |
| `priority` |  | enum | `core`, `support`, `deep_dive`, `later`. |
| `status` |  | enum | `active`, `stale`. |
| `recommended_stage` |  | string | Free string naming the coverage stage or sprint. |
| `related_hubml_modules` |  | string array | Examples: `Theory`, `Practice`, `Tasks`, `Data Lab`, `ML Lab`, `Notebook`. |
| `expected_output` |  | string array | Examples: `note`, `practice_card`, `mentor_task`, `project`, `model_card`. |
| `notes` |  | string | Short rationale. |

## Validation Rules

`tools/validate_resources.py` fails when:

- any required field is missing or empty;
- an enum field has a value outside its allowed set;
- an `id` is duplicated;
- a URL is missing `http(s)` scheme;
- a URL contains placeholders such as `example.com`, `TODO`, `<`, or `xxx`;
- a `track` is not present in the coverage matrix.

Successful validation prints:

```text
resources OK: N records, M tracks covered
```
