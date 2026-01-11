// Real API client for AI Research Agent backend

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

/**
 * Submit a new research query
 * POST /api/query
 * @param {string} question - The research question
 * @returns {Promise<{session_id: string, status: string}>}
 */
export const submitQuery = async (question) => {
  const response = await fetch(`${API_BASE_URL}/api/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question }),
  });

  if (response.status === 503) {
    throw new Error('Database temporarily unavailable. Please retry later.');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }

  const data = await response.json();
  // Map backend response to frontend expected format
  return {
    query_id: data.session_id,
    status: data.status,
  };
};

/**
 * Poll the current processing status
 * GET /api/query/{session_id}/status
 * @param {string} sessionId - The session UUID
 * @returns {Promise<{status: string, is_complete: boolean}>}
 */
export const pollStatus = async (sessionId) => {
  const response = await fetch(`${API_BASE_URL}/api/query/${sessionId}/status`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (response.status === 404) {
    throw new Error('Query not found');
  }

  if (response.status === 503) {
    throw new Error('Database temporarily unavailable. Please retry later.');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }

  const data = await response.json();
  const isComplete = data.status === 'DONE' || data.status === 'FAILED';
  
  return {
    query_id: sessionId,
    status: data.status,
    is_complete: isComplete,
    // Map planner states to pipeline steps for UI
    pipeline_step: mapStatusToPipelineStep(data.status),
    current_step_index: mapStatusToStepIndex(data.status),
  };
};

/**
 * Fetch the final result once processing completes
 * GET /api/query/{session_id}/result
 * @param {string} sessionId - The session UUID
 * @returns {Promise<Object>} The research result with answer, confidence, and evidence
 */
export const fetchResult = async (sessionId) => {
  const response = await fetch(`${API_BASE_URL}/api/query/${sessionId}/result`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (response.status === 404) {
    throw new Error('Query not found');
  }

  if (response.status === 409) {
    throw new Error('Result not ready yet');
  }

  if (response.status === 503) {
    throw new Error('Database temporarily unavailable. Please retry later.');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }

  return await response.json();
};

/**
 * Retrieve planner execution trace (debug/internal)
 * GET /api/query/{session_id}/trace
 * @param {string} sessionId - The session UUID
 * @param {string} [internalToken] - Optional X-Internal-Token header value
 * @returns {Promise<{planner_traces: Array, search_logs: Array}>}
 */
export const fetchTrace = async (sessionId, internalToken = null) => {
  const headers = {
    'Content-Type': 'application/json',
  };

  // Add internal token header if provided
  if (internalToken) {
    headers['X-Internal-Token'] = internalToken;
  }

  const response = await fetch(`${API_BASE_URL}/api/query/${sessionId}/trace`, {
    method: 'GET',
    headers,
  });

  if (response.status === 403) {
    throw new Error('Forbidden: Invalid or missing internal token');
  }

  if (response.status === 404) {
    throw new Error('Query not found');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }

  return await response.json();
};

// Helper: Map backend status to pipeline step name
function mapStatusToPipelineStep(status) {
  const statusMap = {
    'INIT': 'Searching sources',
    'RESEARCH': 'Searching sources',
    'VERIFY': 'Verifying evidence',
    'SYNTHESIZE': 'Synthesizing answer',
    'DONE': 'Synthesizing answer',
    'FAILED': 'Synthesizing answer',
  };
  return statusMap[status] || 'Processing';
}

// Helper: Map backend status to step index (0-4)
function mapStatusToStepIndex(status) {
  const indexMap = {
    'INIT': 0,
    'RESEARCH': 1,
    'VERIFY': 2,
    'SYNTHESIZE': 4,
    'DONE': 4,
    'FAILED': 4,
  };
  return indexMap[status] ?? 0;
}
