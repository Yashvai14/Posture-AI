import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";
import Link from "next/link";
import { Activity, Shield, Users, Heart } from "lucide-react";

export const metadata: Metadata = {
  title: "PostureAI - Premium AI Posture Assessment & Healthcare",
  description: "Detect posture deviations, receive AI-guided therapeutic exercises, and connect with expert nearby clinics.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossOrigin="" />
      </head>
      <body className="min-h-screen flex flex-col justify-between bg-neutral-light">
        <Providers>
          {/* Glassmorphism Navigation Bar */}
          <nav className="sticky top-0 z-50 glass-nav">
            <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
              <Link href="/" className="flex items-center gap-2 text-primary font-bold text-xl">
                <Activity className="w-6 h-6 stroke-[2.5]" />
                <span>Posture<span className="text-secondary">AI</span></span>
              </Link>
              
              <div className="hidden md:flex items-center gap-8 text-sm font-medium text-neutral-dark/80">
                <Link href="/" className="hover:text-primary transition-colors">Home</Link>
                <Link href="/dashboard" className="hover:text-primary transition-colors">Dashboard</Link>
                <Link href="/history" className="hover:text-primary transition-colors">Patient History</Link>
                <Link href="/doctors" className="hover:text-primary transition-colors">Find Doctors</Link>
              </div>

              <div>
                <Link href="/dashboard" className="bg-primary hover:bg-primary-hover text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-all duration-300 transform active:scale-95 shadow-soft">
                  Get Started
                </Link>
              </div>
            </div>
          </nav>

          {/* Core App View */}
          <main className="flex-grow">
            {children}
          </main>

          {/* Footer Component */}
          <footer className="bg-white border-t border-neutral-border py-12">
            <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 md:grid-cols-4 gap-8">
              <div className="flex flex-col gap-3">
                <span className="text-primary font-bold text-lg flex items-center gap-2">
                  <Activity className="w-5 h-5" />
                  PostureAI
                </span>
                <p className="text-xs text-neutral-dark/60 leading-relaxed">
                  Advancing preventative musculoskeletal health using cutting-edge computer vision and local edge-AI reasoning models.
                </p>
              </div>
              <div>
                <h4 className="text-sm font-semibold text-neutral-dark mb-4">Features</h4>
                <ul className="text-xs text-neutral-dark/60 space-y-2">
                  <li><Link href="/dashboard" className="hover:text-primary">Posture Analyzer</Link></li>
                  <li><Link href="/history" className="hover:text-primary">Patient History Tracker</Link></li>
                  <li><Link href="/doctors" className="hover:text-primary">Doctor Finder Maps</Link></li>
                </ul>
              </div>
              <div>
                <h4 className="text-sm font-semibold text-neutral-dark mb-4">Resources</h4>
                <ul className="text-xs text-neutral-dark/60 space-y-2">
                  <li><Link href="#" className="hover:text-primary">Medical Disclaimer</Link></li>
                  <li><Link href="#" className="hover:text-primary">API Documentation</Link></li>
                  <li><Link href="#" className="hover:text-primary">GitHub Codebase</Link></li>
                </ul>
              </div>
              <div>
                <h4 className="text-sm font-semibold text-neutral-dark mb-4">Legal</h4>
                <ul className="text-xs text-neutral-dark/60 space-y-2">
                  <li><Link href="#" className="hover:text-primary">Privacy Policy</Link></li>
                  <li><Link href="#" className="hover:text-primary">Terms of Use</Link></li>
                  <li><Link href="#" className="hover:text-primary">HIPAA Compliance</Link></li>
                </ul>
              </div>
            </div>
            <div className="max-w-7xl mx-auto px-6 mt-8 pt-8 border-t border-neutral-border flex flex-col md:flex-row items-center justify-between text-xs text-neutral-dark/40">
              <span>&copy; {new Date().getFullYear()} PostureAI Inc. All rights reserved.</span>
              <span className="flex items-center gap-1 mt-4 md:mt-0">
                Created with <Heart className="w-3.5 h-3.5 text-red-500 fill-red-500" /> for anatomical health.
              </span>
            </div>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
