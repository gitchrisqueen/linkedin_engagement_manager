import os

MISSING_CONSTANTS = []


def isTrue(s: str) -> bool:
    return s.lower() in ['true', '1', 't', 'y', 'yes']


def get_constanct_from_env(key: str, required: bool = False, default_value: str = None) -> str:
    if required:
        return os.environ[key]
    else:
        const = os.environ.get(key)
        if not const:
            MISSING_CONSTANTS.append(key)
            return default_value
        else:
            return const


# Get constants from GitHub Actions
try:
    IS_GITHUB_ACTION = isTrue(get_constanct_from_env('GITHUB_ACTION_TRUE', default_value='False'))
except KeyError:
    IS_GITHUB_ACTION = False

# Get constants from environment .env file
OPENAI_API_KEY = get_constanct_from_env('OPENAI_API_KEY')
LI_USER = get_constanct_from_env('LI_USER')
LI_PASSWORD = get_constanct_from_env('LI_PASSWORD')
SELENIUM_HUB_HOST=get_constanct_from_env('SELENIUM_HUB_HOST', default_value='selenium_hub')
SELENIUM_HUB_PORT=get_constanct_from_env('SELENIUM_HUB_PORT', default_value='4444')
SELENIUM_REGISTRATION_SECRET=get_constanct_from_env('SELENIUM_REGISTRATION_SECRET', default_value='secret')
HEADLESS_BROWSER = isTrue(get_constanct_from_env('HEADLESS_BROWSER', default_value='True'))
WAIT_DEFAULT_TIMEOUT = float(get_constanct_from_env('WAIT_DEFAULT_TIMEOUT', default_value='15'))
MAX_WAIT_RETRY = int(get_constanct_from_env('MAX_WAIT_RETRY', default_value='2'))
RETRY_PARSER_MAX_RETRY = int(get_constanct_from_env('RETRY_PARSER_MAX_RETRY', default_value='3'))
SHOW_ERROR_LINE_NUMBERS = isTrue(get_constanct_from_env('SHOW_ERROR_LINE_NUMBERS', default_value='False'))

NGROK_FREE_DOMAIN=get_constanct_from_env('NGROK_FREE_DOMAIN')
NGROK_API_PREFIX=get_constanct_from_env('NGROK_API_PREFIX')
# If both NGROK_FREE_DOMAIN and NGROK_API_PREFIX are not None then set API_BASE_URL as the concatenation of both
if NGROK_FREE_DOMAIN and NGROK_API_PREFIX:
    API_BASE_URL = f"https://{NGROK_API_PREFIX}.{NGROK_FREE_DOMAIN}"
else:
    API_BASE_URL = get_constanct_from_env('API_BASE_URL', default_value='http://localhost:8000')
NGROK_LIPREVIEW_PREFIX=get_constanct_from_env('NGROK_LIPREVIEW_PREFIX')
if NGROK_FREE_DOMAIN and NGROK_LIPREVIEW_PREFIX:
    LINKEDIN_PREVIEW_URL = f"https://{NGROK_LIPREVIEW_PREFIX}.{NGROK_FREE_DOMAIN}"
else:
    LINKEDIN_PREVIEW_URL = get_constanct_from_env('LINKEDIN_PREVIEW_URL', default_value='http://localhost:8081')

# Set other constants here
USE_DOCKER_BROWSER = isTrue(get_constanct_from_env('USE_DOCKER_BROWSER', default_value='False'))
