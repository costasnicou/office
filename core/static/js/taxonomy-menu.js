const initializeTaxonomyMenu = () => {
    const endpoint = document.body.dataset.taxonomyUrl;
    const deleteEndpoint = document.body.dataset.taxonomyDeleteUrl;
    const recordType = document.body.dataset.recordType;
    const modal = document.querySelector(".taxonomy-modal");
    const form = modal ? modal.querySelector(".taxonomy-modal-form") : null;

    if (!endpoint || !deleteEndpoint || !recordType || !modal || !form) {
        return;
    }
    if (modal.dataset.taxonomyInitialized === "true") {
        return;
    }
    modal.dataset.taxonomyInitialized = "true";

    const title = modal.querySelector("#taxonomy-modal-title");
    const context = modal.querySelector(".taxonomy-modal-context");
    const nameInput = form.elements.name;
    const kindInput = form.elements.kind;
    const categoryInput = form.elements.category_slug;
    const error = modal.querySelector(".taxonomy-modal-error");
    const submit = modal.querySelector(".taxonomy-modal-submit");
    const closeButton = modal.querySelector(".taxonomy-modal-close");
    const backdrop = modal.querySelector(".taxonomy-modal-backdrop");
    const csrfToken = form.elements.csrfmiddlewaretoken.value;
    const typeLabel = recordType === "centralpoint"
        ? "central point"
        : recordType;
    let returnFocus = null;

    const closeModal = () => {
        modal.hidden = true;
        form.reset();
        error.hidden = true;
        document.body.classList.remove("taxonomy-modal-open");
        if (returnFocus) {
            returnFocus.focus();
        }
    };

    const openModal = ({kind, categorySlug = "", categoryName = "", trigger}) => {
        returnFocus = trigger;
        kindInput.value = kind;
        categoryInput.value = categorySlug;
        title.textContent = `Create ${kind}`;
        context.textContent = kind === "subcategory"
            ? `Add a subcategory under “${categoryName}”.`
            : `Add a ${kind} for ${typeLabel} records.`;
        nameInput.placeholder = `${kind[0].toUpperCase()}${kind.slice(1)} name`;
        error.hidden = true;
        modal.hidden = false;
        document.body.classList.add("taxonomy-modal-open");
        nameInput.focus();
    };

    const createButton = (label, className, options) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `taxonomy-add-button ${className}`;
        button.innerHTML = `<span aria-hidden="true">+</span> ${label}`;
        button.addEventListener("click", () => {
            openModal({...options, trigger: button});
        });
        return button;
    };

    const wrapItemLink = (item, link) => {
        const row = document.createElement("div");
        row.className = "taxonomy-item-row";
        item.insertBefore(row, link);
        row.append(link);
        return row;
    };

    const addDeleteButton = (item, link, kind, slug, name) => {
        const row = wrapItemLink(item, link);
        const button = document.createElement("button");
        button.type = "button";
        button.className = "taxonomy-delete-button";
        button.setAttribute("aria-label", `Delete ${name}`);
        button.title = `Delete ${name}`;
        button.innerHTML = '<span aria-hidden="true">&times;</span>';
        button.addEventListener("click", async () => {
            if (!window.confirm(`Delete “${name}”?`)) {
                return;
            }

            button.disabled = true;
            const data = new FormData();
            data.append("csrfmiddlewaretoken", csrfToken);
            data.append("kind", kind);
            data.append("slug", slug);

            try {
                const response = await fetch(deleteEndpoint, {
                    method: "POST",
                    body: data,
                    headers: {"X-Requested-With": "XMLHttpRequest"},
                });
                const result = await response.json();
                if (!response.ok) {
                    throw new Error(result.error || "The item could not be deleted.");
                }
                window.location.assign(result.redirect_url);
            } catch (requestError) {
                window.alert(requestError.message);
                button.disabled = false;
            }
        });
        item.classList.add("taxonomy-item-with-delete");
        row.append(button);
    };

    const categories = document.querySelector(".categories");
    if (categories) {
        const categoryItems = [...categories.children].filter(
            (child) => child.tagName === "LI"
        );

        categoryItems.forEach((item) => {
            const categoryLink = [...item.children].find(
                (child) => child.tagName === "A"
            );
            if (!categoryLink) {
                return;
            }

            const pathParts = new URL(categoryLink.href).pathname
                .split("/")
                .filter(Boolean);
            const categorySlug = pathParts[pathParts.length - 1];
            const categoryName = categoryLink.textContent.trim();
            const isDefaultCategory = categorySlug === "uncategorized";
            let subcategoryList = [...item.children].find(
                (child) => child.classList &&
                    child.classList.contains("sub-categories")
            );
            if (!subcategoryList) {
                subcategoryList = document.createElement("ul");
                subcategoryList.className = "sub-categories";
                item.append(subcategoryList);
            }

            [...subcategoryList.children].forEach((subcategoryItem) => {
                const subcategoryLink = [...subcategoryItem.children].find(
                    (child) => child.tagName === "A"
                );
                if (!subcategoryLink) {
                    return;
                }
                const subcategoryParts = new URL(subcategoryLink.href).pathname
                    .split("/")
                    .filter(Boolean);
                addDeleteButton(
                    subcategoryItem,
                    subcategoryLink,
                    "subcategory",
                    subcategoryParts[subcategoryParts.length - 1],
                    subcategoryLink.textContent.trim(),
                );
            });

            if (isDefaultCategory) {
                item.classList.add("taxonomy-default-category");
                wrapItemLink(item, categoryLink);
            } else {
                addDeleteButton(
                    item, categoryLink, "category", categorySlug, categoryName,
                );
                const control = document.createElement("li");
                control.className = "taxonomy-control taxonomy-subcategory-control";
                control.append(createButton(
                    "Add subcategory",
                    "taxonomy-add-subcategory",
                    {kind: "subcategory", categorySlug, categoryName},
                ));
                subcategoryList.append(control);
            }
        });

        const categoryControl = document.createElement("li");
        categoryControl.className = "taxonomy-control taxonomy-category-control";
        categoryControl.append(createButton(
            categoryItems.length ? "Add category" : "Create your first category",
            "taxonomy-add-category",
            {kind: "category"},
        ));
        categories.append(categoryControl);
    }

    const tags = document.querySelector(".tags");
    if (tags) {
        const tagContainer = tags.querySelector(".tags-wraper") || tags;
        [...tagContainer.children].filter(
            (child) => child.tagName === "LI"
        ).forEach((tagItem) => {
            const tagLink = [...tagItem.children].find(
                (child) => child.tagName === "A"
            );
            if (!tagLink) {
                return;
            }
            const tagParts = new URL(tagLink.href).pathname
                .split("/")
                .filter(Boolean);
            addDeleteButton(
                tagItem,
                tagLink,
                "tag",
                tagParts[tagParts.length - 1],
                tagLink.textContent.trim(),
            );
        });
        const tagControl = document.createElement("li");
        tagControl.className = "taxonomy-control taxonomy-tag-control";
        tagControl.append(createButton(
            tagContainer.querySelector("li")
                ? "Add tag"
                : "Create your first tag",
            "taxonomy-add-tag",
            {kind: "tag"},
        ));
        tagContainer.append(tagControl);
    }

    closeButton.addEventListener("click", closeModal);
    backdrop.addEventListener("click", closeModal);
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !modal.hidden) {
            closeModal();
        }
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        error.hidden = true;
        submit.disabled = true;
        submit.textContent = "Creating…";

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                body: new FormData(form),
                headers: {"X-Requested-With": "XMLHttpRequest"},
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || "The item could not be created.");
            }
            window.location.reload();
        } catch (requestError) {
            error.textContent = requestError.message;
            error.hidden = false;
        } finally {
            submit.disabled = false;
            submit.textContent = "Create";
        }
    });
};

// Production asset optimizers can execute deferred scripts after DOMContentLoaded.
// Initialize immediately in that case instead of waiting for an event that has
// already fired.
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeTaxonomyMenu);
} else {
    initializeTaxonomyMenu();
}
