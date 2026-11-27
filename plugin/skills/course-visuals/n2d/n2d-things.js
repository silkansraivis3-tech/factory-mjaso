/* The things a figure is drawn from: each a flat pictogram in a 100 x 100 box, in its tone.
   A figure never draws a named rectangle: a spec names a thing ("is": "firewall") and gets its picture.
   A thing the library does not have is made here once, then every course can name it. */
(function () {
  var N = '#0A2463', W = '#FFFFFF', S = '#5B6B85', G = '#DCE3EC', A = '#E9A51E', LED = '#2FD08A', RED = '#D23B2B';

  function pale(hex, k) {
    k = k == null ? 0.82 : k;
    var n = parseInt(hex.slice(1), 16), r = n >> 16, g = (n >> 8) & 255, b = n & 255;
    r = Math.round(r + (255 - r) * k); g = Math.round(g + (255 - g) * k); b = Math.round(b + (255 - b) * k);
    return 'rgb(' + r + ',' + g + ',' + b + ')';
  }
  function rect(x, y, w, h, f, rx, extra) { return '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '"' + (rx ? ' rx="' + rx + '"' : '') + ' fill="' + f + '"' + (extra || '') + '/>'; }
  function circ(cx, cy, r, f, extra) { return '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="' + f + '"' + (extra || '') + '/>'; }
  function path(d, f, extra) { return '<path d="' + d + '" fill="' + (f || 'none') + '"' + (extra || '') + '/>'; }
  function line(d, s, w, extra) { return '<path d="' + d + '" fill="none" stroke="' + s + '" stroke-width="' + w + '" stroke-linecap="round" stroke-linejoin="round"' + (extra || '') + '/>'; }
  function arcs(cx, cy, rs, from, to, s, w) {
    return rs.map(function (r) {
      var a1 = from * Math.PI / 180, a2 = to * Math.PI / 180;
      return line('M' + (cx + r * Math.cos(a1)).toFixed(1) + ' ' + (cy + r * Math.sin(a1)).toFixed(1) + ' A' + r + ' ' + r + ' 0 0 1 ' + (cx + r * Math.cos(a2)).toFixed(1) + ' ' + (cy + r * Math.sin(a2)).toFixed(1), s, w);
    }).join('');
  }
  function monitor(x, y, w, h, inner) {
    return rect(x, y, w, h, N, 6) + rect(x + 5, y + 5, w - 10, h - 10, inner, 3) +
      rect(x + w / 2 - 6, y + h, 12, 9, S) + rect(x + w / 2 - 20, y + h + 9, 40, 6, N, 3);
  }
  function person(t, head) {
    return path('M22 96 V76 a28 26 0 0 1 56 0 V96 Z', t) + circ(50, 30, 17, head || N) + path('M38 52 l12 14 l12 -14', 'none', ' stroke="' + W + '" stroke-width="3" opacity=".7"');
  }

  var T = {
    sensor: function (t, p) {
      return line('M50 12 C50 2 70 2 74 12 C78 22 90 20 92 12', N, 4) +
        rect(32, 12, 36, 22, t, 5) + rect(32, 12, 36, 7, N, 4, ' opacity=".22"') +
        path('M38 34 h24 l-3 10 h-18 z', N) +
        path('M43 44 h14 v38 q0 10 -7 14 q-7 -4 -7 -14 z', S) +
        line('M43 56h14 M43 64h14 M43 72h14', W, 2, ' opacity=".55"') +
        arcs(50, 86, [20, 30], 200, 340, t, 4);
    },
    controller: function (t, p) {
      var s = '';
      for (var i = 0; i < 7; i++) { s += rect(19 + i * 9.5, 12, 6, 9, S, 1) + rect(19 + i * 9.5, 79, 6, 9, S, 1); }
      return s + rect(14, 20, 72, 60, t, 7) + rect(14, 20, 72, 11, N, 6, ' opacity=".22"') +
        rect(22, 39, 34, 26, W, 3) + line('M27 58 l7 -8 l7 5 l9 -11', t, 3.5) +
        circ(68, 42, 4.5, LED) + circ(68, 54, 4.5, A) + circ(68, 66, 4.5, LED);
    },
    screen: function (t, p) {
      return monitor(8, 12, 84, 58, p) + line('M18 54 L30 46 L40 50 L52 34 L62 42 L74 30', t, 4.5) +
        path('M68 58 l9 -16 l9 16 z', A) + rect(76, 47, 2, 6, N) + rect(76, 55, 2, 2, N);
    },
    pc: function (t, p) {
      return monitor(4, 16, 66, 48, p) + line('M14 50 h30 M14 40 h40 M14 30 h22', t, 4) +
        rect(74, 20, 22, 66, t, 4) + rect(78, 28, 14, 4, W, 1, ' opacity=".8"') + circ(85, 74, 3.5, LED);
    },
    laptop: function (t, p) {
      return path('M22 18 h56 a5 5 0 0 1 5 5 v41 h-66 v-41 a5 5 0 0 1 5 -5 z', N) + rect(23, 23, 54, 37, p, 2) +
        line('M30 50 h26 M30 40 h36 M30 31 h18', t, 4) + path('M6 66 h88 l-8 12 h-72 z', S) + rect(42, 66, 16, 3, G, 1);
    },
    server: function (t, p) {
      var s = '';
      [12, 39, 66].forEach(function (y) {
        s += rect(18, y, 64, 23, t, 4) + rect(18, y, 64, 6, N, 3, ' opacity=".2"') +
          line('M26 ' + (y + 14) + ' h28', W, 3, ' opacity=".7"') + circ(68, y + 13, 3.5, LED) + circ(76, y + 13, 3.5, LED);
      });
      return s;
    },
    switch: function (t, p) {
      var s = rect(4, 30, 92, 40, t, 6) + rect(4, 30, 92, 8, N, 5, ' opacity=".2"');
      for (var i = 0; i < 8; i++) { s += rect(10 + i * 10.6, 48, 8, 11, W, 1.5) + circ(14 + i * 10.6, 42, 2.4, LED); }
      return s;
    },
    router: function (t, p) {
      return line('M30 52 L22 14 M70 52 L78 14', N, 5) + circ(22, 14, 4, N) + circ(78, 14, 4, N) +
        rect(12, 50, 76, 30, t, 7) + rect(12, 50, 76, 8, N, 6, ' opacity=".2"') +
        circ(26, 68, 3.5, LED) + circ(36, 68, 3.5, LED) + circ(46, 68, 3.5, A) + line('M60 68 h18', W, 3, ' opacity=".7"');
    },
    firewall: function (t, p) {
      var B = '#C2493A', s = path('M50 4 C62 16 66 24 60 34 C70 30 72 22 70 16 C80 26 80 40 70 46 H30 C20 40 22 26 32 18 C32 26 36 30 40 32 C34 20 40 12 50 4 Z', A) +
        path('M50 22 C56 30 58 36 54 42 H44 C40 36 44 28 50 22 Z', '#FFD34D');
      [[46, 0], [62, 1], [78, 0]].forEach(function (r) {
        for (var i = 0; i < 4; i++) { var x = 8 + i * 22 - (r[1] ? 11 : 0); var w = 20; if (x < 8) { w -= 8 - x; x = 8; } if (x + w > 92) w = 92 - x; s += rect(x, r[0], w, 14, B, 2); }
      });
      return s;
    },
    wifi: function (t, p) {
      return arcs(50, 58, [12, 24, 36], 220, 320, t, 7) + circ(50, 58, 6, t) + path('M18 76 h64 a8 8 0 0 1 0 14 h-64 a8 8 0 0 1 0 -14 z', N) + circ(50, 83, 3, LED);
    },
    vsat: function (t, p) {
      return arcs(66, 22, [10, 20], 260, 350, t, 5) + path('M24 62 a26 26 0 0 1 52 0 z', W, ' stroke="' + N + '" stroke-width="4"') +
        line('M36 46 q14 -10 28 0', G, 3) + rect(42, 62, 16, 22, S) + rect(28, 84, 44, 8, N, 3);
    },
    satellite: function (t, p) {
      var s = rect(4, 40, 30, 20, t, 2) + rect(66, 40, 30, 20, t, 2) + line('M14 40v20 M24 40v20 M76 40v20 M86 40v20', W, 2, ' opacity=".6"') +
        line('M34 50 h8 M58 50 h8', N, 4) + rect(40, 34, 20, 32, S, 4) + path('M42 72 q8 14 16 0 z', G, ' stroke="' + N + '" stroke-width="3"');
      return s;
    },
    constellation: function (t, p) {
      function sat(x, y, k) { return '<g transform="translate(' + x + ' ' + y + ') scale(' + k + ')">' + rect(-22, -6, 14, 12, t, 1) + rect(8, -6, 14, 12, t, 1) + rect(-7, -9, 14, 18, S, 3) + '</g>'; }
      return arcs(50, 160, [120], 235, 305, G, 3) + sat(22, 52, 0.9) + sat(52, 40, 0.9) + sat(82, 52, 0.9) + path('M0 96 Q50 74 100 96 Z', pale('#1F78C8', 0.6));
    },
    mast: function (t, p) {
      return line('M50 14 L34 94 M50 14 L66 94 M38 74 L62 74 M41 56 L59 56 M44 38 L56 38 M38 74 L59 56 M41 56 L56 38', N, 4) +
        rect(44, 18, 4, 16, t) + rect(52, 18, 4, 16, t) + arcs(50, 24, [14, 24], 200, 250, t, 5) + arcs(50, 24, [14, 24], 290, 340, t, 5);
    },
    office: function (t, p) {
      var s = rect(30, 14, 52, 80, t, 3) + rect(8, 46, 24, 48, S, 2);
      for (var r = 0; r < 5; r++) for (var c = 0; c < 3; c++) s += rect(37 + c * 15, 22 + r * 13, 9, 8, W, 1, ' opacity=".85"');
      return s + rect(12, 54, 6, 6, W, 1, ' opacity=".6"') + rect(22, 54, 6, 6, W, 1, ' opacity=".6"') + rect(50, 82, 12, 12, N, 1);
    },
    globe: function (t, p) {
      return circ(50, 50, 40, t) + '<ellipse cx="50" cy="50" rx="17" ry="40" fill="none" stroke="' + W + '" stroke-width="3" opacity=".8"/>' +
        line('M10 50 h80 M16 30 h68 M16 70 h68', W, 3, ' opacity=".8"');
    },
    malware: function (t, p) {
      return line('M30 44 L14 36 M30 58 L12 58 M32 72 L16 82 M70 44 L86 36 M70 58 L88 58 M68 72 L84 82 M42 22 L36 10 M58 22 L64 10', N, 4) +
        '<ellipse cx="50" cy="60" rx="22" ry="28" fill="' + RED + '"/>' + circ(50, 28, 13, N) + line('M50 36 V86', N, 3, ' opacity=".5"') + circ(44, 26, 3, W) + circ(56, 26, 3, W);
    },
    engine: function (t, p) {
      var s = '';
      for (var i = 0; i < 4; i++) s += rect(16 + i * 14, 20, 11, 16, S, 2);
      return s + rect(10, 34, 64, 44, t, 5) + rect(10, 34, 64, 8, N, 4, ' opacity=".2"') + line('M18 54 h48 M18 64 h48', W, 3, ' opacity=".5"') +
        circ(82, 60, 15, N) + circ(82, 60, 6, G) + rect(6, 78, 90, 8, N, 2);
    },
    gnss: function (t, p) {
      return line('M28 26 L46 52 M50 18 L50 50 M72 26 L54 52', t, 3, ' stroke-dasharray="4 5"') + circ(26, 22, 6, t) + circ(50, 14, 6, t) + circ(74, 22, 6, t) +
        path('M28 66 a22 14 0 0 1 44 0 z', W, ' stroke="' + N + '" stroke-width="4"') + rect(46, 66, 8, 22, S) + rect(36, 88, 28, 6, N, 3);
    },
    gyro: function (t, p) {
      var s = circ(50, 50, 42, N) + circ(50, 50, 36, W) + circ(50, 50, 26, p);
      for (var a = 0; a < 360; a += 30) { var r = a * Math.PI / 180; s += line('M' + (50 + 30 * Math.sin(r)).toFixed(1) + ' ' + (50 - 30 * Math.cos(r)).toFixed(1) + ' L' + (50 + 35 * Math.sin(r)).toFixed(1) + ' ' + (50 - 35 * Math.cos(r)).toFixed(1), N, 2.5); }
      return s + path('M50 16 L58 50 L50 46 L42 50 Z', t) + path('M50 84 L58 50 L50 54 L42 50 Z', S) + circ(50, 50, 4, N);
    },
    radar: function (t, p) {
      return circ(50, 50, 44, N) + circ(50, 50, 38, '#0E2A47') + '<circle cx="50" cy="50" r="25" fill="none" stroke="' + t + '" stroke-width="1.5" opacity=".6"/><circle cx="50" cy="50" r="12" fill="none" stroke="' + t + '" stroke-width="1.5" opacity=".6"/>' +
        path('M50 50 L50 12 A38 38 0 0 1 83 31 Z', t, ' opacity=".45"') + line('M50 50 L83 31', t, 2.5) + circ(64, 34, 4, A) + circ(30, 64, 3.5, A) + circ(70, 66, 3, A);
    },
    ais: function (t, p) {
      return arcs(50, 30, [12, 22], 220, 320, t, 4.5) + rect(16, 34, 68, 50, N, 6) + rect(22, 40, 56, 38, p, 3) +
        path('M50 46 L58 70 L50 64 L42 70 Z', t) + circ(34, 52, 3, S) + circ(68, 60, 3, S);
    },
    ecdis: function (t, p) {
      return monitor(6, 12, 88, 60, '#CFE8F7') + path('M11 17 h30 q6 12 -2 22 q-10 10 -4 24 h-24 z', '#EAD9A6') +
        line('M44 62 L58 44 L80 30', RED, 3.5, ' stroke-dasharray="6 5"') + circ(58, 44, 3.5, RED) + path('M44 56 l5 8 l-10 0 z', N);
    },
    conning: function (t, p) {
      return monitor(6, 12, 88, 60, p) + arcs(50, 60, [26], 200, 340, N, 3) + line('M50 60 L64 40', t, 5) + circ(50, 60, 4, N) +
        '<text x="50" y="30" text-anchor="middle" font-size="12" font-weight="800" fill="' + N + '">045°</text>';
    },
    socket: function (t, p) {
      return rect(20, 14, 60, 72, W, 9, ' stroke="' + N + '" stroke-width="4"') + path('M36 38 h28 v20 h-6 v6 h-16 v-6 h-6 z', N) + circ(50, 24, 2.5, S) + circ(50, 76, 2.5, S);
    },
    person: function (t) { return person(t); },
    manager: function (t) { return person(t) + rect(58, 62, 18, 24, W, 2, ' stroke="' + N + '" stroke-width="2.5"') + line('M62 70 h10 M62 76 h10', S, 2); },
    sponsor: function (t) { return person(t) + path('M50 56 l5 6 l-5 20 l-5 -20 z', A); },
    attendant: function (t) { return person(t) + rect(64, 58, 12, 22, N, 3) + line('M72 58 V42', N, 3) + circ(70, 66, 2.5, LED); },
    permit: function (t, p) {
      return rect(18, 12, 64, 82, '#9A6B3C', 7) + rect(24, 22, 52, 66, W, 2) + rect(38, 6, 24, 12, N, 4) +
        line('M32 34 h36 M32 44 h28 M32 54 h32', G, 4) + line('M44 70 l7 8 l16 -18', '#12805A', 6);
    },
    padlock: function (t, p) {
      return line('M34 46 V32 a16 16 0 0 1 32 0 V46', N, 9) + rect(22, 44, 56, 44, t, 8) + circ(50, 62, 6, N) + rect(47, 64, 6, 12, N, 2) +
        line('M78 60 L88 74', S, 3) + rect(80, 72, 14, 20, RED, 2);
    },
    fan: function (t, p) {
      return circ(50, 50, 44, N) + circ(50, 50, 38, W) + '<g class="n2-spin">' +
        [0, 120, 240].map(function (a) { return '<path transform="rotate(' + a + ' 50 50)" d="M50 50 C44 34 46 18 56 14 C64 22 60 38 50 50 Z" fill="' + t + '"/>'; }).join('') + '</g>' + circ(50, 50, 7, N);
    },
    detector: function (t, p) {
      return rect(26, 8, 48, 86, '#F2B705', 12) + rect(32, 14, 36, 8, N, 3, ' opacity=".35"') + rect(32, 28, 36, 28, '#163A2A', 4) +
        '<text x="50" y="47" text-anchor="middle" font-size="13" font-weight="800" fill="' + LED + '">O₂ 21</text>' +
        circ(40, 70, 5, N) + circ(60, 70, 5, N) + rect(40, 82, 20, 5, N, 2, ' opacity=".4"');
    },
    manhole: function (t, p) {
      return '<ellipse cx="50" cy="56" rx="44" ry="22" fill="' + S + '"/><ellipse cx="50" cy="56" rx="34" ry="15" fill="' + N + '"/>' +
        line('M38 44 V96 M62 44 V96 M38 58 h24 M38 72 h24 M38 86 h24', A, 4) + '<ellipse cx="50" cy="56" rx="44" ry="22" fill="none" stroke="' + N + '" stroke-width="3"/>';
    },
    document: function (t, p) {
      return path('M22 8 h40 l18 18 v66 h-58 z', W, ' stroke="' + N + '" stroke-width="4" stroke-linejoin="round"') + path('M62 8 v18 h18', 'none', ' stroke="' + N + '" stroke-width="4"') +
        line('M32 40 h36 M32 52 h36 M32 64 h26 M32 76 h30', t, 4);
    },
    change: function (t, p) {
      return T.document(t, p) + path('M58 86 L86 44 L94 50 L66 92 L56 94 Z', A) + path('M86 44 L94 50', 'none', ' stroke="' + N + '" stroke-width="3"');
    },
    plan: function (t, p) {
      return rect(10, 14, 80, 72, W, 5, ' stroke="' + N + '" stroke-width="4"') + rect(18, 26, 30, 9, t, 2) + rect(36, 42, 34, 9, t, 2) + rect(54, 58, 28, 9, A, 2) + line('M18 76 h64', G, 3);
    },
    calendar: function (t, p) {
      var s = rect(10, 16, 80, 74, W, 6, ' stroke="' + N + '" stroke-width="4"') + rect(10, 16, 80, 18, t, 6) + rect(26, 8, 6, 16, N, 2) + rect(68, 8, 6, 16, N, 2);
      for (var r = 0; r < 3; r++) for (var c = 0; c < 4; c++) s += rect(18 + c * 17, 42 + r * 15, 12, 10, r === 1 && c === 2 ? A : G, 2);
      return s;
    },
    check: function () { return circ(50, 50, 42, '#12805A') + line('M30 52 l13 14 l27 -30', W, 9); },
    tester: function (t, p) {
      var s = rect(14, 22, 72, 56, t, 8) + rect(22, 32, 56, 20, N, 3);
      for (var i = 0; i < 8; i++) s += circ(28 + i * 6.3, 42, 2.4, i === 5 ? RED : LED);
      return s + '<text x="50" y="70" text-anchor="middle" font-size="11" font-weight="800" fill="' + W + '">1 2 3 4 5 6 7 8</text>' + line('M14 50 H4 M86 50 H96', N, 5);
    },
    cable: function (t, p) {
      return line('M18 30 C40 0 60 100 82 70', t, 7) + rect(6, 20, 18, 16, W, 2, ' stroke="' + N + '" stroke-width="3"') + rect(76, 64, 18, 16, W, 2, ' stroke="' + N + '" stroke-width="3"');
    },
    pump: function (t, p) {
      return rect(56, 14, 16, 26, S, 2) + rect(52, 10, 24, 6, N, 2) + circ(48, 56, 34, t) + circ(48, 56, 20, W) +
        '<g class="n2-spin">' + [0, 60, 120, 180, 240, 300].map(function (a) { return '<path transform="rotate(' + a + ' 48 56)" d="M48 56 Q54 46 48 38" fill="none" stroke="' + N + '" stroke-width="4" stroke-linecap="round"/>'; }).join('') + '</g>' + circ(48, 56, 5, N);
    },
    valve: function (t, p) {
      return line('M50 46 V18', N, 5) + '<ellipse cx="50" cy="16" rx="24" ry="7" fill="none" stroke="' + RED + '" stroke-width="6"/>' +
        path('M10 34 L50 56 L10 78 Z', t) + path('M90 34 L50 56 L90 78 Z', t) + circ(50, 56, 7, N);
    },
    tank: function (t, p) {
      return rect(20, 10, 60, 82, W, 6, ' stroke="' + N + '" stroke-width="4"') + rect(22, 46, 56, 44, t, 3) + line('M22 46 h56', N, 2, ' opacity=".4"');
    },
    ship: function (t, p) {
      return path('M50 6 C64 22 68 40 68 60 V92 H32 V60 C32 40 36 22 50 6 Z', t) + rect(38, 62, 24, 20, W, 3) + rect(40, 64, 20, 5, N, 1, ' opacity=".5"');
    },
    barometer: function (t, p) {
      var s = circ(50, 50, 44, '#9A6B3C') + circ(50, 50, 36, W);
      for (var a = -120; a <= 120; a += 20) { var r = a * Math.PI / 180; s += line('M' + (50 + 28 * Math.sin(r)).toFixed(1) + ' ' + (50 - 28 * Math.cos(r)).toFixed(1) + ' L' + (50 + 34 * Math.sin(r)).toFixed(1) + ' ' + (50 - 34 * Math.cos(r)).toFixed(1), N, 2); }
      return s + line('M50 50 L30 34', t, 4) + circ(50, 50, 4, N);
    },
    wind: function (t, p) { return line('M8 36 H62 a12 12 0 1 0 -12 -12 M8 54 H80 a12 12 0 1 1 -12 12 M8 72 H50', t, 7); },
    question: function (t, p) { return circ(50, 50, 42, t) + '<text x="50" y="66" text-anchor="middle" font-size="48" font-weight="800" fill="#fff">?</text>'; }
  };

  var ALIAS = {
    probe: 'sensor', 'temperature sensor': 'sensor', plc: 'controller', 'local controller': 'controller', panel: 'controller',
    monitor: 'screen', display: 'screen', 'alarm system': 'screen', ams: 'screen', workstation: 'pc', computer: 'pc', 'office pc': 'pc',
    'access point': 'wifi', 'wi-fi': 'wifi', 'crew wifi': 'wifi', dome: 'vsat', antenna: 'vsat', 'sat dish': 'vsat',
    geo: 'satellite', leo: 'constellation', 'mobile mast': 'mast', 'cell tower': 'mast', shore: 'office', company: 'office', maker: 'office',
    internet: 'globe', virus: 'malware', ransomware: 'malware', 'main engine': 'engine', gps: 'gnss', 'gyro compass': 'gyro', arpa: 'radar',
    chart: 'ecdis', 'wall socket': 'socket', crew: 'person', officer: 'person', pm: 'manager', 'project manager': 'manager',
    lock: 'padlock', lockout: 'padlock', isolate: 'padlock', ventilation: 'fan', blower: 'fan', 'gas detector': 'detector', 'gas meter': 'detector',
    entry: 'manhole', hatch: 'manhole', report: 'document', paper: 'document', 'change request': 'change', schedule: 'plan',
    'cable tester': 'tester', 'patch cable': 'cable', 'hand radio': 'attendant', standby: 'attendant'
  };

  function find(is) {
    var k = String(is || '').toLowerCase().trim();
    if (T[k]) return k;
    if (ALIAS[k]) return ALIAS[k];
    return null;
  }

  window.N2THINGS = {
    draw: function (is, tone) { var k = find(is) || 'question'; return T[k](tone, pale(tone)); },
    has: function (is) { return !!find(is); },
    find: find,
    list: function () { return Object.keys(T).filter(function (k) { return k !== 'question'; }); },
    pale: pale
  };
})();
