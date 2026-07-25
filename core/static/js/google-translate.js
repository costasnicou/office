(function () {
    "use strict";

    var selectorObserver = null;

    function translatedLanguage() {
        var match = document.cookie.match(/(?:^|;\s*)googtrans=\/en\/([^;]+)/);
        return match && match[1] === "el" ? "el" : "en";
    }

    function setDocumentLanguage(language) {
        document.documentElement.lang = language === "el" ? "el" : "en";
    }

    function updateFlagState(language) {
        document.querySelectorAll(".language-flag").forEach(function (button) {
            var isActive = button.dataset.language === language;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-pressed", String(isActive));
        });
    }

    function persistLanguage(language) {
        var value = language === "el" ? "/en/el" : "/en/en";
        var cookie = "googtrans=" + value + ";path=/;SameSite=Lax";
        document.cookie = cookie;

        // Google may create its cookie for the root domain on production.
        // Write the same preference there so a stale domain cookie cannot win.
        var rootDomain = window.location.hostname.replace(/^www\./, "");
        if (rootDomain.includes(".") && !/^\d+\.\d+\.\d+\.\d+$/.test(rootDomain)) {
            document.cookie = cookie + ";domain=." + rootDomain;
        }
    }

    function bindFlagButtons() {
        document.querySelectorAll(".language-flag").forEach(function (button) {
            if (button.dataset.languageBound === "true") {
                return;
            }
            button.dataset.languageBound = "true";
            button.addEventListener("click", function () {
                var language = button.dataset.language;
                persistLanguage(language);
                setDocumentLanguage(language);
                updateFlagState(language);
                window.location.reload();
            });
        });
    }

    function connectGoogleSelector() {
        var selector = document.querySelector(".goog-te-combo");
        if (!selector) {
            return false;
        }

        if (selector.dataset.languageBound !== "true") {
            selector.dataset.languageBound = "true";
            selector.setAttribute("aria-label", "Choose website language");
            selector.addEventListener("change", function () {
                setDocumentLanguage(selector.value);
                updateFlagState(selector.value);
            });
        }

        if (selectorObserver) {
            selectorObserver.disconnect();
            selectorObserver = null;
        }
        return true;
    }

    function watchForGoogleSelector() {
        if (connectGoogleSelector() || selectorObserver) {
            return;
        }
        selectorObserver = new MutationObserver(connectGoogleSelector);
        selectorObserver.observe(document.documentElement, {
            childList: true,
            subtree: true
        });
    }

    window.googleTranslateElementInit = function () {
        new window.google.translate.TranslateElement({
            pageLanguage: "en",
            includedLanguages: "en,el",
            autoDisplay: false
        }, "google_translate_element");

        setDocumentLanguage(translatedLanguage());
        watchForGoogleSelector();
    };

    var initialLanguage = translatedLanguage();
    setDocumentLanguage(initialLanguage);
    updateFlagState(initialLanguage);
    bindFlagButtons();
    watchForGoogleSelector();
}());
