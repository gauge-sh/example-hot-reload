import time

start_time = time.perf_counter()

print("Starting server.py execution...")
import json
import sys
from example.module_0.file_0 import example_function_0 as startup_function

# Import this at startup to demonstrate initialization delay
startup_function()


class WSGIApp:
    def __init__(self):
        self.routes = {
            "/": self.handle_root,
            "/lazy": self.handle_lazy_import,
            "/multi": self.handle_multiple_modules,
            "/modules": self.list_loaded_modules,
        }

    def handle_root(self, environ):
        return {
            "status": "200 OK",
            "response": "Welcome to the HMR demo app! Try /lazy, /multi, or /modules",
        }

    def handle_lazy_import(self, environ):
        # Demonstrate lazy importing
        from example.module_1.file_1 import example_function_1

        result = example_function_1()
        return {
            "status": "200 OK",
            "response": f"Lazily imported and called function. Result: {result}",
        }

    def handle_multiple_modules(self, environ):
        # Import and use multiple modules
        from example.module_2.file_0 import example_function_0
        from example.module_3.file_1 import example_function_1
        from example.module_4.file_2 import example_function_2

        results = {
            "module_2": example_function_0(),
            "module_3": example_function_1(),
            "module_4": example_function_2(),
        }

        return {
            "status": "200 OK",
            "response": f"Called multiple module functions. Results: {results}",
        }

    def list_loaded_modules(self, environ):
        # Show which modules are currently loaded
        example_modules = [
            mod for mod in sys.modules.keys() if mod.startswith("example.")
        ]
        return {
            "status": "200 OK",
            "response": f"Currently loaded example modules: {example_modules}",
        }

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "/")
        handler = self.routes.get(path, self.handle_root)

        try:
            result = handler(environ)
            status = result["status"]
            response = json.dumps(result["response"]).encode("utf-8")

            headers = [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response))),
            ]

            start_response(status, headers)
            return [response]

        except Exception as e:
            status = "500 Internal Server Error"
            response = json.dumps(
                {"error": str(e), "type": e.__class__.__name__}
            ).encode("utf-8")

            headers = [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response))),
            ]

            start_response(status, headers)
            return [response]


application = WSGIApp()

end_time = time.perf_counter()
print(f"Server.py initialization completed in {end_time - start_time:.3f} seconds")
