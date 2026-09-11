const state = {
  user: null,
  tab: null,
  trainerSectionId: null,
  sessionId: null,
};

const view = document.getElementById("view");
const tabsEl = document.getElementById("tabs");
const roleBadge = document.getElementById("role-badge");

const ROLE_LABEL = { student: "Студент", trainer: "Тренер", admin: "Администратор" };
const WEEKDAY_LABEL = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str == null ? "" : String(str);
  return div.innerHTML;
}

function showToast(message) {
  const tpl = document.getElementById("tpl-toast");
  const node = tpl.content.firstElementChild.cloneNode(true);
  node.textContent = message;
  document.body.appendChild(node);
  setTimeout(() => node.remove(), 2500);
}

function applyTelegramTheme() {
  const tg = window.Telegram && Telegram.WebApp;
  if (!tg) return;
  tg.ready();
  tg.expand();
  const p = tg.themeParams || {};
  const root = document.documentElement.style;
  if (p.bg_color) root.setProperty("--tg-bg", p.bg_color);
  if (p.text_color) root.setProperty("--tg-text", p.text_color);
  if (p.hint_color) root.setProperty("--tg-hint", p.hint_color);
  if (p.link_color) root.setProperty("--tg-link", p.link_color);
  if (p.button_color) root.setProperty("--tg-button", p.button_color);
  if (p.button_text_color) root.setProperty("--tg-button-text", p.button_text_color);
  if (p.secondary_bg_color) root.setProperty("--tg-secondary-bg", p.secondary_bg_color);
}

const TABS = [
  { id: "sections", label: "Секции", roles: ["student"], render: renderStudentSections },
  { id: "profile", label: "Профиль", roles: ["student"], render: renderStudentProfile },
  { id: "trainer_sections", label: "Мои секции", roles: ["trainer"], render: renderTrainerSections },
  { id: "admin_sections", label: "Секции", roles: ["admin"], render: renderAdminSections },
  { id: "admin_users", label: "Пользователи", roles: ["admin"], render: renderAdminUsers },
  { id: "news", label: "Новости", roles: ["student", "trainer", "admin"], render: renderNews },
];

function tabsForRole(role) {
  return TABS.filter((t) => t.roles.includes(role));
}

function renderTabs() {
  const tabs = tabsForRole(state.user.role);
  tabsEl.innerHTML = tabs
    .map((t) => `<button class="tab${t.id === state.tab ? " active" : ""}" data-tab="${t.id}">${t.label}</button>`)
    .join("");
  tabsEl.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => selectTab(btn.dataset.tab));
  });
}

function selectTab(tabId) {
  state.tab = tabId;
  state.trainerSectionId = null;
  state.sessionId = null;
  renderTabs();
  const tab = TABS.find((t) => t.id === tabId);
  if (tab) tab.render();
}

async function boot() {
  applyTelegramTheme();
  try {
    state.user = await Api.get("/api/me");
  } catch (e) {
    view.innerHTML = `<div class="empty">Не удалось авторизоваться: ${escapeHtml(e.message)}<br>Откройте приложение через кнопку в Telegram-боте.</div>`;
    return;
  }
  roleBadge.textContent = ROLE_LABEL[state.user.role] || state.user.role;
  const first = tabsForRole(state.user.role)[0];
  selectTab(first.id);
}

/* ---------------- СТУДЕНТ ---------------- */

async function renderStudentSections() {
  view.innerHTML = `<div class="empty">Загрузка…</div>`;
  const sections = await Api.get("/api/sections");
  if (!sections.length) {
    view.innerHTML = `<div class="empty">Секций пока нет</div>`;
    return;
  }
  view.innerHTML = sections
    .map((s) => {
      const full = s.taken >= s.capacity && !s.enrolled;
      const schedule = s.schedule
        .map((sl) => `${WEEKDAY_LABEL[sl.weekday]} ${sl.start_time.slice(0, 5)}–${sl.end_time.slice(0, 5)}${sl.location ? " · " + escapeHtml(sl.location) : ""}`)
        .join("<br>");
      return `
        <div class="card">
          <h3>${escapeHtml(s.name)}</h3>
          <p>${escapeHtml(s.description || "")}</p>
          <p class="muted">Тренер: ${escapeHtml(s.trainer_name || "не назначен")}</p>
          ${schedule ? `<p class="muted">${schedule}</p>` : ""}
          <div class="row">
            <span class="muted">Мест занято: ${s.taken} / ${s.capacity}</span>
            ${
              s.enrolled
                ? `<button class="btn secondary" data-action="cancel" data-id="${s.id}">Отменить запись</button>`
                : `<button class="btn" data-action="enroll" data-id="${s.id}" ${full ? "disabled" : ""}>${full ? "Нет мест" : "Записаться"}</button>`
            }
          </div>
        </div>`;
    })
    .join("");

  view.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.id;
      try {
        if (btn.dataset.action === "enroll") {
          await Api.post(`/api/sections/${id}/enroll`);
          showToast("Вы записаны");
        } else {
          await Api.del(`/api/sections/${id}/enroll`);
          showToast("Запись отменена");
        }
        renderStudentSections();
      } catch (e) {
        showToast(e.message);
      }
    });
  });
}

async function renderStudentProfile() {
  view.innerHTML = `<div class="empty">Загрузка…</div>`;
  const [enrollments, attendance] = await Promise.all([
    Api.get("/api/my/enrollments"),
    Api.get("/api/my/attendance"),
  ]);

  const enrollmentsHtml = enrollments.length
    ? enrollments.map((e) => `<div class="student-row"><span>${escapeHtml(e.name)}</span></div>`).join("")
    : `<p class="muted">Нет активных записей</p>`;

  const attendanceHtml = attendance.length
    ? attendance
        .map(
          (a) =>
            `<div class="student-row"><span>${a.session_date} · ${escapeHtml(a.section_name)}</span><span class="pill ${a.status}">${a.status}</span></div>`
        )
        .join("")
    : `<p class="muted">Пока нет отметок посещаемости</p>`;

  view.innerHTML = `
    <div class="card"><h3>${escapeHtml(state.user.full_name)}</h3><p class="muted">${ROLE_LABEL[state.user.role]}</p></div>
    <div class="section-header"><h3>Мои записи</h3></div>
    ${enrollmentsHtml}
    <div class="section-header" style="margin-top:16px"><h3>Посещаемость</h3></div>
    ${attendanceHtml}
  `;
}

/* ---------------- ТРЕНЕР ---------------- */

async function renderTrainerSections() {
  if (state.sessionId) return renderTrainerAttendance();
  if (state.trainerSectionId) return renderTrainerSectionDetail();

  view.innerHTML = `<div class="empty">Загрузка…</div>`;
  const sections = await Api.get("/api/trainer/sections");
  view.innerHTML = `
    ${
      sections.length
        ? sections
            .map(
              (s) => `
      <div class="card">
        <h3>${escapeHtml(s.name)}</h3>
        <p class="muted">Занято: ${s.taken} / ${s.capacity}</p>
        <button class="btn small" data-id="${s.id}">Управлять</button>
      </div>`
            )
            .join("")
        : `<div class="empty">У вас пока нет секций. Обратитесь к администратору.</div>`
    }
  `;
  view.querySelectorAll("[data-id]").forEach((btn) =>
    btn.addEventListener("click", () => {
      state.trainerSectionId = Number(btn.dataset.id);
      renderTrainerSections();
    })
  );
}

async function renderTrainerSectionDetail() {
  view.innerHTML = `<div class="empty">Загрузка…</div>`;
  const sectionId = state.trainerSectionId;
  const [scheduleList, sessionList, studentList] = await Promise.all([
    fetchScheduleFor(sectionId),
    Api.get(`/api/trainer/sections/${sectionId}/sessions`),
    Api.get(`/api/trainer/sections/${sectionId}/students`),
  ]);

  const upcoming = sessionList.filter((s) => s.status === "scheduled");

  view.innerHTML = `
    <button class="btn secondary small" id="back">← К списку секций</button>

    <div class="section-header" style="margin-top:12px"><h3>Расписание</h3></div>
    ${
      scheduleList.length
        ? scheduleList
            .map(
              (sl) => `
      <div class="student-row">
        <span>${WEEKDAY_LABEL[sl.weekday]} ${sl.start_time.slice(0, 5)}–${sl.end_time.slice(0, 5)} ${sl.location ? "· " + escapeHtml(sl.location) : ""}</span>
        <button class="btn small danger" data-del-slot="${sl.id}">Удалить</button>
      </div>`
            )
            .join("")
        : `<p class="muted">Слоты не добавлены</p>`
    }
    <form id="slot-form" style="margin-top:8px">
      <label>День недели</label>
      <select name="weekday">${WEEKDAY_LABEL.map((w, i) => `<option value="${i}">${w}</option>`).join("")}</select>
      <label>Начало</label>
      <input name="start_time" type="time" required>
      <label>Окончание</label>
      <input name="end_time" type="time" required>
      <label>Место</label>
      <input name="location" type="text" placeholder="Зал / корпус">
      <button class="btn" type="submit">Добавить слот</button>
    </form>

    <div class="section-header" style="margin-top:16px">
      <h3>Занятия</h3>
      <button class="btn small secondary" id="generate">Сгенерировать на 4 недели</button>
    </div>
    ${
      upcoming.length
        ? upcoming
            .map(
              (s) => `
      <div class="student-row">
        <span>${s.session_date} ${s.start_time.slice(0, 5)}–${s.end_time.slice(0, 5)}</span>
        <span>
          <button class="btn small" data-open-session="${s.id}">Посещаемость</button>
          <button class="btn small danger" data-cancel-session="${s.id}">Отменить</button>
        </span>
      </div>`
            )
            .join("")
        : `<p class="muted">Нет запланированных занятий</p>`
    }

    <div class="section-header" style="margin-top:16px"><h3>Записанные студенты (${studentList.length})</h3></div>
    ${
      studentList.length
        ? studentList.map((s) => `<div class="student-row"><span>${escapeHtml(s.full_name)}</span><span class="muted">${s.username ? "@" + escapeHtml(s.username) : ""}</span></div>`).join("")
        : `<p class="muted">Пока никто не записался</p>`
    }
  `;

  document.getElementById("back").addEventListener("click", () => {
    state.trainerSectionId = null;
    renderTrainerSections();
  });

  document.getElementById("slot-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await Api.post(`/api/trainer/sections/${sectionId}/schedule`, {
        weekday: Number(fd.get("weekday")),
        start_time: fd.get("start_time"),
        end_time: fd.get("end_time"),
        location: fd.get("location") || "",
      });
      showToast("Слот добавлен");
      renderTrainerSectionDetail();
    } catch (err) {
      showToast(err.message);
    }
  });

  view.querySelectorAll("[data-del-slot]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      try {
        await Api.del(`/api/trainer/schedule/${btn.dataset.delSlot}`);
        renderTrainerSectionDetail();
      } catch (err) {
        showToast(err.message);
      }
    })
  );

  document.getElementById("generate").addEventListener("click", async () => {
    try {
      const res = await Api.post(`/api/trainer/sections/${sectionId}/sessions/generate`, { weeks: 4 });
      showToast(`Создано занятий: ${res.created}`);
      renderTrainerSectionDetail();
    } catch (err) {
      showToast(err.message);
    }
  });

  view.querySelectorAll("[data-open-session]").forEach((btn) =>
    btn.addEventListener("click", () => {
      state.sessionId = Number(btn.dataset.openSession);
      renderTrainerSections();
    })
  );

  view.querySelectorAll("[data-cancel-session]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      try {
        await Api.del(`/api/trainer/sessions/${btn.dataset.cancelSession}`);
        renderTrainerSectionDetail();
      } catch (err) {
        showToast(err.message);
      }
    })
  );
}

async function fetchScheduleFor(sectionId) {
  const sections = await Api.get("/api/sections");
  const section = sections.find((s) => s.id === sectionId);
  return section ? section.schedule : [];
}

async function renderTrainerAttendance() {
  view.innerHTML = `<div class="empty">Загрузка…</div>`;
  const sessionId = state.sessionId;
  const data = await Api.get(`/api/trainer/sessions/${sessionId}/attendance`);

  view.innerHTML = `
    <button class="btn secondary small" id="back">← К секции</button>
    <div class="section-header" style="margin-top:12px">
      <h3>Занятие ${data.session.session_date} ${data.session.start_time.slice(0, 5)}</h3>
    </div>
    ${
      data.students.length
        ? data.students
            .map(
              (s) => `
      <div class="student-row">
        <span>${escapeHtml(s.full_name)}</span>
        <span>
          <button class="btn small ${s.status === "present" ? "" : "secondary"}" data-mark="${s.student_id}" data-status="present">Был</button>
          <button class="btn small ${s.status === "absent" ? "danger" : "secondary"}" data-mark="${s.student_id}" data-status="absent">Не был</button>
        </span>
      </div>`
            )
            .join("")
        : `<p class="muted">На секции нет записанных студентов</p>`
    }
  `;

  document.getElementById("back").addEventListener("click", () => {
    state.sessionId = null;
    renderTrainerSections();
  });

  view.querySelectorAll("[data-mark]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      try {
        await Api.post(`/api/trainer/sessions/${sessionId}/attendance`, {
          marks: { [btn.dataset.mark]: btn.dataset.status },
        });
        renderTrainerAttendance();
      } catch (err) {
        showToast(err.message);
      }
    })
  );
}

/* ---------------- АДМИН ---------------- */

async function renderAdminSections() {
  view.innerHTML = `<div class="empty">Загрузка…</div>`;
  const [sections, trainers] = await Promise.all([
    Api.get("/api/admin/sections"),
    Api.get("/api/admin/users?role=trainer"),
  ]);

  const trainerOptions = (selectedId) =>
    `<option value="">— не назначен —</option>` +
    trainers.map((t) => `<option value="${t.id}" ${t.id === selectedId ? "selected" : ""}>${escapeHtml(t.full_name)}</option>`).join("");

  view.innerHTML = `
    <form id="create-form" class="card">
      <h3>Новая секция</h3>
      <label>Название</label>
      <input name="name" required>
      <label>Описание</label>
      <textarea name="description" rows="2"></textarea>
      <label>Вместимость</label>
      <input name="capacity" type="number" min="1" required>
      <label>Тренер</label>
      <select name="trainer_id">${trainerOptions(null)}</select>
      <button class="btn" type="submit">Создать</button>
    </form>

    ${sections
      .map(
        (s) => `
      <div class="card">
        <div class="section-header">
          <h3>${escapeHtml(s.name)}</h3>
          <button class="btn small danger" data-del="${s.id}">Удалить</button>
        </div>
        <p class="muted">Занято: ${s.taken} / ${s.capacity} · Тренер: ${escapeHtml(s.trainer_name || "—")}</p>
        <form data-edit="${s.id}">
          <label>Название</label>
          <input name="name" value="${escapeHtml(s.name)}" required>
          <label>Описание</label>
          <textarea name="description" rows="2">${escapeHtml(s.description || "")}</textarea>
          <label>Вместимость</label>
          <input name="capacity" type="number" min="1" value="${s.capacity}" required>
          <label>Тренер</label>
          <select name="trainer_id">${trainerOptions(s.trainer_id)}</select>
          <button class="btn small secondary" type="submit">Сохранить</button>
        </form>
      </div>`
      )
      .join("")}
  `;

  document.getElementById("create-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await Api.post("/api/admin/sections", {
        name: fd.get("name"),
        description: fd.get("description") || "",
        capacity: Number(fd.get("capacity")),
        trainer_id: fd.get("trainer_id") ? Number(fd.get("trainer_id")) : null,
      });
      showToast("Секция создана");
      renderAdminSections();
    } catch (err) {
      showToast(err.message);
    }
  });

  view.querySelectorAll("[data-edit]").forEach((form) =>
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        await Api.put(`/api/admin/sections/${form.dataset.edit}`, {
          name: fd.get("name"),
          description: fd.get("description") || "",
          capacity: Number(fd.get("capacity")),
          trainer_id: fd.get("trainer_id") ? Number(fd.get("trainer_id")) : null,
        });
        showToast("Сохранено");
        renderAdminSections();
      } catch (err) {
        showToast(err.message);
      }
    })
  );

  view.querySelectorAll("[data-del]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      try {
        await Api.del(`/api/admin/sections/${btn.dataset.del}`);
        renderAdminSections();
      } catch (err) {
        showToast(err.message);
      }
    })
  );
}

async function renderAdminUsers() {
  view.innerHTML = `<div class="empty">Загрузка…</div>`;
  const users = await Api.get("/api/admin/users");

  view.innerHTML = users
    .map(
      (u) => `
    <div class="card">
      <div class="row">
        <div>
          <h3 style="margin:0">${escapeHtml(u.full_name)}</h3>
          <p class="muted" style="margin:2px 0 0">${u.username ? "@" + escapeHtml(u.username) : "id " + u.tg_id}</p>
        </div>
        <select data-role="${u.id}">
          <option value="student" ${u.role === "student" ? "selected" : ""}>Студент</option>
          <option value="trainer" ${u.role === "trainer" ? "selected" : ""}>Тренер</option>
          <option value="admin" ${u.role === "admin" ? "selected" : ""}>Администратор</option>
        </select>
      </div>
    </div>`
    )
    .join("");

  view.querySelectorAll("[data-role]").forEach((sel) =>
    sel.addEventListener("change", async () => {
      try {
        await Api.post(`/api/admin/users/${sel.dataset.role}/role`, { role: sel.value });
        showToast("Роль обновлена");
      } catch (err) {
        showToast(err.message);
        renderAdminUsers();
      }
    })
  );
}

/* ---------------- НОВОСТИ ---------------- */

async function renderNews() {
  view.innerHTML = `<div class="empty">Загрузка…</div>`;
  const news = await Api.get("/api/news");
  const canPost = state.user.role === "trainer" || state.user.role === "admin";

  view.innerHTML = `
    ${
      canPost
        ? `
      <form id="news-form" class="card">
        <h3>Опубликовать новость</h3>
        <label>Заголовок</label>
        <input name="title" required>
        <label>Текст</label>
        <textarea name="content" rows="3" required></textarea>
        <button class="btn" type="submit">Опубликовать</button>
      </form>`
        : ""
    }
    ${
      news.length
        ? news
            .map((n) => {
              const canDelete = state.user.role === "admin" || n.author_id === state.user.id;
              return `
      <div class="card">
        <div class="section-header">
          <h3 style="margin:0">${escapeHtml(n.title)}</h3>
          ${canDelete ? `<button class="btn small danger" data-del-news="${n.id}">Удалить</button>` : ""}
        </div>
        <p>${escapeHtml(n.content)}</p>
        <p class="muted">${escapeHtml(n.author_name || "")} · ${new Date(n.created_at).toLocaleDateString("ru-RU")}</p>
      </div>`;
            })
            .join("")
        : `<div class="empty">Новостей пока нет</div>`
    }
  `;

  const form = document.getElementById("news-form");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        await Api.post("/api/news", { title: fd.get("title"), content: fd.get("content") });
        showToast("Опубликовано");
        renderNews();
      } catch (err) {
        showToast(err.message);
      }
    });
  }

  view.querySelectorAll("[data-del-news]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      try {
        await Api.del(`/api/news/${btn.dataset.delNews}`);
        renderNews();
      } catch (err) {
        showToast(err.message);
      }
    })
  );
}

boot();
