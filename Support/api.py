import json
from collections import OrderedDict
from UserDict import UserDict

from websocket import create_connection

nodes = {}

class RemoteDebuggerError(Exception):
    def __init__(self, error_obj):
        self.error_obj = error_obj
    
    def __str__(self):
        return "{message} ({code})".format(**self.error_obj)

class UnexpectedMessageError(Exception):
    def __str__(self):
        return "{}"

def rgb(r, g, b):
    return {'r': r, 'g': g, 'b': b}

def rgba(r, g, b, a):
    return dict(rgb(r, g, b), a=a)

HIGHLIGHT_STYLE = {
    'borderColor': rgb(255, 0, 0),
    'contentColor': rgba(255, 0, 0, 0.5),
}

def api_handler(method, args=(), returns=None, no_return=False, each=None):
    """
    Decorator for wrapping a class method.  The wrapped function becomes the response handler for
    the API call.  The API method's argument list is given by ``args``, which lets the caller send
    positional and keyword arguments to the function's API decorator.
    
    Unless ``no_return`` is ``True``, this function returns a decorator to be applied to a class
    method that should act as the response handler, where the handler's arguments should accept the
    Webkit API response values.
    
    ``returns``: If given, ``returns`` is a string key which should be returned from the response
            JSON.  Default is ``None``, meaning that the whole response dictionary is returned.
    
    ``no_return``: If ``True``, the decorator will generate its own dummy handler that returns
            ``None``.  This use of ``api_handler`` returns the callable, making it less of a
            decorator than a handler generator.
    
    ``each``: If given, ``each`` is a string key which describes a top-level value in the response
            JSON that contains an iterable.  Instead of the iterable being sent to the handler, each
            item in the iterable will be sent to the handler in turn.  The handler's arguments
            should consequently allow for the values found in each iterable, sent as ``**kwargs``.
    
    """
    
    method_kwargs = OrderedDict((arg, None) for arg in args)
    def _decorator(unbound_f):
        def _wrapper(self, *caller_args, **caller_kwargs):
            callback = caller_kwargs.pop('callback', None)
            kwargs = method_kwargs.copy()
            params = {}
            for k, v in caller_kwargs.items():
                if k not in kwargs:
                    raise TypeError("Unsupported method parameter '{}'".format(k))
                params[k] = v
                kwargs.pop(k)
            for k, v in zip(kwargs.keys(), caller_args):
                params[k] = v
            
            # Read past incoming objects until we find the one matching the request.
            # This will discard unhandled notifications sitting in the buffer from a previous call
            # to an API method that generated them.
            request_id, response_data = self.request(method, params=params)
            # while request_id != response_data.get('id'):
            #     print '<hr />skipping', response_data
            #     response_data = self.get_response()

            if 'error' in response_data:
                raise RemoteDebuggerError(response_data['error'])
            
            # Read notifications
            reading = True
            notifications = {}
            while reading:
                try:
                    notification = self.get_response()
                except: # Skip timeout
                    reading = False
                else:
                    notifications[notification['method']] = Notification(**notification)
            
            # Move nested k:v pairs directly into the main dictionary's top level
            response_data = response_data.get('result', {})
            
            if each is not None:
                value = [unbound_f(self, notifications=notifications, **item)
                            for item in response_data[each]]
            
            value = unbound_f(self, notifications=notifications, **response_data)
            
            if callback:
                callback(notifications=notifications, **response_data)
            
            return value
        return _wrapper
    
    if returns is not None:
        def _automatic_handler(self, request, **kwargs):
            return kwargs[returns]
        return _decorator(_automatic_handler)
    elif no_return:
        def _null_return(*args, **kwargs):
            return
        return _decorator(_null_return)
    
    return _decorator

class API(object):
    id = -1
    
    def __init__(self, url, **options):
        """
        Opens a websocket to the given valid websocket ``url``.  ``options`` are passed through to
        ``websocket.create_connection()``.
        
        """
        
        self.socket = create_connection(url, **options)
    
    def request(self, method=None, data={}, **options):
        """ Requests API method ``method``, sending JSON data equal to ``dict(data, **options)`` """
        
        # Increment global request id
        self.__class__.id += 1
        
        # Derive JSON payload
        data = dict(data, method=method, id=self.__class__.id, **options)
        
        self.socket.send(json.dumps(data))
        return data['id'], self.get_response()
    
    def get_response(self):
        return json.loads(self.socket.recv())
    
    
    ##
    # API response handlers
    
    # No custom handling required
    get_document = api_handler("DOM.getDocument", returns='root')
    get_response_body = api_handler("Network.getResponseBody", args=('requestId',), returns='body')
    
    # No return values
    enable_page_notifications = api_handler("Page.enable", no_return=True)
    disable_page_notifications = api_handler("Page.disable", no_return=True)
    reload_page = api_handler("Page.reload", no_return=True)
    highlight_node = api_handler("DOM.highlightNode", args=('nodeId', 'highlightConfig'), no_return=True)
    
    @api_handler("DOM.querySelectorAll", args=('nodeId', 'selector'), each='nodes')
    def query_selector_all(self, **node):
        return node['nodeId']

class AttrContainer(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if isinstance(v, dict):
                v = AttrContainer(**v)
            setattr(self, k, v)
    
    def __repr__(self):
        attrs = self.__dict__.items()
        attrs = dict(filter(lambda kv: not kv[0].startswith('_') and not callable(kv[1]), attrs))
        return repr(attrs)
                

class Notification(AttrContainer):
    method = None
    
    def __init__(self, method, params={}):
        super(Notification, self).__init__(**params)
        self.method = method
