"""
Some URL loading methods I jacked from the web while reading up on how to start.
No cops allowed
MDK
"""
from contextlib import closing
from requests.exceptions import RequestException
from requests import get


def simple_get(url):
    """
    Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the
    text content, otherwise return None.
    """
    try:
        Log.Debug("[url_loading] Requesting " + str(url))
        with closing(get(url, stream=True, headers = {'Accept-Encoding': 'identity'})) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None

    except RequestException as exc:
        log_error('Error during requests to {0} : {1}'.format(url, str(exc)))
        return None


def is_good_response(resp):
    """
    Returns True if the response seems to be HTML, False otherwise.
    """
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1)


def log_error(exc):
    """
    It is always a good idea to log errors.
    This function just prints them, but you can
    make it do anything.
    """
    Log.Error("[url_loading] " + exc)