from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

#Flaskオブジェクトの生成
app = Flask(__name__)
socketio = SocketIO(app)


@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('message')
def handle_message(message):
    # ユーザーのリクエストを処理 (例: メニューの確認や予約の応答)
    response = process_message(message)
    socketio.emit('response', response)

def process_message(message):
    # ここでNLP処理や予約システムとの連携を行う
    if "予約" in message:
        return "予約しますか？希望の時間を教えてください。"
    elif "メニュー" in message:
        return "今日のおすすめメニューは寿司と天ぷらです。"
    return "ご用件は何でしょうか？"

if __name__ == '__main__':
    socketio.run(app)