// AVLizador: millora progressiva de la pàgina de traduir. Sense este
// fitxer, el formulari s'envia al servidor i la pàgina torna amb la
// traducció. Amb ell: traducció sense recarregar, comptador, botó
// "Copiar" i avisos per als lectors de pantalla. Sense JavaScript en línia
// (Content-Security-Policy: script-src 'self').
(function () {
  "use strict";

  var form = document.getElementById("traductor");
  if (!form || !window.fetch) { return; }

  var dades = JSON.parse(document.getElementById("dades-pagina").textContent);
  var t = dades.textos;
  var maxim = dades.maxim;

  var text = document.getElementById("text");
  var eixida = document.getElementById("traduccio");
  var origen = document.getElementById("origen");
  var desti = document.getElementById("desti");
  var boto = document.getElementById("boto-traduir");
  var copiar = document.getElementById("copiar");
  var comptador = document.getElementById("comptador");
  var errorText = document.getElementById("error-text");
  var estat = document.getElementById("estat");
  var avisos = document.getElementById("avisos");
  var ocupat = false;
  var rellotge = null;

  function nombre(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  }

  function format(plantilla, valors) {
    return plantilla.replace(/\{(\w+)\}/g, function (_, clau) { return valors[clau]; });
  }

  // Un missatge en la regió "status": es buida abans perquè, si es repetix
  // el mateix text, el lector de pantalla el torne a llegir.
  function anuncia(missatge) {
    estat.textContent = "";
    window.setTimeout(function () { estat.textContent = missatge; }, 50);
  }

  function avisa(missatge) {
    avisos.textContent = "";
    if (missatge) {
      var p = document.createElement("p");
      p.textContent = missatge;
      avisos.appendChild(p);
    }
  }

  function errorCamp(missatge) {
    var ids = ["ajuda-text", "comptador"];
    if (missatge) {
      errorText.textContent = missatge;
      errorText.hidden = false;
      text.setAttribute("aria-invalid", "true");
      ids.push("error-text");
    } else {
      errorText.textContent = "";
      errorText.hidden = true;
      text.removeAttribute("aria-invalid");
    }
    text.setAttribute("aria-describedby", ids.join(" "));
  }

  function actualitzaComptador() {
    var n = text.value.length;
    comptador.textContent = format(t.comptador, { n: nombre(n), maxim: nombre(maxim) });
    if (n > maxim) {
      errorCamp(format(t.massa_llarg, { n: nombre(n), maxim: nombre(maxim) }));
    } else if (text.getAttribute("aria-invalid") === "true" && errorText.dataset.tipus !== "buit") {
      errorCamp("");
    }
  }

  function actualitzaIdiomes() {
    var triat = desti.value;
    desti.innerHTML = "";
    dades.parells.forEach(function (p) {
      if (p.origen !== origen.value) { return; }
      var opcio = document.createElement("option");
      opcio.value = p.desti;
      opcio.textContent = p.nom_desti;
      opcio.selected = p.desti === triat;
      desti.appendChild(opcio);
    });
    text.lang = origen.value;
    eixida.lang = desti.value;
  }

  function posaOcupat(valor) {
    ocupat = valor;
    // aria-disabled (no disabled): el botó continua en l'ordre de tabulació.
    boto.setAttribute("aria-disabled", valor ? "true" : "false");
    if (rellotge) { window.clearTimeout(rellotge); rellotge = null; }
    if (valor) {
      rellotge = window.setTimeout(function () { anuncia(t.tardant); }, 4000);
    }
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    if (ocupat) { return; }
    avisa("");
    estat.textContent = "";
    if (!text.value.trim()) {
      errorText.dataset.tipus = "buit";
      errorCamp(t.text_buit);
      text.focus();
      return;
    }
    errorText.dataset.tipus = "";
    if (text.value.length > maxim) {
      actualitzaComptador();
      text.focus();
      return;
    }
    errorCamp("");
    posaOcupat(true);
    anuncia(t.traduint);
    fetch("/api/tradueix?idioma=" + encodeURIComponent(dades.idioma), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text.value, origen: origen.value, desti: desti.value })
    }).then(function (resposta) {
      return resposta.json().then(function (cos) { return { ok: resposta.ok, cos: cos }; });
    }).then(function (r) {
      posaOcupat(false);
      if (r.ok) {
        eixida.value = r.cos.traduccio;
        anuncia(t.traduccio_feta);
      } else {
        estat.textContent = "";
        avisa(r.cos.error || t.error_xarxa);
      }
    }).catch(function () {
      posaOcupat(false);
      estat.textContent = "";
      avisa(t.error_xarxa);
    });
  });

  copiar.hidden = false;
  copiar.addEventListener("click", function () {
    if (!eixida.value) { anuncia(t.res_per_copiar); return; }
    var feta = function () { anuncia(t.copiada); };
    var falla = function () {
      eixida.focus();
      eixida.select();
      anuncia(t.no_copiada);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(eixida.value).then(feta, falla);
    } else {
      falla();
    }
  });

  text.addEventListener("input", function () {
    if (errorText.dataset.tipus === "buit" && text.value.trim()) {
      errorText.dataset.tipus = "";
      errorCamp("");
    }
    actualitzaComptador();
  });
  origen.addEventListener("change", actualitzaIdiomes);
  desti.addEventListener("change", function () { eixida.lang = desti.value; });
})();
