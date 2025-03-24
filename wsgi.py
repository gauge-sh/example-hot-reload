from reloadable import ReloadableWSGI


# TODO: config file for this?
wsgi = ReloadableWSGI("server:simple_app")
