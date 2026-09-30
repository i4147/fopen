from __future__ import annotations

import ast
import errno
import hashlib
import os
import platform
import random
import secrets
import shutil
import subprocess
import threading
import time
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from glob import glob
from typing import Optional, Union

try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    relativedelta = None


_PACKAGE_NAME: str = "WithOpen"
_WRITE_COPIES: int = 3
_CORRUPT_MARKER: list = ["!!<<CORRUPT_DATA_BLOCK::UNRECOVERABLE::ID#e3f7!!>>"]
_ACTIVE_PACKAGE_FILE: str = f".{_PACKAGE_NAME}_active_package"
_WRITE_LOCK_FILE: str = f".{_PACKAGE_NAME}_write_lock"
_CONSOLE_TAG_FILE: str = "__console_987812919120.txt"
_CONTROL_PANEL_FILE: str = "__control_panel_987812919120"
_HIDE_ALERT_FILE: str = "__hide_new_alert_987812919120.txt"
_MAX_QUEUE_LEN: int = 100000
_QUEUE_DONE_AGE: int = 2
_ACTIVE_AGE_LIMIT: int = 30


def _cwd() -> str:
    return os.getcwd()


def _main_folder() -> str:
    return os.path.join(_cwd(), _PACKAGE_NAME)


def _terminal_width() -> int:
    return shutil.get_terminal_size().columns


def _new_session_id() -> int:
    timestamp: float = time.time()
    uname = platform.uname()
    entropy: bytes = secrets.token_bytes(64)
    payload: str = f"{timestamp}{uname}{entropy.hex()}"
    digest: str = hashlib.sha256(payload.encode()).hexdigest()
    return secrets.randbelow(int(digest, 16))


def wipe_screen(clear_first: bool = True, delay: float = 0.1) -> None:
    try:
        if clear_first:
            time.sleep(delay)
        os.system("clear")
    except Exception as exc:
        print(f"Clear output failed:{exc}")


def wipe_screen_soft(clear_first: bool = True, delay: float = 0.1) -> None:
    try:
        if clear_first:
            time.sleep(delay)
        os.system("clear")
    except Exception:
        if clear_first:
            time.sleep(delay)
        os.system("clear")


def align_text(text: str, align: Optional[Union[str, int]] = None) -> str:
    width: int = _terminal_width()
    if align is None:
        align = "left"
    if isinstance(align, str):
        align = align.strip()
        if align.lstrip("-").isdigit():
            align = int(align)
    if isinstance(align, int):
        if align >= 0:
            return " " * align + text
        pad = max(0, width + align - len(text))
        return " " * pad + text
    if isinstance(align, str):
        align = align.lower()
        if align == "left":
            return text
        if align == "center":
            return text.center(width)
        if align == "right":
            return text.rjust(width)
    return text


_ANSI_COLORS: dict = {
    "reset": "\x1b[0m",
    "black": "\x1b[30m",
    "red": "\x1b[31m",
    "green": "\x1b[32m",
    "yellow": "\x1b[33m",
    "blue": "\x1b[34m",
    "magenta": "\x1b[35m",
    "cyan": "\x1b[36m",
    "white": "\x1b[37m",
}
_ANSI_STYLES: dict = {
    "bold": "\x1b[1m",
    "underline": "\x1b[4m",
    "italic": "\x1b[3m",
    "reset": "\x1b[0m",
}


def colorize(
    text: str,
    color: Optional[str] = None,
    rgb: Optional[tuple] = None,
    bold: bool = False,
    underline: bool = False,
    italic: bool = False,
) -> str:
    prefix: list = []
    if rgb:
        r, g, b = rgb
        prefix.append(f"\x1b[38;2;{r};{g};{b}m")
    elif color and color in _ANSI_COLORS:
        prefix.append(_ANSI_COLORS[color])
    if bold:
        prefix.append(_ANSI_STYLES["bold"])
    if underline:
        prefix.append(_ANSI_STYLES["underline"])
    if italic:
        prefix.append(_ANSI_STYLES["italic"])
    start: str = "".join(prefix)
    end: str = _ANSI_STYLES["reset"]
    return f"{start}{text}{end}"


def stylize(
    text: str,
    color: Optional[str] = None,
    rgb: Optional[tuple] = None,
    bold: bool = False,
    underline: bool = False,
    italic: bool = False,
    highlights: Optional[list] = None,
) -> str:
    if color or rgb or bold or underline or italic:
        return colorize(text, color=color, rgb=rgb, bold=bold, underline=underline, italic=italic)
    if not highlights:
        return text
    marks: list = []
    for item in highlights:
        idx = text.find(item["text"])
        if idx != -1:
            marks.append((idx, idx + len(item["text"]), item))
    marks.sort(key=lambda x: x[0])
    parts: list = []
    cursor: int = 0
    for start, end, item in marks:
        if start >= cursor:
            parts.append(text[cursor:start])
            colored = colorize(
                text[start:end],
                color=item.get("color"),
                rgb=item.get("rgb"),
                bold=item.get("bold", False),
                underline=item.get("underline", False),
                italic=item.get("italic", False),
            )
            parts.append(colored)
            cursor = end
    parts.append(text[cursor:])
    return "".join(parts)


def loop_progress(
    current: int,
    total: int,
    as_percent: bool = True,
    with_percent: bool = True,
    precision: int = 0,
    mode_: str = "both",
    reverse: bool = False,
) -> str:
    ratio = 0 if total == 0 else current / total
    if reverse:
        ratio = 1 - ratio
    count = f"{current}/{total}"
    if as_percent:
        ratio *= 100
    if with_percent:
        if precision == 0:
            pct = f"{round(ratio)}%"
        else:
            pct = f"{round(ratio, precision)}%"
    else:
        pct = f"{ratio:.{precision}f}%"
    if mode_ == "count":
        return f"⟳ [ {count} ]"
    if mode_ == "percentage":
        return f"⟳ [ {pct} ]"
    return f"⟳ [ {count}-{pct} ]"


def future_datetime(amount: int, unit: str = "s", with_date: bool = False, use_ampm: bool = True) -> str:
    now: datetime = datetime.now()
    unit = unit.lower()
    if unit == "s":
        target = now + timedelta(seconds=amount)
        delta = timedelta(seconds=amount)
    elif unit == "m":
        target = now + timedelta(minutes=amount)
        delta = timedelta(minutes=amount)
    elif unit == "h":
        target = now + timedelta(hours=amount)
        delta = timedelta(hours=amount)
    elif unit == "d":
        target = now + timedelta(days=amount)
        delta = timedelta(days=amount)
    elif unit == "mo":
        if relativedelta is None:
            raise ImportError("dateutil is required for month units")
        target = now + relativedelta(months=amount)
        delta = timedelta(days=30 * amount)
    elif unit == "y":
        if relativedelta is None:
            raise ImportError("dateutil is required for year units")
        target = now + relativedelta(years=amount)
        delta = timedelta(days=365 * amount)
    else:
        raise ValueError(f"Unsupported time unit:{unit}")
    if with_date or delta >= timedelta(days=1):
        fmt = "%Y-%m-%d%I:%M:%S%p" if use_ampm else "%Y-%m-%d%H:%M:%S"
    else:
        fmt = "%I:%M:%S%p" if use_ampm else "%H:%M:%S"
    return target.strftime(fmt)


_DATE_FORMATS: list = [
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%m/%d/%Y%H:%M:%S",
    "%m/%d/%Y%H:%M",
    "%m/%d/%Y",
    "%m-%d-%Y%H:%M:%S",
    "%m-%d-%Y",
    "%d/%m/%Y%H:%M:%S",
    "%d/%m/%Y%H:%M",
    "%d/%m/%Y",
    "%d-%m-%Y%H:%M:%S",
    "%d-%m-%Y",
    "%Y/%m/%d%H:%M:%S",
    "%Y/%m/%d",
    "%d.%m.%Y%H:%M:%S",
    "%d.%m.%Y",
    "%Y-%m-%d%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S%z",
]


def parse_date_string(value: str) -> datetime:
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date string:{value}")


def time_ago(
    when: Union[str, datetime],
    compact: bool = True,
    full_words: bool = False,
    hour_scale: bool = False,
) -> str:
    def _fmt(unit: str, value: float) -> str:
        if full_words:
            plural = "" if value == 1 else "s"
            return f"{value} {unit}{plural}"
        if compact:
            return f"{value}{unit[0]}"
        return f"{value} {unit}"

    if isinstance(when, str):
        try:
            when = parse_date_string(when)
        except Exception as exc:
            raise ValueError(f"Invalid date string format:{when}") from exc
    if not isinstance(when, datetime):
        raise TypeError("Input must be a datetime object or a valid string")
    now: datetime = datetime.now()
    delta = when - now
    total_seconds = delta.total_seconds()
    future = total_seconds > 0
    total_seconds = abs(total_seconds)
    if total_seconds < 5:
        return "just now"
    days = int(total_seconds // 86400)
    rem = total_seconds % 86400
    hours = int(rem // 3600)
    rem %= 3600
    minutes = int(rem // 60)
    seconds = int(rem % 60)
    if hour_scale:
        if days >= 1:
            value = round(days + (hours * 3600 + minutes * 60 + seconds) / 86400, 1)
            unit = "day" if value == 1 else "days"
            text = f"{value} {unit}" if full_words else f"{value}d"
        else:
            value = round(hours + (minutes * 60 + seconds) / 3600, 1)
            unit = "hour" if value == 1 else "hours"
            text = f"{value} {unit}" if full_words else f"{value}h"
    else:
        pieces: list = []
        if days > 0:
            pieces.append(_fmt("day", days))
        if hours > 0:
            pieces.append(_fmt("hour", hours))
        if minutes > 0:
            pieces.append(_fmt("min", minutes))
        if not pieces and seconds > 0:
            pieces.append(_fmt("sec", seconds))
        text = ",".join(pieces) if not compact else " ".join(pieces)
    return f"in {text} time" if future else f"{text} ago"


def time_between(
    start: Union[str, datetime],
    end: Union[str, datetime],
    compact: bool = True,
    full_words: bool = False,
    hour_scale: bool = False,
) -> str:
    if isinstance(start, str):
        try:
            start = parse_date_string(start)
        except Exception as exc:
            raise ValueError(f"Invalid start_time string format:{start}") from exc
    if isinstance(end, str):
        try:
            end = parse_date_string(end)
        except Exception as exc:
            raise ValueError(f"Invalid end_time string format:{end}") from exc
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        raise TypeError("Inputs must be datetime objects or valid date strings")
    if start > end:
        start, end = end, start

    def _strip(value: str) -> str:
        return value.replace(" ago", "").replace("in ", "").replace(" time", "")

    now: datetime = datetime.now()
    sa = (start - now).total_seconds()
    sb = (end - now).total_seconds()
    if sa > 0 and sb > 0:
        a_txt = _strip(time_ago(start, compact=compact, full_words=full_words, hour_scale=hour_scale))
        b_txt = _strip(time_ago(end, compact=compact, full_words=full_words, hour_scale=hour_scale))
        return f"in {a_txt}-{b_txt} time"
    if sa < 0 and sb < 0:
        a_txt = _strip(time_ago(start, compact=compact, full_words=full_words, hour_scale=hour_scale))
        b_txt = _strip(time_ago(end, compact=compact, full_words=full_words, hour_scale=hour_scale))
        return f"{a_txt}-{b_txt} ago"
    raise ValueError("Both times must be either in the past or in the future (no crossing now)")


def _stamp_path_for(txt_name: str) -> str:
    folder, _, _ = _resolve_txt_path_and_validation(txt_name)
    return os.path.join(folder, f"{txt_name}_snapshot.txt")


def _read_stamp(stamp_file: str) -> Optional[str]:
    if not os.path.exists(stamp_file):
        return None
    with open(stamp_file, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith("---["):
                continue
            return line
    return None


def _write_stamp(stamp_file: str, value: str) -> None:
    folder = os.path.dirname(stamp_file)
    name = os.path.basename(stamp_file)
    if name.endswith(".txt"):
        name = name[:-4]
    write_all_files([value], folder, name, single_write=True)


def _check_date_change(stamp_file: str, unit: str, gap: float = 1, day_start_hour: int = 0) -> str:
    now: datetime = datetime.now(timezone.utc)
    stamp: str = now.strftime("%Y%m%d%H%M%S")
    last = _read_stamp(stamp_file)
    if last is None:
        _write_stamp(stamp_file, stamp)
        return "A"
    try:
        last_dt: datetime = datetime.strptime(last, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        _write_stamp(stamp_file, stamp)
        return "A"
    units: dict = {
        "s": 1,
        "second": 1,
        "m": 60,
        "min": 60,
        "minute": 60,
        "h": 3600,
        "hour": 3600,
        "d": 86400,
        "day": 86400,
        "mo": 2592000,
        "month": 2592000,
        "y": 31536000,
        "year": 31536000,
    }
    key = unit.lower()
    seconds = units.get(key)
    if seconds is None:
        return "Invalid date_type. Use 's','m','h','d','mo',or 'y'."
    if key in ("d", "day"):

        def _anchor(value: datetime) -> datetime:
            return datetime(value.year, value.month, value.day, hour=day_start_hour, tzinfo=timezone.utc)

        if _anchor(now) > _anchor(last_dt):
            _write_stamp(stamp_file, stamp)
            return "A"
        return "R"
    if key in ("mo", "month"):
        if (now.year != last_dt.year or now.month != last_dt.month) and (now.day > 1 or now.hour >= day_start_hour):
            _write_stamp(stamp_file, stamp)
            return "A"
        return "R"
    if key in ("y", "year"):
        if now.year != last_dt.year and (now.month > 1 or now.day > 1 or now.hour >= day_start_hour):
            _write_stamp(stamp_file, stamp)
            return "A"
        return "R"
    diff = (now - last_dt).total_seconds()
    if diff >= seconds * gap:
        _write_stamp(stamp_file, stamp)
        return "A"
    return "R"


def check_date_change(txt_name: str, unit: str, gap: float = 1, day_start_hour: int = 0) -> str:
    return _check_date_change(_stamp_path_for(txt_name), unit, gap=gap, day_start_hour=day_start_hour)


def unhide_folder(path: str) -> str:
    if not os.path.exists(path):
        return f"Error:Path '{path}' does not exist."
    name = os.path.basename(path)
    parent = os.path.dirname(path)
    if name.startswith("."):
        stripped = name.lstrip(".")
        if not stripped:
            return "Error:Cannot unhide folder named only '.'"
        target = os.path.join(parent, stripped)
        if os.path.exists(target):
            return f"Error:Target folder '{target}' already exists."
        shutil.move(path, target)
        return f"Success:Renamed '{path}' to '{target}' to unhide."
    return f"'{path}' is not hidden (no leading dot)."


def hide_folder(path: str) -> str:
    if not os.path.exists(path):
        return f"Error:Path '{path}' does not exist."
    name = os.path.basename(path)
    parent = os.path.dirname(path)
    if not name.startswith("."):
        target = os.path.join(parent, "." + name)
        if os.path.exists(target):
            return f"Error:Target folder '{target}' already exists."
        os.rename(path, target)
        return f"Success:Renamed '{path}' to '{target}' to hide."
    return f"'{path}' is already hidden."


def is_visible(path: str, announce: bool = True) -> Optional[bool]:
    if not os.path.exists(path):
        if announce:
            print("File does not exist")
        return None
    visible = not os.path.basename(path).startswith(".")
    if announce:
        print("Visible" if visible else "Hidden")
    return visible


def _clean_and_normalize_txt_name(txt_name: str) -> str:
    txt_name = txt_name.strip()
    if txt_name.endswith(".txt"):
        txt_name = txt_name[:-4]
    if txt_name.startswith("."):
        raise ValueError("Invalid Txt_Naming Format:txt_name must not start with a dot.")
    if any(sep in txt_name for sep in ("\\", "/")):
        raise ValueError("Invalid Txt_Naming Format:txt_name must not contain/or \\.")
    return txt_name


def _get_main_package() -> str:
    stored = majority_vote_file_reader(_ACTIVE_PACKAGE_FILE, _cwd(), single_read=True)
    if not stored:
        path = _main_folder()
        _set_active_package(path)
        return path
    return stored[0]


def _set_active_package(path: str) -> None:
    write_all_files([path], _cwd(), _ACTIVE_PACKAGE_FILE, ak=True, single_write=True)


def _is_write_locked() -> bool:
    stored = majority_vote_file_reader(_WRITE_LOCK_FILE, _cwd(), single_read=True)
    if stored and stored[0] == "True":
        return True
    return False


def _set_write_lock(value: bool) -> None:
    write_all_files([str(value)], _cwd(), _WRITE_LOCK_FILE, ak=True, single_write=True)


def _restore_main_package_from_backup(recency: int = 0, announce: bool = True, lock: bool = False) -> str:
    backup_root = os.path.join(_cwd(), f"{_PACKAGE_NAME} All Backups")
    if recency in (0, None):
        _set_write_lock(False)
        target = _main_folder()
        _set_active_package(target)
        if announce:
            print(f"get_main_package() now points to:{target}")
        return target
    if not os.path.exists(backup_root):
        raise FileNotFoundError(f"Backup directory not found:{backup_root}")
    backups = sorted([f for f in os.listdir(backup_root) if os.path.isdir(os.path.join(backup_root, f))])
    if not backups:
        raise FileNotFoundError("No backup folders found.")
    chosen = backups[-recency] if recency <= len(backups) else backups[0]
    target = os.path.join(backup_root, chosen)
    _set_write_lock(not lock)
    _set_active_package(target)
    if announce:
        print(f"get_main_package() now points to:{target}")
    return target


def _create_package_and_get_txt_folder_path(txt_name: str, position: str = "main") -> str:
    base = _cwd()
    positions = {
        "main": _get_main_package(),
        "snapshot": os.path.join(base, f"{_PACKAGE_NAME} Snapshots"),
        "backup": os.path.join(base, f"{_PACKAGE_NAME} Backups"),
    }
    if position not in positions:
        raise ValueError(f"Invalid position '{position}'. Must be one of:{list(positions.keys())}")
    return os.path.join(positions[position], txt_name)


def _delete_empty_folder(path: str) -> bool:
    if os.path.isdir(path):
        try:
            shutil.rmtree(path)
            return True
        except (OSError, PermissionError):
            return False
        except Exception as exc:
            print(f"Error deleting folder:{exc}")
            return False
    return False


def _resolve_txt_path_and_validation(txt_name: str, skip_validation_error: bool = False) -> tuple:
    txt_name = _clean_and_normalize_txt_name(txt_name)
    root = _get_main_package()
    folder = os.path.join(root, txt_name)
    unhide_folder(folder)
    os.makedirs(folder, exist_ok=True)
    validation_name = f"{txt_name}_validation"
    tag = None
    for _ in range(3):
        try:
            result = majority_vote_file_reader(validation_name, folder)
        except ValueError:
            result = None
        if result:
            tag = result[0]
            break
        time.sleep(0.003)
    if tag != "1D" and not isinstance(tag, int):
        validation_file = os.path.join(folder, f"{validation_name}.txt")
        if skip_validation_error:
            tag = None
        elif os.path.exists(validation_file):
            raise ValueError("🛑 Validation Error:Corrupted Validation Tag|")
    return (folder, validation_name, tag)


def _path(copy_index: int, folder: str, txt_name: str) -> str:
    name = f"{txt_name}.txt" if copy_index == 0 else f"{txt_name}_{copy_index}.txt"
    return os.path.join(folder, name)


def _read_file_lines(path: str) -> Optional[list]:
    if not os.path.exists(path):
        return None
    out: list = []
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                value = ast.literal_eval(raw)
            except (SyntaxError, ValueError):
                value = raw
            out.append(value)
    if out:
        if isinstance(out[0], str) and out[0].startswith("---[ (c)"):
            return _normalize_text(out[1:])
        return _CORRUPT_MARKER
    return None


def _normalize_text(rows: list) -> list:
    def _fix(value: str) -> str:
        current = value
        for _ in range(4):
            try:
                decoded = current.encode("latin-1").decode("utf-8")
                if decoded == current:
                    break
                current = decoded
            except (UnicodeDecodeError, UnicodeEncodeError):
                break
        return unicodedata.normalize("NFC", current).strip()

    def _walk(item):
        if isinstance(item, list):
            return [_walk(x) for x in item]
        if isinstance(item, str):
            return _fix(item)
        return item

    return [_walk(x) for x in rows]


def _majority_vote(candidates: list) -> Optional[list]:
    def _try(value: str):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value

    if not candidates:
        return []
    serialized = [str([str(x) for x in row]) for row in candidates]
    counts = Counter(serialized)
    top = max(counts.values())
    winners = [row for row, count in counts.items() if count == top]
    if len(winners) > 1:
        parsed = [ast.literal_eval(row) for row in winners]
        raise ValueError(f"Corrupted data:tie in most common rows with frequency {top}:{parsed}")
    chosen = ast.literal_eval(winners[0])
    return [_try(x) for x in chosen]


def _parallel_read(paths: list, max_workers: int = 5) -> list:
    results: list = [None] * len(paths)

    def _task(index: int, path: str) -> tuple:
        return (index, _read_file_lines(path))

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_task, i, p) for i, p in enumerate(paths)]
        for future in as_completed(futures):
            index, value = future.result()
            results[index] = value
    return results


def _validate_and_register_row_shape(
    folder: str,
    rows: list,
    tag: Optional[Union[int, str]],
    validation_name: str,
    list2d: Optional[bool] = None,
) -> list:
    def _is_2d(sequence: list) -> bool:
        if not sequence:
            return False
        return all(isinstance(x, list) for x in sequence[:1])

    inferred = False
    if tag is None:
        if rows:
            if not isinstance(rows[0], list):
                tag = "1D"
            else:
                tag = len(rows[0])
        inferred = True

    consistent = True
    current = rows
    row_tag = None
    i = 0
    item = None
    for attempt in range(3):
        try:
            for i, item in enumerate(rows):
                if not isinstance(item, list):
                    row_tag = "1D"
                else:
                    row_tag = len(item)
                if row_tag != tag:
                    if attempt == 0:
                        rows = [rows]
                        consistent = False
                        break
                    if attempt == 1:
                        if len(current) == 1:
                            rows = current[0]
                            consistent = False
                            break
                        raise ValueError(
                            f"Inconsistent row lengths Passed in the Parameter list at row {i}:\n"
                            f"            Expected {tag} Length but got {row_tag}=>{item}.\n"
                        )
        except TypeError:
            raise ValueError(
                f"Inconsistent row lengths Passed in the Parameter list at row {i}:\n"
                f"            Expected {tag} Length but got {row_tag}=>{item}.\n"
            )
        if consistent is True:
            break

    if inferred is True:
        is_2d = _is_2d(rows)
        if is_2d is False and list2d is None:
            _delete_empty_folder(folder)
            raise ValueError(
                "🟡 1D data detected. On first write or after a reset,setting parameter [ is2d=False ].\n"
                "               This prevents incorrect structure locking for a 2D file created inside a loop.\n"
                "               This action/parameter is only needed when a 1D list is passed at creation or reset.\n"
                "               Auto-correct only works after you've initialized the file (That is after proper first a write or append.)"
            )
        if is_2d is False and list2d is True:
            _delete_empty_folder(folder)
            raise ValueError(
                "⚠️ 'is2d=True' was set,but the data appears 1D. \n"
                "                If you're trying to create a 2D structure,wrap your list in an extra bracket like [[...]].\n"
                "                This action/parameter is only needed when a 1D list is passed at creation or reset.\n"
                "                Auto-correct only works after you've initialized the file (That is after proper first a write or append.)"
            )
        write_all_files([tag], folder, validation_name, single_write=True)
    return rows


def write_all_files(
    data: Optional[list],
    folder: str,
    txt_name: str,
    ak: bool = False,
    single_write: bool = False,
) -> None:
    if _is_write_locked():
        active = _get_main_package()
        if folder.startswith(active):
            _set_write_lock(False)
        elif ak:
            pass
        else:
            print("🛑 Write blocked:currently pointing to a restored backup (write=False).")
            print("   To allow writes,call restore_main_package_from_backup(...,write=True)")
            print("   or reset to main with restore_main_package_from_backup(recency=0).")
            raise PermissionError("Write blocked: active package restored in read-only mode.")
    if data is None:
        payload = ["None"]
    else:
        payload = [str(x) for x in _normalize_text(data)]
    content = corruption_tag(_PACKAGE_NAME) + "\n\n" + "\n".join(payload)
    copies = 1 if single_write else _WRITE_COPIES
    for i in range(copies):
        target = _path(i, folder, txt_name)
        if i > 0 or ak:
            unhide_folder(target)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(content)
        if i > 0 or ak:
            hide_folder(target)


def corruption_tag(name: str) -> str:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"---[ (c) {name}-Last Updated:{stamp}|View Only-Editing Disabled ]---"
    try:
        width = shutil.get_terminal_size().columns
    except Exception:
        width = 80
    padding = max(width - len(header), 0)
    left = padding // 2
    right = padding - left
    return " " * left + header + " " * right


def majority_vote_file_reader(
    txt_name: str,
    folder: str,
    max_retries: int = 2,
    sleep: float = 0.01,
    single_read: bool = False,
) -> Optional[list]:
    result = None
    for _ in range(max_retries):
        copies = 1 if single_read else _WRITE_COPIES
        paths = [_path(i, folder, txt_name) for i in range(copies)]
        contents = _parallel_read(paths)
        if all(c is None for c in contents):
            result = None
        else:
            non_null = [c for c in contents if c is not None]
            voted = _majority_vote(non_null)
            if not voted:
                result = []
            else:
                if voted == _CORRUPT_MARKER:
                    file_path = os.path.join(folder, txt_name)
                    raise ValueError(
                        f"""🛑 File corruption or tampering detected.

Please follow these steps to inspect and fix the issue:

1. 📂 Confirm the file path:
   {file_path}

2. 🧾 Manually read the file content:
   Example in Python:
       with open(r'{file_path}','r',encoding='utf-8') as f:
           print(f.read())

3. 🛠️ Fix any content issues you find.
   You can use a text editor or overwrite the file programmatically.

4. ⚠️ for safety Backup the file elsewhere before deleting.

5. 🗑️ Delete the corrupted file:
       f.remove("{txt_name}")

6. ✅ Save your corrected version with the same filename.
   Make sure the structure and content are valid before reuse."""
                    )
                return voted
        if result:
            return result
        time.sleep(sleep)
    return result


def read_txt(txt_name: str) -> Optional[list]:
    folder, _, _ = _resolve_txt_path_and_validation(txt_name, skip_validation_error=True)
    return majority_vote_file_reader(txt_name, folder)


def get_keep_deletion_rules_filter(
    data: list,
    cutoff: Optional[int],
    del_list: list,
    keep: int,
    indexes: Optional[Union[int, list, str]],
) -> list:
    if indexes:
        keys: list = []
        for row in data:
            for i, idx in enumerate(indexes):
                if i == 0:
                    key = str(row[idx])
                else:
                    key += str(row[idx])
            keys.append(key)
    else:
        keys = [str(x) for x in data]
    uniques: list = []
    for key in keys:
        if key not in [u[0] for u in uniques] and key in del_list:
            uniques.append([key, keys.count(key)])
    out: list = []
    for key, count in uniques:
        extra = count - keep
        n = 0 if extra <= 0 else extra
        out += [key] * n
    return out


def delete_heart(
    data: list,
    filter_list: list,
    indexes: Optional[list],
    single_row: bool,
    is_single: bool,
    keep: int,
) -> tuple:
    def _remove(target_list: list, value) -> list:
        pos = None
        for i, x in enumerate(target_list):
            if value == x:
                pos = i
                break
        target_list.pop(pos)
        return target_list

    removed = 0
    kept: list = []
    if not filter_list:
        kept = data
    else:
        for row in data:
            if single_row is True:
                key = str(row)
            else:
                key = None
                for i, idx in enumerate(indexes):
                    try:
                        if i == 0:
                            key = str(row[idx])
                        else:
                            key += str(row[idx])
                    except IndexError:
                        raise IndexError("🚫 Your File List not up to this index/row_length")
            if key in filter_list:
                removed += 1
                if is_single or keep:
                    filter_list = _remove(filter_list, key)
            elif single_row is True:
                kept.append(row)
            else:
                kept.append(row)
    return (kept, removed)


def _get_validation_shape(data: list) -> Optional[Union[int, str]]:
    if data:
        if not isinstance(data[0], list):
            tag = "1D"
        else:
            tag = len(data[0])
        for i, row in enumerate(data):
            if not isinstance(row, list):
                this = "1D"
            else:
                this = len(row)
            if this != tag:
                raise IndexError(
                    "Inconsistent row lengths passed in the parameter list:all rows must have the same number of elements/length."
                )
        return tag
    return None


def validate_delete_parameters_and_return_index(
    del_list: list,
    cutoff: Optional[int],
    keep: Optional[int],
    auto_trim_len: Optional[int],
    index: Optional[Union[int, list, str]],
    reverse: bool,
) -> tuple:
    if auto_trim_len is not None and auto_trim_len < 1:
        raise ValueError("⚠️ 'size' parameter must be greater than or equal to 1.")
    if not del_list and auto_trim_len is None:
        raise ValueError("del_list Parameter items can't be empty.")
    if cutoff is not None:
        if not isinstance(cutoff, int):
            raise TypeError(f"cutoff must be an int or None,not {type(cutoff)}")
        if cutoff < 1:
            raise ValueError("cutoff must be at least 1")
    if keep is not None:
        if not isinstance(keep, int):
            raise TypeError(f"keep must be an int or None,not {type(keep)}")
        if keep < 0:
            raise ValueError("keep cannot be negative")
    if keep is not None and cutoff is not None:
        raise ValueError("Arguments 'cutoff' and 'keep' cannot be passed at the same time.")
    if auto_trim_len is not None:
        if not isinstance(auto_trim_len, int):
            raise TypeError(f"auto_trim_len must be an int or None,not {type(auto_trim_len)}")
        if auto_trim_len < 0:
            raise ValueError("auto_trim_len cannot be negative")
    if index is None:
        pass
    elif isinstance(index, int):
        index = [index]
    elif isinstance(index, list):
        if not all(isinstance(i, int) for i in index):
            raise TypeError("All elements in the index list must be integers.")
    elif index == "*":
        size = len(del_list[0]) if isinstance(del_list[0], list) else len(del_list)
        index = list(range(size))
    else:
        raise IndexError(f"index must be an int,'*',a list of ints,or None,not {type(index)}")
    if (
        isinstance(index, list)
        and len(index) > 1
        and not (isinstance(del_list, list) and all(isinstance(i, list) for i in del_list))
    ):
        del_list = [del_list]
    if not isinstance(reverse, bool):
        raise TypeError(f"reverse must be a bool,not {type(reverse)}")
    shape = _get_validation_shape(del_list)
    if del_list and shape != "1D" and index is None:
        raise IndexError("Index Requried..")
    if index is None:
        return (index, del_list)
    return (sorted(index), del_list)


def normalize_to_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set, frozenset, range)):
        return list(value)
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, (str, int, float)):
        return [value]
    raise TypeError(f"Unsupported type:{type(value).__name__}. Expected a list-like structure.")


def normalize_to_2d(value: list, is2d: Optional[bool]) -> list:
    if is2d is True and (isinstance(value, list) and all(not isinstance(i, list) for i in value)):
        return [value]
    return value


def snapshot_validate_parameters(
    txt_name: str,
    date_type: str,
    gap: float,
    day_start_hour: int,
    trim: Optional[int],
    display: bool,
) -> None:
    if trim is not None and not (isinstance(trim, int) and not isinstance(trim, bool) and trim >= 1):
        raise ValueError("trim must be an int ≥ 1 or None.")
    if not isinstance(txt_name, str) or not txt_name.strip():
        raise ValueError("Parameter 'txt_name' must be a non-empty string.")
    try:
        date_type = date_type.lower()
    except AttributeError:
        raise AttributeError(
            "Parameter 'unit' must be one of:['s','second','m','min','minute','h','hour','d','day','mo','month','y','year']"
        )
    allowed = ["s", "second", "m", "min", "minute", "h", "hour", "d", "day", "mo", "month", "y", "year"]
    if date_type not in allowed:
        raise ValueError(
            "Parameter 'unit' must be one of:['s','second','m','min','minute','h','hour','d','day','mo','month','y','year']"
        )
    if not isinstance(gap, (int, float)) or gap <= 0:
        raise ValueError("Parameter 'gap' must be numerical and greater than zero (0).")
    if not isinstance(day_start_hour, int) or not 0 <= day_start_hour <= 23:
        raise ValueError("Parameter 'begin' must be an integer between 0 and 23.")
    if not isinstance(display, bool):
        raise ValueError("Parameter 'display' must be a boolean value.")


def _list_visible_files(announce: bool = True) -> list:
    root = _get_main_package()
    try:
        entries = os.listdir(root)
    except FileNotFoundError:
        if announce:
            print(f"Directory not found:{root}")
        return []
    except NotADirectoryError:
        if announce:
            print(f"Not a directory:{root}")
        return []
    except PermissionError:
        if announce:
            print(f"Permission denied:{root}")
        return []
    folders = [
        e
        for e in entries
        if os.path.isdir(os.path.join(root, e))
        and not e.startswith(".")
        and not e.startswith("__")
        and not e.endswith("__")
    ]
    if announce:
        print(f"Visible folders in directory '{root}':")
        print(f"Total files:{len(folders)}")
        for f in folders:
            print(f"-{f}")
    return folders


def _copy_and_paste_file(
    txt_name: str,
    label: str,
    trim: Optional[int],
    display: bool = True,
) -> bool:
    folder, _, _ = _resolve_txt_path_and_validation(txt_name)
    content = majority_vote_file_reader(txt_name, folder)
    if content:
        if label == "Backup 💾":
            target = _create_package_and_get_txt_folder_path(txt_name, position="backup")
        elif label == "Snapshot 📸":
            target = _create_package_and_get_txt_folder_path(txt_name, position="snapshot")
        else:
            target = _create_package_and_get_txt_folder_path(txt_name, position="main")
        trim_folder_files(target, trim)
        os.makedirs(target, exist_ok=True)
        stamp = _timestamp_with_label(txt_name)
        write_all_files(content, target, stamp, ak=True)
        if display:
            print(f"{label} Successfully Done ✅.")
        return True
    if content is None:
        _delete_empty_folder(folder)
        raise FileNotFoundError(f"The file '{txt_name}' does not exist in yet! .")
    if content == []:
        print(f"🚫 Can't {label} An Empty File.")
        return True
    return False


def _timestamp_with_label(label: str) -> str:
    now = datetime.now()
    return f"{now.strftime('%Y-%m-%d_%H-%M-%S')}_{label}"


def _copy_folder(source: str, destination: str, announce: bool, label: str) -> None:
    if not os.path.exists(source):
        raise FileNotFoundError(f"Source folder does not exist:{source}.")
    if os.path.exists(destination):
        raise FileExistsError(f"Destination folder already exists:{destination}.")
    shutil.copytree(source, destination)
    if announce:
        print(f"General (*) {label} Successfully Done ✅.")


def _select_star_copy_paste_folder(announce: bool, kind: str, trim: Optional[int]) -> None:
    source = _get_main_package()
    root = os.path.join(_cwd(), f"{_PACKAGE_NAME} All {kind}")
    trim_subfolders(root, trim)
    if not os.path.exists(root):
        os.makedirs(root)
    target = os.path.join(root, _timestamp_with_label(_PACKAGE_NAME))
    _copy_folder(source, target, announce, kind[:-1])


def trim_folder_files(folder: str, limit: Optional[int]) -> None:
    if limit is not None and os.path.isdir(folder):
        files = [f for f in glob(os.path.join(folder, "*")) if os.path.isfile(f)]
        if len(files) <= limit:
            return
        files.sort(key=os.path.getmtime)
        for i in range(len(files) - limit):
            try:
                os.remove(files[i])
            except Exception as exc:
                print(f"Error deleting {files[i]}:{exc}")


def trim_subfolders(folder: str, limit: Optional[int]) -> None:
    if limit is not None and os.path.isdir(folder):
        dirs = [f for f in glob(os.path.join(folder, "*")) if os.path.isdir(f)]
        if len(dirs) <= limit:
            return
        dirs.sort(key=os.path.getmtime)
        for i in range(len(dirs) - limit):
            try:
                shutil.rmtree(dirs[i])
            except Exception as exc:
                print(f"Error deleting folder {dirs[i]}:{exc}")


def smart_select(data, index: Union[int, list, tuple]):
    if not isinstance(index, (int, list, tuple)):
        raise TypeError("Index must be an int,list,or tuple. Please confirm the index given.")
    is_2d = isinstance(data[0], (list, tuple))
    try:
        if is_2d:
            if isinstance(index, (list, tuple)):
                return [[row[i] for i in index] for row in data]
            return [row[index] for row in data]
        if isinstance(index, (list, tuple)):
            return [data[i] for i in index]
        return data[index]
    except IndexError:
        raise IndexError("One or more indexes are out of range. Please confirm the index given in the parameter.")


def _delete_path(path: str, display: bool = True) -> None:
    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)
        if display:
            print(f"File or symlink deleted:{path}")
    elif os.path.isdir(path):
        shutil.rmtree(path)
        if display:
            print(f"Directory deleted:{path}")
    elif display:
        print(f"Path does not exist:{path}")


def _hide_hidden_files() -> None:
    panel = _CONTROL_PANEL_FILE
    folder = _resolve_txt_path_and_validation(panel, skip_validation_error=True)[0]
    unhide_folder(folder)
    files = majority_vote_file_reader(panel, folder)
    hide_folder(folder)
    if files:
        for name in files:
            sub = _resolve_txt_path_and_validation(name, skip_validation_error=True)[0]
            hide_folder(sub)


def _debug_validation(
    data: list,
    is2d: Optional[bool],
    display: bool,
    row_length: Optional[int],
) -> tuple:
    def _make_buffer():
        title = "\n   🛡️ WithOpen Debug Mode."
        title = stylize(title, bold=True)
        return ScreenBuffer(
            wait=True,
            max_wait=9,
            max_display=8,
            reset=False,
            header=title,
            header_alignment=2,
            show_header=True,
            silent_display=None,
            only_display=None,
            auto_clean_edges=True,
            auto_clean_silent_only_display=False,
            shift_max_display=True,
        )

    viewport = _make_buffer()
    if not isinstance(data, list):
        viewport.put("❌ Major Issue|This file is not a list.")
        viewport.put("🛠️ Manual Inspection Required.")
        viewport.put("To Solve This")
        viewport.put(
            "Step 1-Move file to MaxCleanerDB backup location using the backup def/function [ MaxDBcleaner.backup(filename) ]."
        )
        viewport.put("Step 2-Get the content manually using [ with open( filepath,) as f ] to clean/debug it.")
        viewport.put("Step 3-Reset the file validation using [ MaxCleanerDB.w(filename,[]) ]")
        viewport.put("Step 4 – Now move the manually cleaned file into the orignal file you just reset validation for.")
        return (False,)

    def _log_factory(capacity: int):
        buffer: list = []

        def _log(value: Optional[str] = None) -> str:
            nonlocal buffer
            if value is not None:
                buffer.append(str(value))
                if len(buffer) > capacity:
                    buffer = buffer[-capacity:]
            return "\n".join(buffer)

        return _log

    log = _log_factory(3)
    valid: list = []
    invalid: list = []
    total = len(data)
    for i, row in enumerate(data):
        bad = False
        if is2d:
            if isinstance(row, list):
                if len(row) != row_length:
                    bad = True
                    log(f"Row {i} mismatch inner list/2D length:{str(row)}")
                    invalid.append(row)
            else:
                bad = True
                log(f"Row {i} mismatch (Not a 2D list):{str(row)}")
                invalid.append(row)
        elif not isinstance(row, list):
            valid.append(row)
        else:
            bad = True
            log(f"Row {i} mismatch (Not a 1D List):{str(row)}")
            invalid.append(row)
        seen = len(valid)
        bad_count = len(invalid)
        idx = i + 1
        try:
            pct_valid = seen / idx * 100
        except ZeroDivisionError:
            pct_valid = 0
        try:
            pct_bad = bad_count / idx * 100
        except ZeroDivisionError:
            pct_bad = 0
        viewport.put(f"🧮  Total  :{total:,}", level=0)
        viewport.put(f"❌ Invalid :{bad_count:,} ({round(pct_bad)}%)", level=1)
        viewport.put(f"✅  Valid  :{seen:,} ({round(pct_valid)}%)", level=2)
        viewport.put("", level=3)
        viewport.put(log(), level=4)
        viewport.put("", level=5)
        viewport.put(loop_progress(idx, total), level=6)
        if display is True:
            viewport.display()
            if bad:
                time.sleep(1)
            else:
                time.sleep(0.01)
    return (valid, invalid)


def _validate_debug_params(
    txt_name: str,
    is2d: bool,
    clean: Optional[bool] = None,
    length: Optional[int] = None,
    display: bool = True,
) -> None:
    if not isinstance(txt_name, str):
        raise TypeError("txt_name must be a string.")
    if not isinstance(is2d, bool):
        raise TypeError("is2d must be a boolean.")
    if not isinstance(display, bool):
        raise TypeError("display must be a boolean.")
    if clean is not None and not isinstance(clean, bool):
        raise TypeError("clean must be a boolean if provided.")
    if is2d:
        if length is None:
            raise ValueError("length must be provided when is2d is True.")
        if not isinstance(length, int):
            raise TypeError("length must be an integer when is2d is True.")
        if length <= 0:
            raise ValueError("length must be greater than zero when is2d is True.")


def _get_debug_record(data: list, is2d: bool, row_length: Optional[int], display: bool):
    return _debug_validation(data, is2d, display, row_length)


def info(txt_name: str, display: bool = True) -> dict:
    main = _get_main_package()
    available = _list_visible_files(announce=False)
    folder, _, tag = _resolve_txt_path_and_validation(txt_name, skip_validation_error=True)
    if txt_name not in available:
        _delete_empty_folder(folder)
        raise FileNotFoundError(f"The file '{txt_name}' does not exist in yet! .")
    content = majority_vote_file_reader(txt_name, folder)
    if content is None:
        structure = "Not Found"
    elif content == []:
        structure = "Empty"
    elif isinstance(tag, int):
        structure = "2D"
    elif tag == "1D":
        structure = "1D"
    else:
        structure = "Unknown"
    total = len(content) if isinstance(content, list) else 0
    row_tag = tag if tag else "-"
    base = _cwd()
    main_path = os.path.join(base, f"{main}\\{txt_name}")
    backup_path = os.path.join(base, f"{main} Backups\\{txt_name}")
    snapshot_path = os.path.join(base, f"{main} Snapshots\\{txt_name}")
    backups = glob(os.path.join(backup_path, "*.txt")) if os.path.exists(backup_path) else []
    backup_count = len(backups)
    snaps = glob(os.path.join(snapshot_path, "*.txt")) if os.path.exists(snapshot_path) else []
    snap_count = len(snaps)
    if snaps:
        newest = max(snaps, key=os.path.getmtime)
        last_snap = datetime.fromtimestamp(os.path.getmtime(newest)).strftime("%Y-%m-%d %H:%M:%S")
    else:
        last_snap = "—"
    payload = {
        "Structure": structure,
        "Total Entries": total,
        "Row Validation": row_tag,
        "Backups": backup_count,
        "Snapshots": snap_count,
        "Last Snapshot": last_snap,
        "Main Path": main_path,
        "Backup Path": backup_path,
        "Snapshot Path": snapshot_path,
    }
    if display:
        labels = {
            "1D": "📄 Structure:1D list",
            "2D": "🧱 Structure:2D list",
            "Empty": "🟤 Empty File",
            "Not Found": "🔴 File Not Found",
            "Unknown": "❓ Unknown Structure",
        }
        print(f"\n{labels.get(structure, '❓ Unknown Structure')}")
        print(f"🗃️ Total Entries:{total}")
        print(f"🧠 Row Validation:{row_tag}")
        print()
        print("🛟 Backup/Snapshot Status:")
        print(f"  🔁 Backups:{backup_count}")
        print(f"  📸 Snapshots:{snap_count}")
        print(f"  🕒 Last Snapshot:{last_snap}")
        print()
        print("📁 Folder Paths:")
        print(f"  📂 Main Path:{main_path}")
        print(f"  💾 Backup Path:{backup_path}")
        print(f"  📸 Snapshot Path:{snapshot_path}")
        print()
    return payload


def _snapshot(
    txt_name: str,
    unit: str,
    gap: float,
    trim: Optional[int] = None,
    day_start_hour: int = 0,
    display: bool = True,
) -> None:
    snapshot_validate_parameters(txt_name, unit, gap, day_start_hour, trim, display)
    if txt_name == "*":
        _select_star_copy_paste_folder(display, "Snapshots", trim)
    else:
        folder = _resolve_txt_path_and_validation(txt_name)[0]
        stamp_file = os.path.join(folder, f"{txt_name}_snapshot.txt")
        if _check_date_change(stamp_file, unit, gap=gap, day_start_hour=day_start_hour) == "A":
            _copy_and_paste_file(txt_name, "Snapshot 📸", trim, display=display)


def _backup(txt_name: str, display: bool = True) -> None:
    if not isinstance(display, bool):
        raise ValueError("Parameter 'display' must be either True or False.")
    if txt_name == "*":
        _select_star_copy_paste_folder(display, "Backups", None)
    else:
        _copy_and_paste_file(txt_name, "Backup 💾", None, display=display)


def _read(
    txt_name: str,
    index: Optional[Union[int, list, tuple]] = None,
    default: list = [],
    notify_new: bool = False,
):
    if default not in ([], None):
        raise ValueError("Invalid value for set_new. Only [] or None are allowed.")
    if not isinstance(notify_new, bool):
        raise ValueError("Invalid value for notify_new. Only True or False are allowed.")
    if not (index is None or isinstance(index, (int, list, tuple))):
        raise TypeError("Index must be an int,list,tuple,or None.")
    folder_check = _create_package_and_get_txt_folder_path(txt_name, position="main")
    was_new = not os.path.isdir(folder_check)
    folder, validation_name, tag = _resolve_txt_path_and_validation(txt_name)
    content = majority_vote_file_reader(txt_name, folder, single_read=True)
    if content is None:
        _delete_empty_folder(folder)
        if notify_new and was_new:
            print(f"🔔 New file detected>[ {txt_name} ]<")
        return default
    _validate_and_register_row_shape(folder, content, tag, validation_name)
    queue_name = f"{txt_name}_queue"
    _event_tag(folder, queue_name)
    _hide_hidden_files()
    if index is not None:
        return smart_select(content, index)
    return content


def _write(txt_name: str, data, is2d: Optional[bool] = None) -> None:
    if is2d not in (None, True, False):
        raise TypeError("Parameter 'is2d' must be either None,True,or False.")
    data = normalize_to_list(data)
    folder, validation_name, tag = _resolve_txt_path_and_validation(txt_name, skip_validation_error=True)
    if tag:
        data = normalize_to_2d(data, is2d)
    data = _validate_and_register_row_shape(folder, data, tag, validation_name, is2d)
    _wait_read(folder, txt_name)
    if not data:
        write_all_files("", folder, txt_name, ak=True)
        data = ""
    write_all_files(data, folder, txt_name)
    queue_name = f"{txt_name}_queue"
    _event_tag(folder, queue_name)
    _hide_hidden_files()


def _append(txt_name: str, data, is2d: Optional[bool] = None) -> list:
    if is2d not in (None, True, False):
        raise TypeError("Parameter 'is2d' must be either None,True,or False.")
    data = normalize_to_list(data)
    folder, _, tag = _resolve_txt_path_and_validation(txt_name)
    if tag:
        data = normalize_to_2d(data, is2d)
    data = _validate_and_register_row_shape(folder, data, tag, f"{txt_name}_validation", list2d=is2d)
    content = majority_vote_file_reader(txt_name, folder)
    if content is None:
        content = []
    merged = list(content) + list(data)
    write_all_files(merged, folder, txt_name)
    queue_name = f"{txt_name}_queue"
    _event_tag(folder, queue_name)
    _hide_hidden_files()
    return merged


def _delete(
    txt_name: str,
    del_list: list = [],
    index: Optional[Union[int, list]] = None,
    cutoff: Optional[int] = None,
    keep: Optional[int] = None,
    reverse: bool = False,
    auto_trim_len: Optional[int] = None,
) -> tuple:
    removed = 0
    del_list = normalize_to_list(del_list)
    index, del_list = validate_delete_parameters_and_return_index(del_list, cutoff, keep, auto_trim_len, index, reverse)
    if txt_name not in _list_visible_files(announce=False):
        raise FileNotFoundError(f"The file '{txt_name}' does not exist in yet! .")
    folder, _, tag = _resolve_txt_path_and_validation(txt_name)
    before = majority_vote_file_reader(txt_name, folder, single_read=True)
    if before is None:
        before = []
    content = before
    filter_values = [
        row if isinstance(row, str) else "".join(str(i) for i in row) if hasattr(row, "__iter__") else str(row)
        for row in del_list
    ]
    if cutoff:
        filter_values = filter_values * cutoff
    elif keep:
        filter_values = get_keep_deletion_rules_filter(before, cutoff, filter_values, keep, index)
    empty_filter = True
    if del_list:
        empty_filter = False
        if reverse:
            before = list(reversed(before))
        if not tag:
            raise ValueError("❗Validation missing. Perform create a write or append function before proceeding.")
        single = False
        if tag == "1D":
            single = True
            if index is not None:
                raise IndexError("Index parameter for a Normal list should be None|index=None.")
        elif isinstance(tag, int):
            single = False
            if index is None:
                raise IndexError("Index parameter is required when processing a 2D list.")
        else:
            raise RuntimeError("❗ Failed to get validation tag... retry again")
        content, removed = delete_heart(before, filter_values, index, single, bool(cutoff), keep)
        if reverse:
            content = list(reversed(content))
    if auto_trim_len:
        if not empty_filter:
            content = content[-auto_trim_len:]
        else:
            original_len = len(before)
            content = before[-auto_trim_len:]
            removed = original_len - len(content)
    write_all_files(content, folder, txt_name)
    queue_name = f"{txt_name}_queue"
    _event_tag(folder, queue_name)
    _hide_hidden_files()
    return (removed, content)


def _restore(recency: int = 0, write: bool = False, display: bool = True) -> str:
    if not isinstance(recency, int):
        raise TypeError(f"recency must be an int,got {type(recency).__name__}")
    if not isinstance(write, bool):
        raise TypeError(f"write must be a bool,got {type(write).__name__}")
    if write is None:
        raise ValueError("write cannot be None. Provide a bool (True or False)")
    if not isinstance(display, bool):
        raise TypeError(f"display must be a bool,got {type(display).__name__}")
    if display is None:
        raise ValueError("display cannot be None. Provide a bool (True or False)")
    return _restore_main_package_from_backup(recency=recency, announce=display, lock=write)


def _debug(
    txt_name: str,
    is2d: Optional[bool] = None,
    length: Optional[int] = None,
    row_length: Optional[int] = None,
    display: bool = True,
) -> Optional[dict]:
    folder = _create_package_and_get_txt_folder_path(txt_name, position="main")
    if display:
        print(f"\n🛡️ WithOpen|⏳ Loading data ... [{datetime.now().strftime('%H:%M:%S')}]")
        time.sleep(3)
    if os.path.exists(folder):
        _validate_debug_params(txt_name, is2d, clean=True, length=length, display=display)
        path, _, _ = _resolve_txt_path_and_validation(txt_name)
        content = majority_vote_file_reader(txt_name, path, single_read=True)
        if content:
            good, bad = _get_debug_record(content, is2d, row_length or length, display)
            if display:
                print("Done Debugging ✔️.")
            return {"good": good, "bad": bad}
        print("⚠️ You Can't Debug An Empty File.")
    else:
        print("The file path does not exist.")
    _hide_hidden_files()
    return None


def _remove(txt_name: str, display: bool = True) -> None:
    if not isinstance(display, bool):
        raise TypeError("❌ The 'display' parameter must be a boolean value:either True or False.")
    available = _list_visible_files(announce=False)
    txt_name = _clean_and_normalize_txt_name(txt_name)
    folder = _create_package_and_get_txt_folder_path(txt_name)
    if txt_name not in available:
        _delete_empty_folder(folder)
        raise FileNotFoundError(f"🛑 The file '{txt_name}' does not exist.")
    _delete_path(folder, display=display)


def _listdir(display: bool = True) -> list:
    if not isinstance(display, bool):
        raise TypeError("❌ The 'display' parameter must be a boolean value:either True or False.")
    return _list_visible_files(display)


def _hide(txt_name: str, display: bool = True) -> None:
    if not isinstance(display, bool):
        raise TypeError("❌ The 'display' parameter must be a boolean value:either True or False.")
    available = _list_visible_files(announce=False)
    if txt_name.strip() == "*":
        folder = _get_main_package()
    else:
        folder, _, _ = _resolve_txt_path_and_validation(txt_name)
        if txt_name not in available:
            _delete_empty_folder(folder)
            raise FileNotFoundError(f"The file '{txt_name}' does not exist in yet! .")
        _append(_CONTROL_PANEL_FILE, txt_name, is2d=False)
    result = hide_folder(folder)
    if display:
        print(result)


def _unhide(txt_name: str, display: bool = True) -> None:
    if not isinstance(display, bool):
        raise TypeError("❌ The 'display' parameter must be a boolean value:either True or False.")
    available = _list_visible_files(announce=False)
    if txt_name.strip() == "*":
        folder = _get_main_package()
    else:
        folder, _, _ = _resolve_txt_path_and_validation(txt_name)
        if txt_name not in available:
            _delete_empty_folder(folder)
            raise FileNotFoundError(f"The file '{txt_name}' does not exist in yet! .")
        try:
            _delete(_CONTROL_PANEL_FILE, txt_name)
        except FileNotFoundError:
            pass
    result = unhide_folder(folder)
    if display:
        print(result)


def _consoles(txt_name: str, multiple: bool, alert: bool) -> None:
    if not isinstance(multiple, bool):
        raise ValueError("The 'multiple' argument must be either True or False.")
    if not isinstance(alert, bool):
        raise ValueError("The 'display' argument must be either True or False.")
    txt_name = _clean_and_normalize_txt_name(txt_name)
    folder = _create_package_and_get_txt_folder_path(txt_name)
    fname = f"{txt_name}_consoles"
    write_all_files([multiple, alert], folder, fname, ak=True, single_write=True)


def _warning(multiple: bool) -> None:
    if not isinstance(multiple, bool):
        raise ValueError("The 'multiple' argument must be either True or False.")
    target = os.path.join(_cwd(), _HIDE_ALERT_FILE)
    unhide_folder(target)
    with open(target, "w") as fh:
        fh.write(str(multiple))
    hide_folder(target)


def _event_tag(folder: str, tag: str) -> None:
    path = os.path.join(folder, f"{tag}.txt")
    stamp = time.perf_counter()
    try:
        if os.path.exists(path):
            content = majority_vote_file_reader(tag, folder)
            content[1] = stamp
            write_all_files(content, folder, tag, single_write=True)
        else:
            payload = [None, stamp, "Done"]
            write_all_files(payload, folder, tag, single_write=True)
    except ValueError:
        payload = ["1111", stamp, "Active"]
        write_all_files(payload, folder, tag, single_write=True)
    except OSError as exc:
        if exc.errno == errno.EACCES:
            return
        raise


def _is_new_alert_enabled() -> bool:
    target = os.path.join(_cwd(), _HIDE_ALERT_FILE)
    unhide_folder(target)
    try:
        with open(target, "r") as fh:
            value = fh.read().strip()
            flag = ast.literal_eval(value)
    except FileNotFoundError:
        with open(target, "w") as fh:
            fh.write(str(True))
        flag = True
    hide_folder(target)
    return flag


def _in_active_window(second: float) -> bool:
    windows = [(0, 4), (10, 14), (20, 24), (30, 34), (40, 44), (50, 54)]
    return any(lo <= second <= hi for lo, hi in windows)


def _perf_seconds() -> float:
    return time.perf_counter()


def _queue_state_is_active(folder: str, queue_name: str) -> bool:
    try:
        content = _read_majority(queue_name, folder)
        if not content or not isinstance(content, list) or len(content) != 3:
            return True
        _, stamp, state = content
        age = _perf_seconds() - stamp
        if state == "Active":
            return age > _ACTIVE_AGE_LIMIT
        if state == "Done":
            return age >= _QUEUE_DONE_AGE
        return False
    except Exception:
        return False


def _read_majority(txt_name: str, folder: str):
    for _ in range(9):
        try:
            content = majority_vote_file_reader(txt_name, folder, single_read=True)
            if content is not None:
                return content
        except ValueError:
            continue
        except Exception:
            raise


def _update_queue_state(folder: str, queue_name: str, new_id: Optional[int] = None) -> bool:
    path = os.path.join(folder, f"{queue_name}.txt")
    stamp = _perf_seconds()
    try:
        if os.path.exists(path):
            content = _read_majority(queue_name, folder)
            content[1] = stamp
            if new_id:
                content[0] = new_id
                content[2] = "Active"
            else:
                content[2] = "Done"
            write_all_files(content, folder, queue_name, single_write=True)
        else:
            payload = ["new", stamp, "Done"]
            write_all_files(payload, folder, queue_name, single_write=True)
    except ValueError:
        payload = ["1111", stamp, "Active"]
        write_all_files(payload, folder, queue_name, single_write=True)
    except OSError as exc:
        if exc.errno == errno.EACCES:
            return False
        raise
    return True


def _write_with_retry(folder: str, txt_name: str, session_id) -> None:
    max_tries = 12
    interval = 1
    stamp = _perf_seconds()
    payload = [[session_id, stamp]]
    for attempt in range(max_tries):
        try:
            write_all_files(payload, folder, txt_name, single_write=True)
            break
        except OSError as exc:
            if exc.errno == errno.EACCES and attempt < max_tries - 1:
                time.sleep(interval)
            else:
                raise


def _queue_match(folder: str, txt_name: str, session_id) -> bool:
    content = _read_majority(txt_name, folder)
    if isinstance(content, list) and content:
        return content[0][0] == session_id
    return False


def _random_second_frac() -> float:
    now = time.perf_counter() % 60
    whole = int(now)
    return whole % 10 + (now - whole)


def _wait_for_window(period: float, tolerance: float = 0.001) -> None:
    while True:
        now = time.perf_counter() % 60
        offset = now % period
        if offset < tolerance or period - offset < tolerance:
            break
        gap = min(offset, period - offset)
        if gap > 0.01:
            time.sleep(0.005)
        else:
            time.sleep(0)


def _print_queue_status(status: str, hold_time: float = 0) -> None:
    status = status.upper().strip()
    stamp = datetime.now().strftime("%H:%M:%S")
    marks = {"HOLDING": "🔴", "QUEUING": "🟡", "DEQUEUE": "🟢"}
    mark = marks.get(status, "⚪")
    extra = f" ⟳ x{int(hold_time / 0.05)}" if hold_time > 0 else ""
    print(f"🪖𝗪𝗜𝗧𝗛𝗢𝗣𝗘𝗡 ▸ {status:<8} {mark}|{stamp}{extra}")


def _with_timeout(func, timeout, *args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    if elapsed > timeout:
        raise TimeoutError(f"Function exceeded timeout of {timeout} seconds (took {elapsed:.10f}s)")
    return result


def _wait_read(folder: str, txt_name: str, ignore_memory: bool = False):
    txt_name = txt_name.strip()
    session_id = _new_session_id()
    queue_name = f"{txt_name}_queue"
    queue_len_name = f"{txt_name}_queue_len"
    console_name = f"{txt_name}_consoles"
    console = _read_majority(console_name, folder)
    try:
        multiple = console[0]
        verbose = console[1]
    except (TypeError, IndexError):
        multiple = False
        verbose = False
        if _is_new_alert_enabled():
            print(
                "🪖 [NEW] Multiple C. OFF → f.consoles(txt_name,multiple=True,alert=True/False)|Hide alert:f.warning(False)."
            )
        write_all_files([multiple, verbose], folder, console_name, single_write=True)
    retries = 0
    if multiple:
        hold_time = 0.0
        silent = False
        while True:
            try:
                while True:
                    frac = _perf_seconds() % 60
                    if _in_active_window(frac):
                        if _queue_state_is_active(folder, queue_name):
                            if hold_time:
                                time.sleep(hold_time)
                            break
                    elif verbose and not silent:
                        silent = True
                        _print_queue_status("HOLDING", hold_time)
                    _wait_for_window(10, tolerance=0.001)
                if verbose:
                    _print_queue_status("QUEUING")
                confirmed = False
                if _random_second_frac() < 4.5:
                    _write_with_retry(folder, queue_len_name, session_id)
                    if _random_second_frac() < 5:
                        _wait_for_window(6, tolerance=0.001)
                        confirmed = _queue_match(folder, queue_len_name, session_id)
                if confirmed and _queue_state_is_active(folder, queue_name):
                    if verbose:
                        _print_queue_status("DEQUEUE")
                    if _update_queue_state(folder, queue_name, new_id=session_id):
                        break
                silent = True
                hold_time = max(hold_time + 0.05, 0)
                _print_queue_status("HOLDING", hold_time)
                _wait_for_window(10, tolerance=0.001)
            except (FileNotFoundError, OSError, PermissionError):
                hold_time = max(hold_time + 0.05, 0)
                silent = True
                _print_queue_status("HOLDING", hold_time)
                _wait_for_window(10, tolerance=0.001)
                retries += 1
                if retries > 12:
                    raise
                time.sleep(0.001)
    content = _with_timeout(_read_majority, 15, txt_name, folder)
    if not ignore_memory and content and len(content) >= _MAX_QUEUE_LEN:
        raise MemoryError(
            f"Memory full:maximum allowed length is {_MAX_QUEUE_LEN:,} rows. Please delete/trim to free up space."
        )
    return content


class ScreenBuffer:
    EMOJI_STATES = {0: "🟢", 1: "🟡", 2: "🔴"}
    FILLER = "<<FILLER>>"

    def __init__(
        self,
        wait: bool = True,
        log_file: Optional[str] = None,
        max_main: Optional[int] = None,
        max_wait: Optional[int] = None,
        max_display: Optional[int] = None,
        reset: bool = False,
        header: Optional[str] = None,
        header_alignment=None,
        footer: Optional[str] = None,
        footer_alignment=None,
        show_header: Optional[bool] = None,
        show_footer: Optional[bool] = None,
        silent_display=None,
        only_display=None,
        auto_clean_edges: bool = False,
        auto_clean_silent_only_display: bool = False,
        shift_max_display: bool = True,
    ) -> None:
        self.buffer: list = []
        self.wait = wait
        self.silent_display = self._validate_silent_display(silent_display)
        self.only_display = self._validate_silent_display(only_display)
        self.max_main = max_main
        self.max_wait = max_wait
        self.max_display = max_display
        self.shift_max_display = shift_max_display
        self.auto_clean_edges = auto_clean_edges
        self.auto_clean_silent_only_display = auto_clean_silent_only_display
        if (self.max_wait is not None and self.max_display is not None) and self.max_wait < self.max_display:
            raise ValueError("max_wait cannot be less than max_display")
        self.header = header if isinstance(header, str) else None
        self.footer = footer if isinstance(footer, str) else None
        self.show_header = show_header if show_header is not None else bool(self.header)
        self.show_footer = show_footer if show_footer is not None else bool(self.footer)
        self.header_alignment = header_alignment
        self.footer_alignment = footer_alignment
        self.buffer_lock = threading.RLock()
        self.file_lock = threading.RLock()
        if log_file:
            self.log_file = self._prepare_log_path(log_file)
            base, ext = os.path.splitext(self.log_file)
            self.wait_log_file = f"{base}_wait{ext}"
            self.header_file = f"{base}_header{ext}"
            self.footer_file = f"{base}_footer{ext}"
        else:
            self.log_file = None
            self.wait_log_file = None
            self.header_file = None
            self.footer_file = None
        if reset:
            self._reset_all()
        self.refresh_buffer_from_wait_log()
        if not self.wait:
            self.display()
        self.alignments: dict = {}

    def _validate_silent_display(self, value):
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, list):
            for i in value:
                if not isinstance(i, int):
                    raise ValueError("silent_display list must contain integers")
            return value
        if isinstance(value, slice):
            return value
        if isinstance(value, str):
            if value.lower() == "all":
                return value.lower()
            raise ValueError("silent_display string must be 'all'")
        raise ValueError("Invalid silent_display value")

    def refresh_buffer_from_wait_log(self) -> None:
        if self.wait_log_file and os.path.exists(self.wait_log_file):
            try:
                with open(self.wait_log_file, "r", encoding="utf-8") as fh:
                    content = fh.read()
                if content.strip() and not self.buffer:
                    with self.buffer_lock:
                        self.buffer = content.splitlines()
            except Exception:
                pass

    def _reset_all(self) -> None:
        with self.buffer_lock:
            self.buffer.clear()
        if self.wait_log_file:
            try:
                with self.file_lock, open(self.wait_log_file, "w", encoding="utf-8") as fh:
                    fh.write("")
            except Exception:
                pass
        if self.header_file:
            try:
                with self.file_lock, open(self.header_file, "w", encoding="utf-8") as fh:
                    fh.write(self.header if self.header is not None else "")
            except Exception:
                pass
        if self.footer_file:
            try:
                with self.file_lock, open(self.footer_file, "w", encoding="utf-8") as fh:
                    fh.write(self.footer if self.footer is not None else "")
            except Exception:
                pass

    def _prepare_log_path(self, name: str) -> str:
        folder = "logs"
        if not os.path.exists(folder):
            os.makedirs(folder)
        name = self._ensure_txt_extension(name)
        return os.path.join(folder, name)

    def _ensure_txt_extension(self, name: str) -> str:
        return name if name.lower().endswith(".txt") else f"{name}.txt"

    def get_header(self) -> str:
        if not self.show_header or self.header is None:
            return ""
        raw = ""
        if self.header_file and os.path.exists(self.header_file):
            try:
                with open(self.header_file, "r", encoding="utf-8") as fh:
                    content = fh.read()
                    raw = content if content else self.header or ""
            except Exception:
                raw = self.header or ""
        else:
            raw = self.header or ""
        if self.header_alignment:
            try:
                raw = align_text(raw, self.header_alignment)
            except Exception:
                pass
        return raw

    def set_header(self, value: str, display: bool = True) -> None:
        self.header = value if isinstance(value, str) else None
        if display and self.header_file:
            try:
                with open(self.header_file, "w", encoding="utf-8") as fh:
                    fh.write(self.header if self.header is not None else "")
            except Exception:
                pass
        if self.header:
            self.show_header = True

    def clear(self) -> None:
        wipe_screen(clear_first=True)

    def configure(self, **kwargs) -> None:
        silent = kwargs.get("silent_display", None)
        only = kwargs.get("only_display", None)
        if silent is not None and only is not None:
            raise ValueError("silent_display and only_display cannot be used simultaneously")
        for key in ["silent_display", "only_display"]:
            if key in kwargs:
                kwargs[key] = self._validate_silent_display(kwargs[key])
        for key, value in kwargs.items():
            if key == "header":
                self.set_header(value, display=True)
            elif key == "footer":
                self.set_footer(value, display=True)
            elif key == "show_header":
                self.show_header = bool(value)
            elif key == "show_footer":
                self.show_footer = bool(value)
            elif key == "silent_display":
                self.silent_display = value
                self.only_display = None
            elif key == "only_display":
                self.only_display = value
                self.silent_display = None
            elif key == "log_file":
                self.log_file = self._prepare_log_path(value)
                base, ext = os.path.splitext(self.log_file)
                self.wait_log_file = f"{base}_wait{ext}"
                self.header_file = f"{base}_header{ext}"
                self.footer_file = f"{base}_footer{ext}"
            elif key in {
                "wait",
                "max_main",
                "max_wait",
                "max_display",
                "shift_max_display",
                "auto_clean_edges",
                "auto_clean_silent_only_display",
            }:
                setattr(self, key, value)
            elif hasattr(self, key):
                setattr(self, key, value)
        if (self.max_wait is not None and self.max_display is not None) and self.max_wait < self.max_display:
            raise ValueError("max_wait cannot be less than max_display")
        if not self.wait:
            self.display()

    def remove(self, index, keyword: Optional[str] = None, exact_token: bool = True) -> None:
        with self.buffer_lock:
            if not (isinstance(index, int) or isinstance(index, slice)):
                raise TypeError("Index must be int or slice")

            def _match(value: str) -> bool:
                if keyword is None:
                    return True
                lower = value.lower()
                key = keyword.lower()
                if exact_token:
                    tokens = lower.split()
                    return key in tokens
                return key in lower

            if isinstance(index, int):
                if index < 0:
                    index += len(self.buffer)
                if not 0 <= index < len(self.buffer):
                    raise IndexError("Index out of range")
                if _match(self.buffer[index]):
                    self.buffer.pop(index)
                    self.alignments.pop(index, None)
            else:
                indices = list(range(*index.indices(len(self.buffer))))
                new_buffer: list = []
                new_align: dict = {}
                for i, value in enumerate(self.buffer):
                    if i in indices and _match(value):
                        continue
                    new_buffer.append(value)
                    if i in self.alignments:
                        new_align[len(new_buffer) - 1] = self.alignments[i]
                self.buffer = new_buffer
                self.alignments = new_align
        if not self.wait:
            self.display()

    def _trim_wait_log_file(self) -> None:
        if not self.wait_log_file or self.max_wait is None:
            return
        try:
            with self.file_lock, open(self.wait_log_file, "r+", encoding="utf-8") as fh:
                lines = fh.readlines()
                if len(lines) > self.max_wait:
                    lines = lines[-self.max_wait :]
                    fh.seek(0)
                    fh.truncate()
                    fh.writelines(lines)
        except Exception:
            pass

    def clear_buffer(self) -> None:
        with self.buffer_lock:
            self.buffer.clear()
            self.alignments.clear()
        if self.wait_log_file:
            try:
                with self.file_lock, open(self.wait_log_file, "w", encoding="utf-8") as fh:
                    fh.write("")
            except Exception:
                pass
        if not self.wait:
            self.display()

    def reset(self) -> None:
        with self.buffer_lock:
            self.buffer.clear()
            self.alignments.clear()
        self.header = None
        self.footer = None
        self.show_header = False
        self.show_footer = False
        if self.wait_log_file:
            try:
                with self.file_lock, open(self.wait_log_file, "w", encoding="utf-8") as fh:
                    fh.write("")
            except Exception:
                pass
        if self.header_file:
            try:
                with self.file_lock, open(self.header_file, "w", encoding="utf-8") as fh:
                    fh.write("")
            except Exception:
                pass
        if self.footer_file:
            try:
                with self.file_lock, open(self.footer_file, "w", encoding="utf-8") as fh:
                    fh.write("")
            except Exception:
                pass
        if not self.wait:
            self.display()

    def get_footer(self) -> str:
        if not self.show_footer or self.footer is None:
            return ""
        raw = ""
        if self.footer_file and os.path.exists(self.footer_file):
            try:
                with open(self.footer_file, "r", encoding="utf-8") as fh:
                    content = fh.read()
                    raw = content if content else self.footer or ""
            except Exception:
                raw = self.footer or ""
        else:
            raw = self.footer or ""
        if self.footer_alignment:
            try:
                raw = align_text(raw, self.footer_alignment)
            except Exception:
                pass
        return raw

    def set_footer(self, value: str, display: bool = True) -> None:
        self.footer = value if isinstance(value, str) else None
        if display and self.footer_file:
            try:
                with open(self.footer_file, "w", encoding="utf-8") as fh:
                    fh.write(self.footer if self.footer is not None else "")
            except Exception:
                pass
        if self.footer:
            self.show_footer = True
        if not self.wait:
            self.display()

    def put(
        self,
        text: str,
        level: int = 0,
        index: Optional[int] = None,
        filler=None,
        alignment=None,
    ) -> None:
        if not self.buffer:
            self.refresh_buffer_from_wait_log()
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        emoji = self.EMOJI_STATES.get(level, "🟢")
        if not isinstance(text, str):
            text = str(text)
        filler = self.FILLER if filler is None else filler
        with self.buffer_lock:
            if index is None:
                index = len(self.buffer)
                self.buffer.append(text)
            else:
                if index < 0:
                    index += len(self.buffer)
                if index < 0:
                    raise IndexError("Negative index out of range after adjustment")
                if index >= len(self.buffer):
                    self.buffer.extend([filler] * (index - len(self.buffer)))
                    self.buffer.append(text)
                else:
                    self.buffer[index] = text
            if alignment is not None:
                self.alignments[index] = alignment
        if self.wait_log_file:
            try:
                with self.file_lock, open(self.wait_log_file, "w", encoding="utf-8") as fh:
                    with self.buffer_lock:
                        lines: list = []
                        for i, value in enumerate(self.buffer):
                            if value == self.FILLER:
                                lines.append("")
                            else:
                                align = self.alignments.get(i, "left")
                                lines.append(align_text(value, align))
                        fh.write("\n".join(lines) + "\n")
                self._trim_wait_log_file()
            except Exception:
                pass
        if self.log_file:
            try:
                with self.file_lock:
                    with open(self.log_file, "a", encoding="utf-8") as fh:
                        entry = f"{stamp} {emoji} {text}"
                        if index is not None:
                            fh.write(f"{entry} [📍{index}]\n")
                        else:
                            fh.write(f"{entry}\n")
                if self.max_main is not None:
                    try:
                        with self.file_lock, open(self.log_file, "r+", encoding="utf-8") as fh:
                            lines = fh.readlines()
                            if len(lines) > self.max_main:
                                lines = lines[-self.max_main :]
                                fh.seek(0)
                                fh.truncate()
                                fh.writelines(lines)
                    except Exception:
                        pass
            except Exception as exc:
                raise RuntimeError(f"Error writing to log file:{exc}")
        if not self.wait:
            self.display()

    def format_text_for_display(self) -> list:
        header = self.get_header()
        footer = self.get_footer()
        with self.buffer_lock:
            total = list(self.buffer)
            rows = [
                [value if value != self.FILLER else "", self.alignments.get(i, "left")] for i, value in enumerate(total)
            ]
        length = len(rows)
        if self.max_display is not None:
            if self.shift_max_display:
                start, end = 0, length
            else:
                start, end = max(length - self.max_display, 0), length
        else:
            start, end = 0, length
        self.display_range = (start, end)
        values = [rows[i][0] for i in range(start, end)]
        aligns = [rows[i][1] for i in range(start, end)]
        indices = list(range(start, end))
        count = len(values)
        if self.only_display is not None:
            try:
                if isinstance(self.only_display, str) and self.only_display.lower() == "all":
                    pass
                else:
                    visible = set()
                    if isinstance(self.only_display, list):
                        visible = set(self.only_display)
                    elif isinstance(self.only_display, int):
                        visible = {self.only_display}
                    elif isinstance(self.only_display, slice):
                        visible = set(range(len(total))[self.only_display])
                    values = [values[i] if indices[i] in visible else "" for i in range(count)]
                    aligns = [aligns[i] if indices[i] in visible else "left" for i in range(count)]
            except Exception:
                values = []
                aligns = []
        elif self.silent_display is not None:
            try:
                if isinstance(self.silent_display, str) and self.silent_display.lower() == "all":
                    values = [""] * count
                    aligns = ["left"] * count
                else:
                    hidden = set()
                    if isinstance(self.silent_display, list):
                        hidden = set(self.silent_display)
                    elif isinstance(self.silent_display, int):
                        hidden = {self.silent_display}
                    elif isinstance(self.silent_display, slice):
                        hidden = set(range(len(total))[self.silent_display])
                    values = ["" if indices[i] in hidden else values[i] for i in range(count)]
                    aligns = ["left" if indices[i] in hidden else aligns[i] for i in range(count)]
            except Exception:
                values = []
                aligns = []
        indices = indices[: len(values)]
        aligns = aligns[: len(values)]
        if self.auto_clean_silent_only_display:
            new_values: list = []
            new_aligns: list = []
            new_indices: list = []
            for i, value in enumerate(values):
                if value.strip() != "":
                    new_values.append(value)
                    new_aligns.append(aligns[i])
                    new_indices.append(indices[i])
            values, aligns, indices = new_values, new_aligns, new_indices
        if self.max_display is not None:
            values = values[-self.max_display :]
            aligns = aligns[-len(values) :]
            indices = indices[-len(values) :]
        if self.auto_clean_edges:
            while values and values[0].strip() == "":
                values.pop(0)
                aligns.pop(0)
                indices.pop(0)
            while values and values[-1].strip() == "":
                values.pop()
                aligns.pop()
                indices.pop()
            if values:
                values.insert(0, "")
                aligns.insert(0, "left")
                indices.insert(0, -1)
                values.append("")
                aligns.append("left")
                indices.append(-1)
        rows: list = []
        for value, align in zip(values, aligns):
            rows.append([value, align])
        output: list = []
        if self.show_header and header:
            output.append([header.rstrip("\n"), self.header_alignment or "left"])
        output.extend(rows)
        if self.show_footer and footer:
            output.append([footer.lstrip("\n"), self.footer_alignment or "left"])
        return output

    def to_string(self) -> str:
        rows = self.format_text_for_display()
        return "\n".join(align_text(value, align) for value, align in rows)

    def display(self) -> None:
        wipe_screen(clear_first=True)
        rows = self.format_text_for_display()
        for value, align in rows:
            if align:
                print(align_text(value, align))
            else:
                print(value)

    def inspect(self) -> None:
        with self.buffer_lock:
            for i, value in enumerate(self.buffer):
                print(f"[{i}]:{value!r}")


def info_panel(txt_name: str, display: bool = True) -> dict:
    return info(txt_name, display=display)


def help() -> None:
    print(
        "WithOpen — lightweight nested-json store. Use w/r/a/d/backup/snapshot/debug/remove/hide/unhide/listdir/info/consoles/warning."
    )


def w(txt_name: str, data, is2d: Optional[bool] = None) -> None:
    _write(txt_name, data, is2d)


def r(txt_name: str, index=None, default: list = [], notify_new: bool = False):
    return _read(txt_name, index=index, default=default, notify_new=notify_new)


def a(txt_name: str, data, is2d: Optional[bool] = None) -> list:
    return _append(txt_name, data, is2d)


def d(
    txt_name: str,
    del_list: list = [],
    index=None,
    cutoff: Optional[int] = None,
    keep: Optional[int] = None,
    reverse: bool = False,
    auto_trim_len: Optional[int] = None,
) -> tuple:
    return _delete(
        txt_name,
        del_list=del_list,
        index=index,
        cutoff=cutoff,
        keep=keep,
        reverse=reverse,
        auto_trim_len=auto_trim_len,
    )


def backup(txt_name: str, display: bool = True) -> None:
    return _backup(txt_name, display=display)


def snapshot(
    txt_name: str,
    unit: str,
    gap: float,
    trim: Optional[int] = None,
    day_start_hour: int = 0,
    display: bool = True,
) -> None:
    return _snapshot(txt_name, unit, gap, trim=trim, day_start_hour=day_start_hour, display=display)


def backdate(
    txt_name: str,
    unit: str,
    gap: float = 1,
    day_start_hour: int = 0,
) -> str:
    return check_date_change(txt_name, unit=unit, gap=gap, day_start_hour=day_start_hour)


def debug(
    txt_name: str,
    is2d: Optional[bool] = None,
    length: Optional[int] = None,
    row_length: Optional[int] = None,
    display: bool = True,
) -> Optional[dict]:
    return _debug(txt_name, is2d=is2d, length=length, row_length=row_length, display=display)


def remove(txt_name: str, display: bool = True) -> None:
    return _remove(txt_name, display=display)


def hide(txt_name: str, display: bool = True) -> None:
    return _hide(txt_name, display=display)


def unhide(txt_name: str, display: bool = True) -> None:
    return _unhide(txt_name, display=display)


def listdir(display: bool = True) -> list:
    return _listdir(display=display)


def consoles(txt_name: str, multiple: bool, alert: bool) -> None:
    return _consoles(txt_name, multiple, alert)


def warning(multiple: bool) -> None:
    return _warning(multiple)


def restore(recency: int = 0, write: bool = False, display: bool = True) -> str:
    return _restore(recency=recency, write=write, display=display)


__all__ = [
    "w",
    "r",
    "a",
    "d",
    "backup",
    "snapshot",
    "backdate",
    "debug",
    "remove",
    "hide",
    "unhide",
    "listdir",
    "info",
    "help",
    "consoles",
    "warning",
    "restore",
    "ScreenBuffer",
    "wipe_screen",
    "wipe_screen_soft",
    "align_text",
    "colorize",
    "stylize",
    "loop_progress",
    "future_datetime",
    "parse_date_string",
    "time_ago",
    "time_between",
    "check_date_change",
    "unhide_folder",
    "hide_folder",
    "is_visible",
    "write_all_files",
    "majority_vote_file_reader",
    "read_txt",
    "corruption_tag",
]
