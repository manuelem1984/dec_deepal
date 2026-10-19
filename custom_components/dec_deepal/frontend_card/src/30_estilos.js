  // ---------------------------------------------------------------------------
  // Estilos
  // ---------------------------------------------------------------------------
  const TILE_BG = "rgba(var(--rgb-primary-text-color, 33, 33, 33), 0.05)";
  const CARD_CSS = `
    :host { display: block; }
    ha-card { overflow: hidden; }
    .hdr { display: flex; align-items: center; gap: 8px; padding: 14px 8px 4px 16px; }
    .grow { flex: 1; min-width: 0; }
    .name { font-size: 20px; line-height: 1.2; color: var(--primary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .upd { font-size: 12px; color: var(--secondary-text-color); margin-top: 2px; }
    button { font: inherit; color: inherit; border: 0; background: none; margin: 0; cursor: pointer; -webkit-tap-highlight-color: transparent; }
    .icon-btn { width: 40px; height: 40px; border-radius: 50%; color: var(--secondary-text-color); display: flex; align-items: center; justify-content: center; }
    .icon-btn:hover { background: ${TILE_BG}; }
    .spin ha-icon { animation: dec-spin 1s linear infinite; }
    @keyframes dec-spin { to { transform: rotate(360deg); } }
    .carbox { position: relative; overflow: hidden; aspect-ratio: ${ISOMETRIC.crop.w} / ${ISOMETRIC.crop.h}; }
    .carbox[hidden] { display: none; }
    :host([dark]) .carbox { background: ${STUDIO_BG}; }
    .carbox.plain { aspect-ratio: auto; }
    .carbox.plain .car { position: static; width: 100%; }
    /* Vista planta: tumbada (morro a la izquierda) o de pie. */
    .carbox.top { aspect-ratio: ${TOP.crop.h} / ${TOP.crop.w}; }
    .carbox.top .car { transform: rotate(-90deg);
      width: ${(TOP.size / TOP.crop.h) * 100}%;
      left: ${(-TOP.crop.y / TOP.crop.h) * 100}%;
      top: ${(-TOP.crop.x / TOP.crop.w) * 100}%; }
    .carbox.top.vertical { aspect-ratio: ${TOP.crop.w} / ${TOP.crop.h}; max-width: 320px; margin: 0 auto; }
    .carbox.top.vertical .car { transform: none;
      width: ${(TOP.size / TOP.crop.w) * 100}%;
      left: ${(-TOP.crop.x / TOP.crop.w) * 100}%;
      top: ${(-TOP.crop.y / TOP.crop.h) * 100}%; }
    .car { position: absolute; max-width: none; display: block;
      width: ${(ISOMETRIC.width / ISOMETRIC.crop.w) * 100}%;
      left: ${(-ISOMETRIC.crop.x / ISOMETRIC.crop.w) * 100}%;
      top: ${(-ISOMETRIC.crop.y / ISOMETRIC.crop.h) * 100}%; }
    .energy { cursor: pointer; border-radius: 12px; outline-offset: -2px; }
    .energy:active { opacity: .7; }
    .range { display: flex; align-items: center; gap: 8px; padding: 0 16px; }
    .range .batt { --mdc-icon-size: 26px; }
    .range .km { font-size: 24px; color: var(--primary-text-color); white-space: nowrap; }
    .range .kms { font-size: 15px; color: var(--secondary-text-color); white-space: nowrap; margin-left: -2px; }
    .range .kms[hidden] { display: none; }
    .range .estb { font-size: 11px; color: var(--warning-color, #e65100); background: rgba(255, 152, 0, .15); border-radius: 8px; padding: 1px 7px; margin-left: 6px; white-space: nowrap; }
    .range .charge.est { color: var(--success-color, #43a047); font-weight: 500; }
    .upd.est { color: var(--warning-color, #e65100); }
    .range .charge { font-size: 14px; color: var(--secondary-text-color); display: flex; align-items: center; gap: 4px; --mdc-icon-size: 18px; }
    .bar { position: relative; height: 8px; border-radius: 4px; background: ${TILE_BG}; margin: 6px 16px 14px; overflow: hidden; }
    .bar i { display: block; height: 100%; border-radius: 4px; transition: width .4s; }
    /* Límite de carga: la marca en la barra, el selector y qué va a pasar. */
    .bar .tgt { position: absolute; top: 0; bottom: 0; width: 2px; background: var(--primary-text-color); opacity: .7; }
    .limits { display: flex; align-items: center; gap: 8px; padding: 0 16px; margin: -6px 0 10px; }
    .limits[hidden], .lhint[hidden], .lhint .once[hidden] { display: none; }
    .limits .lbl { font-size: 12.5px; color: var(--secondary-text-color); display: flex; gap: 4px; align-items: center; white-space: nowrap; --mdc-icon-size: 16px; }
    .lseg { flex: 1; display: flex; border: 1px solid var(--divider-color, #ddd); border-radius: 16px; overflow: hidden; }
    .lseg button { flex: 1; padding: 6px 2px; font-size: 12.5px; white-space: nowrap; color: var(--primary-text-color); border-right: 1px solid var(--divider-color, #ddd); }
    .lseg button:last-child { border-right: 0; }
    .lseg button.on { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .limits button:disabled, .lhint .once:disabled { cursor: default; opacity: .55; }
    .lhint { display: flex; align-items: center; gap: 6px; padding: 0 16px; margin: -4px 0 10px; font-size: 12px; color: var(--primary-color); --mdc-icon-size: 15px; }
    .lhint.warn { color: var(--warning-color, #e65100); }
    .lhint .tx { flex: 1; min-width: 0; }
    .lhint .once { font-size: 12px; color: var(--primary-color); border: 1px solid rgba(var(--rgb-primary-color, 3, 169, 244), .4); border-radius: 14px; padding: 3px 10px; white-space: nowrap; }
    .lhint .once.on { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
    .status { display: flex; justify-content: flex-end; align-items: center; gap: 10px; padding: 0 16px 10px; min-height: 22px; --mdc-icon-size: 22px; }
    .status .ok { color: var(--success-color, #43a047); }
    .status button { padding: 0; display: flex; }
    /* 6 botones en dos filas de 3. */
    .tiles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; padding: 0 12px 12px; }
    .tile { background: ${TILE_BG}; border-radius: 12px; padding: 10px 6px; display: flex; flex-direction: column; align-items: center; gap: 4px; text-align: center; min-height: 84px; color: var(--secondary-text-color); transition: opacity .2s, transform .1s; }
    .tile:active { transform: scale(.97); }
    .tile.on { color: var(--state-active-color, #ffc107); }
    .tile.pri { color: var(--primary-color); }
    .tile.busy { opacity: .45; pointer-events: none; }
    .tile b { font-size: 12px; font-weight: 500; color: var(--primary-text-color); }
    .tile small { font-size: 11px; color: var(--secondary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
    .msg { padding: 16px; color: var(--secondary-text-color); font-size: 14px; }
  `;
  const DIALOG_CSS = `
    :host { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; box-sizing: border-box;
      /* En el iPhone, Home Assistant pinta bajo la hora y la batería: se respeta la zona segura. */
      padding: max(16px, calc(env(safe-area-inset-top, 0px) + 8px)) 16px max(16px, calc(env(safe-area-inset-bottom, 0px) + 8px));
      background: rgba(0, 0, 0, .32); font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); color: var(--primary-text-color); }
    .dlg { width: 100%; max-width: 440px; max-height: 100%; overflow: auto; background: var(--ha-card-background, var(--card-background-color, #fff));
      border-radius: 28px; box-shadow: 0 8px 24px rgba(0, 0, 0, .3); }
    button { font: inherit; color: inherit; border: 0; background: none; margin: 0; cursor: pointer; -webkit-tap-highlight-color: transparent; }
    .head { display: flex; align-items: center; gap: 4px; padding: 8px 8px 4px; }
    .head h2 { margin: 0; font-size: 20px; font-weight: 400; flex: 1; }
    .icon-btn { width: 40px; height: 40px; border-radius: 50%; color: var(--secondary-text-color); display: flex; align-items: center; justify-content: center; }
    .stage { position: relative; margin: 4px 12px 0; border-radius: 16px; overflow: hidden; background: ${TILE_BG};
      aspect-ratio: ${INTERIOR.crop.w} / ${INTERIOR.crop.h}; }
    .stage img { position: absolute; max-width: none;
      width: ${(INTERIOR.width / INTERIOR.crop.w) * 100}%;
      left: ${(-INTERIOR.crop.x / INTERIOR.crop.w) * 100}%;
      top: ${(-INTERIOR.crop.y / INTERIOR.crop.h) * 100}%; }
    .hot { position: absolute; transform: translate(-50%, -50%); width: 44px; height: 44px; display: flex; align-items: center; justify-content: center;
      color: #fff; --mdc-icon-size: 34px; filter: drop-shadow(0 1px 2px rgba(0, 0, 0, .65)); opacity: .38; transition: opacity .2s; }
    .hot.on { opacity: 1; }
    .hot.busy { animation: dec-pulse .8s ease-in-out infinite; pointer-events: none; }
    @keyframes dec-pulse { 50% { opacity: .25; } }
    .hot u { position: absolute; left: 82%; top: -2px; font-size: 15px; font-weight: 500; text-decoration: none; }
    .temp { display: flex; align-items: center; justify-content: center; gap: 18px; padding: 16px 12px 14px; }
    .temp b { font-size: 40px; font-weight: 400; min-width: 3.2ch; text-align: center; }
    .temp sup { font-size: 16px; color: var(--secondary-text-color); }
    .round { width: 48px; height: 48px; border-radius: 50%; background: ${TILE_BG}; display: flex; align-items: center; justify-content: center; color: var(--secondary-text-color); }
    .power { display: flex; align-items: center; justify-content: center; gap: 8px; margin: 0 12px; width: calc(100% - 24px); padding: 12px; border-radius: 12px;
      background: ${TILE_BG}; font-size: 14px; font-weight: 500; --mdc-icon-size: 20px; }
    .power ha-icon { color: var(--secondary-text-color); }
    .power.on { background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); }
    .power.on ha-icon { color: var(--primary-color); }
    .power.busy { opacity: .5; pointer-events: none; }
    .info { font-size: 12px; color: var(--secondary-text-color); text-align: center; margin: 12px 12px 16px; }
    /* Ventana de carga. La vista de carga es un coche translúcido y claro:
       sobre fondo claro se oscurece para que se vea; en tema oscuro va tal cual. */
    .chg { padding: 4px 16px 6px; }
    .chg .view { position: relative; overflow: hidden; aspect-ratio: ${CHARGING.crop.w} / ${CHARGING.crop.h}; }
    .chg .view[hidden] { display: none; }
    .chg .view img { position: absolute; max-width: none;
      width: ${(CHARGING.width / CHARGING.crop.w) * 100}%;
      left: ${(-CHARGING.crop.x / CHARGING.crop.w) * 100}%;
      top: ${(-CHARGING.crop.y / CHARGING.crop.h) * 100}%;
      filter: brightness(.62) contrast(1.25); }
    .chg.dark .view img { filter: none; }
    .chg.dark .view { background: ${STUDIO_BG}; }
    .chg .now { font-size: 13px; font-weight: 500; display: flex; gap: 6px; align-items: center; color: var(--secondary-text-color); --mdc-icon-size: 18px; }
    .chg .now.on { color: var(--success-color, #43a047); }
    .chg .pct { display: flex; align-items: baseline; gap: 10px; margin: 6px 0; }
    .chg .pct b { font-size: 34px; font-weight: 400; }
    .chg .pct span { font-size: 14px; color: var(--secondary-text-color); }
    .chg .lvl { height: 10px; border-radius: 5px; background: ${TILE_BG}; overflow: hidden; }
    .chg .lvl i { display: block; height: 100%; border-radius: 5px; transition: width .4s; }
    .chg .lvl.on i { background-image: repeating-linear-gradient(110deg, rgba(255, 255, 255, .35) 0 8px, transparent 8px 16px); }
    .chg .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 14px; }
    .chg .stats:empty { display: none; }
    .chg .st { background: ${TILE_BG}; border-radius: 12px; padding: 10px 12px; min-width: 0; }
    .chg .st.wide { grid-column: 1 / 3; }
    .chg .st .k { font-size: 12px; color: var(--secondary-text-color); display: flex; gap: 6px; align-items: center; --mdc-icon-size: 16px; }
    .chg .st .n { font-size: 19px; margin-top: 3px; }
    .chg .st .d { font-size: 12px; color: var(--secondary-text-color); min-height: 14px; }
    .chg .st .bal { font-size: 11px; color: var(--primary-color); display: flex; gap: 4px; align-items: center; margin-top: 3px; --mdc-icon-size: 14px; }
    .three { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; padding: 8px 12px 16px; }
    /* Menú con menos de tres opciones: centradas, con el mismo ancho que en una fila de tres. */
    .three.center { display: flex; justify-content: center; }
    .three.center .tile { flex: 0 1 calc((100% - 16px) / 3); }
    /* Menú "Otros": de dos en dos, centrado si sobra uno. */
    .three.pairs { display: flex; flex-wrap: wrap; justify-content: center; }
    .three.pairs .tile { flex: 0 1 calc((100% - 8px) / 2); box-sizing: border-box; }
    .mt dl { display: grid; grid-template-columns: auto 1fr; gap: 6px 14px; margin: 0; font-size: 13px; }
    .mt dt { color: var(--secondary-text-color); }
    .mt dd { margin: 0; text-align: right; }
    .calls { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 14px; }
    .calls:empty { display: none; }
    .call span { display: flex; flex-direction: column; align-items: flex-start; line-height: 1.25; }
    .call small { font-size: 11px; font-weight: 400; opacity: .85; }
    .call { display: flex; align-items: center; justify-content: center; gap: 6px; padding: 10px; border-radius: 12px; font-size: 13px; font-weight: 500;
      text-decoration: none; color: var(--primary-color); background: rgba(var(--rgb-primary-color, 3, 169, 244), .12); --mdc-icon-size: 18px; }
    .tile { background: ${TILE_BG}; border-radius: 12px; padding: 10px 6px; display: flex; flex-direction: column; align-items: center; gap: 4px;
      text-align: center; min-height: 84px; color: var(--secondary-text-color); }
    .tile:active { transform: scale(.97); }
    .tile b { font-size: 12px; font-weight: 500; color: var(--primary-text-color); }
    .tile small { font-size: 11px; color: var(--secondary-text-color); }
    .confirm { padding: 20px 24px 8px; }
    .hist { margin: 4px 0 0; padding: 0 20px 0 36px; font-size: 13px; line-height: 1.6; color: var(--secondary-text-color); max-height: 50vh; overflow: auto; }
    .confirm h2 { margin: 0 0 10px; font-size: 22px; font-weight: 400; }
    .confirm p { margin: 0; font-size: 14px; color: var(--secondary-text-color); line-height: 1.5; }
    .btns { display: flex; justify-content: flex-end; gap: 8px; padding: 14px 16px 16px; }
    .tb { font-size: 14px; font-weight: 500; color: var(--primary-color); padding: 10px 14px; border-radius: 20px; }
    .tb.fill { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    a.tile { text-decoration: none; box-sizing: border-box; }
    .mt { padding: 0 20px 4px; }
    .mt .next { font-size: 15px; font-weight: 500; margin: 4px 0 10px; display: flex; align-items: center; gap: 8px; --mdc-icon-size: 22px; }
    .mt .two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
    .mt .stat { background: ${TILE_BG}; border-radius: 12px; padding: 10px 12px; }
    .mt .stat b { display: block; font-size: 24px; font-weight: 400; }
    .mt .stat small, .mt .due { font-size: 12px; color: var(--secondary-text-color); }
    .mt .due { margin: 8px 0 0; }
    .mt h3 { font-size: 13px; font-weight: 500; margin: 16px 0 6px; }
    .mt ul { margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.5; color: var(--secondary-text-color); }
  `;
