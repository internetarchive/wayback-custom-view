import re
import json
from urllib.parse import urlsplit
from urllib.request import urlopen
from jinja2 import Environment, PackageLoader
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import NotFound

class CustomViewTestApp:
    _config = {
        'wayback_base': 'https://web.archive.org',
        'playback_template': '/web/{timestamp}id_/{target_uri}',
    }

    def __init__(self):
        self.tmplenv = Environment(loader=PackageLoader('ia.wayback_custom_view', 'templates'))
        self.csp_header = ' '.join([
            "default-src 'self'",
            "'unsafe-eval'",
            "'unsafe-inline'",
            "data:",
            "blob:",
            "archive.org",
            "web.archive.org",
            "web-static.archive.org",
            "wayback-api.archive.org",
            "athena.archive.org",
            "analytics.archive.org",
            "pragma.archivelab.org"
        ])

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ, start_response):
        req = Request(environ)
        res = self.dispatch_request(req)
        return res(environ, start_response)

    def dispatch_request(self, req: Request):
        path_info = req.environ['PATH_INFO']
        if path_info == '/':
            return self._render('test_app/index.html', {})

        if 'RAW_URI' in req.environ:
            uri = req.environ['RAW_URI']
        else:
            uri = req.full_path

        if m := re.match(r'/web/(?P<timestamp>\d{1,14})/(?P<target_uri>.*)', uri):
            timestamp = m.group('timestamp')
            target_uri = m.group('target_uri')

            uc = urlsplit(target_uri)
            if uc.netloc in ('twitter.com',
                            'x.com') and (m := re.match(r'/[^/]+/status/\d+', uc.path)):
                return self.twitter_post(req, timestamp, target_uri)

        return NotFound()

    def _render(self, tmpl_name, tvars, headers=None):
        tmpl = self.tmplenv.get_template(tmpl_name)
        content = tmpl.render(tvars)
        return Response(content, mimetype='text/html', headers=headers)

    def twitter_post(self, req, timestamp, target_uri):
        wayback_url = f'{self._config["wayback_base"]}{self._config["playback_template"].format(**locals())}'
        # TODO: disable auto-handling of redirects, and return redirect to the
        # path part of the location header, so that test app location is updated.
        r = urlopen(wayback_url, timeout=20)
        assert r.status == 200
        assert r.getheader('Content-Type') == 'application/json'

        error = None
        try:
            parsed_content = json.load(r)
        except ValueError as ex:
            parsed_content = None
            error = f'content is not a valid JSON {ex}'
        tvars = {
            'parsed_content': parsed_content,
            # TODO: add more vars available in real wayback env
            'context': ReplayContext(timestamp.encode('ascii'))
        }
        if error:
            tvars.update(error=error)
        headers = {
            'Content-Security-Policy': self.csp_header
        }
        return self._render('replay/jsontweet.html', tvars, headers=headers)

class ReplayContext:
    """ stripped-down replica of wayback.replay.core.ReplayContext for testing.
    TODO: add methods added for this module in entry.py!
    """
    def __init__(self, default_timestamp: bytes):
        """stripped-down replica of wayback.replay.core.ReplayContext.
        """
        self.base_url = 'https://web.archive.org/web'
        self.default_timestamp = default_timestamp

    def make_replay_url(self, absurl, timestamp=None, flags=None):
        """make playback URL for the target URL `url` at time `timestamp`,
        and `flags`. This version can only generate absolute URL (no `style`
        argument.) for production wayback (web.archive.org)
        """
        if timestamp is None:
            timestamp = self.default_timestamp
        timestamp = timestamp.decode('latin1')
        if flags:
            timestamp += ''.join(f'{fl}_' for fl in flags)
        return f'{self.base_url}/{timestamp}/{absurl}'

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
        # timestamp = timestamp.decode('latin1')
        if flags:
            timestamp += ''.join(f'{fl}_' for fl in flags)
        return f'{self.base_url}/{timestamp}/{stripped_url}?name=orig&format={extension}'

    def make_query_url(self, absurl, prefix=False, variant=None):
        """make capture/URL search URL for the target URL `url`,
        of `variant`.
        """
        if variant == 'timemap':
            return f'{self.base_url}/timemap/link/{absurl}'
        else:
            return f'{self.base_url}/*/{absurl}{"*" if prefix else ""}'
        
    def get_timestamp(self, wayback_full_url):
        """get timestamp from request"""
        return wayback_full_url.split('/')[4]

    def rework_image_url(self, absurl):
        """strip extension off of URL, add "?name=orig&format={extension}
        """
        stripped_url = absurl.rsplit('.',1)[0]
        extension = absurl.rsplit('.',1)[1]
        return f'{stripped_url}?name=orig&format={extension}'
