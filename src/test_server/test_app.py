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
            if uc.netloc in ('twitter.com', 'x.com') and (m := re.match(r'/[^/]+/status/\d+', uc.path)):
                return self.twitter_post(req, timestamp, target_uri)

        return NotFound()

    def _render(self, tmpl_name, tvars):
        tmpl = self.tmplenv.get_template(tmpl_name)
        content = tmpl.render(tvars)
        return Response(content, mimetype='text/html')
    
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
        }
        if error:
            tvars.update(error=error)

        return self._render('replay/jsontweet.html', tvars)
