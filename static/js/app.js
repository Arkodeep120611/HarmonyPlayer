(() => {
  const HP = window.HarmonyPlayer = window.HarmonyPlayer || {};
  const config = HP.config || {};
  const storageKey = "harmonyplayer.theme";

  function setTheme(theme) {
    const nextTheme = theme === "light" ? "light" : "dark";
    document.documentElement.dataset.theme = nextTheme;
    localStorage.setItem(storageKey, nextTheme);
    if (HP.player && typeof HP.player.updateTheme === "function") {
      HP.player.updateTheme(nextTheme);
    }
  }

  async function apiFetch(url, options = {}) {
    const opts = { ...options };
    const headers = new Headers(opts.headers || {});
    const method = (opts.method || "GET").toUpperCase();
    if (method !== "GET" && method !== "HEAD") {
      headers.set("X-CSRFToken", config.csrfToken || "");
    }
    if (opts.json) {
      headers.set("Content-Type", "application/json");
      opts.body = JSON.stringify(opts.json);
      delete opts.json;
    }
    opts.headers = headers;
    return fetch(url, opts);
  }

  function formatTime(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return "00:00";
    const total = Math.floor(seconds);
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const remaining = total % 60;
    if (hours > 0) {
      return `${hours}:${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
    }
    return `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
  }

  function initTheme() {
    const storedTheme = localStorage.getItem(storageKey);
    const initialTheme = storedTheme || config.settings?.theme || "dark";
    setTheme(initialTheme);
  }

  function initSidebar() {
    const toggle = document.querySelector("[data-sidebar-toggle]");
    const overlay = document.getElementById("sidebarOverlay");
    if (toggle) {
      toggle.addEventListener("click", () => document.body.classList.toggle("sidebar-open"));
    }
    if (overlay) {
      overlay.addEventListener("click", () => document.body.classList.remove("sidebar-open"));
    }
  }

  function initThemeToggle() {
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        const nextTheme = document.documentElement.dataset.theme === "light" ? "dark" : "light";
        setTheme(nextTheme);
      });
    });
  }

  function initFlashDismiss() {
    document.querySelectorAll(".flash-dismiss").forEach((button) => {
      button.addEventListener("click", () => button.closest(".flash")?.remove());
    });
  }

  HP.setTheme = setTheme;
  HP.apiFetch = apiFetch;
  HP.formatTime = formatTime;

  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initSidebar();
    initThemeToggle();
    initFlashDismiss();
  });
})();
