import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { CandidateProvider } from './context/CandidateContext';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './pages/Dashboard';
import { CandidateProfile } from './pages/CandidateProfile';
import { ResumeUpload } from './pages/ResumeUpload';
import { ResumeHistory } from './pages/ResumeHistory';
import { ResumeDetails } from './pages/ResumeDetails';

export const App = () => {
  return (
    <BrowserRouter>
      <CandidateProvider>
        <Routes>
          <Route
            path="/"
            element={
              <Layout pageTitle="Dashboard">
                <Dashboard />
              </Layout>
            }
          />
          <Route
            path="/profile"
            element={
              <Layout pageTitle="Candidate Profile">
                <CandidateProfile />
              </Layout>
            }
          />
          <Route
            path="/upload"
            element={
              <Layout pageTitle="Upload Resume">
                <ResumeUpload />
              </Layout>
            }
          />
          <Route
            path="/history"
            element={
              <Layout pageTitle="Resume History">
                <ResumeHistory />
              </Layout>
            }
          />
          <Route
            path="/resumes/:id"
            element={
              <Layout pageTitle="Resume Details">
                <ResumeDetails />
              </Layout>
            }
          />
          {/* Catch-all redirect to Dashboard */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </CandidateProvider>
    </BrowserRouter>
  );
};

export default App;
