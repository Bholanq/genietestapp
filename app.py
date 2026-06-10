import os
import time
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")

# ── Config ────────────────────────────────────────────────────────────────────
DATABRICKS_HOST  = os.environ["DATABRICKS_HOST"]          # e.g. https://adb-xxxx.azuredatabricks.net
DATABRICKS_TOKEN = os.environ["DATABRICKS_TOKEN"]         # Personal Access Token or SP token
GENIE_SPACE_ID   = os.environ["GENIE_SPACE_ID"]           # Copied from Genie Space URL

HEADERS = {
    "Authorization": f"Bearer {DATABRICKS_TOKEN}",
    "Content-Type": "application/json",
}

BASE_URL = f"{DATABRICKS_HOST}/api/2.0/genie/spaces/{GENIE_SPACE_ID}"


# ── Helper: poll until message is complete ────────────────────────────────────
def poll_message(conversation_id: str, message_id: str, timeout: int = 120):
    """Poll Genie until the message status is COMPLETED or FAILED."""
    url = f"{BASE_URL}/conversations/{conversation_id}/messages/{message_id}"
    deadline = time.time() + timeout

    while time.time() < deadline:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "")

        if status == "COMPLETED":
            # Extract the text result from the attachments
            for attachment in data.get("attachments", []):
                if attachment.get("type") == "TEXT":
                    return {"answer": attachment["text"]["content"], "status": "COMPLETED"}
                if attachment.get("type") == "QUERY":
                    query_att = attachment.get("query", {})
                    description = query_att.get("description", "")
                    return {"answer": description, "status": "COMPLETED"}
            return {"answer": "(No text response returned by Genie)", "status": "COMPLETED"}

        if status in ("FAILED", "CANCELLED"):
            error_msg = data.get("error", {}).get("message", "Unknown error")
            return {"answer": f"Genie error: {error_msg}", "status": status}

        time.sleep(2)

    return {"answer": "Timed out waiting for Genie response.", "status": "TIMEOUT"}


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/ask", methods=["POST"])
def ask():
    """
    Body: { "question": "...", "conversation_id": "<optional>" }
    Returns: { "answer": "...", "conversation_id": "..." }
    """
    body = request.get_json(force=True)
    question        = body.get("question", "").strip()
    conversation_id = body.get("conversation_id")

    if not question:
        return jsonify({"error": "question is required"}), 400

    try:
        # ── Start or continue a conversation ──────────────────────────────────
        if conversation_id:
            # Continue existing conversation
            msg_url = f"{BASE_URL}/conversations/{conversation_id}/messages"
            msg_resp = requests.post(
                msg_url,
                headers=HEADERS,
                json={"content": question},
                timeout=30,
            )
        else:
            # Start a new conversation
            msg_url = f"{BASE_URL}/start-conversation"
            msg_resp = requests.post(
                msg_url,
                headers=HEADERS,
                json={"content": question},
                timeout=30,
            )

        msg_resp.raise_for_status()
        msg_data = msg_resp.json()

        conversation_id = msg_data.get("conversation_id") or msg_data.get("conversation", {}).get("id")
        message_id      = msg_data.get("message_id")      or msg_data.get("message", {}).get("id")

        if not conversation_id or not message_id:
            return jsonify({"error": "Unexpected response from Genie API", "raw": msg_data}), 500

        # ── Poll for result ───────────────────────────────────────────────────
        result = poll_message(conversation_id, message_id)
        result["conversation_id"] = conversation_id
        return jsonify(result)

    except requests.HTTPError as e:
        return jsonify({"error": str(e), "detail": e.response.text}), e.response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)