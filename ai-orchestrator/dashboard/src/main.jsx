import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Global Error Trap for debugging Ingress issues
window.onerror = function (msg, source, lineno, colno, error) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'cp-fatal-error';
    const title = document.createElement('strong');
    title.textContent = 'Dashboard error';
    const message = document.createElement('div');
    message.textContent = String(msg || 'Unknown error');
    const location = document.createElement('small');
    location.textContent = `${source || 'unknown'}:${lineno || 0}:${colno || 0}`;
    const stack = document.createElement('pre');
    stack.textContent = error?.stack || '';
    errorDiv.append(title, message, location, stack);
    document.body.appendChild(errorDiv);
    return false;
};

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
)
