import os

settings = {
    'sqlite_path': os.path.dirname(os.path.realpath(__file__)),
    'redirect_domain': '',
    'slack': {
        'command_tokens': (''),
        'web_api_token': '',
        'incoming_webhook': {
            'url': '',
            'username': '',
            'icon_url': ''
        }
    }
}
