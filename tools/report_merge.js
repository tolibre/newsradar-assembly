  // ---------- 보고 대조(국회팀판 팀장 화면 — tools/make_variant.py가 tools/report_merge.js를 넣는다, 2026-10-29) ----------
  // 여당팀·야당팀 막내 보고를 팀장 화면(주소에 ?team= 없음)에 붙여 넣으면 같은 기사를 찾아 체크한다.
  //  - 체크된 묶음 = 막내가 올린 것, 체크 안 된 묶음 = 빈틈. '안 올라온 것' 필터는 한 기사라도 체크된 묶음을 통째로 숨긴다.
  //  - 페이지에서 못 찾은 줄(다른 경로로 고른 기사 등)은 버리지 않고 '전체 양식' 끝에 그대로 붙인다.
  //  - 그래서 팀장이 빈틈만 더 체크하면 '전체 양식'이 곧 국회팀 최종 보고가 된다(같은 기사가 두 번 올라와도 한 줄).
  //  - 이 브라우저에만 저장(보고마다, 14일). '대조 취소'는 대조가 체크한 것만 되돌린다.
  var CMPSTORE = TK + 'cmp-v1';
  var cmp = {}, GAP = {};
  try{ cmp = JSON.parse(localStorage.getItem(CMPSTORE) || '{}') || {}; }catch(e){ cmp = {}; }
  function cmpSave(){ pruneRid(cmp, 14); try{ localStorage.setItem(CMPSTORE, JSON.stringify(cmp)); }catch(e){} }
  function cmpParse(text){
    var out = [], sec = 'm';
    String(text || '').split(/\r?\n/).forEach(function(line){
      var s = line.trim(); if(!s) return;
      var h = /^<\s*([^<>]+?)\s*>$/.exec(s);
      if(h){ sec = /기처리/.test(h[1]) ? 'g' : 'm'; return; }
      s = s.replace(/^(?:[-·•*]|\d+[.)])\s*/, '');
      var t = s.replace(/\s*\(([^()]*)\)\s*$/, '');   // 끝의 (매체)·(쓴 기자)
      var k = tnorm(t);
      if(k) out.push({line: s, k: k, sec: sec});
    });
    return out;
  }
  function cmpRun(text){
    var rep = curRep(), lines = cmpParse(text), items = [], byK = {};
    allSegs(rep).forEach(function(s){ (s.groups || []).forEach(function(g){ g.clusters.forEach(function(c){ c.forEach(function(it){
      var x = {it: it, sid: s.id, k: tnorm(it.t)}; items.push(x); (byK[x.k] = byK[x.k] || []).push(x);
    }); }); }); });
    var rec = cmp[rep.id] || {added: [], extra: {m: [], g: []}};
    var res = {n: 0, hit: 0, miss: 0}, once = {};
    lines.forEach(function(L){
      if(once[L.k]) return; once[L.k] = 1; res.n++;
      var ms = byK[L.k] || [];
      if(!ms.length && L.k.length >= 10) ms = items.filter(function(x){ return x.k.length >= 10 && (x.k.indexOf(L.k) >= 0 || L.k.indexOf(x.k) >= 0); });
      if(!ms.length){ res.miss++; if(rec.extra[L.sec].indexOf(L.line) < 0) rec.extra[L.sec].push(L.line); return; }
      res.hit++;
      ms.forEach(function(x){
        var key = x.it.l || x.it.t;
        if(!isPicked(rep.id, x.sid, key)){ setPick(rep.id, x.sid, key, true); rec.added.push([x.sid, key]); }
      });
    });
    rec.n = (rec.n || 0) + res.n; rec.hit = (rec.hit || 0) + res.hit; rec.at = Date.now();
    cmp[rep.id] = rec; cmpSave(); savePicks();
    return res;
  }
  function cmpUndo(){
    var rep = curRep(), rec = cmp[rep.id]; if(!rec) return;
    rec.added.forEach(function(a){ setPick(rep.id, a[0], a[1], false); });
    delete cmp[rep.id]; cmpSave(); savePicks();
  }
  // '전체 양식'에 못 찾은 줄을 붙인다 — 보고 전체(모든 구간)를 낼 때만.
  function cmpExtraFor(rep, segs){
    var rec = !TEAM && cmp[rep.id];
    if(!rec || segs.length < allSegs(rep).length) return {m: [], g: []};
    return rec.extra;
  }
  function cmpMergeLines(lines, ex){
    var gi = lines.indexOf('<기처리>');
    var mon = gi < 0 ? lines.slice() : lines.slice(0, gi), gch = gi < 0 ? [] : lines.slice(gi + 1);
    while(mon.length && mon[mon.length - 1] === '') mon.pop();
    if(ex.m.length){ if(mon[0] !== '<모니터>') mon.unshift('<모니터>'); mon = mon.concat(ex.m); }
    gch = gch.concat(ex.g);
    var out = mon.slice();
    if(gch.length){ if(out.length) out.push(''); out.push('<기처리>'); out = out.concat(gch); }
    return out;
  }
  // '안 올라온 것' — 한 기사라도 체크된 묶음(구간 묶음·보고 전체 묶음 모두)은 통째로 숨긴다.
  function gapSet(rep){
    var o = {}, pk = function(s, it){ return isPicked(rep.id, s.id, it.l || it.t); };
    rep.segments.forEach(function(s){ (s.groups || []).forEach(function(g, gi){ g.clusters.forEach(function(c, ci){
      if(c.some(function(it){ return pk(s, it); })) c.forEach(function(it, ii){ o[rep.id + '|' + s.id + '|' + gi + '-' + ci + '-' + ii] = 1; });
    }); }); });
    (rep.all || []).forEach(function(mg){ mg.c.forEach(function(refs){
      var xs = refs.map(function(ref){ var s = rep.segments[ref[0]], g = s && s.groups[ref[1]], c = g && g.clusters[ref[2]], it = c && c[ref[3]];
        return it ? {s: s, it: it, u: rep.id + '|' + s.id + '|' + ref[1] + '-' + ref[2] + '-' + ref[3]} : null; }).filter(Boolean);
      if(xs.some(function(x){ return pk(x.s, x.it); })) xs.forEach(function(x){ o[x.u] = 1; });
    }); });
    return o;
  }
  function setFilter(f){
    ui.filter = f;
    [].forEach.call(document.querySelectorAll('.seg button'), function(b){ b.setAttribute('aria-pressed', String(b.dataset.f === f)); });
  }
  function cmpNote(rep){
    var el = document.getElementById('cmpnote'), rec = !TEAM && rep && cmp[rep.id];
    if(!rec){ el.hidden = true; el.innerHTML = ''; return; }
    var ex = rec.extra.m.length + rec.extra.g.length;
    el.innerHTML = '<b>보고 대조</b> 막내 보고 ' + rec.n + '줄 중 ' + rec.hit + '줄 체크' +
      (ex ? ' · 화면에 없는 ' + ex + '줄은 ‘전체 양식’ 끝에 붙습니다' : '') +
      ' <button type="button" class="lk" data-cg="1">' + (ui.filter === 'gap' ? '모든 기사 보기' : '안 올라온 것만') + '</button>' +
      ' <button type="button" class="lk" data-cadd="1">더 붙이기</button>' +
      ' <button type="button" class="lk" data-cun="1">대조 취소</button>';
    el.hidden = false;
  }
  var cveil = document.createElement('div');
  cveil.className = 'veil'; cveil.hidden = true;
  cveil.innerHTML = '<div class="panel" role="dialog" aria-modal="true" aria-labelledby="cmptitle"><div class="panel-head"><h3 id="cmptitle">보고 대조</h3>' +
    '<span class="sub" id="cmpsub"></span><button class="x" type="button" data-cx="1" aria-label="닫기">&times;</button></div>' +
    '<textarea id="cmptext" class="cmptext" spellcheck="false" placeholder="여당팀·야당팀 막내 보고를 그대로 붙여 넣으세요. 둘을 한꺼번에 넣어도 되고, 하나씩 따로 대조해도 쌓입니다.&#10;&lt;모니터&gt; 아래 줄은 모니터, &lt;기처리&gt; 아래 줄은 기처리로 봅니다."></textarea>' +
    '<div class="panel-foot"><button class="btn primary" type="button" data-cgo="1">대조</button>' +
    '<span class="hint">올라온 기사를 이 화면에서 찾아 체크합니다. 체크 안 된 묶음이 빈틈이고, 빈틈을 더 체크하면 ‘전체 양식’이 최종 보고가 됩니다.</span></div></div>';
  document.body.appendChild(cveil);
  function cmpOpen(){
    var r = curRep(); document.getElementById('cmpsub').textContent = r ? r.title : '';
    document.getElementById('cmptext').value = ''; cveil.hidden = false; document.getElementById('cmptext').focus();
  }
  var cbtn = document.getElementById('cmpbtn');
  if(cbtn){ cbtn.hidden = !!TEAM; cbtn.addEventListener('click', function(){ if(!PAST) cmpOpen(); }); }
  cveil.addEventListener('click', function(e){
    if(e.target === cveil || e.target.closest('[data-cx]')){ cveil.hidden = true; return; }
    if(e.target.closest('[data-cgo]')){
      var txt = document.getElementById('cmptext').value;
      if(!txt.trim()) return;
      cmpRun(txt); cveil.hidden = true;
      ui.tab = ui.rep + '/all'; tabManual = true; setFilter('gap'); draw(); window.scrollTo(0, 0);
    }
  });
  document.getElementById('cmpnote').addEventListener('click', function(e){
    if(e.target.closest('[data-cg]')){ setFilter(ui.filter === 'gap' ? 'all' : 'gap'); draw(); return; }
    if(e.target.closest('[data-cadd]')){ cmpOpen(); return; }
    if(e.target.closest('[data-cun]')){ cmpUndo(); setFilter('all'); draw(); }
  });

