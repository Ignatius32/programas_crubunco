import os
import sys
import logging

# Configure logging with more flexible error handling
log_paths = [
    '/var/www/programas/logs/programas.log',  # Primary location
    '/tmp/programas.log',                     # Fallback to /tmp
    './programas.log'                         # Last resort - current directory
]

# Try each log location until one works
log_handler = None
for log_path in log_paths:
    try:
        # Make sure the directory exists
        log_dir = os.path.dirname(log_path)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
                print(f"Created directory: {log_dir}")
            except Exception as e:
                print(f"Could not create directory {log_dir}: {e}")
                continue  # Try next path

        # Try to open the file for writing
        log_handler = logging.FileHandler(log_path)
        print(f"Successfully using log file: {log_path}")
        break  # Success!
    except Exception as e:
        print(f"Could not use log file {log_path}: {e}")

# Configure the logger
try:
    handlers = [logging.StreamHandler()]  # Always include console output
    if log_handler:
        handlers.append(log_handler)

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] - %(message)s',
        handlers=handlers
    )
    logging.info("Logging initialized successfully")
except Exception as e:
    # Last resort - basic console-only logging
    print(f"Error setting up logging: {e}")
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] - %(message)s'
    )

# Add application directory to path
sys.path.insert(0, '/var/www/programas')  # Add the root programas directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

# Helper class to restore request body for reading
class RestoreContentLengthWrapper:
    def __init__(self, stream, content):
        self.stream = stream
        self.content = content
        self.position = 0

    def read(self, size=-1):
        if size == -1 or size > len(self.content) - self.position:
            result = self.content[self.position:]
            self.position = len(self.content)
        else:
            result = self.content[self.position:self.position + size]
            self.position += size
        return result

    def readline(self, size=-1):
        return self.read(size)

    def __iter__(self):
        while True:
            line = self.readline()
            if not line:
                break
            yield line

# Simple middleware that handles paths
class PrefixMiddleware:
    def __init__(self, app, prefix='/programas'):
        self.app = app
        self.prefix = prefix
        logging.info(f"PrefixMiddleware initialized with prefix: {prefix}")

    def __call__(self, environ, start_response):
        try:
            original_path = environ.get('PATH_INFO', '')
            request_method = environ.get('REQUEST_METHOD', '')
            logging.debug(f"Original request path: {original_path} [{request_method}]")

            # Log request details for debugging
            if request_method in ['POST', 'PUT']:
                content_length = environ.get('CONTENT_LENGTH', '0')
                if content_length and int(content_length) > 0:
                    try:
                        request_body = environ.get('wsgi.input').read(int(content_length))
                        environ['wsgi.input'] = RestoreContentLengthWrapper(environ['wsgi.input'], request_body)
                        logging.debug(f"Request body: {request_body.decode('utf-8', errors='replace')}")
                    except Exception as read_error:
                        logging.warning(f"Could not read request body: {read_error}")

            # Adjust paths for our prefix
            if original_path.startswith(self.prefix):
                path_info = original_path[len(self.prefix):]
                if not path_info:  # Handle '/programas' -> '/programas/'
                    path_info = '/'
                environ['PATH_INFO'] = path_info
                environ['SCRIPT_NAME'] = self.prefix
                logging.debug(f"Adjusted path: {path_info}")

            # Wrap start_response to log response status
            def custom_start_response(status, headers, exc_info=None):
                logging.debug(f"Response status: {status}")
                return start_response(status, headers, exc_info)

            return self.app(environ, custom_start_response)
            
        except Exception as middleware_error:
            logging.error(f"Middleware error: {middleware_error}", exc_info=True)
            status = '500 Internal Server Error'
            output = f"Middleware error: {str(middleware_error)}".encode('utf-8')
            response_headers = [('Content-type', 'text/plain'),
                              ('Content-Length', str(len(output)))]
            start_response(status, response_headers)
            return [output]

# Import the Flask application
try:
    # Try different import approaches
    try:
        from app.app import app
        application = app
        logging.info("Flask application imported successfully from app.app")
    except ImportError:
        # Try an alternative import path
        from app import app
        application = app
        logging.info("Flask application imported successfully from app")
except Exception as import_error:
    # Store the error message for later use
    error_message = str(import_error)
    logging.error(f"Error importing Flask application: {error_message}")
    
    # Define application function with access to the error_message
    def application(environ, start_response):
        status = '500 Internal Server Error'
        output = f"Import error: {error_message}".encode('utf-8')
        response_headers = [('Content-type', 'text/plain'),
                          ('Content-Length', str(len(output)))]
        start_response(status, response_headers)
        return [output]

# Apply the middleware
if hasattr(application, 'wsgi_app'):
    application.wsgi_app = PrefixMiddleware(application.wsgi_app)
    logging.info("Middleware applied to application.wsgi_app")
else:
    application = PrefixMiddleware(application)
    logging.info("Middleware applied directly to application")

if __name__ == '__main__':
    application.run()