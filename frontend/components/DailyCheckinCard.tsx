"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { programApi } from "@/lib/api";
import { Activity, CheckCircle2, HeartPulse, Send, Sparkles } from "lucide-react";

export function DailyCheckinCard() {
  const queryClient = useQueryClient();
  const [neck, setNeck] = useState<number>(2);
  const [shoulder, setShoulder] = useState<number>(3);
  const [back, setBack] = useState<number>(2);
  const [completed, setCompleted] = useState<string>("yes");
  const [notes, setNotes] = useState<string>("");
  const [submittedToday, setSubmittedToday] = useState<boolean>(false);

  const { data: checkins } = useQuery({
    queryKey: ["checkins"],
    queryFn: programApi.getCheckins,
  });

  const checkinMutation = useMutation({
    mutationFn: async () => {
      return await programApi.submitCheckin({
        neck_discomfort: neck,
        shoulder_discomfort: shoulder,
        back_discomfort: back,
        exercises_completed: completed,
        notes: notes.trim() || undefined,
      });
    },
    onSuccess: () => {
      setSubmittedToday(true);
      queryClient.invalidateQueries({ queryKey: ["checkins"] });
      queryClient.invalidateQueries({ queryKey: ["weeklySummary"] });
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || "Failed to save daily check-in.");
    },
  });

  return (
    <div className="bg-white rounded-2xl p-6 border border-neutral-border shadow-soft flex flex-col gap-5">
      <div className="flex items-center justify-between border-b border-neutral-border pb-3">
        <div className="flex items-center gap-2">
          <HeartPulse className="w-5 h-5 text-teal-600" />
          <h3 className="font-bold text-neutral-dark text-sm">Daily Symptom & Habit Check-In</h3>
        </div>
        <span className="text-[10px] font-semibold text-neutral-dark/50 bg-neutral-light px-2.5 py-1 rounded-full">
          Track Consistency
        </span>
      </div>

      {submittedToday ? (
        <div className="bg-teal-50 border border-teal-200 rounded-xl p-5 flex flex-col items-center justify-center text-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-8 h-8 text-teal-600" />
          <h4 className="text-xs font-bold text-teal-900">Check-In Recorded For Today!</h4>
          <p className="text-[11px] text-teal-700 max-w-sm">
            Thank you for checking in. Your daily discomfort logs help tailor weekly summaries and ergonomic insights.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <p className="text-xs text-neutral-dark/70">
            How are you feeling today? Rate discomfort on a 1 (minimal) to 10 (intense) scale:
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Neck Discomfort */}
            <div className="bg-neutral-light/40 p-3.5 rounded-xl border border-neutral-border/70 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-neutral-dark">Neck Discomfort</label>
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${neck > 5 ? "bg-amber-100 text-amber-700" : "bg-teal-100 text-teal-700"}`}>
                  {neck}/10
                </span>
              </div>
              <input 
                type="range" 
                min={1} 
                max={10} 
                value={neck} 
                onChange={(e) => setNeck(Number(e.target.value))}
                className="w-full accent-teal-600 cursor-pointer h-1.5 bg-neutral-border rounded-lg"
              />
            </div>

            {/* Shoulder Discomfort */}
            <div className="bg-neutral-light/40 p-3.5 rounded-xl border border-neutral-border/70 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-neutral-dark">Shoulder Discomfort</label>
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${shoulder > 5 ? "bg-amber-100 text-amber-700" : "bg-teal-100 text-teal-700"}`}>
                  {shoulder}/10
                </span>
              </div>
              <input 
                type="range" 
                min={1} 
                max={10} 
                value={shoulder} 
                onChange={(e) => setShoulder(Number(e.target.value))}
                className="w-full accent-teal-600 cursor-pointer h-1.5 bg-neutral-border rounded-lg"
              />
            </div>

            {/* Back Discomfort */}
            <div className="bg-neutral-light/40 p-3.5 rounded-xl border border-neutral-border/70 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-neutral-dark">Back Discomfort</label>
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${back > 5 ? "bg-amber-100 text-amber-700" : "bg-teal-100 text-teal-700"}`}>
                  {back}/10
                </span>
              </div>
              <input 
                type="range" 
                min={1} 
                max={10} 
                value={back} 
                onChange={(e) => setBack(Number(e.target.value))}
                className="w-full accent-teal-600 cursor-pointer h-1.5 bg-neutral-border rounded-lg"
              />
            </div>
          </div>

          {/* Exercise Completion */}
          <div className="flex flex-col gap-2">
            <label className="text-xs font-semibold text-neutral-dark">Did you complete today's mobility / posture exercises?</label>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Yes, fully", value: "yes" },
                { label: "Partially", value: "partially" },
                { label: "Not today", value: "no" }
              ].map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setCompleted(opt.value)}
                  className={`py-2 text-xs font-semibold rounded-lg border transition-all ${
                    completed === opt.value
                      ? "bg-teal-50 border-teal-500 text-teal-700 shadow-sm"
                      : "bg-white border-neutral-border text-neutral-dark/70 hover:bg-neutral-light"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <button
            type="button"
            onClick={() => checkinMutation.mutate()}
            disabled={checkinMutation.isPending}
            className="bg-teal-600 hover:bg-teal-700 disabled:bg-teal-400 text-white font-semibold text-xs py-2.5 rounded-lg flex items-center justify-center gap-2 transition-colors mt-1 shadow-soft"
          >
            <Send className="w-3.5 h-3.5" />
            {checkinMutation.isPending ? "Submitting Check-In..." : "Save Today's Check-In"}
          </button>
        </div>
      )}
    </div>
  );
}
