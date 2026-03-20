const state = {
    accounts: [],
    summary: null,
    auth: null,
    roles: [],
    periods: { years: [], months_by_year: {}, latest: null },
    editingEntry: null,
    loginResolver: null,
};
const THEME_STORAGE_KEY = "contas_theme";
const SIDEBAR_STORAGE_KEY = "contas_sidebar_collapsed";

const MONTH_LABELS = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
};

function formatCurrency(value) {
    return new Intl.NumberFormat("es-CL", {
        style: "currency",
        currency: "CLP",
        maximumFractionDigits: 0,
    }).format(value || 0);
}

function signedClass(value) {
    if (Number(value) > 0) return "signed-positive";
    if (Number(value) < 0) return "signed-negative";
    return "signed-neutral";
}

function applySignedClass(element, value) {
    if (!element) return;
    element.classList.remove("signed-positive", "signed-negative", "signed-neutral");
    element.classList.add(signedClass(value));
}

function qs(id) {
    return document.getElementById(id);
}

function applyTheme(theme) {
    const isDark = theme === "dark";
    document.body.setAttribute("data-theme", isDark ? "dark" : "light");
    const toggleBtn = qs("theme-toggle-btn");
    const icon = qs("theme-toggle-icon");
    if (toggleBtn) {
        toggleBtn.setAttribute("aria-label", isDark ? "Cambiar a modo claro" : "Cambiar a modo oscuro");
        toggleBtn.setAttribute("title", isDark ? "Cambiar a modo claro" : "Cambiar a modo oscuro");
    }
    if (icon) {
        icon.textContent = isDark ? "☀️" : "🌙";
    }
}
function setupThemeToggle() {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    applyTheme(saved === "dark" ? "dark" : "light");

    const toggleBtn = qs("theme-toggle-btn");
    if (!toggleBtn) {
        return;
    }

    toggleBtn.addEventListener("click", () => {
        const current = document.body.getAttribute("data-theme") === "dark" ? "dark" : "light";
        const next = current === "dark" ? "light" : "dark";
        localStorage.setItem(THEME_STORAGE_KEY, next);
        applyTheme(next);
    });
}

function applySidebarCollapsed(collapsed) {
    document.body.classList.toggle("sidebar-collapsed", Boolean(collapsed));
    const icon = qs("sidebar-toggle-icon");
    const toggleBtn = qs("sidebar-toggle-btn");
    if (icon) {
        icon.textContent = collapsed ? "☰" : "✕";
    }
    if (toggleBtn) {
        toggleBtn.setAttribute("aria-label", collapsed ? "Expandir menú" : "Colapsar menú");
        toggleBtn.setAttribute("title", collapsed ? "Expandir menú" : "Colapsar menú");
    }
}

function setupSidebarToggle() {
    const saved = localStorage.getItem(SIDEBAR_STORAGE_KEY);
    const initialCollapsed = saved === null ? window.innerWidth <= 980 : saved === "1";
    applySidebarCollapsed(initialCollapsed);

    const toggleBtn = qs("sidebar-toggle-btn");
    if (!toggleBtn) {
        return;
    }

    toggleBtn.addEventListener("click", () => {
        const collapsed = !document.body.classList.contains("sidebar-collapsed");
        applySidebarCollapsed(collapsed);
        localStorage.setItem(SIDEBAR_STORAGE_KEY, collapsed ? "1" : "0");
    });
}

function normalizeMoneyValue(value) {
    let raw = String(value ?? "").trim().replace(/\s+/g, "").replace(/\$/g, "");
    if (!raw) return "";

    const hasDot = raw.includes(".");
    const hasComma = raw.includes(",");

    if (hasDot && hasComma) {
        const lastDot = raw.lastIndexOf(".");
        const lastComma = raw.lastIndexOf(",");
        const decimalSep = lastComma > lastDot ? "," : ".";
        const thousandSep = decimalSep === "," ? "." : ",";
        raw = raw.split(thousandSep).join("");
        raw = raw.replace(decimalSep, ".");
    } else if (hasComma) {
        const count = (raw.match(/,/g) || []).length;
        const idx = raw.lastIndexOf(",");
        const decimals = raw.length - idx - 1;
        if (count === 1 && decimals > 0 && decimals <= 2) {
            raw = raw.replace(",", ".");
        } else {
            raw = raw.split(",").join("");
        }
    } else if (hasDot) {
        const count = (raw.match(/\./g) || []).length;
        const idx = raw.lastIndexOf(".");
        const decimals = raw.length - idx - 1;
        if (!(count === 1 && decimals > 0 && decimals <= 2)) {
            raw = raw.split(".").join("");
        }
    }

    raw = raw.replace(/[^0-9.\-]/g, "");
    const negative = raw.startsWith("-");
    raw = raw.replace(/-/g, "");

    const firstDot = raw.indexOf(".");
    if (firstDot !== -1) {
        raw = raw.slice(0, firstDot + 1) + raw.slice(firstDot + 1).replace(/\./g, "");
    }

    if (!raw) return "";
    return negative ? `-${raw}` : raw;
}

function formatMoneyForInput(value) {
    const normalized = normalizeMoneyValue(value);
    if (!normalized) return "";
    const numeric = Number(normalized);
    if (!Number.isFinite(numeric)) return "";
    const decimals = normalized.includes(".") ? Math.min((normalized.split(".")[1] || "").length, 2) : 0;
    return new Intl.NumberFormat("es-CL", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: 2,
    }).format(numeric);
}

function setupMoneyMasks(root = document) {
    const inputs = root.querySelectorAll('[data-money-mask="1"]');
    inputs.forEach((input) => {
        if (input.dataset.moneyMaskReady === "1") {
            return;
        }
        input.dataset.moneyMaskReady = "1";

        input.addEventListener("focus", () => {
            input.value = normalizeMoneyValue(input.value);
        });

        input.addEventListener("blur", () => {
            input.value = formatMoneyForInput(input.value);
        });

        input.addEventListener("input", () => {
            input.value = input.value.replace(/[^0-9.,\-]/g, "");
        });

        if (input.value) {
            input.value = formatMoneyForInput(input.value);
        }
    });
}

function openEditEntryModal(entry) {
    state.editingEntry = entry;

    qs("edit-entry-id").value = entry.id || "";
    qs("edit-entry-date").value = entry.entry_date || "";
    qs("edit-entry-description").value = entry.description || "";
    qs("edit-entry-account-code").value = entry.account_code || "";
    qs("edit-entry-account-name").value = entry.account_name || "";
    qs("edit-entry-credit").value = String(entry.credit || 0);
    qs("edit-entry-debit").value = String(entry.debit || 0);
    qs("edit-entry-note").value = entry.note || "";
    qs("edit-entry-remove-receipt-flag").value = "0";
    qs("edit-entry-receipt-image").value = "";
    const removeBtn = qs("edit-entry-remove-receipt");
    removeBtn.textContent = "Quitar respaldo";
    const entryAttachments = Array.isArray(entry.receipt_attachments) ? entry.receipt_attachments : [];
    removeBtn.disabled = entryAttachments.length === 0 && !entry.receipt_image_url;
    const currentReceipt = qs("edit-entry-current-receipt");
    if (currentReceipt) {
        if (entryAttachments.length > 0) {
            currentReceipt.innerHTML = entryAttachments
                .map((att, idx) => `<a class="attachment" href="${att.url}" target="_blank" rel="noopener">Adjunto ${idx + 1}</a>`)
                .join(" | ");
        } else if (entry.receipt_image_url) {
            currentReceipt.innerHTML = `<a class="attachment" href="${entry.receipt_image_url}" target="_blank" rel="noopener">Ver respaldo actual</a>`;
        } else {
            currentReceipt.textContent = "Sin respaldo cargado";
        }
    }

    const modal = qs("edit-entry-modal");
    qs("edit-entry-credit").value = formatMoneyForInput(qs("edit-entry-credit").value);
    qs("edit-entry-debit").value = formatMoneyForInput(qs("edit-entry-debit").value);
    modal.hidden = false;
    qs("edit-entry-date").focus();
}

function closeEditEntryModal() {
    state.editingEntry = null;
    qs("edit-entry-modal").hidden = true;
    qs("edit-entry-form").reset();
}

function setupEditEntryModal() {
    const modal = qs("edit-entry-modal");
    const form = qs("edit-entry-form");

    qs("edit-entry-close").addEventListener("click", closeEditEntryModal);
    qs("edit-entry-cancel").addEventListener("click", closeEditEntryModal);
    qs("edit-entry-remove-receipt").addEventListener("click", () => {
        const flag = qs("edit-entry-remove-receipt-flag");
        const currentReceipt = qs("edit-entry-current-receipt");
        const removeBtn = qs("edit-entry-remove-receipt");
        const active = flag.value === "1";
        flag.value = active ? "0" : "1";
        if (flag.value === "1") {
            currentReceipt.textContent = "El respaldo actual será eliminado al guardar";
            removeBtn.textContent = "Deshacer quitar respaldo";
        } else if ((state.editingEntry?.receipt_attachments || []).length > 0) {
            currentReceipt.innerHTML = state.editingEntry.receipt_attachments
                .map((att, idx) => `<a class="attachment" href="${att.url}" target="_blank" rel="noopener">Adjunto ${idx + 1}</a>`)
                .join(" | ");
            removeBtn.textContent = "Quitar respaldo";
        } else if (state.editingEntry?.receipt_image_url) {
            currentReceipt.innerHTML = `<a class="attachment" href="${state.editingEntry.receipt_image_url}" target="_blank" rel="noopener">Ver respaldo actual</a>`;
            removeBtn.textContent = "Quitar respaldo";
        } else {
            currentReceipt.textContent = "Sin respaldo cargado";
            removeBtn.textContent = "Quitar respaldo";
        }
    });

    modal.addEventListener("click", (event) => {
        if (event.target === modal) {
            closeEditEntryModal();
        }
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const entryId = Number(qs("edit-entry-id").value || 0);
        if (!entryId) {
            toast("No se encontró el movimiento", true);
            return;
        }

        const payload = {
            entry_date: qs("edit-entry-date").value,
            description: qs("edit-entry-description").value.trim(),
            account_code: qs("edit-entry-account-code").value.trim(),
            account_name: qs("edit-entry-account-name").value.trim(),
            credit: normalizeMoneyValue(qs("edit-entry-credit").value) || "0",
            debit: normalizeMoneyValue(qs("edit-entry-debit").value) || "0",
            note: qs("edit-entry-note").value.trim(),
        };

        const formData = new FormData();
        Object.entries(payload).forEach(([key, value]) => formData.set(key, value));
        const receiptFile = qs("edit-entry-receipt-image")?.files?.[0];
        formData.set("remove_receipt", qs("edit-entry-remove-receipt-flag").value || "0");
        if (receiptFile) {
            formData.set("receipt_image", receiptFile);
        }

        try {
            await fetchJson(`/api/entries/${entryId}`, {
                method: "PATCH",
                body: formData,
            });
            closeEditEntryModal();
            await loadSummary();
            await loadRecent();
            toast("Movimiento actualizado");
        } catch (error) {
            toast(error.message, true);
        }
    });
}

function toast(message, isError = false) {
    const box = qs("toast");
    box.textContent = message;
    box.style.background = isError ? "#a33327" : "#0f2f3a";
    box.classList.add("show");
    if (isError) console.error("[toast error]", message);
    window.setTimeout(() => box.classList.remove("show"), isError ? 6000 : 2200);
}

function hasPermission(permission) {
    return Boolean(state.auth?.permissions?.[permission]);
}

function updateSessionUi() {
    qs("session-email").textContent = state.auth?.email || "Sin sesión";
    qs("session-role").textContent = state.auth?.effective_role || "-";

    const presenterEmail = document.querySelector('#voucher-form input[name="presenter_email"]');
    if (presenterEmail) {
        presenterEmail.value = state.auth?.email || "";
        presenterEmail.readOnly = !hasPermission("approve_vouchers");
    }
}

function applyPermissionVisibility() {
    const buttons = Array.from(document.querySelectorAll(".menu-btn"));
    buttons.forEach((btn) => {
        const permission = btn.dataset.permission;
        const allowed = !permission || hasPermission(permission);
        btn.hidden = !allowed;
        if (!allowed) {
            const panel = document.getElementById(btn.dataset.panel);
            if (panel) panel.hidden = true;
        }
    });
}

function setupLoginModal() {
    const form = qs("login-form");
    const modal = qs("login-modal");
    const errorBox = qs("login-error");
    const submitBtn = qs("login-submit-btn");

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const email = qs("login-email").value.trim();
        const password = qs("login-password").value || "";
        if (!email) {
            errorBox.textContent = "Debes ingresar un correo";
            errorBox.hidden = false;
            return;
        }

        submitBtn.disabled = true;
        errorBox.hidden = true;
        try {
            const login = await fetchJson("/auth/login", {
                method: "POST",
                body: JSON.stringify({ email, password }),
            });

            modal.hidden = true;
            form.reset();
            if (state.loginResolver) {
                state.loginResolver(login);
                state.loginResolver = null;
            }
        } catch (error) {
            errorBox.textContent = error.message || "No fue posible iniciar sesión";
            errorBox.hidden = false;
        } finally {
            submitBtn.disabled = false;
        }
    });
}

function requestLogin(cachedEmail = "") {
    return new Promise((resolve) => {
        state.loginResolver = resolve;
        qs("login-email").value = cachedEmail || "";
        qs("login-password").value = "";
        qs("login-error").hidden = true;
        qs("login-modal").hidden = false;
        qs("login-email").focus();
    });
}

async function loadSession() {
    const me = await fetchJson("/auth/me");
    if (me.user) {
        state.auth = me.user;
        state.roles = me.roles || [];
        localStorage.setItem("contable_user_email", me.user.email);
        updateSessionUi();
        applyPermissionVisibility();
        return;
    }

    const cached = localStorage.getItem("contable_user_email") || "";
    const login = await requestLogin(cached);
    state.auth = login.user;
    state.roles = login.roles || [];
    localStorage.setItem("contable_user_email", login.user.email);
    updateSessionUi();
    applyPermissionVisibility();
}

async function logout() {
    await fetchJson("/auth/logout", { method: "POST", body: JSON.stringify({}) });
    localStorage.removeItem("contable_user_email");
    window.location.reload();
}

async function switchUser() {
    const entered = window.prompt("Correo del usuario", state.auth?.email || "");
    if (!entered) {
        return;
    }

    const targetEmail = entered.trim();
    let login;
    if (state.auth?.effective_role === "admin") {
        login = await fetchJson("/auth/switch-user", {
            method: "POST",
            body: JSON.stringify({ target_email: targetEmail }),
        });
    } else {
        const password = window.prompt("Contraseña", "") || "";
        login = await fetchJson("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email: targetEmail, password }),
        });
    }

    state.auth = login.user;
    state.roles = login.roles || [];
    localStorage.setItem("contable_user_email", login.user.email);
    window.location.reload();
}

function openChangePasswordModal() {
    const modal = qs("change-password-modal");
    modal.hidden = false;
    qs("current-password").focus();
}

function closeChangePasswordModal() {
    qs("change-password-modal").hidden = true;
    qs("change-password-form").reset();
}

function setupChangePasswordModal() {
    const modal = qs("change-password-modal");
    const form = qs("change-password-form");

    qs("change-password-btn").addEventListener("click", openChangePasswordModal);
    qs("change-password-close").addEventListener("click", closeChangePasswordModal);
    qs("change-password-cancel").addEventListener("click", closeChangePasswordModal);

    modal.addEventListener("click", (event) => {
        if (event.target === modal) {
            closeChangePasswordModal();
        }
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const payload = {
            current_password: qs("current-password").value,
            new_password: qs("new-password").value,
            confirm_password: qs("confirm-password").value,
        };
        try {
            await fetchJson("/auth/change-password", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            closeChangePasswordModal();
            toast("Contraseña actualizada");
        } catch (error) {
            toast(error.message, true);
        }
    });
}

function applyKpis(totals) {
    const kpiPrev = qs("kpi-prev-balance");
    const kpiPeriod = qs("kpi-period-balance");
    const kpiAccum = qs("kpi-balance");

    kpiPrev.textContent = formatCurrency(totals.previous_balance);
    qs("kpi-credit").textContent = formatCurrency(totals.credit);
    qs("kpi-debit").textContent = formatCurrency(totals.debit);
    kpiPeriod.textContent = formatCurrency(totals.period_balance);
    kpiAccum.textContent = formatCurrency(totals.accumulated_final_balance);
    qs("kpi-entries").textContent = totals.entries;

    applySignedClass(kpiPrev, totals.previous_balance);
    applySignedClass(kpiPeriod, totals.period_balance);
    applySignedClass(kpiAccum, totals.accumulated_final_balance);
}

function renderYearOptions(selectedYear = "") {
    const select = qs("year");
    const years = state.periods.years || [];
    select.innerHTML = '<option value="">Todos</option>';

    years.forEach((year) => {
        const option = document.createElement("option");
        option.value = String(year);
        option.textContent = String(year);
        if (String(year) === String(selectedYear)) {
            option.selected = true;
        }
        select.appendChild(option);
    });
}

function renderMonthOptions(selectedYear = "", selectedMonth = "") {
    const select = qs("month");
    const months = selectedYear
        ? state.periods.months_by_year?.[String(selectedYear)] || []
        : [];

    select.innerHTML = '<option value="">Todos</option>';
    months.forEach((month) => {
        const option = document.createElement("option");
        option.value = String(month);
        option.textContent = MONTH_LABELS[month] || String(month);
        if (String(month) === String(selectedMonth)) {
            option.selected = true;
        }
        select.appendChild(option);
    });

    select.disabled = !selectedYear;
}

async function loadAvailablePeriods() {
    const payload = await fetchJson("/api/reports/available-periods");
    state.periods = payload;

    const defaultYear = payload.latest?.year ? String(payload.latest.year) : "";
    const defaultMonth = payload.latest?.month ? String(payload.latest.month) : "";

    renderYearOptions(defaultYear);
    renderMonthOptions(defaultYear, defaultMonth);
}

function setupPeriodFilters() {
    qs("year").addEventListener("change", async (event) => {
        const selectedYear = event.currentTarget.value;
        renderMonthOptions(selectedYear, "");

        try {
            await loadSummary();
            await loadRecent();
        } catch (error) {
            toast(error.message, true);
        }
    });

    qs("month").addEventListener("change", async () => {
        try {
            await loadSummary();
            await loadRecent();
        } catch (error) {
            toast(error.message, true);
        }
    });
}

function treeNodeTemplate(node) {
    const wrapper = document.createElement("article");
    wrapper.className = "node";

    const header = document.createElement("button");
    header.type = "button";
    header.className = "node-header";
    const nodeBalanceClass = signedClass(node.balance);
    header.innerHTML = `
        <span class="node-title">${node.code} | ${node.name || "(sin nombre)"}</span>
        <span class="badge">Nivel ${node.level}</span>
        <span class="amount out">Egreso ${formatCurrency(node.debit)}</span>
        <span class="amount in">Ingreso ${formatCurrency(node.credit)}</span>
        <span class="amount ${nodeBalanceClass}">Saldo ${formatCurrency(node.balance)}</span>
    `;

    const content = document.createElement("div");
    content.className = "node-content";

    if (node.entries && node.entries.length > 0) {
        const detail = document.createElement("div");
        detail.className = "entries";
        node.entries.slice(0, 40).forEach((entry) => {
            const row = document.createElement("div");
            row.className = "entry-row";
            const attachments = Array.isArray(entry.receipt_attachments) ? entry.receipt_attachments : [];
            const attachment = attachments.length > 0
                ? attachments
                    .map((att, idx) => `<a class="attachment" href="${att.url}" target="_blank" rel="noopener">Adjunto ${idx + 1}</a>`)
                    .join(" | ")
                : "";
            row.innerHTML = `
                <span>${entry.entry_date}</span>
                <span>${entry.description}</span>
                <span class="amount out">${formatCurrency(entry.debit)}</span>
                <span class="amount in">${formatCurrency(entry.credit)} ${attachment}</span>
            `;
            detail.appendChild(row);
        });
        content.appendChild(detail);
    }

    if (node.children && node.children.length > 0) {
        node.children.forEach((child) => content.appendChild(treeNodeTemplate(child)));
    }

    header.addEventListener("click", () => {
        wrapper.classList.toggle("open");
    });

    wrapper.appendChild(header);
    wrapper.appendChild(content);
    return wrapper;
}

function renderSummary(summary) {
    applyKpis(summary.totals);
    const tbody = qs("summary-body");
    tbody.innerHTML = "";

    // Extraer entradas del árbol jerárquico sin duplicar por id.
    const entriesById = new Map();
    function extractEntries(nodes) {
        nodes.forEach((node) => {
            if (node.entries && node.entries.length > 0) {
                node.entries.forEach((entry) => {
                    if (!entry || entry.id === undefined || entry.id === null) {
                        return;
                    }
                    if (!entriesById.has(entry.id)) {
                        entriesById.set(entry.id, entry);
                    }
                });
            }
            if (node.children && node.children.length > 0) {
                extractEntries(node.children);
            }
        });
    }

    if (summary.tree && summary.tree.length > 0) {
        extractEntries(summary.tree);
    }

    const allEntries = Array.from(entriesById.values());
    const pendingEntries = (summary.pending_items || []).map((item) => ({ ...item, pending: true }));
    const combinedEntries = [...allEntries, ...pendingEntries];

    if (combinedEntries.length === 0) {
        const row = document.createElement("tr");
        row.innerHTML = `<td colspan="7">No hay datos para este filtro.</td>`;
        tbody.appendChild(row);
        return;
    }

    // Ordenar por fecha descendente
    combinedEntries.sort((a, b) => new Date(b.entry_date) - new Date(a.entry_date));

    combinedEntries.forEach((entry) => {
        const row = document.createElement("tr");
        if (entry.pending) {
            row.classList.add("pending-row");
        }
        const attachments = Array.isArray(entry.receipt_attachments) ? entry.receipt_attachments : [];
        const attachment = attachments.length > 0
            ? attachments
                .map((att, idx) => `<a class="attachment" href="${att.url}" target="_blank" rel="noopener">Adjunto ${idx + 1}</a>`)
                .join(" | ")
            : "-";
        const accountCell = `${entry.account_code || "-"} ${entry.account_name || ""}`.trim();
        const actions = !entry.pending && hasPermission("create_entries")
            ? `<button type="button" class="edit-entry-btn" data-id="${entry.id}">Editar</button>
               <button type="button" class="delete-entry-btn" data-id="${entry.id}">Borrar</button>`
            : "-";
        const pendingIcon = entry.pending
            ? `<span class="pending-icon" title="Pendiente de aprobación">!</span>`
            : "";
        row.innerHTML = `
            <td>${pendingIcon}${entry.entry_date || ""}</td>
            <td>${accountCell}</td>
            <td class="num">${formatCurrency(entry.credit)}</td>
            <td class="num">${formatCurrency(entry.debit)}</td>
            <td>${entry.description || ""}${entry.pending ? `<br><small>Pendiente de aprobación</small>` : ""}${entry.note ? `<br><small>${entry.note}</small>` : ""}</td>
            <td>${attachment}</td>
            <td><div class="row-actions">${actions}</div></td>
        `;

        const firstAttachmentUrl = attachments[0]?.url || entry.receipt_image_url;
        if (firstAttachmentUrl) {
            row.classList.add("summary-row-with-attachment");
            row.title = "Click para abrir respaldo";
            row.addEventListener("click", (event) => {
                if (event.target.closest("a, button, input, select, textarea, label")) {
                    return;
                }
                const newTab = window.open(firstAttachmentUrl, "_blank");
                if (newTab) {
                    newTab.opener = null;
                }
            });
        }

        tbody.appendChild(row);
    });

    if (!hasPermission("create_entries")) {
        return;
    }

    tbody.querySelectorAll(".edit-entry-btn").forEach((button) => {
        button.addEventListener("click", async () => {
            const entryId = Number(button.dataset.id);
            const entry = allEntries.find((item) => item.id === entryId);
            if (!entry) {
                toast("No se encontró el movimiento", true);
                return;
            }
            openEditEntryModal(entry);
        });
    });

    tbody.querySelectorAll(".delete-entry-btn").forEach((button) => {
        button.addEventListener("click", async () => {
            const entryId = Number(button.dataset.id);
            const accepted = window.confirm("¿Seguro que deseas borrar este movimiento?");
            if (!accepted) {
                return;
            }

            try {
                await fetchJson(`/api/entries/${entryId}`, {
                    method: "DELETE",
                });
                await loadSummary();
                await loadRecent();
                toast("Movimiento eliminado");
            } catch (error) {
                toast(error.message, true);
            }
        });
    });
}


async function fetchJson(url, options = {}) {
    const headers = {};
    if (!(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
    }

    const response = await fetch(url, {
        headers,
        ...options,
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.message || "Error de solicitud");
    }
    return data;
}

function buildFilterQuery() {
    const params = new URLSearchParams();
    const year = qs("year").value;
    const month = qs("month").value;

    if (year) params.set("year", year);
    if (month) params.set("month", month);
    params.set("include_entries", "1");

    return params.toString();
}

function buildReportQuery() {
    const params = new URLSearchParams();
    const year = qs("year").value;
    const month = qs("month").value;

    if (year) params.set("year", year);
    if (month) params.set("month", month);
    return params.toString();
}

function renderBarReport(targetId, items, emptyMessage, tone = "neutral") {
    const container = qs(targetId);
    if (!container) return;

    if (!items || items.length === 0) {
        container.innerHTML = `<p class="report-empty">${emptyMessage}</p>`;
        return;
    }

    const max = Math.max(...items.map((item) => Number(item.amount || 0)), 1);
    container.innerHTML = "";

    items.forEach((item, idx) => {
        const amount = Number(item.amount || 0);
        const width = Math.max(6, (amount / max) * 100);
        const row = document.createElement("div");
        row.className = `bar-row tone-${tone}`;
        row.innerHTML = `
            <div class="bar-meta">
                <span class="bar-rank">#${idx + 1}</span>
                <span class="bar-title">${item.description || item.type || "Sin detalle"}</span>
                <span class="bar-amount">${formatCurrency(amount)}</span>
            </div>
            <div class="bar-track">
                <div class="bar-fill" style="width: ${width}%"></div>
            </div>
            <div class="bar-subtitle">${item.entry_date || item.account_code || ""}</div>
        `;
        container.appendChild(row);
    });
}

function renderLevel3SummaryRows(items) {
    const tbody = qs("report-level3-body");
    if (!tbody) return;

    tbody.innerHTML = "";
    if (!items || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8">No hay datos para el período seleccionado.</td></tr>';
        return;
    }

    items.forEach((item) => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${item.code || "-"}</td>
            <td>${item.name || "-"}</td>
            <td class="num">${formatCurrency(item.period?.credit || 0)}</td>
            <td class="num">${formatCurrency(item.period?.debit || 0)}</td>
            <td class="num ${signedClass(item.period?.balance || 0)}">${formatCurrency(item.period?.balance || 0)}</td>
            <td class="num">${formatCurrency(item.accumulated?.credit || 0)}</td>
            <td class="num">${formatCurrency(item.accumulated?.debit || 0)}</td>
            <td class="num ${signedClass(item.accumulated?.balance || 0)}">${formatCurrency(item.accumulated?.balance || 0)}</td>
        `;
        tbody.appendChild(row);
    });
}

function formatReportPeriod(filters = {}) {
    const from = filters.period_start || "inicio";
    const to = filters.period_end || "hoy";
    if (!filters.period_start && !filters.period_end) {
        return "Período: todo el histórico";
    }
    return `Período: ${from} a ${to}`;
}

async function openReportsModal() {
    const modal = qs("reports-modal");
    if (!modal) return;

    try {
        const query = buildReportQuery();
        const payload = await fetchJson(`/api/reports/insights?${query}`);

        qs("reports-period-label").textContent = formatReportPeriod(payload.filters || {});
        renderBarReport("report-top-expenses", payload.top_expenses, "Sin egresos en el período.", "expense");
        renderBarReport("report-top-incomes", payload.top_incomes, "Sin ingresos en el período.", "income");
        renderBarReport("report-investments", payload.investments_by_type, "Sin inversiones acumuladas.", "investment");
        renderLevel3SummaryRows(payload.level3_summary || []);

        modal.hidden = false;
    } catch (error) {
        toast(error.message, true);
    }
}

function closeReportsModal() {
    const modal = qs("reports-modal");
    if (!modal) return;
    modal.hidden = true;
}

function setupReportsModal() {
    const modal = qs("reports-modal");
    const openBtn = qs("open-reports-btn");
    const closeBtn = qs("reports-close");
    const exportBtn = qs("export-reports-xlsx");

    if (!modal || !openBtn || !closeBtn) {
        return;
    }

    openBtn.addEventListener("click", async () => {
        await openReportsModal();
    });

    closeBtn.addEventListener("click", closeReportsModal);

    modal.addEventListener("click", (event) => {
        if (event.target === modal) {
            closeReportsModal();
        }
    });

    if (exportBtn) {
        exportBtn.addEventListener("click", async () => {
            try {
                const query = buildReportQuery();
                const link = document.createElement("a");
                link.href = `/api/reports/export?${query}&format=xlsx`;
                link.click();
                toast("Descargando reportes...");
            } catch (error) {
                toast(error.message, true);
            }
        });
    }
}

function setupMenu() {
    const buttons = Array.from(document.querySelectorAll(".menu-btn")).filter((btn) => !btn.hidden && btn.dataset.panel);
    const panels = Array.from(document.querySelectorAll(".panel"));

    function activate(panelId) {
        buttons.forEach((btn) => {
            btn.classList.toggle("active", btn.dataset.panel === panelId);
        });

        panels.forEach((panel) => {
            panel.hidden = panel.id !== panelId;
        });
    }

    buttons.forEach((btn) => {
        btn.addEventListener("click", () => {
            activate(btn.dataset.panel);
            if (window.innerWidth <= 980) {
                applySidebarCollapsed(true);
                localStorage.setItem(SIDEBAR_STORAGE_KEY, "1");
            }
        });
    });

    activate(buttons[0]?.dataset.panel || "panel-summary");
}

async function loadSummary() {
    const query = buildFilterQuery();
    const payload = await fetchJson(`/api/reports/bank-summary?${query}`);
    state.summary = payload;
    renderSummary(payload);
}

async function loadAccounts() {
    const payload = await fetchJson("/api/accounts");
    state.accounts = payload.items || [];
    const datalist = qs("account-options");
    datalist.innerHTML = "";

    state.accounts.forEach((item) => {
        const option = document.createElement("option");
        option.value = item.code;
        option.label = `${item.code} - ${item.name}`;
        datalist.appendChild(option);
    });
}

async function loadRecent() {
    const year = qs("year").value;
    const month = qs("month").value;
    const params = new URLSearchParams({ limit: "30" });
    if (year) params.set("year", year);
    if (month) params.set("month", month);
    const payload = await fetchJson(`/api/entries/recent?${params.toString()}`);
    const tbody = qs("recent-body");
    tbody.innerHTML = "";

    payload.items.forEach((item) => {
        const row = document.createElement("tr");
        const attachments = Array.isArray(item.receipt_attachments) ? item.receipt_attachments : [];
        const attachment = attachments.length > 0
            ? attachments
                .map((att, idx) => `<a class="attachment" href="${att.url}" target="_blank" rel="noopener">Adjunto ${idx + 1}</a>`)
                .join(" | ")
            : "-";
        row.innerHTML = `
            <td>${item.entry_date || ""}</td>
            <td>${item.account_code || ""} ${item.account_name || ""}</td>
            <td>${item.description || ""}</td>
            <td class="num">${formatCurrency(item.debit)}</td>
            <td class="num">${formatCurrency(item.credit)}</td>
            <td>${item.movement_type || "general"}</td>
            <td>${attachment}</td>
        `;
        tbody.appendChild(row);
    });
}

function formToJson(form) {
    const payload = {};
    const fd = new FormData(form);
    fd.forEach((value, key) => {
        if (value !== "") payload[key] = value;
    });
    return payload;
}

function makeVoucherLineRow(defaults = {}) {
    const row = document.createElement("div");
    row.className = "voucher-line";
    row.innerHTML = `
        <label>Cuenta
            <input list="account-options" class="vl-account" value="${defaults.account_code || ""}" placeholder="2.01.03.05">
        </label>
        <label>Descripcion
            <input type="text" class="vl-description" value="${defaults.description || ""}" placeholder="Detalle linea" required>
        </label>
        <label>Debe
            <input type="text" class="vl-debit" data-money-mask="1" inputmode="decimal" value="${defaults.debit || ""}" placeholder="0">
        </label>
        <label>Haber
            <input type="text" class="vl-credit" data-money-mask="1" inputmode="decimal" value="${defaults.credit || ""}" placeholder="0">
        </label>
        <button type="button" class="vl-remove">Quitar</button>
    `;

    row.querySelector(".vl-remove").addEventListener("click", () => row.remove());
    setupMoneyMasks(row);
    return row;
}

function collectVoucherLines() {
    const rows = Array.from(document.querySelectorAll("#voucher-lines .voucher-line"));
    return rows.map((row) => ({
        account_code: row.querySelector(".vl-account").value.trim(),
        description: row.querySelector(".vl-description").value.trim(),
        debit: normalizeMoneyValue(row.querySelector(".vl-debit").value.trim()) || "0",
        credit: normalizeMoneyValue(row.querySelector(".vl-credit").value.trim()) || "0",
    }));
}

async function loadPendingVouchers() {
    const payload = await fetchJson("/api/vouchers?status=pending_approval");
    const tbody = qs("voucher-pending-body");
    if (!tbody) {
        return;
    }
    tbody.innerHTML = "";

    payload.items.forEach((item) => {
        const canApprove = hasPermission("approve_vouchers");
        const actionCell = canApprove
            ? `
                <input type="email" class="approve-email" placeholder="aprobador@colbun.cl" value="${item.assigned_approver_email}">
                <button type="button" class="approve-btn" data-id="${item.id}">Aprobar</button>
                <button type="button" class="reject-btn" data-id="${item.id}">Rechazar</button>
            `
            : "-";

        const motivo = item.rejection_reason
            ? `<span title="${item.rejection_reason}">${item.rejection_reason.slice(0, 40)}${item.rejection_reason.length > 40 ? "..." : ""}</span>`
            : "-";

        const row = document.createElement("tr");
        if (item.status === "rejected") row.classList.add("rejected-row");
        row.innerHTML = `
            <td>${item.voucher_number}</td>
            <td>${item.voucher_date}</td>
            <td>${item.presenter_name || ""}<br><small>${item.presenter_email}</small></td>
            <td>${item.assigned_approver_email}</td>
            <td>${item.line_count}</td>
            <td>${item.status}</td>
            <td>${motivo}</td>
            <td>${actionCell}</td>
        `;
        tbody.appendChild(row);
    });

    if (!hasPermission("approve_vouchers")) {
        return;
    }

    tbody.querySelectorAll(".approve-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const tr = btn.closest("tr");
            const input = tr.querySelector(".approve-email");
            const approver_email = (input.value || "").trim();
            if (!approver_email) {
                toast("Debes indicar email aprobador", true);
                return;
            }

            try {
                await fetchJson(`/api/vouchers/${btn.dataset.id}/approve`, {
                    method: "POST",
                    body: JSON.stringify({ approver_email }),
                });
                await loadPendingVouchers();
                await loadSummary();
                await loadRecent();
                toast("Comprobante aprobado y enviado a contabilidad");
            } catch (error) {
                toast(error.message, true);
            }
        });
    });

    tbody.querySelectorAll(".reject-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const tr = btn.closest("tr");
            const input = tr.querySelector(".approve-email");
            const rejector_email = (input.value || "").trim();
            if (!rejector_email) {
                toast("Debes indicar tu email en el campo aprobador para rechazar", true);
                return;
            }

            const rejection_reason = window.prompt("Motivo del rechazo (requerido)", "");
            if (rejection_reason === null) return;
            if (!rejection_reason.trim()) {
                toast("Debes ingresar un motivo de rechazo", true);
                return;
            }

            try {
                await fetchJson(`/api/vouchers/${btn.dataset.id}/reject`, {
                    method: "POST",
                    body: JSON.stringify({ rejector_email, rejection_reason: rejection_reason.trim() }),
                });
                await loadPendingVouchers();
                await loadSummary();
                toast("Comprobante rechazado");
            } catch (error) {
                toast(error.message, true);
            }
        });
    });
}

async function loadAuditLog(filters = {}) {
    if (!hasPermission("manage_users")) return;
    const params = new URLSearchParams({ limit: "200" });
    if (filters.user_email) params.set("user_email", filters.user_email);
    if (filters.action) params.set("action", filters.action);

    const payload = await fetchJson(`/admin/audit-logs?${params.toString()}`);
    const tbody = qs("audit-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (payload.items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7">Sin registros.</td></tr>`;
        return;
    }

    payload.items.forEach((item) => {
        const row = document.createElement("tr");
        const ts = item.timestamp ? item.timestamp.replace("T", " ").slice(0, 19) : "";
        row.innerHTML = `
            <td>${ts}</td>
            <td>${item.user_email || "-"}</td>
            <td><code>${item.action || ""}</code></td>
            <td>${item.entity || "-"}</td>
            <td>${item.entity_id ?? "-"}</td>
            <td>${item.detail || "-"}</td>
            <td>${item.ip_address || "-"}</td>
        `;
        tbody.appendChild(row);
    });
}

async function loadUsers() {
    if (!hasPermission("manage_users")) {
        return;
    }

    const payload = await fetchJson("/admin/users");
    const createRoleSelect = qs("new-user-role");
    if (createRoleSelect) {
        createRoleSelect.innerHTML = state.roles
            .map((role) => `<option value="${role}">${role}</option>`)
            .join("");
        if (!createRoleSelect.value && state.roles.includes("visita")) {
            createRoleSelect.value = "visita";
        }
    }

    const tbody = qs("users-body");
    if (!tbody) {
        return;
    }
    tbody.innerHTML = "";

    payload.items.forEach((item) => {
        const options = state.roles
            .map((role) => `<option value="${role}" ${item.role === role ? "selected" : ""}>${role}</option>`)
            .join("");

        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${item.email}</td>
            <td>${item.name || ""}</td>
            <td>${item.role}</td>
            <td>${item.effective_role}</td>
            <td>
                <div class="row-actions">
                    <select class="role-select" data-id="${item.id}">${options}</select>
                    <button type="button" class="save-role-btn" data-id="${item.id}">Guardar</button>
                    <button type="button" class="delete-user-btn" data-id="${item.id}">Eliminar</button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });

    tbody.querySelectorAll(".save-role-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const row = btn.closest("tr");
            const select = row.querySelector(".role-select");
            const role = select.value;
            try {
                const payloadUpdate = await fetchJson(`/admin/users/${btn.dataset.id}/role`, {
                    method: "PATCH",
                    body: JSON.stringify({ role }),
                });
                await loadUsers();
                if (payloadUpdate?.user?.email === state.auth?.email) {
                    state.auth = payloadUpdate.user;
                    updateSessionUi();
                    applyPermissionVisibility();
                    setupMenu();
                }
                toast(payloadUpdate.message || "Rol actualizado");
            } catch (error) {
                toast(error.message, true);
            }
        });
    });

    tbody.querySelectorAll(".delete-user-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const row = btn.closest("tr");
            const email = row?.children?.[0]?.textContent?.trim() || "";
            const accepted = window.confirm(`¿Seguro que deseas eliminar a ${email || "este usuario"}?`);
            if (!accepted) {
                return;
            }

            try {
                const deleted = await fetchJson(`/admin/users/${btn.dataset.id}`, {
                    method: "DELETE",
                });
                await loadUsers();
                await loadAuditLog();
                toast(deleted.message || "Usuario eliminado");
            } catch (error) {
                toast(error.message, true);
            }
        });
    });
}

async function loadBankStatements() {
    if (!hasPermission("view_reports")) {
        return;
    }

    try {
        const payload = await fetchJson("/api/bank-statements");
        const tbody = qs("statements-body");
        if (!tbody) {
            return;
        }
        tbody.innerHTML = "";

        const canManage = hasPermission("manage_term_deposits");

        payload.items.forEach((item) => {
            const row = document.createElement("tr");
            const uploadedAt = item.uploaded_at ? item.uploaded_at.replace("T", " ").slice(0, 16) : "-";
            const actions = canManage
                ? `
                    <div class="row-actions">
                        <a href="/api/bank-statements/${item.id}/view" class="view-btn" target="_blank" rel="noopener">Ver</a>
                        <a href="/api/bank-statements/${item.id}/download" class="download-btn">Descargar</a>
                        <button type="button" class="delete-statement-btn" data-id="${item.id}">Eliminar</button>
                    </div>
                `
                : `<a href="/api/bank-statements/${item.id}/view" class="view-btn" target="_blank" rel="noopener">Ver</a>`;

            row.innerHTML = `
                <td>${item.year}-${String(item.month).padStart(2, "0")}</td>
                <td>${item.original_filename}</td>
                <td><code>${item.file_type.toUpperCase()}</code></td>
                <td>${item.uploaded_by_email}</td>
                <td>${uploadedAt}</td>
                <td>${item.description || "-"}</td>
                <td>${actions}</td>
            `;
            tbody.appendChild(row);
        });

        if (canManage) {
            tbody.querySelectorAll(".delete-statement-btn").forEach((btn) => {
                btn.addEventListener("click", async () => {
                    const row = btn.closest("tr");
                    const period = row?.children?.[0]?.textContent?.trim() || "";
                    const accepted = window.confirm(`¿Seguro que deseas eliminar la cartola de ${period}?`);
                    if (!accepted) {
                        return;
                    }

                    try {
                        await fetchJson(`/api/bank-statements/${btn.dataset.id}`, {
                            method: "DELETE",
                        });
                        await loadBankStatements();
                        toast("Cartola eliminada");
                    } catch (error) {
                        toast(error.message, true);
                    }
                });
            });
        }
    } catch (error) {
        toast(error.message, true);
    }
}

function setupBankStatementsForm() {
    const form = qs("upload-statement-form");
    const actionsDiv = qs("upload-stmt-actions");
    const yearInput = qs("stmt-year");
    const monthInput = qs("stmt-month");
    const fileInput = qs("stmt-file");
    const descriptionInput = qs("stmt-description");

    if (!form || !actionsDiv || !yearInput || !monthInput || !fileInput || !descriptionInput) {
        return;
    }

    if (!hasPermission("manage_term_deposits")) {
        form.parentElement.innerHTML = '<p class="subtitle">Solo Tesoreros y Administradores pueden subir cartolas.</p>';
        return;
    }

    actionsDiv.style.display = "flex";

    const today = new Date();
    yearInput.value = today.getFullYear();

    fileInput.addEventListener("change", () => {
        const file = fileInput.files?.[0];
        if (!file || !file.name) {
            fileInput.setCustomValidity("");
            return;
        }

        const match = String(file.name).trim().match(/^(\d{4})-(\d{2})\.(pdf|xlsx)$/i);
        if (!match) {
            fileInput.setCustomValidity("El archivo debe tener formato yyyy-mm.pdf o yyyy-mm.xlsx");
            fileInput.reportValidity();
            return;
        }

        fileInput.setCustomValidity("");
        const year = Number(match[1]);
        const month = Number(match[2]);
        if (!month || month < 1 || month > 12) {
            fileInput.setCustomValidity("El mes debe estar entre 01 y 12");
            fileInput.reportValidity();
            return;
        }

        yearInput.value = year;
        monthInput.value = String(month);
        descriptionInput.value = `Cartola ${MONTH_LABELS[month]} del año ${year}`;
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const payload = new FormData();
        payload.set("year", yearInput.value);
        payload.set("month", monthInput.value);
        payload.set("description", descriptionInput.value);
        payload.set("file", fileInput.files[0]);

        try {
            const result = await fetchJson("/api/bank-statements", {
                method: "POST",
                body: payload,
            });
            form.reset();
            yearInput.value = today.getFullYear();
            await loadBankStatements();
            toast(result.message || "Cartola subida");
        } catch (error) {
            toast(error.message, true);
        }
    });
}

async function loadTreasuryLibrary() {
    if (!hasPermission("view_reports")) {
        return;
    }

    try {
        const payload = await fetchJson("/api/treasury-library");
        const tbody = qs("library-body");
        if (!tbody) {
            return;
        }
        tbody.innerHTML = "";

        const canManage = hasPermission("manage_term_deposits");

        payload.items.forEach((item) => {
            const row = document.createElement("tr");
            const uploadedAt = item.uploaded_at ? item.uploaded_at.replace("T", " ").slice(0, 16) : "-";
            const actions = canManage
                ? `
                    <div class="row-actions">
                        <a href="/api/treasury-library/${item.id}/view" class="view-btn" target="_blank" rel="noopener">Ver</a>
                        <a href="/api/treasury-library/${item.id}/download" class="download-btn">Descargar</a>
                        <button type="button" class="delete-library-btn" data-id="${item.id}">Eliminar</button>
                    </div>
                `
                : `<a href="/api/treasury-library/${item.id}/view" class="view-btn" target="_blank" rel="noopener">Ver</a>`;

            row.innerHTML = `
                <td>${item.title || "-"}</td>
                <td>${item.original_filename || "-"}</td>
                <td><code>${(item.file_type || "").toUpperCase()}</code></td>
                <td>${item.uploaded_by_email || "-"}</td>
                <td>${uploadedAt}</td>
                <td>${item.description || "-"}</td>
                <td>${actions}</td>
            `;
            tbody.appendChild(row);
        });

        if (canManage) {
            tbody.querySelectorAll(".delete-library-btn").forEach((btn) => {
                btn.addEventListener("click", async () => {
                    const row = btn.closest("tr");
                    const title = row?.children?.[0]?.textContent?.trim() || "documento";
                    const accepted = window.confirm(`¿Seguro que deseas eliminar "${title}"?`);
                    if (!accepted) {
                        return;
                    }

                    try {
                        await fetchJson(`/api/treasury-library/${btn.dataset.id}`, {
                            method: "DELETE",
                        });
                        await loadTreasuryLibrary();
                        toast("Documento eliminado");
                    } catch (error) {
                        toast(error.message, true);
                    }
                });
            });
        }
    } catch (error) {
        toast(error.message, true);
    }
}

function setupTreasuryLibraryForm() {
    const form = qs("upload-library-form");
    const actionsDiv = qs("upload-lib-actions");
    const titleInput = qs("lib-title");
    const descriptionInput = qs("lib-description");
    const fileInput = qs("lib-file");

    if (!form || !actionsDiv || !titleInput || !descriptionInput || !fileInput) {
        return;
    }

    if (!hasPermission("manage_term_deposits")) {
        form.parentElement.innerHTML = '<p class="subtitle">Solo Tesoreros y Administradores pueden subir documentos.</p>';
        return;
    }

    actionsDiv.style.display = "flex";

    fileInput.addEventListener("change", () => {
        const file = fileInput.files?.[0];
        if (!file || !file.name) {
            return;
        }
        if (!titleInput.value.trim()) {
            titleInput.value = file.name.replace(/\.[^.]+$/, "");
        }
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const payload = new FormData();
        payload.set("title", titleInput.value.trim());
        payload.set("description", descriptionInput.value.trim());
        payload.set("file", fileInput.files[0]);

        try {
            const result = await fetchJson("/api/treasury-library", {
                method: "POST",
                body: payload,
            });
            form.reset();
            await loadTreasuryLibrary();
            toast(result.message || "Documento subido");
        } catch (error) {
            toast(error.message, true);
        }
    });
}

async function refreshAllVisibleData() {
    await Promise.all([
        loadSummary(),
        loadRecent(),
        loadPendingVouchers(),
        loadUsers(),
        loadAuditLog(),
        loadBankStatements(),
        loadTreasuryLibrary(),
    ]);
}

function setupForms() {
    qs("filter-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        try {
            await loadSummary();
            await loadRecent();
            toast("Resumen actualizado");
        } catch (error) {
            toast(error.message, true);
        }
    });

    qs("entry-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const payload = new FormData(form);
        payload.set("amount", normalizeMoneyValue(payload.get("amount")) || "0");

        try {
            await fetchJson("/api/entries", {
                method: "POST",
                body: payload,
            });
            form.reset();
            await loadSummary();
            await loadRecent();
            toast("Movimiento registrado");
        } catch (error) {
            toast(error.message, true);
        }
    });

    qs("open-deposit-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const payload = formToJson(form);
        payload.principal_amount = normalizeMoneyValue(payload.principal_amount) || "0";

        try {
            await fetchJson("/api/term-deposits/open", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            form.reset();
            await loadSummary();
            await loadRecent();
            toast("Deposito a plazo registrado");
        } catch (error) {
            toast(error.message, true);
        }
    });

    qs("rescue-deposit-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const payload = formToJson(form);
        payload.rescue_amount = normalizeMoneyValue(payload.rescue_amount) || "0";
        const code = payload.code;
        delete payload.code;

        try {
            await fetchJson(`/api/term-deposits/${encodeURIComponent(code)}/rescue`, {
                method: "POST",
                body: JSON.stringify(payload),
            });
            form.reset();
            await loadSummary();
            await loadRecent();
            toast("Rescate registrado");
        } catch (error) {
            toast(error.message, true);
        }
    });

    qs("add-voucher-line").addEventListener("click", () => {
        qs("voucher-lines").appendChild(makeVoucherLineRow());
    });

    const auditFilterForm = qs("audit-filter-form");
    if (auditFilterForm) {
        auditFilterForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const email = (qs("audit-filter-email").value || "").trim();
            const action = (qs("audit-filter-action").value || "").trim();
            try {
                await loadAuditLog({ user_email: email, action });
            } catch (error) {
                toast(error.message, true);
            }
        });
    }

    const createUserForm = qs("create-user-form");
    if (createUserForm) {
        createUserForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const payload = {
                email: qs("new-user-email").value.trim(),
                name: qs("new-user-name").value.trim(),
                role: qs("new-user-role").value,
                password: qs("new-user-password").value,
            };

            try {
                const created = await fetchJson("/admin/users", {
                    method: "POST",
                    body: JSON.stringify(payload),
                });
                createUserForm.reset();
                if (state.roles.includes("visita")) {
                    qs("new-user-role").value = "visita";
                }
                await loadUsers();
                await loadAuditLog();
                toast(created.message || "Usuario creado");
            } catch (error) {
                toast(error.message, true);
            }
        });
    }

    qs("submit-voucher").addEventListener("click", async () => {
        const form = qs("voucher-form");
        const payload = new FormData(form);
        const lines = collectVoucherLines().filter((line) => line.description);

        if (lines.length === 0) {
            toast("Debes agregar al menos una linea", true);
            return;
        }

        payload.append("lines", JSON.stringify(lines));

        try {
            await fetchJson("/api/vouchers", {
                method: "POST",
                body: payload,
            });
            form.reset();
            updateSessionUi(); // re-populate presenter_email after reset
            qs("voucher-lines").innerHTML = "";
            qs("voucher-lines").appendChild(makeVoucherLineRow());
            await loadPendingVouchers();
            toast("Comprobante enviado a aprobación");
        } catch (error) {
            console.error("[submit-voucher error]", error);
            toast(error.message, true);
        }
    });
}

async function bootstrap() {
    setupThemeToggle();
    setupSidebarToggle();
    const today = new Date().toISOString().slice(0, 10);
    [
        ...document.querySelectorAll('#entry-form input[type="date"]'),
        ...document.querySelectorAll('#open-deposit-form input[type="date"]'),
        ...document.querySelectorAll('#rescue-deposit-form input[type="date"]'),
        ...document.querySelectorAll('#voucher-form input[type="date"]'),
    ].forEach((el) => {
        if (!el.value) el.value = today;
    });

    setupLoginModal();
    await loadSession();
    await loadAvailablePeriods();

    setupMenu();
    setupForms();
    setupEditEntryModal();
    setupChangePasswordModal();
    setupReportsModal();
    setupBankStatementsForm();
    setupTreasuryLibraryForm();
    setupPeriodFilters();
    setupMoneyMasks(document);
    qs("voucher-lines").appendChild(makeVoucherLineRow());

    qs("logout-btn").addEventListener("click", async () => {
        try {
            await logout();
        } catch (error) {
            toast(error.message, true);
        }
    });
    qs("switch-user-btn").addEventListener("click", async () => {
        try {
            await switchUser();
        } catch (error) {
            toast(error.message, true);
        }
    });

    await loadAccounts();
    await refreshAllVisibleData();
}

bootstrap().catch((error) => {
    toast(error.message, true);
});
