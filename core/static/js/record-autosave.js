(function () {
    "use strict";

    const form = document.querySelector(".record-form[data-autosave-url]");
    const status = document.querySelector(".autosave-status");
    if (!form || !status) return;

    let dirty = false;
    let saving = false;
    let submitting = false;
    let autosaveFailed = false;

    function markDirty() {
        if (submitting) return;
        dirty = true;
    }

    form.addEventListener("input", markDirty);
    form.addEventListener("change", markDirty);

    function connectEditors() {
        form.querySelectorAll(".django_ckeditor_5").forEach(function (textarea) {
            if (textarea.dataset.autosaveConnected === "1") return;
            const connect = function (editor) {
                editor.model.document.on("change:data", markDirty);
                textarea.dataset.autosaveConnected = "1";
            };
            if (window.editors && window.editors[textarea.id]) {
                connect(window.editors[textarea.id]);
            } else if (window.ckeditorRegisterCallback) {
                window.ckeditorRegisterCallback(textarea.id, connect);
            }
        });
    }

    connectEditors();
    document.addEventListener("DOMContentLoaded", connectEditors);

    async function autosave() {
        if (!dirty || saving || submitting) return;
        saving = true;
        dirty = false;

        const data = new FormData(form);
        data.delete("action");
        data.append("record_slug", form.dataset.recordSlug || "");

        try {
            const response = await fetch(form.dataset.autosaveUrl, {
                method: "POST",
                body: data,
                credentials: "same-origin",
                headers: {"X-Requested-With": "XMLHttpRequest"},
            });
            if (!response.ok) throw new Error("Autosave failed");
            if (autosaveFailed) {
                status.textContent = "Draft saved successfully after retry.";
                status.classList.add("is-saved");
                status.classList.remove("has-error");
                autosaveFailed = false;
            }
        } catch (error) {
            dirty = true;
            autosaveFailed = true;
            status.textContent = "Draft could not be saved. Retrying…";
            status.classList.add("has-error");
            status.classList.remove("is-saved");
        } finally {
            saving = false;
        }
    }

    window.setInterval(autosave, 1000);
    form.addEventListener("submit", function () {
        submitting = true;
    });
})();
