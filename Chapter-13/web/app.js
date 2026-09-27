/*
 * The chat window.
 *
 * It does three jobs beyond showing text. It labels every reply with the part
 * of the system that produced it, so the router in section 3.3 is visible
 * instead of theoretical. It shows the sources under a knowledge answer, which
 * is what section 4.4 means by a grounded, cited reply. And it is the place the
 * customer's consent is collected: when the assistant answers that it needs
 * confirmation, this page asks, and only a real click sends the request back
 * with confirmed set. The server never takes the click's word for it, because
 * section 6.6 keeps its own guard.
 */

const transcript = document.getElementById("transcript");
const form = document.getElementById("composer");
const input = document.getElementById("message");
const sendButton = document.getElementById("send");
const customerField = document.getElementById("customer");

// Plain strings, the shape src/tools/selector.py joins with newlines when it
// rewrites a follow-up like "block the second one" into a standalone request.
const history = [];

const AGENTS = {
  question: { label: "Knowledge agent", hint: "answered from the knowledge base" },
  advice: { label: "Product advisor", hint: "matched a product to this customer" },
  action: { label: "Action agent", hint: "used a banking tool" },
};

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function addTurn(node) {
  const welcome = transcript.querySelector(".welcome");
  if (welcome) welcome.remove();
  transcript.append(node);
  transcript.scrollTop = transcript.scrollHeight;
}

function showCustomer(text) {
  const row = el("div", "turn customer");
  row.append(el("div", "bubble", text));
  addTurn(row);
}

function showThinking() {
  const row = el("div", "turn assistant thinking");
  const bubble = el("div", "bubble");
  bubble.append(el("span", "dots", "..."));
  bubble.append(el("span", undefined, "working on it"));
  row.append(bubble);
  addTurn(row);
  return row;
}

function showReply(reply, originalMessage) {
  const agent = AGENTS[reply.kind] || { label: reply.kind, hint: "" };
  const row = el("div", "turn assistant");

  const meta = el("div", "meta");
  meta.append(el("span", `badge badge-${reply.kind}`, agent.label));
  if (agent.hint) meta.append(el("span", "hint", agent.hint));
  if (reply.from_cache) meta.append(el("span", "chip-flag", "served from cache"));
  row.append(meta);

  row.append(el("div", "bubble", reply.text));

  if (reply.sources && reply.sources.length) {
    const sources = el("div", "sources");
    sources.append(el("span", "sources-label", "Sources"));
    reply.sources.forEach((source) => {
      sources.append(el("span", "source", typeof source === "string"
        ? source
        : source.title || source.doc_id || JSON.stringify(source)));
    });
    row.append(sources);
  }

  if (reply.reference && !reply.needs_confirmation) {
    row.append(el("div", "reference", `Reference: ${reply.reference}`));
  }

  if (reply.needs_confirmation) {
    row.append(confirmationBar(originalMessage));
  }

  addTurn(row);
}

function confirmationBar(originalMessage) {
  const bar = el("div", "confirm");
  bar.append(el("span", "confirm-text", "This one changes something. Go ahead?"));

  const yes = el("button", "confirm-yes", "Yes, do it");
  yes.addEventListener("click", () => {
    bar.remove();
    showCustomer("yes, go ahead");
    history.push("Customer: yes, go ahead");
    send(originalMessage, true);
  });

  const no = el("button", "confirm-no", "No, cancel");
  no.addEventListener("click", () => {
    bar.replaceWith(el("div", "cancelled", "Cancelled. Nothing was changed."));
  });

  bar.append(yes, no);
  return bar;
}

function showError(message) {
  const row = el("div", "turn assistant");
  row.append(el("div", "bubble error", message));
  addTurn(row);
}

function setBusy(busy) {
  sendButton.disabled = busy;
  input.disabled = busy;
  if (!busy) input.focus();
}

async function send(message, confirmed) {
  setBusy(true);
  const waiting = showThinking();
  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_id: customerField.value.trim() || "demo",
        message,
        history,
        confirmed: Boolean(confirmed),
      }),
    });
    waiting.remove();
    if (!response.ok) {
      showError(`The assistant answered with ${response.status}. Check the API logs.`);
      return;
    }
    const reply = await response.json();
    history.push(`Assistant: ${reply.text}`);
    showReply(reply, message);
  } catch (error) {
    waiting.remove();
    showError("Could not reach the assistant. Is the API still running?");
  } finally {
    setBusy(false);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  showCustomer(message);
  history.push(`Customer: ${message}`);
  send(message, false);
});

transcript.addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  input.value = chip.dataset.say;
  form.requestSubmit();
});

// The same health check the operators read, in the corner of the page.
async function pollHealth() {
  const dot = document.getElementById("health-dot");
  const text = document.getElementById("health-text");
  try {
    const response = await fetch("/health");
    const body = await response.json();
    const down = Object.entries(body.components || {})
      .filter(([, ok]) => !ok)
      .map(([name]) => name);
    dot.className = `dot ${body.status}`;
    text.textContent = down.length ? `degraded: ${down.join(", ")}` : body.status;
  } catch (error) {
    dot.className = "dot degraded";
    text.textContent = "api unreachable";
  }
}

pollHealth();
setInterval(pollHealth, 15000);
input.focus();
