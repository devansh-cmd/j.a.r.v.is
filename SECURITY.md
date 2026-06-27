# Security

## Secrets policy

**No secret is ever hardcoded in this repository.** Every credential is read
from an environment variable at runtime.

| Secret | How it's loaded | Where it lives |
| ------ | --------------- | -------------- |
| `ANTHROPIC_API_KEY` | `os.getenv("ANTHROPIC_API_KEY")` in `core/brain.py` | your local `.env` (gitignored) |
| `ELEVENLABS_API_KEY` *(optional, future)* | env var | your local `.env` (gitignored) |

`.env` is listed in [`.gitignore`](.gitignore) and has **never** been committed.
Only `.env.example` (a placeholder template with no real values) is tracked.

### Why your key is safe even though this repo is public

Jarvis is a **local desktop application**, not a web app. The UI (the PySide6
HUD) runs only on your machine — it is never served to a browser, so there is no
client-side bundle that could leak a key. Your API key is read from your local
`.env` into the local Python process and never leaves your computer. Cloning this
repo gives someone the *code*; they must supply *their own* key to run it.

## Pre-commit secret guard

A pre-commit hook ([`scripts/git-hooks/pre-commit`](scripts/git-hooks/pre-commit))
blocks any commit that contains something resembling an API key, cloud
credential, private key, or a `.env` file. Activate it after cloning:

```sh
git config core.hooksPath scripts/git-hooks
```

To bypass on a confirmed false positive: `git commit --no-verify`.

### Recommended: enable GitHub push protection

In the repo on GitHub → **Settings → Code security** → enable
**Secret scanning** and **Push protection**. This is a free, server-side backstop
that rejects pushes containing detected secrets even if the local hook is skipped.

## Capability note — the `shell` tool

Jarvis can execute PowerShell on your machine via the `shell` tool, running with
your normal user privileges. This is intentional (it's a personal assistant), but
it means you should not point Jarvis at untrusted instructions or expose its input
to the public internet. Keep it local and personal.

## Rotating a key

If you ever suspect a key was exposed, rotate it immediately at
<https://console.anthropic.com/settings/keys> — revoking the old key makes any
leaked copy useless. This is faster and safer than trying to scrub history.
