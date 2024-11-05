const socket = io();

// 音声認識をセットアップ
const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.lang = 'ja-JP';
recognition.interimResults = false;

const textInput = document.getElementById('text-input');
const conversation = document.getElementById('conversation');

document.getElementById('send-btn').addEventListener('click', () => {
    const message = textInput.value;
    socket.emit('message', message);
    appendMessage('あなた', message);
    textInput.value = '';
});

document.getElementById('voice-btn').addEventListener('click', () => {
    recognition.start();
});

recognition.onresult = (event) => {
    const message = event.results[0][0].transcript;
    socket.emit('message', message);
    appendMessage('あなた (音声)', message);
};

socket.on('response', (response) => {
    appendMessage('ボット', response);
});

function appendMessage(sender, message) {
    const msgDiv = document.createElement('div');
    msgDiv.textContent = `${sender}: ${message}`;
    conversation.appendChild(msgDiv);
}