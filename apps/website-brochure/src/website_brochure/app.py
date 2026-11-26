from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from website_brochure.fetcher import PageContent, PageFetchError, fetch_page
from website_brochure.llm import (
    BrochureGenerator,
    GenerationResult,
    ProviderError,
    create_generator,
    create_generator_for,
)
from website_brochure.models import (
    AvailableModelsResponse,
    CompareRequest,
    CompareResponse,
    ComparisonResult,
    GenerateRequest,
    GenerateResponse,
    ModelOption,
    ModelSelection,
)
from website_brochure.settings import ConfigurationError, ProviderName, Settings


STATIC_DIR = Path(__file__).with_name("static")
PageFetcher = Callable[[str], Awaitable[PageContent]]
GeneratorFactory = Callable[[], BrochureGenerator]
ComparisonGeneratorFactory = Callable[[ProviderName, str], BrochureGenerator]
ModelCatalog = Callable[[], list[ModelOption]]


def _default_generator_factory() -> BrochureGenerator:
    return create_generator(Settings.from_env())


def _default_comparison_generator_factory(
    provider: ProviderName, model: str
) -> BrochureGenerator:
    return create_generator_for(Settings.from_env(), provider, model)


def _default_model_catalog() -> list[ModelOption]:
    return [
        ModelOption(
            provider=provider.value,
            model=model,
            label=f"{provider.value.title()} · {model}",
        )
        for provider, model in Settings.from_env().configured_models()
    ]


def _generation_response(
    page: PageContent, generation: GenerationResult
) -> GenerateResponse:
    return GenerateResponse(
        **generation.content.model_dump(),
        source_url=page.source_url,
        page_title=page.title,
        generation_metrics=generation.metrics,
    )


def create_app(
    *,
    page_fetcher: PageFetcher = fetch_page,
    generator_factory: GeneratorFactory = _default_generator_factory,
    comparison_generator_factory: ComparisonGeneratorFactory = (
        _default_comparison_generator_factory
    ),
    model_catalog: ModelCatalog = _default_model_catalog,
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

    @application.get("/api/models", response_model=AvailableModelsResponse)
    async def available_models() -> AvailableModelsResponse:
        try:
            return AvailableModelsResponse(models=model_catalog())
        except ConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @application.post("/api/generate", response_model=GenerateResponse)
    async def generate(request: GenerateRequest) -> GenerateResponse:
        try:
            generator = generator_factory()
            page = await page_fetcher(str(request.website_url))
            generation = await generator.generate(page, request.category)
        except ConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except PageFetchError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ProviderError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return _generation_response(page, generation)

    @application.post("/api/compare", response_model=CompareResponse)
    async def compare(request: CompareRequest) -> CompareResponse:
        try:
            page = await page_fetcher(str(request.website_url))
        except PageFetchError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        async def generate_one(selection: ModelSelection) -> ComparisonResult:
            try:
                generator = comparison_generator_factory(
                    ProviderName(selection.provider), selection.model
                )
                generation = await generator.generate(page, request.category)
                return ComparisonResult(
                    selection=selection,
                    generation=_generation_response(page, generation),
                )
            except (ConfigurationError, ProviderError) as exc:
                return ComparisonResult(selection=selection, error=str(exc))
            except Exception:
                return ComparisonResult(
                    selection=selection,
                    error="The model could not complete this generation.",
                )

        results = await asyncio.gather(
            *(generate_one(selection) for selection in request.models)
        )
        return CompareResponse(
            source_url=page.source_url,
            page_title=page.title,
            results=list(results),
        )

    return application


app = create_app()

