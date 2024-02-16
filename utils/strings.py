import hashlib
import re


def hash_of_text(input: str):
    """Hashes a string to a short, unique string given an input string."""
    # Use SHA256 for a secure hash with a reasonable length
    hash_digest = hashlib.sha256(
        input.encode()
    ).hexdigest()  # Encode to bytes for hashing
    # Truncate to 16 characters for a shorter folder name
    short_hash = hash_digest[-16:]
    # short_hash = hash_digest
    # Create a unique folder name by appending a 4-digit random string
    unique_folder_name = short_hash
    return unique_folder_name


def extract_times_to_seconds(text):
    """Extracts time segments from text and converts them to seconds.

    Args:
        text (str): The input text containing time segments.

    Returns:
        list: A list of tuples, where each tuple contains the extracted time segment
              as a string and its corresponding duration in seconds.
    """

    time_regex = [
        r"^(\d{1,2}):+(\d{1,2}):+(\d{1,2})[^0-9:]+",  # Matches HH:MM:SS
        r"^(\d{1,2}):+(\d{1,2})[^0-9:]+",
    ]  # Matches HH:MM
    time_in_seconds = []
    for regex in time_regex:
        time_segments = re.findall(regex, text, re.MULTILINE)
        for tm_seg in time_segments:
            hours = "0"
            if len(tm_seg) == 2:
                minutes, seconds = tm_seg
            elif len(tm_seg) == 3:
                hours, minutes, seconds = tm_seg
            seconds_total = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
            time_in_seconds.append(seconds_total)
    time_in_seconds.sort()
    return time_in_seconds


def seconds_to_hh_mm_ss(seconds):
    """
    Converts a given number of seconds to a string in hh:mm:ss format.

    Args:
        seconds: An integer representing the number of seconds.

    Returns:
        A string in hh:mm:ss format, or "00:00:00" if seconds is negative.
    """

    if seconds < 0:
        return "00:00:00"

    hours = seconds // 3600  # Get hours by dividing by total seconds in an hour
    seconds %= 3600  # Get remaining seconds after hours calculation

    minutes = seconds // 60  # Get minutes by dividing by total seconds in a minute
    seconds %= 60  # Get remaining seconds after minutes calculation

    # Format hour, minute, and second values with leading zeros
    hours_str = f"{hours:02d}"
    minutes_str = f"{minutes:02d}"
    seconds_str = f"{seconds:02d}"

    return f"{hours_str}:{minutes_str}:{seconds_str}"
