#!/usr/bin/env node
/** One-shot: solid green arcs + geodesic altitude on network-globe/server.js */
const fs = require('fs');
const path = process.argv[2] || require('path').join(__dirname, '..', 'server.js');
let t = fs.readFileSync(path, 'utf8');
if (t.includes('function arcAltitudeFor')) {
  console.log('already patched', path);
  process.exit(0);
}
const helper = `
function angularDistanceRad(lat1, lng1, lat2, lng2) {
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return 2 * Math.atan2(Math.sqrt(a), Math.sqrt(Math.max(0, 1 - a)));
}
function arcAltitudeFor(lat1, lng1, lat2, lng2) {
  const ang = angularDistanceRad(lat1, lng1, lat2, lng2);
  return Math.min(0.55, Math.max(0.08, 0.09 + (ang / Math.PI) * 0.48));
}
const ARC_COLOR_GREEN = ['#22c55e', '#86efac'];

`;
if (!t.includes('function buildPayload()')) {
  console.error('buildPayload not found');
  process.exit(1);
}
t = t.replace('function buildPayload() {', helper + 'function buildPayload() {');
t = t.replace(
  /color: processName\.includes\('git'\) \? \['#60a5fa','#ffffff'\] : processName\.includes\('megasync'\) \? \['#a78bfa','#ffffff'\] : \['#ff6b9d','#ffffff'\],/g,
  'color: ARC_COLOR_GREEN,'
);
t = t.replace(/color: \['#38bdf8','#ffffff'\],/g, 'color: ARC_COLOR_GREEN,');
t = t.replace(
  /altitude: 0\.12 \+ Math\.min\(0\.28, Math\.abs\(g\.lat - origin\.lat\) \/ 350\),/g,
  'altitude: arcAltitudeFor(origin.lat, origin.lng, g.lat, g.lng),\n      animateMs: Math.max(600, Math.min(1600, 700 + angularDistanceRad(origin.lat, origin.lng, g.lat, g.lng) * 400)),'
);
t = t.replace(
  /altitude: 0\.12 \+ Math\.min\(0\.28, Math\.abs\(g\.lat - flow\.source\.lat\) \/ 350\),/g,
  'altitude: arcAltitudeFor(flow.source.lat, flow.source.lng, g.lat, g.lng),\n      animateMs: Math.max(600, Math.min(1600, 700 + angularDistanceRad(flow.source.lat, flow.source.lng, g.lat, g.lng) * 400)),'
);
t = t.replace(
  /stroke: Math\.max\(0\.35, Math\.min\(2\.4, 0\.5 \+ Math\.log10\(1 \+ packetsPerSecondSafe\(pps\)\) \* 0\.8\)\),/g,
  'stroke: Math.max(0.7, Math.min(2.6, 0.9 + Math.log10(1 + packetsPerSecondSafe(pps)) * 0.85)),'
);
t = t.replace(
  /stroke: 0\.85,\n          altitude: 0\.22,/g,
  'stroke: 1.0,\n          altitude: arcAltitudeFor(origin.lat, origin.lng, n.lat, n.lng),\n          animateMs: Math.max(600, Math.min(1600, 700 + angularDistanceRad(origin.lat, origin.lng, n.lat, n.lng) * 400)),'
);
fs.writeFileSync(path, t);
console.log('patched', path);
