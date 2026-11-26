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
  comparisonResult: null,
  availableModels: [],
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
const compareToggle = document.querySelector("#compare-models");
const comparisonAvailability = document.querySelector("#comparison-availability");
const comparisonOptions = document.querySelector("#comparison-options");
const comparisonModelA = document.querySelector("#comparison-model-a");
const comparisonModelB = document.querySelector("#comparison-model-b");
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
const comparisonWorkspace = document.querySelector("#comparison-workspace");
const comparisonSourceLink = document.querySelector("#comparison-source-link");
const comparisonEditButton = document.querySelector("#comparison-edit-button");
const comparisonResults = document.querySelector("#comparison-results");
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

function comparisonMetric(label, value) {
  const wrapper = document.createElement("div");
  const term = document.createElement("dt");
  const detail = document.createElement("dd");
  term.textContent = label;
  detail.textContent = value;
  wrapper.append(term, detail);
  return wrapper;
}

function renderComparisonMetrics(metrics) {
  const list = document.createElement("dl");
  list.className = "comparison-metrics";
  list.append(
    comparisonMetric(
      "Latency",
      typeof metrics?.latency_ms === "number" ? `${(metrics.latency_ms / 1000).toFixed(2)} s` : "N/A",
    ),
    comparisonMetric("Input", metricValue(metrics?.input_tokens)),
    comparisonMetric("Output", metricValue(metrics?.output_tokens)),
    comparisonMetric("Total", metricValue(metrics?.total_tokens)),
    comparisonMetric("Cached", metricValue(metrics?.cached_input_tokens)),
    comparisonMetric(
      "Est. cost",
      typeof metrics?.estimated_cost_usd === "number" ? `$${metrics.estimated_cost_usd.toFixed(6)}` : "N/A",
    ),
  );
  return list;
}

function renderComparisonBrochure(generation) {
  const brochure = generation.brochure;
  const article = document.createElement("article");
  article.className = "brochure theme-minimal comparison-brochure";
  article.setAttribute("aria-label", `Brochure generated by ${generation.generation_metrics.model}`);

  const masthead = document.createElement("header");
  masthead.className = "brochure-masthead";
  const kicker = document.createElement("p");
  kicker.className = "brochure-kicker";
  kicker.textContent = "Overview";
  const title = document.createElement("h3");
  title.textContent = brochure.headline;
  masthead.append(kicker, title);

  const introduction = document.createElement("p");
  introduction.className = "brochure-intro";
  introduction.textContent = brochure.introduction;
  const brochureSections = document.createElement("div");
  brochureSections.className = "brochure-sections";
  for (const item of brochure.sections) {
    const section = document.createElement("section");
    const sectionHeading = document.createElement("h4");
    const sectionBody = document.createElement("p");
    sectionHeading.textContent = item.heading;
    sectionBody.textContent = item.body;
    section.append(sectionHeading, sectionBody);
    brochureSections.append(section);
  }
  article.append(masthead, introduction, brochureSections);
  if (brochure.call_to_action) {
    const callToAction = document.createElement("p");
    callToAction.className = "brochure-cta";
    callToAction.textContent = brochure.call_to_action;
    article.append(callToAction);
  }
  return article;
}

function renderQualityRating(index, disabled = false) {
  const label = document.createElement("label");
  label.className = "quality-rating";
  label.htmlFor = `quality-rating-${index}`;
  label.append("Your quality rating");
  const select = document.createElement("select");
  select.id = `quality-rating-${index}`;
  select.disabled = disabled;
  for (const [value, text] of [
    ["", "Not rated"],
    ["1", "1 — Poor"],
    ["2", "2 — Fair"],
    ["3", "3 — Good"],
    ["4", "4 — Very good"],
    ["5", "5 — Excellent"],
  ]) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    select.append(option);
  }
  label.append(select);
  return label;
}

function renderComparisonResult(result, index) {
  const card = document.createElement("article");
  card.className = "comparison-card";
  const header = document.createElement("header");
  const provider = document.createElement("span");
  provider.className = "comparison-provider";
  provider.textContent = result.selection.provider;
  const model = document.createElement("h3");
  model.textContent = result.selection.model;
  header.append(provider, model);
  card.append(header);

  if (result.error) {
    const error = document.createElement("p");
    error.className = "comparison-error";
    error.setAttribute("role", "alert");
    error.textContent = result.error;
    card.append(error, renderComparisonMetrics(null), renderQualityRating(index, true));
    return card;
  }

  const generation = result.generation;
  if (generation.status === "ready") {
    card.append(renderComparisonBrochure(generation));
  } else {
    const feedback = document.createElement("p");
    feedback.className = "comparison-feedback";
    feedback.textContent = generation.feedback || "The source did not contain enough detail.";
    card.append(feedback);
  }
  card.append(renderComparisonMetrics(generation.generation_metrics), renderQualityRating(index));
  return card;
}

function showComparisonResult(data) {
  state.successfulResult = null;
  state.comparisonResult = data;
  comparisonResults.replaceChildren();
  data.results.forEach((result, index) => comparisonResults.append(renderComparisonResult(result, index)));
  comparisonSourceLink.href = data.source_url;
  comparisonSourceLink.textContent = sourceDomain(data.source_url);
  workspace.hidden = true;
  comparisonWorkspace.hidden = false;
  body.classList.remove("mode-initial", "mode-editing");
  body.classList.add("mode-generated", "mode-comparison");
  hideComposer();
  requestAnimationFrame(() => {
    comparisonWorkspace.scrollIntoView({
      behavior: reducedMotion.matches ? "auto" : "smooth",
      block: "start",
    });
  });
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
  compareToggle.disabled = isLoading || state.availableModels.length < 2;
  comparisonModelA.disabled = isLoading;
  comparisonModelB.disabled = isLoading;
  form.setAttribute("aria-busy", String(isLoading));
  generateButton.classList.toggle("loading", isLoading);
  workspaceProgress.hidden = !(isLoading && replacing && !compareToggle.checked);
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
  if (compareToggle.checked) {
    buttonLabel.textContent = replacement ? "Run new comparison" : "Compare models";
  } else {
    buttonLabel.textContent = replacement ? "Generate replacement" : "Generate brochure";
  }
}

function hideComposer() {
  composer.hidden = true;
  body.classList.remove("mode-editing");
}

function showGeneratedResult(data) {
  state.successfulResult = data;
  state.comparisonResult = null;
  renderDocument(data);
  renderGenerationMetrics(data.generation_metrics);
  summaryText.textContent = data.factual_summary;
  summaryDisclosure.open = false;
  sourceDomainLink.href = data.source_url;
  sourceDomainLink.textContent = sourceDomain(data.source_url);
  workspaceBar.hidden = false;
  appearancePanel.hidden = false;
  workspace.hidden = false;
  comparisonWorkspace.hidden = true;
  exampleLabel.hidden = true;
  body.classList.remove("mode-initial", "mode-editing", "mode-comparison");
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

  const comparing = compareToggle.checked;
  const selectedModels = comparing
    ? [state.availableModels[Number(comparisonModelA.value)], state.availableModels[Number(comparisonModelB.value)]]
    : [];
  if (comparing && (selectedModels.some((model) => !model) || comparisonModelA.value === comparisonModelB.value)) {
    showError("Choose two different configured models to compare.");
    return;
  }

  const replacing = state.successfulResult !== null || state.comparisonResult !== null;
  if (replacing) hideComposer();
  setLoading(true, replacing);

  try {
    const response = await fetch(comparing ? "/api/compare" : "/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        website_url: urlInput.value,
        category: categoryInput.value,
        ...(comparing
          ? {
              models: selectedModels.map(({ provider, model }) => ({ provider, model })),
            }
          : {}),
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : "The request could not be completed.";
      throw new Error(detail);
    }
    if (!comparing && data.status === "insufficient") {
      throw new Error(data.feedback || "This page does not contain enough relevant detail for that brochure type.");
    }
    if (comparing) {
      showComparisonResult(data);
    } else {
      showGeneratedResult(data);
    }
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

comparisonEditButton.addEventListener("click", () => {
  clearError();
  showComposer({ replacement: true });
  composer.scrollIntoView({ behavior: reducedMotion.matches ? "auto" : "smooth", block: "start" });
  urlInput.focus({ preventScroll: true });
});

compareToggle.addEventListener("change", () => {
  comparisonOptions.hidden = !compareToggle.checked;
  showComposer({ replacement: state.successfulResult !== null || state.comparisonResult !== null });
});

async function loadAvailableModels() {
  try {
    const response = await fetch("/api/models");
    const data = await response.json();
    if (!response.ok) throw new Error("Configured models could not be loaded.");
    state.availableModels = Array.isArray(data.models) ? data.models : [];
    comparisonModelA.replaceChildren();
    comparisonModelB.replaceChildren();
    state.availableModels.forEach((item, index) => {
      for (const select of [comparisonModelA, comparisonModelB]) {
        const option = document.createElement("option");
        option.value = String(index);
        option.textContent = item.label;
        select.append(option);
      }
    });
    const comparisonReady = state.availableModels.length >= 2;
    compareToggle.disabled = !comparisonReady;
    comparisonAvailability.textContent = comparisonReady
      ? "Uses the same extracted page content for both generations."
      : "Configure two providers/models to enable comparison.";
    if (comparisonReady) comparisonModelB.value = "1";
  } catch {
    compareToggle.disabled = true;
    comparisonAvailability.textContent = "Model comparison is currently unavailable.";
  }
}

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
loadAvailableModels();
