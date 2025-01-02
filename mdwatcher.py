import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import markdown
from http.server import SimpleHTTPRequestHandler, HTTPServer
import threading

# Define paths
WATCH_FOLDER = "zcode-versions"
HTML_FOLDER = os.path.join(WATCH_FOLDER, "html")

# HTML template for better rendering
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ 
            max-width: 800px; 
            margin: 40px auto; 
            padding: 0 20px; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; 
            line-height: 1.6;
        }}
        pre {{ 
            background-color: #f6f8fa; 
            padding: 16px; 
            border-radius: 6px; 
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    {content}
</body>
</html>
"""

class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HTML_FOLDER, **kwargs)

    def list_directory(self, path):
        # Override to ensure directory listing works
        try:
            return super().list_directory(path)
        except OSError:
            self.send_error(404, "No permission to list directory")
            return None

class MarkdownHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith('.md'):
            return
        self.process_file(event.src_path)

    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.md'):
            return
        self.process_file(event.src_path)

    def on_deleted(self, event):
        if event.is_directory or not event.src_path.endswith('.md'):
            return
        self.delete_html(event.src_path)

    def process_file(self, file_path):
        try:
            base_name = os.path.basename(file_path)
            html_name = base_name.replace(".md", ".html")
            html_path = os.path.join(HTML_FOLDER, html_name)
            
            with open(file_path, "r", encoding="utf-8") as md_file:
                md_content = md_file.read()
                # Convert markdown to HTML with extra features enabled
                html_content = markdown.markdown(
                    md_content,
                    extensions=['fenced_code', 'tables', 'nl2br']
                )
                # Insert into HTML template
                full_html = HTML_TEMPLATE.format(
                    title=base_name,
                    content=html_content
                )
                
                with open(html_path, "w", encoding="utf-8") as html_file:
                    html_file.write(full_html)
                    
            print(f"Processed {file_path} -> {html_path}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    def delete_html(self, file_path):
        try:
            base_name = os.path.basename(file_path)
            html_name = base_name.replace(".md", ".html")
            html_path = os.path.join(HTML_FOLDER, html_name)
            if os.path.exists(html_path):
                os.remove(html_path)
                print(f"Deleted {html_path}")
        except Exception as e:
            print(f"Error deleting {html_path}: {e}")

def process_existing_files():
    """Process existing markdown files on startup"""
    for filename in os.listdir(WATCH_FOLDER):
        if filename.endswith('.md'):
            file_path = os.path.join(WATCH_FOLDER, filename)
            MarkdownHandler().process_file(file_path)

def start_file_watcher():
    # Ensure HTML directory exists
    os.makedirs(HTML_FOLDER, exist_ok=True)
    
    # Process existing files first
    process_existing_files()
    
    # Start the file watcher
    event_handler = MarkdownHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_FOLDER, recursive=False)
    observer.start()
    print(f"Watching {WATCH_FOLDER} for markdown files...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()

def start_http_server():
    server = HTTPServer(("localhost", 8000), CustomHTTPRequestHandler)
    print("Server started at http://localhost:8000")
    server.serve_forever()

if __name__ == "__main__":
    # Start the file watcher in a separate thread
    watcher_thread = threading.Thread(target=start_file_watcher, daemon=True)
    watcher_thread.start()

    # Start the HTTP server in the main thread
    start_http_server()
