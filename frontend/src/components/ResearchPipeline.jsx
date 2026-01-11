import React from 'react';

const STEPS = [
    'Searching sources',
    'Extracting factual claims',
    'Verifying evidence',
    'Scoring confidence',
    'Synthesizing answer'
];

const ResearchPipeline = ({ currentStepIndex }) => {
    return (
        <div className="clay-card" style={{ marginTop: '2rem', textAlign: 'center' }}>
            <div style={{ marginBottom: '1.5rem' }}>
                <img
                    src="/asset/images/icon/search-Icon.jpg"
                    alt="Searching..."
                    style={{
                        width: '60px',
                        height: '60px',
                        borderRadius: '50%',
                        objectFit: 'cover',
                        border: '4px solid var(--clay-primary)',
                        animation: 'float 2s infinite ease-in-out'
                    }}
                />
            </div>
            <h3 style={{ marginBottom: '2rem', color: 'var(--clay-text)' }}>Research Pipeline</h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center' }}>
                {STEPS.map((step, index) => {
                    let statusClass = 'pipeline-step';
                    if (index === currentStepIndex) statusClass += ' active';
                    if (index < currentStepIndex) statusClass += ' completed';

                    return (
                        <div key={index} className={statusClass} style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '1rem',
                            width: '100%',
                            maxWidth: '500px'
                        }}>
                            {/* Step indicator (Clay Ball) */}
                            <div style={{
                                width: '40px',
                                height: '40px',
                                borderRadius: '50%',
                                backgroundColor: index <= currentStepIndex ? (index === currentStepIndex ? 'var(--clay-accent)' : 'var(--clay-green)') : '#dcdcdc',
                                boxShadow: 'inset -3px -3px 6px rgba(0,0,0,0.2), inset 3px 3px 6px rgba(255,255,255,0.5)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: 'white',
                                fontWeight: 'bold',
                                fontSize: '1.2rem',
                                fontFamily: 'Sniglet'
                            }}>
                                {index < currentStepIndex ? '✓' : (index + 1)}
                            </div>

                            {/* Text */}
                            <div style={{
                                flex: 1,
                                textAlign: 'left',
                                padding: '1rem',
                                backgroundColor: index === currentStepIndex ? 'white' : 'transparent',
                                borderRadius: '15px',
                                boxShadow: index === currentStepIndex ? 'var(--clay-shadow-out)' : 'none',
                                fontWeight: index === currentStepIndex ? 'bold' : 'normal',
                                color: index > currentStepIndex ? '#aaa' : 'var(--clay-text)'
                            }}>
                                {step}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default ResearchPipeline;
