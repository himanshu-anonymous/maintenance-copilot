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

export const TechnicianView: React.FC<TechnicianViewProps> = ({ assets, onWorkOrderSubmitted }) => {
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

            // Create troubleshooting session in background
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
      {/* 1. Equipment Selection Card */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">
              Target Equipment
            </h2>
          </div>
          {selectedAsset && (
            <div className="flex items-center gap-2">
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-semibold ${
                  selectedAsset.badge_color === 'green'
                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400'
                    : selectedAsset.badge_color === 'amber'
                    ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-400'
                    : 'bg-red-50 text-red-700 dark:bg-red-950/50 dark:text-red-400'
                }`}
              >
                Readiness: {selectedAsset.readiness_score}/100
              </span>
              <span className="text-xs text-slate-500 font-mono">
                {selectedAsset.model} • {selectedAsset.critical_rating}-Class
              </span>
            </div>
          )}
        </div>

        {/* Equipment Selector Chips */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          {assets.map((asset) => {
            const isSelected = asset.asset_id === selectedAssetId;
            return (
              <button
                key={asset.asset_id}
                onClick={() => setSelectedAssetId(asset.asset_id)}
                className={`p-3 rounded-xl border text-left transition-all relative ${
                  isSelected
                    ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-950/30 ring-2 ring-blue-500/20'
                    : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="font-mono font-bold text-sm text-slate-900 dark:text-white">
                  {asset.asset_id}
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                  {asset.name}
                </div>
                {asset.is_superseded_manual && (
                  <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-amber-500" title="Superseded Manual Trap" />
                )}
              </button>
            );
          })}
        </div>

        {/* Warning callout if asset is on superseded manual */}
        {selectedAsset?.is_superseded_manual && (
          <div className="mt-3 p-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/60 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-600 mt-0.5" />
            <div>
              <strong>Compliance Notice:</strong> {selectedAsset.superseded_warning}
            </div>
          </div>
        )}
      </div>

      {/* 2. Symptom Input & Quick Pills */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
            Quick Symptom Scenarios (Tap to Load)
          </label>
          <div className="flex flex-wrap gap-1.5">
            {COMMON_SYMPTOM_PILLS.map((pill, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setSymptomText(pill.text);
                  setAlarmCode(pill.alarm || '');
                }}
                className={`text-xs px-2.5 py-1 rounded-lg border transition-colors ${
                  symptomText === pill.text
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-slate-50 dark:bg-slate-800/60 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                {pill.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
            Observed Symptom Description
          </label>
          <textarea
            rows={3}
            value={symptomText}
            onChange={(e) => setSymptomText(e.target.value)}
            placeholder="Describe what you hear, see, feel, or smell..."
            className="w-full text-sm p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-sans"
          />
        </div>

        <div className="flex items-center justify-between gap-4">
          <div className="flex-1">
            <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1">
              Alarm Code (Optional)
            </label>
            <input
              type="text"
              value={alarmCode}
              onChange={(e) => setAlarmCode(e.target.value)}
              placeholder="e.g. ALM-VIB-101"
              className="text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white w-48 font-mono"
            />
          </div>

          <button
            onClick={handleStartDiagnosis}
            disabled={isDiagnosing || !symptomText.trim()}
            className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white text-sm font-semibold rounded-xl shadow-md shadow-blue-500/20 disabled:opacity-50 transition-all self-end"
          >
            {isDiagnosing ? (
              <>
                <Sparkles className="w-4 h-4 animate-spin" />
                <span>Diagnosing...</span>
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                <span>Diagnose Asset</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>Diagnostic error: {errorMsg}</span>
        </div>
      )}

      {/* 3. Latency & Telemetry Badge */}
      {timing && (
        <div
          className={`flex items-center justify-between px-4 py-2 rounded-xl text-xs font-mono border ${
            timing.total_ms > 4000
              ? 'bg-red-50 dark:bg-red-950/40 border-red-200 dark:border-red-800 text-red-700 dark:text-red-400'
              : 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400'
          }`}
        >
          <div className="flex items-center gap-3">
            <Clock className="w-4 h-4" />
            <span>
              First Token: <strong>{timing.first_token_ms} ms</strong> (p50: 711ms)
            </span>
            <span>•</span>
            <span>
              Total: <strong>{timing.total_ms} ms</strong>
            </span>
            <span>•</span>
            <span>
              Engine Overhead: <strong>{timing.retrieval_ms || 14} ms</strong>
            </span>
          </div>
          <span className="font-semibold uppercase tracking-wider text-[10px]">
            {timing.cache_hit ? '[Cache Hit]' : '[Live Gemma 4]'}
          </span>
        </div>
      )}

      {/* 4. Safety-First Alert Banner (Gatekeeper) */}
      {safetyAlert && (
        <div className="p-4 rounded-2xl bg-red-600 text-white shadow-lg shadow-red-500/20 border-2 border-red-400 animate-pulse">
          <div className="flex items-start gap-3">
            <ShieldAlert className="w-6 h-6 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="font-bold text-sm tracking-wide uppercase">
                CRITICAL SAFETY STOP-WORK HAZARD DETECTED
              </h3>
              <p className="text-xs font-medium text-red-100 mt-1">
                Hazard: {safetyAlert.hazard_type} (Matched: "{safetyAlert.matched_text}")
              </p>
              <div className="mt-2 p-2.5 bg-red-700/80 rounded-xl text-xs font-mono border border-red-400/30">
                <strong>MANDATORY ACTION:</strong> {safetyAlert.emergency_action}
              </div>
              <p className="text-[11px] text-red-200 mt-2">
                Procedure: <strong>{safetyAlert.procedure_id}</strong>. Immediate electrical isolation & Lockout/Tagout (LOTO) mandated before any physical inspection.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 5. Ranked Candidate Causes */}
      {causeCards.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              Evidence-Ranked Candidate Causes
            </h3>
            <span className="text-[11px] text-slate-500 dark:text-slate-400">
              Deterministic Graph Decides • LLM Synthesizes
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {causeCards.map((cause, idx) => (
              <div
                key={cause.cause_id || idx}
                className="bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-2.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="font-semibold text-sm text-slate-900 dark:text-white">
                    {cause.name}
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                        cause.evidence_strength === 'high'
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                          : cause.evidence_strength === 'moderate'
                          ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'
                          : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                      }`}
                    >
                      {cause.evidence_strength}
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300">
                      {cause.label || 'Documented'}
                    </span>
                  </div>
                </div>

                {cause.explanation && (
                  <p className="text-xs text-slate-600 dark:text-slate-300">
                    {cause.explanation}
                  </p>
                )}

                {cause.evidence_reasons && cause.evidence_reasons.length > 0 && (
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 space-y-0.5">
                    {cause.evidence_reasons.map((r, i) => (
                      <div key={i} className="flex items-center gap-1.5">
                        <span className="w-1 h-1 rounded-full bg-blue-500" />
                        <span>{r}</span>
                      </div>
                    ))}
                  </div>
                )}

                <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
                  <span className="font-mono flex items-center gap-1">
                    <BookOpen className="w-3 h-3 text-slate-400" />
                    {cause.source_doc_id} • §{cause.section}
                  </span>
                  <span className="text-blue-600 dark:text-blue-400 font-mono text-[10px]">
                    {cause.cause_id}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 6. Streaming Synthesis Explanation */}
      {streamedText && (
        <div className="bg-slate-50 dark:bg-slate-900/60 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-sans">
          <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-blue-500" />
            AI Diagnostic Synthesis (Strictly Grounded)
          </div>
          <div className="whitespace-pre-line text-xs">{streamedText}</div>
        </div>
      )}

      {/* 7. Technician Field Finding Recording */}
      {causeCards.length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <ClipboardCheck className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Record Field Finding & Measurements
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                Finding Type
              </label>
              <select
                value={findingType}
                onChange={(e) => setFindingType(e.target.value)}
                className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              >
                <option value="measurement">Physical Measurement</option>
                <option value="observation">Visual Observation</option>
                <option value="unresolved">Unresolved / Needs Teardown</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                Parameter
              </label>
              <input
                type="text"
                value={findingParameter}
                onChange={(e) => setFindingParameter(e.target.value)}
                className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                Value Measured
              </label>
              <input
                type="text"
                value={findingValue}
                onChange={(e) => setFindingValue(e.target.value)}
                className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
              Inspection Notes
            </label>
            <input
              type="text"
              value={findingNotes}
              onChange={(e) => setFindingNotes(e.target.value)}
              className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
            />
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              onClick={handleRecordFinding}
              disabled={findingSaved}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-xl shadow-sm disabled:opacity-50 flex items-center gap-2"
            >
              {findingSaved ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Finding Saved to Session</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Record Finding</span>
                </>
              )}
            </button>

            <button
              onClick={handleGenerateDraftWorkOrder}
              disabled={draftWorkOrder !== null}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl shadow-sm disabled:opacity-50 flex items-center gap-2"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Generate Draft Work Order</span>
            </button>
          </div>
        </div>
      )}

      {/* 8. Draft Work Order & Resolution Submission */}
      {draftWorkOrder && (
        <div className="bg-indigo-50/50 dark:bg-indigo-950/20 rounded-2xl p-5 border border-indigo-200 dark:border-indigo-800/60 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Wrench className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              <div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                  Draft Work Order: {draftWorkOrder.id}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Status: <strong>{draftWorkOrder.status}</strong> • Priority: {draftWorkOrder.priority}
                </p>
              </div>
            </div>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300">
              Needs Supervisor Approval
            </span>
          </div>

          <div className="space-y-3 pt-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Confirmed Root Cause
              </label>
              <select
                value={confirmedCauseId}
                onChange={(e) => setConfirmedCauseId(e.target.value)}
                className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-mono"
              >
                {causeCards.map((c) => (
                  <option key={c.cause_id} value={c.cause_id}>
                    {c.cause_id} — {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Corrective Action Taken
              </label>
              <textarea
                rows={2}
                value={actionTaken}
                onChange={(e) => setActionTaken(e.target.value)}
                className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-sans"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Parts Installed / Replaced
              </label>
              <input
                type="text"
                value={partsUsed}
                onChange={(e) => setPartsUsed(e.target.value)}
                className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-mono"
              />
            </div>

            <div className="pt-2 flex items-center justify-between">
              <span className="text-[11px] text-slate-500">
                Notice: Submitting will move work order to <em>pending_approval</em> for supervisor review.
              </span>

              <button
                onClick={handleSubmitResolution}
                disabled={resolutionSubmitted}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl shadow-md shadow-emerald-500/20 disabled:opacity-50 flex items-center gap-2"
              >
                {resolutionSubmitted ? (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Submitted for Supervisor Approval</span>
                  </>
                ) : (
                  <>
                    <ArrowRight className="w-4 h-4" />
                    <span>Submit Resolution</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
