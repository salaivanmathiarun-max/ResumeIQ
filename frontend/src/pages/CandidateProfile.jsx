import React, { useState } from 'react';
import { User, Mail, Briefcase, Plus, Check, AlertCircle, ArrowRight, Clock } from 'lucide-react';
import { useCandidate } from '../context/CandidateContext';
import { api } from '../api/client';
import { Button } from '../components/common/Button';
import { Card, CardHeader, CardContent } from '../components/common/Card';
import { Alert } from '../components/common/Alert';
import { Badge } from '../components/common/Badge';

export const CandidateProfile = () => {
  const {
    activeCandidate,
    candidateId,
    candidatesList,
    selectCandidate,
    refreshCandidatesList,
  } = useCandidate();

  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    candidate_type: 'student',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setErrorMessage(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.full_name.trim() || !formData.email.trim()) {
      setErrorMessage('Full name and email are required.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const created = await api.createCandidate(formData);
      selectCandidate(created.id, created);
      await refreshCandidatesList();

      setSuccessMessage(`Candidate profile "${created.full_name}" created and set as active.`);
      setFormData({
        full_name: '',
        email: '',
        candidate_type: 'student',
      });
    } catch (err) {
      setErrorMessage(err.message || 'Failed to create candidate profile.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSelectExisting = (candidate) => {
    selectCandidate(candidate.id, candidate);
    setSuccessMessage(`Active candidate switched to "${candidate.full_name}".`);
    setErrorMessage(null);
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">Candidate Profile</h2>
        <p className="text-sm text-slate-500 mt-1">
          Create or switch candidate profiles. All resume uploads and career intelligence metrics associate with the active profile.
        </p>
      </div>

      {/* Notifications */}
      {successMessage && (
        <Alert
          type="success"
          message={successMessage}
          onClose={() => setSuccessMessage(null)}
        />
      )}
      {errorMessage && (
        <Alert
          type="error"
          message={errorMessage}
          onClose={() => setErrorMessage(null)}
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Create Candidate Form */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader
              title="Create New Candidate"
              subtitle="Register a candidate profile to attach resumes and analysis"
            />
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                    Full Name *
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                      <User className="w-4 h-4" />
                    </div>
                    <input
                      type="text"
                      name="full_name"
                      value={formData.full_name}
                      onChange={handleChange}
                      placeholder="e.g. Alex Morgan"
                      disabled={isSubmitting}
                      className="w-full pl-10 pr-4 py-2.5 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition-colors"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                    Email Address *
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                      <Mail className="w-4 h-4" />
                    </div>
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      placeholder="e.g. alex.morgan@example.com"
                      disabled={isSubmitting}
                      className="w-full pl-10 pr-4 py-2.5 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition-colors"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                    Candidate Type *
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {[
                      { value: 'student', label: 'Student', desc: 'Currently in education' },
                      { value: 'fresher', label: 'Fresher', desc: '0 - 1 years experience' },
                      { value: 'experienced', label: 'Experienced', desc: '1+ years in industry' },
                    ].map((type) => (
                      <label
                        key={type.value}
                        className={`flex flex-col p-3.5 rounded-lg border cursor-pointer transition-all ${
                          formData.candidate_type === type.value
                            ? 'border-indigo-600 bg-indigo-50/50 ring-1 ring-indigo-600'
                            : 'border-slate-200 hover:border-slate-300 bg-white'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-semibold text-slate-800">
                            {type.label}
                          </span>
                          <input
                            type="radio"
                            name="candidate_type"
                            value={type.value}
                            checked={formData.candidate_type === type.value}
                            onChange={handleChange}
                            className="text-indigo-600 focus:ring-indigo-500"
                          />
                        </div>
                        <span className="text-xs text-slate-500">{type.desc}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <Button
                    type="submit"
                    variant="primary"
                    isLoading={isSubmitting}
                    icon={Plus}
                  >
                    Save & Set as Active
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>

        {/* Active Candidate Card */}
        <div className="space-y-6">
          <Card className="border-indigo-100 bg-gradient-to-b from-indigo-50/40 to-white">
            <CardHeader
              title="Active Profile"
              subtitle="Selected for current session"
            />
            <CardContent>
              {activeCandidate ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-lg shadow-sm">
                      {activeCandidate.full_name?.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <h4 className="text-base font-semibold text-slate-900">
                        {activeCandidate.full_name}
                      </h4>
                      <p className="text-xs text-slate-500">{activeCandidate.email}</p>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-100 space-y-2 text-xs">
                    <div className="flex items-center justify-between text-slate-600">
                      <span>Candidate ID:</span>
                      <strong className="font-mono text-slate-900">#{activeCandidate.id}</strong>
                    </div>
                    <div className="flex items-center justify-between text-slate-600">
                      <span>Career Stage:</span>
                      <span className="capitalize font-semibold text-indigo-700">
                        {activeCandidate.candidate_type}
                      </span>
                    </div>
                    {activeCandidate.created_at && (
                      <div className="flex items-center justify-between text-slate-600">
                        <span>Created:</span>
                        <span>{new Date(activeCandidate.created_at).toLocaleDateString()}</span>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-center py-6 text-slate-500 text-xs">
                  <User className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                  <p className="font-medium text-slate-700 mb-1">No Active Profile</p>
                  <p>Create a candidate using the form or select one from the list below.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Existing Candidates List */}
      <Card>
        <CardHeader
          title="All Candidate Profiles"
          subtitle={`${candidatesList.length} registered candidate profile${
            candidatesList.length === 1 ? '' : 's'
          }`}
        />
        <CardContent className="p-0">
          {candidatesList.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-sm">
              No candidate profiles registered yet. Create one above to get started.
            </div>
          ) : (
            <div className="divide-y divide-slate-100 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50/70 text-slate-600 text-xs font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="px-5 py-3">ID</th>
                    <th className="px-5 py-3">Candidate</th>
                    <th className="px-5 py-3">Type</th>
                    <th className="px-5 py-3">Registered</th>
                    <th className="px-5 py-3 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {candidatesList.map((cand) => {
                    const isActive = cand.id === candidateId;
                    return (
                      <tr
                        key={cand.id}
                        className={`hover:bg-slate-50/80 transition-colors ${
                          isActive ? 'bg-indigo-50/30' : ''
                        }`}
                      >
                        <td className="px-5 py-3.5 font-mono text-xs text-slate-500">
                          #{cand.id}
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="font-medium text-slate-900">{cand.full_name}</div>
                          <div className="text-xs text-slate-500">{cand.email}</div>
                        </td>
                        <td className="px-5 py-3.5">
                          <span className="capitalize text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                            {cand.candidate_type}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-xs text-slate-500">
                          {cand.created_at
                            ? new Date(cand.created_at).toLocaleDateString()
                            : '—'}
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          {isActive ? (
                            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                              <Check className="w-3.5 h-3.5" />
                              Active
                            </span>
                          ) : (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleSelectExisting(cand)}
                            >
                              Select
                            </Button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

