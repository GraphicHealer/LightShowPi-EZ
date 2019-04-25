#!/usr/bin/python

#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.org/
#
# Author: Ken B
#
# Note : The three values that follow can be anything, but an empty password is not allowed.
#        Since this is web facing, please use adequate user/pass complexity and reuse principles 

listenport = 28080
username = "externaluser"
password = ""

if not password:
    print("Empty password is not allowed!")
    exit(1)

import CGIHTTPServer_root
import cgitb; cgitb.enable()  ## This line enables CGI error reporting
import os, sys

def excepthook(etype,ex,tb):
    sys.stdout.flush()

sys.excepthook = excepthook
 
server = CGIHTTPServer_root.HTTPServer
handler = CGIHTTPServer_root.CGIHTTPRequestHandler
server_address = ("", listenport)
lspitools = os.getenv("SYNCHRONIZED_LIGHTS_HOME") + "/web/microweb"
os.chdir(lspitools)
handler.cgi_directories = ["/cgi-bin"]
handler.user = username
handler.password = password

httpd = server(server_address, handler)
httpd.serve_forever()

