import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  FileText,
  User,
  ArrowRight,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { useCandidate } from '../context/CandidateContext';
import { api } from '../api/client';
import { FileDropzone } from '../components/upload/FileDropzone';
import { Button } from '../components/common/Button';
import { Card, CardHeader, CardContent } from '../components/common/Card';
import { Alert } from '../components/common/Alert';

export const ResumeUpload = () => {
  const navigate = useNavigate();
  const { activeCandidate, candidateId } = useCandidate();

  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    setErrorMessage(null);
    setUploadResult(null);
  };

  const handleFileRemove = () => {
    setSelectedFile(null);
    setUploadProgress(0);
    setErrorMessage(null);
    setUploadResult(null);
  };

  const handleUpload = async () => {
    if (!candidateId) {
      setErrorMessage('Please select or create an active Candidate Profile first before uploading.');
      return;
    }

    if (!selectedFile) {
      setErrorMessage('Please select a PDF or DOCX file to upload.');
      return;
    }

    setIsUploading(true);
    setUploadProgress(5);
    setErrorMessage(null);
    setUploadResult(null);

    try {
      const result = await api.uploadResume(candidateId, selectedFile, (percent) => {
        setUploadProgress(percent);
      });

      setUploadResult(result);
      setSelectedFile(null);
    } catch (err) {
      setErrorMessage(err.message || 'Upload and text extraction failed.');
      setUploadProgress(0);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">Upload Resume</h2>
        <p className="text-sm text-slate-500 mt-1">
          Upload a resume in PDF or DOCX format for automated validation and text extraction.
        </p>
      </div>

      {/* Candidate Profile Requirement Banner */}
      {!activeCandidate ? (
        <Alert
          type="warning"
          title="Candidate Profile Required"
          message={
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mt-1">
              <span>
                You must select or create a candidate profile before uploading a resume document.
              </span>
              <Link to="/profile">
                <Button variant="secondary" size="sm" icon={User}>
                  Configure Profile
                </Button>
              </Link>
            </div>
          }
        />
      ) : (
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-indigo-50/70 border border-indigo-100 text-xs text-indigo-900">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-indigo-600 text-white flex items-center justify-center font-bold text-xs">
              {activeCandidate.full_name?.charAt(0).toUpperCase()}
            </div>
            <div>
              <span className="font-semibold text-slate-900">{activeCandidate.full_name}</span>
              <span className="text-slate-500 ml-2">({activeCandidate.email})</span>
            </div>
          </div>
          <Link
            to="/profile"
            className="text-indigo-600 hover:text-indigo-800 font-semibold underline"
          >
            Switch Profile
          </Link>
        </div>
      )}

      {/* Feedback Notifications */}
      {errorMessage && (
        <Alert
          type="error"
          title="Upload Failed"
          message={errorMessage}
          onClose={() => setErrorMessage(null)}
        />
      )}

      {/* Success Banner */}
      {uploadResult && (
        <Card className="border-emerald-200 bg-emerald-50/40">
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center flex-shrink-0">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <h3 className="text-base font-semibold text-emerald-950 mb-1">
                  Document Uploaded & Text Extracted Successfully
                </h3>
                <p className="text-sm text-emerald-800 mb-3">
                  <strong>{uploadResult.original_filename}</strong> was parsed. Resume ID:{' '}
                  <span className="font-mono font-semibold">#{uploadResult.id}</span>
                </p>
                <div className="flex flex-wrap items-center gap-3">
                  <Button
                    variant="primary"
                    size="sm"
                    icon={FileText}
                    onClick={() => navigate(`/resumes/${uploadResult.id}`)}
                  >
                    View Extracted Text & Details
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setUploadResult(null);
                      setUploadProgress(0);
                    }}
                  >
                    Upload Another Document
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Dropzone Card */}
      {!uploadResult && (
        <Card>
          <CardHeader
            title="Select Document"
            subtitle="Upload candidate resume file (Max 5 MB)"
          />
          <CardContent className="space-y-6">
            <FileDropzone
              selectedFile={selectedFile}
              onFileSelect={handleFileSelect}
              onFileRemove={handleFileRemove}
              isUploading={isUploading}
              uploadProgress={uploadProgress}
              disabled={!activeCandidate || isUploading}
              onError={(msg) => setErrorMessage(msg)}
            />

            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-3 border-t border-slate-100">
              <div className="text-xs text-slate-500 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>Files are validated with binary header inspection and stored securely.</span>
              </div>

              <Button
                variant="primary"
                size="md"
                onClick={handleUpload}
                isLoading={isUploading}
                disabled={!selectedFile || !activeCandidate || isUploading}
                icon={UploadCloud}
                className="w-full sm:w-auto"
              >
                {isUploading ? `Uploading (${uploadProgress}%)` : 'Upload & Process'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Processing Pipeline Info Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-600">
        <div className="p-4 rounded-xl border border-slate-200 bg-white">
          <div className="font-semibold text-slate-900 mb-1 flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-indigo-600" />
            Binary Validation
          </div>
          <p className="text-slate-500">
            Checks magic headers (%PDF- and OpenXML PK) to prevent disguised or corrupt uploads.
          </p>
        </div>
        <div className="p-4 rounded-xl border border-slate-200 bg-white">
          <div className="font-semibold text-slate-900 mb-1 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-indigo-600" />
            PyMuPDF & python-docx
          </div>
          <p className="text-slate-500">
            High-fidelity text extraction across multi-page PDFs, Word paragraphs, and tables.
          </p>
        </div>
        <div className="p-4 rounded-xl border border-slate-200 bg-white">
          <div className="font-semibold text-slate-900 mb-1 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
            Collision-Free Storage
          </div>
          <p className="text-slate-500">
            Files are saved using UUID naming under uploads/, while maintaining original filenames.
          </p>
        </div>
      </div>
    </div>
  );
};

