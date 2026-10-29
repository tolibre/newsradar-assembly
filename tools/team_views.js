  // ---------- 팀별 화면(국회팀판 — tools/make_variant.py가 tools/team_views.js를 넣는다, 2026-10-29) ----------
  // 여당팀·야당팀 막내가 각자 모니터해 박정환 팀장에게 올리고, 팀장이 빈틈을 보강해 국회팀 보고를 완성한다.
  // 주소 끝 ?team=여당 / ?team=야당 → 그 팀 섹션과 그 팀원 <기처리>만(박정환 기사는 양쪽). 주소에 없으면 지금처럼 전부.
  // '숨김 목록' 방식이라 목록에 없는 섹션(기타 단독·앞으로 생길 국회 공통 섹션 등)은 두 화면 모두에 나온다.
  // 저장키도 팀마다 따로 — 같은 기기에서 두 화면을 열어도 체크·'여기까지 확인'이 섞이지 않게.
  var TEAMS = __TEAMS__;
  var TEAM_ALIAS = __ALIASES__;
  var TEAM = null;
  (function(){
    var m = /[?&]team=([^&#]*)/.exec(location.search), v = '';
    if(m){ try{ v = decodeURIComponent(m[1].replace(/\+/g, ' ')).trim(); }catch(e){ v = m[1]; } }
    var k = TEAM_ALIAS[v] || TEAM_ALIAS[v.toLowerCase()];
    if(k){ TEAM = TEAMS[k]; TEAM.key = k; TEAM.drop = {}; TEAM.hide.forEach(function(g){ TEAM.drop[g] = 1; }); }
  })();
  var TK = '__PREFIX__' + (TEAM ? TEAM.key + '-' : '');
  function teamByline(b){   // 그 팀원이 쓴(공동 바이라인이면 한 명이라도) 기사만. 쓴 기자를 모르면 남긴다.
    if(!TEAM || !b || !b.groups || !b.groups[0]) return b;
    var b2 = {}, g2 = {}, n = 0;
    Object.keys(b).forEach(function(k){ b2[k] = b[k]; });
    Object.keys(b.groups[0]).forEach(function(k){ g2[k] = b.groups[0][k]; });
    g2.clusters = b.groups[0].clusters.map(function(c){
      return c.filter(function(it){
        var ws = (it.w || '').split(/[·,]/).filter(Boolean);
        return !ws.length || ws.some(function(w){ return TEAM.members.indexOf(w) >= 0; });
      });
    }).filter(function(c){ return c.length; });
    g2.clusters.forEach(function(c){ n += c.length; });
    g2.n = n; b2.groups = [g2]; b2.n = n;
    return b2;
  }
  if(TEAM){   // 머리줄 이름 — 좁은 화면은 .whob를 숨기므로 팀 이름을 앞에 둔다. 처음 화면 링크도 팀 주소를 유지
    var _who = document.querySelector('.who');
    if(_who) _who.innerHTML = '국회 ' + TEAM.label + '<span class="whob"> (CBS 국회팀)</span>';
    var _br = document.querySelector('a.brand');
    if(_br) _br.setAttribute('href', './' + location.search);
  }
