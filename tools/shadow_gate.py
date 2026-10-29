# ---- 국회팀판 그림자 기록(tools/make_variant.py가 이 파일을 news_monitor.py 맨 아래 main 앞에 넣는다 — 직접 고치지 말 것) ----
# 2026-10-29 사용자 결정 "1번 바로 시작하자" + "여야 협상, 국회의장 기사도 모니터 보고에 넣어".
# 목적: 관문(제목에 정당 단서)을 넓히기 전에 **무엇이 얼마나 들어올지** 실측한다.
# 2026-10-29 22시 관문 넓히기(assembly_gate) 반영 — 통과하는 탐색 검색 기사는 articles로 받고, 그림자 표에 이미 있던 통과분은
# 원래 기록 시각(seen_dt) 그대로 articles로 옮긴다(shadow_migrate, check 앞). 나머지 탈락분은 계속 기록한다.
#   ① 관문 탈락 기록 — 정당 검색어로 잡혔지만 제목에 정당 단서가 없어 버려진 기사([단독] 제외)를 shadow_gate에 남긴다.
#      (제목 맨 앞 정치인·국회 기관어·노컷 기사 등 어떤 규칙을 넣을지는 이 표로 나중에 채점한다.)
#   ② 탐색 검색 — 정당 검색어로는 아예 안 잡히는 국회 기관 기사(국회의장·여야 협상)를 보려고
#      SHADOW_PROBE_KEYWORDS를 따로 검색해 기록만 한다. articles에 이미 있는 기사는 건너뛴다.
#   ③ 노컷 기사 바이라인 — ①②에 든 노컷 기사 원문을 열어 국회팀원 기사인지 표시한다(<기처리> 누락 실측).
# 기록은 SHADOW_KEEP_DAYS일만 둔다. 끄려면 생성기에서 이 파일 삽입을 빼고 재생성(테이블은 남아도 무해).
# 한계: merge_db.py는 이 표를 모르는 표로 보고 기준 DB 쪽을 남긴다 — push 경합이 난 실행의 기록은 빠질 수 있다(측정용이라 감수).

SHADOW_PROBE_KEYWORDS = {"국회의장": 2, "여야": 3}   # 검색어 → 네이버 최대 페이지
SHADOW_KEEP_DAYS = 4
SHADOW_BYLINE_MAX = 20     # 실행당 여는 노컷 원문 상한(본 바이라인 수집 40과 별도)
SHADOW_FRESH_HOURS = 36    # 탐색 검색·옮기기는 발행 36시간 이내만(첫 탐색이 몇 달 전 기사까지 거슬러 갔다)
_SHADOW_ROWS = []


def _shadow_add(it, kw):
    """run_check 폴백에서 관문 탈락 기사를 메모리에 모은다(저장은 실행 끝에 shadow_finish)."""
    _SHADOW_ROWS.append((it["id"], it["title"], it["link"], it["source"], it["pub_dt"], kw, it["origin"]))


def _shadow_table(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS shadow_gate(
        id TEXT PRIMARY KEY, title TEXT, link TEXT, source TEXT,
        pub_dt TEXT, seen_dt TEXT,     -- seen_dt = 처음 기록한 실행 시각
        kw TEXT,                       -- 잡은 검색어(정당 검색어 = 관문 탈락, 탐색 검색어 = 탐색)
        origin TEXT,
        own INTEGER, note TEXT)        -- 노컷 기사만: 국회팀원 기사인가 / 판정 근거""")


def shadow_finish(now=None, fetch=None):
    now = now or datetime.datetime.now(KST)
    conn = db()
    try:
        _shadow_table(conn)
        seen = now.isoformat()
        n_gate = 0
        for r in _SHADOW_ROWS:
            cur = conn.execute("INSERT OR IGNORE INTO shadow_gate VALUES(?,?,?,?,?,?,?,?,NULL,NULL)",
                               (r[0], r[1], r[2], r[3], r[4], seen, r[5], r[6]))
            n_gate += cur.rowcount
        # ② 탐색 검색
        known = {x[0] for x in conn.execute("SELECT id FROM articles")} | \
                {x[0] for x in conn.execute("SELECT id FROM shadow_gate")}
        n_probe = n_take = 0
        for kw, pages in SHADOW_PROBE_KEYWORDS.items():
            KEYWORD_MAX_PAGES.setdefault(kw, pages)
            try:
                items = fetch_naver(conn, kw, set(known)) + fetch_google(kw, set(known))
            except Exception as e:
                print(f"[shadow] 탐색 '{kw}' 실패: {e}")
                continue
            fresh = (now - datetime.timedelta(hours=SHADOW_FRESH_HOURS)).isoformat()
            for it in items:
                if it["id"] in known or is_excluded(it["title"]):
                    continue
                known.add(it["id"])
                g = assembly_gate(it["title"], it["source"]) if it["pub_dt"] >= fresh else None
                if g:   # 관문 넓히기 — 국회의장·정치인·국회 전반 기사는 페이지로
                    conn.execute("INSERT OR IGNORE INTO articles VALUES(?,?,?,?,?,?,?,?)",
                                 (it["id"], it["title"], it["link"], it["source"], it["pub_dt"], seen, g, it["origin"]))
                    n_take += 1
                    continue
                conn.execute("INSERT OR IGNORE INTO shadow_gate VALUES(?,?,?,?,?,?,?,?,NULL,NULL)",
                             (it["id"], it["title"], it["link"], it["source"], it["pub_dt"], seen, kw, it["origin"]))
                n_probe += 1
        # ③ 노컷 기사 바이라인
        fetch = fetch or _fetch_page
        todo = [x for x in conn.execute(
            "SELECT id, title, link FROM shadow_gate WHERE own IS NULL ORDER BY seen_dt DESC")
            if _is_nocut_link(x[2])][:SHADOW_BYLINE_MAX]
        n_own = 0
        for aid, title, link in todo:
            tail = _PROGRAM_TAIL_RE.search(clean_title_display(title))
            if tail and any(k in tail.group(1) for k in BYLINE_PROGRAM_TAGS):
                own, note = False, "라디오 대담 녹취(제목 [프로그램])"
            else:
                try:
                    own, note = byline_in_html(fetch(link))
                except Exception as e:
                    print(f"[shadow] 노컷 원문 열기 실패 {clean_title_display(title)[:30]} — {e}")
                    continue
            conn.execute("UPDATE shadow_gate SET own=?, note=? WHERE id=?", (int(own), note, aid))
            n_own += int(own)
            if own:
                print(f"  [shadow 팀원] {clean_title_display(title)[:50]} ({note})")
        cut = (now - datetime.timedelta(days=SHADOW_KEEP_DAYS)).isoformat()
        conn.execute("DELETE FROM shadow_gate WHERE seen_dt < ?", (cut,))
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM shadow_gate").fetchone()[0]
        print(f"[shadow] 관문 탈락 신규 {n_gate}건 · 탐색 받음 {n_take}건 · 탐색 탈락 {n_probe}건 · 노컷 확인 {len(todo)}건(팀원 {n_own}) · 보관 {total}건")
    finally:
        conn.close()


def shadow_migrate(now=None):
    """그림자 표에 있던 기사 중 assembly_gate를 통과하는 것을 원래 기록 시각 그대로 articles로 옮긴다(보고 구간이 맞게)."""
    now = now or datetime.datetime.now(KST)
    conn = db()
    try:
        _shadow_table(conn)
        fresh = (now - datetime.timedelta(hours=SHADOW_FRESH_HOURS)).isoformat()
        moved = 0
        for aid, title, link, source, pub, seen, origin in conn.execute(
                "SELECT id, title, link, source, pub_dt, seen_dt, origin FROM shadow_gate WHERE pub_dt >= ?", (fresh,)).fetchall():
            g = assembly_gate(title, source)
            if not g:
                continue
            conn.execute("INSERT OR IGNORE INTO articles VALUES(?,?,?,?,?,?,?,?)", (aid, title, link, source, pub, seen, g, origin))
            conn.execute("DELETE FROM shadow_gate WHERE id=?", (aid,))
            moved += 1
        # 본문 매칭 섹션('기타 단독'·국회의장·국회)에 다른 정당 검색어가 덧붙은 옛 기록을 바로잡는다(멱등 — 바로잡을 게 없으면 0건).
        fixed = 0
        for aid, kw in conn.execute("SELECT id, keywords FROM articles WHERE keywords LIKE '%,%' AND "
                                    "(keywords LIKE '%기타 단독%' OR keywords LIKE '%국회%')").fetchall():
            ks = kw.split(",")
            own = [g for g in ("기타 단독", GATE_SPEAKER_GROUP, GATE_ASSEMBLY_GROUP) if g in ks]
            if own and len(ks) > 1:
                conn.execute("UPDATE articles SET keywords=? WHERE id=?", (own[0], aid))
                fixed += 1
        conn.commit()
        if moved or fixed:
            print(f"[shadow] 관문 넓히기로 그림자 표에서 {moved}건 옮김 · 섹션 덧붙은 검색어 {fixed}건 바로잡음")
    finally:
        conn.close()


_run_check_orig = run_check


def run_check():
    try:
        shadow_migrate()
    except Exception as e:
        print(f"[warn] 그림자 표 옮기기 실패: {e}")
    _run_check_orig()
    try:
        shadow_finish()
    except Exception as e:   # 기록 실패는 check 결과에 영향 없음
        print(f"[warn] 그림자 기록 실패: {e}")


