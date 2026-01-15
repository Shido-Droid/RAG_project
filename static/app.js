document.addEventListener('DOMContentLoaded', () => {
    const questionInput = document.getElementById('question');
    const sendBtn = document.getElementById('send-btn');
    const chatBox = document.getElementById('chat-box');

    // Auto-resize textarea
    questionInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.value === '') this.style.height = '52px';
    });

    // Handle Enter key (Shift+Enter for new line)
    questionInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            ask();
        }
    });

    sendBtn.addEventListener('click', ask);

    async function ask() {
        const text = questionInput.value.trim();
        if (!text) return;

        // Reset input
        questionInput.value = '';
        questionInput.style.height = '52px';
        sendBtn.disabled = true;

        // Add user message
        appendMessage(text, 'user');

        // Create bot message container with loading indicator
        const botMsgId = 'msg-' + Date.now();
        const botMsgContentId = botMsgId + '-content';

        const botDiv = document.createElement('div');
        botDiv.className = 'message bot';
        botDiv.id = botMsgId;
        botDiv.innerHTML = `
            <div id="${botMsgContentId}">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        chatBox.appendChild(botDiv);
        scrollToBottom();

        // Accumulate answer text
        let fullAnswer = '';
        let sources = [];

        try {
            const response = await fetch('/api/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: text })
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            // Remove loading indicator when first chunk arrives
            let isFirstChunk = true;
            const contentDiv = document.getElementById(botMsgContentId);

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (!line.trim()) continue;

                    try {
                        const data = JSON.parse(line);

                        if (data.type === 'status') {
                            // Optional: Show status update (e.g. "Searching...")
                            if (isFirstChunk) {
                                contentDiv.innerHTML = `<span style="color: #94a3b8; font-style: italic;">${data.content}</span>`;
                            }
                        }
                        else if (data.type === 'answer') {
                            if (isFirstChunk || contentDiv.querySelector('.typing-indicator') || contentDiv.querySelector('span')) {
                                contentDiv.innerHTML = ''; // Clear loading/status
                                isFirstChunk = false;
                            }
                            fullAnswer += data.content;
                            contentDiv.innerHTML = marked.parse(fullAnswer);
                            hljs.highlightAll(); // Re-highlight code blocks
                            scrollToBottom();
                        }
                        else if (data.type === 'sources') {
                            sources = data.content;
                        }
                    } catch (e) {
                        console.error('Error parsing JSON chunk', e);
                    }
                }
            }

            // Append sources if available
            if (sources.length > 0) {
                let sourcesHtml = '<div style="margin-top: 15px; border-top: 1px solid #475569; padding-top: 10px; font-size: 0.85em; color: #94a3b8;"><strong>Sources:</strong><ul>';
                sources.forEach(source => {
                    const filename = source.metadata?.source || 'Unknown';
                    const score = source.score ? `(Score: ${source.score.toFixed(2)})` : '';
                    sourcesHtml += `<li>${filename} ${score}</li>`;
                });
                sourcesHtml += '</ul></div>';
                contentDiv.innerHTML += sourcesHtml;
            }

        } catch (e) {
            document.getElementById(botMsgContentId).innerHTML = `<span style="color: #ef4444;">Error: ${e.message}</span>`;
        } finally {
            sendBtn.disabled = false;
            questionInput.focus();
        }
    }

    function appendMessage(text, type) {
        const div = document.createElement('div');
        div.className = `message ${type}`;
        div.innerHTML = text.replace(/\n/g, '<br>'); // Simple escape for user text
        chatBox.appendChild(div);
        scrollToBottom();
    }

    function scrollToBottom() {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
});
