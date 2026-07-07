(function () {
  const storageKey = "oci-networking-workbook-theme";
  const themeButton = document.querySelector(".theme-toggle");
  const backTop = document.querySelector(".back-top");

  function preferredTheme() {
    const saved = localStorage.getItem(storageKey);
    if (saved === "light" || saved === "dark") {
      return saved;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(theme) {
    document.body.dataset.theme = theme;
    if (themeButton) {
      const isDark = theme === "dark";
      themeButton.textContent = isDark ? "Light mode" : "Dark mode";
      themeButton.setAttribute("aria-pressed", String(isDark));
    }
  }

  applyTheme(preferredTheme());

  themeButton?.addEventListener("click", () => {
    const next = document.body.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem(storageKey, next);
    applyTheme(next);
  });

  document.querySelectorAll(".code-toggle-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const card = button.closest(".code-card");
      if (!card) {
        return;
      }
      const isCollapsed = card.dataset.collapsed !== "false";
      card.dataset.collapsed = isCollapsed ? "false" : "true";
      button.setAttribute("aria-expanded", String(isCollapsed));
      button.textContent = isCollapsed ? "Collapse" : "Expand";
    });
  });

  document.querySelectorAll(".copy-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const card = button.closest(".code-card");
      const code = card?.querySelector("pre code");
      if (!code) {
        return;
      }
      const text = code.textContent;
      try {
        await navigator.clipboard.writeText(text);
        button.textContent = "Copied";
      } catch (error) {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.top = "-1000px";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        textarea.remove();
        button.textContent = "Copied";
      }
      window.setTimeout(() => {
        button.textContent = "Copy";
      }, 1800);
    });
  });

  function safeFileName(value) {
    return value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 96) || "exascale-deployment-readiness-record";
  }

  function normalizeCellText(cell) {
    return cell.innerText.replace(/\s+/g, " ").trim();
  }

  function fixedWidthTable(table) {
    const rows = Array.from(table.querySelectorAll("tr"))
      .map((row) => Array.from(row.children).map(normalizeCellText))
      .filter((row) => row.length > 0);
    if (!rows.length) {
      return "";
    }
    const columnCount = Math.max(...rows.map((row) => row.length));
    const normalizedRows = rows.map((row) => {
      const next = row.slice();
      while (next.length < columnCount) {
        next.push("");
      }
      return next;
    });
    const widths = Array.from({ length: columnCount }, (_, index) =>
      Math.max(...normalizedRows.map((row) => row[index].length), 3)
    );
    const formatRow = (row) =>
      row.map((cell, index) => cell.padEnd(widths[index], " ")).join("  ").trimEnd();
    const header = normalizedRows[0].map((cell) => cell.toUpperCase());
    const separator = widths.map((width) => "-".repeat(width)).join("  ");
    const body = normalizedRows.slice(1);
    return [formatRow(header), separator, ...body.map(formatRow)].join("\n");
  }

  function savedSectionText(section) {
    const title = section.querySelector("h2")?.textContent?.trim() || "Deployment Readiness Record";
    const tables = Array.from(section.querySelectorAll("table"));
    if (!tables.length) {
      return title.toUpperCase();
    }
    const tableText = tables.map(fixedWidthTable).filter(Boolean).join("\n\n");
    return `${title.toUpperCase()}\n\n${tableText}`.trim();
  }

  document.querySelectorAll(".save-section-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const section = button.closest(".saveable-section");
      if (!section) {
        return;
      }
      const title = section.dataset.saveTitle || section.querySelector("h2")?.textContent || "Deployment readiness record";
      const fileName = section.dataset.saveFile || `${safeFileName(title)}.txt`;
      const text = savedSectionText(section);
      const blob = new Blob([text + "\n"], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = fileName.endsWith(".txt") ? fileName : `${fileName}.txt`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      button.textContent = "Saved";
      window.setTimeout(() => {
        button.textContent = "Save .txt";
      }, 1800);
    });
  });

  function updateBackTop() {
    if (!backTop) {
      return;
    }
    backTop.classList.toggle("is-visible", window.scrollY > 520);
  }

  backTop?.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  window.addEventListener("scroll", updateBackTop, { passive: true });
  updateBackTop();
})();
