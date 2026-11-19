from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from website_brochure.fetcher import PageContent, PageFetchError, fetch_page
from website_brochure.llm import BrochureGenerator, ProviderError, create_generator
from website_brochure.models import GenerateRequest, GenerateResponse
from website_brochure.settings import ConfigurationError, Settings


STATIC_DIR = Path(__file__).with_name("static")
PageFetcher = Callable[[str], Awaitable[PageContent]]
GeneratorFactory = Callable[[], BrochureGenerator]


def _default_generator_factory() -> BrochureGenerator:
    return create_generator(Settings.from_env())


def create_app(
    *,
    page_fetcher: PageFetcher = fetch_page,
    generator_factory: GeneratorFactory = _default_generator_factory,
) -> FastAPI:
    application = FastAPI(title="Website Brochure", version="0.1.0")
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @application.exception_handler(RequestValidationError)
    async def readable_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        invalid_fields = {str(part) for error in exc.errors() for part in error["loc"]}
        if "website_url" in invalid_fields:
            detail = "Enter a valid public website URL beginning with http:// or https://."
        elif "category" in invalid_fields:
            detail = "Choose one of the available brochure categories."
        else:
            detail = "Check the submitted values and try again."
        return JSONResponse(status_code=422, content={"detail": detail})

    @application.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @application.post("/api/generate", response_model=GenerateResponse)
    async def generate(request: GenerateRequest) -> GenerateResponse:
        try:
            generator = generator_factory()
            page = await page_fetcher(str(request.website_url))
            generated = await generator.generate(page, request.category)
        except ConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except PageFetchError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ProviderError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return GenerateResponse(
            **generated.model_dump(),
            source_url=page.source_url,
            page_title=page.title,
        )

    return application


app = create_app()

