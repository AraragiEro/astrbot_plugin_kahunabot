import httplib2
import google_auth_httplib2
from googleapiclient import discovery
from google.oauth2 import service_account

class GoogleSheetApi:
    def __init__(self):
        self._server = None

    def get_proxy_http(self):
        proxy_info = httplib2.ProxyInfo(
            httplib2.socks.PROXY_TYPE_HTTP,
            "127.0.0.1",
            7890
        )
        return httplib2.Http(proxy_info=proxy_info)

    def get_credentials(self):
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = service_account.Credentials.from_service_account_file(
            'F:\\WorkSpace\\GIT\\kahuna_bot\\AstrBot\\data\\plugins\\kahuna_bot\\credentials.json',
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
        if self._server is None:
            self._server = self.get_service()
        return self._server

google_sheet_api = GoogleSheetApi()