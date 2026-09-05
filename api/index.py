from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.parse
import urllib.request


class handler(BaseHTTPRequestHandler):

    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()

        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):

        try:
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)

            target_url = query.get("url", [None])[0]

            if not target_url:
                self.send_json(400, {
                    "success": False,
                    "error": "Missing url parameter"
                })
                return

            target = urllib.parse.urlparse(target_url)

            if target.scheme not in ("http", "https") or not target.netloc:
                self.send_json(400, {
                    "success": False,
                    "error": "Invalid URL"
                })
                return

            # ==========================================
            # REQUEST 1
            # Get JsonLink homepage
            # ==========================================

            home_request = urllib.request.Request(
                "https://jsonlink.io/",
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Linux; Android 10; K) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/152.0.0.0 Mobile Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml",
                }
            )

            with urllib.request.urlopen(home_request, timeout=15) as response:
                html = response.read().decode(
                    "utf-8",
                    errors="ignore"
                )

            # ==========================================
            # Extract public_token
            # ==========================================

            match = re.search(
                r"__APP_DATA__\.public_token\s*=\s*['\"]([^'\"]+)['\"]",
                html
            )

            if not match:
                self.send_json(502, {
                    "success": False,
                    "error": "JsonLink public_token not found"
                })
                return

            token = match.group(1)

            # ==========================================
            # REQUEST 2
            # Call JsonLink public-extract
            # ==========================================

            params = urllib.parse.urlencode({
                "token": token,
                "url": target_url
            })

            api_url = (
                "https://jsonlink.io/api/public-extract?"
                + params
            )

            api_request = urllib.request.Request(
                api_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Linux; Android 10; K) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/152.0.0.0 Mobile Safari/537.36"
                    ),
                    "Accept": "application/json",
                    "Referer": "https://jsonlink.io/",
                }
            )

            with urllib.request.urlopen(
                api_request,
                timeout=30
            ) as response:

                result = json.loads(
                    response.read().decode(
                        "utf-8",
                        errors="ignore"
                    )
                )

            # ==========================================
            # Return final JSON
            # ==========================================

            self.send_json(200, result)

        except urllib.error.HTTPError as error:

            try:
                raw = error.read().decode(
                    "utf-8",
                    errors="ignore"
                )

                details = json.loads(raw)

            except Exception:
                details = None

            self.send_json(error.code, {
                "success": False,
                "error": "JsonLink HTTP error",
                "details": details
            })

        except urllib.error.URLError as error:

            self.send_json(502, {
                "success": False,
                "error": "Unable to connect to JsonLink",
                "details": str(error.reason)
            })

        except Exception as error:

            self.send_json(500, {
                "success": False,
                "error": str(error)
            })
