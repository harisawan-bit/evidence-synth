# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

We take the security of `evidence-synth` seriously. If you discover a security
vulnerability, please **do not open a public GitHub issue**.

Instead, report it privately:

- Use GitHub's private vulnerability reporting on this repository
  (`Security` tab → `Report a vulnerability`), **or**
- Email the maintainers at **security@harisawan.example** (replace with the
  real contact before publishing).

Please include:

- a description of the vulnerability and its impact,
- steps to reproduce (PoC / minimal repro),
- affected versions,
- any suggested remediation.

We will acknowledge your report within **5 business days**, and aim to provide
a remediation timeline within **15 business days**. Credit will be given in the
release notes unless you request to remain anonymous.

## Scope notes

`evidence-synth` is a research-automation framework. A few things are **out of
scope** for security responses:

- The `openai` screening backend relies on your own API key; never commit it.
  Leaked keys should be revoked at the provider, not reported here.
- Live PubMed queries go to NCBI E-utilities over HTTPS; we do not proxy or
  store query responses.
- The bundled sample corpus is synthetic and contains no real personal data.

## Safe defaults

- No network calls are made unless you explicitly invoke `run` or `novelty`.
- The `demo` command runs fully offline against the bundled sample corpus.
- Tests are deterministic and offline (`pip install -e ".[dev]" && pytest`).
