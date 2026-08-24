export interface Satellite {
  name: string;
  norad_id: number;
  object_type: string;
  epoch: string;
  inclination: number;
  eccentricity: number;
  line1: string;
  line2: string;
}

export interface SearchResult extends Satellite {
  lat?: number;
  lng?: number;
  alt?: number;
  velocity_km_s?: number;
}

export interface RiskFactors {
  distance_score: number;
  velocity_score: number;
  size_multiplier: number;
  maneuver_multiplier: number;
  urgency_multiplier: number;
  base_score: number;
}

export interface ConjunctionObject {
  name: string;
  norad_id: number;
  rcs: string;
  maneuverable: boolean;
  object_type: string;
  epoch: string;
  age_days: number;
  line1: string;
  line2: string;
}

export interface ConjunctionEvent {
  primary: ConjunctionObject;
  secondary: ConjunctionObject;
  tca: string;
  miss_distance_km: number;
  relative_velocity_km_s: number;
  risk_score: number;
  risk_category: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NEGLIGIBLE";
  time_to_tca_hours: number | null;
  factors: RiskFactors;
  recommendation: string;
  confidence: "NORMAL" | "REDUCED";
  lat: number;
  lng: number;
  alt: number;
  collision_probability: number | null;
  probability_method: string | null;
}

export interface LayerVisibility {
  activeSatellites: boolean;
  debris: boolean;
  rocketBodies: boolean;
  unknown: boolean;
  orbitPaths: boolean;
  conjunctionHighlights: boolean;
  mapStyle?: "day" | "night";
  autoRotate?: boolean;
}

export interface FocusTarget {
  lat: number;
  lng: number;
  alt: number;
}
