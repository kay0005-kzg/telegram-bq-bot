def format_number(value, width):
    """Format a number with commas and right-align it."""
    try:
        num = int(value)
        formatted = f"{num:,}"
    except (ValueError, TypeError):
        formatted = str(value)
    
    return formatted.rjust(width)

def truncate_text(text, max_width):
    """Truncate text to fit in the specified width."""
    text = str(text)
    if len(text) > max_width:
        return text[:max_width-1] + "…"
    return text.ljust(max_width)