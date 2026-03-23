import { create } from 'zustand';

/**
 * AI-Traffic GPU-Native Telemetry Store
 * Uses TypedArrays for direct deck.gl buffer upload, bypassing React re-renders.
 */

interface TelemetryState {
  // Metadata
  step: number;
  vehicleCount: number;
  co2mg: number;
  avgWait: number;
  evpActive: boolean;
  evpRoad: string | null;

  // GPU Buffers (TypedArrays)
  // [x, y, z, r, g, b, radius, ...]
  // Using a flat Float32Array for maximum performance
  positions: Float32Array;
  colors: Uint8Array;
  
  // Actions
  updateTelemetry: (data: any) => void;
  resetTelemetry: () => void;
}

const MAX_VEHICLES = 2000;

export const useTelemetryStore = create<TelemetryState>((set) => ({
  step: 0,
  vehicleCount: 0,
  co2mg: 0,
  avgWait: 0,
  evpActive: false,
  evpRoad: null,

  // Initialize buffers
  positions: new Float32Array(MAX_VEHICLES * 3), // [x, y, z] per vehicle
  colors: new Uint8Array(MAX_VEHICLES * 4),    // [r, g, b, a] per vehicle

  updateTelemetry: (data) => {
    set((state) => {
      // In a real implementation, we would parse binary WebSocket data here.
      // For the mock/poll integration, we update the state and the underlying buffers.
      
      const count = data.vehicle_count || 0;
      const newPositions = state.positions;
      const newColors = state.colors;

      // Logic for mapping incoming vehicle data to TypedArray offsets
      // ... (This will be expanded once the backend streamer is ready)

      return {
        step: data.step,
        vehicleCount: count,
        co2mg: data.co2_mg,
        avgWait: data.avg_wait_s,
        evpActive: data.evp_active,
        evpRoad: data.evp_road,
        // We don't trigger a React re-render for positions/colors if 
        // they are used directly in a deck.gl layer ref.
      };
    });
  },

  resetTelemetry: () => {
    set({
      step: 0,
      vehicleCount: 0,
      positions: new Float32Array(MAX_VEHICLES * 3),
      colors: new Uint8Array(MAX_VEHICLES * 4),
    });
  }
}));
