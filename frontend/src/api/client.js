/**
 * Centralized API client for ResumeIQ.
 * Supports VITE_API_BASE_URL for decoupled production hosting (e.g. Vercel + Render/Railway)
 * while defaulting to relative URLs (/api) for local development via Vite's proxy.
 */

const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const API_BASE_URL = RAW_BASE_URL.replace(/\/+$/, '');

function buildUrl(endpoint) {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${cleanEndpoint}`;
}

class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function request(endpoint, options = {}) {
  const url = buildUrl(endpoint);

  const defaultHeaders = {
    'Accept': 'application/json',
  };

  if (!(options.body instanceof FormData)) {
    defaultHeaders['Content-Type'] = 'application/json';
  }

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);

    // 204 No Content
    if (response.status === 204) {
      return null;
    }

    let data = null;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      const text = await response.text();
      data = text ? { detail: text } : null;
    }

    if (!response.ok) {
      const errorMessage =
        (data && (data.detail || data.message)) ||
        `Request failed with status ${response.status}`;
      throw new ApiError(errorMessage, response.status, data);
    }

    return data;
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }
    // Network errors or backend unavailable
    throw new ApiError(
      'Unable to connect to the ResumeIQ backend server. Please verify that the FastAPI backend is running.',
      0,
      null
    );
  }
}

export const api = {
  // System Health
  getHealth: () => request('/api/health'),

  // Candidates
  getCandidates: () => request('/api/candidates/'),
  getCandidate: (id) => request(`/api/candidates/${id}`),
  createCandidate: (data) =>
    request('/api/candidates/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Resumes
  getResumes: () => request('/api/resumes/'),
  getResume: (id) => request(`/api/resumes/${id}`),
  getResumeText: (id) => request(`/api/resumes/${id}/text`),
  deleteResume: (id) =>
    request(`/api/resumes/${id}`, {
      method: 'DELETE',
    }),

  // Analyses
  analyzeResume: (id, payload = {}) =>
    request(`/api/resumes/${id}/analyze`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getResumeAnalysis: (id) => request(`/api/resumes/${id}/analysis`),


  /**
   * Upload resume document (PDF or DOCX).
   * Uses XMLHttpRequest to accurately support upload progress tracking.
   * Does NOT manually set Content-Type header so browser generates multipart boundary.
   */
  uploadResume: (candidateId, file, onProgress) => {
    return new Promise((resolve, reject) => {
      const formData = new FormData();
      formData.append('candidate_id', candidateId);
      formData.append('file', file);

      const xhr = new XMLHttpRequest();
      xhr.open('POST', buildUrl('/api/resumes/upload'));

      if (onProgress && xhr.upload) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            onProgress(percent);
          }
        };
      }

      xhr.onload = () => {
        let responseData = null;
        try {
          responseData = JSON.parse(xhr.responseText);
        } catch {
          responseData = { detail: xhr.responseText };
        }

        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(responseData);
        } else {
          const detail =
            (responseData && (responseData.detail || responseData.message)) ||
            `Upload failed with status ${xhr.status}`;
          reject(new ApiError(detail, xhr.status, responseData));
        }
      };

      xhr.onerror = () => {
        reject(
          new ApiError(
            'Network failure during file upload. Check your connection or backend status.',
            0,
            null
          )
        );
      };

      xhr.send(formData);
    });
  },
};

export { ApiError };

