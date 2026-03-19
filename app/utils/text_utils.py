import re


def normalize_text(text: str) -> str:
    """Basic whitespace normalization."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def normalize_property_details(plot_no: str) -> str:
    """
    Standardize plot numbers.
    "Plot No 101" -> "101"
    "Plot # 101" -> "101"
    "No. 101" -> "101"
    """
    if not plot_no:
        return "Unknown"

    # Remove "Plot No", "Plot", "No", etc.
    # regex: ^(Plot|No|Plot No|Plot No.|#)\s*[:.\-]?\s*
    clean = re.sub(
        r"^(?:Plot\s*No\.?|Plot\s*#|Plot|No\.?|#)\s*[:.\-]?\s*",
        "",
        plot_no,
        flags=re.IGNORECASE,
    )

    return clean.strip()
