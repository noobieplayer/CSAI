from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from google.cloud import dialogflow_v2 as dialogflow
import os
from dotenv import load_dotenv
import sqlite3

DIALOGFLOW_PROJECT_ID = os.environ.get("DIALOGFLOW_PROJECT_ID")
DIALOGFLOW_LANGUAGE_CODE = 'ja'
SESSION_ID = os.environ.get("SESSION_ID")

#Flaskオブジェクトの生成
app = Flask(__name__)
socketio = SocketIO(app)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'private_key.json'

# SQLiteデータベースにクエリを実行して予約可能かどうかを確認
def search_reservations(query_date, query_time, query_people):
    conn = sqlite3.connect('your_database.db')  # SQLiteのデータベースファイル
    cursor = conn.cursor()
    
    # 予約可能な場合を検索
    cursor.execute("""
        SELECT * FROM reservations
        WHERE date = ? AND time = ? AND people = ? AND available = 1
    """, (query_date, query_time, query_people))
    
    results = cursor.fetchall()
    conn.close()

    return len(results) > 0  # 予約が存在する場合はTrueを返す

def detect_intent_texts(project_id, session_id, texts, language_code):
    """
    Dialogflowにテキストを送信し、インテントを解析する関数。
    :param project_id: Google CloudプロジェクトID
    :param session_id: ユーザーごとのセッションID
    :param texts: ユーザーが送信するテキスト（リスト）
    :param language_code: 使用する言語（例: 'ja'）
    :return: Dialogflowの応答を返す
    """
    
    # Dialogflowセッションクライアントを作成
    session_client = dialogflow.SessionsClient()

    # セッションパスを構築
    session = session_client.session_path(project_id, session_id)

    for text in texts:
        # ユーザーのテキストを構築
        text_input = dialogflow.TextInput(text=text, language_code=language_code)

        # QueryInputにテキストを設定
        query_input = dialogflow.QueryInput(text=text_input)

        # Dialogflow APIにリクエストを送信してインテントを検出
        response = session_client.detect_intent(
            request={"session": session, "query_input": query_input}
        )

        # Dialogflow APIにリクエストを送信
        response = session_client.detect_intent(
            request={"session": session, "query_input": query_input}
        )

        # 結果を返す(response.query_result.fulfillment_text)
        # [response.query_result.query_text,response.query_result.query_text,response.query_result.intent_detection_confidence,response.query_result.fulfillment_text]
        return response.query_result.fulfillment_text

@app.route('/')
def index():
    return render_template('index.html')

# Webhookエンドポイントを設定
@app.route('/webhook', methods=['POST'])
def webhook():
    # DialogflowからのリクエストをJSONとして取得
    req = request.get_json(silent=True, force=True)

    # リクエスト内容を解析
    intent_name = req['queryResult']['intent']['display_name']  # インテント名を取得
    parameters = req['queryResult']['parameters']  # パラメータを取得
    query_text = req['queryResult']['queryText']  # ユーザーの元の発言

    # パラメータの処理（例：予約確認の場合、日付や時間を取得）
    if intent_name == '予約確認':
        date = parameters.get('date')  # 日付パラメータ
        time = parameters.get('time')  # 時間パラメータ
        people = parameters.get('people')  # 人数パラメータ

        # 予約状況の確認ロジック（例: データベース検索）
        # 仮に予約が可能とした場合の応答
        response_text = f"{date}の{time}に{people}名での予約が可能です。"
    
    else:
        # 他のインテントに対する処理
        response_text = "何かお手伝いしましょうか？"

    # Dialogflowに返す応答を構築
    return jsonify({
        "fulfillmentText": response_text
    })

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

if __name__ == '__main__':
    socketio.run(app)