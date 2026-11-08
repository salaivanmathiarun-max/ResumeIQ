import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  FileText,
  ArrowLeft,
  Copy,
  Check,
  Trash2,
  Calendar,
  User,
  Hash,
  Search,
  BookOpen,
  Code2,
  Sparkles,
  RefreshCw,
  Award,
  CheckCircle2,
  AlertCircle,
  Briefcase,
  TrendingUp,
  Layers,
  ChevronDown,
  ChevronUp,
  Cpu,
  ShieldCheck,
  Target,
} from 'lucide-react';
import { api } from '../api/client';
import { Button } from '../components/common/Button';
import { Card, CardHeader, CardContent } from '../components/common/Card';
import { Badge, StatusBadge } from '../components/common/Badge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { Alert } from '../components/common/Alert';
import { Modal } from '../components/common/Modal';

/**
 * Helper component that renders formatted text with clean typography,
 * section headings, and bullet points.
 */
const FormattedTextViewer = ({ text, searchQuery }) => {
  const renderedContent = useMemo(() => {
    if (!text) return null;

    const bulletRegex = /^(?:[•\-\*·–—]|\d+[\.\)])\s+(.*)$/;
    const headingKeywords = [
      'summary',
      'professional summary',
      'executive summary',
      'experience',
      'work experience',
      'professional experience',
      'employment history',
      'education',
      'academic background',
      'skills',
      'technical skills',
      'core competencies',
      'projects',
      'certifications',
      'awards',
      'languages',
      'publications',
    ];

    const paragraphs = text.split('\n\n');

    return paragraphs.map((para, paraIdx) => {
      const lines = para.split('\n').map((l) => l.trim()).filter(Boolean);

      return (
        <div key={paraIdx} className="space-y-2">
          {lines.map((line, lineIdx) => {
            const cleanLine = line.replace(/^[•\-\*·–—]\s*/, '').trim();
            const lowerLine = line.toLowerCase().replace(/:$/, '').trim();
            const isBullet = bulletRegex.test(line);
            const isExplicitHeading =
              (headingKeywords.includes(lowerLine) || line.endsWith(':')) &&
              line.length < 45 &&
              !isBullet;
            const isAllCapsHeading =
              line === line.toUpperCase() &&
              line.length >= 3 &&
              line.length <= 35 &&
              /^[A-Z\s&/,\-]+$/.test(line) &&
              !isBullet;

            const highlightText = (str) => {
              if (!searchQuery || !searchQuery.trim()) return str;
              const query = searchQuery.trim();
              const parts = str.split(new RegExp(`(${query})`, 'gi'));
              return parts.map((part, i) =>
                part.toLowerCase() === query.toLowerCase() ? (
                  <mark key={i} className="bg-amber-200 text-amber-900 rounded-xs px-0.5 font-medium">
                    {part}
                  </mark>
                ) : (
                  part
                )
              );
            };

            if (isExplicitHeading || isAllCapsHeading) {
              return (
                <div
                  key={lineIdx}
                  className="pt-4 pb-1 border-b border-slate-200/80 first:pt-0"
                >
                  <h4 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-indigo-950 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 inline-block" />
                    {highlightText(line)}
                  </h4>
                </div>
              );
            }

            if (isBullet) {
              return (
                <div
                  key={lineIdx}
                  className="flex items-start gap-2.5 text-xs sm:text-sm text-slate-700 leading-relaxed pl-1 sm:pl-3"
                >
                  <span className="text-indigo-500 font-bold select-none mt-0.5">•</span>
                  <span className="flex-1 break-words">{highlightText(cleanLine)}</span>
                </div>
              );
            }

            return (
              <p
                key={lineIdx}
                className="text-xs sm:text-sm text-slate-800 leading-relaxed break-words"
              >
                {highlightText(line)}
              </p>
            );
          })}
        </div>
      );
    });
  }, [text, searchQuery]);

  return <div className="space-y-5 p-6 sm:p-10 font-sans">{renderedContent}</div>;
};

/**
 * Score Pill with appropriate color semantics.
 */
const ScoreBadge = ({ score }) => {
  let color = 'bg-rose-50 text-rose-700 border-rose-200';
  let label = 'Needs Work';
  if (score >= 80) {
    color = 'bg-emerald-50 text-emerald-700 border-emerald-200';
    label = 'Excellent';
  } else if (score >= 65) {
    color = 'bg-indigo-50 text-indigo-700 border-indigo-200';
    label = 'Good';
  } else if (score >= 50) {
    color = 'bg-amber-50 text-amber-700 border-amber-200';
    label = 'Moderate';
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${color}`}>
      <span>{score}/100</span>
      <span className="opacity-70 font-normal">· {label}</span>
    </span>
  );
};

export const ResumeDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [resume, setResume] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);

  // Active view tab: 'analysis' | 'document'
  const [activeTab, setActiveTab] = useState('analysis');
  const [copied, setCopied] = useState(false);
  const [viewMode, setViewMode] = useState('formatted'); // 'formatted' | 'raw'
  const [searchQuery, setSearchQuery] = useState('');
  const [showFactorsBreakdown, setShowFactorsBreakdown] = useState(false);

  // Deletion modal state
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const fetchResumeAndAnalysis = async () => {
      setLoading(true);
      setError(null);
      try {
        const resumeData = await api.getResumeText(id);
        if (isMounted) setResume(resumeData);

        // Attempt to fetch existing analysis
        try {
          const analysisData = await api.getResumeAnalysis(id);
          if (isMounted) {
            setAnalysis(analysisData);
            if (analysisData.analysis_status === 'failed' && analysisData.analysis_error) {
              setAnalysisError(analysisData.analysis_error);
            }
          }
        } catch (err) {
          // If no analysis exists yet (404), default gracefully
          if (isMounted) setAnalysis(null);
        }

      } catch (err) {
        if (isMounted) setError(err.message || 'Failed to load resume details.');
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchResumeAndAnalysis();
    return () => {
      isMounted = false;
    };
  }, [id]);

  const handleAnalyzeResume = async () => {
    setAnalyzing(true);
    setAnalysisError(null);
    try {
      const data = await api.analyzeResume(id, { force_refresh: true });
      setAnalysis(data);
      if (data.analysis_status === 'failed' && data.analysis_error) {
        setAnalysisError(data.analysis_error);
      }
    } catch (err) {
      setAnalysisError(err.message || 'Failed to analyze resume. Please retry.');
    } finally {
      setAnalyzing(false);
    }
  };

  const activeText = useMemo(() => {
    if (!resume) return '';
    return viewMode === 'formatted'
      ? resume.normalized_text || resume.extracted_text || ''
      : resume.extracted_text || '';
  }, [resume, viewMode]);

  const stats = useMemo(() => {
    if (!activeText) return { words: 0, characters: 0, lines: 0 };
    const words = activeText.trim() ? activeText.trim().split(/\s+/).length : 0;
    const characters = activeText.length;
    const lines = activeText.split('\n').filter((l) => l.trim()).length;
    return { words, characters, lines };
  }, [activeText]);

  const handleCopyText = async () => {
    if (!activeText) return;
    try {
      await navigator.clipboard.writeText(activeText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.deleteResume(id);
      setIsDeleteModalOpen(false);
      navigate('/history');
    } catch (err) {
      setError(err.message || 'Failed to delete resume record.');
      setIsDeleting(false);
    }
  };

  if (loading) {
    return <LoadingSpinner label="Loading resume details and career intelligence..." size="lg" />;
  }

  if (error || !resume) {
    return (
      <div className="max-w-3xl mx-auto space-y-4">
        <Alert
          type="error"
          title="Resume Not Found"
          message={error || `Could not find a resume record with ID #${id}.`}
        />
        <div className="flex gap-3">
          <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate('/history')}>
            Back to Resume History
          </Button>
          <Button variant="ghost" onClick={() => navigate('/')}>
            Dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Top Header & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            icon={ArrowLeft}
            onClick={() => navigate(-1)}
          >
            Back
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-slate-900 tracking-tight truncate max-w-md">
                {resume.original_filename}
              </h2>
              <Badge variant={resume.file_type === 'pdf' ? 'pdf' : 'docx'}>
                {resume.file_type?.toUpperCase()}
              </Badge>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Resume ID: <span className="font-mono font-semibold text-slate-700">#{resume.id}</span>
              {' · '}Candidate #{resume.candidate_id}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Analyze / Retry / Re-run Action Button */}
          <Button
            variant={analysis?.analysis_status === 'completed' ? 'secondary' : 'primary'}
            size="sm"
            icon={analyzing ? RefreshCw : analysis?.analysis_status === 'failed' ? RefreshCw : analysis ? RefreshCw : Sparkles}
            onClick={handleAnalyzeResume}
            disabled={analyzing}
            className={analyzing ? 'animate-pulse' : ''}
          >
            {analyzing
              ? 'Analyzing...'
              : analysis?.analysis_status === 'failed'
              ? 'Retry Analysis'
              : analysis
              ? 'Re-run Analysis'
              : 'Analyze Resume'}
          </Button>

          <Button
            variant="secondary"
            size="sm"
            icon={copied ? Check : Copy}
            onClick={handleCopyText}
            disabled={!activeText}
          >
            {copied ? 'Copied' : 'Copy Text'}
          </Button>

          <Button
            variant="danger"
            size="sm"
            icon={Trash2}
            onClick={() => setIsDeleteModalOpen(true)}
          >
            Delete
          </Button>
        </div>
      </div>

      {/* Main Tabs Navigation */}
      <div className="flex border-b border-slate-200 bg-white rounded-t-xl px-4 pt-2 gap-2 shadow-xs">
        <button
          type="button"
          onClick={() => setActiveTab('analysis')}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'analysis'
              ? 'border-indigo-600 text-indigo-700'
              : 'border-transparent text-slate-500 hover:text-slate-900'
          }`}
        >
          <Sparkles className="w-4 h-4 text-indigo-600" />
          <span>Resume Compatibility & AI Insights</span>
          {analysis && (
            <span className="ml-1 px-2 py-0.5 text-xs rounded-full bg-indigo-50 text-indigo-700 font-bold border border-indigo-200">
              {analysis.compatibility_score}%
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('document')}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'document'
              ? 'border-indigo-600 text-indigo-700'
              : 'border-transparent text-slate-500 hover:text-slate-900'
          }`}
        >
          <FileText className="w-4 h-4 text-slate-500" />
          <span>Extracted Document Text</span>
          <span className="text-xs text-slate-400 font-mono">({stats.words} words)</span>
        </button>
      </div>

      {/* Tab 1: AI Compatibility & Insights */}
      {activeTab === 'analysis' && (
        <div className="space-y-6">
          {/* Analysis Error Notification if any */}
          {analysisError && (
            <Alert
              type="error"
              title="Analysis Error"
              message={analysisError}
              onClose={() => setAnalysisError(null)}
            />
          )}

          {/* If analyzing currently */}
          {analyzing && (
            <Card className="p-12 text-center">
              <div className="max-w-md mx-auto space-y-4">
                <div className="w-14 h-14 mx-auto rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center">
                  <RefreshCw className="w-7 h-7 text-indigo-600 animate-spin" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Evaluating Resume Compatibility...
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Running candidate-type-aware scoring engine and extracting evidence-grounded career intelligence with Gemini.
                  </p>
                </div>
              </div>
            </Card>
          )}

          {/* Empty State: Not yet analyzed */}
          {!analyzing && !analysis && (
            <Card className="p-8 sm:p-12 text-center bg-gradient-to-b from-white to-slate-50 border-dashed border-2 border-slate-200">
              <div className="max-w-md mx-auto space-y-4">
                <div className="w-14 h-14 mx-auto rounded-2xl bg-indigo-100/70 text-indigo-600 flex items-center justify-center">
                  <Sparkles className="w-7 h-7" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900">
                    Unlock Career Intelligence
                  </h3>
                  <p className="text-xs sm:text-sm text-slate-500 mt-1.5 leading-relaxed">
                    Generate an objective <strong>Resume Compatibility Score</strong>, section completeness audit, verified technical skills matrix, and evidence-grounded recommendations tailored to this candidate profile.
                  </p>
                </div>
                <div className="pt-2">
                  <Button
                    variant="primary"
                    icon={Sparkles}
                    onClick={handleAnalyzeResume}
                    disabled={analyzing}
                  >
                    Analyze Resume Now
                  </Button>
                </div>
              </div>
            </Card>
          )}

          {/* Populated Analysis View */}
          {!analyzing && analysis && (
            <div className="space-y-6">
              {/* Primary Score Overview Card */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {/* Composite Resume Compatibility Score */}
                <div className="md:col-span-1 p-6 rounded-2xl bg-slate-900 bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 text-white shadow-md border border-slate-800 flex flex-col justify-between overflow-hidden min-w-0">
                  <div>
                    <span className="text-[11px] uppercase tracking-wider font-bold text-indigo-300">
                      Overall Rating
                    </span>
                    <h3 className="text-base font-bold text-white mt-0.5">
                      Resume Compatibility
                    </h3>
                  </div>

                  <div className="my-5 text-center">
                    <div className="inline-flex items-baseline gap-1">
                      <span className="text-5xl sm:text-6xl font-extrabold tracking-tight text-white drop-shadow-xs">
                        {analysis.compatibility_score}
                      </span>
                      <span className="text-lg text-slate-300 font-semibold">/100</span>
                    </div>
                    <div className="mt-2.5">
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${
                        analysis.compatibility_score >= 80
                          ? 'bg-emerald-500/25 text-emerald-200 border border-emerald-400/40'
                          : analysis.compatibility_score >= 65
                          ? 'bg-sky-500/25 text-sky-200 border border-sky-400/40'
                          : 'bg-amber-500/25 text-amber-200 border border-amber-400/40'
                      }`}>
                        {analysis.compatibility_score >= 80
                          ? 'Strong Profile Match'
                          : analysis.compatibility_score >= 65
                          ? 'Good Foundation'
                          : 'Optimization Recommended'}
                      </span>
                    </div>
                  </div>

                  <div className="text-[11px] text-slate-300/80 border-t border-slate-800 pt-3 flex items-center justify-between">
                    <span className="truncate mr-2">Engine: {analysis.model_name || 'ResumeIQ Heuristic'}</span>
                    <span className="capitalize shrink-0">{analysis.analysis_status}</span>
                  </div>
                </div>

                {/* Subscore Pillars */}
                <div className="md:col-span-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {/* Section Completeness */}
                  <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col justify-between min-w-0">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="p-2 rounded-xl bg-blue-50 text-blue-600">
                          <Layers className="w-4 h-4" />
                        </span>
                        <ScoreBadge score={analysis.section_score} />
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">
                        Section Completeness
                      </h4>
                      <p className="text-xs text-slate-500 mt-1">
                        Coverage of essential sections based on candidate experience level.
                      </p>
                    </div>
                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
                      <span>Detected:</span>
                      <span className="font-semibold text-slate-900">
                        {analysis.identified_sections?.length || 0} Sections
                      </span>
                    </div>
                  </div>

                  {/* Impact & Action Verbs */}
                  <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col justify-between min-w-0">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="p-2 rounded-xl bg-purple-50 text-purple-600">
                          <TrendingUp className="w-4 h-4" />
                        </span>
                        <ScoreBadge score={analysis.impact_score} />
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">
                        Measurable Impact
                      </h4>
                      <p className="text-xs text-slate-500 mt-1">
                        Frequency of action verbs, metrics, percentages, and scale indicators.
                      </p>
                    </div>
                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
                      <span>Action Score:</span>
                      <span className="font-semibold text-purple-700">
                        {analysis.impact_score >= 70 ? 'High Active Tone' : 'Passive/Descriptive'}
                      </span>
                    </div>
                  </div>

                  {/* Formatting & Scannability */}
                  <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col justify-between min-w-0">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="p-2 rounded-xl bg-emerald-50 text-emerald-600">
                          <ShieldCheck className="w-4 h-4" />
                        </span>
                        <ScoreBadge score={analysis.formatting_score} />
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">
                        Document Structure
                      </h4>
                      <p className="text-xs text-slate-500 mt-1">
                        Scannable bullet points, length suitability, and contact links.
                      </p>
                    </div>
                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
                      <span>Word Count:</span>
                      <span className="font-semibold text-slate-900">
                        {stats.words.toLocaleString()} words
                      </span>
                    </div>
                  </div>
                </div>
              </div>


              {/* Collapsible Factor Breakdown Explanation */}
              {analysis.scoring_breakdown && (
                <Card className="overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setShowFactorsBreakdown(!showFactorsBreakdown)}
                    className="w-full p-4 sm:px-6 bg-slate-50/70 hover:bg-slate-100/70 transition-colors flex items-center justify-between text-left"
                  >
                    <div className="flex items-center gap-2">
                      <Target className="w-4 h-4 text-indigo-600" />
                      <span className="text-xs sm:text-sm font-bold text-slate-900">
                        Candidate-Type Scoring Breakdown & Transparent Weights
                      </span>
                      <span className="text-xs text-slate-500 capitalize">
                        ({analysis.scoring_breakdown.candidate_type || 'General'} Profile)
                      </span>
                    </div>
                    {showFactorsBreakdown ? (
                      <ChevronUp className="w-4 h-4 text-slate-500" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-slate-500" />
                    )}
                  </button>

                  {showFactorsBreakdown && (
                    <CardContent className="p-6 space-y-5 border-t border-slate-200">
                      {/* Section Factors */}
                      {analysis.scoring_breakdown.section_factors?.length > 0 && (
                        <div>
                          <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                            Section Completeness Audit
                          </h5>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                            {analysis.scoring_breakdown.section_factors.map((f, idx) => (
                              <div
                                key={idx}
                                className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-start justify-between gap-3 min-w-0"
                              >
                                <div className="min-w-0 flex-1">
                                  <div className="text-xs font-semibold text-slate-900 truncate">{f.name}</div>
                                  <div className="text-[11px] text-slate-500 mt-0.5 break-words leading-relaxed">{f.explanation}</div>
                                </div>
                                <span className={`text-xs font-bold px-2 py-0.5 rounded-full shrink-0 ${
                                  f.score >= 100 ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                                }`}>
                                  {f.score}%
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Impact Factors */}
                      {analysis.scoring_breakdown.impact_factors?.length > 0 && (
                        <div>
                          <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                            Impact & Content Precision Factors
                          </h5>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                            {analysis.scoring_breakdown.impact_factors.map((f, idx) => (
                              <div
                                key={idx}
                                className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-start justify-between gap-3 min-w-0"
                              >
                                <div className="min-w-0 flex-1">
                                  <div className="text-xs font-semibold text-slate-900 truncate">{f.name}</div>
                                  <div className="text-[11px] text-slate-500 mt-0.5 break-words leading-relaxed">{f.explanation}</div>
                                </div>
                                <span className="text-xs font-bold text-slate-700 bg-slate-200/80 px-2 py-0.5 rounded-full shrink-0">
                                  {f.score}%
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Formatting Factors */}
                      {analysis.scoring_breakdown.formatting_factors?.length > 0 && (
                        <div>
                          <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                            Formatting & Structure Factors
                          </h5>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                            {analysis.scoring_breakdown.formatting_factors.map((f, idx) => (
                              <div
                                key={idx}
                                className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-start justify-between gap-3 min-w-0"
                              >
                                <div className="min-w-0 flex-1">
                                  <div className="text-xs font-semibold text-slate-900 truncate">{f.name}</div>
                                  <div className="text-[11px] text-slate-500 mt-0.5 break-words leading-relaxed">{f.explanation}</div>
                                </div>
                                <span className="text-xs font-bold text-slate-700 bg-slate-200/80 px-2 py-0.5 rounded-full shrink-0">
                                  {f.score}%
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  )}
                </Card>
              )}

              {/* Executive Summary */}
              {analysis.summary && (
                <Card className="p-6 bg-gradient-to-r from-indigo-50/70 via-slate-50 to-purple-50/40 border border-indigo-100/90 overflow-hidden min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-4 h-4 text-indigo-600 shrink-0" />
                    <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-950">
                      Executive Profile Summary
                    </h4>
                  </div>
                  <p className="text-xs sm:text-sm text-slate-800 leading-relaxed break-words whitespace-normal">
                    {analysis.summary}
                  </p>
                </Card>
              )}

              {/* Grounded Strengths & Actionable Improvements Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 min-w-0">
                {/* Strengths */}
                <Card className="p-6 flex flex-col justify-between overflow-hidden min-w-0">
                  <div>
                    <div className="flex items-center gap-2 pb-3 border-b border-slate-100 mb-4">
                      <span className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600 shrink-0">
                        <CheckCircle2 className="w-4 h-4" />
                      </span>
                      <h4 className="text-sm font-bold text-slate-900">
                        Verified Strengths
                      </h4>
                    </div>
                    {analysis.strengths?.length > 0 ? (
                      <ul className="space-y-3">
                        {analysis.strengths.map((str, idx) => (
                          <li key={idx} className="flex items-start gap-2.5 text-xs text-slate-700 leading-relaxed min-w-0">
                            <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                            <span className="break-words min-w-0">{str}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-400 italic">No specific strengths recorded.</p>
                    )}
                  </div>
                </Card>

                {/* Improvements */}
                <Card className="p-6 flex flex-col justify-between overflow-hidden min-w-0">
                  <div>
                    <div className="flex items-center gap-2 pb-3 border-b border-slate-100 mb-4">
                      <span className="p-1.5 rounded-lg bg-amber-50 text-amber-600 shrink-0">
                        <TrendingUp className="w-4 h-4" />
                      </span>
                      <h4 className="text-sm font-bold text-slate-900">
                        Evidence-Based Improvements
                      </h4>
                    </div>
                    {analysis.improvements?.length > 0 ? (
                      <div className="space-y-3.5">
                        {analysis.improvements.map((item, idx) => (
                          <div key={idx} className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1.5 overflow-hidden min-w-0">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-amber-100 text-amber-900">
                                {item.category}
                              </span>
                            </div>
                            <div className="text-xs font-semibold text-slate-900 break-words">
                              {item.issue}
                            </div>
                            <div className="text-xs text-slate-600 leading-relaxed break-words whitespace-normal">
                              {item.recommendation}
                            </div>
                            {item.example && (
                              <div className="mt-1 p-2 rounded-lg bg-white border border-slate-200 text-[11px] font-mono text-slate-700 break-words whitespace-pre-wrap overflow-x-auto">
                                💡 Example: {item.example}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400 italic">No major issues detected.</p>
                    )}
                  </div>
                </Card>
              </div>

              {/* Categorized Skills Matrix */}
              {analysis.skills_categorized && Object.keys(analysis.skills_categorized).length > 0 && (
                <Card className="p-6 overflow-hidden min-w-0">
                  <div className="flex items-center gap-2 pb-3 border-b border-slate-100 mb-4">
                    <span className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600 shrink-0">
                      <Cpu className="w-4 h-4" />
                    </span>
                    <div>
                      <h4 className="text-sm font-bold text-slate-900">
                        Categorized Technical & Domain Skills
                      </h4>
                      <p className="text-[11px] text-slate-500">
                        Verified skills extracted directly from resume project and experience descriptions.
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Object.entries(analysis.skills_categorized).map(([category, skillList], idx) => (
                      <div key={idx} className="p-3.5 rounded-xl bg-slate-50/70 border border-slate-200/80 overflow-hidden min-w-0">
                        <div className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2 truncate">
                          {category}
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {Array.isArray(skillList) && skillList.map((skill, sIdx) => (
                            <span
                              key={sIdx}
                              className="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700 text-xs font-medium break-words max-w-full"
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {/* Suggested Matching Job Roles */}
              {analysis.suggested_roles?.length > 0 && (
                <Card className="p-6 bg-slate-50/60 overflow-hidden min-w-0">
                  <div className="flex items-center gap-2 mb-3">
                    <Briefcase className="w-4 h-4 text-indigo-600 shrink-0" />
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      Target Job Roles Matched to Profile
                    </h4>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {analysis.suggested_roles.map((role, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 rounded-full bg-white border border-indigo-200 text-indigo-900 text-xs font-semibold shadow-2xs break-words"
                      >
                        {role}
                      </span>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          )}
        </div>
      )}


      {/* Tab 2: Extracted Document Text */}
      {activeTab === 'document' && (
        <Card className="overflow-hidden">
          {/* Header with View Controls */}
          <div className="p-4 sm:px-6 bg-slate-50/80 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 mr-1">
                Preview Mode:
              </span>
              <div className="inline-flex rounded-lg p-0.5 bg-slate-200/80 text-xs font-medium">
                <button
                  type="button"
                  onClick={() => setViewMode('formatted')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
                    viewMode === 'formatted'
                      ? 'bg-white text-indigo-700 shadow-xs font-semibold'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>Clean Reader</span>
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('raw')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
                    viewMode === 'raw'
                      ? 'bg-white text-indigo-700 shadow-xs font-semibold'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Code2 className="w-3.5 h-3.5" />
                  <span>Raw Extracted</span>
                </button>
              </div>
            </div>

            {/* Quick Search in Document */}
            <div className="relative w-full sm:w-64">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search in document..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition-colors"
              />
            </div>
          </div>

          {/* Content Area */}
          <CardContent className="p-0">
            {!activeText ? (
              <div className="p-12 text-center text-slate-400 text-sm">
                <FileText className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                <p>No extracted text available for this document.</p>
              </div>
            ) : viewMode === 'formatted' ? (
              <div className="bg-white max-h-[650px] overflow-y-auto">
                <FormattedTextViewer text={activeText} searchQuery={searchQuery} />
              </div>
            ) : (
              <div className="p-6 bg-slate-900 text-slate-100 max-h-[650px] overflow-y-auto overflow-x-auto">
                <pre className="text-xs sm:text-sm font-mono leading-relaxed whitespace-pre-wrap select-text break-words">
                  {activeText}
                </pre>
              </div>
            )}
          </CardContent>

          {/* Footer info */}
          <div className="px-6 py-3 bg-slate-50/60 border-t border-slate-100 text-xs text-slate-500 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <span>
              {viewMode === 'formatted'
                ? '✨ Clean Reader View: Normalized line wrapping and formatted headings. Factual content is strictly preserved.'
                : 'Verbatim extracted text as parsed directly by the document processing engine.'}
            </span>
            <span className="font-mono text-[11px] text-slate-400">
              {stats.lines} text blocks
            </span>
          </div>
        </Card>
      )}

      {/* Bottom Navigation */}
      <div className="flex items-center justify-between pt-2">
        <Link to="/history" className="text-xs text-slate-500 hover:text-slate-800 underline">
          ← Back to Resume History
        </Link>
        <Link to="/" className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">
          Go to Dashboard →
        </Link>
      </div>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title="Delete Resume Record"
        confirmLabel="Yes, Delete Record"
        confirmVariant="danger"
        isConfirming={isDeleting}
        onConfirm={handleDelete}
      >
        <p>
          Are you sure you want to delete <strong>{resume.original_filename}</strong> (ID #{resume.id})?
        </p>
        <p className="mt-2 text-xs text-slate-500">
          This will permanently remove the resume metadata, extracted text, and the stored file from disk. This action cannot be undone.
        </p>
      </Modal>
    </div>
  );
};
