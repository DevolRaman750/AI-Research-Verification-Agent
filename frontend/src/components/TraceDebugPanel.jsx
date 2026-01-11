import React, { useState } from 'react';

const TraceDebugPanel = ({ traceData, isLoading, error }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    if (!traceData && !isLoading && !error) {
        return null;
    }

    const { planner_traces = [], search_logs = [] } = traceData || {};

    const getDecisionColor = (decision) => {
        switch (decision) {
            case 'ACCEPT': return '#4CAF50';
            case 'RETRY': return '#FF9800';
            case 'STOP': return '#f44336';
            default: return '#9e9e9e';
        }
    };

    const getStateColor = (state) => {
        switch (state) {
            case 'DONE': return '#4CAF50';
            case 'FAILED': return '#f44336';
            case 'VERIFY': return '#2196F3';
            case 'RESEARCH': return '#FF9800';
            case 'SYNTHESIZE': return '#9C27B0';
            default: return '#9e9e9e';
        }
    };

    return (
        <div className="clay-card" style={{
            marginTop: '2rem',
            backgroundColor: '#2d2d2d',
            color: '#e0e0e0',
            border: '3px solid #444'
        }}>
            {/* Header - Always visible */}
            <div
                onClick={() => setIsExpanded(!isExpanded)}
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    cursor: 'pointer',
                    padding: '0.5rem 0'
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span style={{ fontSize: '1.2rem' }}>🔍</span>
                    <h3 style={{ margin: 0, color: '#ffd54f', fontFamily: 'Sniglet' }}>
                        Debug Trace
                    </h3>
                    <span style={{
                        fontSize: '0.75rem',
                        backgroundColor: '#444',
                        padding: '0.25rem 0.5rem',
                        borderRadius: '8px'
                    }}>
                        {planner_traces.length} attempts · {search_logs.length} searches
                    </span>
                </div>
                <span style={{
                    fontSize: '1.5rem',
                    transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s'
                }}>
                    ▼
                </span>
            </div>

            {/* Loading State */}
            {isLoading && (
                <div style={{ padding: '1rem', textAlign: 'center', color: '#888' }}>
                    Loading trace data...
                </div>
            )}

            {/* Error State */}
            {error && (
                <div style={{
                    padding: '1rem',
                    backgroundColor: 'rgba(244, 67, 54, 0.1)',
                    borderRadius: '8px',
                    color: '#f44336'
                }}>
                    ⚠️ {error}
                </div>
            )}

            {/* Expanded Content */}
            {isExpanded && traceData && (
                <div style={{ marginTop: '1rem' }}>
                    {/* Planner Traces */}
                    <div style={{ marginBottom: '1.5rem' }}>
                        <h4 style={{
                            color: '#81d4fa',
                            marginBottom: '0.75rem',
                            borderBottom: '1px solid #444',
                            paddingBottom: '0.5rem'
                        }}>
                            📋 Planner Traces
                        </h4>
                        {planner_traces.length === 0 ? (
                            <div style={{ color: '#888', fontStyle: 'italic' }}>No traces recorded</div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                {planner_traces.map((trace, idx) => (
                                    <div
                                        key={idx}
                                        style={{
                                            backgroundColor: '#383838',
                                            borderRadius: '10px',
                                            padding: '0.75rem 1rem',
                                            borderLeft: `4px solid ${getDecisionColor(trace.verification_decision)}`
                                        }}
                                    >
                                        <div style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            marginBottom: '0.5rem'
                                        }}>
                                            <span style={{
                                                fontWeight: 'bold',
                                                color: '#fff'
                                            }}>
                                                Attempt #{trace.attempt_number}
                                            </span>
                                            <span style={{
                                                backgroundColor: getDecisionColor(trace.verification_decision),
                                                color: '#fff',
                                                padding: '0.2rem 0.6rem',
                                                borderRadius: '12px',
                                                fontSize: '0.75rem',
                                                fontWeight: 'bold'
                                            }}>
                                                {trace.verification_decision}
                                            </span>
                                        </div>
                                        <div style={{
                                            display: 'grid',
                                            gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                                            gap: '0.5rem',
                                            fontSize: '0.85rem'
                                        }}>
                                            <div>
                                                <span style={{ color: '#888' }}>State: </span>
                                                <span style={{ color: getStateColor(trace.planner_state) }}>
                                                    {trace.planner_state}
                                                </span>
                                            </div>
                                            <div>
                                                <span style={{ color: '#888' }}>Strategy: </span>
                                                <span style={{ color: '#ce93d8' }}>{trace.strategy_used}</span>
                                            </div>
                                            <div>
                                                <span style={{ color: '#888' }}>Docs: </span>
                                                <span style={{ color: '#fff' }}>{trace.num_docs}</span>
                                            </div>
                                        </div>
                                        {trace.created_at && (
                                            <div style={{
                                                fontSize: '0.7rem',
                                                color: '#666',
                                                marginTop: '0.5rem'
                                            }}>
                                                {new Date(trace.created_at).toLocaleString()}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Search Logs */}
                    <div>
                        <h4 style={{
                            color: '#81d4fa',
                            marginBottom: '0.75rem',
                            borderBottom: '1px solid #444',
                            paddingBottom: '0.5rem'
                        }}>
                            🔎 Search Logs
                        </h4>
                        {search_logs.length === 0 ? (
                            <div style={{ color: '#888', fontStyle: 'italic' }}>No searches recorded</div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                {search_logs.map((log, idx) => (
                                    <div
                                        key={idx}
                                        style={{
                                            backgroundColor: '#383838',
                                            borderRadius: '10px',
                                            padding: '0.75rem 1rem',
                                            borderLeft: `4px solid ${log.success ? '#4CAF50' : '#f44336'}`
                                        }}
                                    >
                                        <div style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'flex-start',
                                            gap: '1rem'
                                        }}>
                                            <div style={{ flex: 1 }}>
                                                <div style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.5rem',
                                                    marginBottom: '0.25rem'
                                                }}>
                                                    <span style={{ color: '#888', fontSize: '0.85rem' }}>
                                                        #{log.attempt_number}
                                                    </span>
                                                    <span style={{
                                                        color: log.success ? '#4CAF50' : '#f44336',
                                                        fontSize: '0.75rem'
                                                    }}>
                                                        {log.success ? '✓ Success' : '✗ Failed'}
                                                    </span>
                                                </div>
                                                <div style={{
                                                    color: '#fff',
                                                    fontSize: '0.9rem',
                                                    wordBreak: 'break-word'
                                                }}>
                                                    "{log.query_used}"
                                                </div>
                                            </div>
                                            <div style={{
                                                backgroundColor: '#444',
                                                padding: '0.25rem 0.5rem',
                                                borderRadius: '6px',
                                                fontSize: '0.75rem',
                                                whiteSpace: 'nowrap'
                                            }}>
                                                {log.num_docs} docs
                                            </div>
                                        </div>
                                        {log.created_at && (
                                            <div style={{
                                                fontSize: '0.7rem',
                                                color: '#666',
                                                marginTop: '0.5rem'
                                            }}>
                                                {new Date(log.created_at).toLocaleString()}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default TraceDebugPanel;
