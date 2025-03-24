from dependency_one import CONSTANT


def simple_app(environ, start_response):
    status = "200 OK"
    headers = [("Content-type", "text/plain")]
    start_response(status, headers)
    return [CONSTANT.encode("utf-8")]
