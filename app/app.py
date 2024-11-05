from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from google.cloud import dialogflow_v2 as dialogflow
import os
from dotenv import load_dotenv
import sqlite3
import datetime
import json

DIALOGFLOW_PROJECT_ID = os.environ.get("DIALOGFLOW_PROJECT_ID")
DIALOGFLOW_LANGUAGE_CODE = 'ja'
SESSION_ID = os.environ.get("SESSION_ID")

#Flaskオブジェクトの生成
app = Flask(__name__)
socketio = SocketIO(app)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'private_key.json'

reservation_dict = {}
webhook_one_running = True

def sql_insert_query(req_comment): # SQLのInsert文クエリ発行処理
    conn = sqlite3.connect('restaurant-A.v3.4.db')  # SQLiteのデータベースファイル
    cursor = conn.cursor()

    f = open('reservation.json', 'r')
    reservation_dict_json = json.load(f)
    f.close()

    date, time, people, name, phone_number_query = reservation_dict_json.values()

    comment_query = req_comment

    date_query = date[0:10]
    time_query = time[11:16]
    people_query = int(people)
    name_query = name["name"]
    
    cursor.execute("""
        SELECT 席番号 FROM 席情報 
        WHERE 席番号 in (SELECT 席番号 FROM 席情報 
        WHERE 対応人数 >= ? 
        EXCEPT SELECT 席番号 FROM 予約 
        WHERE 予約日 = ? 
        AND 予約時間 = ?) 
        ORDER by 対応人数,席番号 LIMIT 1;
    """, (people_query, date_query, time_query))
    
    reservation__table = cursor.fetchall()

    table_num = reservation__table[0][0]

    dt_now = datetime.datetime.now()
    today_query = dt_now.strftime('%Y-%m-%d')
    now_time_query = dt_now.strftime('%H:%M')

    cursor.execute("""
        INSERT INTO 予約 
        (席番号, 予約人数, 予約者氏名, 電話番号, 日付, 時間, 予約日, 予約時間, 備考) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (table_num, people_query, name_query, phone_number_query, today_query, now_time_query, date_query, time_query, comment_query))

    #結果を確定
    conn.commit()

    conn.close()

# SQLiteデータベースにクエリを実行して予約可能かどうかを確認
def search_reservations(query_date, query_time, query_people):
    conn = sqlite3.connect('restaurant-A.v3.4.db')  # SQLiteのデータベースファイル
    cursor = conn.cursor()
    
    # 予約可能な場合を検索
    cursor.execute("""
        SELECT 席番号 FROM 席情報 
        WHERE 対応人数 >= ? 
        EXCEPT SELECT 席番号 FROM 予約 
        WHERE 予約日 = ? 
        AND 予約時間 = ?;
    """, (query_people, query_date, query_time)) # 予約時間 BETWEEN "18:00" AND "19:00"でもいい
    
    results = cursor.fetchall()
    conn.close()

    return len(results) > 0  # 予約が存在する場合はTrueを返す

def detect_intent_texts(project_id, session_id, text, language_code):
    
    # Dialogflowセッションクライアントを作成
    session_client = dialogflow.SessionsClient()

    # セッションパスを構築
    session = session_client.session_path(project_id, session_id)

    # ユーザーのテキストを構築
    text_input = dialogflow.TextInput(text=text, language_code=language_code)

    # QueryInputにテキストを設定
    query_input = dialogflow.QueryInput(text=text_input)

    # Dialogflow APIにリクエストを送信してインテントを検出
    response = session_client.detect_intent(
        request={"session": session, "query_input": query_input}
    )

    # 結果を返す
    return response.query_result.fulfillment_text

@app.route('/')
def index():
    return render_template('index.html')

# Webhookエンドポイントを設定
@app.route('/webhook', methods=['POST'])
def webhook():
    global webhook_one_running

    if webhook_one_running:
        webhook_one_running = False

        # DialogflowからのリクエストをJSONとして取得
        req = request.get_json(silent=True, force=True)

        global reservation_dict

        if req['queryResult']['intent']['displayName'] == "reserve - date" or "not - reserve" in req['queryResult']['intent']['displayName']:
            reservation_dict = {}

        if req['queryResult']['intent']['displayName'] == "reserve - remarks":
            sql_insert_query(req['queryResult']['queryText'])

        else:
            # パラメータを取得
            parameters = req['queryResult']['parameters']
            key, value = parameters.popitem()

            # 予約情報の保存処理
            reservation_dict[key] = value

            if len(reservation_dict) == 5:
                reservation_json = open('reservation.json', 'w')
                json.dump(reservation_dict, reservation_json)
                reservation_json.close()

                reservation_dict = {}

            if len(reservation_dict) == 3:
                date, time, people = reservation_dict.values()

                date_query = date[0:10]
                time_query = time[11:16]
                people_query = int(people)

                date_now = datetime.datetime.now()

                date_time = datetime.datetime(
                    int(date_query[:4]),  # 年
                    int(date_query[5:7]), # 月
                    int(date_query[8:]),  # 日
                    int(time_query[:2]),  # 時
                    int(time_query[3:])   # 分
                )

                if date_time < date_now:
                    fulfillment_text = "ご希望の予約時刻、及び予約日は過ぎていますので予約できません。"
                    # Dialogflowに返す応答を構築
                    return jsonify({
                        "fulfillmentText": fulfillment_text
                    })
                elif people_query > 6:
                    fulfillment_text = "申し訳ございませんが、7名以上でのご予約は対応していません。"
                    # Dialogflowに返す応答を構築
                    return jsonify({
                        "fulfillmentText": fulfillment_text
                    })

                is_available = search_reservations(date_query, time_query, people_query)

                # 予約可能かどうかに基づいて応答を生成
                if not is_available:
                    fulfillment_text = f"{date_query}の{time_query}に{people_query}名での予約は埋まっています。"
                    # Dialogflowに返す応答を構築
                    return jsonify({
                        "fulfillmentText": fulfillment_text
                    })
    else:
        webhook_one_running = True

@socketio.on('message')
def handle_message(message):
    # ユーザーのリクエストを処理 (例: メニューの確認や予約の応答)
    response = process_message(message, DIALOGFLOW_PROJECT_ID, SESSION_ID)
    socketio.emit('response', response)

def process_message(message, DIALOGFLOW_PROJECT_ID, SESSION_ID):
    # ここでNLP処理や予約システムとの連携を行う
    language_code = "ja"  # 使用言語（日本語）

    # Dialogflowにテキストを送信し、インテントを解析
    return detect_intent_texts(DIALOGFLOW_PROJECT_ID, SESSION_ID, message, language_code)

# Flaskサーバーを実行
if __name__ == '__main__':
    socketio.run(app)