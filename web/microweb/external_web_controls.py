#!/usr/bin/python

#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.org/
#
# Author: Ken B
# 
# Basic Auth for web-facing controls

listenport = 28080
username = "externaluser"
password = "2Usm9b7E7324jyrT1kO90"

import BaseHTTPServer
import CGIHTTPServer_root
import cgitb; cgitb.enable()  ## This line enables CGI error reporting
import os, sys

def excepthook(etype,ex,tb):
    sys.stdout.flush()

sys.excepthook = excepthook
 
server = BaseHTTPServer.HTTPServer
handler = CGIHTTPServer_root.CGIHTTPRequestHandler
server_address = ("", listenport)
lspitools = os.getenv("SYNCHRONIZED_LIGHTS_HOME") + "/web/microweb"
os.chdir(lspitools)
handler.cgi_directories = ["/cgi-bin"]
handler.user = username
handler.password = password

try: 
    httpd = server(server_address, handler)
    httpd.serve_forever()

#except KeyboardInterrupt:
#    os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
#    os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')


