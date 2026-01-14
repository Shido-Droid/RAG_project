import { useState, useRef } from 'react';
import * as api from './api/client';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import { useChat } from './hooks/useChat';
import { useDocuments } from './hooks/useDocuments';
import { useTheme } from './hooks/useTheme';

function App() {
  // Custom Hooks
  const { 
    messages, addMessage, clearMessages, 
    isLoading, loadingMessage, isHistoryLoading, 
    handleSend, handleStop 
  } = useChat();

  const {
    documents, setDocuments, isDocsLoading, isUploading,
    editingDoc, setEditingDoc, editTitle, setEditTitle, deletingDoc, useOcr, setUseOcr,
    uploadFile, deleteDocument, updateTitle
  } = useDocuments();

  const { isDarkMode, setIsDarkMode } = useTheme();

  // UI States
  const [isSidebarOpen, setIsSidebarOpen] = useState(true); // モバイル対応用
  const [viewingDoc, setViewingDoc] = useState(null);
  const [modalTab, setModalTab] = useState('summary'); // 'summary' | 'content'
  const [pendingChatInput, setPendingChatInput] = useState('');
  
  const fileInputRef = useRef(null);

  // --- ファイルアップロード ---
  const handleFileUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    try {
      const data = await uploadFile(files[0]);
      // アップロード成功通知（チャット欄に表示）
      addMessage({ 
        sender: 'system', 
        text: `✅ ファイルを読み込みました: ${files[0].name} (${data.message})`,
        timestamp: new Date().toLocaleTimeString()
      });
    } catch (error) {
      addMessage({ 
        sender: 'system', 
        text: `❌ アップロードエラー: ${error.message}`,
        timestamp: new Date().toLocaleTimeString()
      });
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // --- DBリセット ---
  const handleResetDb = async () => {
    if (!confirm("本当にすべての学習データを削除しますか？")) return;
    try {
      await api.resetDb();
      setDocuments([]);
      addMessage({ 
        sender: 'system', 
        text: "🗑️ データベースを初期化しました。",
        timestamp: new Date().toLocaleTimeString()
      });
    } catch (e) {
      alert("リセットに失敗しました");
    }
  };

  // --- ドキュメント削除 ---
  const handleDeleteDocument = async (filename) => {
    if (!confirm(`"${filename}" を削除しますか？`)) return;
    try {
      await deleteDocument(filename);
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
    try {
      await updateTitle();
    } catch (e) {
      alert("更新エラー");
    }
  };

  const handleCancelEdit = () => {
    setEditingDoc(null);
    setEditTitle('');
  };

  const handleClearChat = async () => {
    if (!confirm("チャット履歴を削除しますか？")) return;
    try {
      await api.clearHistory();
      clearMessages();
    } catch (e) {
      alert("削除に失敗しました");
    }
  };

  // --- 文脈リセット (話題を変える) ---
  const handleResetContext = async () => {
    try {
      // サーバー側の履歴を削除して、AIのコンテキストをクリアする
      await api.clearHistory();
      
      // 画面上には区切り線となるメッセージを表示
      addMessage({ 
        sender: 'system', 
        text: "🧹 会話の文脈をリセットしました。新しい話題について質問してください。",
        timestamp: new Date().toLocaleTimeString()
      });
    } catch (e) {
      console.error("Reset context failed", e);
    }
  };

  // 生徒向けのおすすめ質問
  const suggestedQuestions = ["このドキュメントの要約を教えて", "重要なポイントを3つ挙げて", "初心者向けに解説して"];

  const handleSelectDoc = (doc) => {
    setPendingChatInput(`「${doc.title || doc.source}」の内容について、`);
    setViewingDoc(null);
  };

  const handleViewDoc = (doc) => {
    setViewingDoc(doc);
    setModalTab('summary');
  };

  return (
    <div className="fixed inset-0 flex h-[100dvh] w-full bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 font-sans overflow-hidden transition-colors duration-200">
      
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        fileInputRef={fileInputRef}
        onFileUpload={handleFileUpload}
        isUploading={isUploading}
        useOcr={useOcr}
        setUseOcr={setUseOcr}
        documents={documents}
        isDocsLoading={isDocsLoading}
        isLoading={isDocsLoading}
        editingDoc={editingDoc}
        editTitle={editTitle}
        setEditTitle={setEditTitle}
        onSaveTitle={handleSaveTitle}
        onCancelEdit={handleCancelEdit}
        deletingDoc={deletingDoc}
        onViewDoc={handleViewDoc}
        onStartEdit={handleStartEdit}
        onDeleteDoc={handleDeleteDocument}
        onResetDb={handleResetDb}
      />

      {/* --- Main Chat Area --- */}
      <ChatArea
        messages={messages}
        isLoading={isLoading}
        loadingMessage={loadingMessage}
        isHistoryLoading={isHistoryLoading}
        suggestedQuestions={suggestedQuestions}
        documents={documents}
        isSidebarOpen={isSidebarOpen}
        setIsSidebarOpen={setIsSidebarOpen}
        isDarkMode={isDarkMode}
        setIsDarkMode={setIsDarkMode}
        onSend={handleSend}
        onStop={handleStop}
        onResetContext={handleResetContext}
        onClearHistory={handleClearChat}
        pendingChatInput={pendingChatInput}
        onChatInputSet={() => setPendingChatInput('')}
      />

      {/* Document Details Modal */}
      {viewingDoc && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col max-h-[80vh] animate-in fade-in zoom-in duration-200">
            <div className="p-4 border-b border-slate-100 dark:border-slate-700 flex justify-between items-center bg-slate-50/50 dark:bg-slate-700/50">
              <h3 className="font-bold text-slate-700 dark:text-slate-200 flex items-center gap-2">
                <span className="text-xl">📄</span> {viewingDoc.title || viewingDoc.source}
              </h3>
              <button 
                onClick={() => setViewingDoc(null)} 
                className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-200 text-slate-400 transition-colors"
              >
                ✕
              </button>
            </div>
            <div className="p-6 overflow-y-auto space-y-4">
              <div>
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">ファイル名</h4>
                <p className="text-sm text-slate-700 dark:text-slate-300 font-mono bg-slate-50 dark:bg-slate-700 px-2 py-1 rounded border border-slate-100 dark:border-slate-600 inline-block">{viewingDoc.source}</p>
              </div>
              
              <div className="flex flex-col h-full min-h-[200px]">
                <div className="flex border-b border-slate-200 dark:border-slate-700 mb-2">
                  <button 
                    onClick={() => setModalTab('summary')}
                    className={`px-4 py-2 text-sm font-bold transition-colors border-b-2 ${modalTab === 'summary' ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}
                  >
                    要約
                  </button>
                  <button 
                    onClick={() => setModalTab('content')}
                    className={`px-4 py-2 text-sm font-bold transition-colors border-b-2 ${modalTab === 'content' ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}
                  >
                    本文 (OCR結果)
                  </button>
                </div>
                <div className="bg-slate-50 dark:bg-slate-700 p-4 rounded-lg border border-slate-100 dark:border-slate-600 flex-1 overflow-y-auto max-h-[300px]">
                  <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap font-mono">
                    {modalTab === 'summary' ? (viewingDoc.summary || "要約はありません") : (viewingDoc.content || "本文データがありません")}
                  </p>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-100 dark:border-slate-700">
                <button
                  onClick={() => {
                    handleSelectDoc(viewingDoc);
                    setViewingDoc(null);
                  }}
                  className="w-full bg-indigo-600 text-white py-3 rounded-xl hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2 font-bold shadow-md hover:shadow-lg transform active:scale-[0.98] transition-all"
                >
                  💬 このドキュメントについて質問する
                </button>
                <p className="text-center text-xs text-slate-400 mt-2">OCRの結果をテストするには、ここからチャットを開始してください。</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
