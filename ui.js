// ===========================================================================
// ui.js
// Global nga JavaScript: confirmation dialogs ug copy-to-clipboard buttons.
// Kini kay ma-load sa tanang page (tan-awa ang base.html).
// ===========================================================================

// KONFIRMASYON sa form nga naay data-confirm attribute.
// querySelectorAll = pangitaa ang TANANG elemento nga mohaom sa selector.
document.querySelectorAll("form[data-confirm]").forEach(function (form) {
  // forEach = sa matag nakit-an nga form, ibutang ang event listener.
  form.addEventListener("submit", function (event) {
    // addEventListener("submit", ...) = modagan ni kung i-submit ang form.
    // window.confirm(...) = mogawas ang OK/Cancel dialog; mobalik og true/false.
    if (!window.confirm(form.dataset.confirm)) {
      // Kung gi-Cancel, pugngan ang pag-submit.
      event.preventDefault();
    }
  });
});

// COPY-TO-CLIPBOARD sa mga button nga naay data-copy attribute.
document.querySelectorAll("[data-copy]").forEach(function (button) {
  button.addEventListener("click", function () {
    // Kuhaon ang text nga kopyahon; "" kung wala.
    var text = button.dataset.copy || "";

    // Kini nga function kay modagan kung successful ang pagkopya.
    var done = function () {
      // Tipigan ang orihinal nga label para ibalik human sa 1.4 seconds.
      var original = button.dataset.label || button.textContent;
      button.dataset.label = original;
      button.textContent = "Copied!"; // Temporary nga mensahe.
      button.classList.add("copied"); // Idugang ang CSS class para sa green color.

      // setTimeout = modagan ang function human sa 1400 milliseconds.
      setTimeout(function () {
        button.textContent = original; // Ibalik ang orihinal nga text.
        button.classList.remove("copied"); // Tangtangon ang "copied" class.
      }, 1400);
    };

    // Modern nga paagi: Clipboard API (gikinahanglan og HTTPS o localhost).
    if (navigator.clipboard && window.isSecureContext) {
      // writeText = ilista ang text sa clipboard; .then = kung successful; .catch = kung fail.
      navigator.clipboard.writeText(text).then(done).catch(function () {});
      return; // Human na, ayaw na padayon sa ubos.
    }

    // Fallback (karaan nga paagi) kung walay Clipboard API.
    var area = document.createElement("textarea"); // Himoon og temporary nga textarea.
    area.value = text; // Ibutang ang text.
    area.style.position = "fixed"; // Aron dili makaguba sa layout.
    area.style.opacity = "0"; // Itago (pero naa gihapon sa page).
    document.body.appendChild(area); // Idugang sa page.
    area.select(); // Pilia ang tanang text.

    try {
      document.execCommand("copy"); // Karaang command para pagkopya.
      done(); // Ipakita ang "Copied!".
    } finally {
      // "finally" = modagan ni bisan successful o naay error.
      document.body.removeChild(area); // Tangtangon ang temporary nga textarea.
    }
  });
});
