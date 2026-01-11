import React from 'react';

const ContactPage = () => {
    // Background style using the specific image requested
    const bgStyle = {
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        backgroundImage: "url('/asset/images/picture-1.jpg')",
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        zIndex: -1,
    };

    // Overlay to ensure text readability if the image is busy
    const overlayStyle = {
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(240, 230, 210, 0.6)', // Semi-transparent clay color
        backdropFilter: 'blur(3px)'
    };

    return (
        <>
            <div style={bgStyle}>
                <div style={overlayStyle}></div>
            </div>

            <div className="clay-container" style={{ paddingTop: '5rem', display: 'flex', justifyContent: 'center' }}>
                <div className="clay-card" style={{ maxWidth: '600px', width: '100%', textAlign: 'center', backgroundColor: 'rgba(255, 255, 255, 0.9)' }}>
                    <h2 style={{ fontSize: '2.5rem', color: 'var(--clay-primary)', marginBottom: '1.5rem' }}>Contact Us</h2>

                    <p style={{ fontSize: '1.1rem', lineHeight: '1.6', marginBottom: '2rem', color: '#555' }}>
                        We value your feedback and inquiries. Whether you have a question about our research methodology,
                        need assistance with the agent, or just want to say hello, we are here to assist you.
                        Molding the future of research requires collaboration, and we'd love to hear from you.
                    </p>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', alignItems: 'center' }}>

                        {/* Phone */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <div style={{
                                width: '50px', height: '50px',
                                backgroundColor: 'var(--clay-secondary)',
                                borderRadius: '50%',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                color: 'white', fontSize: '1.5rem'
                            }}>
                                📞
                            </div>
                            <div style={{ fontSize: '1.3rem', fontFamily: 'Sniglet' }}>+91-9872494516</div>
                        </div>

                        {/* Email */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <div style={{
                                width: '50px', height: '50px',
                                backgroundColor: 'var(--clay-red)',
                                borderRadius: '50%',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                color: 'white', fontSize: '1.5rem'
                            }}>
                                ✉️
                            </div>
                            <div style={{ fontSize: '1.3rem', fontFamily: 'Sniglet' }}>ramantripathi0707@gmail.com</div>
                        </div>

                    </div>

                    <div style={{ marginTop: '3rem' }}>
                        <button className="clay-btn" onClick={() => window.location.href = 'mailto:ramantripathi0707@gmail.com'}>
                            Send a Message
                        </button>
                    </div>

                </div>
            </div>
        </>
    );
};

export default ContactPage;
