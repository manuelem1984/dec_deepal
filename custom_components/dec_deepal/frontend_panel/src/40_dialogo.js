  // ---------------------------------------------------------------------------
  // Ventana emergente mínima (se cuelga de <body> para quedar por encima)
  // ---------------------------------------------------------------------------
  function openDialog(html, onAction) {
    const host = document.createElement("div");
    const root = host.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${DIALOG_CSS}</style><div class="dlg" role="dialog" aria-modal="true">${html}</div>`;
    const close = () => {
      document.removeEventListener("keydown", onKey);
      host.remove();
    };
    const onKey = (event) => event.key === "Escape" && close();
    document.addEventListener("keydown", onKey);
    host.addEventListener("click", (event) => {
      const path = event.composedPath();
      if (path[0] === host) return close(); // toque en el fondo oscuro
      const target = path.find((node) => node.dataset && node.dataset.action);
      if (!target) return undefined;
      if (target.dataset.action === "close") return close();
      return onAction(target.dataset.action, dialog, target);
    });
    const dialog = {
      root,
      close,
      /** Valores del formulario: `{ nombre: valor }` (casillas → true/false). */
      values() {
        const values = {};
        for (const field of root.querySelectorAll("[name]")) {
          values[field.name] = field.type === "checkbox" ? field.checked : field.value;
        }
        return values;
      },
      error(text) {
        const box = root.querySelector(".err");
        if (box) box.textContent = text || "";
      },
    };
    document.body.append(host);
    return dialog;
  }
