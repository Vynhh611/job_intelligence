"""Read deployment settings without printing or persisting secrets."""
import os
import sys


def setting(name, default=''):
    value = os.environ.get(name)
    if value is not None:
        return value
    if 'streamlit' in sys.modules:
        try:
            return str(sys.modules['streamlit'].secrets.get(name, default))
        except Exception:
            pass
    return default
