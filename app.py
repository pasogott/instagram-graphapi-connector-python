import os
import json
import requests
from flask import Flask, request, redirect, jsonify
from dotenv import load_dotenv

# .env-Datei laden
load_dotenv()

# Werte aus der .env-Datei auslesen
app_id = os.getenv("APP_ID")
app_secret = os.getenv("APP_SECRET")
user_access_token = os.getenv("USER_ACCESS_TOKEN")
long_lived_token = os.getenv("LONG_LIVED_TOKEN")
ig_user_id = os.getenv("IG_USER_ID")

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World</p>"

@app.route("/privacy_policy")
def privacy_policy():
    with open("./privacy_policy.html", "rb") as file:
        return file.read()

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "POST":
        try:
            print(json.dumps(request.get_json(), indent=4))
        except:
            pass
        return "<p>This is POST Request, Hello Webhook</p>"

    if request.method == "GET":
        hub_challenge = request.args.get("hub.challenge")
        return hub_challenge if hub_challenge else "<p>This is GET Request, Hello webhook</p>"

# Instagram OAuth Login
redirect_uri = "https://3fbc-80-108-89-100.ngrok-free.app/your_insta_token"

@app.route("/login")
def login():
    url = (
        f"https://www.instagram.com/oauth/authorize?"
        f"client_id={app_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={('instagram_business_basic,instagram_business_content_publish,instagram_business_manage_messages,instagram_business_manage_comments').replace(',', '%2C')}"
    )
    return redirect(url)

@app.route("/your_insta_token")
def your_insta_token():
    authorization_code = request.args.get("code") + "#_"

    url = "https://api.instagram.com/oauth/access_token"
    payload = {
        "client_id": app_id,
        "client_secret": app_secret,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code": authorization_code
    }

    response = requests.post(url, data=payload)
    data = response.json()
    user_access_token = data.get("access_token")

    return f"<p>Hello, User! Your token is : {user_access_token}</p>" if user_access_token else jsonify(data), 400

@app.route("/your_long_lived_token")
def your_long_lived_token():
    url = "https://graph.instagram.com/access_token"
    payload = {
        "grant_type": "ig_exchange_token",
        "client_secret": app_secret,
        "access_token": user_access_token
    }

    response = requests.get(url, params=payload)
    data = response.json()
    return jsonify(data)

@app.route("/user_info")
def user_info():
    url = f"https://graph.instagram.com/v22.0/me"
    payload = {
        "fields": "id,user_id,username,account_type,followers_count,follows_count,media_count",
        "access_token": long_lived_token
    }

    response = requests.get(url, params=payload)
    return jsonify(response.json())

@app.route("/user_media_info")
def user_media_info():
    url = f"https://graph.instagram.com/v22.0/me/media"
    payload = {
        "fields": "id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,username,comments_count,like_count",
        "access_token": long_lived_token
    }

    response = requests.get(url, params=payload)
    return jsonify(response.json())

@app.route("/get_comments")
def get_comments_v2():
    url = f"https://graph.instagram.com/v22.0/{ig_user_id}/media"
    
    try:
        media_payload = {
            "fields": "id,username",
            "access_token": long_lived_token
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
                "access_token": long_lived_token,
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

image_url = "https://www.flugninja.at/assets/images/flugninja_logo.png"
caption = "Probleme mit deinem Flug? Meld dich bei uns und wir helfen"

@app.route("/poste_bild")
def poste_bild():
    url = f"https://graph.instagram.com/v22.0/{ig_user_id}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": long_lived_token
    }

    response = requests.post(url, data=payload)
    data = response.json()

    if "id" not in data:
        return jsonify({"Fehler": data}), 400  

    creation_id = data["id"]

    url = f"https://graph.instagram.com/v17.0/{ig_user_id}/media_publish"
    payload = {
        "creation_id": creation_id,
        "access_token": long_lived_token
    }

    response = requests.post(url, data=payload)
    data = response.json()

    return jsonify({"media_id": data["id"]}) if "id" in data else jsonify({"Fehler": data}), 400  

if __name__ == "__main__":
    app.run(debug=True)
