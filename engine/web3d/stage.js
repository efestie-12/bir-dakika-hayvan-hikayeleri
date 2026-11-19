// Bir Dakika! 3D sahne çizici (engine/scene3d.py sürer). Deterministik: window.renderAt(t) yalnız t'ye bağlıdır.
// Yapılandırma window.setup(cfg) ile gelir; tüm zamanlar Python'da saniyeye çevrilmiştir (yalnız sayı).
//   cfg = {w, h, stage:{preset, light, fog, exposure}, camera:{pos, look, fov, drift, to:{pos, look, fov, at, dur}},
//          figures:[{id, x, z, yaw, outfit, body, do:[{at, anim, to, dur}]}],
//          props:[{id, kind|shape, size, color, pos, rot, attach, track:[{at, pos, rot}]}], kinds:{...props.json}}
// Açılar derece. Dünya: y yukarı, +z kameraya doğru; yaw 0 = figür kameraya bakar.
import * as THREE from 'three';
import * as L from './lib.js';

const D2R = Math.PI / 180;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const sstep = (a, b, x) => { const u = clamp((x - a) / Math.max(1e-6, b - a), 0, 1); return u * u * (3 - 2 * u); };
const s5 = (a, b, x) => { const u = clamp((x - a) / Math.max(1e-6, b - a), 0, 1); return u * u * u * (u * (u * 6 - 15) + 10); };
const lerp = (a, b, u) => a + (b - a) * u;
const v3 = (a) => a ? new THREE.Vector3(a[0], a[1], a[2]) : new THREE.Vector3();
const std = (color, rough = .85, metal = 0, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: metal, ...extra });
const box = (s, w, h, d, mat, x, y, z) => L.mesh(new THREE.BoxGeometry(w, h, d), mat, s, x, y, z);
const SOFT = (l) => { l.shadow.radius = 2; l.shadow.blurSamples = 8; };

let r, s, cam, post, pcam, CFG, anchors = {};
const figs = [], props = {}, updaters = [];

// ===================================================================== sahne presetleri
function softBeam(a, b, r0, r1, color, I, o) {
  return [[1, 1, 1, 1], [1.12, 1.45, .45, 1.7], [1.25, 2.0, .22, 2.6]].map(([k0, k1, ii, p]) =>
    L.beam(s, a, b, r0 * k0, r1 * k1, color, I * ii, { top: .22, ...o, pow: (o.pow ?? 2.2) * p }));
}
function brickWall(set, tile, x0, x1, y0, y1, z, th, hole, tint = '#ffffff') {
  const parts = hole ? [[x0, hole[0], y0, y1], [hole[1], x1, y0, y1], [hole[0], hole[1], y0, hole[2]], [hole[0], hole[1], hole[3], y1]] : [[x0, x1, y0, y1]];
  for (const [a, b, c, d] of parts) {
    const t = L.brickTex(set, [(b - a) / tile, (d - c) / tile]);
    t.map.offset.set(a / tile, c / tile); t.bump.offset.copy(t.map.offset);
    box(s, b - a, d - c, th, std(tint, .92, 0, { map: t.map, bumpMap: t.bump, bumpScale: 2.2 }), (a + b) / 2, (c + d) / 2, z);
  }
}
function windowSky(hole, wz, glow = 'rgba(255,170,100,.32)', skyTint = '#ffffff') {
  const [x0, x1, y0, y1] = hole, cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const sky = new THREE.Mesh(new THREE.PlaneGeometry((x1 - x0) * 2.4, (y1 - y0) * 2.4), new THREE.MeshBasicMaterial({ map: L.skyTex(), fog: false, color: skyTint }));
  sky.position.set(cx, cy, wz - .9); s.add(sky);
  const st = std('#5c4a3e', .9);
  box(s, x1 - x0 + .2, .12, .55, st, cx, y0 - .06, wz + .05); box(s, x1 - x0 + .2, .14, .55, st, cx, y1 + .07, wz + .05);
  L.glowSprite(s, new THREE.Vector3(cx, cy, wz + .3), glow, (x1 - x0) * 2.4);
  return { cx, cy };
}
function dustMotes(A, T, n, color, seed) {
  const R = L.rng(seed), d = new THREE.Vector3().subVectors(T, A);
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, -1, 0), d.clone().normalize());
  const base = [], ph = [];
  for (let i = 0; i < n; i++) {
    const t = .08 + R() * .85, rr = (.6 + .5 * t) * Math.sqrt(R()) * .9, an = R() * 6.283;
    base.push(new THREE.Vector3(Math.cos(an) * rr, 0, Math.sin(an) * rr).applyQuaternion(q).add(A.clone().addScaledVector(d, t)));
    ph.push([R() * 6.28, R() * 6.28, R() * 6.28, .5 + R() * .9, R()]);
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(n * 3), 3));
  s.add(new THREE.Points(g, new THREE.PointsMaterial({ color, size: .022, map: L.radialTex('rgba(255,255,255,1)', 'rgba(255,255,255,0)'), transparent: true, opacity: .85, blending: THREE.AdditiveBlending, depthWrite: false })));
  updaters.push(t => {
    const a = g.attributes.position.array;
    for (let i = 0; i < n; i++) {
      const [p1, p2, p3, sp, k] = ph[i], b = base[i];
      a[i * 3] = b.x + Math.sin(t * .45 * sp + p1) * .06 + t * .02;
      a[i * 3 + 1] = b.y + Math.sin(t * .35 * sp + p2) * .05 - ((t * .025 * sp + k * .2) % .2);
      a[i * 3 + 2] = b.z + Math.cos(t * .4 * sp + p3) * .06;
    }
    g.attributes.position.needsUpdate = true;
  });
}
function keyLights(sunPos, sunTarget, sunColor, sunI, fill = '#7f9cd8') {
  s.add(new THREE.HemisphereLight('#d6b08a', '#1a1410', .4));
  const d = new THREE.DirectionalLight('#ffc890', .9); d.position.set(4, 6, 7); d.target.position.set(0, 0, -.5); s.add(d, d.target);
  d.castShadow = true; d.shadow.mapSize.set(2048, 2048); Object.assign(d.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6, near: .5, far: 30 });
  d.shadow.bias = -.0004; d.shadow.normalBias = .02; SOFT(d);
  const f = new THREE.DirectionalLight(fill, .45); f.position.set(-6, 3, 3); s.add(f);
  const sun = new THREE.SpotLight(sunColor, sunI, 0, .2, .5, 2); sun.position.copy(sunPos); sun.target.position.copy(sunTarget); s.add(sun, sun.target);
  sun.castShadow = true; sun.shadow.mapSize.set(1024, 1024); sun.shadow.bias = -.0005; sun.shadow.camera.near = 1; sun.shadow.camera.far = 30; SOFT(sun);
}
function hangingLamp(lx, ly, lz, color, top) {
  L.mesh(new THREE.CylinderGeometry(.01, .01, 2.6, 6), std('#111'), s, lx, ly + 1.4, lz);
  const shade = L.mesh(new THREE.ConeGeometry(.3, .25, 32, 1, true), std('#5a3a22', .5, .5, { side: THREE.DoubleSide }), s, lx, ly + .02, lz); shade.castShadow = false;
  const bulb = new THREE.Mesh(new THREE.SphereGeometry(.07, 16, 12), new THREE.MeshBasicMaterial({ color: '#fff1c8' })); bulb.position.set(lx, ly - .08, lz); s.add(bulb);
  L.glowSprite(s, bulb.position, 'rgba(255,170,90,1)', 1.6);
  const lamp = new THREE.SpotLight(color, 40, 0, .75, .7, 2); lamp.position.set(lx, ly - .1, lz); lamp.target.position.set(lx, 0, lz); s.add(lamp, lamp.target);
  lamp.castShadow = true; lamp.shadow.mapSize.set(1024, 1024); lamp.shadow.bias = -.0008; SOFT(lamp);
  const pt = new THREE.PointLight(color, 4, 0, 2); pt.position.set(lx, ly - .15, lz); s.add(pt);
  softBeam(new THREE.Vector3(lx, ly - .05, lz), new THREE.Vector3(lx, top + .05, lz), .28, .95, '#ffc488', .14, { bot: .3, end: .45, floor: 0.001 });
}
// Tek tezgâh düzeni: odanın ortasında TEK bir iş tezgâhı (arka duvardan net uzak, başka masa yok).
function bench(bx, bz, w, d, top, woodTop, woodLeg) {
  box(s, w, .1, d, woodTop, bx, top - .05, bz);
  for (const [dx, dz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) box(s, .09, top - .1, .09, woodLeg, bx + dx * (w / 2 - .08), (top - .1) / 2, bz + dz * (d / 2 - .08));
  box(s, w - .2, .05, d - .16, woodLeg, bx, .25, bz);
  L.blob(s, bx, bz, Math.max(w, d) * .62, .35);
  anchors.bench = { x: bx, z: bz, top, w, d };
}

const PRESETS = {
  workshop(o) {
    s.background = new THREE.Color('#1b1714'); s.fog = new THREE.FogExp2(o.fog || '#2a211b', .04);
    L.warmEnv(r, s, .4);
    const pk = L.planks(7, [5, 7]);
    box(s, 10, .3, 11, std('#ffffff', .8, 0, { map: pk.map, bumpMap: pk.bump, bumpScale: 2 }), -.5, -.15, 2.3).castShadow = false;
    L.grime(s, 10, 11, -.5, 2.3, 12, .5);
    const wz = -3.0, hole = [-2.55, -1.05, 3.5, 4.6];
    brickWall(L.bricks(8, { mortar: '#2a211b', hue: [12, 16], sat: [20, 18], lum: [26, 38] }), 1.6, -5.5, 4.5, 1.1, 7.5, wz, .4, hole);
    const { cx, cy } = windowSky(hole, wz);
    { const fr = std('#3a281b', .8); box(s, .06, hole[3] - hole[2], .08, fr, cx, cy, wz + .12); box(s, hole[1] - hole[0], .06, .08, fr, cx, cy, wz + .12); }
    { const wood = std('#3a281b', .85), ms = [];
      for (const x of [-3.4, -1.1, 1.2, 3.5]) ms.push(box(s, .22, .3, 8, wood, x, 5.7, 1));
      for (const z of [-2.2, -.2, 1.8]) ms.push(box(s, 12, .26, .22, wood, 0, 5.98, z));
      ms.push(box(s, 14, .1, 8, std('#221810', .95), 0, 6.18, 1)); for (const m of ms) m.castShadow = false; }
    { const wp = L.planks(4, [3, .6]); wp.map.rotation = Math.PI / 2; wp.bump.rotation = Math.PI / 2;
      box(s, 10, 1.1, .5, std('#ffffff', .8, 0, { map: wp.map, bumpMap: wp.bump, bumpScale: 1.5, color: '#b8a08a' }), -.5, .55, wz + .02); }
    const woodD = std('#5a3a20', .8), woodL = std('#9a6a3e', .75), metal = std('#7a7068', .35, .85);
    // duvar rafı (ince, duvara yapışık: masa gibi okunmaz)
    for (const y of [2.1, 2.85]) { box(s, 2.3, .05, .3, woodL, -1.55, y, wz + .36); for (const x of [-2.5, -.6]) box(s, .05, .2, .26, woodD, x, y - .12, wz + .34); }
    { const R = L.rng(4);
      for (const [y, xs] of [[2.12, [-2.45, -2.2, -1.9, -1.55, -1.2, -.85]], [2.87, [-2.4, -2.05, -1.7, -1.2, -.8]]]) for (const x of xs) {
        const k = R();
        if (k < .4) L.mesh(new THREE.CylinderGeometry(.09, .09, .22 + R() * .1, 20), std(['#7a8a5a', '#b8743a', '#8a4a3a', '#c9b06a'][Math.floor(R() * 4)], .3, .1, { transparent: true, opacity: .9 }), s, x, y + .14, wz + .38);
        else if (k < .75) box(s, .22, .16 + R() * .12, .24, std(['#7a5a3a', '#a07a4a', '#6a5a4a'][Math.floor(R() * 3)], .9), x, y + .12, wz + .36);
        else { const g = L.gear(s, .1, 10, .04); g.position.set(x, y + .12, wz + .36); g.rotation.x = Math.PI / 2; }
      } }
    // alet panosu (duvarda)
    box(s, 2.2, 1.25, .05, std('#3e2c1e', .9), 1.25, 2.35, wz + .25);
    const hang = (x, y) => { L.mesh(new THREE.CylinderGeometry(.012, .012, .08, 8), metal, s, x, y, wz + .31).rotation.x = Math.PI / 2; };
    { const g = new THREE.Group(); s.add(g); g.position.set(.45, 2.35, wz + .3);
      const bl = new THREE.Shape(); bl.moveTo(0, .32); bl.lineTo(.13, .32); bl.lineTo(.09, -.4); bl.lineTo(0, -.4);
      L.mesh(new THREE.ExtrudeGeometry(bl, { depth: .01, bevelEnabled: false }), std('#c8c2ba', .25, .9), g, -.06, 0, 0);
      box(g, .14, .2, .04, woodL, 0, .42, 0); hang(.45, 2.9); }
    { const g = new THREE.Group(); s.add(g); g.position.set(.9, 2.35, wz + .3); g.rotation.z = .1;
      box(g, .05, .55, .02, metal, 0, 0, 0); const h = L.mesh(new THREE.TorusGeometry(.06, .02, 8, 20, Math.PI * 1.5), metal, g, 0, .32, 0); h.rotation.z = -Math.PI * .25; hang(.9, 2.72); }
    { const h = L.hammer(s, 1.4); h.position.set(1.32, 2.3, wz + .32); h.rotation.z = Math.PI; hang(1.32, 2.6); }
    { L.mesh(new THREE.TorusGeometry(.17, .035, 10, 32), std('#b39a6a', .95), s, 1.85, 2.42, wz + .32); hang(1.85, 2.62); }
    { const g = new THREE.Group(); s.add(g); g.position.set(2.2, 2.3, wz + .32);
      L.mesh(new THREE.CylinderGeometry(.025, .03, .5, 12), woodL, g, 0, -.05, 0); const hd = L.mesh(new THREE.CylinderGeometry(.08, .08, .22, 20), woodD, g, 0, .25, 0); hd.rotation.z = Math.PI / 2; hang(2.2, 2.62); }
    // yazısız çizim kâğıdı
    { const m = new THREE.Mesh(new THREE.PlaneGeometry(1.0, .72), std('#e6d3b0', .95)); m.position.set(-1.55, 1.45, wz + .21); m.receiveShadow = true; s.add(m);
      const ln = std('#9a6a3a', .9); for (const [w, h, x, y] of [[.7, .006, -1.55, 1.6], [.006, .45, -1.75, 1.42], [.5, .006, -1.45, 1.3], [.006, .3, -1.25, 1.45]]) box(s, w, h, .004, ln, x, y, wz + .215);
      L.mesh(new THREE.TorusGeometry(.12, .005, 6, 40), ln, s, -1.45, 1.45, wz + .215); }
    { const b = L.barrel(s, .95, .36); b.position.set(-1.9, 0, -1.9); }
    { const b = L.barrel(s, .7, .28); b.position.set(-2.45, 0, -1.25); b.rotation.y = 1; }
    // TEK tezgâh: odanın ortasında, arka duvardan ~2,4 m önde
    const BX = .95, BZ = -.45, BW = 1.9, BD = .8, TOP = .92;
    bench(BX, BZ, BW, BD, TOP, std('#ffffff', .7, 0, { map: L.planks(13, [1.4, .6]).map, color: '#c9a07a' }), woodD);
    box(s, .45, .28, .36, std('#7a5a3a', .9), BX + .45, .41, BZ - .05);                       // alt rafta sandık
    { const g = L.gear(s, .2, 14, .06); g.position.set(BX + .55, TOP + .24, BZ - .2); g.rotation.x = Math.PI / 2; g.rotation.z = .2; box(s, .12, .04, .12, woodD, BX + .55, TOP + .02, BZ - .2); }
    box(s, .22, .14, .18, std('#6a4a32', .5, .6), BX + .75, TOP + .07, BZ + .15); box(s, .06, .12, .3, std('#6a4a32', .5, .6), BX + .75, TOP + .14, BZ + .15);
    const lc = o.light || '#ffb36b';
    hangingLamp(BX + .1, 2.75, BZ + .05, lc, TOP);
    const T = new THREE.Vector3(-.6, 0, .1), Wc = new THREE.Vector3(cx, cy, wz);
    const P = Wc.clone().addScaledVector(Wc.clone().sub(T), .8), A = new THREE.Vector3(cx, cy, wz + .2);
    softBeam(A, T, .6, .95, '#ffae6a', .2, { bot: .2, end: .6, pow: 1.5, wall: wz + .2, floor: .5 });
    dustMotes(A, T, 220, '#ffe0b0', 8);
    L.haze(s, [[cx, cy - .2, wz + .9, 3.0, 2.0, '#ff9b5a', .18], [BX, 1.6, BZ + .5, 3, 3, '#ffb070', .16], [0, 1, -.5, 8, 3.5, '#a8704a', .14]]);
    keyLights(P, T, '#ffb070', 120);
  },
  dungeon(o) {
    s.background = new THREE.Color('#0d0f14'); s.fog = new THREE.FogExp2(o.fog || '#141820', .05);
    L.warmEnv(r, s, .25);
    const fl = L.cobble(3, [6, 6], { hue: [200, 30], sat: [4, 10], lum: [16, 30] });
    box(s, 10, .3, 11, std('#ffffff', .9, 0, { map: fl.map, bumpMap: fl.bump, bumpScale: 3 }), -.5, -.15, 2.3).castShadow = false;
    L.grime(s, 10, 11, -.5, 2.3, 5, .6);
    const wz = -3.0, hole = [-1.9, -1.0, 3.0, 4.1];
    const ws = L.cobble(11, [1, 1], { rows: 8, bg: '#0a0b0e', hue: [205, 25], sat: [4, 10], lum: [20, 34] });
    const wall = (x0, x1) => { const t = L.cobble(11, [(x1 - x0) / 2.2, 6.4 / 2.2], { rows: 8, bg: '#0a0b0e', hue: [205, 25], sat: [4, 10], lum: [20, 34] });
      box(s, x1 - x0, 6.4, .4, std('#ffffff', .95, 0, { map: t.map, bumpMap: t.bump, bumpScale: 3 }), (x0 + x1) / 2, 3.2, wz); };
    wall(-5.5, hole[0]); wall(hole[1], 4.5);
    { const t = ws; box(s, hole[1] - hole[0], hole[2], .4, std('#ffffff', .95, 0, { map: t.map, bumpMap: t.bump }), (hole[0] + hole[1]) / 2, hole[2] / 2, wz);
      box(s, hole[1] - hole[0], 6.4 - hole[3], .4, std('#ffffff', .95, 0, { map: t.map, bumpMap: t.bump }), (hole[0] + hole[1]) / 2, (6.4 + hole[3]) / 2, wz); }
    const { cx, cy } = windowSky(hole, wz, 'rgba(120,160,230,.25)', '#6a7fb0');
    const iron = std('#2b2f35', .45, .8);
    for (let i = 1; i < 5; i++) box(s, .035, hole[3] - hole[2], .05, iron, hole[0] + (hole[1] - hole[0]) * i / 5, cy, wz + .1);
    // taş sıra (bench çapası)
    const BX = .95, BZ = -.45, BW = 1.9, BD = .8, TOP = .85;
    const st = L.cobble(5, [1.2, .5], { rows: 4, hue: [200, 30], sat: [3, 8], lum: [24, 36] });
    box(s, BW, .14, BD, std('#ffffff', .9, 0, { map: st.map, bumpMap: st.bump, bumpScale: 2 }), BX, TOP - .07, BZ);
    for (const dx of [-1, 1]) box(s, .3, TOP - .14, BD - .1, std('#4a4e56', .95), BX + dx * (BW / 2 - .2), (TOP - .14) / 2, BZ);
    anchors.bench = { x: BX, z: BZ, top: TOP, w: BW, d: BD };
    L.blob(s, BX, BZ, 1.2, .35);
    // duvar meşalesi: sıcak nokta ışık + parıltı (alev titremesi t'ye bağlı, deterministik)
    const tx = 1.9, ty = 2.2, tz = wz + .35;
    box(s, .08, .4, .08, std('#3a2a1a', .9), tx, ty - .2, tz);
    const fl2 = L.glowSprite(s, new THREE.Vector3(tx, ty + .08, tz + .05), 'rgba(255,160,70,1)', 1.2);
    const tl = new THREE.PointLight(o.light || '#ff9a4a', 9, 0, 2); tl.position.set(tx, ty + .1, tz + .3); tl.castShadow = true; tl.shadow.mapSize.set(512, 512); s.add(tl);
    updaters.push(t => { const k = 1 + .12 * Math.sin(t * 13.1) + .07 * Math.sin(t * 29.7 + 1); tl.intensity = 9 * k; fl2.scale.setScalar(1.2 * k); });
    const T = new THREE.Vector3(-.4, 0, .2), Wc = new THREE.Vector3(cx, cy, wz);
    const P = Wc.clone().addScaledVector(Wc.clone().sub(T), .8), A = new THREE.Vector3(cx, cy, wz + .2);
    softBeam(A, T, .45, .85, '#9fbfff', .16, { bot: .2, end: .6, pow: 1.5, wall: wz + .2, floor: .5 });
    dustMotes(A, T, 160, '#cfe0ff', 9);
    L.haze(s, [[cx, cy - .2, wz + .9, 2.6, 2.0, '#6f8fd0', .14], [tx, ty, tz + .4, 2, 2, '#ff9a4a', .14]]);
    keyLights(P, T, '#a8c4ff', 90, '#5f7fc8');
  },
};

// ===================================================================== prop'lar
function propMesh(p) {
  const K = (CFG.kinds || {})[p.kind] || {}, col = p.color || K.color, k = +(p.size ?? K.size ?? 1);
  const g = new THREE.Group(); s.add(g);
  if (p.shape) {
    const sz = Array.isArray(p.size) ? p.size : [.3, .3, .3], m = std(p.color || '#8a6a44', .8);
    const geo = p.shape === 'box' ? new THREE.BoxGeometry(sz[0], sz[1], sz[2]) : p.shape === 'cylinder' ? new THREE.CylinderGeometry(sz[0] / 2, sz[0] / 2, sz[1], 24) : new THREE.SphereGeometry(sz[0] / 2, 24, 16);
    L.mesh(geo, m, g, 0, p.shape === 'sphere' ? sz[0] / 2 : sz[1] / 2, 0);
    return g;
  }
  switch (p.kind) {
    case 'hammer': { const h = L.hammer(g, k); h.children[0].material = std(col, .7); break; }
    case 'wrench': { const m = std(col, .35, .85); box(g, .035 * k, .3 * k, .015 * k, m, 0, 0, 0);
      const hd = L.mesh(new THREE.TorusGeometry(.045 * k, .016 * k, 8, 20, Math.PI * 1.4), m, g, 0, .17 * k, 0); hd.rotation.z = -Math.PI * .2; break; }
    case 'gear': { const gg = L.gear(g, .12 * k, 11, .04 * k, std(col, .35, .8)); gg.rotation.x = Math.PI / 2; gg.position.y = .12 * k; break; }
    case 'bottle': L.mesh(new THREE.CylinderGeometry(.06 * k, .07 * k, .22 * k, 20), std(col, .3, .1, { transparent: true, opacity: .9 }), g, 0, .11 * k, 0);
      L.mesh(new THREE.CylinderGeometry(.025 * k, .03 * k, .08 * k, 12), std(col, .3, .1), g, 0, .26 * k, 0); break;
    case 'lantern': { box(g, .16 * k, .03 * k, .16 * k, std(col, .6, .5), 0, .015 * k, 0); box(g, .16 * k, .03 * k, .16 * k, std(col, .6, .5), 0, .25 * k, 0);
      const gl = new THREE.Mesh(new THREE.CylinderGeometry(.06 * k, .06 * k, .2 * k, 16), new THREE.MeshBasicMaterial({ color: '#ffd28a' })); gl.position.y = .13 * k; g.add(gl);
      L.mesh(new THREE.TorusGeometry(.05 * k, .008 * k, 6, 16, Math.PI), std(col, .6, .5), g, 0, .27 * k, 0);
      L.glowSprite(g, new THREE.Vector3(0, .13 * k, 0), 'rgba(255,180,90,.9)', .7 * k); break; }
    case 'crate': box(g, .45 * k, .38 * k, .4 * k, std(col, .9), 0, .19 * k, 0); break;
    case 'barrel': L.barrel(g, .9 * k, .34 * k); break;
    case 'bucket': L.mesh(new THREE.CylinderGeometry(.16 * k, .12 * k, .3 * k, 24, 1, true), std(col, .7, .4, { side: THREE.DoubleSide }), g, 0, .15 * k, 0); break;
    case 'stool': box(g, .4 * k, .05 * k, .4 * k, std(col, .8), 0, .48 * k, 0); for (const [dx, dz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) box(g, .04 * k, .46 * k, .04 * k, std(col, .8), dx * .16 * k, .23 * k, dz * .16 * k); break;
    case 'anvil': { const m = std(col, .4, .8); box(g, .2 * k, .25 * k, .2 * k, std('#5a3a20', .9), 0, .125 * k, 0); box(g, .5 * k, .12 * k, .18 * k, m, 0, .31 * k, 0); break; }
    default: box(g, .2, .2, .2, std(col || '#888', .8), 0, .1, 0);
  }
  return g;
}
function eulerQ(rot) { return new THREE.Quaternion().setFromEuler(new THREE.Euler((rot[0] || 0) * D2R, (rot[1] || 0) * D2R, (rot[2] || 0) * D2R)); }
function buildProps() {
  for (const p of CFG.props || []) {
    const K = (CFG.kinds || {})[p.kind] || {};
    const obj = propMesh(p); obj.matrixAutoUpdate = false;
    const pos = v3(p.pos || [0, 0, 0]);
    if (p.attach === 'bench' && anchors.bench) pos.y += anchors.bench.top + (K.lift || 0);
    const rest = new THREE.Matrix4().compose(pos, eulerQ(p.rot || K.rot || [0, 0, 0]), new THREE.Vector3(1, 1, 1));
    const P = { id: p.id, obj, rest, grip: v3(K.grip || [0, 0, 0]).multiplyScalar(+(p.size ?? K.size ?? 1)), holder: null, from: Infinity, off: null, track: (p.track || []).slice().sort((a, b) => a.at - b.at), sleeve: null };
    // kavrama kılıfı: tutulunca sapı saran eldiven halkası (çekicin elin içinden geçtiği görünmesin)
    if (K.holdable) { const sl = L.mesh(new THREE.CylinderGeometry(.04, .04, .1, 16), std('#4a3020', .7), obj, P.grip.x, P.grip.y, P.grip.z); sl.visible = false; P.sleeve = sl; }
    obj.matrix.copy(rest); props[p.id] = P;
    if (p.attach && p.attach !== 'bench') P.attachTo = p.attach;   // figür id: baştan elinde
  }
}
function trackMatrix(P, t) {
  const tr = P.track; if (!tr.length) return P.rest;
  const pr = new THREE.Vector3(), qr = new THREE.Quaternion(), sc = new THREE.Vector3(); P.rest.decompose(pr, qr, sc);
  let pos = pr.clone(), q = qr.clone();
  for (const k of tr) {
    const u = s5(k.at, k.at + (k.dur || .8), t); if (u <= 0) break;
    if (k.pos) pos.lerp(v3(k.pos), u); if (k.rot) q.slerp(eulerQ(k.rot), u);
  }
  return new THREE.Matrix4().compose(pos, q, sc);
}

// ===================================================================== manken + hareket
const Y = new THREE.Vector3(0, -1, 0), tmpQ = new THREE.Quaternion();
function aim(bone, dirW) { bone.parent.getWorldQuaternion(tmpQ); const loc = dirW.clone().applyQuaternion(tmpQ.invert()).normalize(); bone.quaternion.setFromUnitVectors(Y, loc); bone.updateMatrixWorld(true); }
function ik(upper, lower, L1, L2, target, pole) {
  upper.parent.updateMatrixWorld(true);
  const a = upper.getWorldPosition(new THREE.Vector3()), d = target.clone().sub(a);
  const dist = clamp(d.length(), .05, L1 + L2 - .002), dir = d.normalize();
  const ca = clamp((L1 * L1 + dist * dist - L2 * L2) / (2 * L1 * dist), -1, 1), sa = Math.sqrt(1 - ca * ca);
  const bend = pole.clone().addScaledVector(dir, -pole.dot(dir)).normalize();
  const up = dir.clone().multiplyScalar(ca).addScaledVector(bend, sa);
  aim(upper, up);
  aim(lower, a.clone().addScaledVector(dir, dist).sub(a.clone().addScaledVector(up, L1)));
}
const ANK = .105, LT = .38, LS = .38, LA = .31, LF = .29, STEP = .3, STANCE = .37, SWING = 2 * STEP - STANCE, LAT = .11, WALK_V = 1.5;
const yawQ = (y, p = 0) => new THREE.Quaternion().setFromEuler(new THREE.Euler(p, y, 0, 'YXZ'));

function makeFigure(f) {
  const M = L.mannequin(f.body ? { body: f.body } : {});
  const o = f.outfit || 'worker';
  if (o === 'worker') L.outfitWorker(M); else if (o === 'prisoner') L.outfitPrisoner(M); else if (o === 'guard') L.outfitGuard(M);
  s.add(M.root);
  const F = { id: f.id, M, blob: L.blob(s, 0, 0, .45, .45), walks: [], turns: [], waves: [], grab: null, lifts: [] };
  let pos = new THREE.Vector2(+f.x || 0, +f.z || 0), yaw = (+f.yaw || 0) * D2R;
  F.p0 = pos.clone(); F.yaw0 = yaw;
  for (const a of (f.do || []).slice().sort((a, b) => a.at - b.at)) {
    if (a.anim === 'walk') {
      const to = new THREE.Vector2(a.to[0], a.to[1]), dist = to.distanceTo(pos);
      const dur = a.dur || Math.max(.6, dist / WALK_V), ta = a.at <= 0 ? 0 : Math.min(.4, dur / 3), td = Math.min(.6, dur / 2.5);
      const dir = to.clone().sub(pos), w = { at: a.at, dur, ta, td, from: pos.clone(), to, v: 1 / (dur - ta / 2 - td / 2), yaw: Math.atan2(dir.x, dir.y) };
      F.walks.push(w); F.turns.push({ t0: a.at <= 0 ? -1 : a.at - .25, t1: a.at <= 0 ? -.99 : a.at + .25, y: w.yaw }); pos = to;
    } else if (a.anim === 'turn') F.turns.push({ t0: a.at, t1: a.at + (a.dur || .8), y: (+a.to || 0) * D2R });
    else if (a.anim === 'wave') F.waves.push({ at: a.at, dur: a.dur || 1.5 });
    else if (a.anim === 'grab') F.grab = { at: a.at, dur: a.dur || .8, prop: a.to };
    else if (a.anim === 'lift') F.lifts.push({ at: a.at, dur: a.dur || .8 });
  }
  F.turns.sort((a, b) => a.t0 - b.t0);
  // adım planı: sabit kadans; basış noktası = duruşun ortasındaki kök konumu + yan kayma
  F.steps = { LL: [], RL: [] };
  const T1 = (CFG.dur || 10) + 2;
  for (let k = -8; k * STEP < T1; k++) {
    const tl = k * STEP + .05, foot = (k & 1) === 0 ? 'LL' : 'RL', side = foot === 'LL' ? -1 : 1, tm = tl + STANCE / 2;
    const p = rootXZ(F, tm), yw = yawOf(F, tm);
    p.x += Math.cos(yw) * LAT * side; p.y += -Math.sin(yw) * LAT * side;
    F.steps[foot].push({ tl, p, yw: yw - side * .06 });
  }
  figs.push(F);
  return F;
}
function walkU(w, t) { // 0..1 yol oranı (yamuk hız profili; at<=0 ise t<at için geriye uzar)
  const tau = t - w.at, D = w.dur;
  if (tau <= 0) return w.ta === 0 ? w.v * tau : 0;
  if (tau < w.ta) return w.v * tau * tau / (2 * w.ta);
  if (tau < D - w.td) return w.v * (w.ta / 2 + tau - w.ta);
  if (tau < D) return 1 - w.v * (D - tau) ** 2 / (2 * w.td);
  return 1;
}
function rootXZ(F, t) {
  let p = F.p0.clone();
  for (const w of F.walks) { const u = walkU(w, t); if (u === 0 && t < w.at) break; p = w.from.clone().lerp(w.to, u); }
  return p;
}
function yawOf(F, t) {
  let y = F.yaw0;
  for (const tr of F.turns) { if (t < tr.t0) break; let d = tr.y - y; d = Math.atan2(Math.sin(d), Math.cos(d)); y = y + d * s5(tr.t0, tr.t1, t); }
  return y;
}
function walkK(F, t) {
  let k = 0;
  for (const w of F.walks) k = Math.max(k, (w.ta === 0 ? 1 : sstep(w.at - .1, w.at + w.ta + .1, t)) * (1 - sstep(w.at + w.dur - .3, w.at + w.dur + .1, t)));
  return k;
}
function footAt(F, foot, t) {
  const st = F.steps[foot]; let i = 0; while (i + 1 < st.length && st[i + 1].tl <= t) i++;
  const cur = st[i], nxt = st[Math.min(i + 1, st.length - 1)], lift = nxt.tl - SWING;
  if (t < lift || nxt === cur) return { x: cur.p.x, z: cur.p.y, y: 0, yaw: cur.yw, pitch: 0 };
  const u = clamp((t - lift) / SWING, 0, 1), dist = cur.p.distanceTo(nxt.p), k = clamp(dist / .12, 0, 1);
  const e = u - Math.sin(2 * Math.PI * u) / (2 * Math.PI);
  return { x: lerp(cur.p.x, nxt.p.x, e), z: lerp(cur.p.y, nxt.p.y, e), y: Math.sin(Math.PI * u) * .085 * k, yaw: lerp(cur.yw, nxt.yw, e), pitch: Math.sin(Math.PI * u) * -.25 * k * (1 - u) };
}
const envW = (list, t) => list.reduce((m, a) => Math.max(m, sstep(a.at, a.at + .4, t) * (1 - sstep(a.at + a.dur - .4, a.at + a.dur, t))), 0);

function poseAt(F, t) {
  const M = F.M, rp = rootXZ(F, t), yaw = yawOf(F, t), wk = walkK(F, t);
  M.root.position.set(rp.x, 0, rp.y); M.root.rotation.set(0, yaw, 0);
  const fL = footAt(F, 'LL', t), fR = footAt(F, 'RL', t);
  const fwdOf = f => (f.x - rp.x) * Math.sin(yaw) + (f.z - rp.y) * Math.cos(yaw);
  const zL = fwdOf(fL), zR = fwdOf(fR);
  const wave = envW(F.waves, t);
  const G = F.grab, reach = G ? sstep(G.at, G.at + G.dur, t) : 0;
  const lift = F.lifts.reduce((m, a) => Math.max(m, sstep(a.at, a.at + a.dur, t)), 0) * (G ? 1 : 0);
  const breath = Math.sin(t * 1.9) * .012 * (1 - wk);
  M.pelvis.rotation.set(0, (zL - zR) * .35, 0);
  M.spine.rotation.set(.06 * wk - .05 * wave + .32 * reach * (1 - lift) + .02 * lift + breath, -(zL - zR) * .55 + .16 * wave + .15 * reach * (1 - lift) - .2 * lift, .05 * wave - .2 * reach * (1 - lift) - .06 * lift);
  M.neck.rotation.set(.05 * wk + .35 * reach * (1 - lift) - .12 * lift + .05 * Math.sin(t * 2.4) * wave, -.25 * wk + .2 * reach * (1 - lift) + .35 * lift - .08 * wave, .08 * wave - .1 * lift);
  M.pelvis.position.y = .95; M.root.updateMatrixWorld(true);
  let hy = .935 - wk * .02 * (1 + Math.cos(4 * Math.PI * (t - .05) / (2 * STEP)));
  for (const [f, side] of [[fL, -1], [fR, 1]]) {
    const h = M[side < 0 ? 'LL' : 'RL'].hip.getWorldPosition(new THREE.Vector3()), dx = h.x - f.x, dz = h.z - f.z;
    hy = Math.min(hy, f.y + ANK + Math.sqrt(Math.max(0, (LT + LS - .01) ** 2 - dx * dx - dz * dz)) + .08);
  }
  M.pelvis.position.y = hy; M.root.updateMatrixWorld(true);
  for (const [f, k] of [[fL, 'LL'], [fR, 'RL']]) {
    const leg = M[k], fwd = new THREE.Vector3(Math.sin(f.yaw), 0, Math.cos(f.yaw));
    ik(leg.hip, leg.kn, LT, LS, new THREE.Vector3(f.x, f.y + ANK, f.z), fwd.clone().add(new THREE.Vector3(0, .15, 0)));
    leg.kn.updateMatrixWorld(true); leg.kn.getWorldQuaternion(tmpQ);
    leg.an.quaternion.copy(tmpQ.invert().multiply(yawQ(f.yaw, f.pitch))); leg.an.updateMatrixWorld(true);
  }
  const swingL = clamp(-1.1 * zR, -.5, .5) * wk, swingR = clamp(-1.1 * zL, -.5, .5) * wk;
  // sol kol: el sallama — ana frekans + ikinci hafif frekans (mekanik görünmesin)
  const w0 = F.waves.length ? F.waves.find(a => t >= a.at - .5)?.at ?? F.waves[0].at : 0, tw = t - w0;
  const wv = .82 * Math.sin(2 * Math.PI * 2.2 * tw) + .18 * Math.sin(2 * Math.PI * 3.6 * tw + 1.1);
  const wv2 = Math.sin(2 * Math.PI * 1.1 * tw + .4);
  M.L.sh.rotation.set(swingL * (1 - wave) - .25 * wave + .04 * wv2 * wave, 0, lerp(-.13, -2.35, wave) + .06 * wv * wave);
  M.L.el.rotation.set(lerp(-.18 - .12 * wk, -.15, wave), 0, lerp(0, -.5 + .5 * wv, wave));
  M.L.wr.rotation.set(.08 * wv2 * wave, 0, -.25 * wv * wave);
  M.R.sh.rotation.set(swingR + .02 * Math.sin(t * 1.9) * (1 - wk), 0, .13); M.R.el.rotation.set(-.18 - .12 * wk, 0, 0); M.R.wr.rotation.set(0, 0, 0);
  M.root.updateMatrixWorld(true);
  if (G && reach > 0 && props[G.prop]) {
    const P = props[G.prop], restM = trackMatrix(P, G.at);
    const shp = M.R.sh.getWorldPosition(new THREE.Vector3()), rest = M.R.wr.getWorldPosition(new THREE.Vector3());
    const grip = P.grip.clone().applyMatrix4(restM).add(new THREE.Vector3(0, .085, 0));
    const right = new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw)), fwd = new THREE.Vector3(Math.sin(yaw), 0, Math.cos(yaw));
    const up = shp.clone().addScaledVector(right, .44).addScaledVector(fwd, .22).add(new THREE.Vector3(0, .12, 0));  // omuz hizası: kaldırılan alet başın üstüne taşmasın
    let tgt = rest.clone().lerp(grip, reach);
    if (lift > 0) { const a = grip.clone().add(new THREE.Vector3(0, .25, 0)), p1 = grip.clone().lerp(a, lift), p2 = a.clone().lerp(up, lift); tgt = p1.lerp(p2, lift);
      const lEnd = F.lifts[F.lifts.length - 1]; tgt.y += Math.sin(t * 3.1) * .015 * sstep(lEnd.at + lEnd.dur, lEnd.at + lEnd.dur + .3, t); }
    const pole = right.clone().multiplyScalar(.8).add(new THREE.Vector3(0, -.6, 0)).addScaledVector(fwd, -.3 + .2 * lift);
    ik(M.R.sh, M.R.el, LA, LF, tgt, pole);
    M.R.wr.rotation.set(.5 * lift, 0, 0); M.R.wr.updateMatrixWorld(true);
  }
}
function updateProps(t) {
  for (const P of Object.values(props)) {
    let held = false;
    if (P.holder && t >= P.from && P.off) { P.obj.matrix.multiplyMatrices(P.holder.M.R.wr.matrixWorld, P.off); held = true; }
    else P.obj.matrix.copy(trackMatrix(P, t));
    P.obj.matrixWorldNeedsUpdate = true;
    if (P.sleeve) P.sleeve.visible = held;
  }
}
function prepareGrips() {
  for (const F of figs) if (F.grab && props[F.grab.prop]) {
    const P = props[F.grab.prop], tg = F.grab.at + F.grab.dur;
    poseAt(F, tg); P.holder = F; P.from = tg; P.off = F.M.R.wr.matrixWorld.clone().invert().multiply(trackMatrix(P, F.grab.at));
  }
  for (const P of Object.values(props)) if (P.attachTo) {
    const F = figs.find(f => f.id === P.attachTo); if (!F || P.holder) continue;
    poseAt(F, 0); F.M.R.wr.updateMatrixWorld(true);
    const hand = new THREE.Matrix4().compose(new THREE.Vector3(0, -.085, 0), new THREE.Quaternion(), new THREE.Vector3(1, 1, 1));
    const gi = new THREE.Matrix4().makeTranslation(-P.grip.x, -P.grip.y, -P.grip.z);
    P.holder = F; P.from = -1e9; P.off = hand.multiply(gi);
  }
}

// ===================================================================== kamera
function camAt(t) {
  const C = CFG.camera || {}, to = C.to || null, k = to ? s5(to.at || 0, (to.at || 0) + (to.dur || 3), t) : 0;
  const p0 = v3(C.pos || [0, 1.2, 6.5]), l0 = v3(C.look || [0, 1, 0]), f0 = +(C.fov || 50);
  const p = to && to.pos ? p0.clone().lerp(v3(to.pos), k) : p0, l = to && to.look ? l0.clone().lerp(v3(to.look), k) : l0;
  const dr = C.drift ?? .015;
  cam.position.set(p.x + Math.sin(t * .7) * dr, p.y + Math.sin(t * .53 + 1) * dr * .4, p.z);
  cam.lookAt(l); cam.fov = to && to.fov ? lerp(f0, +to.fov, k) : f0; cam.updateProjectionMatrix();
}

// ===================================================================== giriş noktaları
window.setup = (cfg) => {
  CFG = cfg;
  const c = document.getElementById('c'); c.width = cfg.w; c.height = cfg.h;
  r = new THREE.WebGLRenderer({ canvas: c, antialias: true, preserveDrawingBuffer: true });
  r.setSize(cfg.w, cfg.h, false); r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFShadowMap;
  r.toneMapping = THREE.ACESFilmicToneMapping; r.toneMappingExposure = +((cfg.stage || {}).exposure || 1.1); r.outputColorSpace = THREE.SRGBColorSpace;
  s = new THREE.Scene(); cam = new THREE.PerspectiveCamera(50, cfg.w / cfg.h, .05, 120);
  const st = cfg.stage || {}; (PRESETS[st.preset] || PRESETS.workshop)(st);
  buildProps();
  for (const f of cfg.figures || []) makeFigure(f);
  prepareGrips();
  post = new THREE.Scene(); pcam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  post.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({ transparent: true, depthTest: false, depthWrite: false,
    vertexShader: 'varying vec2 vU; void main(){ vU = uv; gl_Position = vec4(position.xy, 0., 1.); }',
    fragmentShader: 'varying vec2 vU; void main(){ vec2 d = vU - vec2(.5, .58); float v = smoothstep(.35, .95, length(d * vec2(1.25, .9))); float b = smoothstep(.36, .0, vU.y); gl_FragColor = vec4(.04, .025, .015, clamp(v * .55 + b * .45, 0., .8)); }' })));
  r.autoClear = false;
  window.ready = true;
  return true;
};
window.renderAt = (t) => {
  for (const F of figs) { poseAt(F, t); F.blob.position.set(F.M.root.position.x, .004, F.M.root.position.z); }
  updateProps(t); camAt(t); for (const u of updaters) u(t);
  r.clear(); r.render(s, cam); r.render(post, pcam); return true;
};
// test yardımcısı: figürlerin ayak/baş noktalarının kanvas koordinatları (0..w, 0..h)
window.probe = (t) => {
  window.renderAt(t); const out = {}; const W = CFG.w, H = CFG.h;
  const pr = o => { const v = o.getWorldPosition(new THREE.Vector3()), w = v.clone(); v.project(cam); return { x: +((v.x + 1) / 2 * W).toFixed(1), y: +((1 - v.y) / 2 * H).toFixed(1), wy: +w.y.toFixed(3) }; };
  for (const F of figs) out[F.id] = { LL: pr(F.M.LL.heel), RL: pr(F.M.RL.heel), head: pr(F.M.head) };
  return out;
};
window.ready0 = true;
