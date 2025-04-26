import httplib2
import google_auth_httplib2
from googleapiclient import discovery
from google.oauth2 import service_account

from ..log_server import logger
from ..config_server.config import config

class GoogleSheetApi:
    def __init__(self):
        self._server = None

    def get_proxy_http(self):
        proxy = config['APP']['PROXY']
        port = int(config['APP']['PORT'])
        proxy_info = httplib2.ProxyInfo(
            httplib2.socks.PROXY_TYPE_HTTP,
            proxy,
            port
        )
        return httplib2.Http(proxy_info=proxy_info)

    def get_credentials(self):
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        credentials_json = config['GOOGLE']['CREDENTIALS']
        credentials = service_account.Credentials.from_service_account_file(
            credentials_json,
            scopes=scopes
        )
        return credentials

    def get_service(self):
        credential = self.get_credentials()
        http_proxy = self.get_proxy_http()

        authorize_http = google_auth_httplib2.AuthorizedHttp(credential, http=http_proxy)
        service = discovery.build('sheets', 'v4', http=authorize_http)

        return service

    @property
    def server(self):
        try:
            if self._server is None:
                self._server = self.get_service()
            return self._server
        except Exception as e:
            logger.error(f"get_server error: {e}")
            raise


google_sheet_api = GoogleSheetApi()