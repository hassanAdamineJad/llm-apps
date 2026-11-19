# Repository guidance

This repository is a collection of small, independent LLM applications.

- Keep every app independently installable and runnable from its own directory. An app may choose its own dependencies, UI stack, and run command.
- List every app in the root `README.md`, with a link to its own documentation.
- Document every environment variable in the app README and provide a safe `.env.example` when appropriate.
- Keep secrets and provider credentials on the server. Never expose them to browser code, browser responses, logs, or committed files.
- Record significant decisions and their reasons in the nearest `DECISIONS.dcm` file. Keep app-specific decisions inside the app directory.
- Do not extract shared packages until at least two apps have a concrete need for the same code.

