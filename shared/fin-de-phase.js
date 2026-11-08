/* Fin de phase : pendant JavaScript exact de scripts/fin_de_phase.py (mêmes modèles, même départage),
 * pour rejouer la simulation dans le navigateur avec un scénario de renfort. Toute modification d'un
 * côté se reporte de l'autre ; tests/fin-de-phase.test.js et tests/test_fin_de_phase.py partagent la
 * même valeur de contrôle (espérance de simples sur un alignement fixé). */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api; else root.ACBB_FDP=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const PTS={V:3,N:2,D:1};
  // Ordre des simples, règlement IDF art. 2 : AW BX CY DZ AX BW DY CZ · doubles · AY CW DX BZ.
  const SINGLES=[[0,0],[1,1],[2,2],[3,3],[0,1],[1,0],[3,2],[2,3],[0,2],[2,0],[3,1],[1,3]];
  const sigmoid=(d,s)=>1/(1+Math.pow(10,-d/s));
  const force=p=>p.cls+(p.adj||0);
  const result=(wa,wb)=>wa>wb?'V':wa<wb?'D':'N';

  /* Générateur déterministe (mulberry32) : un scénario rejoué donne les mêmes chiffres. */
  function rng(seed){
    let a=seed>>>0;
    return function(){ a=(a+0x6D2B79F5)>>>0; let t=a; t=Math.imul(t^(t>>>15),t|1); t^=t+Math.imul(t^(t>>>7),t|61); return ((t^(t>>>14))>>>0)/4294967296; };
  }

  function expectedSingles(la,lb,s){
    const sa=la.map(force), sb=lb.map(force); let tot=0;
    SINGLES.forEach(([i,j])=>{ if(i>=sa.length) return; if(j>=sb.length){tot+=1;return;} tot+=sigmoid(sa[i]-sb[j],s); });
    return tot;
  }

  function simMatchB(la,lb,s,rnd){
    const sa=la.map(force), sb=lb.map(force); let wa=0, wb=0;
    SINGLES.forEach(([i,j])=>{
      if(i>=sa.length&&j>=sb.length) return;
      if(i>=sa.length){wb++;return;} if(j>=sb.length){wa++;return;}
      if(rnd()<sigmoid(sa[i]-sb[j],s)) wa++; else wb++;
    });
    const ma=sa.reduce((x,y)=>x+y,0)/sa.length, mb=sb.reduce((x,y)=>x+y,0)/sb.length, pd=sigmoid(ma-mb,s);
    for(let d=0;d<2;d++){
      if(d===1&&(sa.length<4||sb.length<4)){ if(sa.length<4&&sb.length<4) continue; if(sa.length<4) wb++; else wa++; continue; }
      if(rnd()<pd) wa++; else wb++;
    }
    return [wa,wb];
  }
  function simMatchA(ra,rb,s,rnd){ const p=sigmoid(ra-rb,s); let wa=0; for(let i=0;i<14;i++) if(rnd()<p) wa++; return [wa,14-wa]; }

  function lineupShift(lineup,lineups){
    if(!lineup||!lineups||!lineups.length) return 0;
    const avg=l=>l.reduce((x,p)=>x+force(p),0)/l.length;
    return avg(lineup)-lineups.reduce((x,l)=>x+avg(l),0)/lineups.length;
  }

  /* Classement art. 14 : points, puis points entre ex æquo, puis écart de parties entre eux, puis écart total. */
  function rankTeams(teams,pts,mini,diff){
    const order=teams.slice().sort((a,b)=>pts[b]-pts[a]);
    const out=[]; let i=0;
    while(i<order.length){
      const group=[order[i]]; while(i+group.length<order.length&&pts[order[i+group.length]]===pts[order[i]]) group.push(order[i+group.length]);
      if(group.length===1) out.push(group[0]);
      else {
        const sp={}, sd={};
        group.forEach(t=>{ sp[t]=0; sd[t]=0; group.forEach(u=>{ if(u!==t&&mini[t][u]){ sp[t]+=mini[t][u][0]; sd[t]+=mini[t][u][1]; } }); });
        group.sort((a,b)=>(sp[b]-sp[a])||(sd[b]-sd[a])||(diff[b]-diff[a])||(a<b?-1:a>b?1:0));
        group.forEach(t=>out.push(t));
      }
      i+=group.length;
    }
    return out;
  }

  function goalReached(pos,n,quota,objectif){ return objectif==='montee'?(pos<=quota.up?1:0):(pos<=n-quota.down-quota.risk?1:0); }

  function descentProbability(dist,n,quota){
    let down=quota.down?dist.slice(n-quota.down).reduce((x,y)=>x+y,0):0;
    if(quota.risk) down+=quota.frac*dist[n-quota.down-1];
    return down;
  }

  /* T = entrée data/fin_de_phase.json d'une équipe (teams[key]). opts.override(j, teamName, lineup, rnd) peut
     renvoyer un alignement modifié (scénario de renfort) ; opts.objectif remplace l'objectif ; opts.nsim, opts.seed. */
  function simulate(T,opts){
    opts=opts||{}; const nsim=opts.nsim||4000, rnd=rng(opts.seed||2026), s=opts.s, mix=opts.mix==null?0.5:opts.mix;
    const teams=T.teams.map(t=>t.name), n=teams.length, acbb=T.acbb, objectif=opts.objectif||T.objectif, quota=opts.quota||T.quota;
    const byName={}; T.teams.forEach(t=>byName[t.name]=t);
    const basePts={}, baseDiff={}, baseMini={};
    teams.forEach(t=>{basePts[t]=0;baseDiff[t]=0;baseMini[t]={};});
    T.played.forEach(m=>{
      const ra=result(m.wa,m.wb), rb=result(m.wb,m.wa);
      basePts[m.a]+=PTS[ra]; basePts[m.b]+=PTS[rb]; baseDiff[m.a]+=m.wa-m.wb; baseDiff[m.b]+=m.wb-m.wa;
      baseMini[m.a][m.b]=[PTS[ra],m.wa-m.wb]; baseMini[m.b][m.a]=[PTS[rb],m.wb-m.wa];
    });
    (T.standings||[]).forEach(row=>{ if(row.pts!=null&&basePts[row.name]!=null) basePts[row.name]=+row.pts; });
    const rankCount={}; teams.forEach(t=>rankCount[t]=new Array(n).fill(0));
    const matchOut=T.remaining.map(()=>({V:0,N:0,D:0,A:{V:0,N:0,D:0},B:{V:0,N:0,D:0}}));
    const cond=T.remaining.map(()=>({V:[0,0],N:[0,0],D:[0,0]}));
    let goalHits=0;
    for(let it=0;it<nsim;it++){
      const pts=Object.assign({},basePts), diff=Object.assign({},baseDiff), mini={}; teams.forEach(t=>mini[t]=Object.assign({},baseMini[t]));
      const results=[];
      T.remaining.forEach((m,idx)=>{
        const useA=rnd()<mix;
        const La=byName[m.a].lineups, Lb=byName[m.b].lineups;
        let la=La.length?La[Math.floor(rnd()*La.length)]:null, lb=Lb.length?Lb[Math.floor(rnd()*Lb.length)]:null;
        if(opts.override){ la=opts.override(m.j,m.a,la,rnd)||la; lb=opts.override(m.j,m.b,lb,rnd)||lb; }
        let wa,wb,model;
        if(useA||!la||!lb){
          const ra=byName[m.a].rating+(la?lineupShift(la,La):0), rb=byName[m.b].rating+(lb?lineupShift(lb,Lb):0);
          [wa,wb]=simMatchA(ra,rb,s,rnd); model='A';
        } else { [wa,wb]=simMatchB(la,lb,s,rnd); model='B'; }
        const ra=result(wa,wb), rb=result(wb,wa);
        matchOut[idx][ra]++; matchOut[idx][model][ra]++;
        pts[m.a]+=PTS[ra]; pts[m.b]+=PTS[rb]; diff[m.a]+=wa-wb; diff[m.b]+=wb-wa;
        mini[m.a][m.b]=[PTS[ra],wa-wb]; mini[m.b][m.a]=[PTS[rb],wb-wa];
        results.push(ra);
      });
      const ranking=rankTeams(teams,pts,mini,diff);
      ranking.forEach((t,pos)=>rankCount[t][pos]++);
      if(acbb){
        const hit=goalReached(ranking.indexOf(acbb)+1,n,quota,objectif); goalHits+=hit;
        results.forEach((r,idx)=>{cond[idx][r][0]+=hit;cond[idx][r][1]++;});
      }
    }
    const out={nsim,objectif,teams:{},remaining:[],pObjectif:acbb?goalHits/nsim:null};
    teams.forEach(t=>{ const dist=rankCount[t].map(c=>c/nsim); out.teams[t]={ranks:dist,pUp:quota.up?dist.slice(0,quota.up).reduce((x,y)=>x+y,0):0,pDown:descentProbability(dist,n,quota)}; });
    T.remaining.forEach((m,idx)=>{
      const o=matchOut[idx], tot=(o.V+o.N+o.D)||1, ta=(o.A.V+o.A.N+o.A.D)||1, tb=(o.B.V+o.B.N+o.B.D)||1;
      const row={j:m.j,a:m.a,b:m.b,p:{V:o.V/tot,N:o.N/tot,D:o.D/tot},pA:{V:o.A.V/ta,N:o.A.N/ta,D:o.A.D/ta},pB:{V:o.B.V/tb,N:o.B.N/tb,D:o.B.D/tb}};
      if(acbb){ row.impact={}; ['V','N','D'].forEach(r=>{ const [h,c]=cond[idx][r]; row.impact[r]=c?h/c:null; }); const v=Object.values(row.impact).filter(x=>x!=null); row.swing=v.length>1?Math.max(...v)-Math.min(...v):0; }
      out.remaining.push(row);
    });
    return out;
  }

  /* Alignement avec renforts : les renforts entrent à la place des plus faibles de l'alignement tiré. */
  function withRenforts(lineup,renforts){
    if(!renforts||!renforts.length) return lineup;
    const base=(lineup||[]).slice().sort((a,b)=>force(b)-force(a));
    const keep=Math.max(0,4-renforts.length);
    return renforts.map(r=>({nom:r.nom,pre:r.pre,cls:r.cls,adj:r.adj||0,renfort:true})).concat(base.slice(0,keep));
  }

  /* Brûlage II.112 pour un renfort : journées déjà jouées (feuilles FFTT, toutes équipes du même championnat)
     + journées du scénario avant celle visée. Brûlé si au moins deux journées dans des équipes de numéro
     inférieur à l'équipe visée. `history` = [{j, n}] (n = numéro d'équipe). */
  function brulage(history,targetN,targetJ){
    const perRound=new Map();
    history.filter(h=>h.j<targetJ).forEach(h=>perRound.set(h.j,Math.min(perRound.get(h.j)||Infinity,h.n)));
    const ns=[...perRound.values()].sort((a,b)=>a-b);
    return {burned:ns.length>=2&&targetN>ns[1],limit:ns[1]||null,journees:ns.length};
  }

  return {PTS,SINGLES,sigmoid,rng,expectedSingles,simMatchA,simMatchB,lineupShift,rankTeams,goalReached,descentProbability,simulate,withRenforts,brulage,force};
});
