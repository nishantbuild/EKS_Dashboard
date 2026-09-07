import { useEffect, useRef, useState } from 'react'
import { wsLogUrl } from '../api'

export default function LogsViewer({ namespace, podName, onClose }) {
  const [lines, setLines] = useState([])
  const boxRef = useRef(null)

  useEffect(() => {
    const ws = new WebSocket(wsLogUrl(namespace, podName))
    ws.onmessage = (event) => {
      setLines((prev) => [...prev.slice(-999), event.data])
    }
    ws.onerror = () => setLines((prev) => [...prev, '[connection error]'])
    return () => ws.close()
  }, [namespace, podName])

  useEffect(() => {
    boxRef.current?.scrollTo(0, boxRef.current.scrollHeight)
  }, [lines])

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal logs-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Logs: {podName}</h3>
          <button onClick={onClose}>Close</button>
        </div>
        <pre className="logs-box" ref={boxRef}>
          {lines.join('\n')}
        </pre>
      </div>
    </div>
  )
}
