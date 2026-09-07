import { useEffect, useState } from 'react'
import { api } from '../api'

export default function PodList({ namespace, onViewLogs, onOpenTerminal, canExec }) {
  const [pods, setPods] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(null)

  const load = () => {
    api
      .pods(namespace)
      .then(setPods)
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    setError('')
    load()
    const id = setInterval(load, 10000)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [namespace])

  const remove = async (name) => {
    if (!confirm(`Delete pod "${name}"? It will be recreated if managed by a controller.`)) return
    setBusy(name)
    try {
      await api.deletePod(namespace, name)
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(null)
    }
  }

  if (error) return <p className="error">{error}</p>

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Status</th>
          <th>Restarts</th>
          <th>Node</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {pods.map((p) => (
          <tr key={p.name}>
            <td>{p.name}</td>
            <td>
              <span className={`badge badge-${p.status?.toLowerCase()}`}>{p.status}</span>
            </td>
            <td>{p.restarts}</td>
            <td>{p.node}</td>
            <td className="actions">
              <button onClick={() => onViewLogs(p.name)}>Logs</button>
              {canExec && <button onClick={() => onOpenTerminal(p.name)}>Terminal</button>}
              <button className="danger" disabled={busy === p.name} onClick={() => remove(p.name)}>
                {busy === p.name ? 'Deleting…' : 'Delete'}
              </button>
            </td>
          </tr>
        ))}
        {pods.length === 0 && (
          <tr>
            <td colSpan={5}>No pods in this namespace.</td>
          </tr>
        )}
      </tbody>
    </table>
  )
}
