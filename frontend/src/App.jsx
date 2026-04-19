import { useState, useEffect, useCallback, useRef } from 'react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts'
import {
  getDashboardStats, getTimeline, getRiskDistribution,
  listTransactions, listAlerts, submitTransaction, quickCheck
} from './api/client.js'
import { useWebSocket } from './hooks/useWebSocket.js'

// ─── Supported Currencies ────────────────────────────────────────────────────
const CURRENCIES = [
  { code: 'KES', name: 'Kenyan Shilling', symbol: 'KSh', country: '🇰🇪' },
  { code: 'UGX', name: 'Ugandan Shilling', symbol: 'USh', country: '🇺🇬' },
  { code: 'TZS', name: 'Tanzanian Shilling', symbol: 'TSh', country: '🇹🇿' },
  { code: 'ZMW', name: 'Zambian Kwacha', symbol: 'ZK', country: '🇿🇲' },
  { code: 'GHS', name: 'Ghanaian Cedi', symbol: 'GH₵', country: '🇬🇭' },
  { code: 'NGN', name: 'Nigerian Naira', symbol: '₦', country: '🇳🇬' },
  { code: 'ZAR', name: 'South African Rand', symbol: 'R', country: '🇿🇦' },
  { code: 'RWF', name: 'Rwandan Franc', symbol: 'RF', country: '🇷🇼' },
  { code: 'MWK', name: 'Malawian Kwacha', symbol: 'MK', country: '🇲🇼' },
  { code: 'ETB', name: 'Ethiopian Birr', symbol: 'Br', country: '🇪🇹' },
  { code: 'XOF', name: 'West African Franc', symbol: 'CFA', country: '🌍' },
  { code: 'USD', name: 'US Dollar', symbol: '$', country: '🇺🇸' },
  { code: 'EUR', name: 'Euro', symbol: '€', country: '🇪🇺' },
  { code: 'GBP', name: 'British Pound', symbol: '£', country: '🇬🇧' },
]

const getCurrencySymbol = (code) =>
  CURRENCIES.find(c => c.code === code)?.symbol || code

// ─── Helpers ─────────────────────────────────────────────────────────────────
const riskColor = (score) => {
  if (score >= 75) return 'text-red-400'
  if (score >= 50) return 'text-orange-400'
  if (score >= 26) return 'text-yellow-400'
  return 'text-green-400'
}

const statusBadge = (status) => {
  const map = {
    approved:  'bg-green-900 text-green-300 border border-green-700',
    blocked:   'bg-red-900 text-red-300 border border-red-700',
    flagged:   'bg-yellow-900 text-yellow-300 border border-yellow-700',
    pending:   'bg-gray-800 text-gray-300 border border-gray-600',
  }
  return `px-2 py-0.5 rounded text-xs font-semibold ${map[status] || map.pending}`
}

const riskBadge = (level) => {
  const map = {
    low:      'bg-green-900 text-green-300',
    medium:   'bg-yellow-900 text-yellow-300',
    high:     'bg-orange-900 text-orange-300',
    critical: 'bg-red-900 text-red-300',
  }
  return `px-2 py-0.5 rounded text-xs font-bold uppercase ${map[level] || map.low}`
}

const fmt = (n, currency = '') => {
  const sym = currency ? getCurrencySymbol(currency) : ''
  return `${sym}${Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

const fmtTime = (iso) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// ─── KPI Card ────────────────────────────────────────────────────────────────
function KpiCard({ label, value, sub, color = 'text-white', icon }) {
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
      <div className="flex items-center justify-between mb-1">
        <span className="text-gray-400 text-xs font-medium uppercase tracking-wider">{label}</span>
        {icon && <span className="text-xl">{icon}</span>}
      </div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      {sub && <div className="text-gray-500 text-xs mt-1">{sub}</div>}
    </div>
  )
}

// ─── Agent Portal (Transaction Form) ─────────────────────────────────────────
function AgentPortal({ onTxnComplete }) {
  const [form, setForm] = useState({
    phone_number: '', amount: '', currency: 'KES',
    transaction_type: 'send', recipient: '', agent_id: ''
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const submit = async () => {
    setError(''); setResult(null); setLoading(true)
    try {
      const res = await submitTransaction({
        phone_number: form.phone_number.trim(),
        amount: parseFloat(form.amount),
        currency: form.currency,
        transaction_type: form.transaction_type,
        recipient: form.recipient.trim() || undefined,
        agent_id: form.agent_id.trim() || undefined,
      })
      setResult(res.data)
      onTxnComplete?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const decisionStyle = {
    BLOCK:          'border-red-500 bg-red-950',
    APPROVE:        'border-green-500 bg-green-950',
    FLAG_FOR_REVIEW:'border-yellow-500 bg-yellow-950',
  }

  const sym = getCurrencySymbol(form.currency)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Form */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
          <span>📱</span> Agent Transaction Check
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Customer Phone (E.164)</label>
            <input
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              placeholder="+254712345678"
              value={form.phone_number}
              onChange={e => set('phone_number', e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Amount</label>
              <div className="relative">
                <span className="absolute left-3 top-2 text-gray-400 text-sm">{sym}</span>
                <input
                  type="number"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-8 pr-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  placeholder="0.00"
                  value={form.amount}
                  onChange={e => set('amount', e.target.value)}
                  min="0"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-gray-400 mb-1">Currency</label>
              <select
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                value={form.currency}
                onChange={e => set('currency', e.target.value)}
              >
                {CURRENCIES.map(c => (
                  <option key={c.code} value={c.code}>
                    {c.country} {c.code} — {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">Transaction Type</label>
            <select
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              value={form.transaction_type}
              onChange={e => set('transaction_type', e.target.value)}
            >
              <option value="send">Send Money</option>
              <option value="receive">Receive Money</option>
              <option value="withdraw">Withdraw</option>
              <option value="deposit">Deposit</option>
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">Recipient (optional)</label>
            <input
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              placeholder="Recipient name or account"
              value={form.recipient}
              onChange={e => set('recipient', e.target.value)}
              maxLength={100}
            />
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">Agent ID (optional)</label>
            <input
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              placeholder="Your agent ID"
              value={form.agent_id}
              onChange={e => set('agent_id', e.target.value)}
              maxLength={50}
            />
          </div>

          {error && (
            <div className="bg-red-950 border border-red-700 rounded-lg px-3 py-2 text-sm text-red-300">
              ⚠ {error}
            </div>
          )}

          <button
            onClick={submit}
            disabled={loading || !form.phone_number || !form.amount}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg transition-colors"
          >
            {loading ? '🔍 Checking...' : '🛡 Check Transaction'}
          </button>

          {/* Demo numbers */}
          <div className="text-xs text-gray-500 mt-2 space-y-1">
            <div className="font-medium text-gray-400">Demo test numbers:</div>
            <div
              className="cursor-pointer hover:text-blue-400"
              onClick={() => set('phone_number', '+99999991000')}
            >
              ↳ +99999991000 — SIM swap detected (BLOCK)
            </div>
            <div
              className="cursor-pointer hover:text-blue-400"
              onClick={() => set('phone_number', '+99999991001')}
            >
              ↳ +99999991001 — Clean (APPROVE)
            </div>
            <div
              className="cursor-pointer hover:text-blue-400"
              onClick={() => set('phone_number', '+99999991002')}
            >
              ↳ +99999991002 — Device swap (FLAG)
            </div>
          </div>
        </div>
      </div>

      {/* Result */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-bold mb-4">Fraud Analysis Result</h2>

        {!result && !loading && (
          <div className="flex flex-col items-center justify-center h-48 text-gray-600">
            <span className="text-4xl mb-3">🛡</span>
            <p>Submit a transaction to see the AI fraud analysis</p>
          </div>
        )}

        {loading && (
          <div className="flex flex-col items-center justify-center h-48 text-gray-400">
            <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-3" />
            <p>Running CAMARA checks + AI analysis...</p>
          </div>
        )}

        {result && (
          <div className={`border-2 rounded-xl p-5 space-y-4 ${decisionStyle[result.ai_decision] || 'border-gray-600 bg-gray-800'}`}>
            {/* Decision banner */}
            <div className="text-center">
              <div className="text-4xl mb-1">
                {result.ai_decision === 'BLOCK' ? '🚫' :
                 result.ai_decision === 'APPROVE' ? '✅' : '⚠️'}
              </div>
              <div className="text-2xl font-black">{result.ai_decision?.replace('_', ' ')}</div>
              <div className="text-sm text-gray-300 mt-1">{result.ai_explanation}</div>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="bg-black/20 rounded-lg p-2">
                <div className={`text-xl font-bold ${riskColor(result.risk_score)}`}>{result.risk_score}</div>
                <div className="text-xs text-gray-400">Risk Score</div>
              </div>
              <div className="bg-black/20 rounded-lg p-2">
                <div className="text-xl font-bold">{fmt(result.amount, result.currency)}</div>
                <div className="text-xs text-gray-400">{result.currency} Amount</div>
              </div>
              <div className="bg-black/20 rounded-lg p-2">
                <div className="text-sm font-bold capitalize">{result.status}</div>
                <div className="text-xs text-gray-400">Status</div>
              </div>
            </div>

            {/* CAMARA results */}
            {result.camara_results && (
              <div>
                <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">CAMARA API Results</div>
                <div className="space-y-1 text-sm">
                  <CamaraRow
                    label="SIM Swap (24h)"
                    result={result.camara_results.sim_swap_24h}
                  />
                  <CamaraRow
                    label="SIM Swap (7d)"
                    result={result.camara_results.sim_swap_7d}
                  />
                  <CamaraRow
                    label="Device Swap"
                    result={result.camara_results.device_swap}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function CamaraRow({ label, result }) {
  if (!result) return null
  const bad = result.swapped
  return (
    <div className="flex items-center justify-between bg-black/20 rounded px-3 py-1.5">
      <span className="text-gray-300">{label}</span>
      <div className="flex items-center gap-2">
        {result.swap_date && <span className="text-xs text-gray-500">{result.swap_date.slice(0, 10)}</span>}
        <span className={`font-semibold ${bad ? 'text-red-400' : 'text-green-400'}`}>
          {bad ? '⚠ DETECTED' : '✓ CLEAR'}
        </span>
        {result.source === 'simulation' && (
          <span className="text-xs bg-gray-700 text-gray-400 px-1 rounded">sim</span>
        )}
      </div>
    </div>
  )
}

// ─── Live Feed (Transaction list) ────────────────────────────────────────────
function LiveFeed({ liveTransactions }) {
  const [dbTransactions, setDbTransactions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listTransactions({ limit: 40 })
      .then(r => setDbTransactions(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  // Merge live WS transactions with DB transactions, dedup by id
  const all = [...liveTransactions, ...dbTransactions]
  const seen = new Set()
  const merged = all.filter(t => {
    if (seen.has(t.id)) return false
    seen.add(t.id); return true
  }).slice(0, 60)

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800">
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
        <h2 className="font-bold">Live Transaction Feed</h2>
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span className="w-2 h-2 rounded-full bg-green-400 live-dot" />
          Real-time
        </div>
      </div>
      <div className="overflow-auto max-h-96">
        {loading && (
          <div className="text-center py-8 text-gray-500">Loading...</div>
        )}
        {!loading && merged.length === 0 && (
          <div className="text-center py-8 text-gray-500">No transactions yet — submit one from the Agent Portal</div>
        )}
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-gray-900">
            <tr className="text-left text-xs text-gray-500 uppercase tracking-wider border-b border-gray-800">
              <th className="px-4 py-2">Phone</th>
              <th className="px-4 py-2">Amount</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Risk</th>
              <th className="px-4 py-2">AI Decision</th>
              <th className="px-4 py-2">Time</th>
            </tr>
          </thead>
          <tbody>
            {merged.map(tx => (
              <tr key={tx.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                <td className="px-4 py-2 font-mono text-xs">{tx.phone_number}</td>
                <td className="px-4 py-2 font-medium">
                  {getCurrencySymbol(tx.currency)}{Number(tx.amount).toLocaleString()} {tx.currency}
                </td>
                <td className="px-4 py-2">
                  <span className={statusBadge(tx.status)}>{tx.status}</span>
                </td>
                <td className="px-4 py-2">
                  <span className={`font-bold ${riskColor(tx.risk_score)}`}>{tx.risk_score}</span>
                </td>
                <td className="px-4 py-2 max-w-xs">
                  <div className="text-xs text-gray-400 truncate" title={tx.ai_explanation}>
                    {tx.ai_decision || '—'}{tx.ai_explanation ? ': ' + tx.ai_explanation.slice(0, 60) + '…' : ''}
                  </div>
                </td>
                <td className="px-4 py-2 text-gray-400 text-xs">{fmtTime(tx.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Fraud Alerts Feed ────────────────────────────────────────────────────────
function AlertsFeed({ liveAlerts }) {
  const [dbAlerts, setDbAlerts] = useState([])

  useEffect(() => {
    listAlerts({ limit: 30 }).then(r => setDbAlerts(r.data)).catch(() => {})
  }, [liveAlerts.length])

  const seen = new Set()
  const merged = [...liveAlerts, ...dbAlerts].filter(a => {
    if (seen.has(a.id)) return false
    seen.add(a.id); return true
  }).slice(0, 30)

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800">
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
        <h2 className="font-bold">Fraud Alerts</h2>
        <span className="text-xs bg-red-900 text-red-300 px-2 py-0.5 rounded-full font-medium">
          {merged.filter(a => a.risk_level === 'critical' || a.risk_level === 'high').length} high/critical
        </span>
      </div>
      <div className="overflow-auto max-h-96 divide-y divide-gray-800">
        {merged.length === 0 && (
          <div className="text-center py-8 text-gray-500">No fraud alerts yet</div>
        )}
        {merged.map(alert => (
          <div key={alert.id} className="px-5 py-3 hover:bg-gray-800/30">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className={riskBadge(alert.risk_level)}>{alert.risk_level}</span>
                <span className="text-xs text-gray-400 font-mono">{alert.phone_number}</span>
              </div>
              <span className="text-xs text-gray-500">{fmtTime(alert.created_at)}</span>
            </div>
            <div className="text-sm text-gray-300 truncate">{alert.explanation}</div>
            <div className="flex gap-2 mt-1">
              <span className="text-xs text-gray-500 capitalize">{alert.alert_type?.replace('_', ' ')}</span>
              <span className="text-xs text-gray-600">•</span>
              <span className={`text-xs font-medium ${
                alert.action_taken === 'blocked' ? 'text-red-400' :
                alert.action_taken === 'flagged' ? 'text-yellow-400' : 'text-green-400'
              }`}>{alert.action_taken}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Dashboard Overview ───────────────────────────────────────────────────────
const CHART_COLORS = { approved: '#22c55e', blocked: '#ef4444', flagged: '#eab308' }
const PIE_COLORS = ['#22c55e', '#eab308', '#f97316', '#ef4444']

function DashboardOverview({ stats, liveTransactions }) {
  const [timeline, setTimeline] = useState([])
  const [distribution, setDistribution] = useState({})

  const refreshCharts = useCallback(() => {
    getTimeline(24).then(r => setTimeline(r.data)).catch(() => {})
    getRiskDistribution().then(r => setDistribution(r.data)).catch(() => {})
  }, [])

  useEffect(() => { refreshCharts() }, [refreshCharts])
  // Refresh charts when new live transactions arrive
  useEffect(() => { if (liveTransactions.length > 0) refreshCharts() }, [liveTransactions.length, refreshCharts])

  const pieData = Object.entries(distribution).map(([name, value]) => ({ name, value }))
  const totalAmount = liveTransactions.reduce((s, t) => s + (t.amount || 0), 0)

  return (
    <div className="space-y-6">
      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          label="Total Checked"
          value={(stats?.total_transactions ?? 0).toLocaleString()}
          sub="all time"
          icon="🔍"
        />
        <KpiCard
          label="Blocked"
          value={(stats?.total_blocked ?? 0).toLocaleString()}
          color="text-red-400"
          sub={`${stats?.block_rate ?? 0}% block rate`}
          icon="🚫"
        />
        <KpiCard
          label="Flagged"
          value={(stats?.total_flagged ?? 0).toLocaleString()}
          color="text-yellow-400"
          sub="pending review"
          icon="⚠️"
        />
        <KpiCard
          label="Approval Rate"
          value={`${stats?.approval_rate ?? 0}%`}
          color="text-green-400"
          sub={`${(stats?.total_approved ?? 0).toLocaleString()} approved`}
          icon="✅"
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          label="Critical Alerts"
          value={(stats?.critical_alerts ?? 0).toLocaleString()}
          color="text-red-300"
          icon="🔴"
        />
        <KpiCard
          label="Blocked 24h"
          value={(stats?.recent_blocked_24h ?? 0).toLocaleString()}
          icon="📅"
        />
        <KpiCard
          label="Live Transactions"
          value={liveTransactions.length.toLocaleString()}
          color="text-blue-400"
          sub="this session"
          icon="⚡"
        />
        <KpiCard
          label="Session Volume"
          value={`$${(totalAmount * 0.001).toFixed(0)}k`}
          sub="approx. USD equiv."
          icon="💰"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Timeline */}
        <div className="lg:col-span-2 bg-gray-900 rounded-xl border border-gray-800 p-5">
          <h3 className="font-semibold text-sm text-gray-300 mb-4">Transaction Volume (24h)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={timeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="time"
                tickFormatter={v => v.slice(11, 16)}
                tick={{ fontSize: 11, fill: '#9ca3af' }}
              />
              <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                labelStyle={{ color: '#e5e7eb' }}
              />
              <Line type="monotone" dataKey="approved" stroke="#22c55e" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="blocked" stroke="#ef4444" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="flagged" stroke="#eab308" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-2 justify-center">
            {['approved', 'blocked', 'flagged'].map(s => (
              <div key={s} className="flex items-center gap-1 text-xs text-gray-400">
                <div className="w-3 h-1 rounded" style={{ background: CHART_COLORS[s] }} />
                <span className="capitalize">{s}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Risk Distribution Pie */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
          <h3 className="font-semibold text-sm text-gray-300 mb-4">Risk Distribution</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%" cy="50%"
                  innerRadius={55} outerRadius={80}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                  labelLine={false}
                >
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-gray-600 text-sm">
              No data yet
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Root App ─────────────────────────────────────────────────────────────────
const TABS = ['Dashboard', 'Agent Portal', 'Live Feed', 'Alerts']

export default function App() {
  const [tab, setTab] = useState('Dashboard')
  const [stats, setStats] = useState(null)
  const [liveTransactions, setLiveTransactions] = useState([])
  const [liveAlerts, setLiveAlerts] = useState([])
  const [wsConnected, setWsConnected] = useState(false)

  const refreshStats = useCallback(() => {
    getDashboardStats().then(r => setStats(r.data)).catch(() => {})
  }, [])

  useEffect(() => { refreshStats() }, [refreshStats])

  const handleWsMessage = useCallback((msg) => {
    if (msg.type === 'transaction') {
      setLiveTransactions(prev => [msg.data, ...prev].slice(0, 100))
      refreshStats()
    }
  }, [refreshStats])

  const connected = useWebSocket(handleWsMessage)
  useEffect(() => { setWsConnected(connected) }, [connected])

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-lg">🛡</div>
            <div>
              <div className="font-black text-lg tracking-tight">SimGuard</div>
              <div className="text-xs text-gray-500 -mt-0.5">Real-time SIM Swap Fraud Prevention</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs">
              <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-400 live-dot' : 'bg-red-500'}`} />
              <span className="text-gray-400">{wsConnected ? 'Live' : 'Connecting…'}</span>
            </div>
            <div className="text-xs text-gray-600 hidden md:block">Africa Ignite Hackathon 2026</div>
          </div>
        </div>
      </header>

      {/* Navigation tabs */}
      <div className="bg-gray-900/50 border-b border-gray-800 px-6">
        <div className="max-w-7xl mx-auto flex">
          {TABS.map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-6">
        {tab === 'Dashboard' && (
          <DashboardOverview stats={stats} liveTransactions={liveTransactions} />
        )}
        {tab === 'Agent Portal' && (
          <AgentPortal onTxnComplete={refreshStats} />
        )}
        {tab === 'Live Feed' && (
          <LiveFeed liveTransactions={liveTransactions} />
        )}
        {tab === 'Alerts' && (
          <AlertsFeed liveAlerts={liveAlerts} />
        )}
      </main>

      {/* Toast for live blocked transactions */}
      <LiveToast transactions={liveTransactions} />
    </div>
  )
}

// Small popup for high-risk live events
function LiveToast({ transactions }) {
  const [toast, setToast] = useState(null)
  const prevLen = useRef(0)

  useEffect(() => {
    if (transactions.length > prevLen.current) {
      const newest = transactions[0]
      if (newest && (newest.status === 'blocked' || newest.risk_score >= 60)) {
        setToast(newest)
        const t = setTimeout(() => setToast(null), 5000)
        return () => clearTimeout(t)
      }
    }
    prevLen.current = transactions.length
  }, [transactions])

  if (!toast) return null

  return (
    <div className="fixed bottom-5 right-5 bg-red-950 border-2 border-red-600 rounded-xl p-4 max-w-sm shadow-2xl z-50 animate-bounce-once">
      <div className="flex items-start gap-3">
        <span className="text-2xl">🚨</span>
        <div>
          <div className="font-bold text-red-300">{toast.ai_decision} — {toast.phone_number}</div>
          <div className="text-sm text-gray-300 mt-0.5">
            {getCurrencySymbol(toast.currency)}{Number(toast.amount).toLocaleString()} {toast.currency} · Score: {toast.risk_score}
          </div>
          {toast.ai_explanation && (
            <div className="text-xs text-gray-400 mt-1 line-clamp-2">{toast.ai_explanation}</div>
          )}
        </div>
        <button onClick={() => setToast(null)} className="text-gray-500 hover:text-gray-300 ml-auto">✕</button>
      </div>
    </div>
  )
}
