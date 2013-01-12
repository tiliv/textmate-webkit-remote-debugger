#! /usr/bin/env python

import sys
from functools import partial

from utils import get_candidate_tabs, has_css_file, push_resource

def push():
    hostname, port, css_file = sys.argv[1:4]
    
    tabs = filter(partial(has_css_file, css_file), get_candidate_tabs(hostname, port))
    
    print "<ul>"
    for response in map(push_resource, tabs):
        print "<li>{}</li>".format(response)
    print "</ul>"
    
push()
