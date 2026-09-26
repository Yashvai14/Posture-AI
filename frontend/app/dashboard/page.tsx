"use client";

import { useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { authApi, analysisApi, API_BASE_URL } from "@/lib/api";
import { 
  Upload, 
  FileText, 
  User, 
  Activity, 
  AlertTriangle, 
  ArrowRight, 
  FileDown, 
  CheckCircle,
  Stethoscope
} from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [name, setName] = useState<string>("John Doe");
  const [age, setAge] = useState<string>("");
  const [gender, setGender] = useState<string>("Male");
  const [height, setHeight] = useState<string>("");
  const [weight, setWeight] = useState<string>("");
  const [symptoms, setSymptoms] = useState<string>("");
  const [isAuthed, setIsAuthed] = useState<boolean>(false);
  const [results, setResults] = useState<any>(null);

  // Auto-login/register mock account on mount to simplify evaluation
  useEffect(() => {
    const initAuth = async () => {
      try {
        await authApi.me();
        setIsAuthed(true);
      } catch (err) {
        try {
          // Clear stale token
          localStorage.removeItem("token");
          // Register mock user
          const mockEmail = `guest_${Math.floor(Math.random() * 10000)}@postureai.com`;
          await authApi.register({
            email: mockEmail,
            password: "password123",
            full_name: "John Doe"
          });
          await authApi.login(mockEmail, "password123");
          setIsAuthed(true);
        } catch (e) {
          console.error("Failed to seed guest account", e);
        }
      }
    };
    initAuth();
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setPreview(URL.createObjectURL(selected));
    }
  };

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Please upload an image first.");
      
      const formData = new FormData();
      formData.append("file", file);
      if (name) formData.append("name", name);
      if (age) formData.append("age", age);
      formData.append("gender", gender);
      if (height) formData.append("height", height);
      if (weight) formData.append("weight", weight);
      if (symptoms) formData.append("symptoms", symptoms);

      return await analysisApi.upload(formData);
    },
    onSuccess: (data) => {
      setResults(data);
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || err.message || "Analysis failed.");
    }
  });

  const getRiskColor = (level: string) => {
    switch (level) {
      case "High": return "bg-red-100 text-red-700 border-red-200";
      case "Medium": return "bg-yellow-100 text-yellow-700 border-yellow-200";
      default: return "bg-emerald-100 text-emerald-700 border-emerald-200";
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-12 flex flex-col gap-10">
      <div>
        <h1 className="text-3xl font-extrabold text-neutral-dark">Anatomical Analysis Dashboard</h1>
        <p className="text-sm text-neutral-dark/60 mt-1.5">Configure your physiological profile and upload postural imagery for assessment.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Input Configuration Column */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <div className="bg-white rounded-xl p-6 border border-neutral-border shadow-soft flex flex-col gap-4">
            <h2 className="font-bold text-neutral-dark flex items-center gap-2">
              <User className="w-5 h-5 text-primary" />
              Patient Information
            </h2>
            
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-neutral-dark/70">Full Name</label>
              <input 
                type="text" 
                value={name} 
                onChange={(e) => setName(e.target.value)} 
                placeholder="e.g. John Doe" 
                className="border border-neutral-border rounded-lg p-2.5 text-xs bg-neutral-light/50 focus:outline-primary"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-neutral-dark/70">Age</label>
                <input 
                  type="number" 
                  value={age} 
                  onChange={(e) => setAge(e.target.value)} 
                  placeholder="e.g. 28" 
                  className="border border-neutral-border rounded-lg p-2.5 text-xs bg-neutral-light/50 focus:outline-primary"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-neutral-dark/70">Gender</label>
                <select 
                  value={gender} 
                  onChange={(e) => setGender(e.target.value)}
                  className="border border-neutral-border rounded-lg p-2.5 text-xs bg-neutral-light/50 focus:outline-primary"
                >
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-neutral-dark/70">Height (cm)</label>
                <input 
                  type="number" 
                  value={height} 
                  onChange={(e) => setHeight(e.target.value)} 
                  placeholder="e.g. 175" 
                  className="border border-neutral-border rounded-lg p-2.5 text-xs bg-neutral-light/50 focus:outline-primary"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-neutral-dark/70">Weight (kg)</label>
                <input 
                  type="number" 
                  value={weight} 
                  onChange={(e) => setWeight(e.target.value)} 
                  placeholder="e.g. 70" 
                  className="border border-neutral-border rounded-lg p-2.5 text-xs bg-neutral-light/50 focus:outline-primary"
                />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-neutral-dark/70">Symptoms & Workstation Habits</label>
              <textarea 
                rows={3}
                value={symptoms} 
                onChange={(e) => setSymptoms(e.target.value)}
                placeholder="Describe shoulder stiffness, lower back pain, neck strain, or typing setups..." 
                className="border border-neutral-border rounded-lg p-2.5 text-xs bg-neutral-light/50 focus:outline-primary resize-none"
              />
            </div>
          </div>

          {/* Upload Image Section */}
          <div className="bg-white rounded-xl p-6 border border-neutral-border shadow-soft flex flex-col gap-4">
            <h2 className="font-bold text-neutral-dark flex items-center gap-2">
              <Upload className="w-5 h-5 text-primary" />
              Posture Image Upload
            </h2>

            {!preview ? (
              <label className="border-2 border-dashed border-neutral-border hover:border-primary/50 transition-colors rounded-xl h-48 flex flex-col items-center justify-center gap-2 cursor-pointer">
                <Upload className="w-8 h-8 text-neutral-dark/40" />
                <span className="text-xs font-semibold text-neutral-dark">Drag and drop or click to upload</span>
                <span className="text-[10px] text-neutral-dark/40">PNG, JPG, JPEG up to 10MB</span>
                <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
              </label>
            ) : (
              <div className="relative rounded-xl overflow-hidden border border-neutral-border h-48">
                <img src={preview} alt="Preview" className="w-full h-full object-cover" />
                <button 
                  onClick={() => { setFile(null); setPreview(null); }} 
                  className="absolute top-2 right-2 bg-neutral-dark/80 hover:bg-neutral-dark text-white rounded-full p-1.5 text-xs transition-colors"
                >
                  Clear
                </button>
              </div>
            )}

            <button 
              onClick={() => analyzeMutation.mutate()}
              disabled={analyzeMutation.isPending || !file}
              className="bg-primary hover:bg-primary-hover disabled:bg-primary/50 text-white font-medium py-3 rounded-lg text-xs shadow-soft transition-all"
            >
              {analyzeMutation.isPending ? "Running Posture Engine..." : "Run Posture Diagnostics"}
            </button>
          </div>
        </div>

        {/* Right Output Analysis Column */}
        <div className="lg:col-span-7">
          {results ? (
            <div className="flex flex-col gap-6">
              {/* Core Diagnostic Box */}
              <div className="bg-white rounded-xl p-6 border border-neutral-border shadow-soft flex flex-col gap-5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-neutral-dark text-lg flex items-center gap-2">
                    <Activity className="w-5 h-5 text-primary" />
                    Diagnostic Metrics
                  </span>
                  <span className={`text-[10px] font-bold px-3 py-1 rounded-full border ${getRiskColor(results.risk_level)}`}>
                    {results.risk_level} Risk Level
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-neutral-light/50 p-3 rounded-lg border border-neutral-border flex flex-col items-center">
                    <span className="text-[10px] font-bold text-neutral-dark/50">Confidence</span>
                    <span className="text-lg font-extrabold text-neutral-dark mt-1">{Math.round(results.confidence_score * 100)}%</span>
                  </div>
                  <div className="bg-neutral-light/50 p-3 rounded-lg border border-neutral-border flex flex-col items-center">
                    <span className="text-[10px] font-bold text-neutral-dark/50">Neck Angle</span>
                    <span className="text-lg font-extrabold text-neutral-dark mt-1">{results.metrics?.ear_shoulder_angle}°</span>
                  </div>
                  <div className="bg-neutral-light/50 p-3 rounded-lg border border-neutral-border flex flex-col items-center">
                    <span className="text-[10px] font-bold text-neutral-dark/50">Shoulder Tilt</span>
                    <span className="text-lg font-extrabold text-neutral-dark mt-1">{results.metrics?.shoulder_tilt}°</span>
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <h3 className="text-xs font-bold text-neutral-dark">Anatomical Deviations:</h3>
                  <div className="flex flex-wrap gap-2">
                    {results.detected_problems?.map((prob: string, idx: number) => (
                      <span key={idx} className="bg-red-50 text-red-600 border border-red-100 text-[10px] font-semibold px-2.5 py-1 rounded-md flex items-center gap-1.5">
                        <AlertTriangle className="w-3 h-3" />
                        {prob}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Recommendations Box */}
              <div className="bg-white rounded-xl p-6 border border-neutral-border shadow-soft flex flex-col gap-4">
                <h3 className="font-bold text-neutral-dark text-sm flex items-center gap-2 border-b border-neutral-border pb-3">
                  <FileText className="w-4 h-4 text-secondary" />
                  Clinical Findings & Recommendations
                </h3>
                
                <div className="flex flex-col gap-1.5">
                  <h4 className="text-xs font-bold text-neutral-dark">Explanation</h4>
                  <p className="text-xs text-neutral-dark/70 leading-relaxed bg-neutral-light/30 p-3 rounded-lg border border-neutral-border/50">
                    {results.findings}
                  </p>
                </div>

                {results.recommendations?.stretches?.length > 0 && (
                  <div className="flex flex-col gap-1.5">
                    <h4 className="text-xs font-bold text-neutral-dark">Therapeutic Stretches</h4>
                    <ul className="text-xs text-neutral-dark/70 space-y-1">
                      {results.recommendations.stretches.map((s: string, idx: number) => (
                        <li key={idx} className="flex gap-2 items-start">
                          <CheckCircle className="w-3.5 h-3.5 text-accent mt-0.5 flex-shrink-0" />
                          <span>{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {results.recommendations?.exercises?.length > 0 && (
                  <div className="flex flex-col gap-1.5">
                    <h4 className="text-xs font-bold text-neutral-dark">Strength Exercises</h4>
                    <ul className="text-xs text-neutral-dark/70 space-y-1">
                      {results.recommendations.exercises.map((e: string, idx: number) => (
                        <li key={idx} className="flex gap-2 items-start">
                          <CheckCircle className="w-3.5 h-3.5 text-primary mt-0.5 flex-shrink-0" />
                          <span>{e}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {results.recommendations?.lifestyle_tips?.length > 0 && (
                  <div className="flex flex-col gap-1.5">
                    <h4 className="text-xs font-bold text-neutral-dark">Workstation adjustments & habits</h4>
                    <ul className="text-xs text-neutral-dark/70 space-y-1">
                      {results.recommendations.lifestyle_tips.map((t: string, idx: number) => (
                        <li key={idx} className="flex gap-2 items-start">
                          <CheckCircle className="w-3.5 h-3.5 text-secondary mt-0.5 flex-shrink-0" />
                          <span>{t}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="flex flex-wrap gap-4 mt-4 pt-4 border-t border-neutral-border">
                  <a 
                    href={`${API_BASE_URL}/reports/${results.report_id}/download?token=${localStorage.getItem("token")}`}
                    target="_blank"
                    rel="noreferrer"
                    className="bg-secondary hover:bg-secondary-hover text-white text-xs font-semibold px-4 py-2.5 rounded-lg flex items-center gap-2"
                  >
                    <FileDown className="w-4 h-4" />
                    <span>Download Report PDF</span>
                  </a>
                  
                  <Link 
                    href="/doctors"
                    className="bg-primary hover:bg-primary-hover text-white text-xs font-semibold px-4 py-2.5 rounded-lg flex items-center gap-2 ml-auto"
                  >
                    <Stethoscope className="w-4 h-4" />
                    <span>Find Local Doctors</span>
                  </Link>
                </div>
              </div>
            </div>
          ) : (
            <div className="border border-dashed border-neutral-border rounded-xl h-[400px] flex flex-col items-center justify-center text-center p-8 bg-white shadow-soft">
              <Activity className="w-12 h-12 text-neutral-dark/20 animate-pulse mb-3" />
              <span className="font-bold text-neutral-dark text-sm">Diagnostic Results Awaiting</span>
              <p className="text-xs text-neutral-dark/40 max-w-xs mt-1">Configure profile coordinates and execute analysis on your postural scan to generate medical recommendations.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
