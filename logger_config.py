import logging
import sys

def setup_logging(debug=True):
    """
    Configures the root logger for the entire application.

    Args:
        debug (bool): If True, the logging level is set to DEBUG.
                      If False, it's set to INFO.
    """
    # Determine the logging level based on the debug flag
    log_level = logging.DEBUG if debug else logging.INFO

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Create a handler to write log messages to the console (stderr by default)
    # If a handler already exists, don't add another one
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
    
        # Create a formatter to define the log message's structure
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
    
        # Add the handler to the root logger
        root_logger.addHandler(handler)

    logging.info(f"Logging configured with level: {'DEBUG' if debug else 'INFO'}")