from reloadable import ReloadableWSGI


wsgi = ReloadableWSGI("server:application")
