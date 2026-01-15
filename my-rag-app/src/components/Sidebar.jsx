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
    <div className={`${isOpen ? 'w-80' : 'w-0'} bg-white/50 dark:bg-slate-900/60 backdrop-blur-3xl border-r border-white/20 dark:border-white/5 flex flex-col transition-all duration-300 ease-in-out overflow-hidden flex-shrink-0 relative shadow-2xl z-30`}>
      <div className="p-6 border-b border-white/20 dark:border-white/5 flex justify-between items-center bg-white/20 dark:bg-white/5">
        <h2 className="font-bold text-lg text-slate-800 dark:text-slate-100 flex items-center gap-2">
          <span className="text-xl">🗂️</span> ライブラリ
        </h2>
        <button onClick={onClose} className="p-2 rounded-full hover:bg-slate-200/50 dark:hover:bg-slate-800/50 text-slate-500 transition-colors" aria-label="サイドバーを閉じる">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Upload Area */}
        <div
          onClick={() => !isUploading && fileInputRef.current.click()}
          className={`group relative overflow-hidden border-2 border-dashed border-indigo-300/50 dark:border-indigo-500/30 bg-indigo-50/50 dark:bg-indigo-950/20 rounded-2xl p-6 text-center cursor-pointer hover:border-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/10 transition-all duration-300 ${isUploading ? 'opacity-70 pointer-events-none' : ''}`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={onFileUpload}
            className="hidden"
            accept=".pdf,.docx,.pptx,.txt,.md,.png,.jpg,.jpeg"
          />
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
          <div className="text-4xl mb-3 group-hover:scale-110 transition-transform duration-300 transform">📄</div>
          <p className="text-sm font-bold text-slate-700 dark:text-slate-200">ファイルをアップロード</p>
          <p className="text-[10px] text-slate-400 mt-1 uppercase tracking-wide">PDF, Word, Text, Image</p>
          {isUploading && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm">
              <div className="flex flex-col items-center">
                <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-2"></div>
                <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400">Processing...</span>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 px-2 py-2 bg-white/20 dark:bg-white/5 rounded-lg border border-white/10">
          <div className="relative flex items-center">
            <input
              type="checkbox"
              id="use-ocr"
              checked={useOcr}
              onChange={(e) => setUseOcr(e.target.checked)}
              className="peer h-4 w-4 cursor-pointer appearance-none rounded border border-slate-300 bg-white checked:bg-indigo-600 transition-all"
            />
            <span className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-white opacity-0 peer-checked:opacity-100">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
            </span>
          </div>
          <label htmlFor="use-ocr" className="text-xs font-medium text-slate-600 dark:text-slate-400 cursor-pointer select-none flex-1">
            OCR処理 (画像/スキャンPDF)
            <span className="block text-[10px] text-slate-400 dark:text-slate-500 font-normal">有効にすると処理に時間がかかります</span>
          </label>
        </div>

        {/* Document List */}
        <div className="space-y-3 mt-6">
          <div className="flex items-center justify-between px-2">
            <h3 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">登録済み</h3>
            <span className="text-[10px] bg-slate-200 dark:bg-slate-800 text-slate-500 px-2 py-0.5 rounded-full font-mono">{documents.length}</span>
          </div>

          {(isDocsLoading || isLoading) ? (
            <div className="flex flex-col items-center justify-center py-8 space-y-3 text-slate-400">
              <div className="w-6 h-6 border-2 border-indigo-200 border-t-indigo-500 rounded-full animate-spin"></div>
              <span className="text-xs animate-pulse">Syncing library...</span>
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-8 px-4 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
              <p className="text-sm text-slate-400 italic">ドキュメントはありません</p>
            </div>
          ) : (
            <div className="space-y-2">
              {documents.map((doc, i) => (
                <div
                  key={i}
                  className="group relative flex items-center gap-3 p-3 bg-white/40 dark:bg-slate-800/40 hover:bg-white/80 dark:hover:bg-slate-800/80 backdrop-blur-sm rounded-xl border border-white/20 dark:border-white/5 transition-all duration-200 hover:shadow-md hover:scale-[1.02]"
                >
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-100 to-blue-50 dark:from-indigo-900/50 dark:to-blue-900/30 flex items-center justify-center text-lg shadow-inner flex-shrink-0">
                    📑
                  </div>

                  {editingDoc === doc.source ? (
                    <div className="flex-1 flex items-center gap-1 min-w-0">
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="w-full px-2 py-1 bg-white dark:bg-slate-900 border border-indigo-300 dark:border-indigo-700 rounded text-xs outline-none focus:ring-2 focus:ring-indigo-500/50"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') onSaveTitle();
                          if (e.key === 'Escape') onCancelEdit();
                        }}
                      />
                      <button onClick={onSaveTitle} className="p-1 text-green-500 hover:bg-green-50 dark:hover:bg-green-900/30 rounded">✓</button>
                      <button onClick={onCancelEdit} className="p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded">✕</button>
                    </div>
                  ) : (
                    <>
                      <div className="flex-1 min-w-0">
                        <div className="truncate font-semibold text-sm text-slate-700 dark:text-slate-200" title={doc.title || doc.source}>
                          {doc.title || doc.source}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          {doc.size && <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-900 px-1.5 rounded">{formatBytes(doc.size)}</span>}
                          {doc.keywords && <span className="text-[10px] text-slate-500 dark:text-slate-400 truncate max-w-[80px] opacity-70" title={doc.keywords}>{doc.keywords}</span>}
                        </div>
                      </div>

                      {deletingDoc === doc.source ? (
                        <div className="w-4 h-4 border-2 border-red-200 border-t-red-500 rounded-full animate-spin"></div>
                      ) : (
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity absolute right-2 bg-white/90 dark:bg-slate-800/90 p-1 rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm backdrop-blur">
                          <button onClick={() => onViewDoc(doc)} className="p-1.5 rounded-md hover:bg-indigo-50 dark:hover:bg-indigo-900/30 text-indigo-500 transition-colors" title="詳細を確認">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" /></svg>
                          </button>
                          <button onClick={() => onStartEdit(doc)} className="p-1.5 rounded-md hover:bg-blue-50 dark:hover:bg-blue-900/30 text-blue-500 transition-colors" title="タイトル編集">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" /></svg>
                          </button>
                          <button onClick={() => onDeleteDoc(doc.source)} className="p-1.5 rounded-md hover:bg-red-50 dark:hover:bg-red-900/30 text-red-500 transition-colors" title="削除">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18" /><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" /><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" /></svg>
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="p-4 border-t border-white/20 dark:border-white/5 bg-white/10 dark:bg-white/5 backdrop-blur-md">
        <button
          onClick={onResetDb}
          className="w-full py-2.5 px-4 text-xs font-bold text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 border border-red-200 dark:border-red-900/30 rounded-xl transition-all duration-200 flex items-center justify-center gap-2 group"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="group-hover:rotate-12 transition-transform"><path d="M3 6h18" /><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" /><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" /></svg>
          全データを削除
        </button>
      </div>
    </div>
  );
}
