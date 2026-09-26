"use client";

import Link from "next/link";
import { useState } from "react";
import { motion } from "framer-motion";
import { 
  Activity, 
  Sparkles, 
  MapPin, 
  FileText, 
  Calendar, 
  ArrowRight,
  TrendingUp,
  BrainCircuit,
  Lock,
  ChevronDown
} from "lucide-react";

export default function HomePage() {
  const [activeFaq, setActiveFaq] = useState<number | null>(null);

  const stats = [
    { value: "98.4%", label: "Detection Accuracy" },
    { value: "10K+", label: "Images Analyzed" },
    { value: "450+", label: "Doctors Connected" },
    { value: "100%", label: "Local Data Privacy" }
  ];

  const features = [
    {
      icon: <BrainCircuit className="w-6 h-6 text-primary" />,
      title: "AI Posture Detection",
      desc: "Instant assessment of shoulder tilt, neck forward angle, and back curvature using local model estimation."
    },
    {
      icon: <Sparkles className="w-6 h-6 text-secondary" />,
      title: "Local LLM Insights (Ollama)",
      desc: "A local instance of Llama3 or Mistral processes your symptoms and generates physical recommendations."
    },
    {
      icon: <FileText className="w-6 h-6 text-accent" />,
      title: "Personalized Health Reports",
      desc: "Receive and download a hospital-grade PDF listing corrective stretches, daily habits, and workstation setups."
    },
    {
      icon: <MapPin className="w-6 h-6 text-primary" />,
      title: "Nearby Doctor Finder",
      desc: "Locate expert orthopedics and physiotherapists within 30 KM using dynamic geographical coordinate matching."
    },
    {
      icon: <Calendar className="w-6 h-6 text-secondary" />,
      title: "Appointment Booking",
      desc: "Seamless booking flows to lock in consultations with verified therapists directly through the portal."
    },
    {
      icon: <Lock className="w-6 h-6 text-accent" />,
      title: "HIPAA-grade Privacy",
      desc: "No health data leaves your local network. Private storage ensures your scan remains confidential."
    }
  ];

  const faqs = [
    {
      q: "How accurate is the posture detection engine?",
      a: "Our system estimates skeletal angles such as ear-to-shoulder tilt and neck forward lines with high precision, matching standard clinical metrics."
    },
    {
      q: "Is my personal data kept private?",
      a: "Yes, absolutely. Since the AI model runs locally on Ollama, your images, details, and symptoms do not leave your system, maintaining complete data confidentiality."
    },
    {
      q: "Does it require a continuous internet connection?",
      a: "You need internet only to pull nearby clinic maps and register. The core posture evaluation and LLM reasoning run entirely locally."
    },
    {
      q: "Can this system replace a physical orthopedic doctor?",
      a: "No. PostureAI is designed for preventative and wellness screening. We strongly provide direct integration with nearby licensed specialists to get official clinical care."
    }
  ];

  return (
    <div className="relative overflow-hidden">
      {/* Background Decor */}
      <div className="absolute top-[-10%] left-[-10%] w-[40rem] h-[40rem] rounded-full bg-primary-light/50 blur-[120px] -z-10" />
      <div className="absolute bottom-[20%] right-[-10%] w-[35rem] h-[35rem] rounded-full bg-secondary-light/40 blur-[120px] -z-10" />

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-6 pt-20 pb-16 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        <div className="flex flex-col gap-6">
          <div className="inline-flex items-center gap-2 bg-primary-light text-primary text-xs font-semibold px-3.5 py-1.5 rounded-full border border-primary/10 w-fit">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Next-Gen Anatomical AI</span>
          </div>
          
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight text-neutral-dark leading-[1.1]">
            AI-Powered Posture Analysis for a <span className="text-primary">Healthier Life</span>
          </h1>
          
          <p className="text-neutral-dark/70 text-lg leading-relaxed max-w-xl">
            Upload a photo to instantly identify alignment conditions, receive local AI recommendations, and schedule sessions with leading local therapists.
          </p>

          <div className="flex flex-wrap gap-4 mt-2">
            <Link href="/dashboard" className="btn-primary inline-flex items-center gap-2">
              <span>Analyze My Posture</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link href="#features" className="btn-secondary">
              Learn More
            </Link>
          </div>
        </div>

        {/* Hero Visual Mockup */}
        <div className="relative flex justify-center">
          <div className="w-full max-w-md bg-white rounded-xl shadow-premium border border-neutral-border p-6 relative overflow-hidden">
            <div className="absolute top-3 right-3 bg-accent-light text-accent text-[10px] font-bold px-2 py-1 rounded-full">
              Skeletal Mesh OK
            </div>
            
            <div className="h-64 rounded-lg bg-neutral-light border border-dashed border-neutral-border flex flex-col items-center justify-center gap-3">
              <Activity className="w-12 h-12 text-primary animate-pulse" />
              <span className="text-xs text-neutral-dark/40 font-medium">Posture Detection Sandbox Ready</span>
            </div>

            <div className="mt-6 flex flex-col gap-3">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-neutral-dark">Neck forward deviation</span>
                <span className="text-red-500 font-bold">24° (High Risk)</span>
              </div>
              <div className="w-full bg-neutral-light h-2 rounded-full overflow-hidden">
                <div className="bg-red-500 h-full w-[75%]" />
              </div>
              
              <div className="flex justify-between items-center text-xs mt-1">
                <span className="font-semibold text-neutral-dark">Shoulder symmetry</span>
                <span className="text-accent font-bold">Normal</span>
              </div>
              <div className="w-full bg-neutral-light h-2 rounded-full overflow-hidden">
                <div className="bg-accent h-full w-[95%]" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Board */}
      <section className="bg-white border-y border-neutral-border py-10 my-10">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((stat, i) => (
            <div key={i} className="flex flex-col items-center justify-center text-center">
              <span className="text-3xl md:text-4xl font-extrabold text-primary">{stat.value}</span>
              <span className="text-xs font-medium text-neutral-dark/60 mt-1.5">{stat.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="max-w-7xl mx-auto px-6 py-16 flex flex-col gap-12">
        <div className="text-center max-w-2xl mx-auto flex flex-col gap-3">
          <h2 className="text-3xl font-bold text-neutral-dark">Clinical features, engineered locally</h2>
          <p className="text-sm text-neutral-dark/60 leading-relaxed">
            All the tools you need to assess, track, and optimize your musculoskeletal framework safely.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feat, i) => (
            <div key={i} className="bg-white p-6 rounded-xl border border-neutral-border shadow-soft flex flex-col gap-4 hover:border-primary/20 transition-all duration-300">
              <div className="w-12 h-12 rounded-lg bg-neutral-light flex items-center justify-center">
                {feat.icon}
              </div>
              <h3 className="font-bold text-neutral-dark text-lg">{feat.title}</h3>
              <p className="text-xs text-neutral-dark/60 leading-relaxed">{feat.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="bg-neutral-light border-y border-neutral-border py-16 my-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col gap-12">
          <div className="text-center max-w-2xl mx-auto">
            <h2 className="text-3xl font-bold text-neutral-dark">How PostureAI Works</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 text-center">
            {[
              { step: "1", title: "Upload Profile Image", desc: "Upload a side or front image of your standing posture." },
              { step: "2", title: "Describe Symptoms", desc: "Detail any localized tightness, muscle aches, or workspace habits." },
              { step: "3", title: "Verify AI Diagnostics", desc: "Our local model extracts joint lines and produces recommendations." },
              { step: "4", title: "Consult Local Clinics", desc: "Download report and map coordinates to book professional care." }
            ].map((s, idx) => (
              <div key={idx} className="flex flex-col items-center gap-3 relative">
                <div className="w-12 h-12 rounded-full bg-primary text-white font-extrabold flex items-center justify-center text-lg shadow-soft">
                  {s.step}
                </div>
                <h4 className="font-bold text-neutral-dark mt-2">{s.title}</h4>
                <p className="text-xs text-neutral-dark/50 leading-relaxed max-w-[200px]">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="max-w-3xl mx-auto px-6 py-16">
        <h2 className="text-2xl font-bold text-neutral-dark text-center mb-8">Frequently Asked Questions</h2>
        
        <div className="flex flex-col gap-4">
          {faqs.map((faq, idx) => (
            <div key={idx} className="bg-white border border-neutral-border rounded-lg overflow-hidden">
              <button 
                onClick={() => setActiveFaq(activeFaq === idx ? null : idx)}
                className="w-full px-6 py-4 flex items-center justify-between text-left font-semibold text-neutral-dark text-sm hover:bg-neutral-light transition-colors"
              >
                <span>{faq.q}</span>
                <ChevronDown className={`w-4 h-4 text-neutral-dark/50 transition-transform ${activeFaq === idx ? 'rotate-180' : ''}`} />
              </button>
              {activeFaq === idx && (
                <div className="px-6 pb-4 pt-2 text-xs text-neutral-dark/60 leading-relaxed border-t border-neutral-border/50">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
