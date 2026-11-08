import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileText,
  User,
  CheckCircle2,
  Clock,
  ArrowRight,
  Sparkles,
  Layers,
  ChevronRight,
  Shield,
} from 'lucide-react';
import { useCandidate } from '../context/CandidateContext';
import { api } from '../api/client';
import { Button } from '../components/common/Button';
import { Card, CardHeader, CardContent } from '../components/common/Card';
import { Badge, StatusBadge } from '../components/common/Badge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const Dashboard = () => {
  const navigate = useNavigate();
  const { activeCandidate } = useCandidate();

  const [resumes, setResumes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [backendStatus, setBackendStatus] = useState('Checking...');

  useEffect(() => {
    let isMounted = true;

    const loadDashboardData = async () => {
      try {
        const [resumesData, healthData] = await Promise.allSettled([
          api.getResumes(),
          api.getHealth(),
        ]);

        if (isMounted) {
          if (resumesData.status === 'fulfilled') {
            setResumes(resumesData.value || []);
          }
          if (healthData.status === 'fulfilled') {
            setBackendStatus(healthData.value?.status === 'ok' ? 'Online' : 'Degraded');
          } else {
            setBackendStatus('Offline');
          }
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadDashboardData();
    return () => {
      isMounted = false;
    };
  }, []);

  const recentUploads = resumes.slice(0, 5);

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="max-w-xl">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-700/60 text-indigo-200 text-xs font-semibold mb-3 border border-indigo-500/30">
              <Sparkles className="w-3.5 h-3.5" />
              <span>ResumeIQ Career Intelligence</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-2">
              {activeCandidate ? `Welcome, ${activeCandidate.full_name}` : 'Welcome to ResumeIQ'}
            </h2>
            <p className="text-indigo-200/90 text-sm leading-relaxed">
              Upload and manage candidate resumes with automated PDF and DOCX text extraction, schema-validated storage, and inspection tools.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link to="/upload">
              <Button
                variant="primary"
                size="md"
                icon={UploadCloud}
                className="bg-white text-indigo-900 hover:bg-indigo-50 active:bg-indigo-100 shadow-md font-semibold"
              >
                Upload Resume
              </Button>
            </Link>
            <Link to="/history">
              <Button
                variant="ghost"
                size="md"
                className="text-white hover:bg-white/10 active:bg-white/20 border border-white/20"
              >
                View History
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        {/* Active Candidate Metric */}
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between text-slate-500 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider">
                Candidate Profile
              </span>
              <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <User className="w-4 h-4" />
              </div>
            </div>
            {activeCandidate ? (
              <div>
                <h4 className="text-lg font-bold text-slate-900 truncate">
                  {activeCandidate.full_name}
                </h4>
                <p className="text-xs text-slate-500 truncate">{activeCandidate.email}</p>
                <div className="mt-2.5 flex items-center justify-between">
                  <Badge variant="primary" size="xs">
                    {activeCandidate.candidate_type}
                  </Badge>
                  <Link to="/profile" className="text-xs text-indigo-600 hover:underline font-medium">
                    Manage
                  </Link>
                </div>
              </div>
            ) : (
              <div>
                <p className="text-sm font-semibold text-slate-700">No profile selected</p>
                <p className="text-xs text-slate-500 mt-0.5 mb-2">Create or select a candidate.</p>
                <Link to="/profile">
                  <Button variant="secondary" size="sm">
                    Set Candidate
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Total Resumes Metric */}
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between text-slate-500 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider">
                Total Uploads
              </span>
              <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <FileText className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-slate-900">{resumes.length}</div>
            <p className="text-xs text-slate-500 mt-1">
              Parsed resumes in database
            </p>
            <div className="mt-3">
              <Link to="/history" className="text-xs text-indigo-600 hover:underline font-medium flex items-center gap-1">
                <span>View all documents</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* System Backend Health */}
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between text-slate-500 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider">
                System Status
              </span>
              <div className="w-8 h-8 rounded-lg bg-slate-50 text-slate-600 flex items-center justify-center">
                <Shield className="w-4 h-4" />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  backendStatus === 'Online'
                    ? 'bg-emerald-500'
                    : backendStatus === 'Offline'
                    ? 'bg-rose-500'
                    : 'bg-amber-400 animate-pulse'
                }`}
              />
              <span className="text-lg font-bold text-slate-900">{backendStatus}</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              FastAPI + SQLite + PyMuPDF engine
            </p>
            <div className="mt-3 text-xs text-slate-400">
              API endpoint: <code className="text-slate-600">/api/health</code>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Uploads Section */}
      <Card>
        <CardHeader
          title="Recent Uploaded Resumes"
          subtitle="Recently parsed and stored documents"
          action={
            <Link to="/history">
              <Button variant="ghost" size="sm" icon={ArrowRight}>
                View All
              </Button>
            </Link>
          }
        />
        <CardContent className="p-0">
          {loading ? (
            <LoadingSpinner label="Loading recent activity..." size="sm" />
          ) : recentUploads.length === 0 ? (
            <div className="p-10 text-center text-slate-500 text-sm">
              <FileText className="w-8 h-8 mx-auto text-slate-300 mb-2" />
              <p className="font-semibold text-slate-700">No resumes uploaded yet</p>
              <p className="text-xs text-slate-500 max-w-xs mx-auto mt-1 mb-4">
                Upload your first PDF or Word document to inspect extracted plain text.
              </p>
              <Link to="/upload">
                <Button variant="primary" size="sm" icon={UploadCloud}>
                  Upload Resume
                </Button>
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {recentUploads.map((item) => (
                <div
                  key={item.id}
                  onClick={() => navigate(`/resumes/${item.id}`)}
                  className="p-4 sm:px-6 flex items-center justify-between hover:bg-slate-50/80 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    <div
                      className={`w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                        item.file_type === 'pdf'
                          ? 'bg-rose-50 text-rose-600'
                          : 'bg-blue-50 text-blue-600'
                      }`}
                    >
                      <FileText className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors truncate">
                        {item.original_filename}
                      </div>
                      <div className="text-xs text-slate-500 flex items-center gap-2 mt-0.5">
                        <span className="font-mono">#{item.id}</span>
                        <span>•</span>
                        <span>{item.file_type?.toUpperCase()}</span>
                        <span>•</span>
                        <span>
                          {item.created_at
                            ? new Date(item.created_at).toLocaleDateString()
                            : 'Recently'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <StatusBadge status={item.upload_status} />
                    <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 transition-colors hidden sm:block" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

