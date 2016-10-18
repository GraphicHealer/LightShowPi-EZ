#!/usr/bin/python

import BaseHTTPServer
import CGIHTTPServer_root
import cgitb; cgitb.enable()  ## This line enables CGI error reporting
import os
 
server = BaseHTTPServer.HTTPServer
handler = CGIHTTPServer_root.CGIHTTPRequestHandler
server_address = ("", 80)
lspitools = os.getenv("SYNCHRONIZED_LIGHTS_HOME") + "/web"
os.chdir(lspitools)
handler.cgi_directories = ["/"]
 
httpd = server(server_address, handler)
httpd.serve_forever()

