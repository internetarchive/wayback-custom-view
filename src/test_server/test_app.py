import re
import json
import logging
import sys
from urllib.parse import urlsplit
from urllib.request import urlopen
from jinja2 import Environment, PackageLoader
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import NotFound

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

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
        wayback_url = f'{self._config["wayback_base"]}{self._config[
            "playback_template"].format(**locals())}'
        # TODO: disable auto-handling of redirects, and return redirect to the
        # path part of the location header, so that test app location is updated.
        r = urlopen(wayback_url, timeout=20)
        assert r.status == 200
        # Potential problem: in some cases, this is coming back as
        # "text/html; charset=utf-8", which seems to be old tweets
        assert r.getheader('Content-Type') == 'application/json'
        error = None
        try:
            parsed_content = json.load(r)
            error = 'Trying to pass an error'
        except ValueError as ex:
            parsed_content = None
            error = f'content is not a valid JSON {ex}'
        headers = {
            'Content-Security-Policy': self.csp_header
        }
        try:
            main_text = parsed_content['data']['text']
        except KeyError:
            main_text = ""
            error = 'No text in tweet'
        try:
            entities = parsed_content['data']['entities']['urls']
        except KeyError:
            entities = []
            # error = "No entities in tweet"
        try:
            referenced_tweets = parsed_content['data']['referenced_tweets']
        except KeyError:
            referenced_tweets = []
            # error = "No referenced tweets in tweet"
        media_array = []
        quoted_tweets = []
        for entity in entities:
            start = entity['start']
            end = entity['end']

            if (start or start == 0) and end:
                substring = main_text[start:end]
                # this doesn't seem to be firing
                main_text = main_text.replace(substring, "")
                if substring == entity["url"]:
                    # If we are here, there is a match. Now get the media to insert in the tweet
                    if 'media_key' in entity:
                        media_key = entity['media_key']
                        # If there are multiple media, they will all match the same media_key
                        for media in parsed_content['includes']['media']:
                            if media['media_key'] == media_key:
                                media_array.append(media)

        # we need to do this before it gets passed
        for referenced_tweet in referenced_tweets:
            tweet_id = referenced_tweet['id']
            for tweet in parsed_content['includes']['tweets']:
                if tweet['id'] == tweet_id:
                    #  check if quoted tweet has media, append it.
                    quoted_tweet_text = tweet['text']
                    quoted_tweet_entities = tweet['entities']['urls']
                    quoted_tweet_media_array = []

                    for entity in quoted_tweet_entities:
                        start = entity['start']
                        end = entity['end']
                        if (start or start == 0) and end:
                            substring = quoted_tweet_text[start:end]
                            tweet['text'] = quoted_tweet_text.replace(substring, "")
                            if substring == entity["url"]:
                                # If we are here, there is a match.
                                # Now get the media to insert in the tweet
                                if 'media_key' in entity:
                                    media_key = entity['media_key']
                                    # do we need to test this?
                                    quoted_tweet_media_array.append(entity)
                    if len(quoted_tweet_media_array) > 0:
                        tweet['media_array'] = quoted_tweet_media_array
                    # get the URL for the quoted tweet
                    for user in parsed_content['includes']['users']:
                        if user['id'] == tweet['author_id']:
                            tweet['quoted_tweet_url'] =  f'https://twitter.com/{user[
                                "username"]}/status/{tweet["conversation_id"]}'
                            break
                    quoted_tweets.append(tweet)
        outdata = {
            'text': main_text,
            'users': parsed_content['includes']['users'],
            'author_id': parsed_content['data']['author_id'],
            'media_array': [],
            'quoted_tweets': [],
            'created_at': parsed_content['data']['created_at'],
            'wayback_url': wayback_url
        }
        if len(quoted_tweets) > 0:
            outdata.update(quoted_tweets=quoted_tweets)
        if len(media_array) > 0:
            outdata.update(media_array=media_array)
        tvars = {
            'text': main_text,
            'parsed_content':  parsed_content,
            # TODO: add more vars available in real wayback env
            'wayback_url': wayback_url,
            'users': parsed_content['includes']['users'],
            'author_id': parsed_content['data']['author_id'],
            'created_at': parsed_content['data']['created_at'],
            'media_array': [],
            'quoted_tweets': [],
            'context': ReplayContext(timestamp.encode('ascii')),
        }
        if error:
            tvars.update(error=error)
        if len(quoted_tweets) > 0:
            tvars.update(quoted_tweets=quoted_tweets)
        if len(media_array) > 0:
            tvars.update(media_array=media_array)
        logging.info("tvars:  %s", tvars)
        return self._render('replay/jsontweet.html', tvars, headers=headers)

class ReplayContext:
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
        timestamp = timestamp.decode('latin1')
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
