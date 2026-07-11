import { useEffect, useRef } from 'react';

const FOCUSABLE_SELECTOR = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
].join(',');

export function useDialogFocus(onClose, initialFocusRef, active = true) {
    const dialogRef = useRef(null);
    const returnFocusRef = useRef(null);
    const onCloseRef = useRef(onClose);

    useEffect(() => {
        onCloseRef.current = onClose;
    }, [onClose]);

    useEffect(() => {
        if (!active) return undefined;
        returnFocusRef.current = document.activeElement instanceof HTMLElement
            ? document.activeElement
            : null;

        const focusInitialControl = () => {
            const target = initialFocusRef?.current
                || dialogRef.current?.querySelector(FOCUSABLE_SELECTOR);
            target?.focus();
        };
        const animationFrame = window.requestAnimationFrame(focusInitialControl);

        const handleKeyDown = event => {
            if (event.key === 'Escape') {
                event.preventDefault();
                onCloseRef.current?.();
                return;
            }
            if (event.key !== 'Tab' || !dialogRef.current) return;

            const controls = [...dialogRef.current.querySelectorAll(FOCUSABLE_SELECTOR)]
                .filter(control => control.getClientRects().length > 0);
            if (!controls.length) {
                event.preventDefault();
                dialogRef.current.focus();
                return;
            }

            const first = controls[0];
            const last = controls[controls.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => {
            window.cancelAnimationFrame(animationFrame);
            document.removeEventListener('keydown', handleKeyDown);
            const returnTarget = returnFocusRef.current;
            window.requestAnimationFrame(() => {
                if (returnTarget?.isConnected) returnTarget.focus();
            });
        };
    }, [active, initialFocusRef]);

    return dialogRef;
}