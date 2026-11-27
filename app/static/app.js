"use strict";

const COLORS = [
  "#7259e6",
  "#46b493",
  "#f0b657",
  "#e8818d",
  "#5d9ddb",
  "#a78bdb",
];

const elements = {};
let searchTimer;

function cacheElements() {
  document.querySelectorAll("[id]").forEach((element) => {
    elements[element.id] = element;
  });
}

function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (character) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[character],
  );
}

function slug(value) {
  return String(value)
    .toLowerCase()
    .replace(/[^a-z]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("show");
  window.setTimeout(() => elements.toast.classList.remove("show"), 2600);
}

function setCurrentDate() {
  const date = new Intl.DateTimeFormat("en", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(new Date());

  elements.today.textContent = date.toUpperCase();
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    const message = Array.isArray(detail)
      ? detail[0]?.msg
      : detail || "The request could not be completed";
    throw new Error(message);
  }

  return response.status === 204 ? null : response.json();
}

function renderTrend(trend) {
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = new Date();
    date.setDate(date.getDate() - (6 - index));
    return date.toISOString().slice(0, 10);
  });

  const counts = Object.fromEntries(
    trend.map((item) => [item.date, item.count]),
  );
  const maximum = Math.max(1, ...days.map((date) => counts[date] || 0));

  elements["trend-chart"].innerHTML = days
    .map((date, index) => {
      const count = counts[date] || 0;
      const height = count ? Math.max(7, (count / maximum) * 100) : 3;
      const label = new Date(`${date}T00:00:00`).toLocaleDateString("en", {
        weekday: "short",
      });

      return `
        <div class="trend-day">
          <div class="bar-track">
            <div class="bar ${index === 6 ? "today" : ""}" style="height:${height}%">
              ${count ? `<span class="bar-value">${count}</span>` : ""}
            </div>
          </div>
          <span class="day-label">${label}</span>
        </div>`;
    })
    .join("");
}

function renderCategoryChart(categories) {
  const total = categories.reduce((sum, category) => sum + category.count, 0);
  let position = 0;

  const stops = categories.map((category, index) => {
    const start = position;
    position += total ? (category.count / total) * 360 : 0;
    return `${COLORS[index % COLORS.length]} ${start}deg ${position}deg`;
  });

  elements["category-donut"].style.background = total
    ? `conic-gradient(${stops.join(",")})`
    : "conic-gradient(#f1effb 0deg 360deg)";

  elements["category-legend"].innerHTML = categories.length
    ? categories
        .slice(0, 5)
        .map(
          (category, index) => `
          <div class="legend-item">
            <i style="background:${COLORS[index % COLORS.length]}"></i>
            <span>${escapeHtml(category.label)}</span>
            <b>${category.count}</b>
          </div>`,
        )
        .join("")
    : '<span class="legend-item">No categories yet</span>';
}

async function loadStats() {
  const stats = await fetchJson("/api/stats");

  elements["metric-total"].textContent = stats.total;
  elements["metric-open"].textContent = stats.open;
  elements["metric-urgent"].textContent = stats.urgent;
  elements["metric-negative"].textContent = stats.negative;
  elements["donut-total"].textContent = stats.total;
  elements["nav-count"].textContent = stats.open;

  renderTrend(stats.trend);
  renderCategoryChart(stats.categories);
}

function createTicketRow(ticket) {
  return `
    <tr>
      <td class="subject-cell">
        <strong title="${escapeHtml(ticket.subject)}">${escapeHtml(ticket.subject)}</strong>
        <small>#T-${String(ticket.id).padStart(4, "0")} · ${new Date(ticket.created_at).toLocaleDateString()}</small>
      </td>
      <td class="customer-cell">
        <strong>${escapeHtml(ticket.customer_name)}</strong>
        <small>${escapeHtml(ticket.email)}</small>
      </td>
      <td>${escapeHtml(ticket.category)}</td>
      <td><span class="pill priority-${slug(ticket.priority)}">${escapeHtml(ticket.priority)}</span></td>
      <td><span class="sentiment-${slug(ticket.sentiment)}">● ${escapeHtml(ticket.sentiment)}</span></td>
      <td>
        <select class="status-select pill status-${slug(ticket.status)}" data-id="${ticket.id}" aria-label="Ticket status">
          <option ${ticket.status === "Open" ? "selected" : ""}>Open</option>
          <option ${ticket.status === "In Progress" ? "selected" : ""}>In Progress</option>
          <option ${ticket.status === "Resolved" ? "selected" : ""}>Resolved</option>
        </select>
      </td>
      <td>
        <button class="row-menu" data-delete="${ticket.id}" title="Delete ticket">•••</button>
      </td>
    </tr>`;
}

function bindTicketRowActions() {
  document.querySelectorAll(".status-select").forEach((select) => {
    select.addEventListener("change", async (event) => {
      const ticketId = event.target.dataset.id;

      try {
        await fetchJson(`/api/tickets/${ticketId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: event.target.value }),
        });
        showToast("Ticket status updated");
        await refreshDashboard();
      } catch (error) {
        showToast(error.message);
      }
    });
  });

  document.querySelectorAll("[data-delete]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      if (!window.confirm("Delete this ticket?")) {
        return;
      }

      const ticketId = event.currentTarget.dataset.delete;

      try {
        await fetchJson(`/api/tickets/${ticketId}`, { method: "DELETE" });
        showToast("Ticket deleted");
        await refreshDashboard();
      } catch (error) {
        showToast(error.message);
      }
    });
  });
}

async function loadTickets() {
  const params = new URLSearchParams();
  const search = elements.search.value.trim();

  if (search) {
    params.set("search", search);
  }
  if (elements["status-filter"].value) {
    params.set("status", elements["status-filter"].value);
  }
  if (elements["priority-filter"].value) {
    params.set("priority", elements["priority-filter"].value);
  }

  const data = await fetchJson(`/api/tickets?${params}`);

  elements["ticket-rows"].innerHTML = data.items.map(createTicketRow).join("");
  elements["empty-state"].classList.toggle("visible", data.items.length === 0);
  elements["table-count"].textContent =
    `Showing ${data.items.length} of ${data.total} ticket${data.total === 1 ? "" : "s"}`;

  bindTicketRowActions();
}

async function refreshDashboard() {
  try {
    await Promise.all([loadStats(), loadTickets()]);
  } catch (error) {
    showToast(error.message);
  }
}

function openTicketDialog() {
  elements["ticket-form"].reset();
  elements["form-error"].textContent = "";
  elements["ticket-dialog"].showModal();
}

function closeTicketDialog() {
  elements["ticket-dialog"].close();
}

function bindDialogEvents() {
  elements["new-ticket"].addEventListener("click", openTicketDialog);
  elements["empty-new"].addEventListener("click", openTicketDialog);
  elements["close-dialog"].addEventListener("click", closeTicketDialog);
  elements["cancel-dialog"].addEventListener("click", closeTicketDialog);

  elements["ticket-dialog"].addEventListener("click", (event) => {
    if (event.target === elements["ticket-dialog"]) {
      closeTicketDialog();
    }
  });

  elements["ticket-form"].addEventListener("submit", async (event) => {
    event.preventDefault();

    const form = event.currentTarget;
    const button = event.submitter;
    const data = Object.fromEntries(new FormData(form));

    button.disabled = true;
    button.textContent = "Creating…";
    elements["form-error"].textContent = "";

    try {
      const result = await fetchJson("/api/tickets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      closeTicketDialog();
      showToast(`Ticket added: ${result.category} · ${result.priority}`);
      await refreshDashboard();
    } catch (error) {
      elements["form-error"].textContent = error.message;
    } finally {
      button.disabled = false;
      button.innerHTML = "Create ticket <span>→</span>";
    }
  });
}

function bindFilterEvents() {
  ["status-filter", "priority-filter"].forEach((id) => {
    elements[id].addEventListener("change", () => {
      loadTickets().catch((error) => showToast(error.message));
    });
  });

  elements.search.addEventListener("input", () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => {
      loadTickets().catch((error) => showToast(error.message));
    }, 250);
  });
}

function initialize() {
  cacheElements();
  setCurrentDate();
  bindDialogEvents();
  bindFilterEvents();
  refreshDashboard();
}

initialize();
