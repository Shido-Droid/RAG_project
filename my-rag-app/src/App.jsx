import { useState, useRef, useEffect } from 'react';
import { marked } from 'marked';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true); // モバイル対応用
  const [showDocSelector, setShowDocSelector] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState('');
  const [editingDoc, setEditingDoc] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [difficulty, setDifficulty] = useState('normal');
  const [explanation, setExplanation] = useState(null); // { term, text, x, y }
  
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);
  const fileInputRef = useRef(null);

  // --- 初期化 & ドキュメント一覧取得 ---
  useEffect(() => {
    fetchHistory();
    fetchDocuments();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    document.querySelectorAll('pre code').forEach((block) => {
      hljs.highlightElement(block);
    });
  }, [messages]);

  const fetchDocuments = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/documents');
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents);
      }
    } catch (e) {
      console.error("Failed to fetch documents", e);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/history');
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (e) {
      console.error("Failed to fetch history", e);
    }
  };

  // --- ファイルアップロード ---
  const handleFileUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', files[0]);

    try {
      const res = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Upload failed');
      }
      
      const data = await res.json();
      // アップロード成功通知（チャット欄に表示）
      setMessages(prev => [...prev, { 
        sender: 'system', 
        text: `✅ ファイルを読み込みました: ${files[0].name} (${data.message})`,
        timestamp: new Date().toLocaleTimeString()
      }]);
      
      await fetchDocuments(); // リスト更新
    } catch (error) {
      setMessages(prev => [...prev, { 
        sender: 'system', 
        text: `❌ アップロードエラー: ${error.message}`,
        timestamp: new Date().toLocaleTimeString()
      }]);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // --- DBリセット ---
  const handleResetDb = async () => {
    if (!confirm("本当にすべての学習データを削除しますか？")) return;
    try {
      await fetch('http://localhost:8000/api/reset', { method: 'POST' });
      setDocuments([]);
      setMessages(prev => [...prev, { 
        sender: 'system', 
        text: "🗑️ データベースを初期化しました。",
        timestamp: new Date().toLocaleTimeString()
      }]);
    } catch (e) {
      alert("リセットに失敗しました");
    }
  };

  // --- チャット送信 ---
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMessage = { sender: 'user', text: input, timestamp };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('http://localhost:8000/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: input, difficulty: difficulty }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      setMessages(prev => [...prev, { sender: 'bot', text: '', sources: [], timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

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
              }
              return newMessages;
            });
          } catch (e) { console.error(e); }
        }
      }

    } catch (error) {
      if (error.name !== 'AbortError') {
        setMessages(prev => [...prev, { sender: 'bot', text: `エラーが発生しました: ${error.message}` }]);
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  // --- ドキュメント削除 ---
  const handleDeleteDocument = async (filename) => {
    if (!confirm(`"${filename}" を削除しますか？`)) return;
    try {
      const res = await fetch('http://localhost:8000/api/delete_document', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename }),
      });
      if (res.ok) {
        await fetchDocuments();
      } else {
        alert("削除に失敗しました");
      }
    } catch (e) {
      console.error("Delete failed", e);
      alert("削除エラー");
    }
  };

  // --- タイトル編集 ---
  const handleStartEdit = (doc) => {
    setEditingDoc(doc.source);
    setEditTitle(doc.title || doc.source);
  };

  const handleSaveTitle = async () => {
    if (!editTitle.trim()) return;
    try {
      const res = await fetch('http://localhost:8000/api/update_title', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: editingDoc, new_title: editTitle }),
      });
      if (res.ok) {
        await fetchDocuments();
        setEditingDoc(null);
      } else {
        alert("タイトルの更新に失敗しました");
      }
    } catch (e) {
      console.error("Update title failed", e);
      alert("更新エラー");
    }
  };

  const handleCancelEdit = () => {
    setEditingDoc(null);
    setEditTitle('');
  };

  const handleStop = () => abortControllerRef.current?.abort();
  
  const handleClearChat = async () => {
    if (!confirm("チャット履歴を削除しますか？")) return;
    try {
      await fetch('http://localhost:8000/api/history', { method: 'DELETE' });
      setMessages([]);
    } catch (e) {
      alert("削除に失敗しました");
    }
  };

  const handleSuggestedClick = (q) => {
    if (documents.length === 0) {
      setInput(q);
      return;
    }
    setPendingQuestion(q);
    setShowDocSelector(true);
  };

  const handleSelectDoc = (doc) => {
    const title = doc.title || doc.source;
    setInput(`「${title}」の内容について、${pendingQuestion}`);
    setShowDocSelector(false);
    setPendingQuestion('');
  };

  const handleSelectAllDocs = () => {
    setInput(`すべてのドキュメントの内容について、${pendingQuestion}`);
    setShowDocSelector(false);
    setPendingQuestion('');
  };

  const handleOpenDocSelector = () => {
    if (documents.length === 0) {
      alert("ドキュメントが登録されていません。左のサイドバーからアップロードしてください。");
      return;
    }
    setPendingQuestion(input);
    setShowDocSelector(true);
  };

  // --- 用語解説 ---
  const handleExplainTerm = async (term, x, y) => {
    // ポップアップ位置の調整 (画面端にはみ出さないように)
    const popupX = Math.min(x, window.innerWidth - 320); 
    
    setExplanation({ term, text: '解説を生成中...', x: popupX, y });
    try {
      const res = await fetch('http://localhost:8000/api/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ term }),
      });
      if (res.ok) {
        const data = await res.json();
        setExplanation({ term, text: data.explanation, x: popupX, y });
      } else {
        setExplanation({ term, text: '解説の取得に失敗しました', x: popupX, y });
      }
    } catch (e) {
      setExplanation({ term, text: 'エラーが発生しました', x: popupX, y });
    }
  };

  // 生徒向けのおすすめ質問
  const suggestedQuestions = ["このドキュメントの要約を教えて", "重要なポイントを3つ挙げて", "初心者向けに解説して"];

  return (
    <div className="flex h-screen bg-slate-50 text-slate-800 font-sans overflow-hidden">
      
      {/* --- Sidebar (Sources) --- */}
      <div className={`${isSidebarOpen ? 'w-80' : 'w-0'} bg-white border-r border-slate-200 flex flex-col transition-all duration-300 ease-in-out overflow-hidden flex-shrink-0 relative`}>
        <div className="p-5 border-b border-slate-100 flex justify-between items-center">
          <h2 className="font-bold text-lg text-slate-700">📚 ソース</h2>
          <button onClick={() => setIsSidebarOpen(false)} className="md:hidden text-slate-400 hover:text-slate-600">✕</button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {/* Upload Area */}
          <div 
            onClick={() => fileInputRef.current.click()}
            className={`border-2 border-dashed border-slate-200 rounded-xl p-6 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors ${isUploading ? 'opacity-50 pointer-events-none' : ''}`}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileUpload} 
              className="hidden" 
              accept=".pdf,.docx,.pptx,.txt,.md"
            />
            <div className="text-3xl mb-2">📄</div>
            <p className="text-sm font-medium text-slate-600">ソースを追加</p>
            <p className="text-xs text-slate-400 mt-1">PDF, Word, PPT, Text</p>
            {isUploading && <p className="text-xs text-blue-500 mt-2 animate-pulse">読み込み中...</p>}
          </div>

          {/* Document List */}
          <div className="space-y-2 mt-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">登録済み ({documents.length})</h3>
            {documents.length === 0 ? (
              <p className="text-sm text-slate-400 italic">ドキュメントはありません</p>
            ) : (
              documents.map((doc, i) => (
                <div key={i} className="flex items-center gap-2 p-2 bg-slate-50 rounded-lg border border-slate-100 text-sm group">
                  <span className="text-lg">📑</span>
                  
                  {editingDoc === doc.source ? (
                    <div className="flex-1 flex items-center gap-1 min-w-0">
                      <input 
                        type="text" 
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="flex-1 px-2 py-1 border border-blue-300 rounded text-xs outline-none"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveTitle();
                          if (e.key === 'Escape') handleCancelEdit();
                        }}
                      />
                      <button onClick={handleSaveTitle} className="text-green-500 hover:text-green-600 px-1">✓</button>
                      <button onClick={handleCancelEdit} className="text-slate-400 hover:text-slate-600 px-1">✕</button>
                    </div>
                  ) : (
                    <>
                      <div className="flex-1 min-w-0">
                        <div className="truncate font-medium" title={doc.summary || "要約なし"}>{doc.title || doc.source}</div>
                        {doc.keywords && <div className="truncate text-xs text-slate-400" title={doc.keywords}>{doc.keywords}</div>}
                      </div>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button onClick={() => handleStartEdit(doc)} className="text-slate-400 hover:text-blue-500" title="タイトル編集">
                          ✎
                        </button>
                        <button onClick={() => handleDeleteDocument(doc.source)} className="text-slate-400 hover:text-red-500" title="削除">
                          ✕
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        <div className="p-4 border-t border-slate-100">
          <button 
            onClick={handleResetDb}
            className="w-full py-2 px-4 text-xs font-bold text-red-500 hover:bg-red-50 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            🗑️ 全データを削除
          </button>
        </div>
      </div>

      {/* --- Main Chat Area --- */}
      <div className="flex-1 flex flex-col h-full relative">
        {/* Header */}
        <header className="bg-white/80 backdrop-blur-md border-b border-slate-200 p-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            {!isSidebarOpen && (
              <button onClick={() => setIsSidebarOpen(true)} className="p-2 hover:bg-slate-100 rounded-lg text-slate-500">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
              </button>
            )}
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold shadow-sm">
              AI
            </div>
            <h1 className="font-bold text-slate-700">Notebook Assistant</h1>
          </div>
          <button onClick={handleClearChat} className="text-xs text-slate-400 hover:text-red-500 px-3 py-1 rounded-full hover:bg-slate-100 transition-colors">
            チャットをクリア
          </button>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-8 space-y-6 bg-white">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-slate-300 space-y-4">
              <div className="text-6xl">✨</div>
              <p className="text-xl font-medium">何でも聞いてください</p>
              <div className="flex flex-wrap gap-2 justify-center mt-4">
                {suggestedQuestions.map((q, i) => (
                  <button key={i} onClick={() => handleSuggestedClick(q)} className="text-sm bg-white border border-slate-200 px-4 py-2 rounded-full hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-all shadow-sm">
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
                <div className={`px-5 py-3 rounded-2xl shadow-sm prose prose-sm max-w-none ${
                  msg.sender === 'user' 
                    ? 'bg-slate-800 text-white rounded-tr-none' 
                    : msg.sender === 'system'
                    ? 'bg-green-50 text-green-800 border border-green-100'
                    : 'bg-slate-50 text-slate-800 border border-slate-100 rounded-tl-none'
                }`}>
                  <div 
                    onClick={(e) => {
                      if (e.target.classList.contains('technical-term')) {
                        e.stopPropagation();
                        const rect = e.target.getBoundingClientRect();
                        handleExplainTerm(e.target.dataset.term, rect.left, rect.bottom + 5);
                      }
                    }}
                    dangerouslySetInnerHTML={{ __html: marked.parse(msg.text).replace(/\[\[(.*?)\]\]/g, '<span class="technical-term text-indigo-600 font-bold cursor-pointer hover:underline decoration-indigo-400 underline-offset-2" data-term="$1">$1</span>') }} 
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
                             className="flex items-center gap-1 text-xs bg-white border border-slate-200 px-2 py-1 rounded-full text-blue-600 hover:bg-blue-50 hover:border-blue-200 transition-colors shadow-sm">
                            <span className="opacity-50">🔗</span> 
                            <span className="truncate max-w-[150px]">{src.title || src.url}</span>
                          </a>
                        );
                      } else {
                        return (
                          <span key={i} className="flex items-center gap-1 text-xs bg-slate-50 border border-slate-200 px-2 py-1 rounded-full text-slate-600 cursor-default shadow-sm">
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
          
          {isLoading && (
            <div className="flex gap-4 max-w-3xl mx-auto">
               <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0 mt-1">AI</div>
               <div className="bg-slate-50 px-5 py-4 rounded-2xl rounded-tl-none border border-slate-100 flex items-center gap-2">
                  <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
               </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-white border-t border-slate-100">
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
                    ? 'bg-indigo-50 border-indigo-200 text-indigo-700 shadow-sm' 
                    : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'
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
              className="p-3 mb-1 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-colors"
              title="ドキュメントを選択して質問"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
            </button>
            <div className="relative flex-grow">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="質問を入力..."
              className="w-full p-4 pr-12 bg-slate-50 border border-slate-200 rounded-2xl focus:bg-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all outline-none resize-none min-h-[60px] max-h-[200px] shadow-sm"
              rows={1}
              disabled={isLoading}
            />
            <button 
              onClick={isLoading ? handleStop : handleSend}
              disabled={!isLoading && !input.trim()}
              className={`absolute right-3 top-3 p-2 rounded-xl transition-all duration-200 ${
                isLoading 
                  ? 'bg-red-50 text-red-500 hover:bg-red-100' 
                  : input.trim() 
                    ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-md hover:shadow-lg' 
                    : 'bg-slate-200 text-slate-400 cursor-not-allowed'
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
      </div>

      {/* Explanation Popup */}
      {explanation && (
        <div 
          className="fixed z-50 bg-white rounded-xl shadow-xl border border-slate-200 p-4 w-80 animate-in fade-in zoom-in duration-200"
          style={{ top: explanation.y, left: explanation.x }}
        >
          <div className="flex justify-between items-start mb-2">
            <h4 className="font-bold text-indigo-600 text-sm">{explanation.term}</h4>
            <button onClick={() => setExplanation(null)} className="text-slate-400 hover:text-slate-600 text-xs">✕</button>
          </div>
          <p className="text-sm text-slate-700 leading-relaxed">
            {explanation.text}
          </p>
        </div>
      )}

      {/* Document Selection Modal */}
      {showDocSelector && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden flex flex-col max-h-[80vh] animate-in fade-in zoom-in duration-200">
            <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h3 className="font-bold text-slate-700">対象のドキュメントを選択</h3>
              <button 
                onClick={() => setShowDocSelector(false)} 
                className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-200 text-slate-400 transition-colors"
              >
                ✕
              </button>
            </div>
            <div className="overflow-y-auto p-2 space-y-1">
              <button
                onClick={handleSelectAllDocs}
                className="w-full text-left p-3 hover:bg-blue-50 hover:border-blue-100 border border-transparent rounded-xl transition-all flex items-center gap-3 group"
              >
                <div className="w-10 h-10 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center text-xl flex-shrink-0">
                  📚
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-bold text-slate-700 truncate text-sm">すべてのドキュメント</div>
                  <div className="text-xs text-slate-400 truncate mt-0.5">登録済みの全資料から回答</div>
                </div>
                <div className="text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity text-sm font-bold">
                  選択
                </div>
              </button>
              {documents.map((doc, i) => (
                <button
                  key={i}
                  onClick={() => handleSelectDoc(doc)}
                  className="w-full text-left p-3 hover:bg-blue-50 hover:border-blue-100 border border-transparent rounded-xl transition-all flex items-center gap-3 group"
                >
                  <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center text-xl flex-shrink-0">
                    📄
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-slate-700 truncate text-sm">{doc.title || doc.source}</div>
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

export default App;
