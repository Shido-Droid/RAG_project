import React, { useState, useRef, useEffect } from 'react';
import { marked } from 'marked';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';
import * as api from '../api/client';

export default function ChatArea({
  messages,
  isLoading,
  loadingMessage,
  isHistoryLoading,
  suggestedQuestions,
  documents,
  isSidebarOpen,
  setIsSidebarOpen,
  isDarkMode,
  setIsDarkMode,
  onSend,
  onStop,
  onResetContext,
  onClearHistory,
  pendingChatInput,
  onChatInputSet
}) {
  // UI固有の状態はここに移動
  const [input, setInput] = useState('');
  const [difficulty, setDifficulty] = useState('normal');
  const [showDocSelector, setShowDocSelector] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState('');
  const [explanation, setExplanation] = useState(null); // { term, text, x, y }

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // スクロール制御
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // シンタックスハイライト
  useEffect(() => {
    document.querySelectorAll('pre code').forEach((block) => {
      hljs.highlightElement(block);
    });
  }, [messages]);

  // 外部（App.jsx）からの入力セット要求を処理
  useEffect(() => {
    if (pendingChatInput) {
      setInput(pendingChatInput);
      if (onChatInputSet) onChatInputSet();
      inputRef.current?.focus();
    }
  }, [pendingChatInput, onChatInputSet]);

  // テキストエリアの高さを内容に合わせて自動調整
  useEffect(() => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = 'auto'; // 高さをリセットしてscrollHeightを再計算させる
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [input]);

  // 送信ハンドラ
  const handleSendClick = () => {
    if (!input.trim() || isLoading) return;
    onSend(input, difficulty);
    setInput('');
  };

  // おすすめ質問クリック
  const handleSuggestedClick = (q) => {
    if (documents.length === 0) {
      setInput(q);
      return;
    }
    setPendingQuestion(q);
    setShowDocSelector(true);
  };

  // ドキュメント選択関連
  const handleOpenDocSelector = () => {
    if (documents.length === 0) {
      alert("ドキュメントが登録されていません。左のサイドバーからアップロードしてください。");
      return;
    }
    setPendingQuestion(input);
    setShowDocSelector(true);
  };

  const handleSelectDoc = (doc) => {
    const title = doc.title || doc.source;
    setInput(`「${title}」の内容について、${pendingQuestion}`);
    setShowDocSelector(false);
    setPendingQuestion('');
  };

  // 用語解説
  const handleExplainTerm = async (term, x, y) => {
    const popupX = Math.min(x, window.innerWidth - 320); 
    setExplanation({ term, text: '解説を生成中...', x: popupX, y });
    try {
      const data = await api.explainTerm(term);
      setExplanation({ term, text: data.explanation, x: popupX, y });
    } catch (e) {
      setExplanation({ term, text: 'エラーが発生しました', x: popupX, y });
    }
  };

  return (
    <div className="flex-1 flex flex-col min-w-0 relative overflow-hidden">
      
      {/* Header */}
      <header className="bg-white/30 dark:bg-slate-900/30 backdrop-blur-md border-b border-white/20 dark:border-white/10 p-4 flex items-center justify-between z-10 relative">
        <div className="flex items-center gap-3">
          {!isSidebarOpen && (
            <button onClick={() => setIsSidebarOpen(true)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-slate-500 dark:text-slate-400">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
            </button>
          )}
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold shadow-sm">
            AI
          </div>
          <h1 className="font-bold text-slate-700 dark:text-slate-100">Notebook Assistant</h1>
        </div>
        <div className="flex items-center gap-2">
          <button 
            type="button"
            onClick={() => setIsDarkMode(prev => !prev)}
            className="p-2 rounded-full hover:bg-white/20 dark:hover:bg-white/10 text-slate-500 dark:text-slate-400 transition-colors mr-1"
            title={isDarkMode ? "ライトモードに切り替え" : "ダークモードに切り替え"}
          >
            {isDarkMode ? '☀️' : '🌙'}
          </button>
          <button onClick={onResetContext} className="text-xs text-slate-500 dark:text-slate-400 hover:text-indigo-600 px-3 py-1 rounded-full hover:bg-white/40 dark:hover:bg-white/10 transition-colors border border-white/20 dark:border-white/10" title="これまでの会話の流れをリセットします">
            話題を変える
          </button>
          <button onClick={onClearHistory} className="text-xs text-slate-400 hover:text-red-500 px-3 py-1 rounded-full hover:bg-white/40 dark:hover:bg-white/10 transition-colors">
            履歴削除
          </button>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-8 space-y-6 z-10 relative">
        {isHistoryLoading ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400">
            <div className="w-10 h-10 border-4 border-slate-200 border-t-indigo-500 rounded-full animate-spin mb-4"></div>
            <p className="animate-pulse">チャット履歴を読み込み中...</p>
          </div>
        ) : (
          <>
            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-slate-300 dark:text-slate-600 space-y-4">
                <div className="text-6xl">✨</div>
                <p className="text-xl font-medium">何でも聞いてください</p>
                <div className="flex flex-wrap gap-2 justify-center mt-4">
                  {suggestedQuestions.map((q, i) => (
                    <button key={i} onClick={() => handleSuggestedClick(q)} className="text-sm bg-white/40 dark:bg-slate-800/40 backdrop-blur-sm border border-white/30 dark:border-white/10 px-4 py-2 rounded-full hover:bg-white/60 dark:hover:bg-white/10 hover:text-blue-600 dark:hover:text-blue-400 transition-all shadow-sm dark:text-slate-300">
                      {q}
                    </button>
                  ))}
                </div>
                <p className="text-sm">左のサイドバーからPDFや資料を追加できます</p>
              </div>
            )}
        
            {messages.map((msg, index) => (
              <div key={index} className={`flex gap-4 max-w-3xl mx-auto ${msg.sender === 'user' ? 'justify-end' : ''}`}>
                {msg.sender !== 'user' && (
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-1 ${msg.sender === 'system' ? 'bg-green-500 text-white' : 'bg-indigo-600 text-white'}`}>
                    {msg.sender === 'system' ? '✓' : 'AI'}
                  </div>
                )}
                
                <div className={`flex flex-col max-w-[85%] ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className={`px-5 py-3 rounded-2xl shadow-sm prose prose-sm max-w-none dark:prose-invert backdrop-blur-md ${
                    msg.sender === 'user' 
                      ? 'bg-blue-600/90 dark:bg-blue-600/80 text-white rounded-tr-none shadow-lg border border-blue-500/30' 
                      : msg.sender === 'system'
                      ? 'bg-green-50/40 dark:bg-green-900/30 text-green-800 dark:text-green-300 border border-green-200/30 dark:border-green-700/30'
                      : 'bg-white/40 dark:bg-slate-800/40 text-slate-800 dark:text-slate-100 border border-white/30 dark:border-white/10 rounded-tl-none shadow-md'
                  }`}>
                    <div 
                      onClick={(e) => {
                        if (e.target.classList.contains('technical-term')) {
                          e.stopPropagation();
                          const rect = e.target.getBoundingClientRect();
                          handleExplainTerm(e.target.dataset.term, rect.left, rect.bottom + 5);
                        }
                      }}
                      dangerouslySetInnerHTML={{ __html: marked.parse(msg.text).replace(/\[\[(.*?)\]\]/g, '<span class="technical-term text-indigo-600 dark:text-indigo-400 font-bold cursor-pointer hover:underline decoration-indigo-400 underline-offset-2" data-term="$1">$1</span>') }} 
                    />
                  </div>

                  {/* Sources Display */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {msg.sources.map((src, i) => {
                        const isWeb = src.url && /^https?:\/\//.test(src.url);
                        if (isWeb) {
                          return (
                            <a key={i} href={src.url} target="_blank" rel="noopener noreferrer"
                               className="flex items-center gap-1 text-xs bg-white/50 dark:bg-slate-800/50 border border-white/30 dark:border-white/10 px-2 py-1 rounded-full text-blue-600 dark:text-blue-400 hover:bg-white/80 dark:hover:bg-white/10 transition-colors shadow-sm">
                              <span className="opacity-50">🔗</span> 
                              <span className="truncate max-w-[150px]">{src.title || src.url}</span>
                            </a>
                          );
                        } else {
                          return (
                            <span key={i} className="flex items-center gap-1 text-xs bg-white/30 dark:bg-slate-800/30 border border-white/20 dark:border-white/10 px-2 py-1 rounded-full text-slate-600 dark:text-slate-400 cursor-default shadow-sm">
                              <span className="opacity-50">📄</span> 
                              <span className="truncate max-w-[150px]">{src.title || src.url}</span>
                            </span>
                          );
                        }
                      })}
                    </div>
                  )}
                  <span className="text-[10px] text-slate-300 mt-1 px-1">{msg.timestamp}</span>
                </div>

                {msg.sender === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-500 flex-shrink-0 mt-1">
                    U
                  </div>
                )}
              </div>
            ))}
          </>
        )}
        
        {isLoading && (
          <div className="flex gap-4 max-w-3xl mx-auto">
             <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0 mt-1">AI</div>
             <div className="bg-white/40 dark:bg-slate-800/40 backdrop-blur-md px-5 py-4 rounded-2xl rounded-tl-none border border-white/30 dark:border-white/10 flex items-center gap-2 shadow-sm">
                {loadingMessage ? (
                  <span className="text-sm text-slate-500 dark:text-slate-400 animate-pulse">{loadingMessage}</span>
                ) : (
                  <>
                    <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </>
                )}
             </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-white/30 dark:bg-slate-900/30 backdrop-blur-xl border-t border-white/20 dark:border-white/10 z-10 relative">
        {/* Difficulty Selector */}
        <div className="flex justify-center gap-2 mb-3">
          {[
            { id: 'easy', label: '🔰 初学者向け', desc: 'やさしく解説' },
            { id: 'normal', label: '標準', desc: 'バランスよく' },
            { id: 'professional', label: '🎓 専門的', desc: '実務・詳細' }
          ].map((mode) => (
            <button
              key={mode.id}
              onClick={() => setDifficulty(mode.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${
                difficulty === mode.id 
                  ? 'bg-indigo-500/10 dark:bg-indigo-500/20 border-indigo-500/30 text-indigo-700 dark:text-indigo-300 shadow-sm' 
                  : 'bg-white/20 dark:bg-white/5 border-white/20 dark:border-white/10 text-slate-500 dark:text-slate-300 hover:bg-white/40 dark:hover:bg-white/10'
              }`}
              title={mode.desc}
            >
              {mode.label}
            </button>
          ))}
        </div>

        <div className="max-w-3xl mx-auto flex gap-2 items-end">
          <button
            onClick={handleOpenDocSelector}
            className="p-3 mb-1 text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-white/40 dark:hover:bg-white/10 rounded-xl transition-colors"
            title="ドキュメントを選択して質問"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
          </button>
          <div className="relative flex-grow">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                handleSendClick();
              }
            }}
            placeholder="質問を入力... (Enterで送信、Shift+Enterで改行)"
            className="w-full p-4 pr-12 bg-white/40 dark:bg-black/20 backdrop-blur-md border border-white/30 dark:border-white/10 rounded-2xl focus:bg-white/60 dark:focus:bg-black/40 focus:ring-2 focus:ring-indigo-500/50 focus:border-transparent transition-all outline-none resize-none min-h-[60px] max-h-[200px] shadow-sm dark:text-white dark:placeholder-slate-400"
            rows={1}
            disabled={isLoading}
          />
          <button 
            onClick={isLoading ? onStop : handleSendClick}
            disabled={!isLoading && !input.trim()}
            className={`absolute right-3 bottom-3 p-2 rounded-xl transition-all duration-200 ${
              isLoading 
                ? 'bg-red-500/10 text-red-500 hover:bg-red-500/20' 
                : input.trim() 
                  ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-md hover:shadow-lg' 
                  : 'bg-slate-200/50 dark:bg-slate-700/50 text-slate-400 dark:text-slate-500 cursor-not-allowed'
            }`}
          >
            {isLoading ? (
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            )}
          </button>
          </div>
        </div>
        <p className="text-center text-xs text-slate-300 mt-2">AIは間違いを犯す可能性があります。重要な情報は確認してください。</p>
      </div>

      {/* Explanation Popup */}
      {explanation && (
        <div 
          className="fixed z-50 bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl rounded-xl shadow-2xl border border-white/20 dark:border-white/10 p-4 w-80 animate-in fade-in zoom-in duration-200"
          style={{ top: explanation.y, left: explanation.x }}
        >
          <div className="flex justify-between items-start mb-2">
            <h4 className="font-bold text-indigo-600 dark:text-indigo-400 text-sm">{explanation.term}</h4>
            <button onClick={() => setExplanation(null)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs">✕</button>
          </div>
          <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
            {explanation.text}
          </p>
        </div>
      )}

      {/* Document Selection Modal */}
      {showDocSelector && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 dark:border-white/10 max-w-md w-full overflow-hidden flex flex-col max-h-[80vh] animate-in fade-in zoom-in duration-200">
            <div className="p-4 border-b border-white/20 dark:border-white/10 flex justify-between items-center bg-white/20 dark:bg-white/5">
              <h3 className="font-bold text-slate-700 dark:text-slate-200">対象のドキュメントを選択</h3>
              <button 
                onClick={() => setShowDocSelector(false)} 
                className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-200 text-slate-400 transition-colors"
              >
                ✕
              </button>
            </div>
            <div className="overflow-y-auto p-2 space-y-1">
              {documents.map((doc, i) => (
                <button
                  key={i}
                  onClick={() => handleSelectDoc(doc)}
                  className="w-full text-left p-3 hover:bg-white/40 dark:hover:bg-white/10 border border-transparent rounded-xl transition-all flex items-center gap-3 group"
                >
                  <div className="w-10 h-10 rounded-lg bg-blue-100/50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 flex items-center justify-center text-xl flex-shrink-0">
                    📄
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-slate-700 dark:text-slate-200 truncate text-sm">{doc.title || doc.source}</div>
                    {doc.summary && <div className="text-xs text-slate-400 truncate mt-0.5">{doc.summary}</div>}
                  </div>
                  <div className="text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity text-sm font-bold">
                    選択
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
