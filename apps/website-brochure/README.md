# Website Brochure

Website Brochure reads one public HTML page and asks either OpenAI or a local Ollama model to produce two separate results:

1. a short factual summary of the submitted page; and
2. structured brochure copy with a headline, introduction, and relevant sections.

The browser renders that structured copy with app-owned HTML and CSS. You can switch the Minimal, Corporate, and Bold themes or change the accent color without fetching the page or calling the model again. Printing uses the browser dialog and includes only the brochure and source link.

Version 1 reads only the submitted page. It does not crawl linked pages or execute page JavaScript. Sparse and JavaScript-only sites can therefore be rejected with guidance rather than supplemented with invented details.

## Prerequisites

- Python 3.11 or newer
- A public HTTP(S) page to use as source material
- Either an OpenAI API key, or [Ollama](https://ollama.com/) running locally

All commands below start in the repository root. The virtual environment and dependencies stay inside this app.

## Install

```bash
python3 -m venv apps/website-brochure/.venv
source apps/website-brochure/.venv/bin/activate
python -m pip install -e "apps/website-brochure[dev]"
cp apps/website-brochure/.env.example apps/website-brochure/.env
```

On Windows PowerShell, activate with:

```powershell
apps\website-brochure\.venv\Scripts\Activate.ps1
```

The app loads `apps/website-brochure/.env`. A real `.env` is ignored by Git; `.env.example` documents every setting.

## Option A: OpenAI

Edit `apps/website-brochure/.env`:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4.1-mini

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=
```

`OPENAI_API_KEY` and `OPENAI_MODEL` are validated only when OpenAI is selected. The key is sent from the server directly to OpenAI and never exposed to browser JavaScript.

## Option B: Ollama

Install Ollama for your platform, start its local service, and pull the example model:

```bash
ollama serve
```

In a second terminal:

```bash
ollama pull llama3.2:3b
```

Then edit `apps/website-brochure/.env` and use the exact same model name:

```dotenv
LLM_PROVIDER=ollama
OPENAI_API_KEY=
OPENAI_MODEL=

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

Ollama works without an OpenAI key. `OLLAMA_BASE_URL` is operator-controlled and may point at localhost; unlike the user-submitted website URL, it is intentionally not subject to public-internet SSRF restrictions.

## Environment variables

| Variable | Required when | Meaning |
| --- | --- | --- |
| `LLM_PROVIDER` | Always | Active server-side provider: `openai` or `ollama`. |
| `OPENAI_API_KEY` | OpenAI | Secret API key used only by the server. |
| `OPENAI_MODEL` | OpenAI | OpenAI model passed to the Responses API. |
| `OLLAMA_BASE_URL` | Ollama | Ollama HTTP endpoint; defaults to `http://localhost:11434`. |
| `OLLAMA_MODEL` | Ollama | An already-pulled Ollama model name, including its tag. |

Restart the Python app after changing `.env`; configuration is read by the server for generation requests, and restarting makes the active settings unambiguous. If you change or pull an Ollama model, make sure `OLLAMA_MODEL` still exactly matches `ollama list`.

## Run

With the virtual environment active:

```bash
python -m website_brochure
```

Open <http://127.0.0.1:8000>. This single command serves both the FastAPI endpoint and the HTML/CSS/JavaScript UI.

## Example flow

1. Enter `https://www.python.org/about/` as the source URL.
2. Choose **Business Overview**.
3. Select **Generate brochure**.
4. Compare the factual page summary with the brochure preview.
5. Switch to **Corporate** or **Bold**, choose another accent color, then select **Print / Save PDF**.

The precise copy depends on the chosen model. The app instructs the model to omit unsupported calls to action and never fill gaps with prices, testimonials, dates, contact details, or product claims. Review generated copy before publishing it.

## Tests

```bash
python -m pytest apps/website-brochure/tests
```

Tests use fixture HTML and fake generators, so they do not require a provider, API key, or network access.

## Code map

- `src/website_brochure/app.py` — FastAPI routes and dependency wiring
- `src/website_brochure/fetcher.py` — public-URL checks, pinned connections, bounded fetching, and readable-text extraction
- `src/website_brochure/llm.py` — shared provider contract, prompt, OpenAI, and Ollama integrations
- `src/website_brochure/models.py` — request, response, and provider output schemas
- `src/website_brochure/settings.py` — selected-provider environment validation
- `src/website_brochure/static/` — browser-owned rendering and themes

