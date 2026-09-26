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
  RefreshCw
} from "lucide-react";

export default function PatientHistoryPage() {
  const [searchTerm, setSearchTerm] = useState<string>("");

  const { data: history, isLoading, isError, refetch } = useQuery({
    queryKey: ["patientsHistory", searchTerm],
    queryFn: () => analysisApi.getPatientsHistory(searchTerm),
  });

  const getRiskColor = (level: string) => {
    switch (level) {
      case "High": return "bg-red-100 text-red-700 border-red-200";
      case "Medium": return "bg-yellow-100 text-yellow-700 border-yellow-200";
      default: return "bg-emerald-100 text-emerald-700 border-emerald-200";
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-12 flex flex-col gap-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-neutral-dark flex items-center gap-2">
            <FolderHeart className="w-8 h-8 text-primary" />
            Patient Evaluation History
          </h1>
          <p className="text-sm text-neutral-dark/60 mt-1.5">Review, filter, and access generated reports for all patient scans.</p>
        </div>
        
        {/* Dynamic Search Bar */}
        <div className="relative w-full md:w-80 flex items-center">
          <input 
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by patient name, email, or symptoms..."
            className="w-full border border-neutral-border rounded-lg pl-9 pr-4 py-2.5 text-xs bg-white shadow-soft focus:outline-primary"
          />
          <Search className="absolute left-3 w-4 h-4 text-neutral-dark/40" />
        </div>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <RefreshCw className="w-8 h-8 text-primary animate-spin" />
          <span className="text-xs text-neutral-dark/50 font-semibold">Loading history logs...</span>
        </div>
      ) : isError ? (
        <div className="text-center py-20 text-red-500 font-medium text-xs">
          Failed to retrieve records. Ensure the backend FastAPI server is running.
        </div>
      ) : history && history.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {history.map((record: any) => (
            <div key={record.analysis_id} className="bg-white rounded-xl border border-neutral-border p-5 shadow-soft flex flex-col gap-4 hover:border-primary/20 transition-all duration-300">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-neutral-dark flex items-center gap-1.5">
                  <User className="w-4 h-4 text-primary" />
                  {record.patient_name}
                </span>
                <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${getRiskColor(record.risk_level)}`}>
                  {record.risk_level}
                </span>
              </div>

              <div className="flex flex-col gap-1 text-[11px] text-neutral-dark/60">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5 text-neutral-dark/40" />
                  {new Date(record.created_at).toLocaleDateString()} at {new Date(record.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                {record.age && (
                  <span>Metrics: {record.age} years | {record.gender} | {record.height}cm | {record.weight}kg</span>
                )}
              </div>

              <div className="border-t border-neutral-border pt-3 flex flex-col gap-1.5">
                <span className="text-xs font-semibold text-neutral-dark">Reported Symptoms:</span>
                <p className="text-xs text-neutral-dark/60 italic leading-relaxed line-clamp-2">
                  "{record.symptoms || "None entered."}"
                </p>
              </div>

              <div className="flex flex-wrap gap-1.5">
                {record.detected_problems?.map((p: string, i: number) => (
                  <span key={i} className="bg-red-50 text-red-600 border border-red-100 text-[9px] font-medium px-2 py-0.5 rounded-md flex items-center gap-1">
                    <AlertTriangle className="w-2.5 h-2.5" />
                    {p}
                  </span>
                ))}
              </div>

              {record.report_id && (
                <a 
                  href={`${API_BASE_URL}/reports/${record.report_id}/download?token=${localStorage.getItem("token")}`}
                  target="_blank"
                  rel="noreferrer"
                  className="bg-neutral-light hover:bg-primary-light hover:text-primary text-neutral-dark/80 text-[11px] font-semibold py-2 rounded-lg border border-neutral-border flex items-center justify-center gap-2 mt-auto transition-colors"
                >
                  <FileDown className="w-4 h-4" />
                  <span>Download Report PDF</span>
                </a>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="border border-dashed border-neutral-border rounded-xl py-24 flex flex-col items-center justify-center text-center p-8 bg-white shadow-soft">
          <FolderHeart className="w-12 h-12 text-neutral-dark/20 mb-3" />
          <span className="font-bold text-neutral-dark text-sm">No Evaluation Records Found</span>
          <p className="text-xs text-neutral-dark/40 max-w-xs mt-1">Configure profile and run dynamic scans from the dashboard page to build your history log.</p>
        </div>
      )}
    </div>
  );
}
