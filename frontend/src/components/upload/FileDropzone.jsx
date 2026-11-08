import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, X, AlertCircle } from 'lucide-react';
import { Button } from '../common/Button';

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB
const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];

export const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

export const FileDropzone = ({
  selectedFile,
  onFileSelect,
  onFileRemove,
  isUploading = false,
  uploadProgress = 0,
  disabled = false,
  onError,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef(null);

  const validateAndSelect = (file) => {
    if (!file) return;

    const ext = `.${file.name.split('.').pop().toLowerCase()}`;
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      const msg = `Unsupported file format '${ext}'. Please upload a PDF or DOCX file.`;
      if (onError) onError(msg);
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      const msg = `File size (${formatFileSize(file.size)}) exceeds the maximum limit of 5 MB.`;
      if (onError) onError(msg);
      return;
    }

    if (file.size === 0) {
      const msg = 'Selected file is empty (0 bytes).';
      if (onError) onError(msg);
      return;
    }

    if (onError) onError(null);
    onFileSelect(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (disabled || isUploading) return;
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled || isUploading) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSelect(e.target.files[0]);
    }
  };

  const getFileExtension = (name) => {
    return name.split('.').pop().toUpperCase();
  };

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        onChange={handleFileInputChange}
        className="hidden"
        disabled={disabled || isUploading}
      />

      {!selectedFile ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !disabled && !isUploading && inputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 sm:p-12 text-center cursor-pointer transition-all ${
            isDragOver
              ? 'border-indigo-500 bg-indigo-50/50 scale-[1.005]'
              : 'border-slate-300 hover:border-indigo-400 bg-slate-50/40 hover:bg-slate-50'
          } ${disabled || isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center shadow-xs">
            <UploadCloud className="w-7 h-7" />
          </div>
          <h4 className="text-base font-semibold text-slate-800 mb-1">
            Drag & drop your resume here, or <span className="text-indigo-600 underline">browse</span>
          </h4>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mb-3">
            Supports PDF and DOCX documents up to 5 MB.
          </p>
          <div className="inline-flex items-center gap-2 text-[11px] font-medium text-slate-400 px-3 py-1 rounded-full bg-white border border-slate-200">
            <span>PDF (PyMuPDF)</span>
            <span>•</span>
            <span>DOCX (Word)</span>
          </div>
        </div>
      ) : (
        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3.5 min-w-0">
              <div
                className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-xs uppercase flex-shrink-0 ${
                  getFileExtension(selectedFile.name) === 'PDF'
                    ? 'bg-rose-50 text-rose-600 border border-rose-100'
                    : 'bg-blue-50 text-blue-600 border border-blue-100'
                }`}
              >
                <FileText className="w-6 h-6" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-900 truncate">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {formatFileSize(selectedFile.size)} • {getFileExtension(selectedFile.name)} Document
                </p>
              </div>
            </div>

            {!isUploading && (
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => inputRef.current?.click()}
                  disabled={disabled}
                >
                  Replace
                </Button>
                <button
                  type="button"
                  onClick={onFileRemove}
                  disabled={disabled}
                  className="text-slate-400 hover:text-rose-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
                  aria-label="Remove selected file"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          {/* Upload progress state */}
          {isUploading && (
            <div className="mt-4 pt-3 border-t border-slate-100">
              <div className="flex items-center justify-between text-xs font-medium text-slate-600 mb-1.5">
                <span>Uploading and extracting document text...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-indigo-600 h-2 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${Math.max(5, uploadProgress)}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

