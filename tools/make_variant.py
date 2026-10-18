#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""뉴스레이다 국회(정당)판(박정환 기자용) 생성기.

원본(tolibre/news-monitor — 김광일 기자 출입처판)의 파일을 그대로 가져와
'검색어·바이라인·브라우저 저장키·보관 기간' 같은 설정만 바꿔 이 저장소에 쓴다.
(재경부판 tolibre/newsradar-moef의 생성기와 같은 구조 — 설정 블록만 다르다.)

  python tools/make_variant.py <원본 저장소 경로> [<출력 경로, 기본=이 저장소>]

- 치환마다 '원본에서 정확히 몇 번 나와야 하는지'를 적어 두고, 다르면 아무 파일도
  쓰지 않고 멈춘다.
- 원본 쪽 파일은 읽기만 한다. 함수는 run_check의 폴백 한 줄(본문 매칭 → [단독]만)을 빼고 바꾸지 않는다.
"""
import hashlib, os, re, shutil, sys

# ---------------------------------------------------------------- 설정값 ---
REPORTER = "박정환"
# 박정환 기자는 CBS 국회팀장 — <기처리>에 팀원 기사를 모두 넣는다(사용자 요청 2026-10-15).
TEAM = ["박정환", "김태헌", "김재환", "박희영", "박인", "윤준호", "이은지", "김정록"]
TEAM_SECTION = "CBS 국회팀"

# '전체' 탭 묶음 가산(원본 LIVE_MEDIA_BOOST 자리에 채운다 — 사용자 요청 2026-10-15).
# 주요 일간지·종편·보도PP·3대 통신사는 조금, 09:00 보고는 조간 종합지, 14:00 보고는 석간지를 크게.
# 매체명은 원본 media_name() 결과 그대로. 내일신문은 원본 화이트리스트에 없어 아래에서 더한다.
DAILY_AM = ["조선일보", "중앙일보", "동아일보", "한국일보", "경향신문", "한겨레",
            "국민일보", "서울신문", "세계일보"]
DAILY_PM = ["문화일보", "내일신문", "헤럴드경제"]   # 석간 가점은 이 셋만(사용자 결정 2026-10-15). 경제지는 주요 일간지에 넣지 않음
BROADCAST = ["TV조선", "JTBC", "채널A", "MBN", "YTN", "연합뉴스TV"]
WIRE = ["연합뉴스", "뉴시스", "뉴스1"]
BOOST_BASE, BOOST_SLOT = 1.5, 3.0
def _set_lit(names):   # 집합 리터럴을 정렬해 쓴다 — set repr은 실행마다 순서가 달라 생성본 md5가 흔들렸다
    return "{" + ", ".join(repr(x) for x in sorted(set(names))) + "}"
NEW_BOOST = ("LIVE_MEDIA_BOOST = {\n"
             f'    "*": [({_set_lit(DAILY_AM + DAILY_PM + BROADCAST + WIRE)}, {BOOST_BASE})],\n'
             f'    "am": [({_set_lit(DAILY_AM)}, {BOOST_SLOT})],\n'
             f'    "pm": [({_set_lit(DAILY_PM)}, {BOOST_SLOT})],\n'
             "}   # 국회판(생성기)\n")
BEATS_TITLE = "국회·정당"
STORE_PREFIX = "nm-asm-"                  # 원본('nm-live-')·재경부판('nm-moef-')과 같은 출처라 반드시 달라야 한다
PARTIES = ["더불어민주당", "국민의힘", "조국혁신당", "개혁신당"]   # 사용자가 준 순서 = 섹션 순서
REPORT_ORDER_JS = "[" + ",".join(f"'{p}'" for p in PARTIES) + "]"

# 제목에는 정식 명칭보다 약칭이 압도적으로 많다(원본 DB 9/14~10/14 제목 실측:
# '더불어민주당' 9건 vs '민주당' 210건, '국민의힘' 138건 vs '국힘' 223건).
# 약칭이 KEYWORDS에 없으면 제목 판정이 안 돼 기사가 '먼저 검색한 키워드' 섹션으로 쏠린다.
# 그래서 약칭을 KEYWORDS에 넣되 네이버 검색은 0페이지로 막아(제목 판정·구글 RSS만) 호출을 늘리지 않는다.
# 與·여당 → 더불어민주당, 野·야당 → 국민의힘(제1야당)으로 본다(2026-10-15, 사용자 결정 '관문' — 제목 단서 확대).
# **정권이 바뀌면 이 두 줄을 바꿔야 한다.**
ABBR = {"민주당": "더불어민주당", "與": "더불어민주당", "여당": "더불어민주당",
        "국힘": "국민의힘", "野": "국민의힘", "야당": "국민의힘",
        "혁신당": "조국혁신당"}
KW_ORDER = ["더불어민주당", "민주당", "與", "여당", "국민의힘", "국힘", "野", "야당",
            "조국혁신당", "혁신당", "개혁신당"]
# 본문에만 정당명이 나오는 기사는 [단독]만 남겨 이 섹션으로 모은다(사용자 결정 2026-10-15:
# "관문을 달되, 정책 기사라도 단독은 모니터해야"). KEYWORDS에 없는 그룹이라 섹션 맨 뒤에 붙는다.
BODY_SCOOP_GROUP = "기타 단독"

NEW_BASE_KEYWORDS = "BASE_KEYWORDS = [\n" + \
    "    # 뉴스레이다 국회(정당)판(tools/make_variant.py가 생성 — 직접 고치지 말 것).\n" + \
    "    # 약칭(민주당·국힘·혁신당)은 제목 판정용 — 네이버 검색은 KEYWORD_MAX_PAGES 0으로 막았다.\n" + \
    "".join(f'    "{k}",\n' for k in KW_ORDER) + "]\n"

# 정당명·약칭을 KEYWORD_GROUPS에 넣는다. ①약칭 → 정식 그룹 ②정당명이 클러스터링의
# '출입처명 토큰'(CLUSTER_AGENCY_TOKENS — KEYWORD_GROUPS에서 유도)에 들어가야
# '국힘' 한 단어로 서로 다른 사안이 묶이지 않는다(원본 0-14와 같은 구조).
NEW_GROUPS_LINE = "KEYWORD_GROUPS.update(DUTY_KEYWORD_GROUPS)\n" + \
    "KEYWORD_GROUPS.update(" + repr(dict({p: p for p in PARTIES}, **ABBR)) + ")   # 국회판(생성기)\n"

# 약칭 오탐: '개혁신당'에 '혁신당'이 들어 있다. '민주당'은 해외 정당·다른 당명에도 쓰인다.
NEW_ANTI = '    "누리호":   [r"누리호텔"],\n' + \
    '    "혁신당":   [r"개혁신당"],\n' + \
    '    "야당":     [r"야당역", r"야당동"],\n' + \
    '    "민주당":   [r"美\\s*민주당", r"미국\\s*민주당", r"미\\s민주당", r"입헌민주당", r"자유민주당", r"국민민주당", r"사회민주당", r"기독교민주당", r"새천년민주당", r"통합민주당"],\n'

# 정당 기사는 부처 기사보다 몇 배 많다. 네이버는 한 번에 100건씩 최대 5페이지(500건)까지만
# 거슬러 가는데(MAX_PAGES_PER_KEYWORD), 한 시간 새 기사가 그보다 많으면 나머지를 **조용히 놓친다**.
# 네이버 검색 API의 start 상한(1000)까지 10페이지로 연다. 실측 후 다시 볼 것.
NEW_MAX_PAGES = "KEYWORD_MAX_PAGES = {\n    \"CBS\": 1,\n" + \
    "".join(f'    "{p}": 3,   # 관문 탈락분은 DB에 안 남아 매번 상한까지 넘긴다 — 300건이면 시간당 수집량의 몇 배\n' for p in PARTIES) + \
    "".join(f'    "{a}": 0,   # 약칭 — 제목 판정용, 네이버 검색 안 함\n' for a in ABBR) + "}\n"

NEW_FALLBACK = (
    "                # 국회판(생성기, 2026-10-15): 정당명은 거의 모든 정치·정책 기사 본문에 스친다.\n"
    "                # 본문 매칭은 [단독]만 남겨 '기타 단독' 섹션으로 모은다(사용자 결정).\n"
    "                if priority_mark(it[\"title\"]) != \"🔥\":\n"
    "                    continue\n"
    f"                kws = {{\"{BODY_SCOOP_GROUP}\"}}\n")

# 같은 사안이 정당 섹션 두 곳에 갈리던 문제(사용자 결정 2026-10-15 — '1번: 사안 단위로 합치기').
# 섹션은 '제목에 먼저 걸린 정당 단서'로 정해져, 같은 사안이 제목에 與가 있느냐로 갈렸다
# (10/15 09:00 보고: 北 지뢰 규탄 결의안 민주당 13·국민의힘 14 / 임광현 비서실장 11·21).
# 원본 LIVE_STORY_MERGE_GROUPS 자리에 정당 4개를 채우면, 보고 전체를 한 번에 묶어 두 섹션 이상에
# 걸친 사안을 기사가 가장 많은 섹션 하나로 모은다(구간 탭·'전체' 탭·칩·보고 양식 모두 같은 섹션).
NEW_STORY_MERGE = f"LIVE_STORY_MERGE_GROUPS = {PARTIES!r}   # 국회판(생성기)\n"
# 정당명·약칭은 묶음 판정 토큰에서 뺀다. 정당 기사 제목엔 거의 늘 정당명이 있어서, 정당명 하나 +
# 아무 단어 하나로 다른 사안이 이어졌다('[단독] 한미의원연맹 민주당 측 신임 공동회장에 송영길' ↔
# '민주당, 임광현 신임 비서실장 임명 환영' = {민주당, 신임}). 출입처명 토큰(0-14) 규칙은 겹친
# 출입처명이 2개 이상이면 같은 사안으로 인정하는데, 정당판에선 {민주당, 국힘}이 사안이 아니다.
# 위 합치기는 섹션을 넘어 묶으므로 이 다리가 남아 있으면 송영길 [단독]이 국민의힘 섹션으로 끌려간다(실측).
# 원본에는 넣지 않는다 — 원본 DB 50개 슬롯 중 8개(김승원 청문회·호르무즈 파병 등)의 묶음이 바뀐다.
STOP_PARTY = sorted(set(PARTIES) | {a for a in ABBR if re.fullmatch(r"[가-힣]{2,}", a)})
NEW_STOPWORDS = ("# 국회판(생성기): 정당명·약칭은 묶음 판정에서 뺀다 — 정당판에선 사안을 가리키지 않는다.\n"
                 f"TOPIC_STOPWORDS |= set({STOP_PARTY!r})\n\n"
                 "def topic_tokens(title):\n")

# 발언·행위 주체 정당으로 섹션 배정(사용자 결정 2026-10-15). 판정 코드·인물 명단은 tools/party_actor.py —
# 원본 GROUP_ASSIGN_HOOK 자리(digest_by_group 바로 앞)에 그 파일 내용을 그대로 넣는다.
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "party_actor.py"), encoding="utf-8") as _f:
    NEW_ASSIGN_HOOK = _f.read()

# 사진 기사 추가 규칙(사용자 요청 2026-10-15 "박정환 페이지에 사진 기사가 너무 많다") — 원본 CAPTION_EXTRA 자리.
# R1 관형어 + (이름) + 정당 + 직함으로 끝남: '물 마시는 정점식 국민의힘 원내대표'·'퇴장한 국민의힘 의원들'
#    (관형어 끝 글자 는·은·한·된·빈·던·친·운·른·낸 — 이름 끝 글자로 흔한 인·선·진은 뺌, '…에 이기인 전 사무총장' 같은 인사 기사 제외)
# R2 장면 명사로 끝남: '…회의에서 발언'·'인선 관련 브리핑'·'텅 빈 국민의힘 의원 자리'(퇴장·입장은 기사 제목에도 흔해 뺌)
# R3 낫표 사진 태그: '「M포토」 …'
_POS = ("대표|원내대표|최고위원|의원|위원장|부위원장|대변인|수석대변인|원내대변인|사무총장|의장|부의장|장관|차관|총리|"
        "정책위의장|원내수석부대표|후보자|비대위원장|비상대책위원장|시장|지사|대사|대통령|위원")
NEW_CAPTION = (
    "CAPTION_EXTRA = [   # 국회판(생성기) — 사진 설명형 제목\n"
    f"    (re.compile(r\"(?:^|(?<!에)\\s)[가-힣]*(?:는|은|한|된|빈|던|친|운|른|낸)\\s(?:\\S+\\s+){{0,4}}\\S*(?:{_POS})들?$\"), 45, False),\n"
    "    (re.compile(r\"\\s(?:발언|모두발언|인사말|브리핑|기념촬영|대화|악수|자리|모습|박수|묵념|경례|건배|포즈|미소)$\"), 40, False),\n"
    "    (re.compile(r\"「[^」]*(?:포토|사진|pic)[^」]*」\", re.I), 0, True),\n"
    "]\n")

NM = "news_monitor.py"
RP = "render_page.py"

REPLACEMENTS = [
    # ---- news_monitor.py: 검색어 ----
    # 0-44(2026-10-18): 원본은 당직 출입처 8곳을 날마다 따로 수집한다(알림 없음, 뉴스레이다 '당직' 스위치로만 봄).
    # 국회판은 쓰지 않는다 — 켜 두면 이 판 출입처에 없는 당직 그룹(국토부·농식품부 등)을 매시간 수집해 DB만 커진다.
    (NM, "DUTY_COLLECT = True\n",
         "DUTY_COLLECT = False   # 국회판은 당직 수집을 하지 않는다(생성기, 0-44)\n", 1, False),
    # 0-46: 원본의 EXCLUDE_TERMS(대한체육회·스포츠공정위·모의공정위)는 '공정위' 검색어 오탐용이다. 이 판은 '공정위'를
    # 검색하지 않으니 끈다 — 켜 두면 제목에 '대한체육회'가 든 자기 출입처 기사(문체부 감사·국감 등)까지 통째로 버려진다.
    (NM, r"EXCLUDE_TERMS = \[\n(?:.*\n)*?\]\n",
         "EXCLUDE_TERMS = []   # 이 판은 '공정위'를 검색하지 않아 공정위 오탐용 제외어가 필요 없다(생성기, 0-46)\n", 1, True),
    (NM, r"BASE_KEYWORDS = \[\n(?:.*\n)*?\]\n", NEW_BASE_KEYWORDS, 1, True),
    (NM, 'TEMP_KEYWORDS = {\n    "대미투자": "2026-09-23",\n}\n',
         "TEMP_KEYWORDS = {}\n", 1, False),
    (NM, 'KEYWORD_MAX_PAGES = {\n    "CBS": 1,\n}\n', NEW_MAX_PAGES, 1, False),
    (NM, "KEYWORD_GROUPS.update(DUTY_KEYWORD_GROUPS)\n", NEW_GROUPS_LINE, 1, False),
    (NM, '    "누리호":   [r"누리호텔"],\n', NEW_ANTI, 1, False),
    # ---- news_monitor.py: 보관 기간 ----
    # 정당 기사량이면 90일치 DB가 GitHub 파일 한도(100MB)를 넘는다(매시 커밋되는 파일).
    # 라이브 페이지는 사흘치·'이미 나옴'은 24시간·본인 기사는 14일만 쓰므로 14일이면 충분하다.
    (NM, "RETENTION_DAYS = 90 ", "RETENTION_DAYS = 14 ", 1, False),
    # ---- news_monitor.py: run_check 폴백(국회판에서 유일한 함수 본문 변경) ----
    (NM, "                kws = {kw}   # 제목엔 없고 본문에만 있는 경우 — 검색어를 그대로 사용\n",
         NEW_FALLBACK, 1, False),
    # ---- news_monitor.py: 바이라인 ----
    (NM, 'BYLINE_NAME = "김광일"', f'BYLINE_NAME = "{REPORTER}"', 1, False),
    (NM, 'BYLINE_SECTION = "김광일 기자"', f'BYLINE_SECTION = "{TEAM_SECTION}"', 1, False),
    (NM, "BYLINE_NAMES = [BYLINE_NAME]\n", f"BYLINE_NAMES = {TEAM!r}   # 국회팀(생성기)\n", 1, False),
    (NM, 'LIVE_MEDIA_BOOST = {"*": [(LIVE_MEDIA_MAJOR, 1.0)]}\n', NEW_BOOST, 1, False),
    # 원본 0-35(주체 출입처 배정·'전체' 탭 주체 가점)는 국회판에선 끈다 — 배정은 정당 주체 판정(party_actor)이 하고,
    # 주체 가점은 박 기자 요청이 아니다.
    (NM, "ACTOR_ASSIGN = True\n", "ACTOR_ASSIGN = False   # 국회판(생성기) — 배정은 GROUP_ASSIGN_HOOK(정당 주체)\n", 1, False),
    (NM, "LIVE_ACTOR_BONUS = 2.0\n", "LIVE_ACTOR_BONUS = 0   # 국회판(생성기)\n", 1, False),
    # ---- news_monitor.py: 사안 단위 섹션 합치기 + 정당명 묶음 토큰 제외(2026-10-15) ----
    (NM, "LIVE_STORY_MERGE_GROUPS = []\n", NEW_STORY_MERGE, 1, False),
    (NM, "def topic_tokens(title):\n", NEW_STOPWORDS, 1, False),
    (NM, "GROUP_ASSIGN_HOOK = None\n", NEW_ASSIGN_HOOK, 1, False),
    (NM, r"CAPTION_EXTRA = \[\n(?:    .*\n)*?\]\n", NEW_CAPTION, 1, True),
    (NM, "BYLINE_TRUST_META = False\n", "BYLINE_TRUST_META = True   # 국회판(생성기) — 방송 녹취 출연 문구 오탐 방지\n", 1, False),
    # 석간 내일신문을 화이트리스트에 더한다(원본엔 없음 — 없으면 페이지에 아예 안 뜬다)
    (NM, "STORE_NON_WHITELIST = True\n",
         "STORE_NON_WHITELIST = True\nMEDIA_DOMAINS.add(\"naeil.com\"); MEDIA_NAMES.add(\"내일신문\")   # 국회판(생성기)\n", 1, False),
    (NM, "def media_name(source):\n",
         "DOMAIN_TO_NAME[\"naeil.com\"] = \"내일신문\"   # 국회판(생성기)\n\ndef media_name(source):\n", 1, False),

    # ---- render_page.py ----
    (RP, "var REPORT_ORDER = ['방미통위','공정위','과기정통부','우주항공청'];",
         f"var REPORT_ORDER = {REPORT_ORDER_JS};", 2, False),
    (RP, "출입처 순서(방미통위 → 공정위 → 과기정통부 → 우주청 → 2진)",
         "정당 순서(" + " → ".join(PARTIES) + ")", 2, False),
    (RP, "'nm-live-", f"'{STORE_PREFIX}", 6, False),
    (RP, '[data-g="공정위"], [data-b="공정위"]', '[data-g="더불어민주당"], [data-b="더불어민주당"]', 1, False),
    (RP, '[data-g="방미통위"], [data-b="방미통위"]', '[data-g="국민의힘"], [data-b="국민의힘"]', 1, False),
    (RP, '[data-g="우주항공청"], [data-b="우주항공청"]', '[data-g="조국혁신당"], [data-b="조국혁신당"]', 1, False),
    (RP, '[data-g="과기정통부"], [data-b="과기정통부"]', '[data-g="개혁신당"], [data-b="개혁신당"]', 1, False),
    (RP, '[data-g="김광일 기자"], [data-b="김광일 기자"]',
         f'[data-g="{TEAM_SECTION}"], [data-b="{TEAM_SECTION}"]', 1, False),
    (RP, '<button type="button" id="sync" class="sync off"',
         '<button type="button" id="sync" class="sync off" style="display:none"', 1, False),
    (RP, "<title>뉴스레이다</title>", f"<title>뉴스레이다 · {BEATS_TITLE}</title>", 1, False),
    (RP, "document.title = '뉴스레이다 · ' + r.title;",
         "document.title = '뉴스레이다(국회) · ' + r.title;", 1, False),
    (RP, "맨 끝 ‘김광일 기자’는", f"맨 끝 ‘{TEAM_SECTION}’(팀원 {len(TEAM)}명 기사, 보고 양식에선 &lt;기처리&gt;)은", 1, False),
    (RP, "체크한 기사와 ‘여기까지 확인’은 이 기기에 저장되고, 머리줄 <b>기기 연동</b>을 켜면 다른 기기와 맞춰집니다(내 GitHub 비공개 gist). · <a href=\"../\">최신 다이제스트</a> · <a href=\"../archive/\">지난 다이제스트</a></p>",
         "체크한 기사와 ‘여기까지 확인’은 이 기기(브라우저)에만 저장됩니다 — PC와 폰은 따로 기억합니다.</p>", 1, False),
]

# 원본에서 그대로 가져오는 파일(치환 없음)
COPY_AS_IS = ["merge_db.py", "retitle.py"]

# 페이지에 남아 있으면 안 되는 문자열 — 주석(# / //)이 아닌 줄에서만 검사한다.
# (news_monitor.py는 문자열 대신 아래 EXPECT로 '실제로 import했을 때의 값'을 검사한다.
#  원본의 우주항공청·CBS 매핑·소관 어휘는 남아 있어도 검색어가 아니면 무해하다.)
FORBIDDEN = {
    RP: ["nm-live-", "김광일 기자\"", "기기 연동</b>", "방미통위 → 공정위"],
}
# 생성한 news_monitor.py를 별도 프로세스로 import해 확인할 값(당직·임시 키워드가 꺼진 날짜 기준).
EXPECT = {
    "DUTY_ONLY_GROUPS": [],   # 0-44 — 당직 수집 꺼짐
    "EXCLUDE_TERMS": [],      # 0-46 — 공정위 오탐용 제외어 꺼짐
    "KEYWORDS": KW_ORDER,
    "GROUP_ORDER": PARTIES,
    "RETENTION_DAYS": 14,
    "KEYWORD_MAX_PAGES": dict({"CBS": 1}, **{p: 3 for p in PARTIES}, **{a: 0 for a in ABBR}),
    "BYLINE_NAME": REPORTER,
    "BYLINE_SECTION": TEAM_SECTION,
    "BYLINE_NAMES": TEAM,
    "LIVE_STORY_MERGE_GROUPS": PARTIES,
    "ACTOR_ASSIGN": False,
    "LIVE_ACTOR_BONUS": 0,
}


def md5(b):
    return hashlib.md5(b).hexdigest()


def apply(src_dir):
    out = {}
    for fname in {r[0] for r in REPLACEMENTS}:
        with open(os.path.join(src_dir, fname), encoding="utf-8") as f:
            out[fname] = f.read()
    errors = []
    for fname, old, new, count, is_re in REPLACEMENTS:
        text = out[fname]
        found = len(re.findall(old, text)) if is_re else text.count(old)
        if found != count:
            errors.append(f"{fname}: {old[:60]!r} — {count}번이어야 하는데 {found}번")
            continue
        out[fname] = re.sub(old, lambda m: new, text) if is_re else text.replace(old, new)
    if errors:
        raise SystemExit("원본이 예상과 달라 생성을 멈춥니다(아무 파일도 쓰지 않음):\n  "
                         + "\n  ".join(errors))
    leftovers = []
    for fname, pats in FORBIDDEN.items():
        for i, line in enumerate(out[fname].splitlines(), 1):
            s = line.strip()
            if s.startswith("#") or s.startswith("//"):
                continue
            for p in pats:
                if p in line:
                    leftovers.append(f"{fname}:{i}: {p!r} — {s[:80]}")
    if leftovers:
        raise SystemExit("원본 고유 문자열이 남았습니다:\n  " + "\n  ".join(leftovers))
    return out


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    src = os.path.abspath(sys.argv[1])
    dst = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else
                          os.path.join(os.path.dirname(__file__), ".."))
    out = apply(src)
    # 먼저 임시 폴더에 써서 import 검사를 통과한 뒤에만 실제 위치로 옮긴다.
    import json, subprocess, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        for fname, text in out.items():
            with open(os.path.join(tmp, fname), "w", encoding="utf-8") as f:
                f.write(text)
        probe = ("import json, news_monitor as m; print(json.dumps({k: getattr(m, k) for k in %r}, "
                 "ensure_ascii=False))" % list(EXPECT))
        env = dict(os.environ, DUTY_MODE="")
        r = subprocess.run([sys.executable, "-c", probe], cwd=tmp, env=env,
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit("생성본 import 실패:\n" + r.stderr[-2000:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        bad = {k: (got.get(k), v) for k, v in EXPECT.items() if got.get(k) != v}
        if bad:
            raise SystemExit(f"생성본 설정값이 예상과 다릅니다: {bad}")
    for fname, text in sorted(out.items()):
        with open(os.path.join(dst, fname), "w", encoding="utf-8") as f:
            f.write(text)
    for fname in COPY_AS_IS:
        shutil.copyfile(os.path.join(src, fname), os.path.join(dst, fname))
    for fname in sorted(list(out) + COPY_AS_IS):
        with open(os.path.join(src, fname), "rb") as a, open(os.path.join(dst, fname), "rb") as b:
            print(f"{fname:18s} 원본 {md5(a.read())} → 생성 {md5(b.read())}")


if __name__ == "__main__":
    main()
