  // ---------------------------------------------------------------------------
  // Idioma: qué textos toca y cómo se rellenan
  // ---------------------------------------------------------------------------
  /** "pt-BR" → "pt"; un idioma prestado → el que le presta; uno sin traducir → el base. */
  const textLanguage = (language) => {
    const base = String(language || BASE_LANGUAGE).toLowerCase().split("-")[0];
    const resolved = BORROWED_LANGUAGES[base] || base;
    return TEXTS[resolved] ? resolved : BASE_LANGUAGE;
  };

  /** Texto de una clave en el idioma pedido. */
  const translate = (language, key, values) => {
    const table = TEXTS[textLanguage(language)];
    let text = key in table ? table[key] : key;
    for (const [name, value] of Object.entries(values || {})) text = text.split(`{${name}}`).join(String(value));
    return text;
  };

  const escapeHtml = (text) =>
    String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
