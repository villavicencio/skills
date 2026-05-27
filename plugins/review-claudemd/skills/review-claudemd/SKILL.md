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

## Steps

### Step 1 — Find conversation history

```bash
PROJECT_PATH=$(pwd | sed 's|/|-|g' | sed 's|^-||')
CONVO_DIR=~/.claude/projects/-${PROJECT_PATH}
echo "=== Recent conversations ==="
ls -lt "$CONVO_DIR"/*.jsonl 2>/dev/null | head -20
```

### Step 2 — Extract recent conversations

```bash
SCRATCH=/tmp/claudemd-review-$(date +%s)
mkdir -p "$SCRATCH"

for f in $(ls -t "$CONVO_DIR"/*.jsonl | head -20); do
  basename=$(basename "$f" .jsonl)
  cat "$f" | jq -r '
    if .type == "user" then
      "USER: " + (.message.content // "")
    elif .type == "assistant" then
      "ASSISTANT: " + ((.message.content // []) | map(select(.type == "text") | .text) | join("\n"))
    else
      empty
    end
  ' 2>/dev/null | grep -v "^ASSISTANT: $" > "$SCRATCH/${basename}.txt"
done

echo "=== Extracted ==="
ls -lhS "$SCRATCH"
```

### Step 3 — Analyze with parallel subagents

Launch parallel Sonnet subagents to analyze conversations. Each agent reads:
- Global CLAUDE.md: `~/.claude/CLAUDE.md`
- Local CLAUDE.md: `./CLAUDE.md` (if exists)
- A batch of conversation files

Give each agent this prompt:

```
Read:
1. Global CLAUDE.md: ~/.claude/CLAUDE.md
2. Local CLAUDE.md: [project]/CLAUDE.md
3. Conversations: [list of files]

Analyze the conversations against BOTH CLAUDE.md files. Find:
1. Instructions that exist but were violated (need reinforcement or rewording)
2. Patterns that should be added to LOCAL CLAUDE.md (project-specific)
3. Patterns that should be added to GLOBAL CLAUDE.md (applies everywhere)
4. Anything in either file that seems outdated or unnecessary

Be specific. Output bullet points only.
```

Batch conversations by size:
- Large (>100KB): 1-2 per agent
- Medium (10-100KB): 3-5 per agent
- Small (<10KB): 5-10 per agent

### Step 4 — Aggregate and present findings

Combine results from all agents into a summary with these sections:

1. **Instructions violated** — existing rules that weren't followed (need stronger wording)
2. **Suggested additions — LOCAL** — project-specific patterns worth capturing
3. **Suggested additions — GLOBAL** — patterns that apply across all projects
4. **Potentially outdated** — items that may no longer be relevant

Present as tables or bullet points. Ask the user which changes they want applied before editing any files.

### Step 5 — Apply approved changes

Only after user approval, edit the relevant CLAUDE.md file(s). Do not auto-commit — let
the user review the diff first.

## Notes
- Requires `jq` to be installed (it's in the Brewfile)
- Subagents should use Sonnet for cost efficiency — the analysis doesn't need Opus
- Skip the current conversation to avoid circular self-reference
- Clean up the scratch dir when done: `rm -rf "$SCRATCH"`
