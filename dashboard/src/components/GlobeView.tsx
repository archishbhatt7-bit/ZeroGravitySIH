import { useEffect, useRef, useState, useMemo, useCallback } from "react";
import { Viewer, Entity, PointGraphics, PolylineGraphics } from "resium";
import * as Cesium from "cesium";
import * as satellite from "satellite.js";
import { useStore } from "../store";
import { Plus, Minus, Lock, Unlock, Compass } from "lucide-react";

// Set Ion token if available in env
if (import.meta.env.VITE_CESIUM_ION_TOKEN) {
  Cesium.Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN;
}

interface SatPoint {
  id: string;
  position: Cesium.Cartesian3;
  color: Cesium.Color;
  pixelSize: number;
  sat: { norad_id: number; name: string; object_type: string };
}

export function GlobeView() {
  const viewerRef = useRef<any>(null);
  const satrecsRef = useRef<Map<number, any>>(new Map());
  const [satPositions, setSatPositions] = useState<SatPoint[]>([]);
  const [isViewLocked, setIsViewLocked] = useState(false);

  const {
    satellites,
    conjunctions,
    selectedSatelliteId,
    selectedEventId,
    selectedSatConjunctions,
    setSelectedSatellite,
    focusTarget,
    setFocusTarget,
    layerVisibility,
    isAnalysisMode,
  } = useStore();

  // Parse TLEs into satrecs (cached)
  useEffect(() => {
    const map = new Map<number, any>();
    for (const sat of satellites) {
      try {
        const satrec = satellite.twoline2satrec(sat.line1, sat.line2);
        map.set(sat.norad_id, satrec);
      } catch {
        // Skip invalid TLEs
      }
    }
    satrecsRef.current = map;
  }, [satellites]);

  // Compute real satellite positions via satellite.js, update every 10s
  const computePositions = useCallback(() => {
    const now = new Date();
    const gmst = satellite.gstime(now);
    const points: SatPoint[] = [];
    const state = useStore.getState();
    const visibility = state.layerVisibility;
    const mode = state.isAnalysisMode;
    const eventId = state.selectedEventId;
    const selectedSatId = state.selectedSatelliteId;

    const objectsToProcess = new Map<number, any>();

    if (!mode) {
      for (const sat of satellites) {
        objectsToProcess.set(sat.norad_id, sat);
      }
    } else {
      const eventsToRender = eventId
        ? state.conjunctions.filter(
            (c) =>
              `${c.primary.norad_id}-${c.secondary.norad_id}-${c.tca}` ===
              eventId
          )
        : state.conjunctions;

      for (const c of eventsToRender) {
        if (!objectsToProcess.has(c.primary.norad_id)) {
          objectsToProcess.set(c.primary.norad_id, c.primary);
        }
        if (!objectsToProcess.has(c.secondary.norad_id)) {
          objectsToProcess.set(c.secondary.norad_id, c.secondary);
        }
      }
    }

    let skippedCount = 0;
    for (const sat of objectsToProcess.values()) {
      if (!mode) {
        if (
          sat.object_type === "ACTIVE_SATELLITE" &&
          !visibility.activeSatellites
        )
          continue;
        if (sat.object_type === "DEBRIS" && !visibility.debris) continue;
        if (sat.object_type === "ROCKET_BODY" && !visibility.rocketBodies)
          continue;
        if (sat.object_type === "UNKNOWN" && !visibility.unknown) continue;
      }

      let satrec = satrecsRef.current.get(sat.norad_id);
      if (!satrec && sat.line1 && sat.line2) {
        try {
          satrec = satellite.twoline2satrec(sat.line1, sat.line2);
          satrecsRef.current.set(sat.norad_id, satrec);
        } catch {
          // ignore parsing error
        }
      }
      
      if (!satrec) {
        skippedCount++;
        continue;
      }

      try {
        const posVel = satellite.propagate(satrec, now);
        if (posVel.position && typeof posVel.position !== "boolean") {
          const geodetic = satellite.eciToGeodetic(posVel.position, gmst);
          const lat = satellite.degreesLat(geodetic.latitude);
          const lng = satellite.degreesLong(geodetic.longitude);
          const alt = geodetic.height * 1000; // satellite.js height is km, Cesium wants meters

          let color = Cesium.Color.fromCssColorString("rgba(255, 255, 255, 0.5)");
          let pixelSize = 3;

          if (sat.object_type === "ACTIVE_SATELLITE") {
            color = Cesium.Color.fromCssColorString("#00f0ff");
            pixelSize = 5;
          } else if (sat.object_type === "DEBRIS") {
            color = Cesium.Color.fromCssColorString("#999999");
            pixelSize = 3;
          } else if (sat.object_type === "ROCKET_BODY") {
            color = Cesium.Color.fromCssColorString("#eab308");
            pixelSize = 4;
          }

          if (sat.norad_id === useStore.getState().selectedSatelliteId) {
            color = Cesium.Color.WHITE;
            pixelSize = 10;
          }

          points.push({
            id: `sat-${sat.norad_id}`,
            position: Cesium.Cartesian3.fromDegrees(lng, lat, alt),
            color,
            pixelSize,
            sat: {
              norad_id: sat.norad_id,
              name: sat.name,
              object_type: sat.object_type,
            },
          });
        } else {
          skippedCount++;
        }
      } catch {
        skippedCount++;
      }
    }

    console.log(`[ZG] Satellite positions computed: ${points.length} rendered, ${skippedCount} skipped, ${satellites.length} total in catalog`);
    setSatPositions(points);
  }, [satellites]);

  // Initial computation and periodic updates
  useEffect(() => {
    if (satellites.length === 0) return;
    const timer = setTimeout(() => {
      computePositions();
    }, 100);
    const interval = setInterval(computePositions, 10000); // Update every 10s
    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, [satellites, computePositions]);

  // Recompute when layer visibility changes
  useEffect(() => {
    if (satellites.length > 0) {
      computePositions();
    }
  }, [
    layerVisibility,
    isAnalysisMode,
    selectedEventId,
    selectedSatelliteId,
    computePositions,
    satellites.length,
  ]);

  // Conjunction Highlights (only show when NO satellite is selected)
  const ringsData = useMemo(() => {
    if (!layerVisibility.conjunctionHighlights) return [];
    if (selectedSatelliteId) return []; // Hide global conjunctions in focus mode

    return conjunctions.slice(0, 80).map((c, idx) => {
       const colorStr = c.risk_category === "CRITICAL"
          ? "#ef4444"
          : c.risk_category === "HIGH"
            ? "#f97316"
            : c.risk_category === "MEDIUM"
              ? "#eab308"
              : "rgba(100, 120, 255, 0.5)";
              
       const pixelSize = c.risk_category === "CRITICAL" ? 20 : (c.risk_category === "HIGH" ? 15 : 10);
       return {
         id: `ring-${idx}`,
         position: Cesium.Cartesian3.fromDegrees(c.lng, c.lat, c.alt * 1000), 
         color: Cesium.Color.fromCssColorString(colorStr),
         pixelSize
       };
    });
  }, [conjunctions, layerVisibility.conjunctionHighlights, selectedSatelliteId]);

  // Collision markers for the selected satellite's orbit
  const collisionMarkers = useMemo(() => {
    if (!selectedSatelliteId || selectedSatConjunctions.length === 0) return [];

    return selectedSatConjunctions.map((c, idx) => {
      return {
        id: `collision-${idx}`,
        position: Cesium.Cartesian3.fromDegrees(c.lng, c.lat, c.alt * 1000),
        color: Cesium.Color.fromCssColorString("#ff9500"),
        pixelSize: 16,
        label: `${c.secondary.name || c.primary.name} — ${c.miss_distance_km.toFixed(2)} km`,
        riskCategory: c.risk_category,
      };
    });
  }, [selectedSatelliteId, selectedSatConjunctions]);

  // Orbit Paths
  const pathsData = useMemo(() => {
    if (!layerVisibility.orbitPaths) return [];

    const paths = [];
    const now = new Date();

    const getPath = (
      satrec: any,
      startTime: Date,
      durationMins: number,
      color: Cesium.Color,
    ) => {
      const segments = [];
      let currentPositions = [];
      let lastLng = null;

      for (let i = 0; i <= durationMins; i += 2) {
        const t = new Date(startTime.getTime() + i * 60000);
        const gmst = satellite.gstime(t);
        const posVel = satellite.propagate(satrec, t);
        if (posVel.position && typeof posVel.position !== "boolean") {
          const geodetic = satellite.eciToGeodetic(posVel.position, gmst);
          const lng = satellite.degreesLong(geodetic.longitude);
          const lat = satellite.degreesLat(geodetic.latitude);
          const alt = geodetic.height * 1000;

          if (lastLng !== null && Math.abs(lng - lastLng) > 180) {
            if (currentPositions.length > 0) {
              segments.push({ positions: currentPositions, color });
            }
            currentPositions = [];
          }

          currentPositions.push(Cesium.Cartesian3.fromDegrees(lng, lat, alt));
          lastLng = lng;
        }
      }
      
      if (currentPositions.length > 0) {
        segments.push({ positions: currentPositions, color });
      }
      return segments;
    };

    if (selectedEventId) {
      const event = conjunctions.find(
        (c) =>
          `${c.primary.norad_id}-${c.secondary.norad_id}-${c.tca}` ===
          selectedEventId,
      );
      if (event) {
        let sat1 = satrecsRef.current.get(event.primary.norad_id);
        let sat2 = satrecsRef.current.get(event.secondary.norad_id);

        const tca = new Date(event.tca);
        const start = new Date(tca.getTime() - 45 * 60000);

        if (sat1)
          paths.push(...getPath(sat1, start, 90, Cesium.Color.fromCssColorString("rgba(0, 240, 255, 0.5)")));
        if (sat2)
          paths.push(...getPath(sat2, start, 90, Cesium.Color.fromCssColorString("rgba(255, 150, 0, 0.5)")));
      }
    } else if (selectedSatelliteId) {
      const sat = satrecsRef.current.get(selectedSatelliteId);
      if (sat) {
        // Full orbit path (180 mins = ~2 orbits for LEO)
        paths.push(...getPath(sat, now, 180, Cesium.Color.fromCssColorString("rgba(0, 240, 255, 0.6)")));
      }
    }

    return paths;
  }, [
    selectedEventId,
    selectedSatelliteId,
    conjunctions,
    layerVisibility.orbitPaths,
  ]);

  // Camera animation
  useEffect(() => {
    if (focusTarget && viewerRef.current?.cesiumElement) {
      const viewer = viewerRef.current.cesiumElement;
      
      const targetPosition = Cesium.Cartesian3.fromDegrees(
        focusTarget.lng,
        focusTarget.lat,
        (focusTarget.alt * 1000) + 1500000 
      );
      
      viewer.camera.flyTo({
        destination: targetPosition,
        duration: 1.5,
      });
      setTimeout(() => setFocusTarget(null), 1600);
    }
  }, [focusTarget, setFocusTarget]);

  // Initialize viewer: imagery, click handler, scene settings.
  // Using useEffect + ref polling because Resium's onReady callback
  // does not fire reliably with Cesium 1.144.
  const viewerInitialized = useRef(false);

  useEffect(() => {
    const interval = setInterval(() => {
      const viewer = viewerRef.current?.cesiumElement;
      if (!viewer || viewerInitialized.current) return;
      viewerInitialized.current = true;
      clearInterval(interval);

      console.log("[ZG] Viewer detected, initializing...");

      // Click handler for satellite picking
      const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
      handler.setInputAction((click: any) => {
        const pickedObject = viewer.scene.pick(click.position);
        if (Cesium.defined(pickedObject) && pickedObject.id && typeof pickedObject.id.id === 'string' && pickedObject.id.id.startsWith("sat-")) {
           const satId = parseInt(pickedObject.id.id.replace("sat-", ""), 10);
           setSelectedSatellite(satId);
           const pt = satPositions.find(p => p.sat.norad_id === satId);
           if(pt) {
               const carto = Cesium.Cartographic.fromCartesian(pt.position);
               setFocusTarget({
                   lat: Cesium.Math.toDegrees(carto.latitude),
                   lng: Cesium.Math.toDegrees(carto.longitude),
                   alt: carto.height / 1000
               });
           }
        }
      }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

      // Scene aesthetics
      viewer.scene.globe.enableLighting = true;
      viewer.scene.skyAtmosphere.show = true;
      viewer.scene.fog.enabled = true;
      viewer.scene.globe.showGroundAtmosphere = true;

      // Remove double click zoom
      viewer.screenSpaceEventHandler.removeInputAction(
        Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK
      );

      // Replace default Ion imagery with reliable offline + online layers
      viewer.imageryLayers.removeAll();
      (async () => {
        try {
          // Primary: Cesium's bundled Natural Earth II (always works, no network needed)
          const natural = await Cesium.TileMapServiceImageryProvider.fromUrl(
            Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII")
          );
          viewer.imageryLayers.addImageryProvider(natural);

          // Overlay: ESRI World Imagery for higher res when zoomed in (free, no token)
          try {
            const esri = new Cesium.UrlTemplateImageryProvider({
              url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
              credit: new Cesium.Credit("Tiles © Esri"),
              maximumLevel: 18,
            });
            viewer.imageryLayers.addImageryProvider(esri);
          } catch {
            // ESRI overlay is optional — Natural Earth II is sufficient
          }
        } catch (e) {
          console.error("[ZG] Failed to load any imagery:", e);
        }
      })();
    }, 200);

    return () => clearInterval(interval);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle locking the orbital view
  useEffect(() => {
    if (viewerRef.current?.cesiumElement) {
      viewerRef.current.cesiumElement.scene.screenSpaceCameraController.enableTilt = !isViewLocked;
    }
  }, [isViewLocked, viewerInitialized.current]); // Also run if initialization completes

  return (
    <div style={{ width: "100%", height: "100%", background: "#050505", position: "relative" }}>
      {/* Map Controls */}
      <div style={{ position: "absolute", top: "16px", left: "16px", zIndex: 10, display: "flex", flexDirection: "column", gap: "8px" }}>
        <div style={{ display: "flex", flexDirection: "column", background: "rgba(10, 12, 18, 0.8)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", overflow: "hidden", backdropFilter: "blur(8px)" }}>
          <button 
            onClick={() => viewerRef.current?.cesiumElement?.camera.zoomIn(2000000)}
            style={{ padding: "8px", color: "#ccc", borderBottom: "1px solid rgba(255,255,255,0.05)", background: "transparent", border: "none", cursor: "pointer", display: "flex", justifyContent: "center" }}
            onMouseEnter={e => e.currentTarget.style.color = "#fff"}
            onMouseLeave={e => e.currentTarget.style.color = "#ccc"}
            title="Zoom In"
          >
            <Plus size={16} />
          </button>
          <button 
            onClick={() => viewerRef.current?.cesiumElement?.camera.zoomOut(2000000)}
            style={{ padding: "8px", color: "#ccc", background: "transparent", border: "none", cursor: "pointer", display: "flex", justifyContent: "center" }}
            onMouseEnter={e => e.currentTarget.style.color = "#fff"}
            onMouseLeave={e => e.currentTarget.style.color = "#ccc"}
            title="Zoom Out"
          >
            <Minus size={16} />
          </button>
        </div>

        <button
          onClick={() => setIsViewLocked(!isViewLocked)}
          style={{ padding: "8px", color: isViewLocked ? "#ff9500" : "#ccc", background: "rgba(10, 12, 18, 0.8)", border: `1px solid ${isViewLocked ? 'rgba(255,150,0,0.3)' : 'rgba(255,255,255,0.1)'}`, borderRadius: "6px", cursor: "pointer", display: "flex", justifyContent: "center", backdropFilter: "blur(8px)", transition: "all 0.2s" }}
          title={isViewLocked ? "Unlock View" : "Lock Orbital View (Prevent Tilt)"}
        >
          {isViewLocked ? <Lock size={16} /> : <Unlock size={16} />}
        </button>

        <button
          onClick={() => viewerRef.current?.cesiumElement?.camera.flyHome(1.5)}
          style={{ padding: "8px", color: "#ccc", background: "rgba(10, 12, 18, 0.8)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", cursor: "pointer", display: "flex", justifyContent: "center", backdropFilter: "blur(8px)" }}
          onMouseEnter={e => e.currentTarget.style.color = "#fff"}
          onMouseLeave={e => e.currentTarget.style.color = "#ccc"}
          title="Reset View"
        >
          <Compass size={16} />
        </button>
      </div>

      <Viewer
        ref={viewerRef}
        full
        timeline={false}
        animation={false}
        navigationHelpButton={false}
        geocoder={false}
        homeButton={false}
        sceneModePicker={false}
        baseLayerPicker={false}
        infoBox={false}
        selectionIndicator={false}
        fullscreenButton={false}
        scene3DOnly={true}
      >
        {/* Satellites */}
        {satPositions.map((pt) => (
          <Entity key={pt.id} id={pt.id} position={pt.position} description={pt.sat.name}>
            <PointGraphics color={pt.color} pixelSize={pt.pixelSize} />
          </Entity>
        ))}

        {/* Conjunction Highlights (global — hidden in focus mode) */}
        {ringsData.map((r) => (
          <Entity key={r.id} position={r.position}>
             <PointGraphics color={r.color} pixelSize={r.pixelSize} outlineColor={Cesium.Color.WHITE} outlineWidth={2} />
          </Entity>
        ))}

        {/* Collision Markers on selected satellite's orbit */}
        {collisionMarkers.map((m) => (
          <Entity key={m.id} position={m.position} description={m.label}>
            <PointGraphics
              color={m.color}
              pixelSize={m.pixelSize}
              outlineColor={Cesium.Color.WHITE}
              outlineWidth={3}
            />
          </Entity>
        ))}

        {/* Orbit Paths */}
        {pathsData.map((p, idx) => (
          <Entity key={`path-${idx}`}>
            <PolylineGraphics
              positions={p.positions}
              width={2}
              material={p.color}
            />
          </Entity>
        ))}
      </Viewer>
    </div>
  );
}
