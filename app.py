import json
import requests
from flask import Flask, request, jsonify

# Kullanıcı tarafından sağlanan bilgiler
TELEGRAM_BOT_TOKEN = "7033397791:AAHngi7cWt9_QeR9y-5JfRpl3CDBOzitwjU"
TELEGRAM_CHAT_ID = "1051307023"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

app = Flask(__name__)

# Hisse bazında alarm sayacını tutacak sözlük
# Örnek: {"BTCUSD": 2, "ETHUSD": 5}
alarm_counters = {}

def send_telegram_message(text, reply_markup=None):
    """Telegram'a mesaj gönderme işlevi."""
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    try:
        response = requests.post(TELEGRAM_API_URL, data=payload)
        response.raise_for_status()
        return True, response.json()
    except requests.exceptions.RequestException as e:
        print(f"Telegram'a mesaj gönderirken hata oluştu: {e}")
        return False, str(e)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """TradingView'den gelen webhook'ları işler."""
    try:
        # TradingView'den gelen JSON payload'u
        data = request.get_json()
        
        # Gerekli değişkenleri çıkar
        ticker = data.get('ticker')
        close = data.get('close')
        exchange = data.get('exchange', 'BINANCE') # Exchange bilgisi payload'da yoksa varsayılan atama
        interval = data.get('interval', '4h') # Interval bilgisi payload'da yoksa varsayılan atama
        
        if not ticker or not close:
            return jsonify({"status": "error", "message": "Eksik 'ticker' veya 'close' bilgisi"}), 400

        # Ticker'ı büyük harfe çevir ve sayacı artır
        ticker = ticker.upper()
        alarm_counters[ticker] = alarm_counters.get(ticker, 0) + 1
        current_count = alarm_counters[ticker]

        # Mesajı istenen formatta düzenle
        # Örnek: "BTCUSD : 110056.24\nAl Sinyali Geldi. (2. Alarm)"
        message_text = (
            f"<b>{ticker}</b> : {close}\n"
            f"Al Sinyali Geldi. ({current_count}. Alarm)"
        )

        # TradingView linki için reply_markup oluştur
        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "Grafiğe Git",
                        "url": f"https://www.tradingview.com/chart/rGT1wY1Z/?symbol={exchange}:{ticker}&interval={interval}"
                    }
                ]
            ]
        }

        # Telegram'a mesajı gönder
        success, response = send_telegram_message(message_text, reply_markup)

        if success:
            return jsonify({"status": "success", "message": "Webhook başarıyla işlendi ve Telegram'a gönderildi"}), 200
        else:
            return jsonify({"status": "error", "message": f"Telegram'a gönderim hatası: {response}"}), 500

    except Exception as e:
        print(f"Webhook işlenirken genel hata oluştu: {e}")
        return jsonify({"status": "error", "message": f"İç sunucu hatası: {str(e)}"}), 500

@app.route('/reset/<ticker_name>', methods=['POST'])
def reset_counter(ticker_name):
    """Belirli bir hissenin alarm sayacını sıfırlar."""
    ticker_name = ticker_name.upper()
    if ticker_name in alarm_counters:
        del alarm_counters[ticker_name]
        message = f"{ticker_name} için alarm sayacı sıfırlandı."
        send_telegram_message(f"ℹ️ {message}")
        return jsonify({"status": "success", "message": message}), 200
    else:
        message = f"{ticker_name} için aktif sayaç bulunamadı."
        return jsonify({"status": "info", "message": message}), 200

@app.route('/status', methods=['GET'])
def get_status():
    """Aktif sayaçların durumunu gösterir."""
    return jsonify({"status": "ok", "active_counters": alarm_counters}), 200


