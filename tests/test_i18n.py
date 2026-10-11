import i18n


class TestLanguageSelection:
    def test_accept_language_sets_session(self, client):
        resp = client.get("/", headers={"Accept-Language": "de-DE,de;q=0.9,en;q=0.8"})
        assert resp.status_code == 200
        with client.session_transaction() as sess:
            assert sess["lang"] == "de"

    def test_set_lang_route_updates_session(self, client):
        client.get("/")
        resp = client.get("/set-lang/en", follow_redirects=False)
        assert resp.status_code == 302
        with client.session_transaction() as sess:
            assert sess["lang"] == "en"

    def test_unknown_accept_language_falls_back_to_portuguese(self, client):
        client.get("/", headers={"Accept-Language": "fr-FR,fr;q=0.9"})
        with client.session_transaction() as sess:
            assert sess["lang"] == "pt"


class TestTranslations:
    def test_known_common_key_exists_in_all_languages(self):
        for lang in i18n.SUPPORTED_LANGS:
            assert i18n.t("common.nav.home", lang)

    def test_unknown_key_returns_key(self):
        assert i18n.t("missing.key.example", "en") == "missing.key.example"

    def test_unknown_lang_falls_back_to_default(self):
        assert i18n.t("common.nav.home", "xx") == i18n.t("common.nav.home", "pt")


def _flatten(data, prefix=""):
    keys = set()
    for key, value in data.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            keys |= _flatten(value, f"{path}.")
        else:
            keys.add(path)
    return keys


class TestCatalogParity:
    def test_every_language_defines_the_same_keys(self):
        reference = _flatten(i18n.get_translations(i18n.DEFAULT_LANG))
        for lang in i18n.SUPPORTED_LANGS:
            keys = _flatten(i18n.get_translations(lang))
            assert keys == reference, (
                f"{lang}: missing {sorted(reference - keys)[:5]}, "
                f"extra {sorted(keys - reference)[:5]}"
            )
