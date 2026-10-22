import { useState } from 'react';
import {
  AlertTriangle,
  Zap,
  CheckCircle2,
  Wrench,
  Clock,
  BookOpen,
  ArrowRight,
  ShieldAlert,
  Send,
  Sparkles,
  ClipboardCheck,
  FileText,
  Cpu
} from 'lucide-react';
import { Asset, CauseCard, SafetyAlert } from '../types';
import {
  streamDiagnosis,
  createTroubleshootingSession,
  recordFinding,
  createWorkOrder,
  submitWorkOrderResolution
} from '../api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';

interface TechnicianViewProps {
  assets: Asset[];
  onWorkOrderSubmitted?: () => void;
}

const COMMON_SYMPTOM_PILLS = [
  { label: 'Severe radial vibration', text: 'Violent radial vibration on pump drive-end bearing', alarm: 'ALM-VIB-101' },
  { label: 'Cavitation rattling', text: 'Sounds like gravel or marbles rattling inside volute casing with fluctuating flow', alarm: 'ALM-SUCT-P-LO' },
  { label: 'Seal face fluid leak', text: 'Fluid puddle leaking steadily from mechanical seal gland seal faces', alarm: 'ALM-SEAL-LVL-LO' },
  { label: 'Discharge pressure surge', text: 'Discharge pressure needle fluttering violently with line hammering', alarm: 'ALM-PRESS-PULS' },
  { label: 'Motor thermal overload', text: 'Motor body burning hot to touch, overload relay tripped', alarm: 'ALM-ELEC-OVR-01' },
  { label: 'Acrid smoke & arcing (STOP WORK)', text: 'Acrid electrical burning smell with visible arcing flashes from terminal enclosure', alarm: 'ALM-ELEC-ARC' },
  { label: 'Sudden seizure (STOP WORK)', text: 'Loud metallic grinding followed by sudden shaft seizure and high locked-rotor hum', alarm: 'ALM-BRG-SEIZE' },
];

export const TechnicianView = ({ assets, onWorkOrderSubmitted }: TechnicianViewProps) => {
  const [selectedAssetId, setSelectedAssetId] = useState<string>('P-101');
  const [symptomText, setSymptomText] = useState<string>('Violent radial vibration on pump drive-end bearing');
  const [alarmCode, setAlarmCode] = useState<string>('ALM-VIB-101');
  const [isDiagnosing, setIsDiagnosing] = useState<boolean>(false);

  // Streaming results
  const [, setMetadata] = useState<any>(null);
  const [streamedText, setStreamedText] = useState<string>('');
  const [causeCards, setCauseCards] = useState<CauseCard[]>([]);
  const [safetyAlert, setSafetyAlert] = useState<SafetyAlert | null>(null);
  const [timing, setTiming] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Interactive finding & work order workflow
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [findingType, setFindingType] = useState<string>('measurement');
  const [findingParameter, setFindingParameter] = useState<string>('radial_vibration_mm_s');
  const [findingValue, setFindingValue] = useState<string>('7.6 mm/s');
  const [findingNotes, setFindingNotes] = useState<string>('Bearing temperature elevated to 86°C. High frequency acoustic emissions.');
  const [findingSaved, setFindingSaved] = useState<boolean>(false);

  // Work order drafting
  const [draftWorkOrder, setDraftWorkOrder] = useState<any>(null);
  const [confirmedCauseId, setConfirmedCauseId] = useState<string>('CAUSE-BRG-WEAR');
  const [actionTaken, setActionTaken] = useState<string>(
    'Removed bearing housing cover, extracted degraded 6312 ball bearing, inspected shaft journal, fitted new 6312-C3 bearing with induction heater, aligned coupling.'
  );
  const [partsUsed, setPartsUsed] = useState<string>('PART-BRG-6312');
  const [resolutionSubmitted, setResolutionSubmitted] = useState<boolean>(false);

  const selectedAsset = assets.find((a) => a.asset_id === selectedAssetId);

  const handleStartDiagnosis = async () => {
    setIsDiagnosing(true);
    setMetadata(null);
    setStreamedText('');
    setCauseCards([]);
    setSafetyAlert(null);
    setTiming(null);
    setErrorMsg(null);
    setFindingSaved(false);
    setDraftWorkOrder(null);
    setResolutionSubmitted(false);

    try {
      await streamDiagnosis(
        {
          asset_id: selectedAssetId,
          symptom_text: symptomText,
          alarm_code: alarmCode || undefined,
        },
        {
          onMetadata: (data) => {
            setMetadata(data);
            if (data.safety_alert) {
              setSafetyAlert(data.safety_alert);
            }
            if (data.ranked_causes) {
              setCauseCards(data.ranked_causes);
            }
          },
          onChunk: (text, chunkTiming) => {
            setStreamedText((prev) => prev + text);
            if (chunkTiming && chunkTiming.first_token_ms && !timing?.first_token_ms) {
              setTiming((prev: any) => ({ ...prev, first_token_ms: chunkTiming.first_token_ms }));
            }
          },
          onCards: (cards) => {
            if (cards && cards.length > 0) {
              setCauseCards(cards);
            }
          },
          onDone: async (doneTiming) => {
            setTiming(doneTiming);
            setIsDiagnosing(false);

            try {
              const session = await createTroubleshootingSession({
                asset_id: selectedAssetId,
                symptom_text: symptomText,
                alarm_code: alarmCode || undefined,
                diagnosis_summary: streamedText,
                candidate_causes: causeCards,
              });
              setActiveSessionId(session.id);
            } catch (err) {
              console.warn('Could not auto-create session', err);
            }
          },
          onError: (err) => {
            setErrorMsg(err);
            setIsDiagnosing(false);
          },
        }
      );
    } catch (e: any) {
      setErrorMsg(e.message || 'Diagnostic stream failed');
      setIsDiagnosing(false);
    }
  };

  const handleRecordFinding = async () => {
    if (!activeSessionId) return;
    try {
      await recordFinding(activeSessionId, {
        finding_type: findingType,
        parameter: findingParameter,
        value: findingValue,
        notes: findingNotes,
      });
      setFindingSaved(true);
    } catch (e: any) {
      alert(`Error saving finding: ${e.message}`);
    }
  };

  const handleGenerateDraftWorkOrder = async () => {
    try {
      const wo = await createWorkOrder({
        asset_id: selectedAssetId,
        session_id: activeSessionId,
        title: `Corrective Maintenance on ${selectedAssetId}: ${symptomText.slice(0, 50)}...`,
        priority: 'high',
        required_parts: ['PART-BRG-6312'],
        findings_summary: `${findingParameter}: ${findingValue}. ${findingNotes}`,
      });
      setDraftWorkOrder(wo);
    } catch (e: any) {
      alert(`Error drafting work order: ${e.message}`);
    }
  };

  const handleSubmitResolution = async () => {
    if (!draftWorkOrder) return;
    try {
      await submitWorkOrderResolution(draftWorkOrder.id, {
        confirmed_cause: confirmedCauseId,
        action_taken: actionTaken,
        parts_used: partsUsed,
        result: 'resolved',
      });
      setResolutionSubmitted(true);
      onWorkOrderSubmitted?.();
    } catch (e: any) {
      alert(`Error submitting resolution: ${e.message}`);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {/* 1. Target Equipment Selection Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-zinc-500" />
              <CardTitle className="text-sm">Target Equipment</CardTitle>
            </div>
            {selectedAsset && (
              <div className="flex items-center gap-2">
                <Badge
                  variant={
                    selectedAsset.badge_color === 'green'
                      ? 'success'
                      : selectedAsset.badge_color === 'amber'
                      ? 'warning'
                      : 'destructive'
                  }
                >
                  Readiness: {selectedAsset.readiness_score}/100
                </Badge>
                <span className="text-xs text-zinc-500 font-mono">
                  {selectedAsset.model} • {selectedAsset.critical_rating}-Class
                </span>
              </div>
            )}
          </div>
          <CardDescription>
            Select industrial pump or induction motor drive for diagnostic evaluation
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {assets.map((asset) => {
              const isSelected = asset.asset_id === selectedAssetId;
              return (
                <button
                  type="button"
                  key={asset.asset_id}
                  onClick={() => setSelectedAssetId(asset.asset_id)}
                  className={`p-3 rounded-lg border text-left transition-all relative cursor-pointer ${
                    isSelected
                      ? 'border-zinc-900 bg-zinc-50 dark:border-zinc-100 dark:bg-zinc-900 shadow-xs'
                      : 'border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 bg-transparent'
                  }`}
                >
                  <div className="font-mono font-bold text-sm text-zinc-900 dark:text-zinc-50">
                    {asset.asset_id}
                  </div>
                  <div className="text-[11px] text-zinc-500 dark:text-zinc-400 truncate">
                    {asset.name}
                  </div>
                  {asset.is_superseded_manual && (
                    <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-amber-500" title="Superseded Manual Trap" />
                  )}
                </button>
              );
            })}
          </div>

          {selectedAsset?.is_superseded_manual && (
            <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/10 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
              <div>
                <strong>Compliance Trap Flagged:</strong> {selectedAsset.superseded_warning}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 2. Symptom Input Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Observed Symptoms & Fault Indicators</CardTitle>
          <CardDescription>
            Select standard industrial scenario pills or input custom field observations
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div>
            <div className="flex flex-wrap gap-1.5 mb-3">
              {COMMON_SYMPTOM_PILLS.map((pill, idx) => (
                <button
                  type="button"
                  key={idx}
                  onClick={() => {
                    setSymptomText(pill.text);
                    setAlarmCode(pill.alarm || '');
                  }}
                  className={`text-xs px-2.5 py-1 rounded-md border transition-all cursor-pointer ${
                    symptomText === pill.text
                      ? 'bg-zinc-900 text-zinc-50 border-zinc-900 dark:bg-zinc-50 dark:text-zinc-900 dark:border-zinc-50 font-medium'
                      : 'bg-zinc-50/60 dark:bg-zinc-900/60 text-zinc-700 dark:text-zinc-300 border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                  }`}
                >
                  {pill.label}
                </button>
              ))}
            </div>

            <Textarea
              rows={3}
              value={symptomText}
              onChange={(e) => setSymptomText(e.target.value)}
              placeholder="Describe what you hear, see, feel, or measure on the machine..."
              className="resize-none font-sans"
            />
          </div>

          <div className="flex items-center justify-between gap-4">
            <div className="w-48">
              <Input
                type="text"
                value={alarmCode}
                onChange={(e) => setAlarmCode(e.target.value)}
                placeholder="Alarm Code (optional)"
                className="font-mono text-xs"
              />
            </div>

            <Button
              onClick={handleStartDiagnosis}
              disabled={isDiagnosing || !symptomText.trim()}
              className="gap-2"
            >
              {isDiagnosing ? (
                <>
                  <Sparkles className="h-4 w-4 animate-spin" />
                  <span>Diagnosing...</span>
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4" />
                  <span>Diagnose Asset</span>
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Error Alert */}
      {errorMsg && (
        <div className="p-4 rounded-lg border border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-400 text-xs flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>Diagnostic error: {errorMsg}</span>
        </div>
      )}

      {/* 3. Latency & Telemetry Badge */}
      {timing && (
        <div
          className={`flex items-center justify-between px-4 py-2.5 rounded-lg border text-xs font-mono ${
            timing.total_ms > 4000
              ? 'border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-400'
              : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'
          }`}
        >
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            <Clock className="h-3.5 w-3.5 shrink-0" />
            <span>First Token: <strong>{timing.first_token_ms} ms</strong></span>
            <span>•</span>
            <span>Total: <strong>{timing.total_ms} ms</strong></span>
            <span>•</span>
            <span>Engine Overhead: <strong>{timing.retrieval_ms || 14} ms</strong></span>
          </div>
          <span className="font-semibold uppercase tracking-wider text-[10px] shrink-0">
            {timing.cache_hit ? '[Cache Hit]' : '[Live Gemma 4]'}
          </span>
        </div>
      )}

      {/* 4. Safety-First Gatekeeper Banner */}
      {safetyAlert && (
        <div className="p-4 rounded-xl border border-red-500/50 bg-red-500/10 text-red-700 dark:text-red-400 space-y-2">
          <div className="flex items-start gap-3">
            <ShieldAlert className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
            <div className="flex-1 space-y-1">
              <div className="font-bold uppercase tracking-wider text-xs">
                CRITICAL SAFETY STOP-WORK HAZARD DETECTED
              </div>
              <p className="text-xs">
                Hazard: {safetyAlert.hazard_type} (Matched: "{safetyAlert.matched_text}")
              </p>
              <div className="p-2.5 rounded-md bg-red-500/15 border border-red-500/20 font-mono text-xs">
                <strong>MANDATORY ACTION:</strong> {safetyAlert.emergency_action}
              </div>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                Governing Procedure: <strong>{safetyAlert.procedure_id}</strong>. Lockout/Tagout (LOTO) isolation required before diagnosis proceeds.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 5. Ranked Candidate Cause Cards */}
      {causeCards.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold tracking-tight text-zinc-900 dark:text-zinc-50 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              Evidence-Ranked Candidate Causes
            </h3>
            <span className="text-xs text-zinc-500">Deterministic Graph Traversal</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {causeCards.map((cause, idx) => (
              <Card key={cause.cause_id || idx} className="hover:border-zinc-300 dark:hover:border-zinc-700">
                <CardHeader className="p-4 pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-sm">{cause.name}</CardTitle>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <Badge
                        variant={
                          cause.evidence_strength === 'high'
                            ? 'success'
                            : cause.evidence_strength === 'moderate'
                            ? 'outline'
                            : 'secondary'
                        }
                        className="uppercase text-[10px]"
                      >
                        {cause.evidence_strength}
                      </Badge>
                      <Badge variant="purple" className="text-[10px]">
                        {cause.label || 'Documented'}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="p-4 pt-0 space-y-2">
                  {cause.explanation && (
                    <p className="text-xs text-zinc-600 dark:text-zinc-300">
                      {cause.explanation}
                    </p>
                  )}

                  {cause.evidence_reasons && cause.evidence_reasons.length > 0 && (
                    <div className="text-[11px] text-zinc-500 space-y-0.5">
                      {cause.evidence_reasons.map((r, i) => (
                        <div key={i} className="flex items-center gap-1.5">
                          <span className="w-1 h-1 rounded-full bg-zinc-400" />
                          <span>{r}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>

                <CardFooter className="p-4 pt-0 border-t border-zinc-100 dark:border-zinc-800/80 mt-2 flex items-center justify-between text-xs text-zinc-500 font-mono">
                  <span className="flex items-center gap-1 text-[11px]">
                    <BookOpen className="h-3 w-3 text-zinc-400" />
                    {cause.source_doc_id} • §{cause.section}
                  </span>
                  <span className="text-[10px] text-zinc-400">
                    {cause.cause_id}
                  </span>
                </CardFooter>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* 6. Grounded Synthesis Stream */}
      {streamedText && (
        <Card className="bg-zinc-50/70 dark:bg-zinc-900/50">
          <CardHeader className="p-4 pb-2">
            <div className="flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-zinc-500" />
              <CardTitle className="text-xs uppercase tracking-wider text-zinc-500 font-mono">
                AI Diagnostic Synthesis (Strictly Grounded)
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <p className="whitespace-pre-line text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed">
              {streamedText}
            </p>
          </CardContent>
        </Card>
      )}

      {/* 7. Field Findings Recording Card */}
      {causeCards.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <ClipboardCheck className="h-4 w-4 text-zinc-500" />
              <CardTitle className="text-sm">Record Field Finding & Measurements</CardTitle>
            </div>
            <CardDescription>
              Capture calibrated instrument readings and physical inspection observations
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">
                  Finding Type
                </label>
                <select
                  value={findingType}
                  onChange={(e) => setFindingType(e.target.value)}
                  className="w-full text-xs p-2 rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-50"
                >
                  <option value="measurement">Physical Measurement</option>
                  <option value="observation">Visual Observation</option>
                  <option value="unresolved">Unresolved / Needs Teardown</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">
                  Parameter
                </label>
                <Input
                  type="text"
                  value={findingParameter}
                  onChange={(e) => setFindingParameter(e.target.value)}
                  className="font-mono text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">
                  Value Measured
                </label>
                <Input
                  type="text"
                  value={findingValue}
                  onChange={(e) => setFindingValue(e.target.value)}
                  className="font-mono text-xs"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">
                Inspection Notes
              </label>
              <Input
                type="text"
                value={findingNotes}
                onChange={(e) => setFindingNotes(e.target.value)}
                className="text-xs"
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleRecordFinding}
                disabled={findingSaved}
                className="gap-1.5"
              >
                {findingSaved ? (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                    <span>Finding Recorded</span>
                  </>
                ) : (
                  <>
                    <Send className="h-3.5 w-3.5" />
                    <span>Record Finding</span>
                  </>
                )}
              </Button>

              <Button
                size="sm"
                onClick={handleGenerateDraftWorkOrder}
                disabled={draftWorkOrder !== null}
                className="gap-1.5"
              >
                <FileText className="h-3.5 w-3.5" />
                <span>Generate Draft Work Order</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 8. Draft Work Order & Resolution Submission */}
      {draftWorkOrder && (
        <Card className="border-zinc-300 dark:border-zinc-700 bg-zinc-50/50 dark:bg-zinc-900/40">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Wrench className="h-4 w-4 text-zinc-700 dark:text-zinc-300" />
                <CardTitle className="text-sm">
                  Draft Work Order: {draftWorkOrder.id}
                </CardTitle>
              </div>
              <Badge variant="outline" className="text-[10px]">
                Pending Supervisor Review
              </Badge>
            </div>
            <CardDescription>
              Assignee: Field Technician • Asset: {draftWorkOrder.asset_id} • Priority: {draftWorkOrder.priority}
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                Confirmed Root Cause
              </label>
              <select
                value={confirmedCauseId}
                onChange={(e) => setConfirmedCauseId(e.target.value)}
                className="w-full text-xs p-2 rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 font-mono text-zinc-900 dark:text-zinc-50"
              >
                {causeCards.map((c) => (
                  <option key={c.cause_id} value={c.cause_id}>
                    {c.cause_id} — {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                Corrective Action Taken
              </label>
              <Textarea
                rows={2}
                value={actionTaken}
                onChange={(e) => setActionTaken(e.target.value)}
                className="text-xs resize-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                Parts Installed / Replaced
              </label>
              <Input
                type="text"
                value={partsUsed}
                onChange={(e) => setPartsUsed(e.target.value)}
                className="text-xs font-mono"
              />
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-zinc-200 dark:border-zinc-800">
              <span className="text-[11px] text-zinc-500">
                Notice: Submitting will move work order to <em>pending_approval</em>. AI cannot mark ready.
              </span>

              <Button
                variant={resolutionSubmitted ? 'outline' : 'default'}
                size="sm"
                onClick={handleSubmitResolution}
                disabled={resolutionSubmitted}
                className="gap-1.5"
              >
                {resolutionSubmitted ? (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                    <span>Submitted for Approval</span>
                  </>
                ) : (
                  <>
                    <ArrowRight className="h-3.5 w-3.5" />
                    <span>Submit Resolution</span>
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
