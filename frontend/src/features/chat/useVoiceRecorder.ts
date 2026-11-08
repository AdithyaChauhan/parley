import { useEffect, useRef, useState } from "react"
import { MAX_VOICE_MS, type PreparedFile } from "@/lib/files"

// Which formats to ask for, in order. mp4 first: every browser can play it,
// including iPhone Safari, which records nothing else. Chrome records it too.
const FORMATS = ["audio/mp4", "audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"]
const EXTENSIONS: Record<string, string> = { "audio/mp4": "m4a", "audio/webm": "webm", "audio/ogg": "ogg" }

const SHORTEST_MS = 700 // shorter than this is a tap, not a recording

// Voice notes need a secure page (https or localhost) and a browser that can record.
export const canRecord = () =>
  typeof MediaRecorder !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia)

// Hold to record, let go to send. Also stops and sends by itself at 2 minutes.
export function useVoiceRecorder(onDone: (voice: PreparedFile) => void, onHint: (text: string) => void) {
  const [recording, setRecording] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const held = useRef(false) // the button is still being held
  const recorder = useRef<MediaRecorder | null>(null)
  const startedAt = useRef(0)
  const keep = useRef(true) // false: throw this recording away
  const timer = useRef<number | undefined>(undefined)

  function finish(send: boolean) {
    held.current = false
    keep.current = send
    window.clearInterval(timer.current)
    if (recorder.current?.state === "recording") recorder.current.stop()
    setRecording(false)
    setElapsed(0)
  }

  async function start() {
    held.current = true
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      held.current = false
      onHint("Parley needs your microphone for voice notes")
      return
    }
    // The first time, the browser's permission question takes the press: let go happened meanwhile
    if (!held.current) {
      stream.getTracks().forEach((track) => track.stop())
      onHint("Hold the button to record")
      return
    }

    const format = FORMATS.find((candidate) => MediaRecorder.isTypeSupported(candidate))
    const media = new MediaRecorder(stream, format ? { mimeType: format } : undefined)
    const chunks: Blob[] = []
    media.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data)
    }
    media.onstop = () => {
      stream.getTracks().forEach((track) => track.stop())
      const durationMs = Math.min(Date.now() - startedAt.current, MAX_VOICE_MS)
      if (!keep.current) return
      if (durationMs < SHORTEST_MS || chunks.length === 0) {
        onHint("Hold the button to record")
        return
      }
      // "audio/webm;codecs=opus" is sent as plain "audio/webm", the name the server allows
      const type = (media.mimeType || format || "audio/webm").split(";")[0]
      onDone({
        blob: new Blob(chunks, { type }),
        name: `voice-note.${EXTENSIONS[type] ?? "webm"}`,
        type,
        category: "voice",
        durationMs,
      })
    }
    recorder.current = media
    keep.current = true
    startedAt.current = Date.now()
    media.start(250)
    setRecording(true)
    timer.current = window.setInterval(() => {
      const now = Date.now() - startedAt.current
      setElapsed(now)
      if (now >= MAX_VOICE_MS) finish(true)
    }, 200)
  }

  // Leaving the screen throws away a recording in progress
  useEffect(
    () => () => {
      keep.current = false
      held.current = false
      window.clearInterval(timer.current)
      if (recorder.current?.state === "recording") recorder.current.stop()
    },
    [],
  )

  return { recording, elapsed, start, stop: () => finish(true), cancel: () => finish(false) }
}
