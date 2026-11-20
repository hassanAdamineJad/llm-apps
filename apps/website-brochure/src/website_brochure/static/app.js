const EXAMPLE = {
  source_url: "https://studio.example/about",
  factual_summary: "A small creative studio helps organizations turn complex ideas into useful, approachable communication.",
  brochure: {
    headline: "Ideas made clear, useful, and ready to share",
    introduction: "A thoughtful creative practice for teams that need their next story, service, or program to feel simple without losing its substance.",
    sections: [
      {
        heading: "Find the signal",
        body: "Start with the essential idea, then shape a clear narrative around what matters to the people you want to reach.",
      },
      {
        heading: "Make it tangible",
        body: "Turn strategy into language and materials that teams can understand, use, and confidently put into the world.",
      },
      {
        heading: "Built to travel",
        body: "Create a flexible foundation that stays coherent across pages, presentations, and conversations.",
      },
    ],
    call_to_action: "Start with a focused conversation.",
  },
};

const state = {
  successfulResult: null,
  isLoading: false,
  theme: "minimal",
  accent: "#c85c3c",
};

const body = document.body;
const composer = document.querySelector("#composer");
const pageTitle = document.querySelector("#page-title");
const form = document.querySelector("#generate-form");
const urlInput = document.querySelector("#website-url");
const categoryInput = document.querySelector("#category");
const generateButton = document.querySelector("#generate-button");
const buttonLabel = generateButton.querySelector(".button-label");
const formError = document.querySelector("#form-error");
const formStatus = document.querySelector("#form-status");
const workspace = document.querySelector("#preview-workspace");
const workspaceBar = document.querySelector("#workspace-bar");
const workspaceProgress = document.querySelector("#workspace-progress");
const appearancePanel = document.querySelector("#appearance-panel");
const exampleLabel = document.querySelector("#example-label");
const summaryText = document.querySelector("#summary-text");
const summaryDisclosure = document.querySelector(".summary-disclosure");
const sourceDomainLink = document.querySelector("#source-domain-link");
const editSourceButton = document.querySelector("#edit-source-button");
const printButton = document.querySelector("#print-button");
const preview = document.querySelector("#brochure-preview");
const headline = document.querySelector("#brochure-headline");
const intro = document.querySelector("#brochure-intro");
const sections = document.querySelector("#brochure-sections");
const cta = document.querySelector("#brochure-cta");
const sourceLink = document.querySelector("#source-link");
const generationMetrics = document.querySelector("#generation-metrics");
const metricProvider = document.querySelector("#metric-provider");
const metricModel = document.querySelector("#metric-model");
const metricInputTokens = document.querySelector("#metric-input-tokens");
const metricOutputTokens = document.querySelector("#metric-output-tokens");
const metricTotalTokens = document.querySelector("#metric-total-tokens");
const metricCachedInputTokens = document.querySelector("#metric-cached-input-tokens");
const metricCacheHitRatio = document.querySelector("#metric-cache-hit-ratio");
const metricEstimatedCost = document.querySelector("#metric-estimated-cost");
const metricLatency = document.querySelector("#metric-latency");
const metricStatus = document.querySelector("#metric-status");
const accentColor = document.querySelector("#accent-color");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

function sourceDomain(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function renderDocument(data, { example = false } = {}) {
  const brochure = data.brochure;
  sections.replaceChildren();
  headline.textContent = brochure.headline;
  intro.textContent = brochure.introduction;

  for (const item of brochure.sections) {
    const section = document.createElement("section");
    const sectionHeading = document.createElement("h3");
    const sectionBody = document.createElement("p");
    sectionHeading.textContent = item.heading;
    sectionBody.textContent = item.body;
    section.append(sectionHeading, sectionBody);
    sections.append(section);
  }

  cta.textContent = brochure.call_to_action || "";
  cta.hidden = !brochure.call_to_action;
  sourceLink.href = data.source_url;
  sourceLink.textContent = data.source_url;
  preview.classList.toggle("is-example", example);
  preview.setAttribute("aria-label", example ? "Example brochure" : "Generated brochure");
}

function metricValue(value) {
  return value === null || value === undefined || value === "" ? "N/A" : String(value);
}

function renderGenerationMetrics(metrics) {
  if (!metrics) {
    generationMetrics.hidden = true;
    return;
  }

  metricProvider.textContent = metricValue(metrics.provider);
  metricModel.textContent = metricValue(metrics.model);
  metricInputTokens.textContent = metricValue(metrics.input_tokens);
  metricOutputTokens.textContent = metricValue(metrics.output_tokens);
  metricTotalTokens.textContent = metricValue(metrics.total_tokens);
  metricCachedInputTokens.textContent = metricValue(metrics.cached_input_tokens);
  metricCacheHitRatio.textContent =
    typeof metrics.cache_hit_ratio === "number"
      ? `${(metrics.cache_hit_ratio * 100).toFixed(1)}%`
      : "N/A";
  metricEstimatedCost.textContent =
    typeof metrics.estimated_cost_usd === "number"
      ? `$${metrics.estimated_cost_usd.toFixed(6)}`
      : "N/A";
  metricLatency.textContent =
    typeof metrics.latency_ms === "number" ? `${(metrics.latency_ms / 1000).toFixed(2)} s` : "N/A";
  metricStatus.textContent =
    metrics.success === true ? "Succeeded" : metrics.success === false ? "Failed" : "N/A";
  metricStatus.classList.toggle("status-success", metrics.success === true);
  metricStatus.classList.toggle("status-failed", metrics.success === false);
  generationMetrics.open = false;
  generationMetrics.hidden = false;
}

function contrastText(hex) {
  const value = hex.replace("#", "");
  const channels = [0, 2, 4].map((index) => Number.parseInt(value.slice(index, index + 2), 16) / 255);
  const linear = channels.map((channel) =>
    channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4,
  );
  const luminance = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
  return luminance > 0.48 ? "#17201b" : "#ffffff";
}

function applyAccent(color, selectedSwatch = null) {
  state.accent = color;
  preview.style.setProperty("--accent", color);
  preview.style.setProperty("--accent-ink", contrastText(color));
  accentColor.value = color;

  document.querySelectorAll(".color-swatch").forEach((swatch) => {
    const selected = swatch === selectedSwatch;
    swatch.classList.toggle("selected", selected);
    swatch.setAttribute("aria-pressed", String(selected));
  });
  document.querySelector(".custom-color").classList.toggle("selected", selectedSwatch === null);
}

function applyTheme(theme) {
  state.theme = theme;
  preview.classList.remove("theme-minimal", "theme-corporate", "theme-bold");
  preview.classList.add(`theme-${theme}`);
  document.querySelectorAll(".theme-card").forEach((button) => {
    const selected = button.dataset.theme === theme;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
}

function setLoading(isLoading, replacing) {
  state.isLoading = isLoading;
  generateButton.disabled = isLoading;
  urlInput.disabled = isLoading;
  categoryInput.disabled = isLoading;
  form.setAttribute("aria-busy", String(isLoading));
  generateButton.classList.toggle("loading", isLoading);
  workspaceProgress.hidden = !(isLoading && replacing);
  formStatus.textContent = isLoading && !replacing ? "Reading the page and drafting from its content…" : "";
}

function clearError() {
  formError.textContent = "";
  formError.hidden = true;
  urlInput.removeAttribute("aria-invalid");
}

function showError(message, { focus = true } = {}) {
  formError.textContent = message;
  formError.hidden = false;
  urlInput.setAttribute("aria-invalid", "true");
  if (focus) formError.focus({ preventScroll: true });
}

function validSourceUrl() {
  try {
    const parsed = new URL(urlInput.value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function showComposer({ replacement = false } = {}) {
  composer.hidden = false;
  body.classList.toggle("mode-editing", replacement);
  pageTitle.textContent = replacement ? "Edit source" : "Create a brochure";
  buttonLabel.textContent = replacement ? "Generate replacement" : "Generate brochure";
}

function hideComposer() {
  composer.hidden = true;
  body.classList.remove("mode-editing");
}

function showGeneratedResult(data) {
  state.successfulResult = data;
  renderDocument(data);
  renderGenerationMetrics(data.generation_metrics);
  summaryText.textContent = data.factual_summary;
  summaryDisclosure.open = false;
  sourceDomainLink.href = data.source_url;
  sourceDomainLink.textContent = sourceDomain(data.source_url);
  workspaceBar.hidden = false;
  appearancePanel.hidden = false;
  exampleLabel.hidden = true;
  body.classList.remove("mode-initial", "mode-editing");
  body.classList.add("mode-generated");
  hideComposer();

  requestAnimationFrame(() => {
    workspace.scrollIntoView({
      behavior: reducedMotion.matches ? "auto" : "smooth",
      block: "start",
    });
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.isLoading) return;
  clearError();

  if (!validSourceUrl()) {
    showError("Enter a public website URL beginning with http:// or https://.");
    urlInput.focus();
    return;
  }

  const replacing = state.successfulResult !== null;
  if (replacing) hideComposer();
  setLoading(true, replacing);

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
    if (data.status === "insufficient") {
      throw new Error(data.feedback || "This page does not contain enough relevant detail for that brochure type.");
    }
    showGeneratedResult(data);
  } catch (error) {
    showComposer({ replacement: replacing });
    showError(error instanceof Error ? error.message : "The request could not be completed.");
    if (replacing) {
      composer.scrollIntoView({ behavior: reducedMotion.matches ? "auto" : "smooth", block: "start" });
    }
  } finally {
    setLoading(false, replacing);
  }
});

editSourceButton.addEventListener("click", () => {
  clearError();
  showComposer({ replacement: true });
  composer.scrollIntoView({ behavior: reducedMotion.matches ? "auto" : "smooth", block: "start" });
  urlInput.focus({ preventScroll: true });
});

document.querySelectorAll(".theme-card").forEach((button) => {
  button.addEventListener("click", () => applyTheme(button.dataset.theme));
});

document.querySelectorAll(".color-swatch").forEach((swatch) => {
  swatch.addEventListener("click", () => applyAccent(swatch.dataset.color, swatch));
});

accentColor.addEventListener("input", () => applyAccent(accentColor.value));
printButton.addEventListener("click", () => window.print());

renderDocument(EXAMPLE, { example: true });
applyTheme(state.theme);
applyAccent(state.accent, document.querySelector('.color-swatch[data-color="#c85c3c"]'));
