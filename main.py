#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Flask app for self-hosted Juncture site.
'''

CONTENT = 'juncture-digital/hosting' # Github username/repo containing site content
WC_VERSION = 'latest'

import argparse, flask, logging, os, re, requests, urllib.parse
logging.getLogger('requests').setLevel(logging.WARNING)

app = flask.Flask(__name__)

API_ENDPOINT = 'https://api.juncture-digital.org'
WC_ENDPOINT = 'https://cdn.jsdelivr.net/npm/juncture-digital/docs/js/index.js'
CONFIG = {'google_site_search': {'key': '', 'cx': ''}}
SEARCH_CACHE = {}
USE_LOCAL_CONTENT = False

try:
  from serverless_wsgi import handle_request
  def handler(event, context):
    return handle_request(app, event, context)
except:
  pass

def _get_local_content(path):
  '''For local development.'''
  if path.endswith('/'): path = path[:-1]
  for _path in [f'{CONTENT}{path}.md', f'{CONTENT}{path}/README.md']:
    if os.path.exists(_path): return open(_path, 'r').read()

def _get_html(path, base_url, ref=None, **kwargs):
  if USE_LOCAL_CONTENT: # Local development
    markdown = _get_local_content(path)
    if markdown: # Markdown found, convert to HTML using API
      resp = requests.post(f'{API_ENDPOINT}/html/?prefix={CONTENT}&base={base_url}', json={'markdown':markdown, 'prefix':CONTENT})
      return resp.text if resp.status_code == 200 else '', resp.status_code
  else:
    resp = requests.get(f'{API_ENDPOINT}/html{path}?prefix={CONTENT}&base={base_url}{"&ref="+ref if ref else ""}')
    print(f'{API_ENDPOINT}/html{path}?prefix={CONTENT}&base={base_url}{"&ref="+ref if ref else ""}', resp.status_code)
    return resp.text if resp.status_code == 200 else '', resp.status_code
  return 'Not Found', 404

@app.route('/favicon.ico')
@app.route('/robots.txt')
@app.route('/sitemap.txt')
def static_content():
  mimetype = {'ico': 'image/vnd.microsoft.icon', 'css': 'text/css', 'html': 'text/html'}.get(flask.request.path.split('.')[-1], 'text/plain')
  if USE_LOCAL_CONTENT:
    return flask.send_from_directory(CONTENT, flask.request.path[1:], mimetype=mimetype)
  else:
    resp = requests.get(f'https://raw.githubusercontent.com/{CONTENT}/main{flask.request.path}')
    return flask.Response(resp.content if resp.status_code == 200 else '', status=resp.status_code, mimetype=mimetype)

@app.route('/search')
def search():
  '''Invokes Google Custom Search API for site content.'''
  args = {**CONFIG['google_site_search'], **dict(flask.request.args)}
  url = f'https://www.googleapis.com/customsearch/v1?{urllib.parse.urlencode(args)}'
  if url not in SEARCH_CACHE:
    SEARCH_CACHE[url] = requests.get(url).json()
  return SEARCH_CACHE[url]

@app.route('/<path:path>')
@app.route('/')
def render_html(path=None):
  base_url = f'/{"/".join(flask.request.base_url.split("/")[3:])}'
  if base_url != '/' and not base_url.endswith('/'): base_url += '/'
  html, status_code =  _get_html(f'/{path}' if path else '/', base_url, **dict([(k, flask.request.args.get(k)) for k in flask.request.args]))
  if html:
    if WC_VERSION != 'latest':
      html = html.replace('https://cdn.jsdelivr.net/npm/juncture-digital/docs', f'https://cdn.jsdelivr.net/npm/juncture-digital@{WC_VERSION}/docs')
    if WC_ENDPOINT != 'https://cdn.jsdelivr.net/npm/juncture-digital/docs/js/index.js':
      html = html.replace('https://cdn.jsdelivr.net/npm/juncture-digital/docs/js/index.js', WC_ENDPOINT)
      html = re.sub(r'.*https:\/\/cdn\.jsdelivr\.net\/npm\/juncture-digital\/docs\/css\/index\.css.*', '', html)

  return html, status_code

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Juncture website server')
  parser.add_argument('--port', help='Port', type=int, default=8000)
  parser.add_argument('--api', help='API Endpoint', default=API_ENDPOINT)
  parser.add_argument('--wc', help='Web Components Endpoint', default=WC_ENDPOINT)
  parser.add_argument('--content', help='Content source', default=None)
  args = parser.parse_args()
  API_ENDPOINT = args.api
  WC_ENDPOINT = args.wc
  if args.content:
    if os.path.exists(os.path.abspath(args.content)):
      CONTENT = os.path.abspath(args.content)
      USE_LOCAL_CONTENT = True
    else:
      CONTENT = args.content # Github username/repo containing site content
  print(f'\nAPI_ENDPOINT: {API_ENDPOINT}\nWC_ENDPOINT: {WC_ENDPOINT}\CONTENT: {CONTENT}\n')
  app.run(debug=True, host='0.0.0.0', port=args.port)