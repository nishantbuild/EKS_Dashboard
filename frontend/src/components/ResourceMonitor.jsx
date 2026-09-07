import { useEffect, useState } from 'react'
import { api } from '../api'

export default function ResourceMonitor({ namespace }) {
  const [metrics, setMetrics] = useState([])
  const [collapsed, setCollapsed] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const load = () => {
      api
        .podMetrics(namespace)
        .then((m) => !cancelled && setMetrics(m))
        .catch((err) => !cancelled && setError(err.message))
    }
    load()
    const id = setInterval(load, 5000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [namespace])

  const totalCpu = metrics.reduce((sum, m) => sum + m.cpu_millicores, 0)
  const totalMem = metrics.reduce((sum, m) => sum + m.memory_mib, 0)

  return (
    <footer className={`resource-monitor ${collapsed ? 'collapsed' : ''}`}>
      <div className="resource-monitor-header" onClick={() => setCollapsed((c) => !c)}>
        <span className="dot" />
        <span>
          top — {namespace} · {metrics.length} pod{metrics.length === 1 ? '' : 's'} · CPU{' '}
          {totalCpu.toFixed(0)}m · MEM {totalMem.toFixed(0)}Mi
        </span>
        <span className="toggle">{collapsed ? '▲ expand' : '▼ collapse'}</span>
      </div>
      {!collapsed && (
        <div className="resource-monitor-body">
          {error && <p className="error">{error}</p>}
          {!error && metrics.length === 0 && (
            <p className="muted">No metrics yet (metrics-server may still be warming up).</p>
          )}
          {!error && metrics.length > 0 && (
            <table className="metrics-table">
              <thead>
                <tr>
                  <th>Pod</th>
                  <th>CPU (m)</th>
                  <th>Memory (Mi)</th>
                </tr>
              </thead>
              <tbody>
                {metrics.map((m) => (
                  <tr key={m.name}>
                    <td>{m.name}</td>
                    <td>
                      <div className="bar-cell">
                        <span>{m.cpu_millicores}</span>
                        <div className="bar">
                          <div
                            className="bar-fill cpu"
                            style={{ width: `${Math.min(100, m.cpu_millicores / 10)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td>
                      <div className="bar-cell">
                        <span>{m.memory_mib}</span>
                        <div className="bar">
                          <div
                            className="bar-fill mem"
                            style={{ width: `${Math.min(100, m.memory_mib / 5)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </footer>
  )
}
