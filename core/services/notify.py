import os, json, requests, time

class NotifyService:
    def __init__(self):
        self.token = os.getenv("WHATSAPP_TOKEN")
        self.phone_id = os.getenv("WHATSAPP_PHONE_ID")
        self.to = os.getenv("WHATSAPP_TO")
        self.enabled = all([self.token, self.phone_id, self.to])

    def send_whatsapp_text(self, body: str) -> bool:
        if not self.enabled:
            return False
        url = f"https://graph.facebook.com/v19.0/{self.phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": self.to,
            "type": "text",
            "text": {"body": body[:4096]}
        }
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
            if r.status_code >= 300:
                print(f"[NotifyService] Erro WhatsApp {r.status_code}: {r.text}")
                return False
            return True
        except Exception as e:
            print(f"[NotifyService] Exceção envio WhatsApp: {e}")
            return False

    def notify_found(self, serial: str, texto: str, ciclo: int):
        msg = f"[BOT] Texto '{texto}' encontrado no {serial} (ciclo {ciclo})."
        self.send_whatsapp_text(msg)