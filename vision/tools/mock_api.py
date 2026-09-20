from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/ingest":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        print(json.dumps(body, ensure_ascii=False), flush=True)
        response = json.dumps({"accepted": len(body.get("regions", [])), "ignored": []}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

if __name__ == "__main__":
    print("Mock API em http://localhost:8000")
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
