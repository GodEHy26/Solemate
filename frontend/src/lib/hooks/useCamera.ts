import { useCallback, useEffect, useRef, useState } from 'react';

export type CameraStatus = 'idle' | 'starting' | 'ready' | 'denied' | 'unavailable';

function attach(video: HTMLVideoElement, stream: MediaStream) {
  if (video.srcObject !== stream) video.srcObject = stream;
  void video.play().catch(() => undefined);
}

/**
 * Rear-camera stream bound to a <video>, plus a JPEG snapshot helper.
 *
 * `videoRef` is a callback ref, so the stream follows whichever <video> is mounted. The scan
 * wizard shows a different <video> on each step while the camera stays on; with a plain ref the
 * stream stayed on the first element and the next step's preview was black.
 */
export function useCamera(active: boolean) {
  const elementRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [status, setStatus] = useState<CameraStatus>('idle');

  const videoRef = useCallback((el: HTMLVideoElement | null) => {
    elementRef.current = el;
    if (el && streamRef.current) attach(el, streamRef.current);
  }, []);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (elementRef.current) elementRef.current.srcObject = null;
    setStatus('idle');
  }, []);

  useEffect(() => {
    if (!active) {
      stop();
      return;
    }
    let cancelled = false;
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus('unavailable');
      return;
    }
    setStatus('starting');
    navigator.mediaDevices
      .getUserMedia({
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 960 } },
        audio: false,
      })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (elementRef.current) attach(elementRef.current, stream);
        setStatus('ready');
      })
      .catch((err: DOMException) => {
        setStatus(err?.name === 'NotAllowedError' ? 'denied' : 'unavailable');
      });
    return () => {
      cancelled = true;
      stop();
    };
  }, [active, stop]);

  const snapshot = useCallback(async (maxSide = 1280, quality = 0.9): Promise<Blob | null> => {
    const video = elementRef.current;
    if (!video || video.videoWidth === 0) return null;
    const scale = Math.min(1, maxSide / Math.max(video.videoWidth, video.videoHeight));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    canvas.getContext('2d')!.drawImage(video, 0, 0, canvas.width, canvas.height);
    return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality));
  }, []);

  return { videoRef, status, snapshot, stop };
}
