import os
import time
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")

# ── Config ────────────────────────────────────────────────────────────────────
# All of these are automatically injected by Databricks Apps — no manual setup needed.
_host        = os.environ["DATABRICKS_HOST"]
DATABRICKS_HOST = _host if _host.startswith("https://") else f"https://{_host}"
CLIENT_ID    = os.environ["DATABRICKS_CLIENT_ID"]
CLIENT_SECRET= os.environ["DATABRICKS_CLIENT_SECRET"]
GENIE_SPACE_ID = "01f15ff3c23e18e6b043e81ab662dacc"   # ← your space ID, hardcoded

# ── OAuth M2M token (cached) ──────────────────────────────────────────────────
_token_cache = {"token": None, "expires_at": 0}

def get_token() -> str:
    """Fetch a fresh OAuth token using the injected client credentials, with caching."""
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 30:
        return _token_cache["token"]

    resp = requests.post(
        f"{DATABRICKS_HOST}/oidc/v1/token",
        data={
            "grant_type":    "client_credentials",
            "scope":         "all-apis",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"]      = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    return _token_cache["token"]

def headers() -> dict:
    return {"Authorization": f"Bearer {get_token()}", "Content-Type": "application/json"}

BASE_URL = f"{DATABRICKS_HOST}/api/2.0/genie/spaces/{GENIE_SPACE_ID}"


# ── Helper: poll until message is complete ────────────────────────────────────
def poll_message(conversation_id: str, message_id: str, timeout: int = 120):
    url = f"{BASE_URL}/conversations/{conversation_id}/messages/{message_id}"
    deadline = time.time() + timeout

    while time.time() < deadline:
        resp = requests.get(url, headers=headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status", "")

        if status == "COMPLETED":

            texts = []

            for att in data.get("attachments", []):

                # Collect all text attachments
                if "text" in att:
                    texts.append(att["text"]["content"])

            # Return all text responses joined together
            if texts:
                return {
                    "answer": "\n\n".join(texts),
                    "status": "COMPLETED"
                }

            # Fallback if no text attachments exist
            return {
                "answer": "No text response found from Genie.",
                "status": "COMPLETED"
            }

        if status in ("FAILED", "CANCELLED"):
            msg = data.get("error", {}).get("message", "Unknown error")
            return {
                "answer": f"Genie error: {msg}",
                "status": status
            }

        time.sleep(2)

    return {
        "answer": "Timed out waiting for Genie response.",
        "status": "TIMEOUT"
    }

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/ask", methods=["POST"])
def ask():
    body = request.get_json(force=True)

    question = body.get("question", "").strip()
    conversation_id = body.get("conversation_id")

    if not question:
        return jsonify({"error": "question is required"}), 400

    try:
        if conversation_id:
            url = f"{BASE_URL}/conversations/{conversation_id}/messages"

            msg_resp = requests.post(
                url,
                headers=headers(),
                json={"content": question},
                timeout=30
            )
        else:
            url = f"{BASE_URL}/start-conversation"

            msg_resp = requests.post(
                url,
                headers=headers(),
                json={"content": question},
                timeout=30
            )

        msg_resp.raise_for_status()
        msg_data = msg_resp.json()

        conversation_id = (
            msg_data.get("conversation_id")
            or msg_data.get("conversation", {}).get("id")
        )

        message_id = (
            msg_data.get("message_id")
            or msg_data.get("message", {}).get("id")
        )

        if not conversation_id or not message_id:
            return jsonify({
                "error": "Unexpected Genie API response",
                "raw": msg_data
            }), 500

        result = poll_message(conversation_id, message_id)

        return jsonify({
            "answer": result["answer"],
            "status": result["status"],
            "conversation_id": conversation_id
        })

    except requests.HTTPError as e:
        return jsonify({
            "error": str(e),
            "detail": e.response.text
        }), e.response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)