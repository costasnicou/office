(function () {
    "use strict";

    function translatedLanguage() {
        var match = document.cookie.match(/(?:^|;\s*)googtrans=\/en\/([^;]+)/);
        return match && match[1] === "el" ? "el" : "en";
    }

    function setDocumentLanguage(language) {
        document.documentElement.lang = language === "el" ? "el" : "en";
    }

    window.googleTranslateElementInit = function () {
        new window.google.translate.TranslateElement({
            pageLanguage: "en",
            includedLanguages: "en,el",
            autoDisplay: false
        }, "google_translate_element");

        setDocumentLanguage(translatedLanguage());

        var selector = document.querySelector(".goog-te-combo");
        if (selector) {
            selector.setAttribute("aria-label", "Choose website language");
            selector.addEventListener("change", function () {
                setDocumentLanguage(selector.value);
            });
        }
    };

    setDocumentLanguage(translatedLanguage());
}());
