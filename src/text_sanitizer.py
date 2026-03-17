import re
import unicodedata
import logging
from enum import Flag, auto

logger = logging.getLogger(__name__)

# Whitelist: всё, что НЕ входит — удаляется.
# @ добавлен для username'ов и контактов в тексте баннера.
SAFE_CHARS_RE = re.compile(
    r"[^a-zA-Zа-яА-ЯёЁ0-9\s\.,:;!\?\-\(\)\"'%₽$€₫+=/\\|№@]"
)

# Zero-width и variation selectors — убираем до whitelist-прохода.
# Отдельный EMOJI_RE убран: whitelist уже вычищает всё вне разрешённого
# диапазона, включая любые emoji-блоки. Два прохода были избыточны.
VARIATION_RE = re.compile(r'[\uFE00-\uFE0F]')   # полный диапазон variation selectors
ZERO_WIDTH_RE = re.compile(r'[\u200B-\u200D\u2060\uFEFF]')  # + BOM


class SanitizeFlag(Flag):
    """Причины изменения текста — для диагностики и логирования."""
    NONE            = 0
    NORMALIZED      = auto()   # типографские замены / NFC
    STRIPPED_CHARS  = auto()   # whitelist удалил символы
    SPACES_FIXED    = auto()   # нормализация пробелов
    LINES_TRUNCATED = auto()   # обрезка по max_lines
    LENGTH_TRUNCATED = auto()  # обрезка по max_length


def normalize_text(text: str) -> str:
    """NFC + замена типографских символов на ASCII-эквиваленты."""
    if not text:
        return text

    text = unicodedata.normalize("NFC", text)

    replacements = {
        "\u2014": "-",   # — длинное тире
        "\u2013": "-",   # – короткое тире
        "\u00AB": '"',   # «
        "\u00BB": '"',   # »
        "\u201E": '"',   # „
        "\u201C": '"',   # "
        "\u201D": '"',   # "
        "\u2018": "'",   # '
        "\u2019": "'",   # '
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    return text


def sanitize_text(
    text: str,
    max_length: int = 120,
    max_lines: int = 5,
    log_changes: bool = True,
) -> tuple[str, SanitizeFlag]:
    """
    Полная очистка текста для печати.

    Возвращает (clean_text, flags) — флаги описывают, что именно изменилось.

    Pipeline:
    1. normalize — NFC + типографские замены
    2. variation selectors / zero-width
    3. whitelist
    4. нормализация пробелов
    5. ограничение строк
    6. ограничение длины
    """
    if not text:
        return "", SanitizeFlag.NONE

    original = text
    flags = SanitizeFlag.NONE

    # 1. normalize
    text = normalize_text(text)
    if text != original:
        flags |= SanitizeFlag.NORMALIZED

    # 2. variation selectors + zero-width
    text = VARIATION_RE.sub('', text)
    text = ZERO_WIDTH_RE.sub('', text)

    # 3. whitelist
    before_whitelist = text
    text = SAFE_CHARS_RE.sub('', text)
    if text != before_whitelist:
        flags |= SanitizeFlag.STRIPPED_CHARS

    # 4. нормализация пробелов
    before_spaces = text
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{2,}', '\n', text).strip()
    if text != before_spaces:
        flags |= SanitizeFlag.SPACES_FIXED

    # 5. ограничение строк
    lines = text.split('\n')
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        text = '\n'.join(lines)
        flags |= SanitizeFlag.LINES_TRUNCATED

    # 6. ограничение длины
    if len(text) > max_length:
        text = text[:max_length].rstrip()
        flags |= SanitizeFlag.LENGTH_TRUNCATED

    # логирование: пишем только первые 80 символов каждой стороны
    if log_changes and flags != SanitizeFlag.NONE:
        logger.info(
            "[SANITIZE] flags=%s | before='%.80s' | after='%.80s'",
            flags,
            original,
            text,
        )

    return text, flags


# ---------------------------------------------------------------------------
# Интеграционный хелпер
# ---------------------------------------------------------------------------

def sanitize_and_notify(text: str, **kwargs) -> tuple[str, bool]:
    """
    Удобная обёртка для обработчика: возвращает (clean_text, was_modified).
    kwargs пробрасываются в sanitize_text (max_length, max_lines, log_changes).
    """
    clean, flags = sanitize_text(text, **kwargs)
    return clean, flags != SanitizeFlag.NONE


# ---------------------------------------------------------------------------
# Тесты
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    # trailing emoji
    result, _ = sanitize_text("Скидка 50% 🔥")
    assert result == "Скидка 50%", repr(result)

    # leading emoji → no leading space
    result, _ = sanitize_text("🚀 АКЦИЯ!!!")
    assert result == "АКЦИЯ!!!", repr(result)

    # типографские кавычки
    result, _ = sanitize_text("«Лучшее предложение»")
    assert result == '"Лучшее предложение"', repr(result)

    # @ сохраняется
    result, _ = sanitize_text("Пишите @manager")
    assert result == "Пишите @manager", repr(result)

    # zero-width не ломает слово
    result, _ = sanitize_text("Ски\u200Bдка")
    assert result == "Скидка", repr(result)

    # длинное тире → дефис
    result, _ = sanitize_text("10—20 штук")
    assert result == "10-20 штук", repr(result)

    # flags корректны
    _, flags = sanitize_text("Цена 100₽ 🎉")
    assert SanitizeFlag.STRIPPED_CHARS in flags

    # was_modified через хелпер
    _, modified = sanitize_and_notify("чистый текст 123")
    assert not modified

    print("✅ Все тесты пройдены")


if __name__ == "__main__":
    _run_tests()
