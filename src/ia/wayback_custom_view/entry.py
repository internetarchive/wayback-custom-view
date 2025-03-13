# defines entry points
import re

def hello_world():
    return 'hello_world!'

def make_replay_image_url(self, absurl, timestamp=None, flags=None):
    """make playback URL for the target URL `url` at time `timestamp`,
    and `flags`. This version can only generate absolute URL (no `style`
    argument.) for production wayback (web.archive.org)

    Also: strip extension off of URL, add "?name=orig&format={extension}
    """
    stripped_url = absurl.rsplit('.',1)[0]
    extension = absurl.rsplit('.',1)[1]
    if timestamp is None:
        timestamp = self.default_timestamp
    timestamp = timestamp.decode('latin1')
    if flags:
        timestamp += ''.join(f'{fl}_' for fl in flags)
    return f'{self.base_url}/{timestamp}/{stripped_url}?name=orig&format={extension}'

gwb_custom_view = {
    'urlkey_match': [
        re.compile(r'com,twitter\)/[^/]+/status/\d+$')
    ],
    'view':  {
        'template': 'jsontweet',
        'tvars': {
            # can expose Python objects to template
            'hello_world': hello_world,
            'make_replay_image_url': make_replay_image_url,
        }
    }
}
