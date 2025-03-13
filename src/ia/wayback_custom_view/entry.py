# defines entry points
import re

def hello_world():
    return 'hello_world!'

gwb_custom_view = {
    'urlkey_match': [
        re.compile(r'com,twitter\)/[^/]+/status/\d+$')
    ],
    'view':  {
        'template': 'jsontweet',
        'tvars': {
            # can expose Python objects to template
            'hello_world': hello_world
        }
    }
}
