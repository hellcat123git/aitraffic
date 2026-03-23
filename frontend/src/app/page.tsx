'use client';

import React, { useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useTelemetryStore } from '@/store/useTelemetryStore';
import { 
  Activity, 
  Leaf, 
  Clock, 
  AlertTriangle, 
  Settings, 
  Cpu, 
  Zap 
} from 'lucide-react';

// Dynamically import DeckGL map to prevent SSR issues
const TrafficMap = dynamic(() => import('@/components/TrafficMap'), { 
  ssr: false,
  loading: () => <div className="w-full h-full bg-white/5 animate-pulse rounded-3xl" />
});

/**
 * AI-Traffic: High-End Smart City Dashboard
 * Layout: Intelligent Bento Grid
 * Styling: Glassmorphism / Dark Mode
 */

export default function Dashboard() {
  const telemetry = useTelemetryStore();

  // Mock data update for initial visual testing
  useEffect(() => {
    const timer = setInterval(() => {
      // In production, this would be a WebSocket sync or SWR fetch
      telemetry.updateTelemetry({
        step: Math.floor(Date.now() / 1000) % 1000,
        vehicle_count: Math.floor(Math.random() * 50) + 10,
        co2_mg: Math.random() * 50000,
        avg_wait_s: Math.random() * 5,
        evp_active: Math.random() > 0.9,
        evp_road: 'North Approach'
      });
    }, 2000);
    return () => clearInterval(timer);
  }, [telemetry]);

  return (
    <main className="min-h-screen bg-[#050507] text-white p-8 font-sans selection:bg-cyan-500/30">
      {/* --- Header --- */}
      <header className="flex justify-between items-center mb-10">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
            AI-Traffic Orchestrator
          </h1>
          <p className="text-gray-500 text-sm font-medium tracking-widest uppercase mt-1">
            Smart City Brain • Real-time Infrastructure
          </p>
        </div>
        
        <div className="flex gap-4">
          <button className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-all backdrop-blur-md">
            <Settings className="w-4 h-4 text-gray-400" />
            <span className="text-sm font-semibold">Config</span>
          </button>
          <div className="flex items-center gap-3 px-4 py-2 bg-cyan-500/10 border border-cyan-500/20 rounded-xl">
            <span className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />
            <span className="text-sm font-bold text-cyan-400">System Live</span>
          </div>
        </div>
      </header>

      {/* --- Bento Grid --- */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6 auto-rows-[180px]">
        
        {/* Real-time Flow Map (Large) */}
        <div className="md:col-span-2 lg:col-span-3 row-span-3 bg-white/[0.03] border border-white/10 rounded-3xl backdrop-blur-xl p-6 relative overflow-hidden group">
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div>
              <h2 className="text-lg font-bold flex items-center gap-2">
                <Activity className="w-5 h-5 text-cyan-500" />
                Live Network Flow
              </h2>
              <p className="text-xs text-gray-500 uppercase tracking-widest font-bold">Sumo Simulation Engine • TraCI 1.2</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-mono font-black text-cyan-400 leading-none">{telemetry.vehicleCount}</p>
              <p className="text-[10px] text-gray-500 uppercase font-bold">Active Vehicles</p>
            </div>
          </div>
          
          {/* Real-time Map Visualization */}
          <div className="absolute inset-0 z-0">
             <TrafficMap />
          </div>
          
          <div className="absolute bottom-6 left-6 text-xs text-gray-600 font-mono z-10">
            {`MAP_BUFFER_READY: 0x${(Date.now()).toString(16).slice(-8)}`}
          </div>
        </div>

        {/* ECO Analytics Card */}
        <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-3xl backdrop-blur-xl p-6 flex flex-col justify-between group hover:border-emerald-500/40 transition-all">
          <div className="flex justify-between items-start">
            <Leaf className="w-6 h-6 text-emerald-500" />
            <span className="text-[10px] bg-emerald-500/10 text-emerald-500 px-2 py-1 rounded-full font-bold uppercase tracking-wider">Eco Active</span>
          </div>
          <div>
            <p className="text-3xl font-mono font-black text-emerald-400">
               {telemetry.co2mg.toFixed(0)} <span className="text-sm font-normal text-emerald-700">mg</span>
            </p>
            <p className="text-xs text-gray-500 font-bold uppercase tracking-widest mt-1">CO₂ Emissions</p>
          </div>
        </div>

        {/* Wait Time Card */}
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-3xl backdrop-blur-xl p-6 flex flex-col justify-between group hover:border-amber-500/40 transition-all">
          <div className="flex justify-between items-start">
            <Clock className="w-6 h-6 text-amber-500" />
            <span className="text-[10px] bg-amber-500/10 text-amber-500 px-2 py-1 rounded-full font-bold uppercase tracking-wider">Delay Tracker</span>
          </div>
          <div>
            <p className="text-3xl font-mono font-black text-amber-400">
               {telemetry.avgWait.toFixed(2)} <span className="text-sm font-normal text-amber-700">s</span>
            </p>
            <p className="text-xs text-gray-500 font-bold uppercase tracking-widest mt-1">Avg Vehicle Wait</p>
          </div>
        </div>

        {/* EVP Status Card (Dynamic) */}
        <div className={`row-span-1 rounded-3xl backdrop-blur-xl p-6 flex flex-col justify-between border transition-all ${telemetry.evpActive ? 'bg-red-500/10 border-red-500/40 animate-pulse' : 'bg-white/[0.03] border-white/10'}`}>
          <div className="flex justify-between items-start">
            <AlertTriangle className={`w-6 h-6 ${telemetry.evpActive ? 'text-red-500' : 'text-gray-600'}`} />
            <span className={`text-[10px] px-2 py-1 rounded-full font-bold uppercase tracking-wider ${telemetry.evpActive ? 'bg-red-500/20 text-red-500' : 'bg-gray-500/10 text-gray-600'}`}>
              {telemetry.evpActive ? 'Emergency' : 'Standby'}
            </span>
          </div>
          <div>
            <p className={`text-xl font-bold ${telemetry.evpActive ? 'text-white' : 'text-gray-600'}`}>
               {telemetry.evpActive ? telemetry.evpRoad : 'All Clear'}
            </p>
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mt-1">EVP Response Mode</p>
          </div>
        </div>

        {/* Hardware Status */}
        <div className="bg-white/[0.03] border border-white/10 rounded-3xl backdrop-blur-xl p-6 flex items-center gap-4 group">
          <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center border border-white/10 group-hover:border-cyan-500/40 transition-all">
            <Cpu className="w-6 h-6 text-gray-400 group-hover:text-cyan-400" />
          </div>
          <div>
            <p className="text-sm font-bold">ESP32 Bridge</p>
            <p className="text-[10px] text-emerald-500 font-bold uppercase">Connected • 1s Heartbeat</p>
          </div>
        </div>

        {/* Benchmarking Info */}
        <div className="bg-white/[0.03] border border-white/10 rounded-3xl backdrop-blur-xl p-6 flex items-center gap-4 group">
          <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center border border-white/10 group-hover:border-purple-500/40 transition-all">
            <Zap className="w-6 h-6 text-gray-400 group-hover:text-purple-400" />
          </div>
          <div>
            <p className="text-sm font-bold">Simulation Bench</p>
            <p className="text-[10px] text-gray-500 font-bold uppercase">74.7% Efficiency Gain</p>
          </div>
        </div>

      </div>
    </main>
  );
}
