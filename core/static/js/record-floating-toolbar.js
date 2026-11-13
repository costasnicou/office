(function () {
    "use strict";

    const form = document.querySelector(".record-form");
    if (!form) return;
    const connected = new WeakSet();

    function connect(editor) {
        if (!editor || connected.has(editor)) return;
        const toolbar = editor.ui.view.toolbar.element;
        const editable = editor.ui.getEditableElement();
        if (!toolbar || !editable) return;
        connected.add(editor);
        const host = toolbar.parentElement;
        const previousMinHeight = host.style.minHeight;
        let selectionRect = null;
        let frame = null;
        let dragging = false;
        let dismissed = false;

        function reset() {
            toolbar.classList.remove("record-selection-toolbar");
            for (const property of ["left", "top", "width", "max-width"]) {
                toolbar.style.removeProperty(property);
            }
            host.style.minHeight = previousMinHeight;
        }

        function emptyCaretRect(range) {
            let node = range.startContainer;
            if (node.nodeType === Node.ELEMENT_NODE) {
                node = node.childNodes[range.startOffset] || node;
            }
            const element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
            const block = element?.closest("p, li, h1, h2, h3, h4, h5, h6, blockquote, pre, td, th") || editable;
            if (!editable.contains(block)) return null;
            const bounds = block.getBoundingClientRect();
            const style = window.getComputedStyle(block);
            const number = value => parseFloat(value) || 0;
            const lineHeight = number(style.lineHeight) || number(style.fontSize) * 1.5 || 20;
            let left = bounds.left + number(style.borderLeftWidth) + number(style.paddingLeft);
            if (style.direction === "rtl" || style.textAlign === "right") {
                left = bounds.right - number(style.borderRightWidth) - number(style.paddingRight);
            } else if (style.textAlign === "center") {
                left = (bounds.left + bounds.right) / 2;
            }
            const top = bounds.top + number(style.borderTopWidth) + number(style.paddingTop);
            return {left, right: left, top, bottom: top + lineHeight};
        }

        function update() {
            frame = null;
            if (dragging) return;
            if (dismissed || editor.isReadOnly || !editor.ui.focusTracker.isFocused) {
                selectionRect = null;
                reset();
                return;
            }
            const selection = window.getSelection();
            if (selection && selection.rangeCount) {
                const range = selection.getRangeAt(0);
                if (editable.contains(range.startContainer) && editable.contains(range.endContainer)) {
                    const rects = [...range.getClientRects()].filter(rect => rect.height &&
                        (selection.isCollapsed || rect.width));
                    const backwards = selection.anchorNode === range.endContainer &&
                        selection.anchorOffset === range.endOffset;
                    const rect = backwards ? rects[0] : rects[rects.length - 1];
                    if (rect) {
                        selectionRect = {left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom};
                    } else if (selection.isCollapsed) {
                        // Empty paragraphs can have a caret without a measurable DOM range.
                        selectionRect = emptyCaretRect(range);
                    } else {
                        selectionRect = null;
                    }
                }
            }
            if (!selectionRect) {
                reset();
                return;
            }
            const viewport = window.visualViewport;
            const viewportLeft = viewport ? viewport.offsetLeft : 0;
            const header = document.querySelector(".header");
            const headerBottom = header ? header.getBoundingClientRect().bottom : 0;
            const viewportTop = Math.max(viewport ? viewport.offsetTop : 0, headerBottom);
            const viewportWidth = viewport ? viewport.width : window.innerWidth;
            const viewportHeight = viewport ? viewport.height : window.innerHeight;
            const viewportBottom = (viewport ? viewport.offsetTop : 0) + viewportHeight;
            const margin = 8;
            if (selectionRect.bottom < viewportTop || selectionRect.top > viewportBottom) {
                reset();
                return;
            }
            if (!toolbar.classList.contains("record-selection-toolbar")) {
                host.style.minHeight = `${host.getBoundingClientRect().height}px`;
                toolbar.classList.add("record-selection-toolbar");
            }
            toolbar.style.maxWidth = `${viewportWidth - margin * 2}px`;
            const bounds = toolbar.getBoundingClientRect();
            const left = (selectionRect.left + selectionRect.right - bounds.width) / 2;
            const above = selectionRect.top - bounds.height - margin;
            const top = above >= viewportTop + margin ? above : selectionRect.bottom + margin;
            toolbar.style.left = `${Math.max(viewportLeft + margin, Math.min(left, viewportLeft + viewportWidth - bounds.width - margin))}px`;
            toolbar.style.top = `${Math.max(viewportTop + margin, Math.min(top, viewportBottom - bounds.height - margin))}px`;
        }

        function schedule() {
            if (frame === null) frame = window.requestAnimationFrame(update);
        }
        function selectionChanged() {
            schedule();
        }
        function pointerDown(event) {
            if (editable.contains(event.target)) {
                dragging = true;
                dismissed = false;
                reset();
            }
        }
        function pointerUp() {
            dragging = false;
            schedule();
        }
        function keyDown(event) {
            if (editor.ui.focusTracker.isFocused || editable.contains(event.target)) {
                dismissed = true;
                reset();
            }
        }

        // Typing, shortcuts, and caret movement keep the float dismissed until
        // the next pointer interaction in this editor.
        editable.addEventListener("beforeinput", keyDown);
        editable.addEventListener("compositionstart", keyDown);
        document.addEventListener("selectionchange", schedule);
        document.addEventListener("pointerdown", pointerDown);
        document.addEventListener("pointerup", pointerUp);
        document.addEventListener("pointercancel", pointerUp);
        document.addEventListener("keydown", keyDown);
        window.addEventListener("scroll", schedule, true);
        window.addEventListener("resize", schedule);
        window.visualViewport?.addEventListener("resize", schedule);
        window.visualViewport?.addEventListener("scroll", schedule);
        editor.model.document.selection.on("change:range", selectionChanged);
        editor.ui.focusTracker.on("change:isFocused", schedule);
        editor.on("change:isReadOnly", schedule);
        editor.on("destroy", () => {
            if (frame !== null) window.cancelAnimationFrame(frame);
            reset();
            editable.removeEventListener("beforeinput", keyDown);
            editable.removeEventListener("compositionstart", keyDown);
            document.removeEventListener("selectionchange", schedule);
            document.removeEventListener("pointerdown", pointerDown);
            document.removeEventListener("pointerup", pointerUp);
            document.removeEventListener("pointercancel", pointerUp);
            document.removeEventListener("keydown", keyDown);
            window.removeEventListener("scroll", schedule, true);
            window.removeEventListener("resize", schedule);
            window.visualViewport?.removeEventListener("resize", schedule);
            window.visualViewport?.removeEventListener("scroll", schedule);
        });
    }

    form.addEventListener("record-editor-ready", event => connect(event.detail.editor));
    for (const textarea of form.querySelectorAll(".django_ckeditor_5")) {
        connect(window.editors?.[textarea.id]);
    }
})();
