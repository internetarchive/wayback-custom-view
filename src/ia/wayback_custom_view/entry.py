# defines entry points
import re

def hello_world():
    """simple function to test if Python functions can be exposed to templates"""
    return 'hello_world!'

def get_timestamp(wayback_full_url):
    """get timestamp from request"""
    return wayback_full_url.split('/')[2]

# def make_replay_image_url(absurl, timestamp="", flags=None):
#     """make playback URL for the target URL `url` at time `timestamp`,
#     and `flags`. This version can only generate absolute URL (no `style`
#     argument.) for production wayback (web.archive.org)

#     Also: strip extension off of URL, add "?name=orig&format={extension}
#     """
#     base_url = 'https://web.archive.org/web'
#     stripped_url = absurl.rsplit('.',1)[0]
#     extension = absurl.rsplit('.',1)[1]
#     # timestamp = get_timestamp(capture_url)
#     # timestamp = timestamp.decode('latin1')
#     if flags:
#         timestamp += ''.join(f'{fl}_' for fl in flags)
#     return f'{base_url}/{timestamp}/{stripped_url}?name=orig&format={extension}'

gwb_custom_view = {
    'urlkey_match': [
        re.compile(r'com,twitter\)/[^/]+/status/\d+$')
    ],
    'view':  {
        'template': 'jsontweet',
        'tvars': {
            # can expose Python objects to template
            'hello_world': hello_world,
            'get_timestamp': get_timestamp,
            # 'make_replay_image_url': make_replay_image_url
        }
    }
}
