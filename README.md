# Small LLM Apps

A monorepo of focused, independently runnable applications that use large language models to solve one clear task. Each app owns its dependencies, configuration, UI, and run command so experiments can evolve without coupling the whole collection together.

## Apps

| App | What it does | Status |
| --- | --- | --- |
| [Website Brochure](apps/website-brochure/) | Reads one public web page and turns its factual content into a themed, printable brochure. | Available |

## Quick start: Website Brochure

From the repository root:

```bash
python3 -m venv apps/website-brochure/.venv
source apps/website-brochure/.venv/bin/activate
python -m pip install -e "apps/website-brochure[dev]"
cp apps/website-brochure/.env.example apps/website-brochure/.env
# Edit apps/website-brochure/.env for OpenAI or Ollama, then:
python -m website_brochure
```

Open <http://127.0.0.1:8000>. Enter a public HTTP(S) page, choose a brochure category, and generate a factual summary plus brochure. After generation, switch among three visual themes, pick an accent color without another LLM call, and print or save the brochure as a PDF.

See the [app README](apps/website-brochure/README.md) for complete OpenAI and Ollama setup instructions.

