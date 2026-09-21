# Security Policy

## Supported Versions

Only the latest published release on PyPI is actively supported with
security fixes.

| Version | Supported |
|---|---|
| Latest (2.x) | Yes |
| < 2.0 (hackathon builds) | No |

## Reporting a Vulnerability

If you find a security issue, please do not open a public GitHub issue.

Instead, report it privately through GitHub's **Security Advisories**
tab on this repository (Security > Advisories > Report a vulnerability),
or by opening a private discussion with the maintainer.

Please include:
- A description of the vulnerability and its potential impact
- Steps to reproduce it
- Any relevant contract samples or logs (with sensitive data removed)

We aim to acknowledge reports within a few days and to release a fix or
mitigation as soon as reasonably possible.

## Scope Notes

- Hermes Legal Advisor's offline provider and CLI run entirely locally;
  no contract text is sent anywhere unless you explicitly configure a
  hosted LLM provider (Groq, Gemini, OpenRouter).
- When using a hosted provider, contract text is sent to that provider
  according to their own privacy policy. Use the offline provider or
  Ollama (fully local) for confidential material.
- The local web dashboard (`hermes-legal serve`) binds to
  `127.0.0.1` by default and is not intended to be exposed to the
  public internet without additional authentication.
