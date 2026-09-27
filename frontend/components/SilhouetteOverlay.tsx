"use client";

import React from "react";

interface SilhouetteOverlayProps {
  viewType?: "front" | "side" | "back";
  scope?: "upper_body" | "full_body";
}

export function SilhouetteOverlay({ viewType = "front", scope = "full_body" }: SilhouetteOverlayProps) {
  const isSide = viewType === "side";
  const isUpper = scope === "upper_body";

  return (
    <div className="absolute inset-0 pointer-events-none flex items-center justify-center overflow-hidden z-10">
      <svg 
        viewBox="0 0 200 300" 
        className="w-full h-full max-h-full object-contain opacity-55 transition-opacity duration-300"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <linearGradient id="overlayTeal" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0D9488" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#0284C7" stopOpacity="0.85" />
          </linearGradient>
        </defs>

        {/* Central Vertical Plumbline (Gravity Axis) */}
        <line 
          x1="100" 
          y1="10" 
          x2="100" 
          y2={isUpper ? "240" : "290"} 
          stroke="#0D9488" 
          strokeWidth="1.2" 
          strokeDasharray="3 3" 
        />

        {isSide ? (
          /* Side Profile Silhouette Guides */
          <g stroke="url(#overlayTeal)" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            {/* Head */}
            <circle cx="95" cy="45" r="22" strokeDasharray="3 2" />
            {/* Ear reference marker */}
            <circle cx="95" cy="45" r="3" fill="#0D9488" />
            
            {/* Neck & Spine S-Curve */}
            <path d="M 95,67 C 104,95 86,130 96,165" strokeWidth="2" />
            
            {/* Shoulder point */}
            <circle cx="102" cy="90" r="3.5" fill="#0284C7" />
            
            {/* Chest reference */}
            <path d="M 102,90 C 120,110 115,140 100,165" strokeDasharray="2 2" strokeWidth="1" />
            
            {/* Pelvis/Hip Marker */}
            {!isUpper && (
              <>
                <circle cx="98" cy="165" r="4" fill="#0D9488" />
                {/* Leg & Ankle Line */}
                <path d="M 98,169 L 100,230 L 102,280" strokeWidth="1.8" />
                <circle cx="100" cy="230" r="3" fill="#0284C7" />
                <circle cx="102" cy="280" r="3" fill="#0284C7" />
              </>
            )}
          </g>
        ) : (
          /* Front & Back Silhouette Guides */
          <g stroke="url(#overlayTeal)" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            {/* Head circle */}
            <circle cx="100" cy="42" r="21" strokeDasharray="3 2" />
            <circle cx="100" cy="42" r="2" fill="#0D9488" />

            {/* Neck line */}
            <line x1="100" y1="63" x2="100" y2="78" strokeWidth="2" />

            {/* Shoulder Horizontal Level Line */}
            <line x1="55" y1="84" x2="145" y2="84" strokeWidth="1.8" />
            <circle cx="58" cy="84" r="3.5" fill="#0284C7" />
            <circle cx="142" cy="84" r="3.5" fill="#0284C7" />

            {/* Torso & Spine */}
            <line x1="100" y1="78" x2="100" y2="160" strokeWidth="2" />
            
            {/* Arms */}
            <path d="M 58,84 L 46,140" strokeWidth="1.4" />
            <path d="M 142,84 L 154,140" strokeWidth="1.4" />

            {/* Pelvis / Hip Horizontal Level Line */}
            <line x1="68" y1="160" x2="132" y2="160" strokeWidth="1.8" />
            <circle cx="70" cy="160" r="3.5" fill="#0D9488" />
            <circle cx="130" cy="160" r="3.5" fill="#0D9488" />

            {!isUpper && (
              <>
                {/* Legs */}
                <path d="M 75,160 L 78,225 L 80,282" strokeWidth="1.6" />
                <path d="M 125,160 L 122,225 L 120,282" strokeWidth="1.6" />

                {/* Knee Markers */}
                <circle cx="78" cy="225" r="3" fill="#0284C7" />
                <circle cx="122" cy="225" r="3" fill="#0284C7" />

                {/* Ankle Markers */}
                <circle cx="80" cy="282" r="3" fill="#0D9488" />
                <circle cx="120" cy="282" r="3" fill="#0D9488" />
              </>
            )}
          </g>
        )}

        {/* Framing Guides / Corner Reticles */}
        <g stroke="#0D9488" strokeWidth="1.2" opacity="0.6">
          <path d="M 15,30 L 15,15 L 30,15" fill="none" />
          <path d="M 185,30 L 185,15 L 170,15" fill="none" />
          <path d="M 15,270 L 15,285 L 30,285" fill="none" />
          <path d="M 185,270 L 185,285 L 170,285" fill="none" />
        </g>
      </svg>
      
      {/* Badge in top left corner */}
      <div className="absolute top-2 left-2 bg-neutral-dark/70 backdrop-blur text-[10px] font-semibold text-teal-300 px-2 py-0.5 rounded border border-teal-500/30">
        Silhouette Overlay · {isSide ? "Side View" : "Front/Back View"}
      </div>
    </div>
  );
}
