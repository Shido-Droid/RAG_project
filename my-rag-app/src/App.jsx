import { useState, useRef, useEffect } from 'react';
import { marked } from 'marked';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';

function App() {
  const [messages, setMessages] = useState(() => {
    const savedMessages = localStorage.getItem('chatMessages');
    return savedMessages ? JSON.parse(savedMessages) : [];
  });
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState('');
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    localStorage.setItem('chatMessages', JSON.stringify(messages));
  }, [messages]);

  // メッセージが更新されるたびにシンタックスハイライトとコピーボタンを適用
  useEffect(() => {
    // このエフェクトはレンダリング後に毎回実行されます。
    // dangerouslySetInnerHTML によってDOMが再生成されるため、
    // 都度ハイライトの適用とボタンの追加が必要です。
    document.querySelectorAll('pre').forEach(pre => {
      const code = pre.querySelector('code');
      if (!code) return;

      // 1. ハイライトを適用
      hljs.highlightElement(code);

      // 2. コピーボタンが既にあれば追加しない
      if (pre.querySelector('.copy-button')) return;

      // 3. ボタンを追加
      pre.style.position = 'relative';

      const button = document.createElement('button');
      const copyIcon = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>`;
      const checkIcon = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-green-400"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>`;

      button.innerHTML = copyIcon;
      button.className = 'copy-button absolute top-2 right-2 p-1 rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors opacity-20 hover:opacity-100 focus:opacity-100';
      button.title = 'Copy code';

      button.addEventListener('click', (e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(code.innerText).then(() => {
          button.innerHTML = checkIcon;
          button.title = 'Copied!';
          setTimeout(() => {
            button.innerHTML = copyIcon;
            button.title = 'Copy code';
          }, 2000);
        });
      });

      pre.appendChild(button);
    });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMessage = { sender: 'user', text: input, timestamp };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setLoadingStatus('考え中...');
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('http://localhost:8000/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: input }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // ボットの空メッセージを追加
      setMessages(prev => [...prev, { sender: 'bot', text: '', sources: [], timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // 最後の不完全な行をバッファに残す

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            setMessages(prev => {
              const newMessages = [...prev];
              const lastIndex = newMessages.length - 1;
              if (data.type === 'answer') {
                newMessages[lastIndex] = { ...newMessages[lastIndex], text: newMessages[lastIndex].text + data.content };
              } else if (data.type === 'sources') {
                newMessages[lastIndex] = { ...newMessages[lastIndex], sources: data.content };
              } else if (data.type === 'status') {
                setLoadingStatus(data.content);
              }
              return newMessages;
            });
          } catch (e) {
            console.error("JSON parse error", e);
          }
        }
      }

    } catch (error) {
      if (error.name !== 'AbortError') {
        const errorMessage = { sender: 'bot', text: `エラーが発生しました: ${error.message}` };
        setMessages(prev => [...prev, errorMessage]);
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const handleClear = () => {
    setMessages([]);
  };

  return (
    <div className="bg-slate-100 h-screen flex flex-col items-center justify-center p-4 sm:p-6">
      <div className="w-full max-w-4xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col h-[90vh] sm:h-[85vh]">
        <header className="bg-white border-b border-slate-200 p-4 flex items-center gap-3 shadow-sm z-10">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold shadow-sm">
            AI
          </div>
          <h1 className="text-xl font-bold text-slate-800">AI Search Assistant</h1>
          {messages.length > 0 && (
            <button onClick={handleClear} className="ml-auto text-sm text-slate-500 hover:text-red-500 px-3 py-1 rounded hover:bg-slate-100 transition-colors">
              履歴をクリア
            </button>
          )}
        </header>

        <div className="flex-grow overflow-y-auto bg-slate-50 p-4 sm:p-6 space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 opacity-60">
              <p className="text-lg">何か質問してください</p>
            </div>
          )}
        {messages.map((msg, index) => {
            if (msg.sender === 'bot' && !msg.text && (!msg.sources || msg.sources.length === 0)) return null;
            return (
            <div key={index} className={`flex items-start gap-3 ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 shadow-sm ${msg.sender === 'user' ? 'bg-slate-700 text-white' : 'bg-blue-600 text-white'}`}>
                {msg.sender === 'user' ? 'U' : 'AI'}
              </div>
              <div className={`max-w-[85%] sm:max-w-2xl p-4 rounded-2xl shadow-sm ${msg.sender === 'user' ? 'bg-slate-700 text-white rounded-tr-none' : 'bg-white text-slate-800 border border-slate-200 rounded-tl-none'}`}>
                <div className={`prose prose-sm max-w-none ${msg.sender === 'user' ? 'prose-invert' : ''}`} dangerouslySetInnerHTML={{ __html: marked.parse(msg.text) }} />
            {msg.sources && msg.sources.length > 0 && (
                  <div className={`mt-3 pt-3 border-t text-xs ${msg.sender === 'user' ? 'border-slate-600' : 'border-slate-100'}`}>
                    <p className="font-semibold opacity-80 mb-1">参考リンク:</p>
                    <ul className="space-y-1">
                  {msg.sources.map((src, i) => (
                      <li key={i} className="truncate">
                        <a href={src.url} target="_blank" rel="noopener noreferrer" className={`${msg.sender === 'user' ? 'text-blue-300 hover:text-blue-200' : 'text-blue-600 hover:text-blue-700'} hover:underline flex items-center gap-1`}>
                          <span>🔗</span> {src.title || src.url}
                        </a>
                      </li>
                  ))}
                </ul>
              </div>
            )}
            <div className={`text-xs mt-2 opacity-70 ${msg.sender === 'user' ? 'text-blue-100' : 'text-slate-400'}`}>
              {msg.timestamp}
            </div>
          </div>
        </div>
        );
        })}
        {isLoading && (
            <div className="flex items-start gap-3">
               <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0 shadow-sm">AI</div>
               <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-2xl rounded-tl-none border border-blue-100 shadow-md flex items-center gap-3 text-blue-700">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-3 h-3 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-3 h-3 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                  <span className="text-sm font-medium animate-pulse">{loadingStatus}</span>
               </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

        <div className="p-4 bg-white border-t border-slate-200">
          <div className="flex gap-2 max-w-4xl mx-auto relative">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              handleSend();
            }
          }}
          onInput={(e) => {
            e.target.style.height = 'auto';
            e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
          }}
          placeholder="質問を入力してください... (Shift+Enterで改行)"
            className="flex-grow p-4 pr-14 bg-slate-100 border-transparent rounded-2xl focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none shadow-inner text-slate-800 placeholder-slate-400 resize-none overflow-hidden min-h-[56px]"
            rows={1}
            disabled={isLoading}
            autoFocus
        />
            {isLoading ? (
              <button 
                onClick={handleStop}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors shadow-md"
                title="生成を停止"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                  <path fillRule="evenodd" d="M4.5 7.5a3 3 0 013-3h9a3 3 0 013 3v9a3 3 0 01-3 3h-9a3 3 0 01-3-3v-9z" clipRule="evenodd" />
                </svg>
              </button>
            ) : (
            <button 
              onClick={handleSend} 
              disabled={!input.trim()} 
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors shadow-md"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
              </svg>
            </button>
            )}
          </div>
      </div>
    </div>
    </div>
  )
}

export default App
