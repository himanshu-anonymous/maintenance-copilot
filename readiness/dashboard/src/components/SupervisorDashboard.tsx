import { useState, useEffect } from 'react';
import {
  CheckCircle,
  XCircle,
  Search,
  ShieldCheck,
  RefreshCw,
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
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from './ui/tabs';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from './ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';

interface SupervisorDashboardProps {
  onRefreshData?: () => void;
}

export const SupervisorDashboard = ({ onRefreshData }: SupervisorDashboardProps) => {
  const [activeTab, setActiveTab] = useState<string>('readiness');
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
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 pb-3 flex-wrap gap-2">
          <TabsList>
            <TabsTrigger value="readiness">Readiness Board</TabsTrigger>
            <TabsTrigger value="approvals" badge={pendingWorkOrders.length}>
              Approvals Queue
            </TabsTrigger>
            <TabsTrigger value="recurring">Recurring Faults & MTBF</TabsTrigger>
            <TabsTrigger value="graph">Graph Explorer (@xyflow)</TabsTrigger>
            <TabsTrigger value="memory">Maintenance Memory</TabsTrigger>
          </TabsList>

          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            className="gap-1.5 h-8 text-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Sync</span>
          </Button>
        </div>

        {/* TAB 1: READINESS BOARD */}
        <TabsContent value="readiness" className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {assets.map((asset) => (
              <Card key={asset.asset_id} className="flex flex-col justify-between">
                <CardHeader className="p-4 pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="font-mono text-base">{asset.asset_id}</CardTitle>
                    <Badge
                      variant={
                        asset.badge_color === 'green'
                          ? 'success'
                          : asset.badge_color === 'amber'
                          ? 'warning'
                          : 'destructive'
                      }
                      className="text-xs"
                    >
                      {asset.readiness_score}/100
                    </Badge>
                  </div>
                  <div className="text-xs font-medium text-zinc-900 dark:text-zinc-100 truncate mt-1">
                    {asset.name}
                  </div>
                  <CardDescription className="text-[11px]">
                    {asset.model} • {asset.location}
                  </CardDescription>
                </CardHeader>

                <CardContent className="p-4 pt-0 space-y-2">
                  {/* Progress bar */}
                  <div className="h-1.5 w-full rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
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

                  <div className="flex items-center justify-between text-[11px] text-zinc-500 font-mono">
                    <span>Inspection: {asset.days_since_inspection}d ago</span>
                    <span>WOs: {asset.open_work_orders_count}</span>
                  </div>

                  {asset.is_superseded_manual && (
                    <div className="p-2 rounded-md bg-amber-500/10 border border-amber-500/30 text-[10px] text-amber-700 dark:text-amber-400">
                      <strong>TRAP 2 FLAGGED:</strong> Running superseded Rev A (0.080mm tolerance vs Rev B 0.038mm).
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Detailed Table */}
          <Card>
            <CardHeader className="p-4 pb-3 border-b border-zinc-100 dark:border-zinc-800">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-sm">
                    Fleet Readiness & Compliance Penalty Audit
                  </CardTitle>
                  <CardDescription>
                    Real-time 0-100 score components factoring open work order severity, inspection aging, and manual freshness
                  </CardDescription>
                </div>
                <Badge variant="outline" className="font-mono text-xs">
                  5 Assets Monitored
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Asset ID</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Manual Revision</TableHead>
                    <TableHead>Readiness Score</TableHead>
                    <TableHead>Operational Status</TableHead>
                    <TableHead>Active Penalties & Compliance Flags</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {assets.map((a) => (
                    <TableRow key={a.asset_id}>
                      <TableCell className="font-mono font-bold text-zinc-900 dark:text-zinc-50">
                        {a.asset_id}
                      </TableCell>
                      <TableCell className="capitalize">{a.category.replace('_', ' ')}</TableCell>
                      <TableCell className="font-mono">
                        {a.is_superseded_manual ? (
                          <Badge variant="warning" className="text-[10px]">
                            Rev A (Superseded)
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="text-[10px]">
                            {a.model.includes('IM50-VFD') ? 'Rev A' : a.model.includes('CP200') ? 'Rev B' : 'Rev C'}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className="font-bold text-sm">{a.readiness_score}</span>
                        <span className="text-zinc-400 text-xs">/100</span>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            a.badge_color === 'green'
                              ? 'success'
                              : a.badge_color === 'amber'
                              ? 'warning'
                              : 'destructive'
                          }
                          className="text-[10px] capitalize"
                        >
                          {a.status_label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs">
                        {a.penalties.length > 0 ? (
                          <div className="space-y-0.5">
                            {a.penalties.map((p, i) => (
                              <div key={i} className="text-amber-600 dark:text-amber-400">
                                • {p}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <span className="text-emerald-600 dark:text-emerald-400 text-xs">
                            No active penalties. Equipment optimal.
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 2: APPROVALS QUEUE */}
        <TabsContent value="approvals" className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                Supervisor Verification & Operational Clearance Gate
              </h3>
              <p className="text-xs text-zinc-500">
                The AI and technician cannot mark equipment ready. Only verified supervisor approval establishes graph precedent.
              </p>
            </div>
          </div>

          {pendingWorkOrders.length === 0 ? (
            <Card className="p-12 text-center">
              <CheckCircle className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
              <CardTitle className="text-sm mb-1">Approvals Queue Empty</CardTitle>
              <CardDescription className="max-w-md mx-auto text-xs">
                No technician resolutions currently awaiting supervisor verification. Switch to Technician Copilot to troubleshoot an asset and submit a resolution.
              </CardDescription>
            </Card>
          ) : (
            <div className="space-y-3">
              {pendingWorkOrders.map((wo) => (
                <Card key={wo.id} className="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-sm">{wo.id}</span>
                      <Badge variant="warning" className="text-[10px] uppercase">
                        Pending Review
                      </Badge>
                      <Badge variant="outline" className="text-[10px] font-mono">
                        Asset: {wo.asset_id}
                      </Badge>
                    </div>

                    <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                      {wo.title}
                    </div>

                    <div className="text-xs text-zinc-600 dark:text-zinc-300 p-2.5 rounded-md bg-zinc-50 dark:bg-zinc-900 border border-zinc-200/60 dark:border-zinc-800/60 space-y-1">
                      <div>
                        <strong>Technician Action Taken:</strong> {wo.resolution_action_taken}
                      </div>
                      <div className="flex items-center gap-4 text-[11px] text-zinc-500">
                        <span>Confirmed Cause: <code className="text-zinc-900 dark:text-zinc-100 font-bold">{wo.resolution_confirmed_cause}</code></span>
                        <span>Parts Replaced: <code className="font-mono">{wo.resolution_parts_used || 'None'}</code></span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setRejectionModalWo(wo)}
                      className="text-red-600 dark:text-red-400 hover:text-red-700 gap-1.5"
                    >
                      <XCircle className="h-3.5 w-3.5" />
                      <span>Reject</span>
                    </Button>

                    <Button
                      variant="success"
                      size="sm"
                      onClick={() => setApprovalModalWo(wo)}
                      className="gap-1.5"
                    >
                      <CheckCircle className="h-3.5 w-3.5" />
                      <span>Verify & Approve</span>
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* TAB 3: RECURRING FAULTS & MTBF */}
        <TabsContent value="recurring" className="space-y-4">
          <Card>
            <CardHeader className="p-4 pb-3 border-b border-zinc-100 dark:border-zinc-800">
              <CardTitle className="text-sm">
                Equipment Failure Clusters & MTBF Approximations
              </CardTitle>
              <CardDescription>
                Calculated dynamically from verified maintenance incident history across asset components
              </CardDescription>
            </CardHeader>

            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Asset</TableHead>
                    <TableHead>Component</TableHead>
                    <TableHead>Confirmed Root Cause</TableHead>
                    <TableHead>Frequency</TableHead>
                    <TableHead>Downtime (hrs)</TableHead>
                    <TableHead>Approx MTBF</TableHead>
                    <TableHead>Risk Level</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recurringClusters.map((cluster, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-mono font-bold text-zinc-900 dark:text-zinc-50">
                        {cluster.asset_id}
                      </TableCell>
                      <TableCell>{cluster.component_name}</TableCell>
                      <TableCell className="font-medium text-zinc-800 dark:text-zinc-200">
                        {cluster.cause_name}
                      </TableCell>
                      <TableCell className="font-mono">{cluster.occurrence_count} incidents</TableCell>
                      <TableCell className="font-mono">{cluster.total_downtime_hours} hrs</TableCell>
                      <TableCell className="font-mono font-semibold">
                        {cluster.approx_mtbf_hours.toLocaleString()} hrs
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            cluster.risk_level === 'High'
                              ? 'destructive'
                              : cluster.risk_level === 'Moderate'
                              ? 'warning'
                              : 'success'
                          }
                          className="text-[10px] uppercase"
                        >
                          {cluster.risk_level}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 4: GRAPH EXPLORER */}
        <TabsContent value="graph">
          <GraphExplorer />
        </TabsContent>

        {/* TAB 5: MAINTENANCE MEMORY SEARCH */}
        <TabsContent value="memory" className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-400" />
            <Input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search past verified incidents, root causes, procedures, and actions..."
              className="pl-9 text-xs"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {memoryItems.map((item) => (
              <Card key={item.id} className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs text-zinc-900 dark:text-zinc-50">
                    {item.id} • {item.asset}
                  </span>
                  <Badge variant="success" className="text-[10px]">
                    Verified Precedent
                  </Badge>
                </div>

                <div className="font-medium text-xs text-zinc-800 dark:text-zinc-200">
                  {item.cause}
                </div>

                <p className="text-[11px] text-zinc-600 dark:text-zinc-400">
                  "{item.notes}"
                </p>

                <div className="pt-2 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between text-[10px] text-zinc-500 font-mono">
                  <span>Procedure: {item.proc}</span>
                  <span>Verified by: {item.approved_by}</span>
                </div>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* APPROVAL DIALOG */}
      <Dialog open={approvalModalWo !== null} onOpenChange={(open) => !open && setApprovalModalWo(null)}>
        <DialogContent onClose={() => setApprovalModalWo(null)}>
          <DialogHeader>
            <div className="flex items-center gap-2 text-emerald-600">
              <ShieldCheck className="h-5 w-5" />
              <DialogTitle>Approve Resolution & Commit Precedent</DialogTitle>
            </div>
            <DialogDescription>
              Verification creates a permanent <strong>Verified Outcome edge</strong> in the in-memory graph.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <div>
              <label className="block font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                Downtime Duration (Hours)
              </label>
              <Input
                type="number"
                step="0.5"
                value={downtimeHours}
                onChange={(e) => setDowntimeHours(parseFloat(e.target.value))}
                className="font-mono"
              />
            </div>

            <div>
              <label className="block font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                Supervisor Approval Notes
              </label>
              <Textarea
                rows={3}
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                className="resize-none"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setApprovalModalWo(null)}>
              Cancel
            </Button>
            <Button variant="success" size="sm" onClick={handleApprove}>
              Confirm Approval & Write to Graph
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* REJECTION DIALOG */}
      <Dialog open={rejectionModalWo !== null} onOpenChange={(open) => !open && setRejectionModalWo(null)}>
        <DialogContent onClose={() => setRejectionModalWo(null)}>
          <DialogHeader>
            <div className="flex items-center gap-2 text-red-600">
              <XCircle className="h-5 w-5" />
              <DialogTitle>Reject Work Order Resolution</DialogTitle>
            </div>
            <DialogDescription>
              Rejection returns the task to the technician for revision. <strong>No edges</strong> will be created in the knowledge graph.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <div>
              <label className="block font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                Rejection Reason & Required Remediation
              </label>
              <Textarea
                rows={3}
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                className="resize-none"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setRejectionModalWo(null)}>
              Cancel
            </Button>
            <Button variant="destructive" size="sm" onClick={handleReject}>
              Confirm Rejection
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
