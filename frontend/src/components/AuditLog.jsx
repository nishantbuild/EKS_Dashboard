import { useEffect, useState } from 'react'
import { api } from '../api'

export default function AuditLog() {
  const [entries, setEntries] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .audit()
      .then(setEntries)
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="error">{error}</p>

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Time</th>
          <th>User</th>
          <th>Action</th>
          <th>Params</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((e, i) => (
          <tr key={i}>
            <td>{e.ts}</td>
            <td>{e.user}</td>
            <td>{e.action}</td>
            <td>{JSON.stringify(e.params)}</td>
            <td>
              <span className={`badge badge-${e.status}`}>{e.status}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
