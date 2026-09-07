import { useEffect, useRef } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { wsExecUrl } from '../api'

export default function PodTerminal({ namespace, podName, onClose }) {
  const containerRef = useRef(null)

  useEffect(() => {
    const term = new Terminal({
      convertEol: true,
      cursorBlink: true,
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
      fontSize: 13,
      theme: { background: '#0b0f14' },
    })
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    term.open(containerRef.current)
    fitAddon.fit()
    term.writeln(`Connecting to ${podName} in ${namespace}...`)

    const ws = new WebSocket(wsExecUrl(namespace, podName))

    ws.onopen = () => term.writeln('Connected. Type your commands below.\r\n')
    ws.onmessage = (event) => term.write(event.data)
    ws.onerror = () => term.writeln('\r\n[connection error]')
    ws.onclose = () => term.writeln('\r\n[session closed]')

    const onData = term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(data)
    })

    const onResize = () => fitAddon.fit()
    window.addEventListener('resize', onResize)

    return () => {
      onData.dispose()
      window.removeEventListener('resize', onResize)
      ws.close()
      term.dispose()
    }
  }, [namespace, podName])

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal terminal-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>
            <span className="dot" /> Terminal: {podName}
          </h3>
          <button onClick={onClose}>Close</button>
        </div>
        <div className="xterm-container" ref={containerRef} />
      </div>
    </div>
  )
}
