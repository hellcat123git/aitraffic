'use client';

import React, { useMemo } from 'react';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer } from '@deck.gl/layers';
import { MapViewState } from '@deck.gl/core';
import { useTelemetryStore } from '@/store/useTelemetryStore';

/**
 * GPU-Native Traffic Map
 * Uses binary attributes for Float32Array positions and Uint8Array colors.
 * This bypasses React's reconciliation for high-frequency updates.
 */

const INITIAL_VIEW_STATE: MapViewState = {
  longitude: 0,
  latitude: 0,
  zoom: 15,
  pitch: 45,
  bearing: 0
};

export default function TrafficMap() {
  const { positions, colors, vehicleCount } = useTelemetryStore();

  const layers = useMemo(() => [
    new ScatterplotLayer({
      id: 'traffic-flow',
      data: {
        length: vehicleCount,
        attributes: {
          getPosition: { value: positions, size: 3 },
          getFillColor: { value: colors, size: 4 }
        }
      },
      radiusMinPixels: 4,
      radiusMaxPixels: 12,
      opacity: 0.8,
      stroked: true,
      lineWidthMinPixels: 1,
      getLineColor: [255, 255, 255, 100],
      // Performance tweaks for high-frequency telemetry
      parameters: {
        depthTest: false
      },
      _animate: true
    })
  ], [positions, colors, vehicleCount]);

  return (
    <div className="absolute inset-0 rounded-3xl overflow-hidden">
      <DeckGL
        initialViewState={INITIAL_VIEW_STATE}
        controller={true}
        layers={layers}
        style={{ width: '100%', height: '100%' }}
      />
    </div>
  );
}
