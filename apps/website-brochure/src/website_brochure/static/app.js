const form = document.querySelector("#generate-form");
const urlInput = document.querySelector("#website-url");
const categoryInput = document.querySelector("#category");
const generateButton = document.querySelector("#generate-button");
const status = document.querySelector("#status");
const emptyState = document.querySelector("#empty-state");
const results = document.querySelector("#results");
const summaryText = document.querySelector("#summary-text");
const insufficientCard = document.querySelector("#insufficient-card");
const feedbackText = document.querySelector("#feedback-text");
const brochureArea = document.querySelector("#brochure-area");
const preview = document.querySelector("#brochure-preview");
const headline = document.querySelector("#brochure-headline");
const intro = document.querySelector("#brochure-intro");
const sections = document.querySelector("#brochure-sections");
const cta = document.querySelector("#brochure-cta");
const sourceLink = document.querySelector("#source-link");
const accentColor = document.querySelector("#accent-color");
const printButton = document.querySelector("#print-button");

function setLoading(isLoading) {
  generateButton.disabled = isLoading;
  form.setAttribute("aria-busy", String(isLoading));
  generateButton.classList.toggle("loading", isLoading);
}

function setStatus(message, kind = "") {
  status.textContent = message;
  status.className = `status ${kind}`.trim();
}

function clearRenderedBrochure() {
  sections.replaceChildren();
  cta.textContent = "";
  cta.hidden = true;
}

function renderBrochure(data) {
  clearRenderedBrochure();
  headline.textContent = data.brochure.headline;
  intro.textContent = data.brochure.introduction;

  for (const item of data.brochure.sections) {
    const section = document.createElement("section");
    const headingElement = document.createElement("h3");
    const body = document.createElement("p");
    headingElement.textContent = item.heading;
    body.textContent = item.body;
    section.append(headingElement, body);
    sections.append(section);
  }

  if (data.brochure.call_to_action) {
    cta.textContent = data.brochure.call_to_action;
    cta.hidden = false;
  }

  sourceLink.href = data.source_url;
  sourceLink.textContent = data.source_url;
}

function renderResult(data) {
  emptyState.hidden = true;
  results.hidden = false;
  summaryText.textContent = data.factual_summary;

  if (data.status === "insufficient") {
    feedbackText.textContent = data.feedback;
    insufficientCard.hidden = false;
    brochureArea.hidden = true;
    setStatus("The page was read, but it needs more relevant detail.", "warning");
    return;
  }

  insufficientCard.hidden = true;
  brochureArea.hidden = false;
  renderBrochure(data);
  setStatus("Brochure generated successfully.", "success");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(true);
  setStatus("Reading the page and drafting from its content…", "working");

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        website_url: urlInput.value,
        category: categoryInput.value,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : "The request could not be completed.";
      throw new Error(detail);
    }
    renderResult(data);
  } catch (error) {
    setStatus(error.message || "The request could not be completed.", "error");
  } finally {
    setLoading(false);
  }
});

document.querySelectorAll(".theme-button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".theme-button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    preview.className = `brochure theme-${button.dataset.theme}`;
  });
});

accentColor.addEventListener("input", () => {
  preview.style.setProperty("--accent", accentColor.value);
});

printButton.addEventListener("click", () => window.print());

