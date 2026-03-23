# AI-Traffic: High-End UI Design Specification

## 🎨 1. Aesthetics & Palette
- **Theme:** High-Contrast Dark Mode (Glassmorphism/Frost).
- **Primary Background:** `#050507` (Deep Obsidian).
- **Surface/Card Color:** `rgba(20, 20, 25, 0.7)` with `backdrop-filter: blur(12px)`.
- **Accent 1 (AI Active):** `#00F2FF` (Electric Cyan).
- **Accent 2 (Emergency):** `#FF3131` (Pulse Red).
- **Accent 3 (Eco-Success):** `#39FF14` (Neon Green).
- **Border/Stroke:** `rgba(255, 255, 255, 0.1)` (1px solid).

## 📐 2. Layout (Intelligent Bento Grid)
- **Grid System:** 8pt Grid (All margins/padding are multiples of 8).
- **Cards:** Modular, rounded corners (`border-radius: 16px`), and soft shadows (`box-shadow: 0 8px 32px rgba(0,0,0,0.4)`).
- **Responsive:** Fluid stacking for desktop-to-tablet transitions.

## 📊 3. Advanced Data Visualization
- **Real-time Map:** Use `deck.gl TripsLayer` to show animated, moving light trails representing traffic flow.
- **Eco-Analytics:** Sleek, thin circular gauges (D3.js or ECharts) with neon glow for CO2 savings.
- **Emergency Alerts:** Persistent, pulsing top-bar overlay with a subtle red 'haze' effect on the background.
- **Heatmaps:** Dynamic, translucent overlays on the intersection stubs to show approach congestion.

## ✍️ 4. Typography & Hierarchy
- **Font Stack:** 'Geist Mono' or 'Inter' (Vercel-inspired).
- **Scaling:** Use `clamp()` for fluid font sizing.
- **Hierarchy:** 
    - **H1 (Titles):** Semi-Bold, `tracking-tight`.
    - **KPIs:** Tabular figures (monospace) for stable numerical updates.
    - **Sub-labels:** Uppercase, `tracking-widest`, slightly dimmed opacity (`0.6`).

## 🛡️ 5. AI Design Rules (Anti-Hallucination)
- **Consistency Protocol:** Never use a color outside the defined palette.
- **Spacing Invariance:** All elements MUST use the 8pt multiplier (8, 16, 24, 32, 48, 64).
- **Iconography:** Use 'Lucide-React' or 'Phosphor' icons exclusively for a unified line-weight style.
- **Empty States:** Every chart must have a styled 'Skeleton' loader or 'Awaiting Data' pulse.

## 🛠️ 6. Recommended Skills & Tech Stack
- **Framework:** Next.js (React) + Tailwind CSS + Framer Motion.
- **State:** Zustand (Lightweight, real-time sync).
- **Agent Skill:** `ui-aesthetic-polisher` (Activated for final CSS review).
- **Agent Skill:** `data-viz-architect` (Activated for D3/Plotly implementation).
