/**
 * 音频捕获 Hook — 替代 Web Speech API
 *
 * 在桌面模式下使用:
 *   getUserMedia 捕获麦克风音频
 *   → WebSocket 发送到 Python ASR (ws://localhost:8000/ws/asr)
 *   → 接收流式转写结果
 *
 * 回退:
 *   如果 WebSocket 连接失败，使用 Web Speech API 作为后备
 */
import { useState, useCallback, useRef, useEffect } from 'react';

interface AudioCaptureHook {
  isListening: boolean;
  transcript: string;
  interimTranscript: string;
  isSupported: boolean;
  error: string | null;
  startListening: () => void;
  stopListening: () => void;
  resetTranscript: () => void;
  useWebSocket: boolean; // 是否使用 WebSocket ASR
}

const ASR_WS_URL = 'ws://127.0.0.1:8000/ws/asr';

export function useAudioCapture(): AudioCaptureHook {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [useWebSocket, setUseWebSocket] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const isListeningRef = useRef(false);

  // 保持 ref 与 state 同步，避免闭包过期
  useEffect(() => {
    isListeningRef.current = isListening;
  }, [isListening]);

  const isSupported = typeof navigator !== 'undefined' &&
    'mediaDevices' in navigator &&
    'getUserMedia' in navigator.mediaDevices;

  /**
   * 尝试连接 WebSocket ASR
   */
  const connectWebSocket = useCallback((): Promise<boolean> => {
    return new Promise((resolve) => {
      try {
        const ws = new WebSocket(ASR_WS_URL);

        ws.onopen = () => {
          console.log('[AudioCapture] WebSocket ASR 已连接');
          setUseWebSocket(true);
          resolve(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'partial') {
              setInterimTranscript(data.text);
            } else if (data.type === 'final') {
              // 用完整文本替换而非追加，避免旧实现中增量对比失败导致的重复/丢失
              setTranscript(data.text);
              setInterimTranscript('');
            } else if (data.type === 'end') {
              // 服务端确认本次会话结束，此时可以安全关闭连接
              ws.close();
            } else if (data.type === 'error') {
              setError(`ASR 错误: ${data.message}`);
            }
          } catch {
            // 非 JSON 消息
          }
        };

        ws.onerror = () => {
          console.warn('[AudioCapture] WebSocket ASR 连接失败，回退到 Web Speech API');
          ws.close();
          setUseWebSocket(false);
          resolve(false);
        };

        ws.onclose = (event) => {
          console.warn('[AudioCapture] WebSocket 关闭 code=' + event.code + ' reason=' + event.reason);
          // 只有当前 WS 仍然是活跃的且正在监听时才重置状态
          // 避免前一个已关闭的 WS 的 onclose 误停新录音
          if (ws === wsRef.current && isListeningRef.current) {
            console.log('[AudioCapture] 正在录音时 WS 断开，重置录音状态');
            setIsListening(false);
          }
        };

        wsRef.current = ws;
      } catch {
        resolve(false);
      }
    });
  }, []); // 注意: 使用 ref 避免依赖 isListening 导致闭包过期

  /**
   * 使用 WebSocket ASR 开始录音
   */
  const startWebSocketRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // 使用 MediaRecorder 捕获音频块
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm',
      });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
          event.data.arrayBuffer().then((buffer) => {
            wsRef.current?.send(buffer);
          });
        }
      };

      // 每 100ms 发送一次音频块
      mediaRecorder.start(100);
      mediaRecorderRef.current = mediaRecorder;
      setIsListening(true);
      isListeningRef.current = true; // 同步 ref，避免 ws.onclose 闭包检查过期值
      setError(null);
    } catch (err: any) {
      setError(`麦克风访问失败: ${err.message}`);
    }
  }, []);

  /**
   * 使用浏览器 Web Speech API（回退方案）
   */
  const startWebSpeech = useCallback(() => {
    if (typeof window === 'undefined') return;

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setError('浏览器不支持语音识别');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'zh-CN';

    recognition.onresult = (event: any) => {
      let final = '';
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          final += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }
      if (final) setTranscript((prev) => prev + final);
      setInterimTranscript(interim);
    };

    recognition.onerror = (event: any) => {
      setError(`语音识别错误: ${event.error}`);
      setIsListening(false);
    };

    recognition.onend = () => setIsListening(false);

    try {
      recognition.start();
      setIsListening(true);
      setError(null);

      // 保存引用以便停止
      (window as any)._speechRecognition = recognition;
    } catch (e: any) {
      setError(`启动失败: ${e.message}`);
    }
  }, []);

  /**
   * 开始录音
   */
  const startListening = useCallback(async () => {
    setTranscript('');
    setInterimTranscript('');
    setError(null);

    // 优先尝试 WebSocket ASR
    const wsConnected = await connectWebSocket();
    if (wsConnected) {
      await startWebSocketRecording();
    } else {
      // 回退到 Web Speech API
      startWebSpeech();
    }
  }, [connectWebSocket, startWebSocketRecording, startWebSpeech]);

  /**
   * 停止录音
   *
   * 逻辑：
   *   1. 停止麦克风采集
   *   2. 发送 "stop" 命令给服务端
   *   3. 服务端回复 "final"（更新 transcript）+ "end"
   *   4. ws.onmessage 在收到 "end" 时自动关闭连接
   *   5. 8 秒超时保护：如果服务端无响应，强制关闭（只关闭本次 WS）
   *
   * 特别注意：
   *   超时 setTimeout 中必须用局部变量捕获具体的 WS 实例，
   *   不能直接使用 wsRef.current，因为重新录音时 wsRef 会被覆盖，
   *   导致旧超时关闭了新的 WebSocket。
   */
  const stopListening = useCallback(() => {
    // 停止 MediaRecorder
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }

    // 释放麦克风
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    // 发送 stop 命令，但不立即关闭 WS（等待服务端回 final + end）
    if (wsRef.current) {
      try {
        wsRef.current.send(JSON.stringify({ type: 'stop' }));
      } catch {
        // WS 已关闭，忽略发送错误
      }
    }

    // 停止 Web Speech API
    if ((window as any)._speechRecognition) {
      try {
        (window as any)._speechRecognition.stop();
      } catch { /* ignore */ }
      (window as any)._speechRecognition = null;
    }

    setIsListening(false);
    setUseWebSocket(false);

    // 超时保护：捕获当前 WS 实例，避免在重新录音后误关新连接
    // LLM 纠错可能耗时 20s+，所以超时设 60s
    const wsToClose = wsRef.current;
    setTimeout(() => {
      if (wsToClose && wsToClose.readyState === WebSocket.OPEN) {
        wsToClose.close();
      }
    }, 60000);
  }, []);

  /**
   * 重置
   */
  const resetTranscript = useCallback(() => {
    setTranscript('');
    setInterimTranscript('');
  }, []);

  // 清理
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    isListening,
    transcript,
    interimTranscript,
    isSupported,
    error,
    startListening,
    stopListening,
    resetTranscript,
    useWebSocket,
  };
}
