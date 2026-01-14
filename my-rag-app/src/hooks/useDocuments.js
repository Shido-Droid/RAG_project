import { useState, useEffect, useCallback, useRef } from 'react';
import * as api from '../api/client';

export const useDocuments = () => {
  const [documents, setDocuments] = useState([]);
  const [isDocsLoading, setIsDocsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [editingDoc, setEditingDoc] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [deletingDoc, setDeletingDoc] = useState(null);
  const [useOcr, setUseOcr] = useState(false);
  const hasFetchedDocuments = useRef(false);

  const fetchDocuments = useCallback(async (retryCount = 0) => {
    setIsDocsLoading(true);
    try {
      const data = await api.fetchDocuments();
      setDocuments(data.documents || []);
      setIsDocsLoading(false);
    } catch (e) {
      console.error("Failed to fetch documents", e);
      if (retryCount < 5) { // 10回から5回に減らす
        setTimeout(() => fetchDocuments(retryCount + 1), 3000); // 2秒から3秒に
      } else {
        setIsDocsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    if (!hasFetchedDocuments.current) {
      hasFetchedDocuments.current = true;
      fetchDocuments();
    }
  }, [fetchDocuments]);

  const uploadFile = async (file) => {
    setIsUploading(true);
    try {
      const data = await api.uploadFile(file, useOcr);
      await fetchDocuments(); // refresh docs after upload
      return { success: true, data };
    } catch(error) {
      console.error("Upload failed", error);
      return { success: false, error };
    } 
    finally {
      setIsUploading(false);
    }
  };

  const deleteDocument = async (filename) => {
    setDeletingDoc(filename);
    try {
      await api.deleteDocument(filename);
      await fetchDocuments(); // refresh docs after delete
    } catch(error) {
        console.error("Delete failed", error);
    }
    finally {
      setDeletingDoc(null);
    }
  };

  const updateTitle = async (filename, newTitle) => {
    if (!newTitle.trim()) return;
    try {
      await api.updateTitle(filename, newTitle);
      await fetchDocuments(); // refresh docs after title update
      setEditingDoc(null);
    } catch (e) {
      console.error("Update title failed", e);
    }
  };

  const resetDb = async () => {
    try {
      await api.resetDb();
      setDocuments([]);
    } catch (e) {
      console.error("Reset DB failed", e);
      throw e;
    }
  };

  return {
    documents,
    isDocsLoading,
    isUploading,
    editingDoc, 
    setEditingDoc,
    editTitle, 
    setEditTitle,
    deletingDoc,
    useOcr,
    setUseOcr,
    fetchDocuments,
    uploadFile,
    deleteDocument,
    updateTitle,
    resetDb
  };
};