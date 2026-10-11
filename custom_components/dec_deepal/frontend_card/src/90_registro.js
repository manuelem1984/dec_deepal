  // ---------------------------------------------------------------------------
  // Alta de la tarjeta en Home Assistant
  // ---------------------------------------------------------------------------
  customElements.define(TAG, DecDeepalCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: TAG,
    name: "DEC Deepal",
    description: translate(document.documentElement.lang || navigator.language, "card_description"),
    preview: true,
    documentationURL: "https://github.com/manuelem1984/dec_deepal",
  });
