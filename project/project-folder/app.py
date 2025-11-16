from flask import Flask, jsonify
import json
import requests
from byte import encrypt_packet, decrypt_packet, Encrypt_ID
from protobuf_parser import Parser
import visit_count_pb2

app = Flask(__name__)


# ===============================
# LOAD TOKEN THEO SERVER
# ===============================
def load_tokens(server_name):
    try:
        if server_name == "VN":
            path = "token_vn.json"
        elif server_name == "IND":
            path = "token_ind.json"
        elif server_name in ["BR", "US", "SAC", "NA"]:
            path = "token_br.json"
        else:
            path = "token_bd.json"

        with open(path, "r") as f:
            data = json.load(f)

        tokens = [item["token"] for item in data if item.get("token") and item["token"] not in ["", "N/A"]]
        return tokens

    except Exception as e:
        return []


# ===============================
# GET URL THEO SERVER
# ===============================
def get_url(server_name):
    if server_name == "VN":
        return "https://client.vietnam.freefiremobile.com/GetPlayerPersonalShow"
    elif server_name == "IND":
        return "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
    elif server_name in ["BR", "US", "SAC", "NA"]:
        return "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
    else:
        return "https://clientbp.ggblueshark.com/GetPlayerPersonalShow"


# ===============================
# API CHÍNH
# ===============================
@app.route("/<server>/<uid>", methods=["GET"])
def get_profile(server, uid):
    try:
        uid_hex = Encrypt_ID(uid)
        payload = f"0a{uid_hex}"

        encrypted = encrypt_packet(payload)

        tokens = load_tokens(server)
        if not tokens:
            return jsonify({"error": "Không tìm thấy token cho server này"}), 400

        url = get_url(server)

        headers = {
            "Content-Type": "application/octet-stream",
            "User-Agent": "Dalvik/2.1.0",
        }

        success = False
        final_data = None

        for token in tokens:
            headers["Authorization"] = token

            try:
                resp = requests.post(url, data=bytes.fromhex(encrypted), headers=headers, timeout=8)

                if resp.status_code != 200:
                    continue

                decrypted = decrypt_packet(resp.content.hex())

                parser = Parser()
                parsed = parser.parse(decrypted)

                basic = visit_count_pb2.BasicInfo()

                for result in parsed.results:
                    if result.field == 1:
                        nested = result.data
                        for r2 in nested.results:
                            if r2.field == 1:
                                basic.UID = r2.data
                            elif r2.field == 3:
                                basic.PlayerNickname = r2.data
                            elif r2.field == 5:
                                basic.PlayerRegion = r2.data
                            elif r2.field == 6:
                                basic.Levels = r2.data
                            elif r2.field == 21:
                                basic.Likes = r2.data

                final_data = {
                    "UID": basic.UID,
                    "Name": basic.PlayerNickname,
                    "Region": basic.PlayerRegion,
                    "Level": basic.Levels,
                    "Likes": basic.Likes
                }

                success = True
                break

            except:
                continue

        if not success:
            return jsonify({"error": "Không thể lấy dữ liệu, token có thể đã chết"}), 500

        return jsonify(final_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "API Free Fire Profile đang chạy!",
        "usage": "/<server>/<uid>",
        "example": "/VN/123456789"
    })


# ===============================
# CHẠY LOCAL
# ===============================
if __name__ == "__main__":
    app.run(debug=True)
