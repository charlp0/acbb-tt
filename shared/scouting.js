/* ACBB TT — fiche de scouting d'une équipe adverse (module partagé).

   Produit les blocs « niveau, compo récente, meilleur joueur, joueurs récurrents, résultats »
   à partir des feuilles de rencontre FFTT (data/site.json). Utilisé par la page Poules de la
   sportive (fiche adversaire) et par Compos journée (popup au clic sur l'adversaire), pour que
   les deux affichent exactement la même chose.

   Le niveau d'une équipe est la moyenne des points des joueurs qu'elle a RÉELLEMENT alignés sur
   les journées déjà jouées (J1 → aujourd'hui), jamais le repère de la saison passée.
   Les points d'un joueur numéroté sont ses vrais points ; son n° national s'affiche en badge.

   API : ACBB_SCOUT.css() une fois, puis ACBB_SCOUT.html({site, poule, team, acbbTeam}). */
(function () {
  var esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };
  var norm = function (s) {
    return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '')
      .toUpperCase().replace(/[^A-Z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim();
  };
  /* « BOULOGNE BILLAN 11 » ≈ « BOULOGNE BILLANCOURT 11 » : même premier mot et même numéro d'équipe */
  function sameTeam(a, b) {
    a = norm(a); b = norm(b);
    if (!a || !b) return false;
    if (a === b) return true;
    var na = a.match(/(\d+)$/), nb = b.match(/(\d+)$/);
    if (!na || !nb || na[1] !== nb[1]) return false;
    var fa = a.split(' ')[0], fb = b.split(' ')[0];
    return fa === fb || fa.indexOf(fb) === 0 || fb.indexOf(fa) === 0;
  }
  var reels = function (ps) { return (ps || []).filter(function (p) { return p && p.nom && p.nom !== 'Joueur absent'; }); };
  var nom = function (p) { return ((p.prenom || '') + ' ' + (p.nom || '')).trim(); };
  /* points affichés : ceux du joueur ; un numéroté porte en plus son n° national */
  function pts(p) {
    var v = (p.cls == null || p.cls === 'x') ? '—' : p.cls;
    return esc(String(v)) + (p.num ? ' <span class="sc-n" title="joueur numéroté : ' + esc(p.num) + 'ᵉ français">N' + esc(p.num) + '</span>' : '');
  }
  /* points de rencontre FFTT (28 – 14, total 42) -> parties gagnées (14 – 0), l'unité du club */
  function parties(a, b) {
    a = +a; b = +b;
    if (!isFinite(a) || !isFinite(b)) return null;
    return (a + b === 42 && a >= 14 && b >= 14) ? [a - 14, b - 14] : [a, b];
  }
  function jouees(t) {
    return ((t && t.journees) || []).filter(function (j) { return j.match_score != null && j.opp_score != null; })
      .sort(function (x, y) { return (+x.journee) - (+y.journee); });
  }
  /* niveau = moyenne des points de tous les joueurs alignés sur les journées déjà jouées */
  function niveau(js) {
    var n = [];
    (js || []).forEach(function (j) { reels(j.players).forEach(function (p) { if (typeof p.cls === 'number') n.push(p.cls); }); });
    return n.length ? Math.round(n.reduce(function (a, b) { return a + b; }, 0) / n.length) : null;
  }
  function effectif(js) {
    var st = {};
    (js || []).forEach(function (j) {
      reels(j.players).forEach(function (p) {
        var k = (p.nom + '|' + (p.prenom || '')).toUpperCase();
        if (!st[k]) st[k] = { nom: p.nom, prenom: p.prenom || '', cls: p.cls, num: p.num || null, count: 0, vic: 0 };
        if (typeof p.cls === 'number' && (typeof st[k].cls !== 'number' || p.cls > st[k].cls)) st[k].cls = p.cls;
        if (p.num) st[k].num = p.num;
        st[k].count++; st[k].vic += (p.vic || 0);
      });
    });
    return Object.keys(st).map(function (k) { return st[k]; })
      .sort(function (a, b) { return b.count - a.count || b.vic - a.vic; });
  }
  function difficulte(avg, pos) {
    var top = pos != null && pos <= 3;
    if (avg == null) return top ? { cls: 'lose', label: 'Très difficile' } : null;
    if (avg >= 1300 || top) return { cls: 'lose', label: 'Très difficile' };
    if (avg >= 1100) return { cls: 'warn', label: 'Difficile' };
    if (avg >= 900) return { cls: '', label: 'Moyenne' };
    return { cls: 'win', label: 'Accessible' };
  }
  /* équipe adverse dans site.json + moyenne de la poule hors ACBB */
  function contexte(site, poule, team) {
    var D = site && site.DATA && poule ? site.DATA[poule.acbb] : null;
    if (!D) return { js: [], poule: null, rang: null };
    var cible = null, vals = [];
    (D.teams || []).forEach(function (t) {
      var js = jouees(t), n = niveau(js);
      if (sameTeam(t.name, team && team.name)) cible = { t: t, js: js, n: n };
      if (n != null && !t.acbb) vals.push(n);
    });
    var st = site.STANDINGS && site.STANDINGS[poule.acbb];
    var rg = Array.isArray(st) ? st.filter(function (r) { return sameTeam(r.name, team && team.name); })[0] : null;
    return {
      js: cible ? cible.js : [],
      niveau: cible ? cible.n : null,
      poule: vals.length ? Math.round(vals.reduce(function (a, b) { return a + b; }, 0) / vals.length) : null,
      rang: rg && (+rg.mp || 0) > 0 ? rg : null,
      nbPoule: Array.isArray(st) ? st.length : null
    };
  }

  function css() {
    if (document.getElementById('sc-css')) return;
    var st = document.createElement('style'); st.id = 'sc-css';
    st.textContent = [
      '.sc-h{font-family:"JetBrains Mono",monospace;font-size:9.5px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;color:var(--dim);margin:16px 0 6px;display:flex;align-items:center;gap:8px}',
      '.sc-h .n{color:var(--dimmer)}',
      '.sc-row{display:flex;justify-content:space-between;gap:10px;padding:7px 0;border-top:1px solid rgba(255,255,255,.06);font-size:12.5px}',
      '.sc-row .num{font-family:"JetBrains Mono",monospace;font-weight:700;white-space:nowrap}',
      '.sc-n{font-family:"JetBrains Mono",monospace;font-size:9.5px;font-weight:800;padding:1px 5px;border-radius:99px;background:rgba(250,204,21,.14);border:1px solid rgba(250,204,21,.45);color:var(--gold)}',
      '.sc-chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}',
      '.sc-chip{font-family:"JetBrains Mono",monospace;font-size:10.5px;padding:4px 9px;border-radius:99px;background:var(--panel-2);border:1px solid var(--line-2);color:var(--ink-2)}',
      '.sc-chip b{color:var(--ink)}',
      '.sc-tag{font-family:"JetBrains Mono",monospace;font-size:10px;font-weight:800;padding:3px 9px;border-radius:99px;border:1px solid var(--line-2);color:var(--ink-2)}',
      '.sc-tag.lose{color:var(--lose);border-color:rgba(242,99,86,.5)}.sc-tag.warn{color:var(--warn);border-color:rgba(250,204,21,.5)}.sc-tag.win{color:var(--win);border-color:rgba(61,214,140,.5)}',
      '.sc-top{background:var(--panel-2);border:1px solid rgba(61,214,140,.35);border-radius:10px;padding:9px 11px;font-size:12.5px;margin-top:6px}',
      '.sc-line{font-size:12.5px;line-height:1.5;color:var(--ink-2);margin-top:6px}',
      '.sc-line .sep{color:var(--dimmer)}',
      '.sc-empty{font-size:12px;color:var(--dim);padding:6px 0}',
      '.sc-sc{font-family:"JetBrains Mono",monospace;font-weight:800}',
      '.sc-sc.win{color:var(--win)}.sc-sc.lose{color:var(--lose)}.sc-sc.draw{color:var(--warn)}'
    ].join('');
    document.head.appendChild(st);
  }

  /* HTML des blocs de scouting. opts : {site, poule, team, acbbTeam} */
  function html(opts) {
    opts = opts || {};
    var c = contexte(opts.site, opts.poule, opts.team);
    var js = c.js, out = '';
    var scCls = function (a, b) { return a > b ? 'win' : (a < b ? 'lose' : 'draw'); };

    var chips = [];
    if (c.rang) chips.push('<span class="sc-chip" title="place au classement"><b>' + esc(c.rang.pos) + '</b>' + (c.nbPoule ? '/' + c.nbPoule : '') + '</span>',
      '<span class="sc-chip"><b>' + esc(c.rang.pts) + '</b> pts</span>');
    if (c.niveau != null) chips.push('<span class="sc-chip" title="classement moyen des joueurs alignés sur les journées déjà jouées">⌀ <b>' + c.niveau + '</b></span>');
    if (c.poule != null) chips.push('<span class="sc-chip" title="moyenne de la poule sans l\'ACBB">poule <b>' + c.poule + '</b></span>');
    if (js.length) {
      var sm = js.map(function (j) { var p = parties(j.match_score, j.opp_score); return p ? p[0] : null; }).filter(function (x) { return x != null; });
      if (sm.length) chips.push('<span class="sc-chip" title="parties gagnées en moyenne par rencontre">score moy. <b>' + (sm.reduce(function (a, b) { return a + b; }, 0) / sm.length).toFixed(1).replace('.', ',') + '</b></span>');
    }
    var d = difficulte(c.niveau, c.rang ? +c.rang.pos : null);
    if (d) chips.push('<span class="sc-tag ' + d.cls + '" title="estimation : niveau réel de l\'adversaire et place au classement">' + d.label + '</span>');
    if (chips.length) out += '<div class="sc-chips">' + chips.join('') + '</div>';

    if (!js.length) return out + '<div class="sc-empty">Pas encore de feuille de match 26/27 pour cette équipe.</div>';

    var last = js[js.length - 1];
    var pr = parties(last.match_score, last.opp_score);
    out += '<div class="sc-h">Compo récente</div>';
    out += '<div class="sc-line">J' + esc(last.journee) + ' · ' + esc(last.date || '') + ' · <b class="sc-sc ' + scCls(pr[0], pr[1]) + '">' + pr[0] + ' – ' + pr[1] + '</b> vs ' + esc(last.opponent || '') + '<br>'
      + reels(last.players).map(function (p) { return esc(nom(p)) + ' <span class="sc-chip">' + pts(p) + '</span>'; }).join(' ') + '</div>';

    var eff = effectif(js);
    var top = eff.slice().sort(function (a, b) { return b.vic - a.vic; })[0];
    if (top && top.vic > 0) {
      out += '<div class="sc-h">Meilleur joueur</div>';
      out += '<div class="sc-top"><b>' + esc(nom(top)) + '</b> · ' + pts(top) + ' · <b>' + top.vic + ' victoire' + (top.vic > 1 ? 's' : '') + '</b> en ' + top.count + ' feuille' + (top.count > 1 ? 's' : '') + '</div>';
    }
    var rec = eff.filter(function (p) { return p.count >= 2; });
    if (rec.length) {
      out += '<div class="sc-h">Joueurs récurrents <span class="n">' + rec.length + '</span></div>';
      out += rec.map(function (p) {
        return '<div class="sc-row"><span>' + esc(nom(p)) + '</span><span class="num">' + pts(p) + ' · ' + p.count + ' feuilles' + (p.vic ? ' · ' + p.vic + 'V' : '') + '</span></div>';
      }).join('');
    }
    out += '<div class="sc-h">Résultats 26/27 · journée par journée</div>';
    out += js.map(function (j) {
      var p = parties(j.match_score, j.opp_score);
      var nous = opts.acbbTeam && sameTeam(j.opponent, opts.acbbTeam.name);
      return '<div class="sc-row"><span>J' + esc(j.journee) + ' <span class="sep">' + esc(j.date || '') + '</span> ' + esc(j.opponent || '') + (nous ? ' <span class="sc-chip">nous</span>' : '') + '</span>'
        + '<span class="num sc-sc ' + scCls(p[0], p[1]) + '">' + p[0] + ' – ' + p[1] + '</span></div>';
    }).join('');
    return out;
  }

  window.ACBB_SCOUT = { css: css, html: html, sameTeam: sameTeam, niveau: niveau, jouees: jouees, parties: parties };
})();
