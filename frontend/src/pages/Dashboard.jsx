import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../AuthContext'
import PodList from '../components/PodList'
import DeploymentList from '../components/DeploymentList'
import LogsViewer from '../components/LogsViewer'
import PodTerminal from '../components/PodTerminal'
import AuditLog from '../components/AuditLog'
import ResourceMonitor from '../components/ResourceMonitor'

const TABS = ['Pods', 'Deployments', 'Audit']

export default function Dashboard() {
  const { user, logout } = useAuth()
  const [namespaces, setNamespaces] = useState([])
  const [namespace, setNamespace] = useState('')
  const [tab, setTab] = useState('Pods')
  const [logsFor, setLogsFor] = useState(null)
  const [terminalFor, setTerminalFor] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .namespaces()
      .then((ns) => {
        setNamespaces(ns)
        if (ns.length) setNamespace(ns[0])
      })
      .catch((err) => setError(err.message))
  }, [])

  const isAdmin = user?.groups?.includes('admins')

  return (
    <div className="dashboard">
      <header className="topbar">
        <h1>
          <span className="prompt">$</span> eks-dashboard
        </h1>
        <div className="topbar-right">
          <span className="user-chip">{user?.email}</span>
          <button onClick={logout}>Sign out</button>
        </div>
      </header>

      <div className="dashboard-body">
        <aside className="sidebar">
          <div className="sidebar-title">Namespaces</div>
          <ul className="namespace-list">
            {namespaces.map((ns) => (
              <li key={ns}>
                <button
                  className={ns === namespace ? 'active' : ''}
                  onClick={() => setNamespace(ns)}
                >
                  {ns}
                </button>
              </li>
            ))}
            {namespaces.length === 0 && !error && <li className="muted">Loading…</li>}
          </ul>
        </aside>

        <div className="dashboard-main">
          <nav className="tabs">
            {TABS.filter((t) => t !== 'Audit' || isAdmin).map((t) => (
              <button key={t} className={t === tab ? 'active' : ''} onClick={() => setTab(t)}>
                {t}
              </button>
            ))}
          </nav>

          <main className="content">
            {error && <p className="error">{error}</p>}
            {!error && !namespace && <p>No namespaces available for your account.</p>}
            {namespace && tab === 'Pods' && (
              <PodList
                namespace={namespace}
                onViewLogs={setLogsFor}
                onOpenTerminal={setTerminalFor}
                canExec={isAdmin}
              />
            )}
            {namespace && tab === 'Deployments' && <DeploymentList namespace={namespace} />}
            {tab === 'Audit' && isAdmin && <AuditLog />}
          </main>

          {namespace && <ResourceMonitor namespace={namespace} />}
        </div>
      </div>

      {logsFor && (
        <LogsViewer namespace={namespace} podName={logsFor} onClose={() => setLogsFor(null)} />
      )}
      {terminalFor && (
        <PodTerminal namespace={namespace} podName={terminalFor} onClose={() => setTerminalFor(null)} />
      )}
    </div>
  )
}
