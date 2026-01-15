import { useState, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import { useChat } from './hooks/useChat';
import { useDocuments } from './hooks/useDocuments';
import { useTheme } from './hooks/useTheme';
import { ToastProvider, useToast } from './components/ui/ToastContext';

function App() {
  return (
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  );
}

function AppContent() {
  const {
    messages, addMessage, clearMessages,
    isLoading, loadingMessage, isHistoryLoading,
    handleSend, handleStop, resetSession
  } = useChat();

  const {
    documents, setDocuments, isDocsLoading, isUploading,
    editingDoc, setEditingDoc, editTitle, setEditTitle, deletingDoc, useOcr, setUseOcr,
    uploadFile, deleteDocument, updateTitle, resetDb
  } = useDocuments();

  const { isDarkMode, setIsDarkMode } = useTheme();

  // Toast Hooks
  const { addToast, confirm: confirmDialog } = useToast();

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
      addToast(`ファイルを読み込みました: ${files[0].name}`, 'success');
    } catch (error) {
      addMessage({
        sender: 'system',
        text: `❌ アップロードエラー: ${error.message}`,
        timestamp: new Date().toLocaleTimeString()
      });
      addToast(`アップロードエラー: ${error.message}`, 'error');
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // --- DBリセット ---
  const handleResetDb = async () => {
    const isConfirmed = await confirmDialog("本当にすべての学習データを削除しますか？\nこの操作は取り消せません。");
    if (!isConfirmed) return;

    try {
      await resetDb();
      addMessage({
        sender: 'system',
        text: "🗑️ データベースを初期化しました。",
        timestamp: new Date().toLocaleTimeString()
      });
      addToast("データベースを初期化しました", 'success');
    } catch (e) {
      addToast("リセットに失敗しました", 'error');
    }
  };

  // --- ドキュメント削除 ---
  const handleDeleteDocument = async (filename) => {
    const isConfirmed = await confirmDialog(`"${filename}" を削除しますか？`);
    if (!isConfirmed) return;

    try {
      await deleteDocument(filename);
      addToast(`"${filename}" を削除しました`, 'success');
    } catch (e) {
      console.error("Delete failed", e);
      addToast("削除エラーが発生しました", 'error');
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
      addToast("タイトルを更新しました", 'success');
    } catch (e) {
      addToast("更新エラーが発生しました", 'error');
    }
  };

  const handleCancelEdit = () => {
    setEditingDoc(null);
    setEditTitle('');
  };

  const handleClearChat = async () => {
    const isConfirmed = await confirmDialog("チャット履歴を削除しますか？");
    if (!isConfirmed) return;
    try {
      clearMessages();
      addToast("チャット履歴を削除しました", 'info');
    } catch (e) {
      addToast("削除に失敗しました", 'error');
    }
  };

  // --- 文脈リセット (話題を変える) ---
  const handleResetContext = async () => {
    try {
      // サーバー側の履歴を削除して、AIのコンテキストをクリアする
      await resetSession();

      // 画面上には区切り線となるメッセージを表示
      addMessage({
        sender: 'system',
        text: "🧹 会話の文脈をリセットしました。新しい話題について質問してください。",
        timestamp: new Date().toLocaleTimeString()
      });
      addToast("会話の文脈をリセットしました", 'info');
    } catch (e) {
      console.error("Reset context failed", e);
      addToast("リセットに失敗しました", 'error');
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
    <div className="fixed inset-0 flex h-[100dvh] w-full bg-gradient-to-br from-indigo-50 via-slate-50 to-blue-100 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800 text-slate-800 dark:text-slate-100 font-sans overflow-hidden transition-colors duration-200">

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
          <div className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 dark:border-white/10 max-w-2xl w-full overflow-hidden flex flex-col max-h-[80vh] animate-in fade-in zoom-in duration-200">
            <div className="p-4 border-b border-slate-200/30 dark:border-slate-700/30 flex justify-between items-center bg-white/30 dark:bg-white/5">
              <h3 className="font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
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
                <p className="text-sm text-slate-700 dark:text-slate-300 font-mono bg-white/50 dark:bg-black/20 px-2 py-1 rounded border border-slate-200/50 dark:border-slate-700 inline-block">{viewingDoc.source}</p>
              </div>

              <div className="flex flex-col h-full min-h-[200px]">
                <div className="flex border-b border-slate-200/50 dark:border-slate-700/50 mb-2">
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
                <div className="bg-white/40 dark:bg-black/20 p-4 rounded-lg border border-white/20 dark:border-white/5 flex-1 overflow-y-auto max-h-[300px]">
                  <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap font-mono">
                    {modalTab === 'summary' ? (viewingDoc.summary || "要約はありません") : (viewingDoc.content || "本文データがありません")}
                  </p>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-200/30 dark:border-slate-700/30">
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
