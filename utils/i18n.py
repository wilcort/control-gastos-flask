from flask import session
from translations import translations


def t(key):
    lang = session.get("lang", "es")
    return translations.get(lang, translations["es"]).get(key, key)