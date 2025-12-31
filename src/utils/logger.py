import logging
import sys
import io


# Configure logging with UTF-8 support for Windows compatibility
def setup_logger(
    name: str = "api_governance", level: int = logging.INFO
) -> logging.Logger:
    """Configure and return a logger instance with UTF-8 encoding support for emojis"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create console handler with UTF-8 encoding
    # Wrap stdout to ensure UTF-8 encoding on Windows (fixes emoji UnicodeEncodeError)
    # Note: sys.platform == 'win32' is True for ALL Windows versions (32-bit, 64-bit, Win10, Win11)
    if sys.platform == "win32" or sys.platform.startswith("win"):
        # On Windows, force UTF-8 encoding for stdout
        utf8_stdout = io.TextIOWrapper(
            sys.stdout.buffer,
            encoding="utf-8",
            errors="replace",  # Replace unencodable chars instead of crashing
            line_buffering=True,
        )
        console_handler = logging.StreamHandler(utf8_stdout)
    else:
        console_handler = logging.StreamHandler(sys.stdout)

    console_handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)

    # Add handler to logger
    if not logger.handlers:
        logger.addHandler(console_handler)

    return logger


# Create default logger instance
logger = setup_logger()
