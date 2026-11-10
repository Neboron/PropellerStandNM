"""Application language and explicit, state-preserving bindings for Qt text.

English source strings are stable catalog keys. Bind only presentation text;
serial commands, numeric values and data-file formats must never be translated.
"""

import json
from pathlib import Path

from PyQt5.QtCore import QObject, QSettings, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication


LANGUAGES = (("et", "Eesti"), ("en", "English"))
DEFAULT_LANGUAGE = "et"


class LanguageManager(QObject):
    changed = pyqtSignal()

    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings(
            "EAVA", "PropellerMeasuringDevice"
        )
        catalog_path = Path(__file__).parent / "translations" / "et.json"
        with catalog_path.open(encoding="utf-8") as catalog:
            self._estonian = json.load(catalog)
        saved = self.settings.value("ui/language", DEFAULT_LANGUAGE)
        self.language = (
            saved if isinstance(saved, str) and saved in dict(LANGUAGES)
            else DEFAULT_LANGUAGE
        )

    def set_language(self, language):
        if language not in dict(LANGUAGES):
            raise ValueError(f"Unsupported interface language: {language}")
        if language == self.language:
            return
        self.language = language
        self.settings.setValue("ui/language", language)
        self.settings.sync()
        self.changed.emit()

    def translate(self, source, **values):
        text = self._estonian.get(source, source) if self.language == "et" else source
        return text.format(**values) if values else text


def language_manager():
    """Keep one manager alive for the lifetime of the QApplication."""
    app = QApplication.instance()
    if app is None:
        raise RuntimeError("Create QApplication before using GUI translations")
    if not hasattr(app, "_language_manager"):
        app._language_manager = LanguageManager(app)
    return app._language_manager


def tr(source, **values):
    """Translate transient text, such as a file dialog caption or message."""
    return language_manager().translate(source, **values)


class _TextBinding(QObject):
    def __init__(self, target, property_name):
        # Qt ownership also disconnects our slot when the target is destroyed.
        super().__init__(target)
        self.property_name = property_name
        language_manager().changed.connect(self.refresh)

    @pyqtSlot()
    def refresh(self):
        self.parent().setProperty(self.property_name, tr(self.source, **self.values))


def bind_text(target, source, *, property_name="text", **values):
    """Set text and refresh it on language changes, returning the same object.

    Call again for status changes; the latest source and format values replace
    the previous binding. No widgets, connections, values or timers are rebuilt.
    Use setText directly for numeric readouts that do not require translation.
    """
    if not hasattr(target, "_translation_bindings"):
        target._translation_bindings = {}
    binding = target._translation_bindings.get(property_name)
    if binding is None:
        binding = _TextBinding(target, property_name)
        target._translation_bindings[property_name] = binding
    binding.source = source
    binding.values = values
    binding.refresh()
    return target
