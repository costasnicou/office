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

    function translationCookieDomains() {
        var hostname = window.location.hostname.replace(/^www\./, "");
        var domains = ["", hostname, "." + hostname];
        var parts = hostname.split(".");

        // Google Translate commonly stores its preference on the parent domain
        // (for example .costasnicou.com from backoffice.costasnicou.com).
        if (parts.length > 2 && !/^\d+\.\d+\.\d+\.\d+$/.test(hostname)) {
            domains.push("." + parts.slice(-2).join("."));
        }
        return domains;
    }

    function writeTranslationCookie(value, domain) {
        var cookie = "googtrans=" + value + ";path=/;SameSite=Lax";
        document.cookie = domain ? cookie + ";domain=" + domain : cookie;
    }

    function clearTranslationCookies() {
        var expired = ";path=/;expires=Thu, 01 Jan 1970 00:00:00 GMT;Max-Age=0;SameSite=Lax";
        translationCookieDomains().forEach(function (domain) {
            document.cookie = "googtrans=" + expired +
                (domain ? ";domain=" + domain : "");
        });
    }

    function persistLanguage(language) {
        clearTranslationCookies();
        if (language === "el") {
            translationCookieDomains().forEach(function (domain) {
                writeTranslationCookie("/en/el", domain);
            });
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
