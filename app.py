import os
import json
import requests
from flask import Flask, request, redirect, jsonify
from dotenv import load_dotenv
import time

# .env-Datei laden
load_dotenv()

# Funktion: Token in .env schreiben und neu laden
def update_env_variable(key, value, env_path=".env"):
    lines = []
    found = False

    try:
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    found = True
                else:
                    lines.append(line)
    except FileNotFoundError:
        pass

    if not found:
        lines.append(f"{key}={value}\n")

    with open(env_path, "w") as f:
        f.writelines(lines)

    load_dotenv(override=True)  # neu laden nach Update

# Flask Setup
app = Flask(__name__)

#  Konfiguration aus .env
app_id = os.getenv("APP_ID")
app_secret = os.getenv("APP_SECRET")
user_access_token = os.getenv("USER_ACCESS_TOKEN")
long_lived_token = os.getenv("LONG_LIVED_TOKEN")
ig_user_id = os.getenv("IG_USER_ID")

#  Startseite
@app.route("/")
def hello_world():
    return "<p>Hello, World</p>"

# Privacy Policy
@app.route("/privacy_policy")
def privacy_policy():
    with open("./privacy_policy.html", "rb") as file:
        return file.read()

#  Webhook-Handling
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "POST":
        try:
            print(json.dumps(request.get_json(), indent=4))
        except Exception as e:
            app.logger.error(f"Webhook error: {e}")
        return "<p>This is POST Request, Hello Webhook</p>"

    if request.method == "GET":
        hub_challenge = request.args.get("hub.challenge")
        return hub_challenge if hub_challenge else "<p>This is GET Request, Hello webhook</p>"

# Instagram Login
redirect_uri = "https://ed6e-80-108-89-100.ngrok-free.app/your_insta_token"

@app.route("/login")
def login():
    url = (
        f"https://www.instagram.com/oauth/authorize?"
        f"client_id={app_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={'instagram_basic,instagram_content_publish,instagram_manage_comments'.replace(',', '%2C')}"
    )
    return redirect(url)

# Kurzlebiger Token speichern
@app.route("/your_insta_token")
def your_insta_token():
    authorization_code = request.args.get("code")
    if not authorization_code:
        return jsonify({"error": "Kein Code erhalten"}), 400

    url = "https://api.instagram.com/oauth/access_token"
    payload = {
        "client_id": app_id,
        "client_secret": app_secret,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code": authorization_code + "#_"
    }

    response = requests.post(url, data=payload)
    data = response.json()

    user_access_token = data.get("access_token")
    if user_access_token:
        update_env_variable("USER_ACCESS_TOKEN", user_access_token)
        return "<p>Kurzlebiger Access Token gespeichert!</p>"

    return jsonify(data), 400

# Langlebigen Token speichern
@app.route("/your_long_lived_token")
def your_long_lived_token():
    user_token = os.getenv("USER_ACCESS_TOKEN")
    if not user_token:
        return jsonify({"error": "Kein kurzlebiger Token vorhanden"}), 400

    url = "https://graph.instagram.com/access_token"
    payload = {
        "grant_type": "ig_exchange_token",
        "client_secret": app_secret,
        "access_token": user_token
    }

    response = requests.get(url, params=payload)
    data = response.json()

    long_lived_token = data.get("access_token")
    if long_lived_token:
        update_env_variable("LONG_LIVED_TOKEN", long_lived_token)
        return jsonify({"message": "Langlebiger Token gespeichert!"})

    return jsonify(data), 400

# Benutzerinfo anzeigen
@app.route("/user_info")
def user_info():
    url = f"https://graph.instagram.com/v22.0/me"
    payload = {
        "fields": "id,user_id,username,account_type,followers_count,follows_count,media_count",
        "access_token": os.getenv("LONG_LIVED_TOKEN")
    }

    response = requests.get(url, params=payload)
    return jsonify(response.json())

# Medien anzeigen
@app.route("/user_media_info")
def user_media_info():
    url = f"https://graph.instagram.com/v22.0/me/media"
    payload = {
        "fields": "id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,username,comments_count,like_count",
        "access_token": os.getenv("LONG_LIVED_TOKEN")
    }

    response = requests.get(url, params=payload)
    return jsonify(response.json())

# Kommentare abrufen
@app.route("/get_comments")
def get_comments_v2():
    url = f"https://graph.instagram.com/v22.0/{ig_user_id}/media"

    try:
        media_payload = {
            "fields": "id,username",
            "access_token": os.getenv("LONG_LIVED_TOKEN")
        }
        media_response = requests.get(url, params=media_payload)
        media_response.raise_for_status()
        media_data = media_response.json()

        if not media_data.get("data"):
            return jsonify({"error": "Keine Medien gefunden"})

        all_comments = []
        for media in media_data.get("data", []):
            media_id = media["id"]
            comments_url = f"https://graph.instagram.com/{media_id}/comments"
            comments_payload = {
                "fields": "text,timestamp,username,replies",
                "access_token": os.getenv("LONG_LIVED_TOKEN"),
                "limit": 100
            }

            comments_response = requests.get(comments_url, params=comments_payload)
            comments_response.raise_for_status()
            comments_data = comments_response.json()

            all_comments.append({
                "media_id": media_id,
                "comments": comments_data.get("data", [])
            })

        return jsonify(all_comments if any(info["comments"] for info in all_comments) else {"message": "Keine Kommentare gefunden"})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"API-Fehler: {str(e)}"})
    except Exception as e:
        return jsonify({"error": f"Unerwarteter Fehler: {str(e)}"})

# Bild posten
image_url = "https://www.flugninja.at/assets/images/flugninja_logo.png"
caption = "Probleme mit deinem Flug? Meld dich bei uns und wir helfen"

@app.route("/poste_bild")
def poste_bild():
    upload_url = f"https://graph.instagram.com/v22.0/{ig_user_id}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": os.getenv("LONG_LIVED_TOKEN")
    }

    response = requests.post(upload_url, data=payload)
    data = response.json()

    if "id" not in data:
        return jsonify({"Fehler": data}), 400

    creation_id = data["id"]
    publish_url = f"https://graph.instagram.com/v17.0/{ig_user_id}/media_publish"
    publish_payload = {
        "creation_id": creation_id,
        "access_token": os.getenv("LONG_LIVED_TOKEN")
    }

    response = requests.post(publish_url, data=publish_payload)
    data = response.json()

    return jsonify({"media_id": data["id"]}) if "id" in data else jsonify({"Fehler": data}), 400

@app.route("/poste_reel")
def poste_reel():
    video_url = "https://files.catbox.moe/gsbgfo.mp4"
    caption = "Test-Reel_3"
    access_token = os.getenv("LONG_LIVED_TOKEN")
    ig_user_id = os.getenv("IG_USER_ID")

    if not ig_user_id or not access_token:
        return jsonify({"Fehler": "IG_USER_ID oder LONG_LIVED_TOKEN fehlt"}), 400

    # Schritt 1: Medienobjekt erstellen (über Instagram Graph API)
    create_url = f"https://graph.instagram.com/{ig_user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": access_token
    }

    response = requests.post(create_url, data=payload)
    result = response.json()

    if "id" not in result:
        return jsonify({"Fehler beim Erstellen des Reels": result}), 400

    creation_id = result["id"]

    # Instagram braucht Zeit, um das Reel zu verarbeiten
    time.sleep(20)  # 20 Sekunden Pause (je nach Größe des Videos kann es variieren)

    # Schritt 2: Reel veröffentlichen
    publish_url = f"https://graph.instagram.com/{ig_user_id}/media_publish"
    publish_payload = {
        "creation_id": creation_id,
        "access_token": access_token
    }

    publish_response = requests.post(publish_url, data=publish_payload)
    publish_result = publish_response.json()

    if "id" in publish_result:
        return jsonify({
            "message": "Reel erfolgreich gepostet!",
            "media_id": publish_result["id"]
        })
    else:
        return jsonify({
            "Fehler beim Veröffentlichen des Reels": publish_result
        }), 400

def wait_for_finish(creation_id, access_token, retries=10, delay=5):
    """
    Wartet darauf, dass Instagram das Carousel verarbeitet.
    """
    status_url = f"https://graph.instagram.com/{creation_id}"
    params = {
        "fields": "status_code",
        "access_token": access_token
    }
    for _ in range(retries):
        response = requests.get(status_url, params=params)
        data = response.json()
        if data.get("status_code") == "FINISHED":
            return True
        time.sleep(delay)
    return False

# Hilfsfunktion zum Upload einer Media-Item (Bild oder Video)
def upload_media_item(ig_user_id, item, access_token):
    """
    Lädt ein Bild oder Video hoch und gibt die Container-ID zurück.
    """
    base_url = f"https://graph.instagram.com/{ig_user_id}/media"

    if item["type"].upper() == "VIDEO":
        # Schritt 1: Video-Container (resumable) anlegen
        payload = {
            "media_type": "VIDEO",
            "upload_type": "resumable",
            "video_url": item["url"],
            "is_carousel_item": True,
            "access_token": access_token
        }
        resp = requests.post(base_url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        container_id = data.get("id")
        upload_url = data.get("upload_url")
        if not upload_url or not container_id:
            raise RuntimeError(f"Fehler beim Erstellen des Video-Containers: {data}")

        # Schritt 2: Videodaten an rupload-facebook.com senden
        # Hier wird der Download-Link genutzt (öffentlich) für das resumable-Upload
        upload_resp = requests.post(
            upload_url,
            headers={
                "Authorization": f"OAuth {access_token}",
                "Content-Type": "application/octet-stream"
            },
            data=requests.get(item["url"]).content
        )
        upload_resp.raise_for_status()

        # Auf Verarbeitung warten
        if not wait_for_finish(container_id, access_token):
            raise RuntimeError("Video-Verarbeitung timed out")

        return container_id
    else:
        # Bild hochladen: einfacher One-Step-Upload
        payload = {
            "image_url": item["url"],
            "is_carousel_item": True,
            "access_token": access_token
        }
        resp = requests.post(base_url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "id" not in data:
            raise RuntimeError(f"Fehler beim Bild-Upload: {data}")
        return data["id"]

@app.route("/post_carousel")
def post_carousel():
    # Gemischte Medienliste
    media_items = [
        {"url": "https://www.flugninja.at/assets/images/flugninja_logo.png", "type": "IMAGE"},
        {"url": "https://www.flugninja.at/assets/images/flugninja_logo.png", "type": "IMAGE"},
        {"url": "https://www.flugninja.at/assets/images/flugninja_logo.png", "type": "IMAGE"}
        # {"url": "https://files.catbox.moe/gsbgfo.mp4", "type": "VIDEO"},
        # {"url": "https://files.catbox.moe/gsbgfo.mp4", "type": "VIDEO"}
    ]
    caption = "Test_Carousel_mit_Video"
    access_token = os.getenv("LONG_LIVED_TOKEN")
    ig_user_id = os.getenv("IG_USER_ID")

    if not ig_user_id or not access_token:
        return jsonify({"error": "IG_USER_ID oder LONG_LIVED_TOKEN fehlt"}), 400

    # Items hochladen
    media_ids = []
    try:
        for item in media_items:
            media_id = upload_media_item(ig_user_id, item, access_token)
            media_ids.append(media_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Carousel-Container erstellen
    create_url = f"https://graph.instagram.com/{ig_user_id}/media"
    carousel_payload = {
        "media_type": "CAROUSEL",
        "children": ",".join(media_ids),
        "caption": caption,
        "access_token": access_token
    }
    create_resp = requests.post(create_url, json=carousel_payload)
    if create_resp.status_code != 200:
        return jsonify({"error_creating_carousel": create_resp.json()}), create_resp.status_code
    creation_id = create_resp.json().get("id")

    # Auf Verarbeitung warten
    if not wait_for_finish(creation_id, access_token):
        return jsonify({"error": "Carousel-Verarbeitung timed out"}), 500

    # Veröffentlichen
    publish_url = f"https://graph.instagram.com/{ig_user_id}/media_publish"
    publish_payload = {"creation_id": creation_id, "access_token": access_token}
    publish_resp = requests.post(publish_url, json=publish_payload)
    if publish_resp.status_code != 200:
        return jsonify({"error_publishing": publish_resp.json()}), publish_resp.status_code

    return jsonify({"message": "Karussell erfolgreich gepostet!", "media_id": publish_resp.json().get("id")})

if __name__ == "__main__":
    app.run(debug=True)


# App starten
if __name__ == "__main__":
    app.run(debug=True)