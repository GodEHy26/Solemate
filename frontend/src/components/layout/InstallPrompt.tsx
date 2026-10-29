import { useEffect, useState } from 'react';

interface InstallEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

const isStandalone = () =>
  window.matchMedia('(display-mode: standalone)').matches ||
  (navigator as Navigator & { standalone?: boolean }).standalone === true;
const isIos = () => /iphone|ipad|ipod/i.test(navigator.userAgent);

export function InstallPrompt() {
  const [event, setEvent] = useState<InstallEvent | null>(null);
  const [dismissed, setDismissed] = useState(() => {
    try {
      return localStorage.getItem('solemate-install-dismissed') === '1';
    } catch {
      return false;
    }
  });

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setEvent(e as InstallEvent);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const dismiss = () => {
    setDismissed(true);
    try {
      localStorage.setItem('solemate-install-dismissed', '1');
    } catch { /* storage unavailable */ }
  };

  if (dismissed || isStandalone()) return null;
  if (!event && !isIos()) return null;

  return (
    <div className="container" style={{ paddingTop: 12, paddingBottom: 0 }}>
      <div className="install-banner">
        <span className="small">
          {event ? 'Install SoleMate for one-tap scanning.' : 'Install: tap Share, then “Add to Home Screen”.'}
        </span>
        <span className="row">
          {event && (
            <button className="btn primary" onClick={() => void event.prompt().then(dismiss)}>Install</button>
          )}
          <button className="btn ghost" onClick={dismiss} aria-label="Dismiss">✕</button>
        </span>
      </div>
    </div>
  );
}
