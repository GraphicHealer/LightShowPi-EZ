#!/usr/bin/python

#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.org/
#
# Author: Ken B

import BaseHTTPServer
import CGIHTTPServer_root
import cgitb; cgitb.enable()  ## This line enables CGI error reporting
import os
 
server = BaseHTTPServer.HTTPServer
handler = CGIHTTPServer_root.CGIHTTPRequestHandler
server_address = ("", 80)
lspitools = os.getenv("SYNCHRONIZED_LIGHTS_HOME") + "/web/microweb"
os.chdir(lspitools)
handler.cgi_directories = ["/cgi-bin"]

try: 
    httpd = server(server_address, handler)
    httpd.serve_forever()

except KeyboardInterrupt:
    os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
    os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')


