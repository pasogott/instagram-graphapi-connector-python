import os
import json
import requests
from flask import Flask, request, redirect, jsonify
from dotenv import load_dotenv

1️⃣ Unterschiede zwischen Facebook Login API und Instagram Login API
Bei der Instagram Login API gibt es nur vier Haupt-APIs:

Messaging – Senden und Empfangen von Nachrichten
Comment Moderation – Kommentare verwalten und darauf antworten
Content Publishing – Medien abrufen und veröffentlichen
Mentions – Erwähnungen verwalten

Wichtige Unterschiede:

Kein Facebook-Account oder Facebook-Seite erforderlich
Die Meta-App muss auf das Instagram Produkt umgestellt werden
Tokens können per API-Anfrage generiert werden, kein Graph Explorer nötig


2️⃣ Meta App erstellen und Instagram Produkt hinzufügen
Gehe zu Meta for Developers
Melde dich als Meta Developer an
Erstelle eine neue App und wähle „Business“ oder „Other“ aus
Navigiere zu Produkte → Instagram und klicke auf Einrichten
Kopiere deine App ID und App Secret, diese werden später benötigt



3️⃣ Zugriffstoken generieren
1. Autorisierungs-Code abrufen
Führe folgende URL in einem Browser aus (ersetze <APP_ID> und <REDIRECT_URI>):

```
https://api.instagram.com/oauth/authorize?client_id=<APP_ID>&redirect_uri=<REDIRECT_URI>&scope=user_profile,user_media&response_type=code
```

Nach der Autorisierung erhältst du einen Code in der URL zurück.

2. Kurzlebiges Zugriffstoken erhalten
Ersetze <APP_ID>, <APP_SECRET> und <AUTHORIZATION_CODE> mit deinen Werten:

```
curl -X POST https://api.instagram.com/oauth/access_token
  \-F client_id=<APP_ID>\
  -F client_secret=<APP_SECRET> \
  -F grant_type=authorization_code \
  -F redirect_uri=<REDIRECT_URI> \
  -F code=<AUTHORIZATION_CODE>
```

Ergebnis: Eine JSON-Antwort mit access_token und user_id

3. Langzeit-Zugriffstoken (60 Tage) erhalten
Ersetze <ACCESS_TOKEN> mit dem kurzlebigen Token:

curl -X GET `"https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret=<APP_SECRET>&access_token=<ACCESS_TOKEN>"`

Ergebnis: Langzeit-Token (gültig für 60 Tage)


4️⃣ Webhook für Instagram-Events einrichten
Webhooks ermöglichen es, Benachrichtigungen für Kommentare, Mentions und Nachrichten zu erhalten

1. Flask Webserver einrichten (Python)
from flask import Flask, request, jsonify

app = Flask(__name__)

```
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return request.args.get("hub.challenge")
    elif request.method == "POST":
        data = request.json
        print("Webhook Event:", data)
        return jsonify(success=True)
```

```
if __name__ == "__main__":
    app.run(port=5000)
```
2. Ngrok starten
Für den Test muss der Webserver öffentlich erreichbar sein:

./ngrok http 5000
Notiere dir die Ngrok-URL, z. B. https://xyz.ngrok.io/webhook

3. Webhook in der Meta-App registrieren
Gehe zu deiner Meta-App
Navigiere zu Webhooks → Neuer Webhook
Gib die Ngrok-URL ein, z. B. https://xyz.ngrok.io/webhook
Abonniere Kommentare, Nachrichten und Mentions


5. Kommentare & Antworten eines Posts abrufen
    1. Endpunkt für Kommentare eines Posts 
    ```
    https://graph.instagram.com/{MEDIA_ID}/comments?fields=id,text,username,timestamp,like_count,replies&access_token={ACCESS_TOKEN}
    ```
    ```
    2.Endpunkt für Antworten auf einen Kommentar: https://graph.instagram.com/{COMMENT_ID}/replies?fields=id,text,username,timestamp,like_count&access_token={ACCESS_TOKEN}
    ```

6. Kommentar auf einen Post schreiben
📌 Endpunkt:

POST `https://graph.instagram.com/{MEDIA_ID}/comments`
📌 Erforderliche Parameter:

message: Dein Kommentar-Text
📌 Beispiel: Kommentar hinzufügen

```
curl -X POST "https://graph.instagram.com/{MEDIA_ID}/comments" \
  -d "message=Das ist mein erster Kommentar!" \
  -d "access_token={ACCESS_TOKEN}"
```
📌 Antwort:

{
  "id": "17912345678901234"
}
4️⃣ Auf einen Kommentar antworten
📌 Endpunkt:

POST `https://graph.instagram.com/{COMMENT_ID}/replies`
Erforderliche Parameter:

message: Deine Antwort
Beispiel: Auf einen Kommentar antworten

```
curl -X POST "https://graph.instagram.com/{COMMENT_ID}/replies" \
  -d "message=Danke für deinen Kommentar! 😊" \
  -d "access_token={ACCESS_TOKEN}"
```
Antwort:

{
  "id": "17999887766554432"
}
Hinweis:
Falls das Markieren eines Users nicht funktioniert, hat der User möglicherweise eingestellt, dass er nicht in Kommentaren markiert werden kann.


5️⃣ Kommentar verstecken oder wieder anzeigen
Endpunkt:

POST `https://graph.instagram.com/{COMMENT_ID}`
Erforderliche Parameter:

hide: true (verstecken) oder false (anzeigen)
Beispiel: Kommentar verstecken

```
curl -X POST "https://graph.instagram.com/{COMMENT_ID}" \
  -d "hide=true" \
  -d "access_token={ACCESS_TOKEN}"
```

Antwort:

{
  "success": true
}
Beispiel: Kommentar wieder anzeigen

```
curl -X POST "https://graph.instagram.com/{COMMENT_ID}" \
  -d "hide=false" \
  -d "access_token={ACCESS_TOKEN}"
```

Instagram API: Bilder veröffentlichen (Post & Story)

Diese Anleitung beschreibt, wie du mit der Instagram Graph API folgende Funktionen umsetzt:

Bilder auf Instagram posten
Bilder in einer Instagram-Story veröffentlichen
Temporäre URLs für lokale Bilder mit Ngrok erstellen
API-Rate-Limits überwachen

Wichtige Voraussetzung:
Du kannst NUR Inhalte auf Business- oder Creator-Accounts veröffentlichen.

Einschränkungen der Instagram API
Wichtige Regeln für das Veröffentlichen von Bildern:

Bildformat: Nur JPEG
Maximale Dateigröße: 8 MB
Bild muss öffentlich zugänglich sein (darf nicht lokal gespeichert sein)
Max. 50 Posts pro Tag via API
Caption-Limit: 2200 Zeichen, max. 30 Hashtags, 20 Markierungen

Lösung für das Problem „Bild muss online sein“:
Wir verwenden Ngrok, um einen temporären HTTP-Server zu starten und unser Bild kurzfristig öffentlich zu machen.


Schritt: Container für das Bild erstellen
📌 Endpunkt:


POST `https://graph.instagram.com/{IG_USER_ID}/media`
📌 Erforderliche Parameter:

image_url: Ngrok-URL zum Bild
caption: Bildunterschrift (optional mit Emojis & Hashtags)

📌 Beispiel: Container für einen Post erstellen
```
curl -X POST "https://graph.instagram.com/{IG_USER_ID}/media" \
  -d "image_url=https://xyz.ngrok.io/mein-bild.jpg" \
  -d "caption=🌄 Wunderschöner Sonnenuntergang! #nature #sunset" \
  -d "access_token={ACCESS_TOKEN}"
```
📌 Antwort:

{
  "id": "17895695668004550"
}
🚀 Dieser id-Wert ist die Container-ID!


Vorgehensweise beim Veröffentlichen einer Story
📌 Instagram erlaubt keine Captions oder Tags für Stories!

📌 Endpunkt:

POST `https://graph.instagram.com/{IG_USER_ID}/media`
📌 Erforderliche Parameter:

image_url: Ngrok-URL zum Bild
media_type: "STORY"
📌 Beispiel: Story-Container erstellen

```
curl -X POST "https://graph.instagram.com/{IG_USER_ID}/media" \
  -d "image_url=https://xyz.ngrok.io/meine-story.jpg" \
  -d "media_type=STORY" \
  -d "access_token={ACCESS_TOKEN}"
```
📌 Antwort:

{
  "id": "17895695668004551"
}
📌 Story veröffentlichen
```
curl -X POST "https://graph.instagram.com/{IG_USER_ID}/media_publish" \
  -d "creation_id=17895695668004551" \
  -d "access_token={ACCESS_TOKEN}"
```
📌 Antwort:

{
  "id": "17922345678901235"
}
📌 🚀 Story ist jetzt veröffentlicht!