import re
import os
import json
import urllib2
from cgi import escape
from operator import itemgetter
from functools import partial

from api import API

connections = {}
TIMEOUT = 0.1

def rgb(r, g, b):
    return {'r': r, 'g': g, 'b': b}

def rgba(r, g, b, a):
    return dict(rgb(r, g, b), a=a)

HIGHLIGHT_STYLE = {
    'borderColor': rgb(255, 0, 0),
    'contentColor': rgba(255, 0, 0, 0.5),
}

def get_connection(tab):
    """ Gets or creates an ``API`` for the given ``tab``. """
    url = tab['webSocketDebuggerUrl']
    
    if url not in connections:
        connections[url] = API(url, timeout=TIMEOUT)
    
    return connections[url]

def get_tab_list(host, port):
    """ Returns full tab list from remote debugging API. """
    url = "http://{}:{}/json".format(host, port)
    
    try:
        response = urllib2.urlopen(url)
    except Exception:
        raise Exception("Can't connect to {}:{}".format(host, port))
    else:
        return json.loads(response.read().decode())

def get_tabs_with_css_file(css_file):
    return filter(partial(has_css_file, css_file), get_candidate_tabs())

def get_candidate_tabs(host=None, port=None):
    """ Returns tabs using the ``file://`` protocol not already tied up by a connection. """
    if host is None:
        host = os.environ.get('CHROME_LIVE_DEBUGGING_HOST', 'localhost')
    if port is None:
        port = os.environ.get('CHROME_LIVE_DEBUGGING_PORT', 9222)
    
    return filter(is_candidate_tab, get_tab_list(host, port))

def is_candidate_tab(tab):
    """ Returns True/False if the tab can have a connection established. """
    return is_local_tab(tab) and is_available(tab)

def is_local_tab(tab):
    return re.match(r'^(?:file://|https?://(localhost|127\.0\.0\.1)[:/])', tab['url'])

def is_available(tab):
    return 'webSocketDebuggerUrl' in tab

# Interactive functions
def has_css_file(css_file, tab):
    """ Returns ``True`` if ``css_file`` is a linked stylesheet in the content body of ``tab``. """
    api = get_connection(tab)
    
    # root = api.get_document()
    api.enable_page_notifications()
    
    def get_response_body(notifications, **kwargs):
        for name, n in notifications.items():
            print '<hr />', n.method, n
        # frame_id = notifications['Page.frameNavigated'].frame.loaderId
        # 
        # body = api.get_response_body(frame_id)
        # print body
        
    # api.reload_page(callback=get_response_body)
    
    # body = api.get_response_body(api.last_request_id)
    # print body
    return True

def push_resource(tab):
    api = get_connection(tab)
        
    try:
        # TODO: Find a way to push the css without reloading the entire page
        api.reload_page()
    except RemoteDebuggerError as e:
        message = "ERROR: {}".format(e)
    else:
        message = "Pushed."
    
    return escape("{title}: {message}".format(message=message, **tab).decode())

def highlight_nodes(selector, tab):
    api = get_connection(tab)
    
    root = api.get_document()
    for node_id in api.query_selector_all(root['nodeId'], selector):
        api.highlight_node(node_id, HIGHLIGHT_STYLE)

