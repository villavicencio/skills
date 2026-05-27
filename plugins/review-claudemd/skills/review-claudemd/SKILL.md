---
name: review-claudemd
description: "Mine recent conversation history to improve CLAUDE.md — surface violated rules, missing patterns (scoped local vs global), and stale entries, then apply approved changes. Use to keep CLAUDE.md honest as habits and the project evolve."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.1.0"
---

# /review-claudemd — Improve CLAUDE.md from Conversation History

Use this command to mine recent conversations and find patterns that should be captured
in CLAUDE.md files. Surfaces violated instructions, missing rules, and stale entries.

## Step 1 — Locate this project's transcripts (and bail if there are none)

```bash
# Claude Code stores per-project transcripts under ~/.claude/projects/<encoded-cwd>,
# encoding the path by replacing separators with '-'. Compute that, then fall back to
# a basename search if the encoding doesn't match (e.g. paths containing '.' or '_').
PROJECT_PATH=$(pwd | sed 's|/|-|g' | sed 's|^-||')
CONVO_DIR="$HOME/.claude/projects/-${PROJECT_PATH}"
if [ ! -d "$CONVO_DIR" ]; then
  alt=$(find "$HOME/.claude/projects" -maxdepth 1 -type d -iname "*$(basename "$PWD")" 2>/dev/null | head -1)
  [ -n "$alt" ] && CONVO_DIR="$alt"
fi
if [ ! -d "$CONVO_DIR" ] || [ -z "$(ls -A "$CONVO_DIR"/*.jsonl 2>/dev/null)" ]; then
  echo "review-claudemd: no Claude Code transcripts found for this project ($CONVO_DIR)."
  echo "Nothing to mine — stopping."
  exit 0
fi
echo "=== Recent conversations ==="
ls -lt "$CONVO_DIR"/*.jsonl | head -20
```

If it reports no transcripts, **stop** — there's nothing to analyze.

## Step 2 — Extract recent conversations

```bash
# Private scratch dir: mktemp gives mode 0700 + an unpredictable name, so the
# extracted transcript text (which can contain secrets/private content) isn't
# left world-readable at a guessable /tmp path.
SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/claudemd-review.XXXXXX")

# The current (live) session is the most recently modified transcript and is still
# being written — exclude it to avoid circular self-reference and half-written turns.
current=$(ls -t "$CONVO_DIR"/*.jsonl | head -1)

count=0
for f in $(ls -t "$CONVO_DIR"/*.jsonl | head -21); do   # +1 so dropping the current still leaves ~20
  [ "$f" = "$current" ] && continue
  base=$(basename "$f" .jsonl)
  # Content is either a plain string OR an array of typed blocks. `texts` handles both;
  # it keeps user+assistant TEXT and drops tool_result/tool_use/thinking noise. The
  # naive `"USER: " + .message.content` crashes on array content and silently loses the
  # user's actual instructions — the very signal this skill exists to mine.
  jq -r '
    def texts: if type=="string" then . else (map(select(.type=="text")|.text)|join("\n")) end;
    if .type=="user" then
      ((.message.content // []) | texts) as $t | (if ($t|length)>0 then "USER: "+$t else empty end)
    elif .type=="assistant" then
      ((.message.content // []) | texts) as $t | (if ($t|length)>0 then "ASSISTANT: "+$t else empty end)
    else empty end
  ' "$f" > "$SCRATCH/${base}.txt" 2>/dev/null
  count=$((count+1))
done

if [ -z "$(ls -A "$SCRATCH" 2>/dev/null)" ]; then
  echo "review-claudemd: only the current session exists — no prior transcripts to mine. Stopping."
  rmdir "$SCRATCH" 2>/dev/null
  exit 0
fi
echo "=== Extracted $count transcript(s) (current session excluded) into: $SCRATCH ==="
ls -lhS "$SCRATCH"
```

Note the printed `$SCRATCH` path — you'll reference it in Steps 3 and 6.

## Step 3 — Analyze with parallel subagents

Launch parallel Sonnet subagents to analyze the extracted conversations. Each agent reads:
- Global CLAUDE.md: `~/.claude/CLAUDE.md`
- Local CLAUDE.md: `./CLAUDE.md` (if it exists)
- The auto-memory index, if present: `$CONVO_DIR/memory/MEMORY.md`
- A batch of conversation files from `$SCRATCH`

Give each agent this prompt:

```
Read:
1. Global CLAUDE.md: ~/.claude/CLAUDE.md
2. Local CLAUDE.md: [project]/CLAUDE.md (if it exists)
3. Existing memory index (if it exists): [memory MEMORY.md path]
4. Conversations: [list of files]

Compare what ACTUALLY happened in the conversations against BOTH CLAUDE.md files. Find:
1. Instructions that EXIST but were VIOLATED. For each: quote the rule, cite the
   session file + a ≤1-line quote showing the violation, and diagnose the cause —
   ambiguous wording (→ reword) or a clear rule that was ignored (→ reinforce / move
   somewhere more prominent)?
2. Patterns that should be ADDED to LOCAL CLAUDE.md (project-specific).
3. Patterns that should be ADDED to GLOBAL CLAUDE.md (applies everywhere).
4. Entries in either file that now appear outdated or unnecessary.

Rules for proposing — keep signal high:
- Propose a NEW rule only if the pattern RECURS (≥2 distinct instances); cite each. A
  one-off slip is not a rule.
- EVERY finding must carry evidence: session file + a ≤1-line quote. No evidence → drop it.
- Skip anything already covered by the existing CLAUDE.md or MEMORY.md.

Output: bullet points grouped by the four categories, each bullet ending with its citation.
```

Batch conversations by size:
- Large (>100KB): 1-2 per agent
- Medium (10-100KB): 3-5 per agent
- Small (<10KB): 5-10 per agent

## Step 4 — Aggregate and present findings

Combine results from all agents into a summary with these sections:

1. **Instructions violated** — existing rules that weren't followed, with cause (reword vs reinforce)
2. **Suggested additions — LOCAL** — project-specific patterns worth capturing
3. **Suggested additions — GLOBAL** — patterns that apply across all projects
4. **Potentially outdated** — items that may no longer be relevant

De-duplicate findings that multiple agents surfaced, and **rank by recurrence** (most-cited
first). Keep each finding's evidence citation. Present as tables or bullet points, then ask
the user which changes they want applied before editing any files.

## Step 5 — Apply approved changes

Only after user approval, edit the relevant CLAUDE.md file(s). Do not auto-commit — let
the user review the diff first.

## Step 6 — Clean up

Remove the scratch dir (use the actual `$SCRATCH` path printed in Step 2):

```bash
rm -rf "$SCRATCH"
```

## Notes
- Requires `jq` (it's in the Brewfile).
- Subagents should use Sonnet for cost efficiency — the analysis doesn't need Opus.
- The current session is excluded automatically (Step 2) to avoid circular self-reference.
