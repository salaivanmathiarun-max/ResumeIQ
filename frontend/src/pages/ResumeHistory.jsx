import React, { useEffect, useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FileText,
  Trash2,
  ExternalLink,
  Search,
  Filter,
  RefreshCw,
  UploadCloud,
  Calendar,
  AlertCircle,
} from 'lucide-react';
import { api } from '../api/client';
import { Button } from '../components/common/Button';
import { Card, CardHeader, CardContent } from '../components/common/Card';
import { Badge, StatusBadge } from '../components/common/Badge';
import { EmptyState } from '../components/common/EmptyState';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { Alert } from '../components/common/Alert';
import { Modal } from '../components/common/Modal';

export const ResumeHistory = () => {
  const navigate = useNavigate();
  const [resumes, setResumes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');

  // Deletion modal state
  const [resumeToDelete, setResumeToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchResumes = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getResumes();
      setResumes(data || []);
    } catch (err) {
      setError(err.message || 'Failed to fetch resume history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResumes();
  }, []);

  const filteredResumes = useMemo(() => {
    return resumes.filter((item) => {
      const matchesSearch =
        item.original_filename?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.id?.toString().includes(searchQuery);
      const matchesType =
        typeFilter === 'all' || item.file_type?.toLowerCase() === typeFilter.toLowerCase();
      return matchesSearch && matchesType;
    });
  }, [resumes, searchQuery, typeFilter]);

  const confirmDelete = (resume) => {
    setResumeToDelete(resume);
  };

  const handleDelete = async () => {
    if (!resumeToDelete) return;
    setIsDeleting(true);
    try {
      await api.deleteResume(resumeToDelete.id);
      setResumes((prev) => prev.filter((r) => r.id !== resumeToDelete.id));
      setResumeToDelete(null);
    } catch (err) {
      setError(err.message || 'Failed to delete resume record.');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Resume History</h2>
          <p className="text-sm text-slate-500 mt-1">
            Browse, inspect, and manage all parsed resume documents and extracted text.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Button
            variant="secondary"
            size="sm"
            icon={RefreshCw}
            onClick={fetchResumes}
            disabled={loading}
          >
            Refresh
          </Button>
          <Link to="/upload">
            <Button variant="primary" size="sm" icon={UploadCloud}>
              Upload Resume
            </Button>
          </Link>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <Alert
          type="error"
          title="Error"
          message={error}
          onClose={() => setError(null)}
        />
      )}

      {/* Search and Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search by filename or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition-colors"
              />
            </div>

            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="text-sm py-2 px-3 rounded-lg border border-slate-200 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              >
                <option value="all">All Formats</option>
                <option value="pdf">PDF only</option>
                <option value="docx">DOCX only</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Resumes Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <LoadingSpinner label="Loading resume history..." size="md" />
          ) : resumes.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No resumes found"
              description="No documents have been uploaded to ResumeIQ yet. Upload your first PDF or DOCX file to get started."
              actionLabel="Upload First Resume"
              onAction={() => navigate('/upload')}
            />
          ) : filteredResumes.length === 0 ? (
            <div className="p-12 text-center text-slate-500 text-sm">
              No resumes match your current search criteria.
            </div>
          ) : (
            <div className="overflow-x-auto divide-y divide-slate-100">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50/70 text-slate-600 text-xs font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="px-5 py-3.5">ID</th>
                    <th className="px-5 py-3.5">Document Name</th>
                    <th className="px-5 py-3.5">Format</th>
                    <th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5">Candidate ID</th>
                    <th className="px-5 py-3.5">Uploaded</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredResumes.map((item) => (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-50/80 transition-colors group cursor-pointer"
                      onClick={() => navigate(`/resumes/${item.id}`)}
                    >
                      <td className="px-5 py-4 font-mono text-xs text-slate-500">
                        #{item.id}
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2.5">
                          <div
                            className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                              item.file_type?.toLowerCase() === 'pdf'
                                ? 'bg-rose-50 text-rose-600'
                                : 'bg-blue-50 text-blue-600'
                            }`}
                          >
                            <FileText className="w-4 h-4" />
                          </div>
                          <span className="font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors">
                            {item.original_filename}
                          </span>
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <Badge variant={item.file_type === 'pdf' ? 'pdf' : 'docx'}>
                          {item.file_type?.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="px-5 py-4">
                        <StatusBadge status={item.upload_status} />
                      </td>
                      <td className="px-5 py-4 font-mono text-xs text-slate-600">
                        #{item.candidate_id}
                      </td>
                      <td className="px-5 py-4 text-xs text-slate-500 whitespace-nowrap">
                        {item.created_at
                          ? new Date(item.created_at).toLocaleDateString()
                          : '—'}
                      </td>
                      <td
                        className="px-5 py-4 text-right"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="flex items-center justify-end gap-1.5">
                          <Link to={`/resumes/${item.id}`}>
                            <Button variant="ghost" size="sm" icon={ExternalLink}>
                              View
                            </Button>
                          </Link>
                          <button
                            type="button"
                            onClick={() => confirmDelete(item)}
                            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-slate-100 rounded-md transition-colors"
                            aria-label="Delete resume"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!resumeToDelete}
        onClose={() => setResumeToDelete(null)}
        title="Confirm Resume Deletion"
        confirmLabel="Delete Resume"
        confirmVariant="danger"
        isConfirming={isDeleting}
        onConfirm={handleDelete}
      >
        <p>
          Are you sure you want to delete{' '}
          <strong>{resumeToDelete?.original_filename}</strong> (ID #{resumeToDelete?.id})?
        </p>
        <p className="mt-2 text-xs text-slate-500">
          This will permanently delete the resume record, extracted text, and remove the file from storage.
        </p>
      </Modal>
    </div>
  );
};

