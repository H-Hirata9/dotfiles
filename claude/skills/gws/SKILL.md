---
name: gws
description: Operate the user's Google Workspace (Gmail, Calendar, Google Tasks, Drive, Docs, Sheets, Slides, Keep, People) through the installed `gws` CLI. Use this whenever the user asks to send/read/triage email, check or create calendar events, add/list/complete to-do items or reminders, or read/write/search files in their Google account — even if they don't say "Google" or name the CLI. Prefer this over the Google MCP tools: gws is a single authenticated CLI that covers everything except Fitbit-based health data. Also covers registering checkbox-style reminders into Google Tasks for the user's phone.
---

# gws — Google Workspace CLI

`gws` is a single authenticated CLI over the whole Google Workspace API surface. It's already
installed (v0.22.5+) and authenticated for the user's account, so there's no setup — just call it.
Use it instead of the `claude_ai_Gmail` / `Google_Calendar` / `Google_Drive` MCP tools: one uniform
tool, fewer round-trips, and it reaches services the MCP doesn't (Tasks, Docs, Sheets, Keep, etc.).

The one thing gws does **not** cover is the user's health pipeline (Fitbit → Google Health). That
stays on its own scripts — don't route health work through here.

## Universal invocation

```
gws <service> <resource> [sub-resource] <method> [flags]
```

- `--params '<JSON>'` — URL/query/path parameters (e.g. ids, filters, pageSize)
- `--json '<JSON>'` — request body for create/update (POST/PATCH/PUT)
- `--format json|table|yaml|csv` — output shape (json is default; use `table` when reporting to the user)
- `--dry-run` — validate without sending. **Use this first for anything that writes**, so you can
  show the user what will happen before it happens.
- `--page-all` — auto-paginate (NDJSON, one page per line)

Most services also expose **`+helper`** shortcuts (note the leading `+`) that wrap the common case
with friendly flags. Prefer helpers for everyday actions; drop to raw `resource method` when you need
something a helper doesn't expose.

When you need a method or field this skill doesn't list, the CLI is self-documenting — discover it
rather than guessing:

```
gws <service> --help                     # list resources + helpers
gws <service> <resource> --help          # list methods
gws schema <service.resource.method>     # exact params + body schema
```

## Gmail

```
gws gmail +triage                                   # unread inbox summary (sender/subject/date)
gws gmail +triage --query 'from:boss is:unread' --max 10
gws gmail +read --id <messageId>                    # read one message body (--headers for From/To/Subject)
gws gmail +send --to a@x.com --subject '件名' --body '本文'
gws gmail +send --to a@x.com --subject '件名' --body '本文' --cc b@x.com -a report.pdf
gws gmail +send ... --draft                         # save as draft instead of sending
gws gmail +reply --message-id <messageId> --body '返信本文'   # threading handled
```

Raw resource access (search, labels, etc.): `gws gmail users messages list --params '{"userId":"me","q":"label:unread"}'`.

## Calendar

```
gws calendar +agenda --today
gws calendar +agenda --week
gws calendar +agenda --days 3
gws calendar +insert --summary '打ち合わせ' \
  --start '2026-06-22T14:00:00+09:00' --end '2026-06-22T15:00:00+09:00'
gws calendar +insert --summary 'MTG' --start ... --end ... --attendee a@x.com --meet
```

Times are RFC3339. The user is in JST — write `+09:00`. For edits/deletes use the raw resource:
`gws calendar events list|patch|delete --params '{"calendarId":"primary",...}'`.

## Google Tasks  (checkbox reminders)

Use `@default` as the task list id for the user's main list (no need to look up the real id).

```
gws tasks tasks list --params '{"tasklist":"@default"}'
gws tasks tasks insert --params '{"tasklist":"@default"}' \
  --json '{"title":"受験票を準備する","notes":"証明写真も","due":"2026-06-25T00:00:00Z"}'
gws tasks tasks patch  --params '{"tasklist":"@default","task":"<taskId>"}' \
  --json '{"status":"completed"}'                  # check it off
gws tasks tasks delete --params '{"tasklist":"@default","task":"<taskId>"}'
gws tasks tasklists list                            # see all lists + their ids
```

`due` is RFC3339 in UTC and Google Tasks stores **date only** (time is ignored), so the day is what
matters. Use `00:00:00Z` and pick the date the user means.

## Drive / Docs / Sheets / Slides

```
gws drive files list --params '{"q":"name contains \"請求\"","pageSize":10}' --format table
gws drive files get  --params '{"fileId":"<id>"}'
gws drive +upload <localpath>                       # upload with auto metadata
gws sheets spreadsheets values get --params '{"spreadsheetId":"<id>","range":"Sheet1!A1:C10"}'
gws docs documents get --params '{"documentId":"<id>"}'
```

For Slides, Keep, People, Forms, Chat, Meet, Classroom: same pattern — `gws <service> --help` to
discover resources, `gws schema ...` for exact shapes.

## ADA operating rules

**Writes need confirmation.** Sending email, creating/deleting calendar events, deleting Drive
files, and any irreversible or outward-facing action follow the normal HITL approval flow. `--dry-run`
first, show the user the concrete request, then execute on approval. Reads (triage, agenda, list,
search) don't need approval.

**Never** put the user's email contents, contacts, or file contents into external services or
Telegram beyond what's needed to answer. Treat message/file bodies as private.

**Tasks vs ada-board — where a to-do lives:**

- **ada-board** (GitHub Issues) stays the source of truth for *development tasks and design
  decisions* — anything tied to code, projects, or ADA's own work.
- **Google Tasks** is for the user's *personal life reminders* that they want to tick off on their
  phone: errands, deadlines, prep tasks, appointments-to-arrange (e.g. "受験票を準備する", "ふるさと
  納税の上限を確認"). The value is the checkbox on mobile.

When a request is clearly a life reminder, put it in Google Tasks. When it's project/dev work, use
ada-board. If it's genuinely both or ambiguous, ask which the user wants rather than double-filing.
