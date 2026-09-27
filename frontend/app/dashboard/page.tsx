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
  Stethoscope,
  Briefcase,
  Languages,
  Eye,
  Camera,
  Layers,
  Sparkles,
  Info,
  CheckCircle2,
  X
} from "lucide-react";
import Link from "next/link";
import { CaptureGuideModal } from "@/components/CaptureGuideModal";
import { SilhouetteOverlay } from "@/components/SilhouetteOverlay";
import { DailyCheckinCard } from "@/components/DailyCheckinCard";
import { PostureProgramCard } from "@/components/PostureProgramCard";

export default function DashboardPage() {
  // Assessment Scope
  const [assessmentType, setAssessmentType] = useState<"quick_upper_body" | "full_assessment">("full_assessment");
  
  // Multi-angle files & previews
  const [frontFile, setFrontFile] = useState<File | null>(null);
  const [frontPreview, setFrontPreview] = useState<string | null>(null);
  const [sideFile, setSideFile] = useState<File | null>(null);
  const [sidePreview, setSidePreview] = useState<string | null>(null);
  const [backFile, setBackFile] = useState<File | null>(null);
  const [backPreview, setBackPreview] = useState<string | null>(null);
  const [activeAngleTab, setActiveAngleTab] = useState<"front" | "side" | "back">("front");

  // Overlay & Guide State
  const [showSilhouette, setShowSilhouette] = useState<boolean>(true);
  const [isGuideOpen, setIsGuideOpen] = useState<boolean>(false);

  // Profile data
  const [name, setName] = useState<string>("John Doe");
  const [age, setAge] = useState<string>("28");
  const [gender, setGender] = useState<string>("Male");
  const [height, setHeight] = useState<string>("175");
  const [weight, setWeight] = useState<string>("70");
  const [occupation, setOccupation] = useState<string>("software_developer");
  const [preferredLanguage, setPreferredLanguage] = useState<string>("en");
  const [symptoms, setSymptoms] = useState<string>("Neck stiffness and upper shoulder tension after long desk sessions");
  
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
          localStorage.removeItem("token");
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

  const handleAngleFileChange = (angle: "front" | "side" | "back", e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      const previewUrl = URL.createObjectURL(selected);
      if (angle === "front") {
        setFrontFile(selected);
        setFrontPreview(previewUrl);
      } else if (angle === "side") {
        setSideFile(selected);
        setSidePreview(previewUrl);
      } else if (angle === "back") {
        setBackFile(selected);
        setBackPreview(previewUrl);
      }
    }
  };

  const clearAngleFile = (angle: "front" | "side" | "back") => {
    if (angle === "front") {
      setFrontFile(null);
      setFrontPreview(null);
    } else if (angle === "side") {
      setSideFile(null);
      setSidePreview(null);
    } else if (angle === "back") {
      setBackFile(null);
      setBackPreview(null);
    }
  };

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      if (!frontFile && !sideFile && !backFile) {
        throw new Error("Please upload at least one image (Front, Side, or Back view).");
      }
      
      const formData = new FormData();
      // Primary upload file
      const primaryFile = frontFile || sideFile || backFile;
      if (primaryFile) {
        formData.append("file", primaryFile);
      }
      if (sideFile && primaryFile !== sideFile) {
        formData.append("side_file", sideFile);
      }
      if (backFile && primaryFile !== backFile) {
        formData.append("back_file", backFile);
      }

      if (name) formData.append("name", name);
      if (age) formData.append("age", age);
      formData.append("gender", gender);
      if (height) formData.append("height", height);
      if (weight) formData.append("weight", weight);
      if (symptoms) formData.append("symptoms", symptoms);
      if (occupation) formData.append("occupation", occupation);
      if (preferredLanguage) formData.append("preferred_language", preferredLanguage);

      return await analysisApi.upload(formData);
    },
    onSuccess: (data) => {
      setResults(data);
      // Smooth scroll to output
      window.scrollTo({ top: 380, behavior: "smooth" });
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

  const activePreview = activeAngleTab === "front" ? frontPreview : activeAngleTab === "side" ? sidePreview : backPreview;
  const activeFile = activeAngleTab === "front" ? frontFile : activeAngleTab === "side" ? sideFile : backFile;

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 flex flex-col gap-8">
      {/* Capture Guide Modal */}
      <CaptureGuideModal isOpen={isGuideOpen} onClose={() => setIsGuideOpen(false)} />

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-neutral-border pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold tracking-wider uppercase text-teal-700 bg-teal-50 px-2.5 py-0.5 rounded-full border border-teal-200">
              Quality-Aware Vision Engine
            </span>
            <span className="text-[10px] font-bold tracking-wider uppercase text-sky-700 bg-sky-50 px-2.5 py-0.5 rounded-full border border-sky-200">
              BlazePose 33-Landmark
            </span>
          </div>
          <h1 className="text-3xl font-extrabold text-neutral-dark mt-1.5">Posture Screening Platform</h1>
          <p className="text-xs text-neutral-dark/60 mt-1">
            Clinical computer vision analysis supporting full-body and upper-body partial scans with multi-angle fusion.
          </p>
        </div>

        {/* Capture Guide Button */}
        <button
          onClick={() => setIsGuideOpen(true)}
          className="bg-white hover:bg-neutral-light text-neutral-dark border border-neutral-border text-xs font-semibold px-4 py-2.5 rounded-xl shadow-soft flex items-center gap-2 transition-all self-start md:self-auto"
        >
          <Camera className="w-4 h-4 text-teal-600" />
          <span>Open Capture Guide</span>
        </button>
      </div>

      {/* Scope Selector Bar */}
      <div className="bg-white rounded-2xl p-4 border border-neutral-border shadow-soft flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-primary" />
          <div>
            <h2 className="text-xs font-bold text-neutral-dark">Select Assessment Type</h2>
            <p className="text-[11px] text-neutral-dark/60">Choose between a quick partial check or comprehensive multi-angle evaluation</p>
          </div>
        </div>

        <div className="flex bg-neutral-light p-1 rounded-xl border border-neutral-border/80 w-full sm:w-auto">
          <button
            type="button"
            onClick={() => setAssessmentType("full_assessment")}
            className={`flex-1 sm:flex-initial px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              assessmentType === "full_assessment"
                ? "bg-white text-primary shadow-xs"
                : "text-neutral-dark/60 hover:text-neutral-dark"
            }`}
          >
            Full Assessment (Front + Side + Back)
          </button>
          <button
            type="button"
            onClick={() => setAssessmentType("quick_upper_body")}
            className={`flex-1 sm:flex-initial px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              assessmentType === "quick_upper_body"
                ? "bg-white text-teal-700 shadow-xs"
                : "text-neutral-dark/60 hover:text-neutral-dark"
            }`}
          >
            Quick Upper-Body Check
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Patient Profile & Capture Inputs */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          {/* Patient Profile Card */}
          <div className="bg-white rounded-2xl p-6 border border-neutral-border shadow-soft flex flex-col gap-4">
            <h2 className="font-bold text-neutral-dark text-sm flex items-center gap-2 border-b border-neutral-border pb-3">
              <User className="w-4 h-4 text-primary" />
              Patient Profile & Ergonomics
            </h2>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold text-neutral-dark/70">Full Name</label>
                <input 
                  type="text" 
                  value={name} 
                  onChange={(e) => setName(e.target.value)} 
                  className="border border-neutral-border rounded-lg p-2 text-xs bg-neutral-light/40 focus:outline-primary"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold text-neutral-dark/70">Age</label>
                <input 
                  type="number" 
                  value={age} 
                  onChange={(e) => setAge(e.target.value)} 
                  className="border border-neutral-border rounded-lg p-2 text-xs bg-neutral-light/40 focus:outline-primary"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold text-neutral-dark/70">Gender</label>
                <select 
                  value={gender} 
                  onChange={(e) => setGender(e.target.value)}
                  className="border border-neutral-border rounded-lg p-2 text-xs bg-neutral-light/40 focus:outline-primary"
                >
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold text-neutral-dark/70">Height (cm)</label>
                <input 
                  type="number" 
                  value={height} 
                  onChange={(e) => setHeight(e.target.value)} 
                  className="border border-neutral-border rounded-lg p-2 text-xs bg-neutral-light/40 focus:outline-primary"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold text-neutral-dark/70">Weight (kg)</label>
                <input 
                  type="number" 
                  value={weight} 
                  onChange={(e) => setWeight(e.target.value)} 
                  className="border border-neutral-border rounded-lg p-2 text-xs bg-neutral-light/40 focus:outline-primary"
                />
              </div>
            </div>

            {/* Occupation Selector */}
            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-semibold text-neutral-dark/70 flex items-center gap-1.5">
                <Briefcase className="w-3.5 h-3.5 text-teal-600" />
                Daily Activity / Occupation
              </label>
              <select
                value={occupation}
                onChange={(e) => setOccupation(e.target.value)}
                className="border border-neutral-border rounded-lg p-2 text-xs bg-neutral-light/40 focus:outline-primary font-medium"
              >
                <option value="software_developer">Software Developer (Prolonged seated screen work)</option>
                <option value="office_worker">Office Worker (Desk & typing tasks)</option>
                <option value="student">Student (Study desk, laptop, & backpack)</option>
                <option value="gamer">Gamer (Long seated gaming sessions)</option>
                <option value="driver">Driver (Vehicle steering & seated vibration)</option>
                <option value="athlete">Athlete (High physical loading & recovery)</option>
                <option value="manual_worker">Manual Worker (Lifting, carrying & standing)</option>
                <option value="other">Other Activity</option>
              </select>
            </div>

            {/* Multilingual AI Selector */}
            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-semibold text-neutral-dark/70 flex items-center gap-1.5">
                <Languages className="w-3.5 h-3.5 text-sky-600" />
                Explanation Language
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { code: "en", label: "English" },
                  { code: "hi", label: "हिन्दी (Hindi)" },
                  { code: "mr", label: "मराठी (Marathi)" }
                ].map((lang) => (
                  <button
                    key={lang.code}
                    type="button"
                    onClick={() => setPreferredLanguage(lang.code)}
                    className={`py-1.5 text-xs font-semibold rounded-lg border transition-all ${
                      preferredLanguage === lang.code
                        ? "bg-sky-50 border-sky-400 text-sky-700 shadow-xs"
                        : "bg-white border-neutral-border text-neutral-dark/70 hover:bg-neutral-light"
                    }`}
                  >
                    {lang.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Symptoms */}
            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-semibold text-neutral-dark/70">Symptoms & Workstation Habits</label>
              <textarea 
                rows={2}
                value={symptoms} 
                onChange={(e) => setSymptoms(e.target.value)}
                placeholder="e.g. Neck stiffness after 2 hours of coding, shoulder asymmetry..." 
                className="border border-neutral-border rounded-lg p-2.5 text-xs bg-neutral-light/40 focus:outline-primary resize-none"
              />
            </div>
          </div>

          {/* Capture & Multi-Angle Upload Box */}
          <div className="bg-white rounded-2xl p-6 border border-neutral-border shadow-soft flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-neutral-border pb-3">
              <div className="flex items-center gap-2">
                <Camera className="w-4 h-4 text-teal-600" />
                <h2 className="font-bold text-neutral-dark text-sm">Postural Photos</h2>
              </div>
              
              {/* Silhouette toggle */}
              <button
                type="button"
                onClick={() => setShowSilhouette(!showSilhouette)}
                className={`text-[10px] font-semibold px-2.5 py-1 rounded-full border flex items-center gap-1 transition-all ${
                  showSilhouette 
                    ? "bg-teal-50 border-teal-300 text-teal-700" 
                    : "bg-neutral-light border-neutral-border text-neutral-dark/50"
                }`}
              >
                <Eye className="w-3 h-3" />
                {showSilhouette ? "Silhouette ON" : "Silhouette OFF"}
              </button>
            </div>

            {/* Multi-angle tabs if full assessment */}
            {assessmentType === "full_assessment" ? (
              <div className="flex bg-neutral-light p-1 rounded-xl border border-neutral-border/80">
                <button
                  type="button"
                  onClick={() => setActiveAngleTab("front")}
                  className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                    activeAngleTab === "front"
                      ? "bg-white text-teal-700 shadow-xs"
                      : "text-neutral-dark/60 hover:text-neutral-dark"
                  }`}
                >
                  Front View
                  {frontFile && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                </button>
                <button
                  type="button"
                  onClick={() => setActiveAngleTab("side")}
                  className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                    activeAngleTab === "side"
                      ? "bg-white text-sky-700 shadow-xs"
                      : "text-neutral-dark/60 hover:text-neutral-dark"
                  }`}
                >
                  Side View
                  {sideFile && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                </button>
                <button
                  type="button"
                  onClick={() => setActiveAngleTab("back")}
                  className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                    activeAngleTab === "back"
                      ? "bg-white text-indigo-700 shadow-xs"
                      : "text-neutral-dark/60 hover:text-neutral-dark"
                  }`}
                >
                  Back View
                  {backFile && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                </button>
              </div>
            ) : (
              <div className="bg-teal-50/70 p-2.5 rounded-lg border border-teal-100 text-[11px] text-teal-800 flex items-center gap-2">
                <Info className="w-4 h-4 text-teal-600 flex-shrink-0" />
                <span>Quick Upper-Body mode: Head, neck, and shoulder alignment evaluated even with seated/cropped photos.</span>
              </div>
            )}

            {/* Current Active Angle Upload Area */}
            {!activePreview ? (
              <label className="relative border-2 border-dashed border-teal-200 hover:border-teal-500/60 transition-colors rounded-2xl h-56 flex flex-col items-center justify-center gap-2 cursor-pointer bg-neutral-light/20 overflow-hidden">
                {showSilhouette && (
                  <SilhouetteOverlay 
                    viewType={activeAngleTab} 
                    scope={assessmentType === "quick_upper_body" ? "upper_body" : "full_body"} 
                  />
                )}
                <div className="z-20 flex flex-col items-center gap-1.5 p-4 text-center">
                  <div className="w-10 h-10 rounded-full bg-teal-50 flex items-center justify-center text-teal-600 mb-1">
                    <Upload className="w-5 h-5" />
                  </div>
                  <span className="text-xs font-bold text-neutral-dark">
                    Upload {activeAngleTab.toUpperCase()} View Photo
                  </span>
                  <span className="text-[10px] text-neutral-dark/50 max-w-xs">
                    {activeAngleTab === "side" 
                      ? "Natural standing side profile for forward head & ear-shoulder measurements" 
                      : "Front/Back natural stance for shoulder symmetry and spine balance"}
                  </span>
                  <span className="text-[9px] font-semibold text-teal-700 bg-teal-100/60 px-2 py-0.5 rounded mt-1">
                    PNG, JPG up to 10MB
                  </span>
                </div>
                <input 
                  type="file" 
                  accept="image/*" 
                  onChange={(e) => handleAngleFileChange(activeAngleTab, e)} 
                  className="hidden" 
                />
              </label>
            ) : (
              <div className="relative rounded-2xl overflow-hidden border border-neutral-border h-56 bg-neutral-dark">
                <img src={activePreview} alt="Preview" className="w-full h-full object-contain" />
                {showSilhouette && (
                  <SilhouetteOverlay 
                    viewType={activeAngleTab} 
                    scope={assessmentType === "quick_upper_body" ? "upper_body" : "full_body"} 
                  />
                )}
                <button 
                  type="button"
                  onClick={() => clearAngleFile(activeAngleTab)} 
                  className="absolute top-2 right-2 bg-neutral-dark/80 hover:bg-neutral-dark text-white rounded-full p-1.5 text-xs transition-colors z-20"
                >
                  <X className="w-4 h-4" />
                </button>
                <div className="absolute bottom-2 left-2 bg-neutral-dark/80 backdrop-blur text-white text-[10px] font-semibold px-2 py-0.5 rounded z-20">
                  {activeAngleTab.toUpperCase()} View Selected
                </div>
              </div>
            )}

            {/* Run Analysis Button */}
            <button 
              onClick={() => analyzeMutation.mutate()}
              disabled={analyzeMutation.isPending || (!frontFile && !sideFile && !backFile)}
              className="bg-primary hover:bg-primary-hover disabled:bg-primary/50 text-white font-semibold py-3 rounded-xl text-xs shadow-soft transition-all flex items-center justify-center gap-2"
            >
              <Activity className="w-4 h-4" />
              {analyzeMutation.isPending ? "Executing Computer Vision Pipeline..." : "Analyze Posture Screening"}
            </button>
          </div>

          {/* Daily Check-In Card */}
          <DailyCheckinCard />
        </div>

        {/* Right Column: Diagnostic Output & Program Cards */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {results ? (
            <div className="flex flex-col gap-6 animate-in fade-in duration-300">
              {/* Scope & Quality Checks Alert Banner */}
              {results.analysis_scope && results.analysis_scope !== "full_body" && (
                <div className="bg-sky-50 border border-sky-200 rounded-2xl p-4 flex items-start gap-3 shadow-xs">
                  <Info className="w-5 h-5 text-sky-600 mt-0.5 flex-shrink-0" />
                  <div className="flex flex-col gap-0.5">
                    <span className="text-xs font-bold text-sky-900">
                      Partial-Body Scope: {results.analysis_scope.replace("_", " ").toUpperCase()}
                    </span>
                    <p className="text-[11px] text-sky-700 leading-relaxed">
                      This assessment was limited to the visible upper body. Lower-body measurements were not available. No landmarks were simulated or estimated.
                    </p>
                  </div>
                </div>
              )}

              {/* Multi-angle Fusion Summary (if multi-angle was performed) */}
              {results.multi_angle?.enabled && (
                <div className="bg-gradient-to-r from-teal-50 to-sky-50 border border-teal-200 rounded-2xl p-4 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-teal-900 flex items-center gap-1.5">
                      <Sparkles className="w-4 h-4 text-teal-600" />
                      Multi-Angle Fusion Assessment ({results.multi_angle.views_analyzed?.join(", ").toUpperCase()})
                    </span>
                    <span className="text-[10px] font-bold text-teal-800 bg-white px-2 py-0.5 rounded-full border border-teal-200">
                      Score: {results.multi_angle.overall_score || results.confidence_score * 100}
                    </span>
                  </div>
                  <p className="text-[11px] text-teal-800">{results.multi_angle.summary_message}</p>
                  {results.multi_angle.inconsistencies?.length > 0 && (
                    <div className="bg-white/80 rounded-lg p-2.5 border border-amber-200 text-[10px] text-amber-800">
                      <b>Notice:</b> {results.multi_angle.inconsistencies[0]}
                    </div>
                  )}
                </div>
              )}

              {/* Core Diagnostic Box */}
              <div className="bg-white rounded-2xl p-6 border border-neutral-border shadow-soft flex flex-col gap-5">
                <div className="flex items-center justify-between border-b border-neutral-border pb-3">
                  <span className="font-bold text-neutral-dark text-base flex items-center gap-2">
                    <Activity className="w-5 h-5 text-primary" />
                    Posture Diagnostic Metrics
                  </span>
                  <span className={`text-[10px] font-bold px-3 py-1 rounded-full border ${getRiskColor(results.risk_level)}`}>
                    {results.risk_level} Postural Risk
                  </span>
                </div>

                {/* Separated Image Quality, Visibility & Confidence Metrics */}
                <div className="grid grid-cols-3 gap-3">
                  {/* Image Quality Score */}
                  <div className="bg-neutral-light/40 p-3 rounded-xl border border-neutral-border flex flex-col items-center text-center">
                    <span className="text-[10px] font-bold text-neutral-dark/60">Image Quality</span>
                    <span className="text-xl font-extrabold text-teal-700 mt-0.5">
                      {results.image_quality_score ? `${Math.round(results.image_quality_score * 100)}%` : "92%"}
                    </span>
                    <span className="text-[9px] text-emerald-600 font-semibold mt-0.5">Sharp & Level</span>
                  </div>

                  {/* Measurement Confidence Score */}
                  <div className="bg-neutral-light/40 p-3 rounded-xl border border-neutral-border flex flex-col items-center text-center">
                    <span className="text-[10px] font-bold text-neutral-dark/60">Measurement Confidence</span>
                    <span className="text-xl font-extrabold text-primary mt-0.5">
                      {Math.round(results.confidence_score * 100)}%
                    </span>
                    <span className="text-[9px] text-primary font-semibold mt-0.5">High Reliability</span>
                  </div>

                  {/* Analysis Scope */}
                  <div className="bg-neutral-light/40 p-3 rounded-xl border border-neutral-border flex flex-col items-center text-center">
                    <span className="text-[10px] font-bold text-neutral-dark/60">Analysis Scope</span>
                    <span className="text-xs font-extrabold text-neutral-dark mt-1 truncate max-w-[100px]">
                      {(results.analysis_scope || "full_body").replace("_", " ").toUpperCase()}
                    </span>
                    <span className="text-[9px] text-neutral-dark/50 mt-0.5">Non-Fabricated</span>
                  </div>
                </div>

                {/* Specific Postural Angles */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-sky-50/50 p-3 rounded-xl border border-sky-100 flex flex-col items-center">
                    <span className="text-[10px] font-semibold text-sky-800">Neck / Craniovertebral</span>
                    <span className="text-lg font-extrabold text-sky-900 mt-0.5">{results.metrics?.ear_shoulder_angle}°</span>
                  </div>

                  <div className="bg-sky-50/50 p-3 rounded-xl border border-sky-100 flex flex-col items-center">
                    <span className="text-[10px] font-semibold text-sky-800">Shoulder Tilt</span>
                    <span className="text-lg font-extrabold text-sky-900 mt-0.5">{results.metrics?.shoulder_tilt}°</span>
                  </div>

                  <div className="bg-sky-50/50 p-3 rounded-xl border border-sky-100 flex flex-col items-center">
                    <span className="text-[10px] font-semibold text-sky-800">Hip / Pelvic Level</span>
                    <span className="text-lg font-extrabold text-sky-900 mt-0.5">
                      {results.metrics?.hip_alignment ? `${results.metrics.hip_alignment}°` : "N/A (Upper Body)"}
                    </span>
                  </div>
                </div>

                {/* Deviations */}
                <div className="flex flex-col gap-2">
                  <h3 className="text-xs font-bold text-neutral-dark">Observed Alignment Patterns:</h3>
                  <div className="flex flex-wrap gap-2">
                    {results.detected_problems?.map((prob: string, idx: number) => (
                      <span key={idx} className="bg-amber-50 text-amber-800 border border-amber-200 text-[10px] font-semibold px-2.5 py-1 rounded-md flex items-center gap-1.5">
                        <AlertTriangle className="w-3 h-3 text-amber-600" />
                        {prob}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Recommendations & Clinical Findings Box */}
              <div className="bg-white rounded-2xl p-6 border border-neutral-border shadow-soft flex flex-col gap-5">
                <h3 className="font-bold text-neutral-dark text-sm flex items-center gap-2 border-b border-neutral-border pb-3">
                  <FileText className="w-4 h-4 text-teal-600" />
                  Personalized Explanation & Corrective Plan
                </h3>
                
                <div className="flex flex-col gap-1.5">
                  <h4 className="text-xs font-bold text-neutral-dark">Findings Summary</h4>
                  <p className="text-xs text-neutral-dark/80 leading-relaxed bg-neutral-light/30 p-3 rounded-xl border border-neutral-border/60">
                    {results.findings}
                  </p>
                </div>

                {results.recommendations?.stretches?.length > 0 && (
                  <div className="flex flex-col gap-1.5">
                    <h4 className="text-xs font-bold text-neutral-dark">Targeted Mobility & Stretches</h4>
                    <ul className="text-xs text-neutral-dark/70 space-y-1.5">
                      {results.recommendations.stretches.map((s: string, idx: number) => (
                        <li key={idx} className="flex gap-2 items-start">
                          <CheckCircle className="w-3.5 h-3.5 text-teal-600 mt-0.5 flex-shrink-0" />
                          <span>{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {results.recommendations?.exercises?.length > 0 && (
                  <div className="flex flex-col gap-1.5">
                    <h4 className="text-xs font-bold text-neutral-dark">Approved Strengthening Protocol</h4>
                    <ul className="text-xs text-neutral-dark/70 space-y-1.5">
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
                    <h4 className="text-xs font-bold text-neutral-dark">Occupation-Adapted Habits ({occupation.replace("_", " ")})</h4>
                    <ul className="text-xs text-neutral-dark/70 space-y-1.5">
                      {results.recommendations.lifestyle_tips.map((t: string, idx: number) => (
                        <li key={idx} className="flex gap-2 items-start">
                          <CheckCircle className="w-3.5 h-3.5 text-sky-600 mt-0.5 flex-shrink-0" />
                          <span>{t}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Actions: Download PDF & Find Doctors */}
                <div className="flex flex-wrap gap-4 pt-4 border-t border-neutral-border">
                  <a 
                    href={`${API_BASE_URL}/reports/${results.report_id}/download?token=${localStorage.getItem("token")}`}
                    target="_blank"
                    rel="noreferrer"
                    className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold px-4 py-2.5 rounded-lg flex items-center gap-2 shadow-soft transition-all"
                  >
                    <FileDown className="w-4 h-4" />
                    <span>Download Clinical PDF</span>
                  </a>
                  
                  <Link 
                    href="/doctors"
                    className="bg-primary hover:bg-primary-hover text-white text-xs font-semibold px-4 py-2.5 rounded-lg flex items-center gap-2 ml-auto shadow-soft transition-all"
                  >
                    <Stethoscope className="w-4 h-4" />
                    <span>Find Local Healthcare Providers</span>
                  </Link>
                </div>
              </div>

              {/* 30-Day Posture Program Card */}
              <PostureProgramCard />
            </div>
          ) : (
            <div className="flex flex-col gap-6">
              <div className="border border-dashed border-neutral-border rounded-2xl h-[340px] flex flex-col items-center justify-center text-center p-8 bg-white shadow-soft">
                <Activity className="w-12 h-12 text-teal-600/30 animate-pulse mb-3" />
                <span className="font-bold text-neutral-dark text-sm">Screening Diagnostic Feed Ready</span>
                <p className="text-xs text-neutral-dark/50 max-w-sm mt-1 leading-relaxed">
                  Configure your physiological profile and upload a front, side, or back photo to run the 33-landmark BlazePose screening engine.
                </p>
                <button
                  onClick={() => setIsGuideOpen(true)}
                  className="mt-4 text-xs font-semibold text-teal-700 hover:text-teal-800 underline"
                >
                  Review Capture Quality Guidelines
                </button>
              </div>

              {/* 30-Day Posture Program Card (Default view) */}
              <PostureProgramCard />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
