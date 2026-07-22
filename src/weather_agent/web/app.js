const form = document.querySelector("#question-form");
const questionInput = document.querySelector("#question");
const submitButton = document.querySelector("#submit-button");
const runPanel = document.querySelector("#run-panel");
const runStatus = document.querySelector("#run-status");
const answer = document.querySelector("#answer");
const metrics = document.querySelector("#metrics");
const temperatureSection = document.querySelector("#temperature-section");
const temperatures = document.querySelector("#temperatures");
const timeline = document.querySelector("#timeline");
const runId = document.querySelector("#run-id");
const traceDownload = document.querySelector("#trace-download");

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function metric(value, label) {
  const card = element("div", "metric");
  card.append(element("strong", "", String(value)), element("span", "", label));
  return card;
}

function renderTemperatures(items) {
  temperatures.replaceChildren();
  temperatureSection.hidden = !items.length;
  for (const item of items) {
    const card = element("article", "temperature-card");
    const city = item.resolved_city || item.requested_city || "Requested city";
    card.append(
      element("div", "city", city),
      element("div", "value", `${item.temperature} ${item.unit || ""}`.trim()),
      element("time", "", item.observed_at ? `Observed ${item.observed_at}` : "Current reading"),
    );
    temperatures.append(card);
  }
}

function renderTimeline(events) {
  timeline.replaceChildren();
  for (const event of events) {
    const item = element("article", `event ${event.event}`);
    const marker = element("div", "event-marker", String(event.sequence).padStart(2, "0"));
    const body = element("div", "event-body");
    const heading = element("div", "event-heading");
    heading.append(
      element("span", "event-name", event.event.replaceAll("_", " ")),
      element("span", "event-time", `+${Number(event.elapsed_ms).toFixed(1)} ms`),
    );
    body.append(heading, element("p", "event-summary", event.summary || ""));
    if (event.details && Object.keys(event.details).length) {
      const details = document.createElement("details");
      details.append(
        element("summary", "", "Structured details"),
        element("pre", "", JSON.stringify(event.details, null, 2)),
      );
      body.append(details);
    }
    item.append(marker, body);
    timeline.append(item);
  }
}

function renderResult(payload, ok) {
  runPanel.hidden = false;
  runPanel.classList.toggle("error-state", !ok);
  runStatus.textContent = ok
    ? payload.status === "refused" ? "Request safely refused" : "Run completed"
    : "Run failed";
  answer.textContent = payload.answer || payload.error || "No answer was returned.";
  runId.textContent = payload.run_id ? `Run ${payload.run_id}` : "";

  const events = Array.isArray(payload.events) ? payload.events : [];
  const total = events.length ? Number(events.at(-1).elapsed_ms).toFixed(1) : "0.0";
  const modelRounds = events.filter((event) => event.event === "model_request").length;
  const toolCalls = events.filter((event) => event.event === "tool_call_requested").length;
  metrics.replaceChildren(
    metric(payload.status || (ok ? "completed" : "error"), "Status"),
    metric(`${total} ms`, "Total elapsed"),
    metric(modelRounds, "Model rounds"),
    metric(toolCalls, "Tool calls"),
  );

  renderTemperatures(Array.isArray(payload.temperatures) ? payload.temperatures : []);
  renderTimeline(events);

  if (payload.run_id) {
    traceDownload.href = `/api/traces/${payload.run_id}`;
    traceDownload.hidden = false;
  } else {
    traceDownload.hidden = true;
  }
  runPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;

  submitButton.disabled = true;
  submitButton.querySelector("span").textContent = "Running…";
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const payload = await response.json();
    renderResult(payload, response.ok);
  } catch (_error) {
    renderResult({ error: "Could not reach the local Python service.", events: [] }, false);
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector("span").textContent = "Run agent";
  }
});

for (const button of document.querySelectorAll("[data-question]")) {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.question;
    questionInput.focus();
  });
}
