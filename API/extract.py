import json
import re
import urllib.parse
import urllib.request


JSONLINK_HOME = "https://jsonlink.io/"


USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 10; K) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/152.0.0.0 Mobile Safari/537.36"
)


def response(status, data):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(data, ensure_ascii=False),
    }


def get_public_token():
    req = urllib.request.Request(
        JSONLINK_HOME,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )

    with urllib.request.urlopen(req, timeout=15) as res:
        html = res.read().decode("utf-8", errors="ignore")

    match = re.search(
        r"__APP_DATA__\.public_token\s*=\s*['\"]([^'\"]+)['\"]",
        html,
    )

    if not match:
        raise RuntimeError("JsonLink public token was not found")

    return match.group(1)


def public_extract(token, target_url):
    params = urllib.parse.urlencode({
        "token": token,
        "url": target_url,
    })

    api_url = (
        "https://jsonlink.io/api/public-extract?"
        + params
    )

    req = urllib.request.Request(
        api_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Referer": "https://jsonlink.io/",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as res:
        raw = res.read().decode("utf-8", errors="ignore")

    return json.loads(raw)


def handler(request):
    try:
        # Handle CORS preflight
        if request.method == "OPTIONS":
            return {
                "statusCode": 204,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
                "body": "",
            }

        if request.method != "GET":
            return response(405, {
                "success": False,
                "error": "Method Not Allowed",
            })

        target_url = request.args.get("url")

        if not target_url:
            return response(400, {
                "success": False,
                "error": "Missing required parameter: url",
            })

        # Basic URL validation
        parsed = urllib.parse.urlparse(target_url)

        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return response(400, {
                "success": False,
                "error": "Invalid URL",
            })

        # -------------------------------------------------
        # OUTBOUND REQUEST #1
        # Get jsonlink.io homepage and extract public_token
        # -------------------------------------------------
        token = get_public_token()

        # -------------------------------------------------
        # OUTBOUND REQUEST #2
        # Use token to call JsonLink public extractor
        # -------------------------------------------------
        result = public_extract(token, target_url)

        return response(200, result)

    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="ignore")
            try:
                details = json.loads(body)
            except Exception:
                details = body
        except Exception:
            details = None

        return response(e.code, {
            "success": False,
            "error": "JsonLink HTTP error",
            "details": details,
        })

    except urllib.error.URLError as e:
        return response(502, {
            "success": False,
            "error": "Unable to connect to JsonLink",
            "details": str(e.reason),
        })

    except Exception as e:
        return response(500, {
            "success": False,
            "error": str(e),
        })
