import React, { useState } from 'react';

const QueryInput = ({ onSearch, isLoading }) => {
    const [query, setQuery] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (query.trim() && !isLoading) {
            onSearch(query);
        }
    };

    return (
        <div className="clay-card" style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'center', backgroundColor: '#fffdf5' }}>
            <h2 style={{ color: 'var(--clay-primary)', fontSize: '2.5rem', marginBottom: '1rem' }}>Ask Research Clay</h2>
            <p style={{ marginBottom: '2rem', color: '#888' }}>
                Molding insights from chaos. Answers generated using verified sources.
            </p>

            <form onSubmit={handleSubmit} style={{ position: 'relative', width: '100%' }}>
                <input
                    type="text"
                    className="clay-input"
                    placeholder="e.g., 'Is ONDC mandatory for Indian e-commerce?'"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    disabled={isLoading}
                    style={{ width: '100%', paddingRight: '140px' }} // Space for button
                />
                <button
                    className="clay-btn"
                    type="submit"
                    disabled={isLoading || !query.trim()}
                    style={{
                        position: 'absolute',
                        right: '8px',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        padding: '0.5rem 1.5rem',
                        fontSize: '1rem',
                        opacity: isLoading ? 0.7 : 1,
                        marginTop: 0
                    }}
                >
                    {isLoading ? 'Molding...' : 'Research'}
                </button>
            </form>
        </div>
    );
};

export default QueryInput;
