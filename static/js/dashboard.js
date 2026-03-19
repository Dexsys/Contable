const state = {
    accounts: [],
    summary: null,
    auth: null,
    roles: [],
    periods: { years: [], months_by_year: {}, latest: null },
};

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

function qs(id) {
    return document.getElementById(id);
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
    const entered = window.prompt("Ingresa tu correo para iniciar sesión", cached);
    if (!entered) {
        throw new Error("Debes iniciar sesión para usar el sistema");
    }
    const password = window.prompt("Contraseña (deja vacío si no tienes)", "") || "";

    const login = await fetchJson("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: entered.trim(), password }),
    });
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

    const login = await fetchJson("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: entered.trim() }),
    });

    state.auth = login.user;
    state.roles = login.roles || [];
    localStorage.setItem("contable_user_email", login.user.email);
    window.location.reload();
}

function applyKpis(totals) {
    qs("kpi-prev-balance").textContent = formatCurrency(totals.previous_balance);
    qs("kpi-credit").textContent = formatCurrency(totals.credit);
    qs("kpi-debit").textContent = formatCurrency(totals.debit);
    qs("kpi-period-balance").textContent = formatCurrency(totals.period_balance);
    qs("kpi-balance").textContent = formatCurrency(totals.accumulated_final_balance);
    qs("kpi-entries").textContent = totals.entries;
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
    header.innerHTML = `
        <span class="node-title">${node.code} | ${node.name || "(sin nombre)"}</span>
        <span class="badge">Nivel ${node.level}</span>
        <span class="amount out">Egreso ${formatCurrency(node.debit)}</span>
        <span class="amount in">Ingreso ${formatCurrency(node.credit)} | Saldo ${formatCurrency(node.balance)}</span>
    `;

    const content = document.createElement("div");
    content.className = "node-content";

    if (node.entries && node.entries.length > 0) {
        const detail = document.createElement("div");
        detail.className = "entries";
        node.entries.slice(0, 40).forEach((entry) => {
            const row = document.createElement("div");
            row.className = "entry-row";
            const attachment = entry.receipt_image_url
                ? `<a class="attachment" href="${entry.receipt_image_url}" target="_blank" rel="noopener">imagen</a>`
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
        const attachment = entry.receipt_image_url
            ? `<a class="attachment" href="${entry.receipt_image_url}" target="_blank" rel="noopener">Ver</a>`
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

            const entryDate = window.prompt("Fecha (YYYY-MM-DD)", entry.entry_date || "");
            if (entryDate === null) return;
            const description = window.prompt("Descripción", entry.description || "");
            if (description === null) return;
            const accountCode = window.prompt("Código cuenta", entry.account_code || "");
            if (accountCode === null) return;
            const accountName = window.prompt("Nombre cuenta", entry.account_name || "");
            if (accountName === null) return;
            const credit = window.prompt("Ingreso/Haber", String(entry.credit || 0));
            if (credit === null) return;
            const debit = window.prompt("Egreso/Debe", String(entry.debit || 0));
            if (debit === null) return;
            const reference = window.prompt("Referencia", entry.reference || "") ?? "";
            const note = window.prompt("Observación", entry.note || "") ?? "";

            try {
                await fetchJson(`/api/entries/${entryId}`, {
                    method: "PATCH",
                    body: JSON.stringify({
                        entry_date: entryDate,
                        description,
                        account_code: accountCode,
                        account_name: accountName,
                        credit,
                        debit,
                        reference,
                        note,
                    }),
                });
                await loadSummary();
                await loadRecent();
                toast("Movimiento actualizado");
            } catch (error) {
                toast(error.message, true);
            }
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

function setupMenu() {
    const buttons = Array.from(document.querySelectorAll(".menu-btn")).filter((btn) => !btn.hidden);
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
        btn.addEventListener("click", () => activate(btn.dataset.panel));
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
        const attachment = item.receipt_image_url
            ? `<a class="attachment" href="${item.receipt_image_url}" target="_blank" rel="noopener">Ver</a>`
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
            <input type="number" class="vl-debit" value="${defaults.debit || ""}" min="0" step="0.01">
        </label>
        <label>Haber
            <input type="number" class="vl-credit" value="${defaults.credit || ""}" min="0" step="0.01">
        </label>
        <button type="button" class="vl-remove">Quitar</button>
    `;

    row.querySelector(".vl-remove").addEventListener("click", () => row.remove());
    return row;
}

function collectVoucherLines() {
    const rows = Array.from(document.querySelectorAll("#voucher-lines .voucher-line"));
    return rows.map((row) => ({
        account_code: row.querySelector(".vl-account").value.trim(),
        description: row.querySelector(".vl-description").value.trim(),
        debit: row.querySelector(".vl-debit").value.trim() || "0",
        credit: row.querySelector(".vl-credit").value.trim() || "0",
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
                <select class="role-select" data-id="${item.id}">${options}</select>
                <button type="button" class="save-role-btn" data-id="${item.id}">Guardar</button>
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
}

async function refreshAllVisibleData() {
    await Promise.all([
        loadSummary(),
        loadRecent(),
        loadPendingVouchers(),
        loadUsers(),
        loadAuditLog(),
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
    const today = new Date().toISOString().slice(0, 10);
    [
        ...document.querySelectorAll('#entry-form input[type="date"]'),
        ...document.querySelectorAll('#open-deposit-form input[type="date"]'),
        ...document.querySelectorAll('#rescue-deposit-form input[type="date"]'),
        ...document.querySelectorAll('#voucher-form input[type="date"]'),
    ].forEach((el) => {
        if (!el.value) el.value = today;
    });

    await loadSession();
    await loadAvailablePeriods();

    setupMenu();
    setupForms();
    setupPeriodFilters();
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
