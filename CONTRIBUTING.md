# Contributing

Thanks for helping with VoxCPM2 API.

## First evening path

Clone, install the CI extras, and run what works without downloading the VoxCPM2 model.

```bash
git clone https://github.com/shiftbloom-studio/voxcpm2-api.git
cd voxcpm2-api
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
pytest
ruff check .
voxcpm2-api
```

In another terminal:

```bash
curl http://localhost:8000/health
```

`VOXCPM2_STARTUP_LOAD_MODEL` defaults to `false`, so the process starts without loading weights. `/health` and `/v1/runtime` work in that mode. Real `/v1/speech` needs the `voxcpm` extra and a model.

`./scripts/bootstrap.sh` installs `.[dev,voxcpm]` when you want that heavier path.

## Optional extras

CI and docs-only changes use `[dev]`. Add the others only when you need the matching runtime:

| Extra | When it is required |
| --- | --- |
| `dev` | pytest, `ruff check .`, packaging |
| `voxcpm` | official backend, prompt or reference audio, real synthesis |
| `nanovllm` | Linux CUDA `nano-vllm-voxcpm` path |
| `asr` | `/v1/transcribe` via faster-whisper |

## Desktop UI

The Tauri client in [`voxcpm2-ui/`](./voxcpm2-ui) is optional for API work.

```bash
cd voxcpm2-ui/src-tauri
cargo tauri dev
```

## Claiming an issue

Issues labeled `help wanted` or `good first issue` are real engineering tasks, not
diff-shaped homework. Before you write code:

1. Comment on the issue with a short explanation of your **approach**: which files you expect to
   touch, which of the issue's open questions you'd answer which way, and anything
   you'd do differently than the issue suggests.
2. Wait for a maintainer 👍 (usually within a few days). That confirms nobody else
   is already on it and that the direction is right - it saves you throwaway work.
3. Reference the issue in your PR (`Closes #123`).

PRs that skip the discussion step might be closed with a pointer back to it. We are
not gatekeeping effort - we are protecting *yours*: several of these tasks have
design decisions worth debating before anyone types code.

## AI-assisted contributions

shiftbloom studio is a digital studio for creative people. We use
AI as a tool, the same way we use a compiler, and we work on making it better and safer;
neither stance means we pretend the tools don't exist. Using AI assistance on a
contribution is welcome - as long as a human stands behind the result:

- **You checked it yourself.** Review what AI produced before sending
  it: does it actually answer the issue, do the claims in the description match
  the diff, do the tests pass because the code is right and not because they are
  shallow?
- **You own the result.** You must be able to answer review questions about the
  change, defend the design decisions, and maintain it if it breaks. If you
  can't explain your PR, don't send it.

A PR body that only restates the diff doesn't tell us anything we can't read in
the diff - the decision section exists (for medium+ tasks) so we can see that someone
thought about the tradeoffs, whoever drafted the words.

## Pull requests

- Keep the change focused and small enough to review.
- Run `pytest` and `ruff check .` before opening a PR.
- Use conventional commits (`docs:`, `fix:`, `feat:`, `chore:`, `ci:`).
- Fill in the PR template. The decision section is the part we read first (for medium+ tasks).
- Release wheels and tags live under [shiftbloom-studio/voxcpm2-api](https://github.com/shiftbloom-studio/voxcpm2-api), not the old `fabianzimber/voxcpm2-api` remote.

## Security

Report vulnerabilities privately. Do not open public issues or pull requests that include exploit details.

Contributions are licensed under AGPL-3.0-only, the same as the rest of the repository.
