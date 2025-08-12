import os

# Optional: Load environment variables from .env file for local development
# Only import and use python-dotenv if available, but don't require it in production
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not available, continue without it
    pass


def get_env_variable(name, default=None, required=False, cast_type=None):
    """Get environment variable with optional default, type casting, and requirement checking.
    
    Args:
        name (str): Environment variable name
        default: Default value if not found
        required (bool): If True, raises RuntimeError when variable is missing
        cast_type: Type to cast the value to (e.g., int, float)
    
    Returns:
        The environment variable value, optionally cast to specified type
    
    Raises:
        RuntimeError: If required variable is not set
        ValueError: If type casting fails
    """
    value = os.environ.get(name, default)
    if required and value is None:
        raise RuntimeError(f"Environment variable {name} is required.")
    if cast_type and value is not None:
        try:
            value = cast_type(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Failed to cast environment variable {name} to {cast_type.__name__}: {e}")
    return value


# Required environment variables (secrets)
TELEGRAM_BOT_TOKEN = get_env_variable('TELEGRAM_BOT_TOKEN', required=True)
TELEGRAM_CHANNEL_ID = get_env_variable('TELEGRAM_CHANNEL_ID', required=True)
ADMIN_TELEGRAM_ID = get_env_variable('ADMIN_TELEGRAM_ID', required=True)

# Optional environment variables with defaults
MAX_FILE_SIZE_MB = get_env_variable('MAX_FILE_SIZE_MB', default=35, cast_type=int)
DEFAULT_DPI = get_env_variable('DEFAULT_DPI', default=96, cast_type=int)

# Note: Secrets are never logged or printed to maintain security
# This config will work in both local development (with optional .env file)
# and production environments (using environment variables or GitHub Secrets)
