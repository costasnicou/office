document.addEventListener("DOMContentLoaded", () => {
    const menuToggle = document.querySelector(".menu-toggle");
    const sidebarToggle = document.querySelector(".sidebar-toggle");
    const sidebar = document.querySelector(".grid-left");

    if (!sidebarToggle || !sidebar) {
        return;
    }

    const closeSidebar = () => {
        document.body.classList.remove("sidebar-open");
        sidebarToggle.setAttribute("aria-expanded", "false");
    };

    sidebarToggle.addEventListener("click", () => {
        const isOpen = document.body.classList.toggle("sidebar-open");
        sidebarToggle.setAttribute("aria-expanded", String(isOpen));

        if (isOpen && menuToggle) {
            menuToggle.checked = false;
        }
    });

    if (menuToggle) {
        menuToggle.addEventListener("change", () => {
            if (menuToggle.checked) {
                closeSidebar();
            }
        });
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeSidebar();

            if (menuToggle) {
                menuToggle.checked = false;
            }
        }
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth > 1024) {
            closeSidebar();

            if (menuToggle) {
                menuToggle.checked = false;
            }
        }
    });
});
