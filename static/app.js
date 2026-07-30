const taskForm     = document.getElementById("taskForm");
const taskList     = document.getElementById("taskList");
const taskTemplate = document.getElementById("taskTemplate");
const taskCounter  = document.getElementById("taskCounter");
const formError    = document.getElementById("formError");
const filterTabs   = document.querySelectorAll(".filter-tab");

let currentFilter = "all";

// ── helpers ──────────────────────────────────────────────────────────────────

const STATUS_LABELS  = { pending: "Pending", in_progress: "In Progress", done: "Done" };
const STATUS_CLASSES = { pending: "badge-pending", in_progress: "badge-inprogress", done: "badge-done" };

const formatDate = (raw) => {
    if (!raw) return "-";
    const date = new Date(`${raw}T00:00:00`);
    if (Number.isNaN(date.getTime())) return "No schedule";
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
};

const getDaysLeft = (endDate, status) => {
    if (!endDate) return "-";
    if (status === "done") return "0";

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const end = new Date(`${endDate}T00:00:00`);
    if (Number.isNaN(end.getTime())) return "-";

    const diff = Math.ceil((end.getTime() - today.getTime()) / 86400000);
    if (diff < 0) return `-${Math.abs(diff)}`;
    return String(diff);
};

const updateCounter = () => {
    const count = taskList.children.length;
    taskCounter.textContent = `${count} task${count === 1 ? "" : "s"}`;
};

// ── render one task card ──────────────────────────────────────────────────────

const renderTask = (task) => {
    const node = taskTemplate.content.firstElementChild.cloneNode(true);
    node.dataset.id     = String(task.id);
    node.dataset.status = task.status;
    node.classList.toggle("compact-actions", currentFilter !== "all");

    const noteEl         = node.querySelector(".task-note");
    const badge          = node.querySelector(".status-badge");
    const meta           = node.querySelector(".task-meta");
    const titleEl        = node.querySelector(".task-title");
    const daysValueEl    = node.querySelector(".task-days-value");
    const daysBoxEl      = node.querySelector(".task-days");
    const editFields     = node.querySelector(".edit-fields");
    const editNoteInp    = node.querySelector(".edit-note");

    const btnPending    = node.querySelector(".btn-pending");
    const btnInProgress = node.querySelector(".btn-inprogress");
    const btnDone       = node.querySelector(".btn-done");
    const btnEdit       = node.querySelector(".btn-edit");
    const btnDelete     = node.querySelector(".btn-delete");

    // apply status badge + highlight active status button
    const applyStatus = (status) => {
        node.dataset.status    = status;
        badge.textContent      = STATUS_LABELS[status] ?? status;
        badge.className        = "status-badge " + (STATUS_CLASSES[status] ?? "");
        btnPending.classList.toggle("active-status",    status === "pending");
        btnInProgress.classList.toggle("active-status", status === "in_progress");
        btnDone.classList.toggle("active-status",       status === "done");
    };

    noteEl.textContent   = task.note ?? task.message ?? "";
    titleEl.textContent  = task.task_name ?? task.title ?? "Task";
    meta.textContent     = `Schedule: ${formatDate(task.start_date)} -> ${formatDate(task.end_date)}`;
    daysValueEl.textContent = getDaysLeft(task.end_date, task.status);
    daysBoxEl.hidden = currentFilter !== "all";
    applyStatus(task.status);

    // ── status change ─────────────────────────────────────────────────────────
    const changeStatus = async (newStatus) => {
        formError.textContent = "";
        try {
            const res = await fetch(`/api/tasks/${task.id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status: newStatus }),
            });
            if (!res.ok) throw new Error("Failed to update status.");
            const updated = await res.json();
            task.status = updated.status;
            applyStatus(updated.status);
            daysValueEl.textContent = getDaysLeft(task.end_date, updated.status);
            // remove from list when it no longer matches active filter
            if (currentFilter !== "all" && updated.status !== currentFilter) {
                node.remove();
                updateCounter();
            }
        } catch (e) {
            formError.textContent = e.message;
        }
    };

    btnPending.addEventListener("click",    () => changeStatus("pending"));
    btnInProgress.addEventListener("click", () => changeStatus("in_progress"));
    btnDone.addEventListener("click",       () => changeStatus("done"));

    // ── inline edit ───────────────────────────────────────────────────────────
    btnEdit.addEventListener("click", () => {
        editNoteInp.value = noteEl.textContent;
        editNoteInp.dataset.original = noteEl.textContent;
        noteEl.hidden = true;
        editFields.hidden = false;
        editNoteInp.focus();
        editNoteInp.select();
    });

    const closeEdit = () => {
        editFields.hidden = true;
        noteEl.hidden = false;
    };

    const saveEdit = async () => {
        const newNote = editNoteInp.value.trim();
        if (!newNote) {
            formError.textContent = "Note cannot be empty.";
            return;
        }
        if (newNote === (editNoteInp.dataset.original ?? "")) {
            closeEdit();
            return;
        }
        formError.textContent = "";
        try {
            const res = await fetch(`/api/tasks/${task.id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ details: newNote }),
            });
            if (!res.ok) throw new Error("Failed to save changes.");
            const updated      = await res.json();
            noteEl.textContent = updated.details ?? updated.message ?? "";
            task.note = updated.details ?? updated.message ?? "";
            closeEdit();
        } catch (e) {
            formError.textContent = e.message;
        }
    };

    editNoteInp.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
            event.preventDefault();
            void saveEdit();
        }
        if (event.key === "Escape") {
            editNoteInp.value = editNoteInp.dataset.original ?? "";
            closeEdit();
        }
    });

    editNoteInp.addEventListener("blur", () => {
        if (!editFields.hidden) {
            void saveEdit();
        }
    });

    // ── delete ────────────────────────────────────────────────────────────────
    btnDelete.addEventListener("click", async () => {
        formError.textContent = "";
        try {
            const res = await fetch(`/api/tasks/${task.id}`, { method: "DELETE" });
            if (!res.ok) throw new Error("Failed to delete task.");
            node.remove();
            updateCounter();
        } catch (e) {
            formError.textContent = e.message;
        }
    });

    taskList.appendChild(node);
};

// ── load tasks (with optional status filter) ──────────────────────────────────

const loadTasks = async (filter = "all") => {
    formError.textContent = "";
    const url = filter === "all" ? "/api/tasks" : `/api/tasks?status=${filter}`;
    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error("Could not load tasks.");
        const tasks = await res.json();
        taskList.innerHTML = "";
        tasks.forEach(renderTask);
        updateCounter();
    } catch (e) {
        formError.textContent = e.message;
    }
};

// ── filter tabs ───────────────────────────────────────────────────────────────

filterTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
        filterTabs.forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        currentFilter = tab.dataset.filter;
        loadTasks(currentFilter);
    });
});

// ── create task ───────────────────────────────────────────────────────────────

taskForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.textContent = "";
    const formData = new FormData(taskForm);
    const payload = {
        task_name: formData.get("task_name")?.toString().trim() ?? "",
        details: formData.get("details")?.toString().trim() ?? "",
        start_date: formData.get("start_date")?.toString() ?? "",
        end_date: formData.get("end_date")?.toString() ?? "",
    };
    try {
        const res = await fetch("/api/tasks", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify(payload),
        });
        if (!res.ok) {
            let body = {};
            try { body = await res.json(); } catch (_) { body = {}; }
            throw new Error(body.error || "Failed to create task.");
        }
        const newTask = await res.json();
        // add to list only if active filter matches the new task's status
        if (currentFilter === "all" || currentFilter === newTask.status) {
            renderTask(newTask);
            updateCounter();
        }
        taskForm.reset();
    } catch (e) {
        formError.textContent = e.message;
    }
});

// ── boot ──────────────────────────────────────────────────────────────────────
loadTasks();
