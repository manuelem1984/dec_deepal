  // ---------------------------------------------------------------------------
  // Estilos (con las variables del tema de Home Assistant: claro y oscuro)
  // ---------------------------------------------------------------------------
  const SOFT = "rgba(var(--rgb-primary-text-color, 33, 33, 33), 0.06)";
  const PANEL_CSS = `
    :host { display: block; height: 100%; color: var(--primary-text-color); background: var(--primary-background-color, #fafafa);
      font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); font-size: 14px; }
    * { box-sizing: border-box; }
    button { font: inherit; color: inherit; border: 0; background: none; margin: 0; cursor: pointer; -webkit-tap-highlight-color: transparent; }
    .page { display: flex; flex-direction: column; height: 100%; }
    .bar { background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff); flex: none; }
    .top { display: flex; align-items: center; height: var(--header-height, 56px); padding: 0 12px; gap: 8px; font-size: 20px; }
    .top span { flex: 1; } .top small { font-size: 13px; opacity: .85; }
    .tabs { display: flex; padding: 0 12px; gap: 4px; overflow-x: auto; }
    .tabs button { font-weight: 500; font-size: 13px; letter-spacing: .6px; text-transform: uppercase; padding: 13px 16px; opacity: .75;
      border-bottom: 3px solid transparent; display: flex; gap: 8px; align-items: center; white-space: nowrap; --mdc-icon-size: 18px; }
    .tabs button.on { opacity: 1; border-color: currentColor; }
    .scroll { flex: 1; overflow: auto; }
    .view { padding: 20px; max-width: 1040px; margin: 0 auto; }
    .card { background: var(--ha-card-background, var(--card-background-color, #fff)); border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 12px; margin-bottom: 20px; overflow: hidden; }
    .card h2 { font-size: 18px; font-weight: 400; margin: 0; padding: 16px 20px 4px; }
    .sub { color: var(--secondary-text-color); padding: 0 20px 12px; font-size: 13px; }
    .pad { padding: 14px 20px; }
    .empty { padding: 40px 20px; text-align: center; color: var(--secondary-text-color); }

    .btn { display: inline-flex; gap: 8px; align-items: center; border-radius: 18px; padding: 8px 16px; font-weight: 500; white-space: nowrap;
      background: var(--primary-color); color: var(--text-primary-color, #fff); text-decoration: none; --mdc-icon-size: 18px; }
    .btn.o { background: transparent; color: var(--primary-color); border: 1px solid var(--divider-color, #e0e0e0); }
    .btn.r { background: transparent; color: var(--error-color, #db4437); border: 1px solid var(--divider-color, #e0e0e0); }
    .btn[disabled] { opacity: .5; pointer-events: none; }
    .badge { font-size: 12px; padding: 4px 10px; border-radius: 12px; font-weight: 500; display: inline-flex; gap: 4px; align-items: center; --mdc-icon-size: 14px; }
    .badge.ok { background: rgba(67, 160, 71, .15); color: var(--success-color, #2e7d32); }
    .badge + .badge { margin-left: 6px; }
    .badge.warn { background: rgba(249, 168, 37, .18); color: var(--warning-color, #f57f17); }
    .badge.info { background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); color: var(--primary-color); }

    /* --- Coches --- */
    .hero { display: flex; align-items: center; gap: 16px; padding: 12px 20px 0; flex-wrap: wrap; }
    .hero img { width: 380px; max-width: 100%; margin: -4px 0 -8px -16px; }
    .hero .who { flex: 1; min-width: 200px; }
    .hero .n { font-size: 26px; }
    .hero .m { color: var(--secondary-text-color); margin: 2px 0 10px; display: flex; align-items: center; gap: 4px 10px; flex-wrap: wrap; }
    .chead .nm { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .plate { display: inline-flex; align-items: stretch; height: 22px; flex: none; background: #fff; color: #111; border: 1.5px solid #1b1b1b;
      border-radius: 4px; overflow: hidden; line-height: 1; font-family: "DIN 1451", "Barlow Semi Condensed", "Roboto Condensed", "Arial Narrow", sans-serif; }
    .plate .eu { width: 12px; background: #0b3fa8; color: #fff; font-size: 7px; padding: 2px 0 1px; display: flex; flex-direction: column;
      align-items: center; justify-content: space-between; font-family: Arial, sans-serif; }
    .plate .num { display: flex; align-items: center; padding: 0 6px; font-size: 15px; font-weight: 500; letter-spacing: .03em; white-space: nowrap; }
    .plate .seals { display: inline-flex; flex-direction: column; gap: 2px; margin: 0 4px; }
    .plate .seals i { display: block; width: 5px; height: 5px; border-radius: 50%; border: 1px solid #444; }
    .kv { display: flex; gap: 26px; margin-top: 8px; flex-wrap: wrap; }
    .kv div { font-size: 13px; color: var(--secondary-text-color); } .kv b { display: block; font-size: 18px; font-weight: 400; color: var(--primary-text-color); }
    .chips { padding: 14px 20px 2px; }
    .people { display: flex; flex-wrap: wrap; align-items: center; gap: 0 6px; padding: 6px 20px 0; font-size: 13px; }
    .people .lbl { display: inline-flex; gap: 6px; align-items: center; color: var(--secondary-text-color); margin: 0 6px 6px 0; padding: 0; border: 0;
      font-size: 13px; --mdc-icon-size: 18px; }
    .people .chip { margin-bottom: 6px; }
    .people .none { color: var(--secondary-text-color); margin: 0 10px 6px 0; }
    .people .link { margin-bottom: 6px; }
    .ro { display: flex; gap: 10px; align-items: center; margin: 0 0 14px; padding: 10px 14px; border-radius: 10px;
      background: rgba(var(--rgb-primary-color, 3, 169, 244), .1); color: var(--primary-text-color); font-size: 14px; --mdc-icon-size: 20px; }
    .ro ha-icon { color: var(--primary-color); }
    .chip { display: inline-flex; gap: 6px; align-items: center; padding: 5px 12px; border-radius: 16px; background: ${SOFT}; font-size: 13px;
      margin: 0 6px 6px 0; --mdc-icon-size: 16px; }
    .chip ha-icon { color: var(--primary-color); }
    .grid3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; padding: 10px 20px 18px; }
    .tile { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 10px; padding: 12px 14px; min-width: 0; }
    .tile[data-action] { cursor: pointer; }
    .tile .h { display: flex; gap: 8px; align-items: center; color: var(--secondary-text-color); font-size: 13px; --mdc-icon-size: 20px; }
    .tile .h span { flex: 1; }
    .gear { width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: -4px -6px -4px 0;
      color: var(--secondary-text-color); background: ${SOFT}; --mdc-icon-size: 20px; }
    .tile .v { font-size: 20px; margin: 6px 0 2px; } .tile .d { color: var(--secondary-text-color); font-size: 13px; }
    .tile.off .v { color: var(--secondary-text-color); }
    .tile.ok .h > ha-icon { color: var(--success-color, #43a047); }
    .tile.soon .h > ha-icon { color: var(--warning-color, #f9a825); }
    .tile.overdue .h > ha-icon { color: var(--error-color, #db4437); }
    .link { color: var(--primary-color); font-size: 13px; padding: 0; }
    .meter { height: 6px; border-radius: 3px; background: ${SOFT}; margin-top: 10px; overflow: hidden; }
    .meter i { display: block; height: 100%; background: var(--success-color, #43a047); }
    .tile.soon .meter i { background: var(--warning-color, #f9a825); } .tile.overdue .meter i { background: var(--error-color, #db4437); }

    /* --- Avisos --- */
    .chead { display: flex; align-items: center; gap: 10px; padding: 8px 20px 0; flex-wrap: wrap; }
    .chead img { width: 170px; margin: -6px 0 -10px -18px; }
    :host([dark]) .hero img, :host([dark]) .chead img { background: ${STUDIO_BG}; }
    .chead .n { font-size: 20px; flex: 1; min-width: 140px; } .chead .n small { display: block; font-size: 13px; color: var(--secondary-text-color); }
    .wide { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    th { font-weight: 400; font-size: 12px; color: var(--secondary-text-color); padding: 10px 6px; text-align: center; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
    th:first-child { text-align: left; padding-left: 20px; font-size: 13px; }
    .dev { display: flex; flex-direction: column; align-items: center; gap: 4px; max-width: 96px; margin: 0 auto; }
    .dev u { text-decoration: none; width: 30px; height: 30px; border-radius: 50%; background: var(--primary-color); color: var(--text-primary-color, #fff);
      display: flex; align-items: center; justify-content: center; --mdc-icon-size: 17px; }
    .dev.panel u { background: var(--secondary-text-color); }
    td { padding: 6px; text-align: center; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
    td:first-child { text-align: left; padding-left: 20px; }
    tr:last-child td { border-bottom: 0; }
    .box { width: 36px; height: 36px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
      color: var(--secondary-text-color); --mdc-icon-size: 22px; }
    .box.y, .box.some { color: var(--primary-color); }
    .box.ro { cursor: default; opacity: .8; }
    tr.grp td { background: ${SOFT}; }
    tr.grp td:first-child { padding: 0; }
    .fold { display: flex; align-items: center; gap: 8px; width: 100%; padding: 12px 14px; font-weight: 500; font-size: 15px; text-align: left; --mdc-icon-size: 22px; }
    .fold .sic { color: var(--primary-color); } .fold small { font-weight: 400; font-size: 12px; color: var(--secondary-text-color); margin-left: 6px; }
    tr.it td:first-child { padding-left: 52px; }
    .lab { display: flex; align-items: center; gap: 8px; min-height: 36px; }
    .lab b { font-weight: 400; } .lab small { color: var(--secondary-text-color); font-size: 12px; flex: 1; }
    .pen { width: 32px; height: 32px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
      color: var(--secondary-text-color); --mdc-icon-size: 18px; flex: none; }
    tr.ed td { background: rgba(var(--rgb-primary-color, 3, 169, 244), .1); }
    .inp { display: inline-flex; align-items: center; border: 1px solid var(--primary-color); border-radius: 6px; overflow: hidden;
      background: var(--card-background-color, #fff); }
    .inp input { width: 78px; border: 0; padding: 6px 8px; font: inherit; text-align: right; background: transparent; color: inherit; outline: none; }
    .inp span { padding: 6px 10px; color: var(--secondary-text-color); font-size: 13px; border-left: 1px solid var(--divider-color, #e0e0e0); }
    .mini { width: 32px; height: 32px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; --mdc-icon-size: 18px; flex: none; }
    .mini.ok { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .foot { display: flex; align-items: center; gap: 10px; padding: 12px 20px; border-top: 1px solid var(--divider-color, #e0e0e0); flex-wrap: wrap; }
    .foot span { flex: 1; color: var(--secondary-text-color); font-size: 13px; min-width: 160px; }
    .foot.dirty { background: rgba(var(--rgb-primary-color, 3, 169, 244), .08); }

    /* --- Datos y diagnóstico --- */
    .row { display: flex; gap: 14px; align-items: center; padding: 14px 20px; border-top: 1px solid var(--divider-color, #e0e0e0); flex-wrap: wrap; }
    .row .ic { width: 40px; height: 40px; border-radius: 50%; background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); color: var(--primary-color);
      display: flex; align-items: center; justify-content: center; flex: none; }
    .row .ic.grey { background: ${SOFT}; color: var(--secondary-text-color); }
    .under { padding: 0 20px 14px; }
    .seg.wide { display: flex; flex-wrap: nowrap; } .seg.wide button { flex: 1 1 auto; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 8px 5px; font-size: 12.5px; }
    .seg.wide button.on::before { content: "✓ "; }
    .chg-chips { margin-top: 6px; } .chg-chips .chip { margin: 0 6px 4px 0; font-size: 12px; padding: 3px 10px; --mdc-icon-size: 16px; }
    .row .tx { flex: 1; min-width: 180px; } .row .tx small { display: block; color: var(--secondary-text-color); font-size: 13px; }
    select { font: inherit; color: inherit; padding: 7px 8px; border-radius: 8px; border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff); max-width: 100%; }
    .filt { display: flex; gap: 8px; padding: 0 20px 14px; flex-wrap: wrap; }
    .filt button { padding: 5px 12px; border-radius: 16px; border: 1px solid var(--divider-color, #e0e0e0); font-size: 13px; }
    .filt button.on { background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); border-color: var(--primary-color); color: var(--primary-color); }
    .log { display: flex; gap: 12px; padding: 10px 20px; border-top: 1px solid var(--divider-color, #e0e0e0); align-items: flex-start; }
    .log time { color: var(--secondary-text-color); font-size: 12px; width: 86px; flex: none; padding-top: 6px; }
    .log .dot { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex: none; --mdc-icon-size: 17px;
      background: ${SOFT}; color: var(--secondary-text-color); }
    .log .dot.blue { background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); color: var(--primary-color); }
    .log .dot.red { background: rgba(219, 68, 55, .15); color: var(--error-color, #db4437); }
    .log .dot.green { background: rgba(67, 160, 71, .15); color: var(--success-color, #43a047); }
    .log .what { min-width: 0; overflow-wrap: anywhere; } .log .what small { display: block; color: var(--secondary-text-color); font-size: 12px; }

    /* --- Ajustes --- */
    .acct { font-size: 13px; color: var(--secondary-text-color); margin: 0 4px 8px; }
    h2.next { border-top: 1px solid var(--divider-color, #e0e0e0); padding-top: 18px; margin-top: 6px; }
    .lbl { font-size: 13px; color: var(--secondary-text-color); padding: 14px 20px 8px; border-top: 1px solid var(--divider-color, #e0e0e0); }
    .tog { width: 40px; height: 22px; border-radius: 11px; background: var(--disabled-text-color, #bdbdbd); position: relative; flex: none; }
    .tog::after { content: ""; position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%; background: #fff; transition: left .15s; }
    .tog.on { background: var(--primary-color); } .tog.on::after { left: 21px; }
    .seg { display: inline-flex; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 18px; overflow: hidden; flex-wrap: wrap; }
    .seg button { padding: 7px 13px; font-size: 13px; border-right: 1px solid var(--divider-color, #e0e0e0); }
    .seg button:last-child { border: 0; } .seg button.on { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .modes { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; padding: 0 20px 16px; }
    .mode { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 12px; padding: 14px 16px; text-align: left; }
    .mode.on { border: 2px solid var(--primary-color); padding: 13px 15px; background: rgba(var(--rgb-primary-color, 3, 169, 244), .08); }
    .mode b { font-weight: 500; display: flex; gap: 8px; align-items: center; --mdc-icon-size: 20px; } .mode b ha-icon { color: var(--primary-color); }
    .mode p { margin: 6px 0 0; color: var(--secondary-text-color); font-size: 13px; line-height: 1.45; }
    .pinbox { display: inline-flex; align-items: center; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 8px; overflow: hidden;
      background: var(--card-background-color, #fff); }
    .pinbox input { width: 110px; border: 0; padding: 9px 10px; font: inherit; font-size: 16px; letter-spacing: 4px; background: transparent; color: inherit; outline: none; }
    .pinbox button { padding: 6px 8px; color: var(--secondary-text-color); --mdc-icon-size: 20px; display: flex; }
    input.url { font: inherit; color: inherit; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff); width: 320px; max-width: 100%; }

    @media (max-width: 700px) {
      .view { padding: 12px; }
      .modes { grid-template-columns: 1fr; }
      .grid3 { grid-template-columns: 1fr; }
      .hero img { width: 100%; margin: 0; }
      .tabs button { padding: 12px 10px; } .tabs button ha-icon { display: none; }
      tr.it td:first-child { padding-left: 20px; }
    }
  `;

  const DIALOG_CSS = `
    :host { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; padding: 16px; box-sizing: border-box;
      background: rgba(0, 0, 0, .32); font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); color: var(--primary-text-color); font-size: 14px; }
    * { box-sizing: border-box; }
    .dlg { width: 100%; max-width: 460px; max-height: 100%; overflow: auto; background: var(--ha-card-background, var(--card-background-color, #fff));
      border-radius: 24px; box-shadow: 0 8px 24px rgba(0, 0, 0, .3); padding: 20px 22px 16px; }
    button { font: inherit; color: inherit; border: 0; background: none; margin: 0; cursor: pointer; }
    h2 { margin: 0 0 4px; font-size: 20px; font-weight: 400; }
    p { margin: 6px 0 12px; color: var(--secondary-text-color); line-height: 1.45; }
    label { display: block; margin: 12px 0 0; font-size: 13px; color: var(--secondary-text-color); }
    label small { display: block; font-size: 12px; margin-top: 3px; }
    input:not([type=checkbox]), select { display: block; width: 100%; margin-top: 4px; font: inherit; color: var(--primary-text-color); padding: 9px 10px;
      border-radius: 8px; border: 1px solid var(--divider-color, #e0e0e0); background: var(--card-background-color, #fff); }
    label.check { display: flex; align-items: center; gap: 10px; font-size: 15px; color: var(--primary-text-color); }
    label.check input { width: 18px; height: 18px; margin: 0; }
    .two { display: grid; grid-template-columns: 1fr 1fr; gap: 0 12px; }
    .err { color: var(--error-color, #db4437); font-size: 13px; margin-top: 10px; min-height: 18px; }
    .btns { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; flex-wrap: wrap; }
    .tb { font-weight: 500; color: var(--primary-color); padding: 9px 14px; border-radius: 18px; }
    .tb.fill { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .tb.danger { background: var(--error-color, #db4437); color: #fff; }
    .tb.left { margin-right: auto; }
    /* Ventana de Apariencia */
    .dlg.wide { max-width: 640px; }
    /* Fichas y formularios de Coches */
    .dlg.mid { max-width: 580px; }
    a.tb { text-decoration: none; display: inline-block; }
    .thead { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
    .thead .ic { width: 44px; height: 44px; border-radius: 50%; background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); color: var(--primary-color);
      display: flex; align-items: center; justify-content: center; flex: none; }
    .thead h2 { flex: 1; margin: 0; } .thead h2 small { display: block; font-size: 13px; color: var(--secondary-text-color); margin-top: 2px; }
    .sw2 { display: flex; gap: 8px; align-items: center; font-size: 13px; }
    .x { width: 36px; height: 36px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; color: var(--secondary-text-color); --mdc-icon-size: 20px; flex: none; }
    .tog { width: 40px; height: 22px; border-radius: 11px; background: var(--disabled-text-color, #bdbdbd); position: relative; flex: none; }
    .tog::after { content: ""; position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%; background: #fff; transition: left .15s; }
    .tog.on { background: var(--primary-color); } .tog.on::after { left: 21px; }
    .off { padding: 8px 0 4px; }
    .fsec { border-top: 1px solid var(--divider-color, #e0e0e0); padding: 14px 0 4px; }
    .fsec h4 { font-size: 13px; font-weight: 500; margin: 0 0 2px; display: flex; gap: 8px; align-items: center; --mdc-icon-size: 18px; }
    .fsec h4 ha-icon { color: var(--primary-color); }
    .hp { font-size: 12px; color: var(--secondary-text-color); margin-bottom: 10px; line-height: 1.4; }
    .fl, .fld > span:first-child { display: block; font-size: 12px; color: var(--secondary-text-color); margin-bottom: 4px; }
    label.fld { margin: 0; }
    .fi { display: flex; align-items: center; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 8px; background: var(--card-background-color, #fff); overflow: hidden; }
    .fi input:not([type=checkbox]) { border: 0; margin: 0; border-radius: 0; background: transparent; min-width: 0; flex: 1; outline: none; }
    .fi em { font-style: normal; color: var(--secondary-text-color); font-size: 13px; padding: 0 10px; }
    .fg { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 10px; align-items: start; }
    .inline { display: flex; align-items: center; gap: 14px; margin-bottom: 12px; flex-wrap: wrap; }
    .note { font-size: 13px; color: var(--secondary-text-color); padding-top: 16px; }
    .stepper { display: inline-flex; align-items: center; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 20px; overflow: hidden; }
    .stepper button { width: 40px; height: 38px; font-size: 20px; color: var(--primary-color); }
    .stepper b { min-width: 40px; text-align: center; font-size: 17px; font-weight: 400; }
    .hint { display: inline-flex; gap: 6px; align-items: center; font-size: 12px; color: var(--primary-color); margin-top: 5px; --mdc-icon-size: 15px; }
    .opts { margin-bottom: 10px; }
    .kinds { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px; }
    .kind { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 10px; padding: 9px 12px; display: flex; gap: 8px; align-items: center; text-align: left; --mdc-icon-size: 18px; }
    .kind ha-icon { color: var(--secondary-text-color); }
    .kind.on { border: 2px solid var(--primary-color); padding: 8px 11px; background: rgba(var(--rgb-primary-color, 3, 169, 244), .1); } .kind.on ha-icon { color: var(--primary-color); }
    .seg { display: inline-flex; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 18px; overflow: hidden; flex-wrap: wrap; }
    .seg button { padding: 8px 12px; font-size: 13px; border-right: 1px solid var(--divider-color, #e0e0e0); }
    .seg button:last-child { border: 0; } .seg button.on { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .preview { border-radius: 12px; background: rgba(67, 160, 71, .14); padding: 12px 14px; display: flex; gap: 12px; align-items: center; margin-top: 6px; }
    .preview ha-icon { color: var(--success-color, #43a047); flex: none; } .preview b { font-weight: 500; display: block; } .preview small { font-size: 13px; }
    .big { font-size: 28px; margin: 2px 0; overflow-wrap: anywhere; } .bigsub { color: var(--secondary-text-color); font-size: 13px; margin-bottom: 12px; }
    .dual { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 6px; }
    .stat { background: rgba(var(--rgb-primary-text-color, 33, 33, 33), .05); border-radius: 12px; padding: 12px 14px; min-width: 0; }
    .stat .k { font-size: 12px; color: var(--secondary-text-color); display: flex; gap: 6px; align-items: center; --mdc-icon-size: 16px; }
    .stat .n { font-size: 20px; margin: 4px 0 1px; } .stat .d { font-size: 12px; color: var(--secondary-text-color); min-height: 15px; }
    .meter { height: 6px; border-radius: 3px; background: rgba(var(--rgb-primary-text-color, 33, 33, 33), .1); margin-top: 8px; overflow: hidden; }
    .meter i { display: block; height: 100%; background: var(--success-color, #43a047); }
    .h3 { font-size: 13px; font-weight: 500; margin: 16px 0 6px; display: flex; gap: 8px; align-items: center; } .h3 span { font-weight: 400; color: var(--secondary-text-color); }
    .ops { margin: 0; padding: 0; list-style: none; }
    .ops li { display: flex; gap: 10px; align-items: flex-start; padding: 7px 0; border-bottom: 1px solid var(--divider-color, #e0e0e0); --mdc-icon-size: 20px; }
    .ops li:last-child { border: 0; } .ops ha-icon { color: var(--success-color, #43a047); flex: none; }
    .ops small { display: block; color: var(--secondary-text-color); font-size: 12px; }
    .hist { display: flex; gap: 10px; align-items: center; padding: 5px 0; font-size: 13px; --mdc-icon-size: 18px; } .hist ha-icon { color: var(--secondary-text-color); flex: none; }
    .chip { display: inline-block; padding: 5px 12px; border-radius: 16px; background: rgba(var(--rgb-primary-text-color, 33, 33, 33), .06); font-size: 13px; margin: 0 6px 6px 0; }
    .badge { font-size: 12px; padding: 4px 10px; border-radius: 12px; font-weight: 500; }
    .badge.info { background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); color: var(--primary-color); }
    .pol { display: flex; align-items: center; gap: 12px; } .pol span { font-size: 13px; color: var(--secondary-text-color); } .pol b { font-weight: 400; flex: 1; }
    .line { position: relative; height: 34px; margin: 6px 10px 4px; }
    .line .track, .line .fill, .line .amber { position: absolute; top: 14px; height: 6px; border-radius: 3px; }
    .line .track { left: 0; right: 0; background: rgba(var(--rgb-primary-text-color, 33, 33, 33), .1); }
    .line .fill { left: 0; background: var(--success-color, #43a047); } .line .amber { background: var(--warning-color, #f9a825); border-radius: 0; }
    .line .pt { position: absolute; top: 7px; width: 20px; height: 20px; border-radius: 50%; background: var(--card-background-color, #fff); border: 3px solid var(--primary-color); transform: translateX(-50%); }
    .line .pt.now { border-color: var(--success-color, #43a047); background: var(--success-color, #43a047); }
    .calls { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .callb { display: flex; gap: 12px; align-items: center; border-radius: 14px; padding: 12px 14px; text-decoration: none;
      background: rgba(var(--rgb-primary-color, 3, 169, 244), .12); color: var(--primary-color); }
    .callb b { font-weight: 500; display: block; } .callb small { font-size: 13px; }
    .ifoot { display: flex; align-items: center; gap: 8px; margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--divider-color, #e0e0e0); flex-wrap: wrap; }
    .ifoot span { flex: 1; }
    .gearb { width: 40px; height: 40px; border-radius: 50%; background: rgba(var(--rgb-primary-text-color, 33, 33, 33), .06); color: var(--secondary-text-color);
      display: flex; align-items: center; justify-content: center; --mdc-icon-size: 22px; }
    @media (max-width: 520px) { .fg, .dual, .kinds, .calls { grid-template-columns: 1fr; } }
    .prev { background: rgba(var(--rgb-primary-text-color, 33, 33, 33), .05); border-radius: 16px; text-align: center; padding-top: 4px; margin-bottom: 4px; overflow: hidden; }
    .prev img { width: 88%; display: block; margin: 0 auto -4px; }
    .dlg.dark .prev { background: ${STUDIO_BG}; }
    .lbl { font-size: 13px; color: var(--secondary-text-color); margin: 14px 0 6px; }
    .opts { display: flex; gap: 8px; flex-wrap: wrap; }
    .opt { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 12px; padding: 9px 14px; text-align: left; }
    .opt small { display: block; color: var(--secondary-text-color); font-size: 12px; margin-top: 2px; }
    .opt.on { border: 2px solid var(--primary-color); padding: 8px 13px; background: rgba(var(--rgb-primary-color, 3, 169, 244), .1); }
    /* Ventana de un cargador */
    .fsec h4 .num { width: 18px; height: 18px; border-radius: 50%; background: var(--primary-color); color: var(--text-primary-color, #fff); font-size: 11px;
      display: inline-flex; align-items: center; justify-content: center; }
    label.cname { flex: 1; margin: 0; } label.cname > span:first-child { font-size: 12px; color: var(--primary-color); }
    label.cname .cn { display: flex; align-items: center; gap: 6px; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 8px; padding: 0 10px 0 0; margin-top: 4px;
      color: var(--secondary-text-color); --mdc-icon-size: 18px; }
    label.cname input { border: 0; margin: 0; font-size: 18px; padding: 8px 10px; background: transparent; }
    .cname-help { margin: -4px 0 4px 56px; }
    small.eid { display: block; font-size: 11px; color: var(--secondary-text-color); margin-top: 3px; word-break: break-all; }
    .cstack { margin: 12px 0; } .cstack b { display: block; font-weight: 400; font-size: 14px; color: var(--primary-text-color); }
    .cstack small { display: block; font-size: 12px; color: var(--secondary-text-color); margin: 2px 0 8px; }
    .cstack > .seg { margin-top: 6px; }
    .fi.wide { margin-top: 8px; }
    label.ent { margin: 8px 0 0; } label.ent > span { display: flex; justify-content: space-between; gap: 8px; }
    label.ent em { font-style: normal; color: var(--success-color, #43a047); }
    .cline { display: flex; gap: 12px; align-items: center; justify-content: space-between; margin: 10px 0; }
    .cline b { font-weight: 400; color: var(--primary-text-color); font-size: 14px; } .cline small { display: block; font-size: 12px; color: var(--secondary-text-color); }
    .seg.wide { display: flex; flex-wrap: nowrap; } .seg.wide button { flex: 1 1 auto; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 8px 5px; font-size: 12.5px; }
    .seg.wide button.on::before { content: "✓ "; }
    .carpicks { display: flex; gap: 10px; flex-wrap: wrap; }
    .carpick { flex: 1; min-width: 120px; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 12px; padding: 6px; text-align: center; font-size: 13px; }
    .carpick img { width: 100%; height: 56px; object-fit: contain; display: block; }
    .carpick.on { border: 2px solid var(--primary-color); padding: 5px; background: rgba(var(--rgb-primary-color, 3, 169, 244), .08); }
    .fi.small { width: 130px; flex: none; }
    .learned { display: flex; gap: 8px; align-items: center; background: rgba(67, 160, 71, .12); color: var(--success-color, #2e7d32); border-radius: 10px;
      padding: 6px 10px; font-size: 12px; --mdc-icon-size: 18px; } .learned span { flex: 1; }
    .sw { display: flex; gap: 8px; flex-wrap: wrap; }
    .sw button { display: flex; flex-direction: column; align-items: center; gap: 6px; font-size: 12px; width: 92px; padding: 4px 0; }
    .sw i { display: block; width: 44px; height: 44px; border-radius: 50%; border: 1px solid var(--divider-color, #cfd8dc); }
    .sw .on i { outline: 3px solid var(--primary-color); outline-offset: 2px; }
    [hidden] { display: none !important; }
  `;
