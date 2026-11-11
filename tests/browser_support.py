import contextlib
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {
    'desktop-empty': {'width': 1440, 'height': 1000, 'selected': False, 'zoom': 1},
    'desktop-selected': {'width': 1440, 'height': 1000, 'selected': True, 'zoom': 1},
    'mobile-selected': {'width': 390, 'height': 844, 'selected': True, 'zoom': 1},
    'tablet-selected': {'width': 1024, 'height': 768, 'selected': True, 'zoom': 1},
    'narrow-zoom': {'width': 640, 'height': 1000, 'selected': True, 'zoom': 2},
}
INVENTORY_JS = '''root => {
 const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
 const texts = [];
 while (walker.nextNode()) {
  const node = walker.currentNode, el = node.parentElement;
  if (!el || el.closest('script, style, svg') || !el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})) continue;
  const range = document.createRange(); range.selectNodeContents(node);
  if (!range.getClientRects().length) continue;
  const value = node.textContent.replace(/\\s+/g, ' ').trim();
  if (value) texts.push(value);
 }
 return texts;
}'''

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

@contextlib.contextmanager
def serve(overrides=None):
    class Handler(QuietHandler):
        def do_GET(self):
            name = urlsplit(self.path).path.lstrip('/') or 'index.html'
            if overrides is not None and name in overrides:
                content = overrides[name]
                self.send_response(200)
                self.send_header('Content-Type', self.guess_type(name))
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                self.wfile.write(content)
            else:
                super().do_GET()

    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(ROOT)))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/'
    finally:
        server.shutdown()
        server.server_close()
        worker.join()

def fixture(page, base_url, spec):
    page.set_viewport_size({'width': spec['width'], 'height': spec['height']})
    page.goto(base_url, wait_until='networkidle')
    if spec['selected']:
        page.locator('#day1-options button').get_by_text('夜の騎兵', exact=True).click()
    if spec['zoom'] != 1:
        page.locator('html').evaluate('(el, zoom) => el.style.zoom = zoom', spec['zoom'])


def inventory(page, selector='body'):
    return page.locator(selector).evaluate(INVENTORY_JS)
