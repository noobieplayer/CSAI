const socket = io();

// 音声認識をセットアップ
const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.lang = 'ja-JP';
recognition.interimResults = false;

var sender_flag

const textInput = document.getElementById('text-input');
const conversation = document.getElementById('conversation');

document.getElementById('send-btn').addEventListener('click', () => {
    const message = textInput.value;
    sender_flag = true
    socket.emit('message', message);
    appendMessage('あなた', message, sender_flag);
    textInput.value = '';
});

document.getElementById('voice-btn').addEventListener('click', () => {
    recognition.start();
});

recognition.onresult = (event) => {
    const message = event.results[0][0].transcript;
    sender_flag = true
    socket.emit('message', message);
    appendMessage('あなた (音声)', message, sender_flag);
};

socket.on('response', (response) => {
    sender_flag = false
    appendMessage('ボット', response, sender_flag);
});

function appendMessage(sender, message, sender_flag) {
    const msgDiv = document.createElement('div');
    msgDiv.textContent = `${sender}: ${message}`;

    // クラスを設定
    if (sender_flag) {
        msgDiv.classList.add('message', 'user-message');
    } else {
        msgDiv.classList.add('message', 'bot-message');
    }

    conversation.appendChild(msgDiv);
}