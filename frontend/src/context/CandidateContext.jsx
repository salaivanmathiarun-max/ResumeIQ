import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { api } from '../api/client';

const CandidateContext = createContext(null);

const STORAGE_KEY = 'resumeiq_candidate_id';

export const CandidateProvider = ({ children }) => {
  const [candidateId, setCandidateId] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? parseInt(saved, 10) : null;
  });

  const [activeCandidate, setActiveCandidate] = useState(null);
  const [candidatesList, setCandidatesList] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch list of all candidates
  const refreshCandidatesList = useCallback(async () => {
    try {
      const list = await api.getCandidates();
      setCandidatesList(list || []);
      return list;
    } catch (err) {
      console.warn('Failed to fetch candidates list:', err.message);
      return [];
    }
  }, []);

  // Fetch active candidate profile by ID
  const fetchActiveCandidate = useCallback(async (id) => {
    if (!id) {
      setActiveCandidate(null);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getCandidate(id);
      setActiveCandidate(data);
    } catch (err) {
      console.warn(`Candidate ${id} could not be loaded:`, err.message);
      // If 404 or missing, clear active selection
      setActiveCandidate(null);
      setCandidateId(null);
      localStorage.removeItem(STORAGE_KEY);
      setError('Active candidate not found on server.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Update selected candidate
  const selectCandidate = useCallback((id, candidateData = null) => {
    if (!id) {
      setCandidateId(null);
      setActiveCandidate(null);
      localStorage.removeItem(STORAGE_KEY);
      return;
    }

    setCandidateId(id);
    localStorage.setItem(STORAGE_KEY, id.toString());

    if (candidateData) {
      setActiveCandidate(candidateData);
      setIsLoading(false);
    } else {
      fetchActiveCandidate(id);
    }
  }, [fetchActiveCandidate]);

  // Initial load
  useEffect(() => {
    refreshCandidatesList();
    if (candidateId) {
      fetchActiveCandidate(candidateId);
    } else {
      setIsLoading(false);
    }
  }, [candidateId, fetchActiveCandidate, refreshCandidatesList]);

  return (
    <CandidateContext.Provider
      value={{
        candidateId,
        activeCandidate,
        candidatesList,
        isLoading,
        error,
        selectCandidate,
        refreshCandidate: () => candidateId && fetchActiveCandidate(candidateId),
        refreshCandidatesList,
      }}
    >
      {children}
    </CandidateContext.Provider>
  );
};

export const useCandidate = () => {
  const context = useContext(CandidateContext);
  if (!context) {
    throw new Error('useCandidate must be used within a CandidateProvider');
  }
  return context;
};

