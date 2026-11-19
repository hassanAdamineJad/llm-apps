"""Deterministic local server for manual responsive and print QA.

Run from the repository root with:
python -m uvicorn visual_app:app --app-dir apps/website-brochure/tests --port 8001
"""

from pathlib import Path

from website_brochure.app import create_app
from website_brochure.fetcher import PageContent, extract_readable_text
from website_brochure.models import BrochureCategory, GeneratedContent


FIXTURE = Path(__file__).parent / "fixtures" / "example_page.html"
LONG_SOURCE = (
    "https://northstar.example/programs/product-leadership/"
    "workshops/2026/cross-functional-decision-making?ref=brochure-preview"
)


async def fixture_fetcher(url: str) -> PageContent:
    extracted = extract_readable_text(FIXTURE.read_bytes(), LONG_SOURCE)
    return PageContent(
        source_url=LONG_SOURCE,
        title="short" if url.endswith("/short") else "long",
        text=extracted.text,
    )


class VisualGenerator:
    async def generate(
        self, page: PageContent, category: BrochureCategory
    ) -> GeneratedContent:
        if page.title == "short":
            sections = [
                {
                    "heading": "Focused practice",
                    "body": "A practical workshop helps product teams make clearer decisions together.",
                },
                {
                    "heading": "For working teams",
                    "body": "The program serves product managers, designers, and engineers.",
                },
            ]
            headline = "Practical learning for product teams"
        else:
            sections = [
                {
                    "heading": "Discovery",
                    "body": "Participants use realistic exercises to build a shared approach to product discovery and turn ambiguous questions into useful evidence.",
                },
                {
                    "heading": "Prioritization",
                    "body": "Facilitated practice helps cross-functional teams compare options, document trade-offs, and make decisions that colleagues can understand.",
                },
                {
                    "heading": "Repeatable habits",
                    "body": "Guided reflection turns the session into methods participants can carry into planning, reviews, and weekly product work.",
                },
            ]
            headline = (
                "A practical program for cross-functional product teams "
                "learning to make clearer decisions together"
            )

        return GeneratedContent.model_validate(
            {
                "status": "ready",
                "factual_summary": (
                    "Northstar runs facilitated workshops for product managers, designers, "
                    "and engineers focused on discovery, prioritization, and written decisions."
                ),
                "brochure": {
                    "headline": headline,
                    "introduction": (
                        "Facilitated workshops combine concise lessons, realistic planning "
                        "exercises, and guided reflection for established product teams."
                    ),
                    "sections": sections,
                    "call_to_action": None,
                },
                "feedback": None,
            }
        )


app = create_app(
    page_fetcher=fixture_fetcher,
    generator_factory=VisualGenerator,
)
