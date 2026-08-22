declare module 'satellite.js' {
  export function twoline2satrec(line1: string, line2: string): any;
  export function propagate(satrec: any, date: Date): any;
  export function gstime(date: Date): number;
  export function eciToGeodetic(eci: any, gmst: number): {
    longitude: number;
    latitude: number;
    height: number;
  };
  export function degreesLat(radians: number): number;
  export function degreesLong(radians: number): number;
}
