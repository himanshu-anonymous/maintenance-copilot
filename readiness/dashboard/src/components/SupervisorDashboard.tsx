import { useState, useEffect } from 'react';
import {
  CheckCircle,
  XCircle,
  Search,
  ShieldCheck,
  RefreshCw
} from 'lucide-react';
import { Asset, WorkOrder, RecurringCluster } from '../types';
import {
  fetchWorkOrders,
  approveWorkOrder,
  rejectWorkOrder,
  fetchRecurringFaults,
  fetchReadinessBoard,
} from '../api';
import { GraphExplorer } from './GraphExplorer';

interface SupervisorDashboardProps {
  onRefreshData?: () => void;
}

export const SupervisorDashboard: React.FC<SupervisorDashboardProps> = ({ onRefreshData }) => {
  const [activeTab, setActiveTab] = useState<'readiness' | 'approvals' | 'recurring' | 'graph' | 'memory'>('readiness');
  const [assets, setAssets] = useState<Asset[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [recurringClusters, setRecurringClusters] = useState<RecurringCluster[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Approval modal states
  const [approvalModalWo, setApprovalModalWo] = useState<WorkOrder | null>(null);
  const [rejectionModalWo, setRejectionModalWo] = useState<WorkOrder | null>(null);
  const [downtimeHours, setDowntimeHours] = useState<number>(2.5);
  const [approvalNotes, setApprovalNotes] = useState<string>('Inspected vibration baseline after reassembly; vibration dropped to 1.8 mm/s. Approved for service.');
  const [rejectionReason, setRejectionReason] = useState<string>('Missing laser alignment verification data. Please re-check offset before signoff.');

  const loadData = async () => {
    setLoading(true);
    try {
      const [assetsData, wosData, faultsData] = await Promise.all([
        fetchReadinessBoard(),
        fetchWorkOrders(),
        fetchRecurringFaults(),
      ]);
      setAssets(assetsData.assets || []);
      setWorkOrders(wosData || []);
      setRecurringClusters(faultsData.clusters || []);
    } catch (e) {
      console.error('Failed to load supervisor data', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const pendingWorkOrders = workOrders.filter((wo) => wo.status === 'pending_approval');

  const handleApprove = async () => {
    if (!approvalModalWo) return;
    try {
      await approveWorkOrder(approvalModalWo.id, downtimeHours, approvalNotes);
      setApprovalModalWo(null);
      await loadData();
      onRefreshData?.();
    } catch (e: any) {
      alert(`Approval error: ${e.message}`);
    }
  };

  const handleReject = async () => {
    if (!rejectionModalWo) return;
    try {
      await rejectWorkOrder(rejectionModalWo.id, rejectionReason);
      setRejectionModalWo(null);
      await loadData();
      onRefreshData?.();
    } catch (e: any) {
      alert(`Rejection error: ${e.message}`);
    }
  };

  // Filter maintenance memory
  const memoryItems = [
    { id: 'INC-0001', asset: 'P-101', cause: 'Bearing Ball & Race Fatigue Wear', proc: 'PROC-BRG-INSPECT', notes: 'Inner ring spall replaced with 6312-C3.', approved_by: 'supervisor', date: '2024-03-12' },
    { id: 'INC-0002', asset: 'P-101', cause: 'Suction Starvation & Cavitation', proc: 'PROC-SUCT-CLEAR', notes: 'Cleared 40% clogging of strainer mesh.', approved_by: 'supervisor', date: '2024-05-18' },
    { id: 'INC-0003', asset: 'P-102', cause: 'Mechanical Seal Face Thermal Distortion', proc: 'PROC-SEAL-OVERHAUL', notes: 'Flush barrier fluid pressure low.', approved_by: 'supervisor', date: '2024-06-20' },
    { id: 'INC-0004', asset: 'M-104', cause: 'Shaft Angular / Radial Misalignment', proc: 'PROC-ALIGN-LASER', notes: 'Angular offset was 0.12mm. Re-shimmed to 0.02mm.', approved_by: 'supervisor', date: '2024-07-04' },
    { id: 'INC-0005', asset: 'P-103', cause: 'Discharge Check Valve Hinge Pin Flutter', proc: 'PROC-VALVE-SEAT-REPLACE', notes: 'Replaced worn hinge pin and dampener.', approved_by: 'supervisor', date: '2024-08-11' },
    { id: 'INC-0006', asset: 'M-105', cause: 'Shaft Angular / Radial Misalignment', proc: 'PROC-ALIGN-LASER', notes: 'Soft foot condition corrected on front right foot.', approved_by: 'supervisor', date: '2024-09-02' },
    { id: 'INC-0007', asset: 'P-101', cause: 'Bearing Ball & Race Fatigue Wear', proc: 'PROC-BRG-INSPECT', notes: 'Routine replacement during vibration peak.', approved_by: 'supervisor', date: '2024-10-01' },
  ].filter(
    (item) =>
      !searchQuery ||
      item.asset.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.cause.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.notes.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Sub-Navigation Tabs */}
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('readiness')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'readiness'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            Readiness Board
          </button>
          <button
            onClick={() => setActiveTab('approvals')}
            className={`relative px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'approvals'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            Approvals Queue
            {pendingWorkOrders.length > 0 && (
              <span className="ml-1.5 px-1.5 py-0.2 rounded-full bg-red-500 text-white text-[10px]">
                {pendingWorkOrders.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('recurring')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'recurring'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            Recurring Faults & MTBF
          </button>
          <button
            onClick={() => setActiveTab('graph')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'graph'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            Graph Explorer (@xyflow)
          </button>
          <button
            onClick={() => setActiveTab('memory')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'memory'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            Maintenance Memory
          </button>
        </div>

        <button
          onClick={loadData}
          className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-900 dark:hover:text-white"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Sync</span>
        </button>
      </div>

      {/* TAB 1: READINESS BOARD */}
      {activeTab === 'readiness' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {assets.map((asset) => (
              <div
                key={asset.asset_id}
                className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono font-bold text-base text-slate-900 dark:text-white">
                      {asset.asset_id}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                        asset.badge_color === 'green'
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                          : asset.badge_color === 'amber'
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                          : 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                      }`}
                    >
                      {asset.readiness_score}/100
                    </span>
                  </div>

                  <div className="text-xs font-medium text-slate-800 dark:text-slate-200 mb-1 truncate">
                    {asset.name}
                  </div>
                  <div className="text-[11px] text-slate-500 mb-3">
                    {asset.model} • {asset.location}
                  </div>

                  {/* Progress gauge */}
                  <div className="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden mb-3">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        asset.badge_color === 'green'
                          ? 'bg-emerald-500'
                          : asset.badge_color === 'amber'
                          ? 'bg-amber-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${asset.readiness_score}%` }}
                    />
                  </div>

                  <div className="text-[11px] text-slate-500 space-y-1">
                    <div>Days since inspection: <strong>{asset.days_since_inspection}d</strong></div>
                    <div>Open work orders: <strong>{asset.open_work_orders_count}</strong></div>
                  </div>
                </div>

                {asset.is_superseded_manual && (
                  <div className="mt-3 p-2 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl text-[10px] text-amber-800 dark:text-amber-300">
                    <strong>TRAP 2 FLAGGED:</strong> Running superseded Rev A (0.080mm tolerance superseded by Rev B 0.038mm).
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Detailed Fleet Health Table */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                Equipment Readiness Breakdown & Penalty Audit
              </h3>
              <span className="text-xs text-slate-500">5 Monitored Assets</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="px-5 py-3">Asset</th>
                    <th className="px-5 py-3">Category</th>
                    <th className="px-5 py-3">Manual Rev</th>
                    <th className="px-5 py-3">Readiness</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3">Active Penalties & Compliance Flags</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                  {assets.map((a) => (
                    <tr key={a.asset_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                      <td className="px-5 py-3 font-mono font-bold text-slate-900 dark:text-white">
                        {a.asset_id}
                      </td>
                      <td className="px-5 py-3">{a.category}</td>
                      <td className="px-5 py-3 font-mono">
                        {a.is_superseded_manual ? (
                          <span className="text-amber-600 dark:text-amber-400 font-bold">
                            Rev A (Superseded)
                          </span>
                        ) : (
                          'Rev B/C (Current)'
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <span className="font-bold text-sm">{a.readiness_score}</span>/100
                      </td>
                      <td className="px-5 py-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            a.badge_color === 'green'
                              ? 'bg-emerald-50 text-emerald-700'
                              : a.badge_color === 'amber'
                              ? 'bg-amber-50 text-amber-700'
                              : 'bg-red-50 text-red-700'
                          }`}
                        >
                          {a.status_label}
                        </span>
                      </td>
                      <td className="px-5 py-3 space-y-0.5 text-[11px]">
                        {a.penalties.length > 0 ? (
                          a.penalties.map((p, i) => (
                            <div key={i} className="text-amber-600 dark:text-amber-400">
                              • {p}
                            </div>
                          ))
                        ) : (
                          <span className="text-emerald-600 dark:text-emerald-400">
                            No active penalties. Equipment optimal.
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: APPROVALS QUEUE */}
      {activeTab === 'approvals' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                Supervisor Verification & Operational Clearance Gate
              </h3>
              <p className="text-xs text-slate-500">
                AI / Technician proposals cannot close incidents. Only verified supervisor approval establishes graph precedent.
              </p>
            </div>
          </div>

          {pendingWorkOrders.length === 0 ? (
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-12 text-center border border-slate-200 dark:border-slate-800">
              <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
              <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
                Approvals Queue Clean
              </h4>
              <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
                No technician resolutions currently pending review. Switch to Technician Copilot to diagnose an asset and submit a resolution.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {pendingWorkOrders.map((wo) => (
                <div
                  key={wo.id}
                  className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-sm text-slate-900 dark:text-white">
                        {wo.id}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 font-semibold uppercase">
                        Pending Review
                      </span>
                      <span className="text-xs text-slate-500 font-mono font-bold">
                        Asset: {wo.asset_id}
                      </span>
                    </div>

                    <div className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                      {wo.title}
                    </div>

                    <div className="text-xs text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/50 p-2.5 rounded-xl border border-slate-100 dark:border-slate-800">
                      <div>
                        <strong>Technician Action:</strong> {wo.resolution_action_taken}
                      </div>
                      <div className="mt-1 flex items-center gap-4 text-[11px] text-slate-500">
                        <span>Confirmed Cause: <strong className="text-blue-500 font-mono">{wo.resolution_confirmed_cause}</strong></span>
                        <span>Parts Replaced: <strong className="font-mono">{wo.resolution_parts_used || 'None'}</strong></span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0 self-end md:self-center">
                    <button
                      onClick={() => setRejectionModalWo(wo)}
                      className="px-4 py-2 bg-red-50 hover:bg-red-100 dark:bg-red-950/40 dark:hover:bg-red-900/60 text-red-600 dark:text-red-300 text-xs font-semibold rounded-xl border border-red-200 dark:border-red-800 transition-colors flex items-center gap-1.5"
                    >
                      <XCircle className="w-4 h-4" />
                      <span>Reject</span>
                    </button>

                    <button
                      onClick={() => setApprovalModalWo(wo)}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl shadow-md shadow-emerald-500/20 transition-all flex items-center gap-1.5"
                    >
                      <CheckCircle className="w-4 h-4" />
                      <span>Verify & Approve</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: RECURRING FAULTS & MTBF */}
      {activeTab === 'recurring' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                Equipment Failure Clusters & MTBF Approximations
              </h3>
              <p className="text-xs text-slate-500">
                Calculated dynamically from verified maintenance incident history over operating lifetime.
              </p>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-5 py-3">Asset</th>
                  <th className="px-5 py-3">Component Involved</th>
                  <th className="px-5 py-3">Confirmed Root Cause</th>
                  <th className="px-5 py-3">Frequency</th>
                  <th className="px-5 py-3">Downtime (hrs)</th>
                  <th className="px-5 py-3">Approx MTBF</th>
                  <th className="px-5 py-3">Risk Assessment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                {recurringClusters.map((cluster, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                    <td className="px-5 py-3 font-mono font-bold text-slate-900 dark:text-white">
                      {cluster.asset_id}
                    </td>
                    <td className="px-5 py-3">{cluster.component_name}</td>
                    <td className="px-5 py-3 font-semibold text-slate-800 dark:text-slate-200">
                      {cluster.cause_name}
                    </td>
                    <td className="px-5 py-3">
                      <span className="font-bold">{cluster.occurrence_count}</span> incidents
                    </td>
                    <td className="px-5 py-3 font-mono">{cluster.total_downtime_hours} hrs</td>
                    <td className="px-5 py-3 font-mono font-semibold text-blue-600 dark:text-blue-400">
                      {cluster.approx_mtbf_hours.toLocaleString()} hrs
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                          cluster.risk_level === 'High'
                            ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                            : cluster.risk_level === 'Moderate'
                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                            : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                        }`}
                      >
                        {cluster.risk_level}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: GRAPH EXPLORER */}
      {activeTab === 'graph' && <GraphExplorer />}

      {/* TAB 5: MAINTENANCE MEMORY SEARCH */}
      {activeTab === 'memory' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 bg-white dark:bg-slate-900 p-3 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search historical verified incidents, root causes, and corrective actions..."
              className="w-full text-xs bg-transparent focus:outline-none text-slate-900 dark:text-white"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {memoryItems.map((item) => (
              <div
                key={item.id}
                className="bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-blue-600 dark:text-blue-400">
                    {item.id} • {item.asset}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 font-semibold">
                    Verified Precedent
                  </span>
                </div>

                <div className="font-semibold text-slate-800 dark:text-slate-200">
                  {item.cause}
                </div>

                <p className="text-slate-600 dark:text-slate-400 text-[11px]">
                  "{item.notes}"
                </p>

                <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                  <span>Procedure: {item.proc}</span>
                  <span>Approved by: {item.approved_by}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MODAL: APPROVE WORK ORDER */}
      {approvalModalWo && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-3xl p-6 border border-slate-200 dark:border-slate-800 shadow-2xl max-w-md w-full space-y-4">
            <div className="flex items-center gap-2 text-emerald-600">
              <ShieldCheck className="w-5 h-5" />
              <h3 className="text-sm font-bold">Approve Resolution & Verify Outcome</h3>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-400">
              Approving will establish a <strong>Verified Precedent edge</strong> in the knowledge graph. This outcome will guide future AI diagnoses.
            </p>

            <div>
              <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Downtime Duration (Hours)
              </label>
              <input
                type="number"
                step="0.5"
                value={downtimeHours}
                onChange={(e) => setDowntimeHours(parseFloat(e.target.value))}
                className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Supervisor Approval Notes
              </label>
              <textarea
                rows={3}
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 font-sans"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setApprovalModalWo(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handleApprove}
                className="px-5 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-md shadow-emerald-500/20"
              >
                Confirm Approval & Write to Graph
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: REJECT WORK ORDER */}
      {rejectionModalWo && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-3xl p-6 border border-slate-200 dark:border-slate-800 shadow-2xl max-w-md w-full space-y-4">
            <div className="flex items-center gap-2 text-red-600">
              <XCircle className="w-5 h-5" />
              <h3 className="text-sm font-bold">Reject Work Order</h3>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-400">
              Rejecting will return this resolution to the technician with feedback. <strong>Zero edges</strong> will be created in the knowledge graph.
            </p>

            <div>
              <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Rejection Reason & Required Feedback
              </label>
              <textarea
                rows={3}
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 font-sans"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setRejectionModalWo(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                className="px-5 py-2 rounded-xl text-xs font-semibold bg-red-600 hover:bg-red-700 text-white shadow-md shadow-red-500/20"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
