# AGENTS.md

## Project Overview

- This repository contains a small Python web app that shows the weekly weather forecast for Kanagawa Prefecture.
- The main application entrypoint is `src/main.py`.
- Tests live under `tests/`.
- Deployment-related files live in `.github/workflows/` and `render.yaml`.

## Working Rules

- Keep changes aligned with the current product scope: a Kanagawa weather viewer built on the Python standard library.
- Prefer small, reviewable changes over broad rewrites.
- Prefer the Python standard library unless an external dependency has a clear, justified benefit.
- Update `README.md` when setup, runtime behavior, deployment flow, or environment variables change.
- Keep `.github/copilot-instructions.md` and this file consistent with the actual repository purpose.
- If behavior exposed to users changes, update tests and any related deployment or operations docs in the same change.

## Guardrails

- Never commit passwords, API keys, access tokens, private keys, deploy hook URLs, cookies, or any other secret material to the repository.
- Never place real secrets in source code, tests, fixtures, docs, issue bodies, pull request descriptions, or sample config files.
- Use environment variables or the target platform's secret management for sensitive values. Commit only placeholder names or clearly fake examples.
- Treat `.env` files, credential exports, SSH keys, and service account files as non-committable unless the file is an intentionally fake example created for documentation.
- If a secret is discovered in the working tree, stop and remove it from the pending change before commit or push. If it may already have been exposed, tell the user that rotation is required.
- Avoid printing or copying secret values into logs, terminal transcripts, screenshots, or generated documentation.
- Do not weaken security-related behavior such as escaping remote content, request timeouts, response size limits, or defensive headers without a clear reason.

## Local Validation

- Run compile checks with `python -m compileall src tests`.
- Run tests with `python -m unittest discover -s tests -v`.
- When changing request handling, rendering, or payload parsing, add or update tests in `tests/test_main.py`.
- Prefer assertions on complete returned structures when practical, instead of checking many individual fields one by one.

## Deployment Notes

- Render configuration is defined in `render.yaml`.
- GitHub Actions CI and deploy workflows are defined in `.github/workflows/`.
- Be careful when changing `/healthz`, because it is used by Render health checks.
- If you change environment variables, startup behavior, or health check semantics, update `README.md`, `render.yaml`, and related workflows together.

## Commit Scope

- Do not commit local-only files such as `.vscode/`, `.venv/`, or `__pycache__/`.
- Stage files explicitly when the working tree contains mixed changes.

## Pull Requests

- Keep each PR focused on a single change or a tightly related set of changes.
- Prefer draft PRs while work is still in progress or when behavior, deploy flow, or operations impact is still being validated.
- In the PR description, include what changed, why it changed, how it was validated, and any follow-up work or known limitations.
- Link related issues when applicable so reviewers can trace the reason for the change.
- If the change affects deployment, health checks, environment variables, or GitHub Actions, call that out explicitly in the PR description.
- Never include secrets, tokens, deploy hook URLs, or other sensitive values in PR titles, descriptions, comments, screenshots, or logs.

## Code Organization

- Avoid continuing to grow `src/main.py` indefinitely. If new functionality is substantial, prefer extracting focused modules while keeping tests close to the changed behavior.
- Do not add one-off helper functions that are only used once unless they materially improve readability.

## Terraform

- If you need to write Terraform code in this repository, use Cloud Posse's component repositories as the style reference:
  `https://github.com/orgs/cloudposse-terraform-components/repositories`
