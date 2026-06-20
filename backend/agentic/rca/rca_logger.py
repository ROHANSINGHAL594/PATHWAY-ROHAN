# RCA logger that only activates when explicitly called
# Does not detect or log any events unless a logging function is invoked

import logging

_rca_logger = None
_logger_initialized = False

def get_rca_logger():
    """
    Get or initialize the RCA logger.
    Logger is only created when this function is explicitly called.
    No automatic event detection or logging occurs.
    
    Important logs (WARNING and above) are sent to MongoDB for visibility.
    All logs go to PostgreSQL.
    """
    global _rca_logger, _logger_initialized
    if not _logger_initialized:
        from lib.logger import setup_logging
        _rca_logger = setup_logging(
            level=logging.INFO,
            mongo_level=logging.WARNING,  # Only critical/important logs go to MongoDB
            fallback_file="rca_logs.log",
            mongo_collection="rca_events",
        )
        _logger_initialized = True
    return _rca_logger

# Lazy wrapper that only initializes when methods are called
class _LoggerWrapper:
    def __getattr__(self, name):
        # Only initialize and create logger when a method is actually called
        return getattr(get_rca_logger(), name)

rca_logger = _LoggerWrapper()