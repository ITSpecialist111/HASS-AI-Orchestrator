import React from 'react';
import { CircleAlert, RotateCcw } from 'lucide-react';

export class WorkspaceErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { error: null };
    }

    static getDerivedStateFromError(error) {
        return { error };
    }

    componentDidCatch(error, info) {
        console.error('Workspace failed to render', error, info);
    }

    componentDidUpdate(previousProps) {
        if (previousProps.resetKey !== this.props.resetKey && this.state.error) {
            this.setState({ error: null });
        }
    }

    render() {
        if (!this.state.error) return this.props.children;
        return (
            <section className="cp-empty-state" role="alert">
                <CircleAlert size={26} />
                <div>
                    <strong>This workspace could not load</strong>
                    <span>{this.state.error.message || 'An unexpected dashboard error occurred.'}</span>
                </div>
                <button className="cp-button cp-button--primary" type="button" onClick={() => window.location.reload()}>
                    <RotateCcw size={15} /> Reload portal
                </button>
            </section>
        );
    }
}