import os
import functools
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from PySide6.QtCore import QThread, Signal

# --- NEW: Create a TCPServer subclass that allows address reuse ---
class ReusableTCPServer(TCPServer):
    """
    A custom TCPServer that sets the allow_reuse_address flag.
    This prevents "Address already in use" errors on rapid restarts.
    """
    allow_reuse_address = True

class LocalHttpServer(QThread):
    """
    A QThread that runs a simple local HTTP server.
    """
    server_started = Signal(str, int)

    def __init__(self, host="localhost", port=8001, serve_dir="."):
        super().__init__()
        self.host = host
        self.port = port
        self.serve_dir = serve_dir
        self.httpd = None

    def run(self):
        """The entry point for the thread."""
        
        Handler = functools.partial(SimpleHTTPRequestHandler, directory=self.serve_dir)

        try:
            # --- MODIFIED: Use our new ReusableTCPServer class ---
            self.httpd = ReusableTCPServer((self.host, self.port), Handler)
            
            actual_host, actual_port = self.httpd.server_address
            
            print(f"Starting local server at http://{actual_host}:{actual_port}")
            self.server_started.emit(actual_host, actual_port)
            self.httpd.serve_forever()
            print("Server loop has ended.") # This will print when shutdown() is called

        except Exception as e:
            print(f"Error starting server: {e}")
            self.httpd = None

    def stop(self):
        """Stops the server from the main thread."""
        if self.httpd:
            print("Stopping local server...")
            self.httpd.shutdown()
            self.httpd.server_close()