from requests_oauthlib import OAuth2Session
from ..config_server.config import config

# import logger
from ..log_server import logger

LOCAL_HTTP_ADD = "http://localhost:4567"

OAUTH_URL = "https://login.eveonline.com/v2/oauth/token"

PROXY = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890"
}

callback_url = LOCAL_HTTP_ADD + '/auth/eve/callback'

oauth = OAuth2Session(
    client_id=config['EVE']['CLIENT_ID'],
    redirect_uri=callback_url,
    scope=[k for k, v in dict(config['ESI']).items() if v == 'true']
)

def get_auth_url():
    authorizationUrl, state = oauth.authorization_url('http://login.eveonline.com/oauth/authorize')
    return authorizationUrl

def get_token(AUTH_RES):
    secret_key = config['EVE']['SECRET_KEY']
    oauth.fetch_token(
        OAUTH_URL,
        authorization_response=AUTH_RES,
        client_secret=secret_key #, proxies=PROXY
    )

    access_token = oauth.token.get("access_token")
    refresh_token = oauth.token.get("refresh_token")
    expires_at = oauth.token.get("expires_at")

    return access_token, refresh_token, expires_at

def refresh_token(refresh_token):
    client_id = config['EVE']['CLIENT_ID']
    secret_key = config['EVE']['SECRET_KEY']
    newtocker_dict = oauth.refresh_token(
        OAUTH_URL,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=secret_key #, proxies=PROXY
    )

    logger.info(f"token refreshed. {newtocker_dict}")
    """
    {
        "access_token",
        "token_type",
        "expires_in", [second]
        "refresh_token",
        "expires_at"
    }
    """
    return newtocker_dict