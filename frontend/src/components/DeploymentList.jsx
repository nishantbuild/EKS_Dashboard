import { useEffect, useState } from 'react'
import { api } from '../api'

export default function DeploymentList({ namespace }) {
  const [deployments, setDeployments] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(null)

  const load = () => {
    api
      .deployments(namespace)
      .then(setDeployments)
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    setError('')
    load()
    const id = setInterval(load, 10000)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [namespace])

  const scale = async (name) => {
    const value = prompt(`Scale "${name}" to how many replicas?`)
    if (value === null) return
    const replicas = Number(value)
    if (!Number.isInteger(replicas) || replicas < 0 || replicas > 100) {
      alert('Enter a whole number between 0 and 100')
      return
    }
    setBusy(name)
    try {
      await api.scaleDeployment(namespace, name, replicas)
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(null)
    }
  }

  const restart = async (name) => {
    if (!confirm(`Restart deployment "${name}"?`)) return
    setBusy(name)
    try {
      await api.restartDeployment(namespace, name)
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
          <th>Replicas</th>
          <th>Available</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {deployments.map((d) => (
          <tr key={d.name}>
            <td>{d.name}</td>
            <td>{d.replicas}</td>
            <td>{d.available}</td>
            <td className="actions">
              <button disabled={busy === d.name} onClick={() => scale(d.name)}>
                Scale
              </button>
              <button disabled={busy === d.name} onClick={() => restart(d.name)}>
                Restart
              </button>
            </td>
          </tr>
        ))}
        {deployments.length === 0 && (
          <tr>
            <td colSpan={4}>No deployments in this namespace.</td>
          </tr>
        )}
      </tbody>
    </table>
  )
}
