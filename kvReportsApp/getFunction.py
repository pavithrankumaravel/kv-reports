import datetime
import numpy as np
import pandas as pd
import re

def round_to_even(n):
    # If n is between 0 and less than 1.5, return 1
    if 0 <= n < 1.5:
        return 1

    rounded = round(n)
    # If rounded is odd, adjust to the nearest even
    if rounded % 2 != 0:
        if n > rounded:
            return rounded + 1
        else:
            return rounded - 1
    return rounded


def round_for_without_chain(n):
    # If n is between 0.75 and less than 1.5, return 1
    if 0 <= n < 0.75:
        return 0.5
    elif 0.75 <= n < 1.5:
        return 1

    rounded = round(n)
    return rounded

def normalize_subproduct(sp):
    """
    Removes all length/version prefixes like:
    - 18", 20", 23", 2V, 3V, 5BALLS, etc.
    Converts to uppercase and trims.
    """
    if not sp:
        return ""

    # Remove starting patterns like 18", 20", 2V, 3V, 5BALLS, etc.
    sp = sp.strip().upper()
    sp = re.sub(r'^(?:\d{2}|[2-5]V|[2-9]BALLS)[\"\'\s\-]*', '', sp)

    # Remove starting quotes or other junk if still present
    sp = re.sub(r'^["\'\s]+', '', sp)

    # Normalize multiple spaces to single
    return re.sub(r'\s+', ' ', sp).strip()