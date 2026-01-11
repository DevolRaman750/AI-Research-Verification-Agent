import React, { useState } from 'react';

const AnswerSection = ({ result }) => {
    const [evidenceOpen, setEvidenceOpen] = useState(false);

    if (!result) return null;

    const confidenceColor = {
        'HIGH': 'var(--clay-green)',
        'MEDIUM': 'var(--clay-accent)',
        'LOW': 'var(--clay-red)'
    }[result.confidence_level] || 'gray';

    return (
        <div style={{ animation: 'float 0.5s ease-out' }}>
            {/* Answer Card */}
            <div className="clay-card" style={{ borderTop: `10px solid ${confidenceColor}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h2 style={{ margin: 0 }}>The Result</h2>
                    <div style={{
                        backgroundColor: confidenceColor,
                        color: 'white',
                        padding: '0.5rem 1rem',
                        borderRadius: '20px',
                        fontFamily: 'Sniglet',
                        boxShadow: 'inset -2px -2px 4px rgba(0,0,0,0.2)'
                    }}>
                        {result.confidence_level} CONFIDENCE
                    </div>
                </div>

                <p style={{ fontSize: '1.1rem', lineHeight: '1.6' }}>
                    {result.answer}
                </p>

                <div style={{ marginTop: '1rem', fontStyle: 'italic', color: '#666', fontSize: '0.9rem' }}>
                    <strong>Assessment:</strong> {result.confidence_reason}
                </div>
            </div>

            {/* Evidence Section (Accordion) */}
            <div style={{ marginTop: '2rem' }}>
                <button
                    className="clay-btn secondary"
                    onClick={() => setEvidenceOpen(!evidenceOpen)}
                    style={{ width: '100%', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                >
                    <span>View Verified Evidence ({result.evidence.length})</span>
                    <span>{evidenceOpen ? '▲' : '▼'}</span>
                </button>

                {evidenceOpen && (
                    <div className="clay-card" style={{ backgroundColor: '#faf6eb' }}>
                        <ul style={{ listStyle: 'none', padding: 0 }}>
                            {result.evidence.map((item, idx) => (
                                <li key={idx} style={{
                                    marginBottom: '1rem',
                                    paddingBottom: '1rem',
                                    borderBottom: idx < result.evidence.length - 1 ? '1px dashed #ccc' : 'none'
                                }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                        <span style={{
                                            fontWeight: 'bold',
                                            color: item.status === 'VERIFIED' ? 'var(--clay-green)' : 'var(--clay-red)'
                                        }}>
                                            [{item.status}]
                                        </span>
                                        <a href={item.source} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--clay-primary)' }}>Source ↗</a>
                                    </div>
                                    <div>{item.claim}</div>
                                </li>
                            ))}
                        </ul>
                        {result.evidence.length === 0 && <p>No specific claims extracted.</p>}
                    </div>
                )}
            </div>
        </div>
    );
};

export default AnswerSection;
