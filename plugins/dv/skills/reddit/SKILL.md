---
name: reddit
description: Fetch and summarize a Reddit post with all its comments from a URL, using the public Reddit .json API via curl and jq (no auth, API keys, or MCP). Use when the user shares a Reddit URL or asks to read, fetch, or summarize a Reddit thread — WebFetch cannot access reddit.com, so this is the reliable path.
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.2.2"
---

# /reddit — Fetch Reddit Post and Comments

Fetch and summarize a Reddit post with all comments. The post URL is the argument: `$ARGUMENTS`.

## Steps

### Step 1 — Resolve the URL

Start from the argument, and resolve short links (those containing `/s/`) by following
the redirect to their canonical form:

```bash
URL="$ARGUMENTS"
if [[ "$URL" == *"/s/"* ]]; then
  URL=$(curl -sI "$URL" -L -o /dev/null -w '%{url_effective}')
fi
echo "$URL"
```

### Step 2 — Fetch the post and comments

Append `.json` to the canonical URL and fetch:

```bash
curl -s "${URL}.json?limit=100&depth=5" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  -H "Accept: application/json"
```

### Step 3 — Parse and present

Extract from the JSON:
- **Post**: `data[0].data.children[0].data.selftext` for body, `.title` for title, `.score` for votes
- **Comments**: `data[1].data.children` — recurse `.replies.data.children` for nested replies

Use `jq` to extract. Present as:

1. **Post title and body** — full content, formatted as markdown
2. **Top comments** — sorted by score, include author and score
3. **Key takeaways** — summarize the actionable insights at the end

## Notes
- This works without auth, API keys, or MCP servers
- Always use this approach for Reddit URLs — WebFetch cannot access Reddit
- If the URL returns an error, check that `.json` was appended correctly
