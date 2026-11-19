// Ortak yardımcılar: kodla doku, manken iskeleti, kıyafet aksesuarları, plan çizgileri.
import * as THREE from 'three';

export function rng(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
function cv(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
function noise(ctx, w, h, amt, R) {
  const im = ctx.getImageData(0, 0, w, h), d = im.data;
  for (let i = 0; i < d.length; i += 4) { const n = (R() - .5) * amt; d[i] += n; d[i + 1] += n; d[i + 2] += n; }
  ctx.putImageData(im, 0, 0);
}
function tex(c, srgb, rep = [1, 1]) {
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rep[0], rep[1]); t.anisotropy = 8;
  return t;
}
function blurred(src, px) { const c = cv(src.width, src.height), x = c.getContext('2d'); x.filter = `blur(${px}px)`; x.drawImage(src, 0, 0); return c; }

// ---------- kaldırım taşı ----------
export function cobble(seed = 3, rep = [3, 3], o = {}) {
  o = { rows: 12, bg: '#120e0b', hue: [16, 26], sat: [6, 16], lum: [20, 36], ...o };
  const S = 1024, R = rng(seed), c = cv(S, S), b = cv(S, S), x = c.getContext('2d'), y = b.getContext('2d');
  x.fillStyle = o.bg; x.fillRect(0, 0, S, S); y.fillStyle = '#000'; y.fillRect(0, 0, S, S);
  const rows = o.rows, rh = S / rows;
  const stones = [];
  for (let r = 0; r < rows; r++) {
    let px = -R() * rh;
    while (px < S) { const w = rh * (0.7 + R() * 1.1); stones.push([px, r * rh, w, rh]); px += w; }
  }
  for (const [sx, sy, w, h] of stones) {
    const g = 6 + R() * 5, cx = sx + w / 2, cy = sy + h / 2, rx = w / 2 - g, ry = h / 2 - g;
    const pts = []; const N = 14;
    for (let k = 0; k < N; k++) {
      const a = k / N * Math.PI * 2, co = Math.cos(a), si = Math.sin(a);
      const ex = Math.sign(co) * Math.pow(Math.abs(co), .55), ey = Math.sign(si) * Math.pow(Math.abs(si), .55);
      pts.push([cx + ex * rx + (R() - .5) * 7, cy + ey * ry + (R() - .5) * 7]);
    }
    let lum = o.lum[0] + R() * (o.lum[1] - o.lum[0]), hue = o.hue[0] + R() * o.hue[1], sat = o.sat[0] + R() * o.sat[1];
    const kk = R(); if (kk < .12) { hue = 30 + R() * 12; sat += 10; lum += 4; } else if (kk < .2) { lum -= 7; } else if (kk < .26) { hue = 8; sat += 8; }
    const crack = R() < .4 ? (() => { const a = R() * 6.28, L = 0.4 + R() * 0.6; const p = [[cx + Math.cos(a) * rx, cy + Math.sin(a) * ry]]; for (let i = 0; i < 4; i++) { const t = (i + 1) / 4; p.push([cx + Math.cos(a) * rx * (1 - t * L) + (R() - .5) * 18, cy + Math.sin(a) * ry * (1 - t * L) + (R() - .5) * 18]); } return p; })() : null;
    const specks = []; for (let i = 0; i < 25; i++) specks.push([cx + (R() - .5) * rx * 1.6, cy + (R() - .5) * ry * 1.6, 1 + R() * 2.5, R() < .5]);
    for (const off of [-S, 0, S]) {
      const path = new Path2D(); const P = pts.map(p => [p[0] + off, p[1]]);
      const m0 = [(P[N - 1][0] + P[0][0]) / 2, (P[N - 1][1] + P[0][1]) / 2]; path.moveTo(...m0);
      for (let k = 0; k < N; k++) { const a = P[k], n = P[(k + 1) % N]; path.quadraticCurveTo(a[0], a[1], (a[0] + n[0]) / 2, (a[1] + n[1]) / 2); }
      x.fillStyle = `hsl(${hue},${sat}%,${lum}%)`; x.fill(path);
      x.save(); x.clip(path);
      const gr = x.createLinearGradient(cx + off - rx, cy - ry, cx + off + rx, cy + ry); gr.addColorStop(0, 'rgba(255,255,255,.10)'); gr.addColorStop(1, 'rgba(0,0,0,.18)');
      x.fillStyle = gr; x.fillRect(sx + off, sy, w, h);
      for (const [qx, qy, qr, l] of specks) { x.fillStyle = l ? 'rgba(255,230,200,.07)' : 'rgba(0,0,0,.18)'; x.beginPath(); x.arc(qx + off, qy, qr, 0, 7); x.fill(); }
      x.restore();
      const gb = y.createRadialGradient(cx + off - rx * .2, cy - ry * .2, 2, cx + off, cy, Math.max(rx, ry) * 1.05);
      gb.addColorStop(0, '#f0f0f0'); gb.addColorStop(.7, '#b0b0b0'); gb.addColorStop(1, '#505050'); y.fillStyle = gb; y.fill(path);
      if (crack) for (const [ctx, col, lw] of [[x, 'rgba(8,10,16,.85)', 2.2], [y, '#202020', 3]]) {
        ctx.strokeStyle = col === 'rgba(8,10,16,.85)' ? 'rgba(10,6,4,.85)' : col; ctx.lineWidth = lw; ctx.beginPath(); ctx.moveTo(crack[0][0] + off, crack[0][1]);
        for (const p of crack.slice(1)) ctx.lineTo(p[0] + off, p[1]); ctx.stroke();
      }
    }
  }
  noise(x, S, S, 18, R);
  return { map: tex(c, true, rep), bump: tex(blurred(b, 2), false, rep) };
}

// ---------- tuğla ----------
export function bricks(seed = 5, pal = { mortar: '#1e2228', hue: [200, 30], sat: [5, 14], lum: [26, 40] }) {
  const S = 1024, R = rng(seed), c = cv(S, S), b = cv(S, S), x = c.getContext('2d'), y = b.getContext('2d');
  x.fillStyle = pal.mortar; x.fillRect(0, 0, S, S); y.fillStyle = '#000'; y.fillRect(0, 0, S, S);
  const rows = 16, rh = S / rows, bw = S / 6;
  for (let r = 0; r < rows; r++) for (let k = -1; k < 7; k++) {
    const bx = k * bw + (r % 2) * bw / 2, by = r * rh, g = 4 + R() * 2;
    const hue = pal.hue[0] + R() * pal.hue[1], sat = pal.sat[0] + R() * pal.sat[1], lum = pal.lum[0] + R() * (pal.lum[1] - pal.lum[0]);
    for (const off of [0]) {
      x.fillStyle = `hsl(${hue},${sat}%,${lum}%)`; x.beginPath(); x.roundRect(bx + g, by + g, bw - 2 * g, rh - 2 * g, 5); x.fill();
      if (R() < .3) { x.fillStyle = 'rgba(0,0,0,.25)'; x.beginPath(); x.arc(bx + R() * bw, by + (R() < .5 ? g : rh - g), 6 + R() * 8, 0, 7); x.fill(); }
      y.fillStyle = `hsl(0,0%,${55 + R() * 25}%)`; y.beginPath(); y.roundRect(bx + g + 2, by + g + 2, bw - 2 * g - 4, rh - 2 * g - 4, 6); y.fill();
    }
  }
  noise(x, S, S, 22, R);
  return { c, b: blurred(b, 2.5) };
}
export function brickTex(set, rep) { return { map: tex(set.c, true, rep), bump: tex(set.b, false, rep) }; }

// ---------- ahşap tahta ----------
export function planks(seed = 9, rep = [2, 2]) {
  const S = 1024, R = rng(seed), c = cv(S, S), b = cv(S, S), x = c.getContext('2d'), y = b.getContext('2d');
  const n = 6, pw = S / n;
  for (let i = 0; i < n; i++) {
    let py = -R() * S;
    while (py < S) {
      const L = S * (0.5 + R() * 0.7);
      const hue = 24 + R() * 10, sat = 32 + R() * 14, lum = 26 + R() * 13;
      for (const off of [0, S]) {
        const X = i * pw, Y = py - off;
        x.fillStyle = `hsl(${hue},${sat}%,${lum}%)`; x.fillRect(X, Y, pw, L);
        x.save(); x.beginPath(); x.rect(X + 2, Y, pw - 4, L); x.clip();
        for (let k = 0; k < 34; k++) {
          const gx = X + R() * pw, ph = R() * 6, amp = 2 + R() * 6;
          x.strokeStyle = R() < .6 ? `rgba(40,20,8,${.12 + R() * .2})` : `rgba(255,220,170,${.05 + R() * .06})`; x.lineWidth = .8 + R() * 1.6;
          x.beginPath(); for (let t = 0; t <= 1.001; t += .05) { const yy = Y + t * L; const xx = gx + Math.sin(t * 6 + ph) * amp; t === 0 ? x.moveTo(xx, yy) : x.lineTo(xx, yy); } x.stroke();
        }
        if (R() < .5) { const kx = X + pw * (.25 + R() * .5), ky = Y + L * (.2 + R() * .6); for (let q = 0; q < 5; q++) { x.strokeStyle = `rgba(45,22,8,${.5 - q * .08})`; x.lineWidth = 1.5; x.beginPath(); x.ellipse(kx, ky, 5 + q * 4, 10 + q * 9, 0, 0, 7); x.stroke(); } }
        x.restore();
        y.fillStyle = `hsl(0,0%,${62 + R() * 18}%)`; y.fillRect(X + 3, Y + 2, pw - 6, L - 4);
        x.fillStyle = 'rgba(10,5,2,.9)'; x.fillRect(X, Y, 3, L); x.fillRect(X, Y, pw, 3);
        // çivi
        x.fillStyle = '#1a1410'; for (const dx of [.25, .75]) { x.beginPath(); x.arc(X + pw * dx, Y + 14, 3.5, 0, 7); x.fill(); }
      }
      py += L;
    }
  }
  noise(x, S, S, 14, R);
  return { map: tex(c, true, rep), bump: tex(blurred(b, 1.5), false, rep) };
}

// ---------- mühendislik planı arka planı (yazı yok) ----------
export function blueprint(seed = 2, base = '#0a2150') {
  const S = 2048, R = rng(seed), c = cv(S, S), x = c.getContext('2d');
  const g = x.createRadialGradient(S / 2, S * .45, 100, S / 2, S / 2, S * .75); g.addColorStop(0, '#12306a'); g.addColorStop(1, base);
  x.fillStyle = g; x.fillRect(0, 0, S, S);
  const line = (a, w, x0, y0, x1, y1) => { x.strokeStyle = `rgba(160,210,255,${a})`; x.lineWidth = w; x.beginPath(); x.moveTo(x0, y0); x.lineTo(x1, y1); x.stroke(); };
  for (let i = 0; i <= S; i += 32) { line(.12, 1.2, i, 0, i, S); line(.12, 1.2, 0, i, S, i); }
  for (let i = 0; i <= S; i += 256) { line(.3, 2, i, 0, i, S); line(.3, 2, 0, i, S, i); }
  const arrow = (x0, y0, x1, y1) => {
    line(.55, 2, x0, y0, x1, y1); const a = Math.atan2(y1 - y0, x1 - x0);
    for (const [px, py, d] of [[x0, y0, 1], [x1, y1, -1]]) {
      x.fillStyle = 'rgba(170,215,255,.6)'; x.beginPath(); x.moveTo(px, py);
      x.lineTo(px + d * 22 * Math.cos(a) - 7 * Math.sin(a), py + d * 22 * Math.sin(a) + 7 * Math.cos(a));
      x.lineTo(px + d * 22 * Math.cos(a) + 7 * Math.sin(a), py + d * 22 * Math.sin(a) - 7 * Math.cos(a)); x.fill();
      const nx = -Math.sin(a), ny = Math.cos(a); line(.55, 2, px - nx * 18, py - ny * 18, px + nx * 18, py + ny * 18);
    }
  };
  for (let k = 0; k < 9; k++) {
    const t = R();
    if (t < .4) { const yy = 120 + R() * (S - 240), x0 = R() * S * .6; arrow(x0, yy, x0 + 250 + R() * 600, yy); }
    else if (t < .7) { const xx = 120 + R() * (S - 240), y0 = R() * S * .6; arrow(xx, y0, xx, y0 + 250 + R() * 500); }
    else { const cx = R() * S, cy = R() * S, r = 60 + R() * 160; x.strokeStyle = 'rgba(160,210,255,.4)'; x.lineWidth = 2; x.beginPath(); x.arc(cx, cy, r, 0, 7); x.stroke(); x.setLineDash([16, 10]); line(.35, 1.5, cx - r * 1.4, cy, cx + r * 1.4, cy); line(.35, 1.5, cx, cy - r * 1.4, cx, cy + r * 1.4); x.setLineDash([]); }
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

export function radialTex(inner = 'rgba(0,0,0,1)', outer = 'rgba(0,0,0,0)') {
  const c = cv(256, 256), x = c.getContext('2d'), g = x.createRadialGradient(128, 128, 0, 128, 128, 128);
  g.addColorStop(0, inner); g.addColorStop(1, outer); x.fillStyle = g; x.fillRect(0, 0, 256, 256);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

// ---------- manken ----------
export const GOLD = '#ffb347';
const shadowed = m => { m.castShadow = true; m.receiveShadow = true; return m; };
export function mesh(geo, mat, parent, x = 0, y = 0, z = 0) { const m = shadowed(new THREE.Mesh(geo, mat)); m.position.set(x, y, z); parent.add(m); return m; }
function grp(parent, x = 0, y = 0, z = 0) { const g = new THREE.Group(); g.position.set(x, y, z); parent.add(g); return g; }
const cap = (r, len) => new THREE.CapsuleGeometry(r, Math.max(.001, len), 10, 20);
// bel ince, göğüs geniş gövde profili (yerel y: 0 → .64)
const TORSO = [[0, 0], [.1, .005], [.145, .04], [.152, .1], [.165, .2], [.19, .32], [.205, .42], [.2, .5], [.175, .57], [.12, .615], [.05, .635], [0, .64]];
function torsoGeo(k = 1, dy = 0) { return new THREE.LatheGeometry(TORSO.map(([r, y]) => new THREE.Vector2(r * k, y * (1 + (k - 1) * .5) + dy)), 40); }
const sph = (r) => new THREE.SphereGeometry(r, 32, 16);

export function mannequin(opt = {}) {
  const body = new THREE.MeshStandardMaterial({ color: opt.body || '#d3ccc2', roughness: .62, metalness: 0 });
  const gold = new THREE.MeshStandardMaterial({ color: GOLD, roughness: .38, metalness: .3, emissive: '#3a1e00', emissiveIntensity: .25 });
  const root = new THREE.Group(), M = { root, body, gold };
  const pelvis = M.pelvis = grp(root, 0, .95, 0);
  mesh(sph(.2), body, pelvis).scale.set(1.12, .72, .82);
  const spine = M.spine = grp(pelvis, 0, .07, 0);
  mesh(sph(.085), gold, spine);
  mesh(torsoGeo(1), body, spine, 0, -.02, 0).scale.set(1.12, 1, .72);
  const neck = M.neck = grp(spine, 0, .6, 0); mesh(sph(.06), gold, neck);
  const head = M.head = grp(neck, 0, .05, 0); mesh(sph(.2), body, head, 0, .17, 0).scale.set(.94, 1.04, .96);
  const arm = (sx) => {
    const sh = grp(spine, sx * .3, .5, 0); mesh(sph(.075), gold, sh);
    mesh(cap(.068, .3 - .136 - .03), body, sh, 0, -.15, 0);
    const el = grp(sh, 0, -.31, 0); mesh(sph(.06), gold, el);
    mesh(cap(.058, .27 - .116 - .03), body, el, 0, -.14, 0);
    const wr = grp(el, 0, -.29, 0); mesh(sph(.045), gold, wr);
    const hand = mesh(sph(.072), body, wr, 0, -.07, 0); hand.scale.set(.8, 1.05, .6);
    return { sh, el, wr, hand };
  };
  const leg = (sx) => {
    const hip = grp(pelvis, sx * .12, -.08, 0); mesh(sph(.08), gold, hip);
    mesh(cap(.085, .38 - .17 - .04), body, hip, 0, -.19, 0);
    const kn = grp(hip, 0, -.38, 0); mesh(sph(.07), gold, kn);
    mesh(cap(.07, .38 - .14 - .04), body, kn, 0, -.19, 0);
    const an = grp(kn, 0, -.38, 0); mesh(sph(.055), gold, an);
    const foot = mesh(cap(.058, .12), body, an, 0, -.052, .05); foot.rotation.x = Math.PI / 2; foot.scale.set(1.05, 1, .85);
    const sole = grp(an, 0, -.11, .05); const toe = grp(an, 0, -.11, .16); const heel = grp(an, 0, -.11, -.06);
    return { hip, kn, an, foot, sole, toe, heel };
  };
  M.L = arm(-1); M.R = arm(1); M.LL = leg(-1); M.RL = leg(1);
  return M;
}

// poz: {spine:[x,y,z], neck:[..], L:{sh:[..],el:[..]}, ...}
export function pose(M, p) {
  const set = (o, v) => v && o.rotation.set(v[0] || 0, v[1] || 0, v[2] || 0);
  set(M.spine, p.spine); set(M.neck, p.neck); set(M.pelvis, p.pelvis);
  for (const k of ['L', 'R']) if (p[k]) { set(M[k].sh, p[k].sh); set(M[k].el, p[k].el); set(M[k].wr, p[k].wr); }
  for (const k of ['LL', 'RL']) if (p[k]) { set(M[k].hip, p[k].hip); set(M[k].kn, p[k].kn); set(M[k].an, p[k].an); }
}
// en alçaktaki ayak noktası zemine (y=0) değsin
export function ground(M) {
  M.root.updateMatrixWorld(true); let min = Infinity; const v = new THREE.Vector3();
  for (const k of ['LL', 'RL']) for (const o of [M[k].toe, M[k].heel, M[k].sole]) { o.getWorldPosition(v); min = Math.min(min, v.y); }
  M.root.position.y -= min; M.root.updateMatrixWorld(true);
}

// ---------- kıyafet parçaları ----------
const std = (color, rough = .8, metal = 0) => new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: metal });
function sleeve(parent, r, len, y, mat, flare = 1.06) { // açık uçlu kısa tüp
  const m = mesh(new THREE.CylinderGeometry(r, r * flare, len, 24, 1, true), mat, parent, 0, y, 0);
  m.material.side = THREE.DoubleSide; return m;
}
function torsoShell(M, mat, k = 1.08) {
  const t = mesh(torsoGeo(k), mat, M.spine, 0, -.035, 0); t.scale.set(1.12, 1, .74); return t;
}
function hipShell(M, mat, k = 1.1) { const h = mesh(sph(.2 * k), mat, M.pelvis, 0, 0, 0); h.scale.set(1.12, .78, .84); return h; }

export function outfitPrisoner(M) {
  const cloth = std('#857664', .95), dark = std('#5f5446', .95), iron = std('#3b3f45', .45, .8), rope = std('#a08a62', .9);
  torsoShell(M, cloth, 1.09);
  for (const s of ['L', 'R']) sleeve(M[s].sh, .085, .17, -.08, cloth);
  hipShell(M, dark);
  for (const s of ['LL', 'RL']) sleeve(M[s].hip, .105, .2, -.1, dark, 1.0);
  const belt = mesh(new THREE.TorusGeometry(.215, .018, 8, 40), rope, M.pelvis, 0, .07, 0); belt.rotation.x = Math.PI / 2; belt.scale.set(1.12, .82, 1);
  // ayak kelepçesi
  M.shackles = [];
  for (const s of ['LL', 'RL']) { const t = mesh(new THREE.TorusGeometry(.068, .018, 10, 28), iron, M[s].an, 0, .03, 0); t.rotation.x = Math.PI / 2; M.shackles.push(t); }
  // bilek kelepçesi
  for (const s of ['L', 'R']) { const t = mesh(new THREE.TorusGeometry(.058, .015, 10, 24), iron, M[s].wr, 0, -.02, 0); t.rotation.x = Math.PI / 2; }
  M.iron = iron;
}
// iki dünya noktası arasında sarkan zincir (sahneye eklenir)
export function chain(scene, a, b, sag, mat, n = 9) {
  const g = new THREE.Group(); scene.add(g);
  const geo = new THREE.TorusGeometry(.03, .009, 8, 16);
  for (let i = 0; i <= n; i++) {
    const t = i / n, p = new THREE.Vector3().lerpVectors(a, b, t); p.y -= Math.sin(t * Math.PI) * sag;
    const m = mesh(geo, mat, g); m.position.copy(p); m.scale.set(1, 1.5, 1);
    const d = new THREE.Vector3().subVectors(b, a).normalize(); m.lookAt(p.clone().add(d)); m.rotateY(Math.PI / 2); if (i % 2) m.rotateX(Math.PI / 2);
  }
  return g;
}

export function outfitGuard(M) {
  const jacket = std('#4a3a2e', .85), tabard = std('#8a2f22', .9), leather = std('#5a3b22', .7), metal = std('#2a3038', .35, .85), steel = std('#c9d2db', .25, .9);
  torsoShell(M, jacket, 1.08);
  // önde/arkada kısa tabard
  for (const z of [1, -1]) { const t = mesh(new THREE.BoxGeometry(.2, .62, .016), tabard, M.spine, 0, .1, z * .172); t.rotation.x = z * -.08; }
  for (const s of ['L', 'R']) { sleeve(M[s].sh, .084, .26, -.13, jacket); sleeve(M[s].el, .07, .12, -.2, leather, 1.12); }
  hipShell(M, jacket);
  for (const s of ['LL', 'RL']) { sleeve(M[s].hip, .1, .3, -.15, jacket, .95); sleeve(M[s].kn, .085, .22, -.25, leather, 1.0); const boot = mesh(cap(.068, .12), leather, M[s].an, 0, -.05, .05); boot.rotation.x = Math.PI / 2; boot.scale.set(1.12, 1.05, .95); }
  const belt = mesh(new THREE.TorusGeometry(.215, .028, 10, 40), leather, M.pelvis, 0, .06, 0); belt.rotation.x = Math.PI / 2; belt.scale.set(1.12, .84, 1.4);
  mesh(new THREE.BoxGeometry(.08, .07, .03), std('#b8893f', .4, .7), M.pelvis, 0, .06, .185);
  // kask: yarım küre + KISA siper (yüzü örtmesin) + ince sırt
  const helm = mesh(new THREE.SphereGeometry(.212, 32, 16, 0, Math.PI * 2, 0, Math.PI * .5), metal, M.head, 0, .23, 0); helm.scale.set(.97, .95, 1.0);
  const brim = mesh(new THREE.CylinderGeometry(.205, .245, .035, 40, 1, true), metal, M.head, 0, .225, 0); brim.material = metal.clone(); brim.material.side = THREE.DoubleSide;
  const lip = mesh(new THREE.TorusGeometry(.245, .01, 6, 48), metal, M.head, 0, .207, 0); lip.rotation.x = Math.PI / 2;
  mesh(new THREE.BoxGeometry(.02, .045, .3), metal, M.head, 0, .43, 0);
  // yüz dolgu ışığı (yalnız kafa çevresi)
  const fill = new THREE.PointLight('#ffd9a8', .28, .6, 2); fill.position.set(0, .16, .42); M.head.add(fill);
  // elde kılıç: geniş siper, kısa kabza, sivri ağız
  const sw = grp(M.R.wr, 0, -.075, 0); sw.rotation.set(.32, 0, .22); M.sword = sw;
  const bs = new THREE.Shape(); bs.moveTo(-.034, 0); bs.lineTo(.034, 0); bs.lineTo(.028, -.6); bs.lineTo(0, -.7); bs.lineTo(-.028, -.6); bs.closePath();
  const bg = new THREE.ExtrudeGeometry(bs, { depth: .006, bevelEnabled: true, bevelThickness: .005, bevelSize: .006, bevelSegments: 1 }); bg.translate(0, 0, -.003);
  mesh(bg, steel, sw, 0, -.1, 0);
  const fuller = new THREE.MeshStandardMaterial({ color: '#6c7178', roughness: .4, metalness: .8 });
  for (const z of [.0095, -.0095]) mesh(new THREE.BoxGeometry(.012, .46, .002), fuller, sw, 0, -.36, z);
  const cg = std('#b8893f', .35, .75);
  mesh(new THREE.BoxGeometry(.3, .032, .05), cg, sw, 0, -.085, 0);
  for (const sx of [-1, 1]) mesh(sph(.024), cg, sw, sx * .155, -.085, 0);
  mesh(new THREE.CylinderGeometry(.019, .021, .13, 12), std('#3a2414', .8), sw, 0, -.005, 0);
  mesh(sph(.032), cg, sw, 0, .075, 0);
  // bel: boş kın (sol kalça)
  const scab = grp(M.pelvis, -.2, -.02, .02); scab.rotation.set(.2, 0, -.45);
  mesh(new THREE.BoxGeometry(.07, .62, .03), leather, scab, 0, -.3, 0);
  mesh(new THREE.BoxGeometry(.075, .05, .035), cg, scab, 0, -.6, 0);
  // göğüs kayışı
  const strap = mesh(new THREE.TorusGeometry(.25, .014, 6, 40), leather, M.spine, 0, .3, 0); strap.rotation.set(Math.PI / 2, -0.62, 0); strap.scale.set(.95, .72, 1);
}

export function outfitWorker(M, opt = {}) {
  const shirt = std('#5f6442', .9), apron = std('#f2e4c6', .85), pants = std('#6a4d33', .9), leather = std('#4a3020', .7), glass = new THREE.MeshStandardMaterial({ color: '#7fd0ff', roughness: .1, metalness: .3, emissive: '#1a4060', emissiveIntensity: .4 }), brass = std('#c9963f', .35, .8);
  torsoShell(M, shirt, 1.07);
  for (const s of ['L', 'R']) sleeve(M[s].sh, .083, .24, -.12, shirt);
  hipShell(M, pants, 1.08);
  for (const s of ['LL', 'RL']) { sleeve(M[s].hip, .1, .34, -.17, pants, .95); sleeve(M[s].kn, .085, .2, -.12, pants, .98); }
  // önlük: bib + etek
  const ap2 = apron.clone(); ap2.side = THREE.DoubleSide;
  const bib = mesh(new THREE.CylinderGeometry(.205, .19, .3, 24, 1, true, -.62, 1.24), ap2, M.spine, 0, .3, 0); bib.scale.set(1.14, 1, .84);
  const skirt = mesh(new THREE.CylinderGeometry(.235, .3, .56, 28, 1, true, -.85, 1.7), ap2, M.pelvis, 0, -.15, 0); skirt.scale.set(1.12, 1, .95);
  const tie = mesh(new THREE.TorusGeometry(.22, .012, 6, 40), apron, M.pelvis, 0, .1, 0); tie.rotation.x = Math.PI / 2; tie.scale.set(1.12, .86, 1);
  for (const sx of [-1, 1]) { const st = mesh(new THREE.CylinderGeometry(.01, .01, .3, 6), apron, M.spine, sx * .12, .55, .09); st.rotation.x = -.55; st.rotation.z = sx * -.2; }
  mesh(new THREE.BoxGeometry(.09, .07, .012), std('#c9b48e', .9), M.spine, .06, .25, .183);
  // eldiven
  for (const s of ['L', 'R']) M[s].hand.material = leather;
  // şapka (kasket) + alın gözlüğü
  const hat = mesh(sph(.215), std('#6a5a48', .95), M.head, 0, .3, .01); hat.scale.set(1.0, .42, 1.08);
  const visor = mesh(new THREE.CylinderGeometry(.15, .15, .014, 32, 1, false, -Math.PI / 2, Math.PI), std('#4a3e32', .95), M.head, 0, .29, .12); visor.scale.set(1, 1, .75); visor.rotation.x = .12;
  const band = mesh(new THREE.TorusGeometry(.198, .014, 8, 40), leather, M.head, 0, .24, 0); band.rotation.x = Math.PI / 2 - .12;
  for (const sx of [-1, 1]) {
    const lens = mesh(new THREE.CylinderGeometry(.055, .055, .05, 24), brass, M.head, sx * .075, .25, .175); lens.rotation.x = Math.PI / 2 - .25;
    const gl = mesh(new THREE.CylinderGeometry(.042, .042, .01, 24), glass, M.head, sx * .075, .256, .202); gl.rotation.x = Math.PI / 2 - .25;
  }
}

export function hammer(parent, s = 1) {
  const g = grp(parent);
  mesh(new THREE.CylinderGeometry(.02 * s, .024 * s, .38 * s, 12), std('#8a5a32', .7), g, 0, 0, 0);
  mesh(new THREE.BoxGeometry(.17 * s, .065 * s, .065 * s), std('#5d646d', .35, .85), g, .02 * s, .19 * s, 0);
  return g;
}
export function gear(parent, r = .2, teeth = 12, th = .05, mat) {
  const g = grp(parent); mat = mat || std('#b98a3c', .35, .8);
  mesh(new THREE.CylinderGeometry(r, r, th, 40), mat, g);
  for (let i = 0; i < teeth; i++) { const a = i / teeth * Math.PI * 2; const t = mesh(new THREE.BoxGeometry(r * .28, th, r * .22), mat, g, Math.cos(a) * (r + r * .1), 0, Math.sin(a) * (r + r * .1)); t.rotation.y = -a; }
  mesh(new THREE.CylinderGeometry(r * .3, r * .3, th * 1.6, 24), std('#6b5a40', .5, .6), g);
  return g;
}
export function barrel(parent, h = .9, r = .34) {
  const g = grp(parent); const pts = [];
  for (let i = 0; i <= 16; i++) { const t = i / 16; pts.push(new THREE.Vector2(r * (0.82 + 0.18 * Math.sin(t * Math.PI)), t * h)); }
  const wood = std('#7a4e2a', .8); mesh(new THREE.LatheGeometry(pts, 40), wood, g);
  const lid = mesh(new THREE.CircleGeometry(r * .82, 40), std('#6a4224', .85), g, 0, h - .005, 0); lid.rotation.x = -Math.PI / 2;
  for (const t of [.12, .36, .64, .88]) { const rr = r * (0.82 + 0.18 * Math.sin(t * Math.PI)) + .006; const hoop = mesh(new THREE.TorusGeometry(rr, .012, 8, 48), std('#33373c', .4, .8), g, 0, t * h, 0); hoop.rotation.x = Math.PI / 2; }
  return g;
}

// ölçü çizgisi süsü (ince açık mavi, uçlarda çentik)
export function dimLine(scene, a, b, color = '#e9c98f', w = .006, tick = .07) {
  const g = new THREE.Group(); scene.add(g);
  const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: .5, fog: false, depthWrite: false });
  const d = new THREE.Vector3().subVectors(b, a), L = d.length();
  const bar = new THREE.Mesh(new THREE.BoxGeometry(w, L, w), mat); bar.position.copy(a).addScaledVector(d, .5);
  bar.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.clone().normalize()); g.add(bar);
  const perp = new THREE.Vector3(0, 1, 0).cross(d).normalize(); if (perp.lengthSq() < .1) perp.set(1, 0, 0);
  for (const p of [a, b]) {
    const t = new THREE.Mesh(new THREE.BoxGeometry(w, tick * 2, w), mat); t.position.copy(p);
    t.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), perp); g.add(t);
    const cone = new THREE.Mesh(new THREE.ConeGeometry(.022, .07, 12), mat); const dir = (p === a ? d.clone().negate() : d.clone()).normalize();
    cone.position.copy(p).addScaledVector(dir, -.035); cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir); g.add(cone);
  }
  return g;
}

export function blob(scene, x, z, r = .55, op = .45) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(r * 2, r * 2), new THREE.MeshBasicMaterial({ map: radialTex('rgba(0,0,0,1)', 'rgba(0,0,0,0)'), transparent: true, opacity: op, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }));
  m.rotation.x = -Math.PI / 2; m.position.set(x, .004, z); scene.add(m); return m;
}
export function glowSprite(scene, pos, color, size) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: radialTex(color, 'rgba(0,0,0,0)'), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
  s.position.copy(pos); s.scale.set(size, size, 1); scene.add(s); return s;
}
// uzak zemin ızgarası + arka plan planı
export function planVoid(scene, { back = -9, gridY = -.02 } = {}) {
  const bt = blueprint(); bt.wrapS = bt.wrapT = THREE.RepeatWrapping; bt.repeat.set(2.5, 2.5);
  const bp = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshBasicMaterial({ map: bt, fog: false, color: '#e0e8ff' }));
  bp.position.set(0, 8, back); scene.add(bp);
  const gh = new THREE.GridHelper(60, 120, '#5f9de8', '#2c5aa0'); gh.position.y = gridY; gh.material.transparent = true; gh.material.opacity = .55; scene.add(gh);
  return { bp, gh };
}

// ================= SICAK PALET YARDIMCILARI =================
// sahte hacimli huzme: açık uçlu koni, kenarlar fresnel ile yumuşar, uçlarda söner, içinde hafif dalgalı pus
const BEAM_VS = `varying vec3 vN; varying vec3 vV; varying float vT; varying vec3 vW;
void main(){ vT = uv.y; vec4 mv = modelViewMatrix * vec4(position, 1.0); vV = -mv.xyz; vN = normalize(normalMatrix * normal);
 vW = (modelMatrix * vec4(position, 1.0)).xyz; gl_Position = projectionMatrix * mv; }`;
const BEAM_FS = `uniform vec3 uC; uniform float uI, uP, uBot, uTop, uEnd, uN, uFloor, uWall, uWallF;
varying vec3 vN; varying vec3 vV; varying float vT; varying vec3 vW;
float h(vec3 p){ return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
float vn(vec3 p){ vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
 return mix(mix(mix(h(i), h(i + vec3(1,0,0)), f.x), mix(h(i + vec3(0,1,0)), h(i + vec3(1,1,0)), f.x), f.y),
            mix(mix(h(i + vec3(0,0,1)), h(i + vec3(1,0,1)), f.x), mix(h(i + vec3(0,1,1)), h(i + vec3(1,1,1)), f.x), f.y), f.z); }
void main(){
 float f = abs(dot(normalize(vN), normalize(vV)));
 float edge = pow(f, uP);
 float along = smoothstep(0.0, uBot, vT) * smoothstep(1.0, 1.0 - uTop, vT) * mix(uEnd, 1.0, vT);
 float n = vn(vW * 2.2) * 0.6 + vn(vW * 5.0 + 3.1) * 0.4;
 float clipF = smoothstep(0.0, uFloor, vW.y) * smoothstep(uWall, uWall + uWallF, vW.z);
 vec3 col = uC * uI * edge * along * clipF * mix(1.0, 0.45 + n, uN);
 gl_FragColor = vec4(col, 1.0);
 #include <tonemapping_fragment>
 #include <colorspace_fragment>
}`;
export function beam(scene, a, b, r0, r1, color, I = .2, o = {}) {
  const d = new THREE.Vector3().subVectors(b, a), L = d.length();
  const geo = new THREE.CylinderGeometry(r0, r1, L, 64, 1, true);
  const mat = new THREE.ShaderMaterial({ vertexShader: BEAM_VS, fragmentShader: BEAM_FS, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
    uniforms: { uC: { value: new THREE.Color(color) }, uI: { value: I }, uP: { value: o.pow ?? 2.2 }, uBot: { value: o.bot ?? .35 }, uTop: { value: o.top ?? .08 }, uEnd: { value: o.end ?? .5 }, uN: { value: o.noise ?? .6 }, uFloor: { value: o.floor ?? .7 }, uWall: { value: o.wall ?? -100 }, uWallF: { value: o.wallF ?? .4 } } });
  const m = new THREE.Mesh(geo, mat); m.position.copy(a).addScaledVector(d, .5);
  m.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), d.clone().normalize());
  if (o.sx || o.sz) m.scale.set(o.sx || 1, 1, o.sz || 1);
  m.renderOrder = 5; scene.add(m); return m;
}
// birkaç iç içe katman = yumuşak çekirdek + geniş hale
export function softBeam(scene, a, b, r0, r1, color, I = .2, o = {}) {
  return [[1, 1, 1, 1], [1.12, 1.45, .45, 1.7], [1.25, 2.0, .22, 2.6]].map(([k0, k1, ii, p]) => beam(scene, a, b, r0 * k0, r1 * k1, color, I * ii, { top: .22, ...o, pow: (o.pow ?? 2.2) * p }));
}
// bulut/pus dokusu
let _cloud;
export function cloudTex() {
  if (_cloud) return _cloud;
  const S = 512, R = rng(77), c = cv(S, S), x = c.getContext('2d');
  for (let i = 0; i < 90; i++) {
    const px = S / 2 + (R() - .5) * S * .55, py = S / 2 + (R() - .5) * S * .4, r = 40 + R() * 110;
    const g = x.createRadialGradient(px, py, 0, px, py, r); g.addColorStop(0, `rgba(255,255,255,${.05 + R() * .08})`); g.addColorStop(1, 'rgba(255,255,255,0)');
    x.fillStyle = g; x.fillRect(0, 0, S, S);
  }
  const m = cv(S, S), y = m.getContext('2d'); const g = y.createRadialGradient(S / 2, S / 2, S * .1, S / 2, S / 2, S * .5);
  g.addColorStop(0, '#fff'); g.addColorStop(1, 'rgba(255,255,255,0)'); y.fillStyle = g; y.fillRect(0, 0, S, S);
  x.globalCompositeOperation = 'destination-in'; x.drawImage(m, 0, 0);
  _cloud = new THREE.CanvasTexture(c); _cloud.colorSpace = THREE.SRGBColorSpace; return _cloud;
}
export function haze(scene, items) { // items: [[x,y,z,w,h,color,opacity]]
  for (const [x, y, z, w, h, color, op] of items) {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: cloudTex(), color, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, fog: false }));
    s.position.set(x, y, z); s.scale.set(w, h, 1); s.renderOrder = 4; scene.add(s);
  }
}
// huzme içinde toz zerrecikleri
export function motes(scene, a, b, r0, r1, n = 160, color = '#ffe2b0', seed = 5, size = .022) {
  const R = rng(seed), pos = [], d = new THREE.Vector3().subVectors(b, a);
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, -1, 0), d.clone().normalize());
  for (let i = 0; i < n; i++) { const t = .1 + R() * .8, rr = (r0 + (r1 - r0) * t) * Math.sqrt(R()) * .9, an = R() * 6.283;
    const v = new THREE.Vector3(Math.cos(an) * rr, 0, Math.sin(an) * rr).applyQuaternion(q).add(a.clone().addScaledVector(d, t)); pos.push(v.x, v.y, v.z); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  const p = new THREE.Points(g, new THREE.PointsMaterial({ color, size, map: radialTex('rgba(255,255,255,1)', 'rgba(255,255,255,0)'), transparent: true, opacity: .8, blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true }));
  scene.add(p); return p;
}
// gün batımı / alacakaranlık gökyüzü (pencere dışı)
export function skyTex(seed = 3) {
  const W = 512, H = 512, R = rng(seed), c = cv(W, H), x = c.getContext('2d');
  const g = x.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, '#2b2440'); g.addColorStop(.35, '#6b3f4e'); g.addColorStop(.62, '#d9693a'); g.addColorStop(.8, '#ffb35c'); g.addColorStop(1, '#ffd890');
  x.fillStyle = g; x.fillRect(0, 0, W, H);
  const sg = x.createRadialGradient(W * .62, H * .86, 4, W * .62, H * .86, W * .45); sg.addColorStop(0, 'rgba(255,240,190,.95)'); sg.addColorStop(.2, 'rgba(255,190,110,.5)'); sg.addColorStop(1, 'rgba(255,150,80,0)');
  x.fillStyle = sg; x.fillRect(0, 0, W, H);
  for (let i = 0; i < 9; i++) { const y = H * (.2 + R() * .5), w = W * (.3 + R() * .5), x0 = R() * W - w * .3; x.fillStyle = `rgba(${120 + R() * 60},${60 + R() * 40},${70 + R() * 30},${.25 + R() * .25})`; x.beginPath(); x.ellipse(x0 + w / 2, y, w / 2, 4 + R() * 7, 0, 0, 7); x.fill(); }
  // uzak çatı/tepe silueti
  x.fillStyle = '#2a1a1c'; x.beginPath(); x.moveTo(0, H); for (let px = 0; px <= W; px += 16) x.lineTo(px, H * .9 - Math.sin(px * .02 + 1) * 10 - (R() < .2 ? 18 : 0)); x.lineTo(W, H); x.fill();
  const t = new THREE.CanvasTexture(blurred(c, 1.2)); t.colorSpace = THREE.SRGBColorSpace; return t;
}
// zemindeki kir/leke katmanı (tekrarı kırar)
export function grime(scene, w, d, x, z, seed = 9, op = .55) {
  const S = 1024, R = rng(seed), c = cv(S, S), g = c.getContext('2d');
  for (let i = 0; i < 160; i++) { const px = R() * S, py = R() * S, r = 20 + R() * 120, a = R() * .22;
    const gr = g.createRadialGradient(px, py, 0, px, py, r); gr.addColorStop(0, `rgba(255,255,255,${a})`); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, S, S); }
  const t = new THREE.CanvasTexture(c);
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), new THREE.MeshBasicMaterial({ color: '#0a0604', alphaMap: t, transparent: true, opacity: op, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -1 }));
  m.rotation.x = -Math.PI / 2; m.position.set(x, .002, z); scene.add(m); return m;
}
// sıcak ortam yansıması (metaller koyu görünmesin)
export function warmEnv(renderer, scene, k = .45) {
  const es = new THREE.Scene(); es.background = new THREE.Color('#1c1511');
  const pan = (c, x, y, z, w, h, ry = 0, rx = 0) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: c, side: THREE.DoubleSide })); m.position.set(x, y, z); m.rotation.set(rx, ry, 0); es.add(m); };
  pan('#ffcf96', 0, 6, 0, 8, 8, 0, Math.PI / 2); pan('#ff9b3d', -6, 2, 0, 5, 3, Math.PI / 2); pan('#6f86b8', 6, 3, 0, 2, 2, -Math.PI / 2); pan('#3a2a20', 0, -4, 0, 20, 20, 0, Math.PI / 2);
  const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(es, .04).texture; scene.environmentIntensity = k;
}
// altın/krem çizim masası çizgileri (çok soluk; mavi yok)
export function draftLines(scene, x0, x1, y0, y1, z, step = .5, op = .07) {
  const pts = [];
  for (let x = x0; x <= x1 + 1e-6; x += step) pts.push(x, y0, z, x, y1, z);
  for (let y = y0; y <= y1 + 1e-6; y += step) pts.push(x0, y, z, x1, y, z);
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
  const l = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: '#e9c98f', transparent: true, opacity: op, depthWrite: false })); scene.add(l); return l;
}
