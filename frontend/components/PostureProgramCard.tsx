"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { programApi } from "@/lib/api";
import { Calendar, CheckCircle2, ChevronRight, Dumbbell, ShieldCheck, Sparkles } from "lucide-react";

export function PostureProgramCard() {
  const queryClient = useQueryClient();
  const [activeDayIdx, setActiveDayIdx] = useState<number>(1);

  const { data: program, isLoading, isError } = useQuery({
    queryKey: ["activeProgram"],
    queryFn: programApi.getActiveProgram,
  });

  const generateMutation = useMutation({
    mutationFn: programApi.generateProgram,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activeProgram"] });
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || "Could not generate posture plan. Please complete an initial scan first.");
    },
  });

  const completeDayMutation = useMutation({
    mutationFn: (dayNum: number) => programApi.completeProgramDay(dayNum),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activeProgram"] });
    },
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl p-6 border border-neutral-border shadow-soft flex items-center justify-center py-12">
        <span className="text-xs text-neutral-dark/50">Loading your posture program...</span>
      </div>
    );
  }

  if (isError || !program) {
    return (
      <div className="bg-gradient-to-br from-white to-neutral-light/50 rounded-2xl p-6 border border-neutral-border shadow-soft flex flex-col gap-4">
        <div className="flex items-center gap-2 border-b border-neutral-border pb-3">
          <Dumbbell className="w-5 h-5 text-primary" />
          <h3 className="font-bold text-neutral-dark text-sm">Personalized 30-Day Posture Program</h3>
        </div>
        <p className="text-xs text-neutral-dark/70 leading-relaxed">
          Get a structured 4-week posture rehabilitation plan tailored to your postural measurements, symptoms, and occupation using evidence-backed physical therapy exercises.
        </p>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="bg-primary hover:bg-primary-hover text-white text-xs font-semibold py-2.5 px-4 rounded-lg flex items-center justify-center gap-2 transition-all shadow-soft self-start"
        >
          <Sparkles className="w-4 h-4" />
          {generateMutation.isPending ? "Generating 30-Day Plan..." : "Generate 30-Day Posture Plan"}
        </button>
      </div>
    );
  }

  const daysCompleted = program.days_completed || 0;
  const currentDay = program.current_day || 1;
  const planDays = program.plan_data?.days || [];
  const selectedDayData = planDays.find((d: any) => d.day === activeDayIdx) || planDays[currentDay - 1] || planDays[0];

  return (
    <div className="bg-white rounded-2xl p-6 border border-neutral-border shadow-soft flex flex-col gap-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-neutral-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Dumbbell className="w-5 h-5 text-primary" />
            <h3 className="font-bold text-neutral-dark text-sm">{program.title}</h3>
          </div>
          <p className="text-[11px] text-neutral-dark/60 mt-0.5">{program.description}</p>
        </div>

        {/* Progress badge */}
        <div className="flex items-center gap-3">
          <div className="flex flex-col text-right">
            <span className="text-[11px] font-bold text-neutral-dark">Day {currentDay} of 30</span>
            <span className="text-[10px] text-neutral-dark/50">{daysCompleted} days completed</span>
          </div>
          <div className="w-12 h-12 rounded-full border-4 border-primary/20 border-t-primary flex items-center justify-center font-bold text-xs text-primary">
            {Math.round((daysCompleted / 30) * 100)}%
          </div>
        </div>
      </div>

      {/* 4-Week Milestone Indicator */}
      <div className="grid grid-cols-4 gap-2 text-center">
        {[
          { week: 1, label: "Awareness & Mobility", days: "1-7" },
          { week: 2, label: "Mobility & Strength", days: "8-14" },
          { week: 3, label: "Strength & Posture", days: "15-21" },
          { week: 4, label: "Maintenance", days: "22-30" },
        ].map((phase) => {
          const isCurrentPhase = currentDay >= (phase.week - 1) * 7 + 1 && currentDay <= phase.week * 7 + (phase.week === 4 ? 2 : 0);
          return (
            <div 
              key={phase.week} 
              className={`p-2 rounded-lg border text-left transition-all ${
                isCurrentPhase 
                  ? "bg-primary/5 border-primary text-primary" 
                  : "bg-neutral-light/40 border-neutral-border/60 text-neutral-dark/60"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold">Week {phase.week}</span>
                <span className="text-[9px] opacity-70">Days {phase.days}</span>
              </div>
              <p className="text-[10px] font-medium truncate mt-0.5">{phase.label}</p>
            </div>
          );
        })}
      </div>

      {/* Selected Day View */}
      {selectedDayData && (
        <div className="bg-neutral-light/30 rounded-xl p-4 border border-neutral-border/70 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-neutral-dark flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-primary" />
              Day {selectedDayData.day}: {selectedDayData.focus}
            </span>
            {selectedDayData.day <= daysCompleted ? (
              <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Completed
              </span>
            ) : (
              <span className="text-[10px] font-semibold text-neutral-dark/50">Upcoming</span>
            )}
          </div>

          {/* Exercise cards for this day */}
          <div className="flex flex-col gap-2">
            {selectedDayData.exercises?.map((ex: any, idx: number) => (
              <div key={idx} className="bg-white p-3 rounded-lg border border-neutral-border shadow-xs flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-neutral-dark">{ex.name}</span>
                  <span className="text-[10px] font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded">
                    {ex.duration || `${ex.reps || "10"} reps`}
                  </span>
                </div>
                <p className="text-[11px] text-neutral-dark/70">{ex.instructions}</p>
                {ex.safety_note && (
                  <div className="flex items-center gap-1.5 text-[10px] text-amber-700 mt-0.5">
                    <ShieldCheck className="w-3 h-3 flex-shrink-0 text-amber-600" />
                    <span>Safety: {ex.safety_note}</span>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Complete day button */}
          {selectedDayData.day === currentDay && daysCompleted < currentDay && (
            <button
              onClick={() => completeDayMutation.mutate(currentDay)}
              disabled={completeDayMutation.isPending}
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold py-2.5 px-4 rounded-lg flex items-center justify-center gap-2 transition-all shadow-soft mt-1"
            >
              <CheckCircle2 className="w-4 h-4" />
              {completeDayMutation.isPending ? "Marking Complete..." : `Mark Day ${currentDay} Complete`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
