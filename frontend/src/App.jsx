import React, { useState, useEffect } from 'react';
import './styles/global.css';
import QueryInput from './components/QueryInput';
import ResearchPipeline from './components/ResearchPipeline';
import AnswerSection from './components/AnswerSection';
import ContactPage from './components/ContactPage';
import TraceDebugPanel from './components/TraceDebugPanel';
// Use real API client (switch to './mock/api' for local testing without backend)
import { submitQuery, pollStatus, fetchResult, fetchTrace } from './api/client';

function App() {
  const [view, setView] = useState('HOME'); // 'HOME', 'CONTACT'
  // Research State
  const [queryId, setQueryId] = useState(null);
  const [status, setStatus] = useState('IDLE'); // IDLE, RESEARCHING, COMPLETED
  const [pipelineStepIndex, setPipelineStepIndex] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  // Debug trace state
  const [traceData, setTraceData] = useState(null);
  const [traceLoading, setTraceLoading] = useState(false);
  const [traceError, setTraceError] = useState(null);
  const [showDebug, setShowDebug] = useState(false);

  // Background Video Style
  const videoPath = '/asset/video/main-page.mp4';

  const handleSearch = async (question) => {
    setStatus('RESEARCHING');
    setResult(null);
    setPipelineStepIndex(0);
    setError(null);
    setTraceData(null);
    setTraceError(null);

    try {
      const { query_id } = await submitQuery(question);
      setQueryId(query_id);
    } catch (e) {
      setError("Failed to start research: " + e.message);
      setStatus('IDLE');
    }
  };

  // Polling Effect
  useEffect(() => {
    if (status !== 'RESEARCHING' || !queryId) return;

    const interval = setInterval(async () => {
      try {
        const data = await pollStatus(queryId);
        setPipelineStepIndex(data.current_step_index);

        if (data.is_complete) {
          clearInterval(interval);
          const res = await fetchResult(queryId);
          setResult(res);
          setStatus('COMPLETED');
          
          // Fetch trace data after completion
          if (showDebug) {
            loadTraceData(queryId);
          }
        }
      } catch (e) {
        console.error("Polling error", e);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [status, queryId, showDebug]);

  // Load trace data function
  const loadTraceData = async (sessionId) => {
    setTraceLoading(true);
    setTraceError(null);
    try {
      // Get token from env if available (for development)
      const token = import.meta.env.VITE_INTERNAL_TRACE_TOKEN || null;
      const trace = await fetchTrace(sessionId, token);
      setTraceData(trace);
    } catch (e) {
      setTraceError(e.message);
    } finally {
      setTraceLoading(false);
    }
  };

  // Toggle debug mode and load trace if we have a completed query
  const handleToggleDebug = () => {
    const newShowDebug = !showDebug;
    setShowDebug(newShowDebug);
    
    if (newShowDebug && queryId && status === 'COMPLETED' && !traceData) {
      loadTraceData(queryId);
    }
  };

  return (
    <div className="app-root">
      {/* Background Container - Only show video on HOME to avoid conflict with Contact BG */}
      {view === 'HOME' && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100vh',
          overflow: 'hidden',
          zIndex: -1
        }}>
          <div style={{
            position: 'absolute',
            top: 0, left: 0, width: '100%', height: '100%',
            backgroundColor: 'var(--clay-bg)',
            opacity: 0.9
          }}></div>
          <video
            autoPlay
            muted
            loop
            playsInline
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              opacity: 0.15,
              filter: 'contrast(1.2) sepia(0.3)'
            }}
          >
            <source src={videoPath} type="video/mp4" />
          </video>
        </div>
      )}

      {/* Navigation */}
      <header style={{
        padding: '1rem',
        textAlign: 'center',
        borderBottom: '4px solid #e0d0b0',
        backgroundColor: 'rgba(240, 230, 210, 0.9)',
        backdropFilter: 'blur(5px)',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}>
        <div className="clay-container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          {/* Logo / Home Link */}
          <div
            onClick={() => setView('HOME')}
            style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}
          >
            <div style={{
              width: '40px', height: '40px',
              backgroundColor: 'var(--clay-primary)',
              borderRadius: '50%',
              boxShadow: 'inset -2px -2px 4px rgba(0,0,0,0.2)'
            }}></div>
            <h1 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--clay-text)' }}>Research Clay</h1>
          </div>

          {/* Nav Links */}
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              className={view === 'CONTACT' ? 'clay-btn secondary' : 'clay-btn'}
              style={{ padding: '0.5rem 1.5rem', fontSize: '1rem' }}
              onClick={() => setView('CONTACT')}
            >
              Contact Me
            </button>
            <button
              className="clay-btn"
              style={{ padding: '0.5rem 1rem', fontSize: '1rem', backgroundColor: '#a0a0a0' }}
            >
              History
            </button>
            <button
              className={showDebug ? 'clay-btn secondary' : 'clay-btn'}
              style={{
                padding: '0.5rem 1rem',
                fontSize: '1rem',
                backgroundColor: showDebug ? '#ff9800' : '#607d8b'
              }}
              onClick={handleToggleDebug}
              title="Toggle debug trace panel"
            >
              🔍 Debug
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="clay-container" style={{ paddingBottom: '4rem' }}>

        {view === 'HOME' && (
          <>
            <div style={{ marginTop: '3rem' }}>
              <QueryInput onSearch={handleSearch} isLoading={status === 'RESEARCHING'} />
            </div>



            {status === 'RESEARCHING' && (
              <ResearchPipeline currentStepIndex={pipelineStepIndex} />
            )}

            {status === 'COMPLETED' && result && (
              <div style={{ marginTop: '3rem' }}>
                <AnswerSection result={result} />
              </div>
            )}

            {/* Debug Trace Panel - shown when debug mode is on and we have data or a completed query */}
            {showDebug && (status === 'COMPLETED' || traceData) && (
              <TraceDebugPanel
                traceData={traceData}
                isLoading={traceLoading}
                error={traceError}
              />
            )}

            {error && (
              <div className="clay-card" style={{ marginTop: '2rem', borderColor: 'red', color: 'red' }}>
                {error}
              </div>
            )}
          </>
        )}

        {view === 'CONTACT' && (
          <ContactPage />
        )}

      </main>
    </div>
  );
}

export default App;
