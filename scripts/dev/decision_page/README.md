# Decision Page

Turns a list of decisions into one self-contained HTML page. Each card is one
decision with a recommended option. The reader clicks an option per card, or
**Accept all recommended**, and presses **Save decisions**. That downloads a
JSON file and copies a short text block to the clipboard:

```text
Example cleanup decisions
D01 delete
D02 move — keep the old name in a note
```

Use it whenever a review produces more items than a person can hold in their
head (cleanup inventories, triage lists). Keep items that need no decision out
of the cards; put them in the optional reference table instead.

## Build

```bash
python3 scripts/dev/decision_page/build_decision_page.py spec.json -o page.html
```

Add `--measure-root <dir>` to fill a card's `size` from its `paths` (globs,
relative to `<dir>`) when the spec leaves `size` out. The page needs no server
and no network; choices persist in the browser's local storage per page title.
Write pages for private material under `.private/notes/`, not in tracked homes.

## Spec

See `example_spec.json`.

| Field | Required | Meaning |
| --- | --- | --- |
| `title` | yes | Page title; also names the storage key and export file |
| `sections[]` | yes | `{id, title, subtitle?}`; cards are grouped in this order |
| `cards[]` | yes | One decision each (fields below) |
| `intro[]` | no | List items at the top (trusted HTML); a generic three-step guide by default |
| `note` | no | Paragraph under the intro; supports `` `code` `` and `**bold**` |
| `tally` | no | `{choice, label}`: header sums the `size` of cards set to `choice`, e.g. `{"choice": "delete", "label": "frees"}` |
| `table` | no | `{title?, columns[], rows[]}` reference table with a filter box |
| `storage_key`, `export_name` | no | Override the derived names |

Card fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `id`, `section`, `title`, `what` | yes | Identity and the one-line description |
| `options` | yes | `[[key, label], ...]`, at least two; an optional third element sets the colour tone (`del`, `move`, `keep`, `neutral`) |
| `rec` | yes | The recommended option key |
| `why`, `if_yes`, `if_no` | no | Reasoning and consequences; `{size}` in `if_yes` becomes the size label |
| `paths`, `dest`, `mapping` | no | Paths affected, destination, `[[old, new], ...]` rename table |
| `size` / `size_label` | no | Bytes (formatted automatically) or a ready label |
| `chips` | no | `[[label, tone], ...]` with tone `ok`, `warn`, or `neutral` |

Option keys `delete`, `remove`, `move`, `track`, `merge`, `rename`, `keep`,
`skip`, and `later` get a colour tone automatically.

Tests: `tests/unit/test_decision_page.py`.
