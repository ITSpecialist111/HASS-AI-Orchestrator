import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Global Error Trap for debugging Ingress issues
window.onerror = function (msg, source, lineno, colno, error) {
    const errorDiv = document.createElement('div');
    errorDiv.style.position = 'fixed';
    errorDiv.style.top = '0';
    errorDiv.style.left = '0';
    errorDiv.style.width = '100%';
    errorDiv.style.backgroundColor = '#991b1b';
    errorDiv.style.color = '#fee2e2';
    errorDiv.style.padding = '20px';
    errorDiv.style.zIndex = '999999';
    errorDiv.style.fontFamily = 'monospace';
    errorDiv.style.fontSize = '14px';
    errorDiv.innerHTML = `
        <strong>CRITICAL DASHBOARD ERROR:</strong><br/>
        ${msg}<br/>
        <small>${source}:${lineno}:${colno}</small><br/>
        <pre>${error ? error.stack : ''}</pre>
    `;
    document.body.appendChild(errorDiv);
    return false;
};

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
)
