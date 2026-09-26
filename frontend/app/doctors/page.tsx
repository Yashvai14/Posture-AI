"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { doctorApi } from "@/lib/api";
import { 
  MapPin, 
  Stethoscope, 
  Star, 
  Calendar, 
  Clock, 
  Phone, 
  CheckCircle,
  RefreshCw,
  Search
} from "lucide-react";

export default function FindDoctorsPage() {
  const [lat, setLat] = useState<number>(40.7128); // Default NYC lat
  const [lon, setLon] = useState<number>(-74.0060); // Default NYC lon
  const [radius, setRadius] = useState<number>(30);
  const [locLoading, setLocLoading] = useState<boolean>(true);
  
  // Appointment modal states
  const [selectedDoctor, setSelectedDoctor] = useState<any>(null);
  const [bookDate, setBookDate] = useState<string>("");
  const [bookTime, setBookTime] = useState<string>("");
  const [isBooked, setIsBooked] = useState<boolean>(false);

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);

  // Fetch coordinates on mount
  useEffect(() => {
    if (typeof window !== "undefined" && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLat(pos.coords.latitude);
          setLon(pos.coords.longitude);
          setLocLoading(false);
        },
        (err) => {
          console.warn("Geolocation denied, using default NYC coordinates.", err);
          setLocLoading(false);
        }
      );
    } else {
      setLocLoading(false);
    }
  }, []);

  // Fetch doctors nearby
  const { data: doctors, isLoading, isError, refetch } = useQuery({
    queryKey: ["doctors", lat, lon, radius],
    queryFn: () => doctorApi.search(lat, lon, radius),
    enabled: !locLoading,
  });

  // Dynamic Leaflet Map setup
  useEffect(() => {
    if (typeof window === "undefined" || !mapContainerRef.current || locLoading) return;

    // Load Leaflet dynamically on client side
    const L = require("leaflet");

    // Initialize Map if not created
    if (!mapRef.current) {
      mapRef.current = L.map(mapContainerRef.current).setView([lat, lon], 12);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(mapRef.current);
    } else {
      mapRef.current.setView([lat, lon], 12);
    }

    // Clear existing markers
    markersRef.current.forEach((marker) => mapRef.current.removeLayer(marker));
    markersRef.current = [];

    // Place user marker
    const userMarker = L.marker([lat, lon], {
      icon: L.divIcon({
        className: "bg-primary w-4 h-4 rounded-full border-2 border-white shadow-soft",
        html: ""
      })
    }).addTo(mapRef.current).bindPopup("Your Location");
    markersRef.current.push(userMarker);

    // Place doctor markers
    if (doctors && doctors.length > 0) {
      doctors.forEach((doc: any) => {
        const marker = L.marker([doc.latitude, doc.longitude])
          .addTo(mapRef.current)
          .bindPopup(`<b>${doc.name}</b><br/>${doc.specialization}`);
        
        markersRef.current.push(marker);
      });
    }

    return () => {
      // Map cleanup on unmount
    };
  }, [lat, lon, doctors, locLoading]);

  // Book appointment mutation
  const bookMutation = useMutation({
    mutationFn: async () => {
      if (!selectedDoctor || !bookDate || !bookTime) {
        throw new Error("Date and Time are required.");
      }
      return await doctorApi.bookAppointment({
        doctor_id: selectedDoctor.id,
        appointment_date: bookDate,
        appointment_time: bookTime,
      });
    },
    onSuccess: () => {
      setIsBooked(true);
      setTimeout(() => {
        setIsBooked(false);
        setSelectedDoctor(null);
        setBookDate("");
        setBookTime("");
      }, 2500);
    },
    onError: (err: any) => {
      alert("Booking failed. Please try again.");
    }
  });

  return (
    <div className="max-w-7xl mx-auto px-6 py-12 flex flex-col gap-10">
      <div>
        <h1 className="text-3xl font-extrabold text-neutral-dark flex items-center gap-2">
          <Stethoscope className="w-8 h-8 text-primary" />
          Nearby Specialists & Clinics
        </h1>
        <p className="text-sm text-neutral-dark/60 mt-1.5 font-medium">Discover orthopedic clinics, physiotherapists, and book consultations within 30 KM.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Map Panel (7 columns) */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <div className="h-[480px] bg-white rounded-xl border border-neutral-border p-2 shadow-soft overflow-hidden relative">
            <div ref={mapContainerRef} className="w-full h-full" />
            
            {locLoading && (
              <div className="absolute inset-0 bg-white/80 z-20 flex flex-col items-center justify-center gap-2">
                <RefreshCw className="w-8 h-8 text-primary animate-spin" />
                <span className="text-xs text-neutral-dark/50 font-bold">Acquiring current GPS...</span>
              </div>
            )}
          </div>
        </div>

        {/* Doctor List (5 columns) */}
        <div className="lg:col-span-5 flex flex-col gap-4 max-h-[480px] overflow-y-auto pr-2">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-2">
              <RefreshCw className="w-6 h-6 text-primary animate-spin" />
              <span className="text-xs text-neutral-dark/50 font-semibold">Searching nearby clinics...</span>
            </div>
          ) : isError ? (
            <div className="text-xs text-red-500 text-center py-10 font-semibold">
              Failed to query clinics. Check backend.
            </div>
          ) : doctors && doctors.length > 0 ? (
            doctors.map((doc: any) => (
              <div key={doc.id} className="bg-white border border-neutral-border rounded-xl p-5 shadow-soft hover:border-primary/20 transition-all duration-300 flex flex-col gap-3">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-bold text-neutral-dark text-sm">{doc.name}</h3>
                    <span className="bg-secondary-light text-secondary text-[10px] font-bold px-2.5 py-0.5 rounded-full mt-1.5 inline-block">
                      {doc.specialization}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 bg-yellow-50 text-yellow-600 border border-yellow-100 text-[10px] font-bold px-2 py-0.5 rounded">
                    <Star className="w-3 h-3 fill-yellow-500 stroke-yellow-500" />
                    <span>{doc.rating}</span>
                  </div>
                </div>

                <div className="text-xs text-neutral-dark/60 flex flex-col gap-1">
                  <span className="flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-neutral-dark/40 flex-shrink-0" />
                    <span className="truncate">{doc.address}</span>
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 text-neutral-dark/40" />
                    <span>{doc.phone || "N/A"}</span>
                  </span>
                </div>

                <div className="flex items-center justify-between border-t border-neutral-border pt-3 mt-1">
                  <div className="flex flex-col">
                    <span className="text-[10px] text-neutral-dark/40 font-bold">CONSULTATION FEE</span>
                    <span className="text-sm font-extrabold text-neutral-dark">${doc.consultation_fee}</span>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="text-[10px] text-neutral-dark/40 font-bold">DISTANCE</span>
                    <span className="text-xs font-bold text-primary">{doc.distance_km} KM away</span>
                  </div>
                </div>

                <button 
                  onClick={() => setSelectedDoctor(doc)}
                  className="bg-primary hover:bg-primary-hover text-white text-xs font-semibold py-2 rounded-lg mt-1 shadow-soft transition-all"
                >
                  Schedule Appointment
                </button>
              </div>
            ))
          ) : (
            <div className="bg-white border border-dashed border-neutral-border rounded-xl p-8 text-center flex flex-col items-center justify-center gap-2">
              <Stethoscope className="w-10 h-10 text-neutral-dark/20" />
              <span className="text-xs font-bold text-neutral-dark">No Doctors Found</span>
              <p className="text-[10px] text-neutral-dark/40 max-w-[200px]">We couldn't detect specialists within 30 KM of your current coordinates.</p>
            </div>
          )}
        </div>
      </div>

      {/* Appointment Booking Modal */}
      {selectedDoctor && (
        <div className="fixed inset-0 bg-neutral-dark/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-sm w-full p-6 border border-neutral-border shadow-premium flex flex-col gap-4 relative animate-in fade-in-50 duration-200">
            <button 
              onClick={() => setSelectedDoctor(null)}
              className="absolute top-3 right-3 text-neutral-dark/40 hover:text-neutral-dark text-xs"
            >
              Close
            </button>

            {isBooked ? (
              <div className="flex flex-col items-center justify-center py-10 gap-2.5 text-center">
                <CheckCircle className="w-12 h-12 text-accent" />
                <span className="font-bold text-neutral-dark text-sm">Appointment Booked!</span>
                <p className="text-xs text-neutral-dark/40">You scheduled a session with {selectedDoctor.name}.</p>
              </div>
            ) : (
              <>
                <div>
                  <h3 className="font-bold text-neutral-dark">Book Consultation</h3>
                  <p className="text-[11px] text-neutral-dark/50">Schedule a visit with {selectedDoctor.name}.</p>
                </div>

                <div className="flex flex-col gap-3">
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] font-bold text-neutral-dark/60">Preferred Date</label>
                    <div className="relative flex items-center">
                      <input 
                        type="date"
                        value={bookDate}
                        onChange={(e) => setBookDate(e.target.value)}
                        className="w-full border border-neutral-border rounded-lg pl-9 pr-3 py-2 text-xs bg-neutral-light/35 focus:outline-primary"
                      />
                      <Calendar className="absolute left-3 w-4 h-4 text-neutral-dark/30" />
                    </div>
                  </div>

                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] font-bold text-neutral-dark/60">Preferred Time Slot</label>
                    <div className="relative flex items-center">
                      <input 
                        type="time"
                        value={bookTime}
                        onChange={(e) => setBookTime(e.target.value)}
                        className="w-full border border-neutral-border rounded-lg pl-9 pr-3 py-2 text-xs bg-neutral-light/35 focus:outline-primary"
                      />
                      <Clock className="absolute left-3 w-4 h-4 text-neutral-dark/30" />
                    </div>
                  </div>
                </div>

                <button 
                  onClick={() => bookMutation.mutate()}
                  disabled={bookMutation.isPending || !bookDate || !bookTime}
                  className="bg-primary hover:bg-primary-hover disabled:bg-primary/50 text-white text-xs font-semibold py-2.5 rounded-lg shadow-soft mt-2"
                >
                  {bookMutation.isPending ? "Scheduling..." : "Confirm Reservation"}
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
