import React, { createContext, useContext, useState, useCallback } from 'react';

const ToastContext = createContext();

export const useToast = () => useContext(ToastContext);

export const ToastProvider = ({ children }) => {
    const [toasts, setToasts] = useState([]);

    const addToast = useCallback((message, type = 'info') => {
        const id = Date.now();
        setToasts((prev) => [...prev, { id, message, type }]);
        setTimeout(() => {
            removeToast(id);
        }, 3000);
    }, []);

    const removeToast = useCallback((id) => {
        setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, []);

    // confirmDialog state
    const [confirmState, setConfirmState] = useState({
        isOpen: false,
        message: '',
        onConfirm: null,
        onCancel: null
    });

    const confirm = (message) => {
        return new Promise((resolve) => {
            setConfirmState({
                isOpen: true,
                message,
                onConfirm: () => {
                    resolve(true);
                    closeConfirm();
                },
                onCancel: () => {
                    resolve(false);
                    closeConfirm();
                }
            });
        });
    };

    const closeConfirm = () => {
        setConfirmState((prev) => ({ ...prev, isOpen: false }));
    };

    return (
        <ToastContext.Provider value={{ addToast, confirm }}>
            {children}

            {/* Toast Container */}
            <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
                {toasts.map((toast) => (
                    <div
                        key={toast.id}
                        className={`
              pointer-events-auto min-w-[300px] max-w-sm w-full bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700 p-4 flex items-center gap-3 animate-slide-up
              ${toast.type === 'error' ? 'border-l-4 border-l-red-500' :
                                toast.type === 'success' ? 'border-l-4 border-l-green-500' :
                                    'border-l-4 border-l-indigo-500'}
            `}
                    >
                        <div className={`
              w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
              ${toast.type === 'error' ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' :
                                toast.type === 'success' ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400' :
                                    'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400'}
            `}>
                            {toast.type === 'error' ? '✕' : toast.type === 'success' ? '✓' : 'ℹ'}
                        </div>
                        <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{toast.message}</p>
                        <button
                            onClick={() => removeToast(toast.id)}
                            className="ml-auto text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                        >
                            ✕
                        </button>
                    </div>
                ))}
            </div>

            {/* Custom Confirm Dialog */}
            {confirmState.isOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl max-w-sm w-full p-6 border border-white/20 scale-100 animate-in zoom-in-95 duration-200">
                        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">確認</h3>
                        <p className="text-slate-600 dark:text-slate-300 mb-6">{confirmState.message}</p>
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={confirmState.onCancel}
                                className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                            >
                                キャンセル
                            </button>
                            <button
                                onClick={confirmState.onConfirm}
                                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-md transition-colors"
                            >
                                実行する
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </ToastContext.Provider>
    );
};
