---
name: twitter
description: Fetch and summarize an X/Twitter post (and any long-form Article content) from a URL, using the public api.fxtwitter.com endpoint via curl and jq (no auth, API keys, or MCP). Use when the user shares an x.com or twitter.com status URL or asks to read, fetch, or summarize a tweet — WebFetch cannot access x.com, so this is the reliable path.
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.2.2"
---

# /twitter — Fetch X/Twitter Post and Replies

Fetch and summarize an X/Twitter post with replies. The post URL is the argument: `$ARGUMENTS`.

## Steps

### Step 1 — Extract the tweet ID

Parse the tweet ID from the URL (`$ARGUMENTS`). It's the numeric string in the path:
- `https://x.com/user/status/1234567890` → `1234567890`
- `https://twitter.com/user/status/1234567890` → `1234567890`

Also extract the username from the URL.

### Step 2 — Fetch the post via fxtwitter API

```bash
curl -s "https://api.fxtwitter.com/<username>/status/<tweet_id>" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  -H "Accept: application/json"
```

### Step 3 — Parse and present

Extract from the JSON response:
- **Tweet text**: `.tweet.text`
- **Author**: `.tweet.author.name` (`@.tweet.author.screen_name`)
- **Stats**: `.tweet.likes`, `.tweet.retweets`, `.tweet.replies`, `.tweet.views`
- **Article** (if present): `.tweet.article.content.blocks` — this contains long-form
  articles posted as Twitter Articles. Parse the blocks array for text content.
- **Media**: `.tweet.media` for any images/videos
- **Date**: `.tweet.created_at`

Present as:
1. **Author and stats** — who posted, engagement numbers
2. **Tweet text** — full content
3. **Article content** (if present) — formatted as markdown with headers
4. **Key takeaways** — summarize the actionable insights

### Step 4 — Fetch replies (if requested)

If the user asks for replies/comments, note that the fxtwitter API does not return
reply threads. Inform the user and suggest they paste key replies manually, or
try fetching the conversation via:

```bash
curl -s "https://api.fxtwitter.com/<username>/status/<tweet_id>" \
  -H "Accept: application/json" | jq '.tweet.replying_to_status'
```

## Notes
- fxtwitter API works without auth, API keys, or MCP servers
- Always use this for X/Twitter URLs — WebFetch cannot access x.com
- Supports Twitter Articles (long-form posts) via the `.article` field
- If the API returns an error, verify the tweet ID is correct and the post is public
