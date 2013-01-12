import urllib2
import json
from cgi import escape

from api import API

connections = {}
TIMEOUT = 0.1

def get_connection(tab):
    """ Gets or creates an ``API`` for the given ``tab``. """
    url = tab['webSocketDebuggerUrl']
    
    if url not in connections:
        connections[url] = API(url, timeout=TIMEOUT)
    
    return connections[url]

def get_tab_list(host, port):
    """ Returns full tab list from remote debugging API. """
    url = "http://{}:{}/json".format(host, port)
    return json.loads(urllib2.urlopen(url).read().decode())

def get_candidate_tabs(host, port):
    """ Returns tabs using the ``file://`` protocol not already tied up by a connection. """
    return filter(is_candidate_tab, get_tab_list(host, port))

def is_candidate_tab(tab):
    """ Returns True/False if the tab can have a connection established. """
    return is_file_tab(tab) and is_available(tab)

def is_file_tab(tab):
    return tab['url'].startswith('file://')

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
        
    api.reload_page(callback=get_response_body)
    
    # body = api.get_response_body(api.last_request_id)
    # print body

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
