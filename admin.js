// ===========================================================================
// admin.js
// Live search sa user table sa admin page.
// ===========================================================================

// Kuhaon ang search input pinaagi sa iyang ID.
var search = document.getElementById("user-search");

// Kung naa ang search box (admin page lang), ipadagan ang code.
if (search) {
  // Kuhaon ang tanang table rows (<tr>) sa tbody.
  // Array.prototype.slice.call(...) = himoon nga tinuod nga array para magamit ang forEach.
  var rows = Array.prototype.slice.call(document.querySelectorAll("tbody tr"));

  // Ang "No matching accounts." nga mensahe.
  var empty = document.getElementById("search-empty");

  // "input" event = modagan sa matag letra nga i-type.
  search.addEventListener("input", function () {
    // Kuhaon ang gi-type, tangtangon ang space, himoon lowercase.
    var term = search.value.trim().toLowerCase();
    var visible = 0; // Ihap sa mga row nga makita.

    rows.forEach(function (row) {
      // data-search = text sa row (name, username, email).
      // indexOf(term) !== -1 = kung naa ang gi-type nga text.
      var match = (row.dataset.search || "").indexOf(term) !== -1;

      // hidden = true kung dili match, false kung match.
      row.hidden = !match;

      if (match) visible += 1; // Dugang ang ihap kung makita.
    });

    // Ipakita ang "No matching accounts." kung walay match (visible === 0).
    if (empty) {
      empty.hidden = visible !== 0;
    }
  });
}
