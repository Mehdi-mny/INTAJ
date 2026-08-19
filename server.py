#!/usr/bin/env python3
"""
Simple HTTP server for INTAJ website with contact form submission handler.
Stores contact form submissions in a SQLite database.
"""

import json
import sqlite3
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

# SQLite database file
DB_FILE = 'submissions.db'


def init_db():
    """Create the submissions table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            contact TEXT NOT NULL,
            service TEXT NOT NULL,
            project TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def save_submission(data):
    """Insert a new submission into the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO submissions (timestamp, first_name, last_name, contact, service, project)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        data.get('timestamp', datetime.now().isoformat()),
        data.get('firstName', ''),
        data.get('lastName', ''),
        data.get('contact', ''),
        data.get('service', ''),
        data.get('project', '')
    ))
    conn.commit()
    submission_id = cursor.lastrowid
    conn.close()
    return submission_id


def get_all_submissions():
    """Retrieve all submissions from the database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM submissions ORDER BY id DESC')
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


class ContactFormHandler(SimpleHTTPRequestHandler):
    """HTTP request handler with form submission support."""

    def do_GET(self):
        """Handle GET requests - serve static files or admin data."""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/api/submissions':
            # Return all submissions as JSON (simple admin endpoint)
            submissions = get_all_submissions()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(submissions, ensure_ascii=False, indent=2).encode('utf-8'))
        else:
            super().do_GET()

    def do_POST(self):
        """Handle POST requests - save form data to SQLite."""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/api/contact':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            try:
                form_data = json.loads(body.decode('utf-8'))

                submission_id = save_submission(form_data)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'success', 'id': submission_id}).encode('utf-8'))

                print("[+] Form submission saved (id={}): {} {}".format(
                    submission_id, form_data.get('firstName', ''), form_data.get('lastName', '')))

            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode('utf-8'))
                print("[-] Error processing form: {}".format(e))
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def end_headers(self):
        """Add CORS headers to all responses."""
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()


if __name__ == '__main__':
    PORT = 8000
    init_db()

    server = ThreadingHTTPServer(('127.0.0.1', PORT), ContactFormHandler)

    print("[*] Server started at http://127.0.0.1:{}".format(PORT))
    print("[*] Form submissions stored in SQLite database: {}".format(DB_FILE))
    print("[*] View submissions at http://127.0.0.1:{}/api/submissions".format(PORT))
    print("[*] Press Ctrl+C to stop the server.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")
