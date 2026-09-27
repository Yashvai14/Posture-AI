"use client";

import React from "react";
import { X, CheckCircle2, AlertCircle, Camera, Sparkles } from "lucide-react";

interface CaptureGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CaptureGuideModal({ isOpen, onClose }: CaptureGuideModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-dark/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-neutral-border shadow-2xl flex flex-col"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="p-6 border-b border-neutral-border flex items-center justify-between sticky top-0 bg-white/95 backdrop-blur z-10">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-teal-50 border border-teal-100 flex items-center justify-center text-teal-600">
              <Camera className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-neutral-dark">Posture Capture Guide</h2>
              <p className="text-xs text-neutral-dark/60">Follow these guidelines for accurate computer-vision measurements</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="w-8 h-8 rounded-full hover:bg-neutral-light text-neutral-dark/60 hover:text-neutral-dark flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 flex flex-col gap-6">
          {/* Visual Silhouette Demonstration */}
          <div className="bg-gradient-to-br from-teal-50/70 via-sky-50/40 to-blue-50/60 rounded-xl p-5 border border-teal-100 flex flex-col md:flex-row items-center justify-around gap-4">
            {/* Front View Outline */}
            <div className="flex flex-col items-center gap-2 text-center">
              <div className="w-24 h-36 bg-white/80 rounded-lg border border-teal-200 flex flex-col items-center justify-center relative shadow-sm">
                <svg viewBox="0 0 60 90" className="w-16 h-28 text-teal-500">
                  <circle cx="30" cy="14" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
                  <path d="M 30,21 L 30,52" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="2,2" />
                  <line x1="16" y1="27" x2="44" y2="27" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <line x1="20" y1="52" x2="40" y2="52" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <path d="M 16,27 L 12,50" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <path d="M 44,27 L 48,50" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <path d="M 23,52 L 21,84" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <path d="M 37,52 L 39,84" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                <span className="absolute bottom-1 text-[9px] font-bold text-teal-700 bg-teal-50/90 px-1.5 py-0.5 rounded">Front View</span>
              </div>
              <span className="text-[11px] font-semibold text-neutral-dark">Shoulder & Hip Tilt</span>
            </div>

            {/* Side View Outline */}
            <div className="flex flex-col items-center gap-2 text-center">
              <div className="w-24 h-36 bg-white/80 rounded-lg border border-teal-200 flex flex-col items-center justify-center relative shadow-sm">
                <svg viewBox="0 0 60 90" className="w-16 h-28 text-sky-500">
                  <circle cx="26" cy="14" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
                  <path d="M 28,21 C 32,32 25,44 28,52" fill="none" stroke="currentColor" strokeWidth="2" />
                  <line x1="28" y1="5" x2="28" y2="85" stroke="#94A3B8" strokeWidth="1" strokeDasharray="2,2" />
                  <circle cx="28" cy="27" r="2" fill="currentColor" />
                  <path d="M 28,52 L 29,84" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                <span className="absolute bottom-1 text-[9px] font-bold text-sky-700 bg-sky-50/90 px-1.5 py-0.5 rounded">Side View</span>
              </div>
              <span className="text-[11px] font-semibold text-neutral-dark">Forward Head & Spine</span>
            </div>

            {/* Back View Outline */}
            <div className="flex flex-col items-center gap-2 text-center">
              <div className="w-24 h-36 bg-white/80 rounded-lg border border-teal-200 flex flex-col items-center justify-center relative shadow-sm">
                <svg viewBox="0 0 60 90" className="w-16 h-28 text-indigo-500">
                  <circle cx="30" cy="14" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
                  <line x1="30" y1="21" x2="30" y2="52" stroke="currentColor" strokeWidth="2" />
                  <line x1="16" y1="27" x2="44" y2="27" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <line x1="20" y1="52" x2="40" y2="52" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <path d="M 16,27 L 12,50" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <path d="M 44,27 L 48,50" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <path d="M 23,52 L 21,84" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <path d="M 37,52 L 39,84" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                <span className="absolute bottom-1 text-[9px] font-bold text-indigo-700 bg-indigo-50/90 px-1.5 py-0.5 rounded">Back View</span>
              </div>
              <span className="text-[11px] font-semibold text-neutral-dark">Scapular & Pelvic Level</span>
            </div>
          </div>

          {/* Golden Rules */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="flex gap-2.5 items-start p-3 rounded-xl bg-neutral-light/50 border border-neutral-border">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-xs font-bold text-neutral-dark">Stand Naturally</h4>
                <p className="text-[11px] text-neutral-dark/70 mt-0.5">Do not force an unnaturally upright posture. PostureAI evaluates your habitual alignment.</p>
              </div>
            </div>

            <div className="flex gap-2.5 items-start p-3 rounded-xl bg-neutral-light/50 border border-neutral-border">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-xs font-bold text-neutral-dark">Camera at Mid-Torso Height</h4>
                <p className="text-[11px] text-neutral-dark/70 mt-0.5">Position your phone or camera level with your chest/navel (about 3-4 feet high), not tilted downwards.</p>
              </div>
            </div>

            <div className="flex gap-2.5 items-start p-3 rounded-xl bg-neutral-light/50 border border-neutral-border">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-xs font-bold text-neutral-dark">Upper Body or Full Body</h4>
                <p className="text-[11px] text-neutral-dark/70 mt-0.5">Full body is recommended. If only your upper body is in frame, PostureAI will perform an upper-body analysis without guessing lower limbs.</p>
              </div>
            </div>

            <div className="flex gap-2.5 items-start p-3 rounded-xl bg-neutral-light/50 border border-neutral-border">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-xs font-bold text-neutral-dark">Clear, Uniform Lighting</h4>
                <p className="text-[11px] text-neutral-dark/70 mt-0.5">Ensure even light facing you. Avoid standing directly in front of bright windows with strong backlights.</p>
              </div>
            </div>

            <div className="flex gap-2.5 items-start p-3 rounded-xl bg-neutral-light/50 border border-neutral-border">
              <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-xs font-bold text-neutral-dark">Single Subject Only</h4>
                <p className="text-[11px] text-neutral-dark/70 mt-0.5">Ensure only one person is visible in frame to prevent landmark confusion.</p>
              </div>
            </div>

            <div className="flex gap-2.5 items-start p-3 rounded-xl bg-neutral-light/50 border border-neutral-border">
              <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-xs font-bold text-neutral-dark">Avoid Heavy Bulky Clothes</h4>
                <p className="text-[11px] text-neutral-dark/70 mt-0.5">Oversized coats or baggy hoodies can mask true anatomical joint centers and shoulder alignment.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-neutral-border bg-neutral-light/30 flex items-center justify-between">
          <span className="text-[11px] text-neutral-dark/60 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-teal-600" />
            Quality-aware MediaPipe vision engine
          </span>
          <button
            onClick={onClose}
            className="bg-primary hover:bg-primary-hover text-white text-xs font-semibold px-5 py-2.5 rounded-lg shadow-soft transition-all"
          >
            I Understand, Continue
          </button>
        </div>
      </div>
    </div>
  );
}
