import React, { useState, useRef, useEffect } from 'react';
import { marked } from 'marked';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';
import * as api from '../api/client';
import { useToast } from './ui/ToastContext';

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
  const [input, setInput] = useState('');
  const [difficulty, setDifficulty] = useState('normal');
  const [showDocSelector, setShowDocSelector] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState('');
  const [explanation, setExplanation] = useState(null); // { term, text, x, y }

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Scroll control
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Syntax highlighting & Copy Button Injection
  // Use a ref to track which blocks have been processed to avoid duplicate headers
  const processedBlocksRef = useRef(new WeakSet());

  useEffect(() => {
    const processCodeBlocks = () => {
      document.querySelectorAll('pre code').forEach((block) => {
        // Highlight
        if (!block.classList.contains('hljs')) {
          hljs.highlightElement(block);
        }

        // Check if already processed to prevent double injection
        const pre = block.parentElement;
        if (pre.querySelector('.code-header')) return;

        // Create header
        const header = document.createElement('div');
        header.className = 'code-header flex justify-between items-center px-4 py-2 bg-slate-700/50 rounded-t-lg border-b border-white/10';

        // Language label
        const langClass = Array.from(block.classList).find(c => c.startsWith('language-'));
        const lang = langClass ? langClass.replace('language-', '') : 'text';
        const langSpan = document.createElement('span');
        langSpan.className = 'text-xs text-slate-400 font-mono font-medium lowercase';
        langSpan.textContent = lang;

        // Copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'text-xs text-slate-400 hover:text-white transition-colors flex items-center gap-1';
        copyBtn.innerHTML = `
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          Copy
        `;

        copyBtn.addEventListener('click', async () => {
          try {
            await navigator.clipboard.writeText(block.textContent);
            copyBtn.innerHTML = `
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
              Copied!
            `;
            copyBtn.classList.add('text-green-400');
            setTimeout(() => {
              copyBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                Copy
              `;
              copyBtn.classList.remove('text-green-400');
            }, 2000);
          } catch (err) {
            console.error("Copy failed", err);
          }
        });

        header.appendChild(langSpan);
        header.appendChild(copyBtn);

        // Adjust pre styles (remove padding from pre and add to code, or specific styling)
        pre.classList.add('relative', 'group', '!p-0', '!pt-0', '!overflow-hidden'); // Override prose styles
        block.classList.add('!p-4', '!block', '!overflow-x-auto', 'pt-2'); // Add padding to code element

        pre.insertBefore(header, block);
      });
    };

    // Run immediately
    processCodeBlocks();

    // Also run after a short delay to catch any async renders
    const timeoutId = setTimeout(processCodeBlocks, 100);

    return () => clearTimeout(timeoutId);
  }); // Run on every render to ensure headers are always present

  // Handle external input set
  useEffect(() => {
    if (pendingChatInput) {
      setInput(pendingChatInput);
      if (onChatInputSet) onChatInputSet();
      inputRef.current?.focus();
    }
  }, [pendingChatInput, onChatInputSet]);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSendClick = () => {
    if (!input.trim() || isLoading) return;
    onSend(input, difficulty);
    setInput('');
  };

  const handleSuggestedClick = (q) => {
    if (documents.length === 0) {
      setInput(q);
      return;
    }
    setPendingQuestion(q);
    setShowDocSelector(true);
  };

  // Toast hook (assuming passed or imported, but here strictly replacing alert if possible, or using props? 
  // Wait, I need to check if useToast is available here or if I should pass addToast prop from App.
  // Ideally, ChatArea should use the context too.
  // Let's import useToast here as well.

  const { addToast } = useToast();

  const handleOpenDocSelector = () => {
    if (documents.length === 0) {
      addToast("ドキュメントが登録されていません。左のサイドバーからアップロードしてください。", 'info');
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
    <div className="flex-1 flex flex-col min-w-0 relative overflow-hidden bg-slate-50/50 dark:bg-slate-950/50">

      {/* Header */}
      <header className="bg-white/40 dark:bg-slate-900/40 backdrop-blur-xl border-b border-white/20 dark:border-white/5 p-4 flex items-center justify-between z-20 relative shadow-sm">
        <div className="flex items-center gap-4">
          {!isSidebarOpen && (
            <button onClick={() => setIsSidebarOpen(true)} className="p-2 hover:bg-white/50 dark:hover:bg-slate-800/50 rounded-full text-slate-500 dark:text-slate-400 transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
            </button>
          )}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-500/20">
              AI
            </div>
            <div>
              <h1 className="font-bold text-slate-800 dark:text-slate-100 leading-tight">Expert Assistant</h1>
              <div className="flex items-center gap-1.5">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                </span>
                <span className="text-[10px] text-slate-500 font-medium tracking-wide uppercase">Online</span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setIsDarkMode(prev => !prev)}
            className="w-9 h-9 rounded-full flex items-center justify-center hover:bg-white/50 dark:hover:bg-slate-800/50 text-slate-500 dark:text-slate-400 transition-all active:scale-95"
            title={isDarkMode ? 'ライトモードに切り替え' : 'ダークモードに切り替え'}
          >
            {isDarkMode ? '☀️' : '🌙'}
          </button>
          <div className="h-4 w-px bg-slate-300 dark:bg-slate-700 mx-1"></div>
          <button onClick={onResetContext} className="text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 px-3 py-1.5 rounded-lg hover:bg-white/50 dark:hover:bg-slate-800/50 transition-colors border border-transparent hover:border-slate-200 dark:hover:border-slate-700" title="これまでの会話の流れをリセットします">
            話題を変える
          </button>
          <button onClick={onClearHistory} className="text-xs font-medium text-slate-400 hover:text-red-500 px-3 py-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors" title="チャット履歴を削除">
            履歴削除
          </button>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-8 z-10 relative scroll-smooth">
        {isHistoryLoading ? (
          <div className="h-full flex flex-col items-center justify-center">
            <div className="relative w-16 h-16">
              <div className="absolute top-0 left-0 w-full h-full border-4 border-slate-200 dark:border-slate-800 rounded-full"></div>
              <div className="absolute top-0 left-0 w-full h-full border-4 border-indigo-500 rounded-full border-t-transparent animate-spin"></div>
            </div>
            <p className="mt-4 text-slate-400 font-medium animate-pulse">チャット履歴を読み込み中...</p>
          </div>
        ) : (
          <>
            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto text-center space-y-8 animate-fade-in">
                <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-4xl shadow-2xl shadow-indigo-500/30 animate-float">
                  ✨
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">何かお手伝いしましょうか？</h2>
                  <p className="text-slate-500 dark:text-slate-400">ドキュメントについての質問や、一般的な知識についてお答えします。</p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full px-4">
                  {suggestedQuestions.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => handleSuggestedClick(q)}
                      className="group text-left p-4 bg-white/60 dark:bg-slate-800/60 backdrop-blur-md border border-white/40 dark:border-white/5 rounded-2xl hover:bg-white dark:hover:bg-slate-800 hover:scale-[1.02] hover:shadow-lg transition-all duration-300"
                    >
                      <span className="block text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">{q}</span>
                      <span className="text-xs text-slate-400">質問する &rarr;</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, index) => (
              <div key={index} className={`flex gap-4 max-w-4xl mx-auto animate-slide-up ${msg.sender === 'user' ? 'justify-end' : ''}`}>
                {msg.sender !== 'user' && (
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold flex-shrink-0 mt-1 shadow-md ${msg.sender === 'system' ? 'bg-green-500 text-white' : 'bg-gradient-to-br from-indigo-500 to-purple-600 text-white'}`}>
                    {msg.sender === 'system' ? '✓' : 'AI'}
                  </div>
                )}

                <div className={`flex flex-col max-w-[85%] ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className={`px-6 py-4 rounded-2xl shadow-sm backdrop-blur-md transition-all duration-300 ${msg.sender === 'user'
                    ? 'bg-blue-600 text-white rounded-tr-none shadow-blue-500/20'
                    : msg.sender === 'system'
                      ? 'bg-green-50/80 dark:bg-green-900/20 text-green-800 dark:text-green-300 border border-green-200/50 dark:border-green-700/30'
                      : 'bg-white/80 dark:bg-slate-800/80 text-slate-800 dark:text-slate-100 border border-white/50 dark:border-white/5 rounded-tl-none shadow-lg shadow-black/5'
                    }`}>
                    <div
                      className={`prose prose-sm max-w-none ${msg.sender === 'user' ? 'prose-invert' : 'dark:prose-invert'} prose-p:leading-relaxed prose-pre:bg-slate-900 prose-pre:border prose-pre:border-white/10`}
                      onClick={(e) => {
                        if (e.target.classList.contains('technical-term')) {
                          e.stopPropagation();
                          const rect = e.target.getBoundingClientRect();
                          handleExplainTerm(e.target.dataset.term, rect.left, rect.bottom + 5);
                        }
                      }}
                      dangerouslySetInnerHTML={{ __html: marked.parse(msg.text).replace(/\[\[(.*?)\]\]/g, '<span class="technical-term text-indigo-500 dark:text-indigo-400 font-bold cursor-pointer hover:underline decoration-indigo-400 underline-offset-4 decoration-2" data-term="$1">$1</span>') }}
                    />
                  </div>

                  {/* Sources Display */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2 ml-1">
                      {msg.sources.map((src, i) => {
                        const isWeb = src.url && /^https?:\/\//.test(src.url);
                        return (
                          <a
                            key={i}
                            href={isWeb ? src.url : '#'}
                            target={isWeb ? "_blank" : "_self"}
                            rel="noopener noreferrer"
                            className={`flex items-center gap-1.5 text-[10px] font-medium px-2.5 py-1.5 rounded-lg border transition-all ${isWeb
                              ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-300 border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/40'
                              : 'bg-slate-50 dark:bg-slate-800/50 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800'
                              }`}
                            onClick={(e) => !isWeb && e.preventDefault()}
                          >
                            <span className="opacity-70">{isWeb ? '🔗' : '📄'}</span>
                            <span className="truncate max-w-[150px]">{src.title || src.url}</span>
                          </a>
                        );
                      })}
                    </div>
                  )}
                  <span className="text-[10px] text-slate-400 dark:text-slate-500 mt-1.5 px-2 font-mono opacity-0 group-hover:opacity-100 transition-opacity">{msg.timestamp}</span>
                </div>

                {msg.sender === 'user' && (
                  <div className="w-10 h-10 rounded-xl bg-slate-200 dark:bg-slate-700 flex items-center justify-center text-sm font-bold text-slate-500 dark:text-slate-300 flex-shrink-0 mt-1">
                    You
                  </div>
                )}
              </div>
            ))}
          </>
        )}

        {isLoading && (
          <div className="flex gap-4 max-w-4xl mx-auto animate-slide-up">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0 mt-1 shadow-md">AI</div>
            <div className="px-6 py-4 bg-white/80 dark:bg-slate-800/80 backdrop-blur-md rounded-2xl rounded-tl-none border border-white/50 dark:border-white/5 shadow-md flex items-center gap-3">
              {loadingMessage ? (
                <span className="text-sm font-medium text-slate-600 dark:text-slate-300 animate-pulse">{loadingMessage}</span>
              ) : (
                <>
                  <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </>
              )}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} className="h-4" />
      </div>

      {/* Input Area */}
      <div className="p-4 sm:p-6 bg-gradient-to-t from-slate-100 via-slate-50/90 to-transparent dark:from-slate-950 dark:via-slate-900/90 z-20 relative">
        <div className="max-w-4xl mx-auto">
          {/* Difficulty Selector */}
          <div className="flex justify-center gap-2 mb-4">
            {[
              { id: 'easy', label: '🔰 初学者向け', desc: 'やさしく解説' },
              { id: 'normal', label: '標準', desc: 'バランスよく' },
              { id: 'professional', label: '🎓 専門的', desc: '実務・詳細' }
            ].map((mode) => (
              <button
                key={mode.id}
                onClick={() => setDifficulty(mode.id)}
                className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all border ${difficulty === mode.id
                  ? 'bg-indigo-600 text-white border-indigo-600 shadow-lg shadow-indigo-500/30 transform scale-105'
                  : 'bg-white/50 dark:bg-slate-800/50 border-white/40 dark:border-white/10 text-slate-500 dark:text-slate-400 hover:bg-white dark:hover:bg-slate-700'
                  }`}
              >
                {mode.label}
              </button>
            ))}
          </div>

          <div className="relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-600 rounded-2xl opacity-5 group-focus-within:opacity-40 blur transition duration-500"></div>
            <div className="relative flex items-end gap-2 bg-white/80 dark:bg-slate-900/90 backdrop-blur-xl rounded-2xl p-2 border border-white/20 dark:border-white/10 shadow-2xl">
              <button
                onClick={handleOpenDocSelector}
                className="p-3 text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-xl transition-all"
                title="ドキュメントを選択して質問"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>
              </button>

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
                placeholder="質問を入力... (Enterで送信)"
                className="w-full py-4 bg-transparent border-0 focus:ring-0 text-slate-800 dark:text-slate-100 placeholder-slate-400 resize-none max-h-[200px] min-h-[56px]"
                rows={1}
                disabled={isLoading}
              />

              <button
                onClick={isLoading ? onStop : handleSendClick}
                disabled={!isLoading && !input.trim()}
                className={`p-3 rounded-xl transition-all duration-300 mb-1 ${isLoading
                  ? 'bg-red-500 text-white hover:bg-red-600 shadow-red-500/30'
                  : input.trim()
                    ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg shadow-indigo-600/30 transform hover:-translate-y-0.5'
                    : 'bg-slate-200 dark:bg-slate-800 text-slate-400 cursor-not-allowed'
                  }`}
              >
                {isLoading ? (
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2" /></svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                )}
              </button>
            </div>
            <p className="text-center text-[10px] text-slate-400 mt-2 font-medium">AIは間違いを犯す可能性があります。重要な情報は確認してください。</p>
          </div>
        </div>
      </div>

      {/* Explanation Popup */}
      {explanation && (
        <div
          className="fixed z-50 bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 dark:border-white/10 p-5 w-80 animate-in fade-in zoom-in duration-200"
          style={{ top: explanation.y, left: explanation.x }}
        >
          <div className="flex justify-between items-start mb-3">
            <h4 className="font-bold text-indigo-600 dark:text-indigo-400 text-sm flex items-center gap-2">
              <span className="text-lg">💡</span> {explanation.term}
            </h4>
            <button onClick={() => setExplanation(null)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">✕</button>
          </div>
          <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed font-medium">
            {explanation.text}
          </p>
        </div>
      )}

      {/* Document Selection Modal */}
      {showDocSelector && (
        <div className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in">
          <div className="bg-white/90 dark:bg-slate-900/90 backdrop-blur-2xl rounded-3xl shadow-2xl border border-white/20 dark:border-white/10 max-w-lg w-full overflow-hidden flex flex-col max-h-[80vh] animate-slide-up">
            <div className="p-5 border-b border-white/20 dark:border-white/10 flex justify-between items-center bg-white/40 dark:bg-white/5">
              <h3 className="font-bold text-slate-800 dark:text-slate-100 text-lg">ドキュメントを選択</h3>
              <button
                onClick={() => setShowDocSelector(false)}
                className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-200/50 dark:hover:bg-white/10 text-slate-500 transition-colors"
              >
                ✕
              </button>
            </div>
            <div className="overflow-y-auto p-3 space-y-2">
              {documents.map((doc, i) => (
                <button
                  key={i}
                  onClick={() => handleSelectDoc(doc)}
                  className="w-full text-left p-4 hover:bg-indigo-50/50 dark:hover:bg-indigo-900/20 border border-transparent hover:border-indigo-200 dark:hover:border-indigo-800 rounded-2xl transition-all flex items-center gap-4 group"
                >
                  <div className="w-12 h-12 rounded-xl bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-2xl flex-shrink-0 group-hover:scale-110 transition-transform">
                    📄
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-slate-800 dark:text-slate-200 truncate">{doc.title || doc.source}</div>
                    {doc.summary && <div className="text-xs text-slate-500 dark:text-slate-400 truncate mt-1">{doc.summary}</div>}
                  </div>
                  <div className="text-indigo-600 dark:text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity font-bold text-sm bg-indigo-100 dark:bg-indigo-900/50 px-3 py-1 rounded-full">
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
