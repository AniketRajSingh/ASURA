import re
import logging
from datetime import timedelta

# Import project-specific modules for logging and configuration.
# These imports assume the project's structure; adjust if module names differ.
try:
    from settings import settings as config
except Exception as exc:  # pragma: no cover
    # Configuration may not be needed for this utility; log and continue.
    logging.getLogger(__name__).warning(
        "settings could not be imported: %s", exc
    )
    config = None

try:
    from skills.logger import log_app, log_audit
except Exception as exc:  # pragma: no cover
    # Fallback to the standard logging module if core.logger is unavailable.
    logging.getLogger(__name__).warning(
        "core.logger module could not be imported: %s", exc
    )
    log_app = logging.getLogger(__name__).info
    log_audit = logging.getLogger(__name__).debug


__all__ = ["parse_duration", "parse_duration_to_timedelta"]


def _parse_token(token: str) -> int:
    """
    Convert a single duration token into seconds.

    Parameters
    ----------
    token : str
        A string token like ``"1h"`` or ``"30m"``.

    Returns
    -------
    int
        Duration in seconds.

    Raises
    ------
    ValueError
        If the token does not match the expected pattern.
    """
    token = token.strip()
    pattern = re.compile(r"(?P<value>\d+(?:\.\d+)?)(?P<unit>[dhms])$", re.IGNORECASE)
    match = pattern.match(token)
    if not match:
        raise ValueError(f"Invalid duration token: '{token}'")

    value = float(match.group("value"))
    unit = match.group("unit").lower()

    if unit == "d":
        multiplier = 86400
    elif unit == "h":
        multiplier = 3600
    elif unit == "m":
        multiplier = 60
    elif unit == "s":
        multiplier = 1
    else:  # pragma: no cover
        raise ValueError(f"Unknown time unit: '{unit}'")

    return int(value * multiplier)


def parse_duration(duration_str: str) -> int:
    """
    Parse a human‑readable duration string into seconds.

    The function supports hours (h), minutes (m), seconds (s), and days (d).
    Multiple tokens may be separated by whitespace or not at all.

    Examples
    --------
    >>> parse_duration("1h 30m")
    5400
    >>> parse_duration("90m")
    5400
    >>> parse_duration("2h")
    7200
    >>> parse_duration("1.5h")
    5400
    >>> parse_duration("1d 2h 30m")
    93600

    Parameters
    ----------
    duration_str : str
        Human‑readable duration string.

    Returns
    -------
    int
        Total duration in seconds.

    Raises
    ------
    ValueError
        If the input string cannot be parsed.
    """
    if not isinstance(duration_str, str) or not duration_str.strip():
        msg = "Duration must be a non‑empty string."
        log_audit(msg)
        raise ValueError(msg)

    log_app(f"Attempting to parse duration: '{duration_str}'")

    try:
        # Normalize spaces: split on whitespace, then further split tokens that have unit
        # appended without space (e.g., "1h30m").
        # First, replace all unit letters with a space before them for consistent splitting.
        normalized = re.sub(r"(?<=[\d.])([dhms])", r" \1", duration_str.lower())
        tokens = normalized.split()
        total_seconds = 0
        for token in tokens:
            seconds = _parse_token(token)
            total_seconds += seconds
            log_audit(f"Token '{token}' parsed as {seconds} seconds.")
        log_app(f"Total parsed duration: {total_seconds} seconds.")
        return total_seconds
    except Exception as exc:
        log_audit(f"Failed to parse duration '{duration_str}': {exc}")
        raise ValueError(f"Could not parse duration string '{duration_str}': {exc}") from exc


def parse_duration_to_timedelta(duration_str: str) -> timedelta:
    """
    Convert a duration string to a :class:`datetime.timedelta` object.

    Parameters
    ----------
    duration_str : str
        Human‑readable duration string.

    Returns
    -------
    datetime.timedelta
        Duration represented as a timedelta.

    Raises
    ------
    ValueError
        If the input string cannot be parsed.
    """
    seconds = parse_duration(duration_str)
    return timedelta(seconds=seconds)