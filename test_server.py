from wsgiref.simple_server import make_server
from wsgi import wsgi


with make_server("", 9999, wsgi) as httpd:
    print("Serving on port 9999...")

    # Serve until process is killed
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Server shutting down")
