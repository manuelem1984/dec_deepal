// ESLint del JavaScript que se publica: la tarjeta, el panel y los iconos.
//
// Se revisan los ficheros GENERADOS (frontend_*/dec-deepal-*.js), no los
// trozos de frontend_*/src/: los trozos se juntan dentro de una sola función
// y, por separado, usan nombres que están en otros trozos.
//
// Solo para desarrollo (no afecta a la integración):
//   npm install          (instala ESLint, versiones fijadas en package.json)
//   npm run lint:js
// La CI lo pasa en cada push (.github/workflows/tests.yaml).
import js from "@eslint/js";
import globals from "globals";

export default [
  js.configs.recommended,
  {
    files: [
      "custom_components/dec_deepal/frontend_card/dec-deepal-card.js",
      "custom_components/dec_deepal/frontend_panel/dec-deepal-panel.js",
      "custom_components/dec_deepal/icons/*.js",
    ],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.browser },
    },
    rules: {
      // Parámetros y errores capturados sin usar son habituales en los
      // manejadores (event, _error): no se avisan.
      "no-unused-vars": ["error", { args: "none", caughtErrors: "none" }],
    },
  },
];
