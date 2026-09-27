"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analysisApi, API_BASE_URL } from "@/lib/api";
import { 
  Search, 
  User, 
  Calendar, 
  AlertTriangle, 
  FileDown, 
  FolderHeart,
  RefreshCw,
  Sparkles,
  GitCompare,
  ArrowRight,
  TrendingUp,
  Activity,
  CheckCircle2,
  X,
  SlidersHorizontal
} from "lucide-react";

export default function PatientHistoryPage() {
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [dateFilter, setDateFilter] = useState<"all" | "7d" | "30d">("all");
  
  // Comparison modal state
  const [compareBaselineId, setCompareBaselineId] = useState<string | null>(null);
  const [compareCurrentId, setCompareCurrentId] = useState<string | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);

  const { data: history, isLoading, isError, refetch } = useQuery({
    queryKey: ["patientsHistory", searchTerm],
    queryFn: () => analysisApi.getPatientsHistory(searchTerm),
  });

  const { data: weeklySummary } = useQuery({
    queryKey: ["weeklySummary"],
    queryFn: () => analysisApi.getWeeklySummary(),
  });

  const { data: comparisonData, isLoading: isComparisonLoading } = useQuery({
    queryKey: ["comparison", compareBaselineId, compareCurrentId],
    queryFn: () => {
      if (!compareBaselineId || !compareCurrentId) return null;
      return analysisApi.compare(compareBaselineId, compareCurrentId);
    },
    enabled: !!compareBaselineId && !!compareCurrentId && isComparing,
  });

  const getRiskColor = (level: string) => {
    switch (level) {
      case "High": return "bg-red-100 text-red-700 border-red-200";
      case "Medium": return "bg-yellow-100 text-yellow-700 border-yellow-200";
      default: return "bg-emerald-100 text-emerald-700 border-emerald-200";
    }
  };

  // Date filtering logic
  const filteredHistory = history?.filter((record: any) => {
    if (dateFilter === "all") return true;
    const recordDate = new Date(record.created_at).getTime();
    const now = Date.now();
    const days = (now - recordDate) / (1000 * 60 * 60 * 24);
    if (dateFilter === "7d") return days <= 7;
    if (dateFilter === "30d") return days <= 30;
    return true;
  });

  const handleStartCompare = (id: string) => {
    if (!compareBaselineId) {
      setCompareBaselineId(id);
    } else if (compareBaselineId === id) {
      setCompareBaselineId(null);
    } else if (!compareCurrentId) {
      setCompareCurrentId(id);
      setIsComparing(true);
    } else {
      setCompareCurrentId(id);
      setIsComparing(true);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 flex flex-col gap-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-neutral-border pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold tracking-wider uppercase text-primary bg-primary/10 px-2.5 py-0.5 rounded-full border border-primary/20">
              Longitudinal Tracking
            </span>
          </div>
          <h1 className="text-3xl font-extrabold text-neutral-dark mt-1.5 flex items-center gap-2.5">
            <FolderHeart className="w-8 h-8 text-primary" />
            Posture Evaluation History & Progress
          </h1>
          <p className="text-xs text-neutral-dark/60 mt-1">
            Review past screenings, track alignment metrics over time, and compare before/after posture scans.
          </p>
        </div>

        {/* Dynamic Search & Time Filter */}
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <div className="flex bg-neutral-light p-1 rounded-xl border border-neutral-border">
            {[
              { id: "all", label: "All" },
              { id: "7d", label: "Last 7 Days" },
              { id: "30d", label: "Last 30 Days" }
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setDateFilter(f.id as any)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  dateFilter === f.id
                    ? "bg-white text-primary shadow-xs"
                    : "text-neutral-dark/60 hover:text-neutral-dark"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="relative w-full sm:w-64 flex items-center">
            <input 
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search evaluations..."
              className="w-full border border-neutral-border rounded-xl pl-9 pr-4 py-2 text-xs bg-white shadow-soft focus:outline-primary"
            />
            <Search className="absolute left-3 w-4 h-4 text-neutral-dark/40" />
          </div>
        </div>
      </div>

      {/* Weekly AI Posture Summary Widget */}
      {weeklySummary && (
        <div className="bg-gradient-to-r from-teal-500/10 via-sky-500/5 to-primary/10 border border-teal-500/20 rounded-2xl p-6 shadow-soft flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-teal-500/15 pb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-teal-600" />
              <h2 className="font-bold text-neutral-dark text-sm">Weekly Posture Consistency Summary</h2>
            </div>
            <span className="text-[10px] font-bold text-teal-700 bg-white/80 px-2.5 py-1 rounded-full border border-teal-200">
              Trend: {weeklySummary.alignment_trend}
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-white/80 p-3 rounded-xl border border-neutral-border/60">
              <span className="text-[10px] font-semibold text-neutral-dark/60">Sessions Completed</span>
              <div className="text-lg font-extrabold text-teal-700 mt-0.5">
                {weeklySummary.sessions_completed} / {weeklySummary.sessions_planned}
              </div>
            </div>

            <div className="bg-white/80 p-3 rounded-xl border border-neutral-border/60">
              <span className="text-[10px] font-semibold text-neutral-dark/60">Neck Discomfort Days</span>
              <div className="text-lg font-extrabold text-amber-700 mt-0.5">
                {weeklySummary.neck_discomfort_days} day(s)
              </div>
            </div>

            <div className="bg-white/80 p-3 rounded-xl border border-neutral-border/60">
              <span className="text-[10px] font-semibold text-neutral-dark/60">Shoulder Discomfort Days</span>
              <div className="text-lg font-extrabold text-amber-700 mt-0.5">
                {weeklySummary.shoulder_discomfort_days} day(s)
              </div>
            </div>

            <div className="bg-white/80 p-3 rounded-xl border border-neutral-border/60">
              <span className="text-[10px] font-semibold text-neutral-dark/60">Primary Daily Activity</span>
              <div className="text-xs font-bold text-neutral-dark mt-1 truncate">
                {weeklySummary.primary_activity}
              </div>
            </div>
          </div>

          <p className="text-xs text-neutral-dark/80 leading-relaxed bg-white/70 p-3 rounded-xl border border-neutral-border/40">
            {weeklySummary.summary_text}
          </p>

          <div className="flex flex-wrap gap-2 items-center text-xs">
            <span className="font-bold text-neutral-dark text-[11px]">Recommended focus for next week:</span>
            {weeklySummary.focus_areas?.map((item: string, idx: number) => (
              <span key={idx} className="bg-white border border-teal-200 text-teal-800 text-[10px] font-semibold px-2.5 py-0.5 rounded-md flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-teal-600" />
                {item}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Comparison Selector Banner (if user clicked compare on any card) */}
      {compareBaselineId && (
        <div className="bg-primary/5 border border-primary/20 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-soft animate-in fade-in">
          <div className="flex items-center gap-2.5">
            <GitCompare className="w-5 h-5 text-primary" />
            <div>
              <span className="text-xs font-bold text-neutral-dark">Before / After Comparison Active</span>
              <p className="text-[11px] text-neutral-dark/60">
                Baseline selected ({compareBaselineId.slice(0, 8)}...). Click "Select for Comparison" on a second evaluation to view metric changes.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setCompareBaselineId(null);
                setCompareCurrentId(null);
                setIsComparing(false);
              }}
              className="text-xs font-semibold text-neutral-dark/60 hover:text-neutral-dark px-3 py-1.5"
            >
              Cancel
            </button>
            {compareCurrentId && (
              <button
                onClick={() => setIsComparing(true)}
                className="bg-primary hover:bg-primary-hover text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-soft flex items-center gap-1.5"
              >
                <span>View Comparison</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Comparison Modal / Panel */}
      {isComparing && comparisonData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-dark/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto border border-neutral-border shadow-2xl p-6 flex flex-col gap-5">
            <div className="flex items-center justify-between border-b border-neutral-border pb-3">
              <div className="flex items-center gap-2">
                <GitCompare className="w-5 h-5 text-primary" />
                <h3 className="font-bold text-neutral-dark text-base">Before / After Posture Comparison</h3>
              </div>
              <button 
                onClick={() => setIsComparing(false)}
                className="w-8 h-8 rounded-full hover:bg-neutral-light flex items-center justify-center text-neutral-dark/60"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Score Comparison */}
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="bg-neutral-light/50 p-4 rounded-xl border border-neutral-border">
                <span className="text-[10px] font-bold text-neutral-dark/50">Baseline Assessment</span>
                <div className="text-xl font-extrabold text-neutral-dark mt-1">
                  {comparisonData.baseline_score ?? "—"} / 100
                </div>
                <span className="text-[10px] text-neutral-dark/60 mt-0.5 block">
                  {new Date(comparisonData.baseline_date).toLocaleDateString()}
                </span>
              </div>

              <div className="bg-primary/5 p-4 rounded-xl border border-primary/20 flex flex-col items-center justify-center">
                <span className="text-[10px] font-bold text-primary">Score Delta</span>
                <div className="text-xl font-extrabold text-primary mt-1">
                  {comparisonData.score_delta !== null ? (comparisonData.score_delta > 0 ? `+${comparisonData.score_delta}` : comparisonData.score_delta) : "—"}
                </div>
                <span className="text-[9px] text-primary/70 mt-0.5">Alignment delta</span>
              </div>

              <div className="bg-neutral-light/50 p-4 rounded-xl border border-neutral-border">
                <span className="text-[10px] font-bold text-neutral-dark/50">Current Assessment</span>
                <div className="text-xl font-extrabold text-teal-700 mt-1">
                  {comparisonData.current_score ?? "—"} / 100
                </div>
                <span className="text-[10px] text-neutral-dark/60 mt-0.5 block">
                  {new Date(comparisonData.current_date).toLocaleDateString()}
                </span>
              </div>
            </div>

            {/* Metric Deltas Table */}
            <div className="flex flex-col gap-2">
              <h4 className="text-xs font-bold text-neutral-dark">Measured Joint & Spine Deltas:</h4>
              <div className="border border-neutral-border rounded-xl overflow-hidden text-xs">
                <div className="grid grid-cols-4 bg-neutral-light/60 p-2.5 font-bold text-neutral-dark/70 border-b border-neutral-border">
                  <span>Metric</span>
                  <span>Baseline</span>
                  <span>Current</span>
                  <span>Observation</span>
                </div>
                {comparisonData.deltas?.map((d: any, idx: number) => (
                  <div key={idx} className="grid grid-cols-4 p-2.5 border-b border-neutral-border/50 items-center">
                    <span className="font-semibold text-neutral-dark">{d.label}</span>
                    <span className="text-neutral-dark/70">{d.baseline_value}°</span>
                    <span className="text-neutral-dark/70">{d.current_value}°</span>
                    <span className={`font-semibold ${d.delta < 0 ? "text-emerald-700" : d.delta > 0 ? "text-amber-700" : "text-neutral-dark/60"}`}>
                      {d.change_description}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Disclaimer & Summary Message */}
            <div className="bg-neutral-light/40 p-4 rounded-xl border border-neutral-border text-xs text-neutral-dark/70 leading-relaxed">
              <span className="font-bold text-neutral-dark block mb-1">Interpretation Note:</span>
              {comparisonData.summary_message}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setIsComparing(false)}
                className="bg-primary hover:bg-primary-hover text-white text-xs font-semibold px-5 py-2.5 rounded-lg shadow-soft"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* History Grid */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <RefreshCw className="w-8 h-8 text-primary animate-spin" />
          <span className="text-xs text-neutral-dark/50 font-semibold">Loading patient records...</span>
        </div>
      ) : isError ? (
        <div className="text-center py-20 text-red-500 font-medium text-xs">
          Failed to retrieve records. Ensure the backend server is reachable.
        </div>
      ) : filteredHistory && filteredHistory.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredHistory.map((record: any) => {
            const isBaseline = compareBaselineId === record.analysis_id;
            const isCurrent = compareCurrentId === record.analysis_id;

            return (
              <div 
                key={record.analysis_id} 
                className={`bg-white rounded-2xl border p-5 shadow-soft flex flex-col gap-4 transition-all duration-300 ${
                  isBaseline || isCurrent 
                    ? "border-primary ring-2 ring-primary/20 bg-primary/2" 
                    : "border-neutral-border hover:border-primary/20"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-neutral-dark flex items-center gap-1.5">
                    <User className="w-4 h-4 text-primary" />
                    {record.patient_name}
                  </span>
                  <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${getRiskColor(record.risk_level)}`}>
                    {record.risk_level} Risk
                  </span>
                </div>

                <div className="flex flex-col gap-1 text-[11px] text-neutral-dark/60">
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-neutral-dark/40" />
                    {new Date(record.created_at).toLocaleDateString()} at {new Date(record.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                  {record.age && (
                    <span>Metrics: {record.age}y · {record.gender} · {record.height}cm · {record.weight}kg</span>
                  )}
                </div>

                <div className="border-t border-neutral-border pt-3 flex flex-col gap-1">
                  <span className="text-xs font-semibold text-neutral-dark">Reported Symptoms:</span>
                  <p className="text-xs text-neutral-dark/60 italic leading-relaxed line-clamp-2">
                    "{record.symptoms || "None entered."}"
                  </p>
                </div>

                <div className="flex flex-wrap gap-1.5">
                  {record.detected_problems?.map((p: string, i: number) => (
                    <span key={i} className="bg-amber-50 text-amber-800 border border-amber-200 text-[9px] font-medium px-2 py-0.5 rounded-md flex items-center gap-1">
                      <AlertTriangle className="w-2.5 h-2.5 text-amber-600" />
                      {p}
                    </span>
                  ))}
                </div>

                {/* Actions: Compare & Download PDF */}
                <div className="grid grid-cols-2 gap-2 mt-auto pt-3 border-t border-neutral-border">
                  <button
                    type="button"
                    onClick={() => handleStartCompare(record.analysis_id)}
                    className={`text-[11px] font-semibold py-2 rounded-lg border flex items-center justify-center gap-1.5 transition-colors ${
                      isBaseline || isCurrent
                        ? "bg-primary text-white border-primary"
                        : "bg-white border-neutral-border text-neutral-dark/70 hover:bg-neutral-light"
                    }`}
                  >
                    <GitCompare className="w-3.5 h-3.5" />
                    <span>{isBaseline ? "Baseline" : isCurrent ? "Comparing" : "Compare"}</span>
                  </button>

                  {record.report_id && (
                    <a 
                      href={`${API_BASE_URL}/reports/${record.report_id}/download?token=${localStorage.getItem("token")}`}
                      target="_blank"
                      rel="noreferrer"
                      className="bg-neutral-light hover:bg-primary/10 hover:text-primary text-neutral-dark/80 text-[11px] font-semibold py-2 rounded-lg border border-neutral-border flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <FileDown className="w-3.5 h-3.5" />
                      <span>PDF Report</span>
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="border border-dashed border-neutral-border rounded-2xl py-24 flex flex-col items-center justify-center text-center p-8 bg-white shadow-soft">
          <FolderHeart className="w-12 h-12 text-neutral-dark/20 mb-3" />
          <span className="font-bold text-neutral-dark text-sm">No Evaluation Records Found</span>
          <p className="text-xs text-neutral-dark/40 max-w-xs mt-1">
            Configure profile and run dynamic posture scans from the dashboard page to build your history log.
          </p>
        </div>
      )}
    </div>
  );
}
