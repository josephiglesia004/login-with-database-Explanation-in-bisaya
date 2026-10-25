// ===========================================================================
// auth.js
// Nagkontrol sa "Show/Hide" button sa password fields.
// Gigamit ni sa login, register, ug settings pages.
// ===========================================================================

// Pangitaa ang tanang button nga naay class="toggle".
document.querySelectorAll(".toggle").forEach(function (button) {
  // Sa matag toggle button, ibutang ang click event.
  button.addEventListener("click", function () {
    // data-target = ID sa input nga gusto ipakita/ipahipi.
    var input = document.getElementById(button.dataset.target);
    if (!input) return; // Kung wala ang input, hunong.

    // Kung "password" karon, gusto ipakita; kung "text", gusto ipahipi.
    var show = input.type === "password";

    // Ternary operator: condition ? kung-true : kung-false.
    input.type = show ? "text" : "password";

    // Ilisan ang text sa button: "Hide" o "Show".
    button.textContent = show ? "Hide" : "Show";

    // Para sa screen readers (accessibility).
    button.setAttribute("aria-label", show ? "Hide password" : "Show password");
  });
});
