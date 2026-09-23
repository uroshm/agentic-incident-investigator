import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Link, Navigate, NavLink, Route, Routes, useParams } from 'react-router-dom'
import './styles.css'

const api = async (path, options) => {
  const response = await fetch(path, options)
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail || body.error || response.statusText)
  return body
}

const formatDate = (value) => value
  ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
  : 'Date unavailable'

function StatusPill({ status }) {
  return <span className={`pill ${status.toLowerCase()}`}><i />{status}</span>
}

function InvestigationCard({ run }) {
  const result = run.result
  const recommendations = result?.recommendations || []
  return <article className="investigation-card">
    <div className="card-topline"><div><div className="eyebrow">{run.service} {run.model && `· ${run.model}`}</div><h3>{run.incident}</h3></div><StatusPill status={run.status} /></div>
    {run.status === 'RUNNING' && <div className="progress"><span /></div>}
    {run.status === 'FAILED' && <div className="error-box">{run.error}</div>}
    {result && <>
      <div className="result-summary"><div><span className="label">Root cause</span><strong>{result.rootCause}</strong></div><div><span className="label">Confidence</span><strong>{Math.round(result.confidence * 100)}%</strong></div><div><span className="label">Evidence</span><strong>{result.evidence?.length || 0} sources</strong></div></div>
      <details><summary>View investigation detail</summary><div className="detail-grid"><div><h4>Evidence</h4><ul>{(result.evidence || []).map((item, index) => <li key={index}><b>{item.source}</b><span>{item.finding}</span></li>)}</ul></div><div><h4>Recommendations</h4><ul>{recommendations.length ? recommendations.map((item, index) => <li key={index}><b>{item.action}</b><span>{item.reason}</span></li>) : <li><span>No recommendations returned.</span></li>}</ul></div></div>{result.investigationId && <a className="trace-link" href={`/investigations/${result.investigationId}/trace`} target="_blank" rel="noreferrer">Open model and tool trace ↗</a>}</details>
    </>}
  </article>
}

function ReportCard({ report, detailBase = '/console/investigations' }) {
  return <Link className="history-card" to={`${detailBase}/${report.investigationId}`}>
    <div className="card-topline"><div><div className="eyebrow">{report.service} · Report #{report.investigationId}</div><h3>{report.incident}</h3></div><span className="history-date">{formatDate(report.createdAt)}</span></div>
    <p className="history-root-cause">{report.rootCause}</p>
    <div className="history-meta"><span>{Math.round(report.confidence * 100)}% confidence</span><span>{report.evidenceCount ?? report.evidence?.length ?? 0} evidence items</span><span>{report.recommendationCount ?? report.recommendations?.length ?? 0} recommendations</span><b>View report →</b></div>
  </Link>
}

function ReportList({ history, loading, detailBase }) {
  if (loading) return <div className="empty">Loading investigation history…</div>
  if (!history.length) return <div className="empty"><div className="empty-icon">▤</div><b>No historic reports</b><span>Completed investigations will appear here.</span></div>
  return <div className="history-list">{history.map((report) => <ReportCard report={report} detailBase={detailBase} key={report.investigationId} />)}</div>
}

function Sidebar() {
  return <aside className="sidebar">
    <div className="brand"><div className="brand-mark">✦</div><div><b>Signal</b><span>Incident console</span></div></div>
    <nav>
      <NavLink to="/" end><span>◈</span>Overview</NavLink>
      <NavLink to="/console/investigations"><span>⌁</span>Investigations</NavLink>
      <NavLink to="/console/reports"><span>▤</span>Reports</NavLink>
    </nav>
    <div className="sidebar-footer"><div className="system-dot" /><div><b>Local environment</b><span>Ollama connected</span></div></div>
  </aside>
}

function PageHeader({ section, title, description }) {
  return <header className="topbar"><div><div className="eyebrow">Operations / {section}</div><h1>{title}</h1><p>{description}</p></div></header>
}

function OverviewPage({ runningCount, completedCount }) {
  return <>
    <PageHeader section="Overview" title="Incident command center" description="Monitor the current state of incident operations." />
    <section className="stats"><Link to="/console/investigations"><span className="stat-icon blue">◉</span><span className="label">Active investigations</span><strong>{runningCount}</strong></Link><Link to="/console/reports"><span className="stat-icon purple">⌁</span><span className="label">Completed reports</span><strong>{completedCount}</strong></Link></section>
  </>
}

function InvestigationsPage({ availableModels, description, downloadModel, history, loading, model, models, pullJob, pullModel, runs, service, setDescription, setDownloadModel, setModel, setService, submit, submitting }) {
  return <>
    <PageHeader section="Investigations" title="Investigations" description="Start investigations and follow model-driven incident analysis in real time." />
    <section className="model-bar"><div><div className="eyebrow">Local model library</div><h2>Ollama models</h2><p>Download approved models into the configured Ollama runtime.</p></div><div className="model-actions"><select value={downloadModel} onChange={(event) => setDownloadModel(event.target.value)}><option value="">Choose a model</option>{availableModels.filter((name) => !models.includes(name)).map((name) => <option key={name} value={name}>{name}</option>)}</select><button onClick={pullModel} disabled={!downloadModel || (pullJob && !['completed', 'failed'].includes(pullJob.status))}>⬇ Download</button></div>{pullJob && <div className={`pull-status ${pullJob.status === 'failed' ? 'error' : ''}`}><b>{pullJob.model}</b><span>{pullJob.status}</span>{pullJob.total ? <span>{Math.round((pullJob.completed / pullJob.total) * 100)}%</span> : null}</div>}</section>
    <section className="workspace"><div className="section-heading"><div><h2>Live investigations</h2><p>Real-time model-driven incident analysis</p></div><span className="live-indicator"><i />Live updates</span></div><form className="start-form" onSubmit={submit}><div><label>Service</label><input value={service} onChange={(event) => setService(event.target.value)} /></div><div className="wide"><label>Incident description</label><input value={description} onChange={(event) => setDescription(event.target.value)} /></div><div><label>Local model</label><select value={model} onChange={(event) => setModel(event.target.value)} disabled={!models.length}><option value="">No models found</option>{models.map((name) => <option key={name} value={name}>{name}</option>)}</select></div><button disabled={submitting || !model}>{submitting ? 'Starting…' : 'Start investigation'} <span>→</span></button></form>{loading ? <div className="empty">Loading investigations…</div> : runs.length ? <div className="investigation-list">{runs.map((run) => <InvestigationCard run={run} key={run.id} />)}</div> : <div className="empty"><div className="empty-icon">⌁</div><b>No active investigations</b><span>Start an investigation above to watch the agent work.</span></div>}</section>
    <section className="workspace"><div className="section-heading"><div><h2>Investigation history</h2><p>Completed investigations stored in the database</p></div><span className="count">{history.length} total</span></div><ReportList history={history} loading={loading} detailBase="/console/investigations" /></section>
  </>
}

function ReportsPage({ history, loading }) {
  return <>
    <PageHeader section="Reports" title="Previous reports" description="Review completed incident reports stored in the database." />
    <section className="workspace"><div className="section-heading"><div><h2>Historic reports</h2><p>Persisted diagnoses, evidence, and recommendations</p></div><span className="count">{history.length} total</span></div><ReportList history={history} loading={loading} detailBase="/console/reports" /></section>
  </>
}

function ReportDetailPage({ backTo }) {
  const { investigationId } = useParams()
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    api(`/investigations/${investigationId}`)
      .then((response) => { if (active) setReport(response.investigation) })
      .catch((err) => { if (active) setError(err.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [investigationId])

  if (loading) return <><PageHeader section="Reports" title="Loading report…" description="Reading persisted investigation data." /><div className="empty">Loading historic report…</div></>
  if (error || !report) return <><PageHeader section="Reports" title="Report unavailable" description="The requested persisted investigation could not be loaded." /><div className="alert">{error || 'Investigation not found'}</div><Link className="back-link" to={backTo}>← Back to history</Link></>

  return <>
    <PageHeader section="Reports" title={`Report #${report.investigationId}`} description={report.incident} />
    <Link className="back-link" to={backTo}>← Back to history</Link>
    <section className="workspace report-detail">
      <div className="card-topline"><div><div className="eyebrow">{report.service} · {formatDate(report.createdAt)}</div><h2>Investigation report</h2></div><StatusPill status={report.status || 'COMPLETED'} /></div>
      <div className="result-summary"><div><span className="label">Root cause</span><strong>{report.rootCause}</strong></div><div><span className="label">Confidence</span><strong>{Math.round(report.confidence * 100)}%</strong></div><div><span className="label">Started</span><strong>{formatDate(report.startedAt)}</strong></div></div>
      <div className="detail-grid report-sections"><div><h4>Evidence</h4><ul>{report.evidence.length ? report.evidence.map((item, index) => <li key={index}><b>{item.source}</b><span>{item.finding}</span><small>Collected via {item.tool}{item.collectedAt ? ` · ${formatDate(item.collectedAt)}` : ''}</small></li>) : <li><span>No evidence was stored for this investigation.</span></li>}</ul></div><div><h4>Recommendations</h4><ul>{report.recommendations.length ? report.recommendations.map((item, index) => <li key={index}><b>{item.action}</b><span>{item.reason}</span><small>{item.requiresApproval ? 'Approval required' : 'No approval required'}</small></li>) : <li><span>No recommendations were stored for this investigation.</span></li>}</ul></div></div>
      <a className="trace-link" href={`/investigations/${report.investigationId}/trace`} target="_blank" rel="noreferrer">Open model and tool trace ↗</a>
    </section>
  </>
}

function App() {
  const [runs, setRuns] = useState([])
  const [history, setHistory] = useState([])
  const [service, setService] = useState('checkout-service')
  const [description, setDescription] = useState('HTTP 500 errors after deployment 184')
  const [models, setModels] = useState([])
  const [availableModels, setAvailableModels] = useState([])
  const [model, setModel] = useState('')
  const [downloadModel, setDownloadModel] = useState('')
  const [pullJob, setPullJob] = useState(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const loadData = async () => {
    try {
      const [liveResponse, historyResponse, modelResponse] = await Promise.all([api('/investigations/live'), api('/investigations'), api('/api/models')])
      setRuns(liveResponse.investigations)
      setHistory(historyResponse.investigations)
      setModels(modelResponse.models)
      setAvailableModels(modelResponse.available || [])
      setModel((current) => current || modelResponse.default || modelResponse.models[0] || '')
      setError('')
    } catch (err) { setError(err.message) } finally { setLoading(false) }
  }

  useEffect(() => { loadData(); const timer = setInterval(loadData, 2000); return () => clearInterval(timer) }, [])

  useEffect(() => {
    if (!pullJob || ['completed', 'failed'].includes(pullJob.status)) return undefined
    const timer = setInterval(async () => {
      try { setPullJob(await api(`/api/models/pull/${pullJob.id}`)); await loadData() }
      catch (err) { setError(err.message) }
    }, 1000)
    return () => clearInterval(timer)
  }, [pullJob])

  const submit = async (event) => {
    event.preventDefault(); setSubmitting(true); setError('')
    try { await api('/investigate/async', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ service, description, model }) }); await loadData() }
    catch (err) { setError(err.message) } finally { setSubmitting(false) }
  }

  const pullModel = async () => {
    if (!downloadModel) return
    try { setPullJob(await api('/api/models/pull', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model: downloadModel }) })) }
    catch (err) { setError(err.message) }
  }

  const runningCount = runs.filter((run) => run.status === 'RUNNING').length
  const completedCount = history.length
  const visibleRuns = useMemo(() => [...runs].reverse(), [runs])

  return <div className="shell"><Sidebar />
    <main className="main">
      {error && <div className="alert">{error}</div>}
      <Routes>
        <Route path="/" element={<OverviewPage runningCount={runningCount} completedCount={completedCount} />} />
        <Route path="/console/investigations" element={<InvestigationsPage availableModels={availableModels} description={description} downloadModel={downloadModel} history={history} loading={loading} model={model} models={models} pullJob={pullJob} pullModel={pullModel} runs={visibleRuns} service={service} setDescription={setDescription} setDownloadModel={setDownloadModel} setModel={setModel} setService={setService} submit={submit} submitting={submitting} />} />
        <Route path="/console/investigations/:investigationId" element={<ReportDetailPage backTo="/console/investigations" />} />
        <Route path="/console/reports" element={<ReportsPage history={history} loading={loading} />} />
        <Route path="/console/reports/:investigationId" element={<ReportDetailPage backTo="/console/reports" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </main></div>
}

createRoot(document.getElementById('root')).render(<BrowserRouter><App /></BrowserRouter>)
