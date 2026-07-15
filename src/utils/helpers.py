import time
import random
import re
from typing import Any, Callable

def retry_on_rate_limit(max_retries: int = 5, initial_delay: float = 3.0, backoff_factor: float = 2.0) -> Callable:
    """
    Decorator that retries a function with exponential backoff and random jitter
    when transient network errors, rate limits (HTTP 429), or service limits (HTTP 503) occur.
    If the error message contains an explicit retry instruction (e.g. "please retry in 36s"),
    it extracts the time dynamically and waits for that duration plus a small buffer.

    Args:
        max_retries (int): Maximum number of attempts.
        initial_delay (float): Delay in seconds before the first retry (if no exact time is parsed).
        backoff_factor (float): Multiplier for the delay after each retry.
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    err_str = str(e).lower()
                    
                    # Detect rate limits (429), service drops (503), or quota blocks
                    is_transient = any(
                        val in err_str for val in [
                            "429", 
                            "503", 
                            "quota", 
                            "rate limit", 
                            "rate_limit", 
                            "service unavailable", 
                            "resource exhausted"
                        ]
                    )
                    
                    # If it's a transient error and we have retries remaining, sleep and retry
                    if is_transient and attempt < max_retries - 1:
                        # Attempt to parse dynamic wait time requested by API proxy
                        # e.g., "please retry in 36.37587299s."
                        match = re.search(r"please retry in\s*([\d\.]+)\s*(s|second|seconds)?", err_str)
                        if match:
                            try:
                                sleep_time = float(match.group(1)) + 2.0
                                print(f"[Attempt {attempt + 1}/{max_retries}] Rate limit block. Extracted delay: sleeping for {sleep_time:.2f} seconds...")
                            except ValueError:
                                sleep_time = delay + random.uniform(0.1, 1.0)
                                print(f"[Attempt {attempt + 1}/{max_retries}] Rate limit block. Falling back to exponential sleep for {sleep_time:.2f} seconds...")
                        else:
                            sleep_time = delay + random.uniform(0.1, 1.0)
                            print(f"[Attempt {attempt + 1}/{max_retries}] Rate limit block. Sleeping for {sleep_time:.2f} seconds (exponential)...")
                        
                        time.sleep(sleep_time)
                        if not match:
                            delay *= backoff_factor
                    else:
                        raise e
            return None  # Fallback
        return wrapper
    return decorator


def sanitize_ai_output(text: str) -> str:
    """
    Sanitizes AI-generated output to prevent raw HTML/CSS leaks, markdown tables,
    xml tags, developer templates, and prompt leakage.

    Args:
        text (str): The raw AI-generated string response.

    Returns:
        str: A clean, human-readable plain text string.
    """
    if not text or not isinstance(text, str):
        return text if text is not None else ""

    # 1. Strip Markdown Code Fences (e.g. ```json, ```html, ```, etc.)
    text = re.sub(r"```[a-zA-Z0-9_-]*", "", text)

    # 2. Strip scripts and styles blocks completely
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)

    # 3. Strip general XML / HTML tags (e.g., <div>, </span>)
    text = re.sub(r"<[^>]+>", "", text)

    # 4. Strip Markdown tables and row layout indicators
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        trimmed = line.strip()
        # Drop lines starting/ending with | or containing multiple | or divider dashes
        if (
            trimmed.startswith("|") 
            or trimmed.endswith("|") 
            or ("|" in trimmed and "---" in trimmed) 
            or (trimmed.count("|") >= 2)
        ):
            continue
        cleaned_lines.append(line)
    text = "\n".join(cleaned_lines)

    # 5. Eliminate prompt leakage system markers if present
    leak_markers = [
        "System Instruction:", "JSON Schema:", "Developer Instruction:",
        "Assistant Prompt:", "Instructions:", "Response Schema:"
    ]
    for marker in leak_markers:
        if marker.lower() in text.lower():
            text = re.sub(re.escape(marker), "", text, flags=re.IGNORECASE)

    # 6. Normalize Whitespace (collapse spaces and keep max 2 consecutive newlines)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
