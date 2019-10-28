import json
import oauthlib
import requests_oauthlib

#import logging
#import httplib
#httplib.HTTPConnection.debuglevel = 0
#logging.basicConfig(level=logging.DEBUG)

class tcc:
    def __init__(self, device_id, client_id=None, client_secret=None,
        redirect_uri=None, auth_url=None, token_url=None, scope=None,
        token_init=False, token_db=None):

        self.client_id = client_id
        self.client_secret = client_secret
        self.device_id = device_id
        self.redirect_uri = redirect_uri
        self.token_dict = {}
        self.token_url = token_url
        self.token_db = token_db
        self.auth_url=auth_url
        self.scope = scope or ['Basic Power']

        self.oauth = requests_oauthlib.OAuth2Session(
            self.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
            token=self.token_dict,
            auto_refresh_url=self.token_url,
            token_updater=self._update_tokens
        )

        # Do we need to intitialize our tokens?
        if token_init:
            self._init_tokens()
        else:
            self._load_tokens()

    def _init_tokens(self):
        url, state = self.oauth.authorization_url(self.auth_url)

        print "Please visit %s and authorize access." % url
        auth_response = raw_input("Enter the authorization URL received: ")

        self.token_dict = self.oauth.fetch_token(self.token_url,
            authorization_response=auth_response,
            client_secret=self.client_secret)

        self._update_tokens(self.token_dict)

    def _load_tokens(self):
        with open(self.token_db, 'r') as infile:
            self.token_dict = json.load(infile)
            self.oauth.token=self.token_dict

    def _update_tokens(self, tokens):
        self.token_dict = tokens

        with open(self.token_db, 'w') as outfile:
            json.dump(tokens, outfile, indent=4)
            self.oauth.token=self.token_dict

    def get_temp_indoor(self):
        """Returns the current indoor temperature."""

        device_url = "https://mytotalconnectcomfort.com/WebApi/api/devices/%s?allData=True" % self.device_id

        try:
            r = self.oauth.get(device_url, client_id=self.client_id,
                client_secret=self.client_secret)
            return r.json()['thermostat']['indoorTemperature']
        except oauthlib.oauth2.rfc6749.errors.InvalidGrantError:
            print 'Need to re-initialize token database.  Please re-run with --init'
            raise
