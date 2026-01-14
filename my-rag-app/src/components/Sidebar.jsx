import React from 'react';

const formatBytes = (bytes, decimals = 1) => {
  if (bytes === 0) return '0 B';
  if (!bytes) return '';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
};

export default function Sidebar({
  isOpen,
  onClose,
  fileInputRef,
  onFileUpload,
  isUploading,
  useOcr,
  setUseOcr,
  documents,
  isDocsLoading,
  isLoading,
  editingDoc,
  editTitle,
  setEditTitle,
  onSaveTitle,
  onCancelEdit,
  deletingDoc,
  onViewDoc,
  onStartEdit,
  onDeleteDoc,
  onResetDb
}) {
  return (
    <div className={`${isOpen ? 'w-80' : 'w-0'} bg-white/30 dark:bg-slate-900/50 backdrop-blur-2xl border-r border-white/20 dark:border-white/10 flex flex-col transition-all duration-300 ease-in-out overflow-hidden flex-shrink-0 relative shadow-2xl z-20`}>
      <div className="p-5 border-b border-white/20 dark:border-white/10 flex justify-between items-center">
        <h2 className="font-bold text-lg text-slate-700 dark:text-slate-200">📚 ソース</h2>
        <button onClick={onClose} className="md:hidden text-slate-400 hover:text-slate-600">✕</button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {/* Upload Area */}
        <div 
          onClick={() => fileInputRef.current.click()}
          className={`border-2 border-dashed border-slate-400/30 dark:border-slate-600/50 bg-white/20 dark:bg-white/5 rounded-xl p-6 text-center cursor-pointer hover:border-blue-400/70 hover:bg-blue-50/30 dark:hover:bg-blue-900/20 transition-all ${isUploading ? 'opacity-50 pointer-events-none' : ''}`}
        >
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={onFileUpload} 
            className="hidden" 
            accept=".pdf,.docx,.pptx,.txt,.md,.png,.jpg,.jpeg"
          />
          <div className="text-3xl mb-2">📄</div>
          <p className="text-sm font-medium text-slate-600 dark:text-slate-300">ソースを追加</p>
          <p className="text-xs text-slate-400 mt-1">PDF, Word, PPT, Text, Image</p>
          {isUploading && <p className="text-xs text-blue-500 mt-2 animate-pulse">読み込み中...</p>}
        </div>

        <div className="flex items-center gap-2 px-1">
          <input 
            type="checkbox" 
            id="use-ocr"
            checked={useOcr}
            onChange={(e) => setUseOcr(e.target.checked)}
            className="w-3.5 h-3.5 text-blue-600 rounded border-slate-300 focus:ring-blue-500 cursor-pointer"
          />
          <label htmlFor="use-ocr" className="text-xs text-slate-500 cursor-pointer select-none">OCR処理を有効にする (低速)</label>
        </div>

        {/* Document List */}
        <div className="space-y-2 mt-4">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">登録済み ({documents.length})</h3>
          {(isDocsLoading || isLoading) ? (
            <div className="flex items-center gap-2 text-sm text-slate-400 p-2">
              <div className="w-4 h-4 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin"></div>
              <span>接続中...</span>
            </div>
          ) : documents.length === 0 ? (
            <p className="text-sm text-slate-400 italic">ドキュメントはありません</p>
          ) : (
            documents.map((doc, i) => (
              <div key={i} className="flex items-center gap-2 p-2 bg-white/20 dark:bg-white/5 hover:bg-white/40 dark:hover:bg-white/10 backdrop-blur-sm rounded-lg border border-white/20 dark:border-white/10 text-sm group transition-all shadow-sm">
                <span className="text-lg">📑</span>
                
                {editingDoc === doc.source ? (
                  <div className="flex-1 flex items-center gap-1 min-w-0">
                    <input 
                      type="text" 
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="flex-1 px-2 py-1 border border-blue-300 rounded text-xs outline-none dark:bg-slate-600 dark:text-white"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') onSaveTitle();
                        if (e.key === 'Escape') onCancelEdit();
                      }}
                    />
                    <button onClick={onSaveTitle} className="text-green-500 hover:text-green-600 px-1">✓</button>
                    <button onClick={onCancelEdit} className="text-slate-400 hover:text-slate-600 px-1">✕</button>
                  </div>
                ) : (
                  <>
                    <div className="flex-1 min-w-0">
                      <div className="truncate font-medium dark:text-slate-200" title={doc.summary || "要約なし"}>{doc.title || doc.source}</div>
                      {(doc.size || doc.keywords) && (
                        <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                          {doc.size && <span className="flex-shrink-0 font-mono text-[10px] bg-white/50 dark:bg-black/30 px-1.5 py-0.5 rounded opacity-80">{formatBytes(doc.size)}</span>}
                          {doc.keywords && <span className="truncate" title={doc.keywords}>{doc.keywords}</span>}
                        </div>
                      )}
                    </div>
                    {deletingDoc === doc.source ? (
                      <div className="w-4 h-4 border-2 border-slate-300 border-t-red-500 rounded-full animate-spin"></div>
                    ) : (
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button onClick={() => onViewDoc(doc)} className="text-slate-400 hover:text-indigo-500" title="詳細を確認">
                          👁️
                        </button>
                        <button onClick={() => onStartEdit(doc)} className="text-slate-400 hover:text-blue-500" title="タイトル編集">
                          ✎
                        </button>
                        <button onClick={() => onDeleteDoc(doc.source)} className="text-slate-400 hover:text-red-500" title="削除">
                          ✕
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      <div className="p-4 border-t border-white/20 dark:border-white/10">
        <button 
          onClick={onResetDb}
          className="w-full py-2 px-4 text-xs font-bold text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          🗑️ 全データを削除
        </button>
      </div>
    </div>
  );
}
