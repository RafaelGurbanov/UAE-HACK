# kb/data: structured answers for offline mode

In **offline mode** (free, no API key, no AI generation) the website answers from the entries in these files. Every `*.json` file here, except `schema.json`, is a JSON **list of entries**. Use one file per topic area.

## Add an entry
1. Open the file for the topic, or create a new `<topic>.json` containing `[ ]`.
2. Copy an existing entry and give it a new, unique `id` (lowercase letters, digits, `-` or `_`).
3. Fill in the fields (the full schema is in `schema.json`):

| Field | What to write |
|---|---|
| `id` | Unique and stable, e.g. `children-data-consent` |
| `topic` | Short topic name; shown as a suggestion when nothing matches |
| `keywords.en` / `.ar` / `.az` | Search terms **and paraphrases** in English, Arabic and Azerbaijani. Include inflected forms (e.g. `uşaq`, `uşağın`, `uşaqların`; `الطفل`, `الأطفال`). Matching is mostly word-based, so this is what makes Arabic and Azerbaijani questions find the entry. |
| `question` | The canonical question this entry answers |
| `answer` | The answer text shown to the user, word for word (nothing is generated) |
| `citations[]` | `law`, `article`, `layer` (`uae_federal`, `emirate` or `global_example`), `url`, `quote` (exact text from the official source), `verified` |
| `pipeline_nodes` | Any of `SRC C PP M P D SINK` |
| `readiness_dimensions` | Any of the 8 ids in `schema.json` |
| `requires_human_decision` | `true` if the answer affects a child |
| `status` | `draft`, `reviewed`, `approved` or `retired` (retired entries are never returned) |
| `last_checked` | `YYYY-MM-DD`, or `null` |

4. Check your changes: `.\scripts\validate-data.ps1` (or `python -m app.kb.validate_data` from `backend`).
5. The running backend reloads changed files automatically; there is no need to restart it.

## Rules
- **Never invent sources.** Until a person has checked the official text, use `"SOURCE TO BE VERIFIED"` for `law`, `article` and `quote`, leave `url` as `""`, and keep `verified: false`.
- Set `verified: true` only after checking law, article and exact quote against the official source. The website shows a **Verified** badge only then, and "Source to be verified" otherwise.
- The official Arabic text prevails. Prefer quoting the Arabic original.

## What the validator reports
- Schema errors, with the file, entry and field.
- Duplicate ids.
- Entries without citations.
- Entries with `verified=false` or placeholder sources.
- Drafts.
- Entries not checked in the last 180 days.

It exits with an error only on schema errors or duplicate ids.

## Seed entries
The 8 starter entries contain **draft guidance with placeholder citations only**. Replace them with verified content before relying on them.
