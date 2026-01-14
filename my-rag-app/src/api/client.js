// src/api/client.js
// 新規作成: API通信ロジックを集約

const API_BASE = 'http://localhost:8000/api';

export const fetchDocuments = async () => {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error('Fetch failed');
  return res.json();
};

export const fetchHistory = async () => {
  const res = await fetch(`${API_BASE}/history`);
  if (!res.ok) throw new Error('Fetch failed');
  return res.json();
};

export const uploadFile = async (file, enableOcr) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('enable_ocr', enableOcr);
  
  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Upload failed');
  }
  return res.json();
};

export const resetDb = async () => {
  const res = await fetch(`${API_BASE}/reset`, { method: 'POST' });
  if (!res.ok) throw new Error('Reset failed');
};

export const deleteDocument = async (filename) => {
  const res = await fetch(`${API_BASE}/delete_document`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  });
  if (!res.ok) throw new Error('Delete failed');
};

export const updateTitle = async (filename, newTitle) => {
  const res = await fetch(`${API_BASE}/update_title`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, new_title: newTitle }),
  });
  if (!res.ok) throw new Error('Update failed');
};

export const clearHistory = async () => {
  const res = await fetch(`${API_BASE}/history`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Clear history failed');
};

export const explainTerm = async (term) => {
  const res = await fetch(`${API_BASE}/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ term }),
  });
  if (!res.ok) throw new Error('Explain failed');
  return res.json();
};

// ストリーミング用URLなど
export const API_URLS = {
  ask: `${API_BASE}/ask`
};
