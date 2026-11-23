# dv — v0.25.0

Minor release. `dv:critique` lets the caller set the model and effort of its three critique
agents. The other fifteen skills have no behaviour changes; their version moves to `0.25.0` only
because the suite is released as one plugin.

Numbering: 0.25.0 follows 0.24.0, which added the reviewer-wait and leftover-shell rules to
`dv:manager-mode`.

Why: the three agents were fixed on Sonnet with no effort set, so a caller who wanted a deeper or
cheaper critique had no way to ask for it (VIL-801).

## Changed

- **`dv:critique`, arguments.** The arguments can start with `model:` and `effort:` settings:
  `/dv:critique model: opus effort: high migrate from NVM to fnm`. `model` takes `haiku`,
  `sonnet` or `opus`; `effort` takes `low`, `medium`, `high`, `xhigh` or `max`. Either may be
  left out, and a leading `model:` or `effort:` is a setting, not part of the change to critique.
- **`dv:critique`, Step 2 and Notes.** All three agents run on the given `model` (default:
  Sonnet). If an `effort` is given, each agent gets it; if not, none is set. With no settings
  the behaviour is unchanged.
- **`dv:critique`, usage examples** use the `/dv:critique` name instead of `/critique`.

## Not tested

The text is a behaviour rule for a model; it is proved the next time `dv:critique` runs with
`model:` or `effort:` set.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
