import { WebSocketServer } from 'ws';
import { getSttProvider } from './providers/stt/index.js';
import { tagCodeSwitching } from './accent/accentPreprocessor.js';

/**
 * Bridges the browser's MediaRecorder chunks to the streaming-capable STT
 * provider (Deepgram) and relays interim/final results back down as JSON.
 * Kept separate from the HTTP routes so the streaming path and the
 * "upload whole file" batch path can use different providers if desired
 * (e.g. Deepgram live for on-screen captions, Whisper batch for the final,
 * highest-accuracy transcript once recording stops).
 */
export function attachTranscriptionWebSocket(httpServer) {
  const wss = new WebSocketServer({ server: httpServer, path: '/ws/transcribe' });

  wss.on('connection', async (clientSocket) => {
    let session = null;
    let providerKey = 'deepgram';

    clientSocket.on('message', async (data, isBinary) => {
      if (!isBinary) {
        // First text frame is a small JSON config message from the client.
        try {
          const msg = JSON.parse(data.toString());
          if (msg.type === 'start') {
            providerKey = msg.provider || 'deepgram';
            const provider = getSttProvider(providerKey);
            if (typeof provider.openStream !== 'function') {
              clientSocket.send(JSON.stringify({ type: 'error', message: `${providerKey} does not support streaming` }));
              return;
            }
            session = await provider.openStream({
              mimeType: msg.mimeType || 'audio/webm',
              onOpen: () => clientSocket.send(JSON.stringify({ type: 'ready' })),
            });
            session.onResult((result) => {
              const codeSwitch = tagCodeSwitching(result.text);
              clientSocket.send(JSON.stringify({ type: 'transcript', ...result, codeSwitch }));
            });
            session.onError((err) => {
              clientSocket.send(JSON.stringify({ type: 'error', message: 'Upstream STT connection error.' }));
              console.error('[ws upstream]', err);
            });
            session.onClose(() => clientSocket.send(JSON.stringify({ type: 'closed' })));
          } else if (msg.type === 'stop') {
            session?.close();
          }
        } catch (err) {
          clientSocket.send(JSON.stringify({ type: 'error', message: 'Malformed control message.' }));
        }
        return;
      }

      // Binary frame = raw audio chunk
      if (session) session.sendAudio(data);
    });

    clientSocket.on('close', () => session?.close());
    clientSocket.on('error', () => session?.close());
  });

  return wss;
}
