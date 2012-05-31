import os

SOCKBASE = "orionsocket.%s"

def find_sockfile(display=None):
    """
        Finds the appropriate socket file.
    """
    if not display:
        display = os.environ.get("DISPLAY")
    if not display:
        display = ":0.0"
    if '.' not in display:
        display += '.0'
    cache_directory = os.path.expandvars('$XDG_CACHE_HOME')
    if cache_directory == '$XDG_CACHE_HOME': #if variable wasn't set
        cache_directory = os.path.expanduser("~/.cache")
    if not os.path.exists(cache_directory):
        os.makedirs(cache_directory)
    return os.path.join(cache_directory, SOCKBASE%display)