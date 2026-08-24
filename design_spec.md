# ZeroGravity Design System & UI/UX Specification

To stun the judges and create a truly premium experience, we need to abandon basic dashboard templates and embrace a highly modern, immersive design language. The goal is to make the user feel like they are operating a next-generation space command center.

## 1. Core Aesthetic: Cinematic Glassmorphism
The dashboard will use a **"Hero Background"** layout where the 3D globe fills the entire screen, and all UI elements float above it as translucent, blurred glass panels.

- **Background:** Deep space. Pure blacks (`#050505`) with a high-resolution starfield.
- **Panels:** Dark frosted glass. 
  - `background: rgba(15, 15, 20, 0.4)`
  - `backdrop-filter: blur(24px)`
  - `border: 1px solid rgba(255, 255, 255, 0.08)`
- **Shadows:** Soft, deep shadows (`box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6)`) to lift the panels off the globe.

## 2. Typography
We will use modern, geometric sans-serif fonts to convey precision and technical capability.

- **Primary Font:** `Inter` or `Geist Sans` for UI elements, labels, and paragraphs.
- **Numbers & Data:** `JetBrains Mono` or `Roboto Mono`. Monospaced fonts are critical for rapidly changing orbital coordinates (lat/lng, distances, probabilities) so the text doesn't "jump" horizontally.
- **Weight:** Use extremely light weights (300) for labels and bold (700) for critical metrics.

## 3. Color Palette
Colors should be used sparingly against the dark background, relying on neon accents for data visualization and alerts.

- **Base Theme:** Dark Space (`#0a0a0f`, `#12121a`)
- **Primary Accent (Safe/Active):** Cyan (`#00f2fe` to `#4facfe` gradient) - Used for standard satellite orbits, selection highlights, and active tabs.
- **Warning (Elevated Risk):** Amber/Gold (`#ffb75e`) - Used for conjunctions with medium probability or close miss distances.
- **Critical (High Risk):** Neon Red/Crimson (`#ff0844`) - Used for imminent collisions. This should pulse or glow to immediately draw the eye.

## 4. The 3D Globe Visualization (`react-globe.gl`)
The globe is the centerpiece. It must be highly interactive and visually rich.

- **Earth Texture:** Use a high-res "Earth at Night" texture with glowing city lights, as it contrasts beautifully with bright satellite markers.
- **Satellites:** Rendered as small glowing points. Normal satellites are dim white/blue.
- **Orbits (Arcs):** When a satellite is clicked, draw a glowing cyan arc (`<Globe arcsData={...} />`) showing its projected path over the next 90 minutes.
- **Conjunctions:** If a collision is predicted, draw a pulsing red ring at the exact latitude/longitude/altitude of the event.
- **Camera Automation:** When the user clicks a conjunction alert in the side panel, smoothly animate the camera to fly across the Earth and zoom in on the collision point.

## 5. UI Layout & Component Architecture

### The Left Panel: "Command Feed" (350px width, floating)
- **Top Bar:** Search input for finding specific satellites by NORAD ID or Name.
- **Global Stats:** Quick metrics: "Active Tracked Objects: 30,070", "High Risk Events (7-day): 4".
- **The Conjunction Feed:** A scrollable list of upcoming close approaches. Each card shows:
  - Satellite A vs Satellite B
  - Time to closest approach (TCA) (e.g., "T-minus 14:02:00")
  - Miss distance in km (large, monospaced font)
  - A color-coded severity bar (Red/Amber/Green).

### The Right Panel: "Analysis Detail" (Slides in on demand)
This panel only appears when a specific conjunction or satellite is selected.
- **Object Metadata:** Launch date, country, operational status.
- **Probability Breakdown:** A visual gauge (circular progress bar) showing the collision probability ($P_c$).
- **Covariance Visualizer:** A small 2D chart plotting the uncertainty ellipse (B-plane) to show exactly *why* the probability is high or low.

## 6. Micro-Interactions & Animation
- **Hover States:** Buttons and feed items should subtly translate upward (`transform: translateY(-2px)`) and increase their border opacity on hover.
- **Data Updates:** When the TCA counts down, the numbers should smoothly flip or fade, not snap.
- **Loading States:** Use sleek skeleton loaders with a subtle shimmer effect (gradient translation) instead of generic spinning circles.

---

> [!TIP]
> **To achieve this in Vite/React:** We will write scoped vanilla CSS classes (e.g., `.glass-panel`, `.neon-text-red`) and use React state to drive the camera position of the `react-globe.gl` component. No bulky component libraries (like MUI or Bootstrap) will be used—everything will be bespoke and highly optimized.
