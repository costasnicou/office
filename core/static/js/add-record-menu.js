document.addEventListener("DOMContentLoaded", () => {
    const menu = document.querySelector(".add-record-menu");
    const button = menu?.querySelector(".add-record-button");
    const dropdown = menu?.querySelector(".add-record-dropdown");

    if (!menu || !button || !dropdown) {
        return;
    }

    const closeMenu = () => {
        dropdown.hidden = true;
        button.setAttribute("aria-expanded", "false");
    };

    button.addEventListener("click", () => {
        const willOpen = dropdown.hidden;
        dropdown.hidden = !willOpen;
        button.setAttribute("aria-expanded", String(willOpen));
    });

    document.addEventListener("click", (event) => {
        if (!menu.contains(event.target)) {
            closeMenu();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !dropdown.hidden) {
            closeMenu();
            button.focus();
        }
    });
});
