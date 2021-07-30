from slyguy.exceptions import Error

from .language import _

class APIError(Error):
    pass

ERROR_MAP = {
    'not-entitled': _.NOT_ENTITLED,
    'blackout': _.GEO_ERROR,
    'com.espn.watch.api.AccessDeniedException':  _.GEO_ERROR,
    'noAuthz':  _.NOT_ENTITLED,
}

def check_errors(data, error=_.API_ERROR):
    if not type(data) is dict:
        return

    if data.get('status') in (400, 403):
        message = ERROR_MAP.get(data.get('exception')) or ERROR_MAP.get(data.get('message')) or data.get('message') or data.get('details') or data.get('exception')
        raise APIError(_(error, msg=message))

    elif data.get('errors'):
        error_msg = ERROR_MAP.get(data['errors'][0].get('code')) or data['errors'][0].get('description') or data['errors'][0].get('code')
        raise APIError(_(error, msg=error_msg))

    elif data.get('error'):
        error_msg = ERROR_MAP.get(data.get('error_code')) or data.get('error_description') or data.get('error_code')
        raise APIError(_(error, msg=error_msg))
