  // ---------------------------------------------------------------------------
  // Alta de la tarjeta en Home Assistant
  // ---------------------------------------------------------------------------
  /** La misma tarjeta, con el coche visto desde arriba. */
  class DecDeepalTopCard extends DecDeepalCard {
    static get VIEW() {
      return "top";
    }
  }

  customElements.define(TAG, DecDeepalCard);
  customElements.define(TOP_TAG, DecDeepalTopCard);
  const cardText = (key) => translate(document.documentElement.lang || navigator.language, key);
  const documentationURL = "https://github.com/manuelem1984/dec_deepal";
  window.customCards = window.customCards || [];
  window.customCards.push(
    { type: TAG, name: "DEC Deepal", description: cardText("card_description"), preview: true, documentationURL },
    { type: TOP_TAG, name: `DEC Deepal · ${cardText("top_view")}`, description: cardText("top_card_description"), preview: true, documentationURL }
  );
