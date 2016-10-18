#!/usr/bin/python

import BaseHTTPServer
import CGIHTTPServer_root
import cgitb; cgitb.enable()  ## This line enables CGI error reporting
import os
 
server = BaseHTTPServer.HTTPServer
handler = CGIHTTPServer_root.CGIHTTPRequestHandler
server_address = ("", 80)
lspitools = os.getenv("SYNCHRONIZED_LIGHTS_HOME") + "/web/microweb"
os.chdir(lspitools)
handler.cgi_directories = ["/"]

try: 
    httpd = server(server_address, handler)
    httpd.serve_forever()

except KeyboardInterrupt:
    os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
    os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')


