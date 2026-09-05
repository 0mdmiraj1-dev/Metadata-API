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


def make_response(status, data):
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
    request = urllib.request.Request(
        JSONLINK_HOME,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        html = response.read().decode("utf-8", errors="ignore")

    match = re.search(
        r"__APP_DATA__\.public_token\s*=\s*['\"]([^'\"]+)['\"]",
        html,
    )

    if not match:
        raise RuntimeError("Public token not found")

    return match.group(1)


def extract_from_jsonlink(token, target_url):
    params = urllib.parse.urlencode({
        "token": token,
        "url": target_url,
    })

    endpoint = (
        "https://jsonlink.io/api/public-extract?"
        + params
    )

    request = urllib.request.Request(
        endpoint,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Referer": "https://jsonlink.io/",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8", errors="ignore")

    return json.loads(raw)


def handler(request):
    try:
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
            return make_response(405, {
                "success": False,
                "error": "Method Not Allowed",
            })

        target_url = request.args.get("url")

        if not target_url:
            return make_response(400, {
                "success": False,
                "error": "Missing url parameter",
            })

        parsed = urllib.parse.urlparse(target_url)

        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return make_response(400, {
                "success": False,
                "error": "Invalid URL",
            })

        # Request 1:
        # Get jsonlink.io homepage → extract public_token
        token = get_public_token()

        # Request 2:
        # Use token → get metadata
        result = extract_from_jsonlink(token, target_url)

        return make_response(200, result)

    except urllib.error.HTTPError as error:
        try:
            raw = error.read().decode("utf-8", errors="ignore")
            details = json.loads(raw)
        except Exception:
            details = None

        return make_response(error.code, {
            "success": False,
            "error": "JsonLink HTTP error",
            "details": details,
        })

    except urllib.error.URLError as error:
        return make_response(502, {
            "success": False,
            "error": "Could not connect to JsonLink",
            "details": str(error.reason),
        })

    except Exception as error:
        return make_response(500, {
            "success": False,
            "error": str(error),
        })
