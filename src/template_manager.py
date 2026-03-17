"""
template_manager.py — загрузка и доступ к шаблонам Banner Bot.
Источник данных: templates.json (рядом с файлом или по явному пути).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path(__file__).parent / "templates.json"


class TemplateManager:
    def __init__(self, path: Path = _DEFAULT_PATH) -> None:
        self._path = path
        self._data: dict = {}
        self._load()

    # ------------------------------------------------------------------
    # Загрузка
    # ------------------------------------------------------------------

    def _load(self) -> None:
        try:
            with open(self._path, encoding="utf-8") as f:
                self._data = json.load(f)
            logger.info("templates.json загружен: %s", self._path)
        except FileNotFoundError:
            logger.error("templates.json не найден: %s", self._path)
            self._data = {"sizes": [], "slogans": [], "color_schemes": []}
        except json.JSONDecodeError as e:
            logger.error("Ошибка парсинга templates.json: %s", e)
            self._data = {"sizes": [], "slogans": [], "color_schemes": []}

    def reload(self) -> None:
        """Перезагрузить templates.json без перезапуска бота."""
        self._load()

    # ------------------------------------------------------------------
    # Размеры
    # ------------------------------------------------------------------

    def get_sizes(self) -> list[dict]:
        """Возвращает список всех размеров."""
        return self._data.get("sizes", [])

    def get_size_by_key(self, key: str) -> Optional[dict]:
        """Возвращает размер по ключу (например '3x6') или None."""
        for s in self.get_sizes():
            if s.get("key") == key:
                return s
        return None

    # ------------------------------------------------------------------
    # Слоганы
    # ------------------------------------------------------------------

    def get_slogan_categories(self) -> list[str]:
        """Возвращает список названий категорий слоганов."""
        return [c["category"] for c in self._data.get("slogans", [])]

    def get_slogans_by_category(self, category: str) -> list[str]:
        """Возвращает список слоганов для категории или пустой список."""
        for c in self._data.get("slogans", []):
            if c["category"] == category:
                return c.get("items", [])
        return []

    def get_all_slogans(self) -> list[dict]:
        """Возвращает полный список категорий со слоганами."""
        return self._data.get("slogans", [])

    # ------------------------------------------------------------------
    # Цветовые схемы
    # ------------------------------------------------------------------

    def get_color_schemes(self) -> list[dict]:
        """Возвращает список всех цветовых схем."""
        return self._data.get("color_schemes", [])

    def get_color_scheme_by_key(self, key: str) -> Optional[dict]:
        """Возвращает схему по ключу (например 'classic') или None."""
        for s in self.get_color_schemes():
            if s.get("key") == key:
                return s
        return None


# ------------------------------------------------------------------
# Синглтон — используется в handlers
# ------------------------------------------------------------------

_manager: Optional[TemplateManager] = None


def get_template_manager(path: Path = _DEFAULT_PATH) -> TemplateManager:
    """Возвращает синглтон TemplateManager. Инициализирует при первом вызове."""
    global _manager
    if _manager is None:
        _manager = TemplateManager(path)
    return _manager
