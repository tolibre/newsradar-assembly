# ---- 국회판(tools/make_variant.py가 이 파일을 news_monitor.py에 넣는다 — 직접 고치지 말 것) ----
# 발언·행위 주체 정당으로 섹션 배정(사용자 결정 2026-10-15: "발화자가 국민의힘인데 민주당을 욕했다고 민주당
# 섹션에 들어가네 — 발언 주체나 행위 주체 쪽으로 귀속해줘").
# 원본 규칙은 '제목에 KEYWORDS 순서상 먼저 걸린 단서'라 민주당이 늘 이겼다 — 정점식 "민주당 '신천지 집단 입당'
# 압수수색해야"(국민의힘 사무총장의 말)가 민주당 섹션에 갔다.
# 판정 순서(앞에서 정해지면 끝):
#   ① 제목 맨 앞이 정당 단서 — '국힘, 與 신천지 의혹에…' → 국민의힘, '與김영진 "…"' → 더불어민주당
#   ② 제목 맨 앞이 사람 — 바로 뒤 정당 단서('서지영 국민의힘 의원 -') 또는 명단(PARTY_PEOPLE + DB 학습)
#   ③ 따옴표 안을 지운 제목에서, 목적어로 쓰인 것('민주당 겨냥'·'국힘에')을 뺀 첫 정당 단서
#   ④ 못 정하면 None → 원본 규칙
# 여기서 정해진 기사는 사안 단위 합치기(LIVE_STORY_MERGE_GROUPS)가 옮기지 않는다.

# 사람 → 정당 명단. 정권·당적이 바뀌면 고칠 것. (2026-10-15: 제목 '정당 이름 + 직함' 패턴 실측 + 사용자 확인 + Claude 정리)
# 정부 인사(총리·장관)는 여권으로 보고 더불어민주당에 둔다.
PARTY_PEOPLE = {
    "더불어민주당": """
        정청래 김민석 한병도 박찬대 추미애 최민희 서영교 김병주 진성준 윤호중 김성주 박지원 우상호 김남국
        박주민 윤건영 김영진 이상식 김남희 김용민 장경태 김현정 한준호 전현희 정동영 백혜련 고민정 부승찬
        김준혁 양문석 황희 이재정 조정식 김태년 문금주 이해식 노종면 이훈기 이정헌 김윤덕 박선원 박범계
        이성윤 이언주 송영길 이인영 이광재 권칠승 김영호 김우영 남인순 문대림 문진석 민홍철 박균택 박상혁
        송재봉 윤후덕 이기헌 이소영 이주희 임문영 임미애 전은수 최종성 강훈식 김병기 허영 박홍근 홍익표
    """,
    "국민의힘": """
        장동혁 한동훈 장예찬 정점식 송언석 김재섭 윤상현 강명구 오세훈 배현진 김석기 김종혁 이성권 박형수
        나경원 권성동 추경호 김기현 안철수 조경태 주호영 김민전 서지영 주진우 이진숙 김태규 권영세 신동욱
        김도읍 박수영 윤한홍 유상범 곽규택 김용태 박정훈 김예지 최수진 강승규 조배숙 김장겸 박충권 유용원
        임이자 김대식 성일종 권영진 이상휘 박성훈 박정하 윤재옥 이종배 임종득 정성국 정희용 조은희 최보윤
        최은석 최형두 이철규 김은혜 인요한 박덕흠
    """,
    "조국혁신당": """
        조국 신장식 황운하 차규근 서왕진 김선민 박은정 이해민 강경숙 백선희 김준형 정춘생 임명희
    """,
    "개혁신당": """
        이준석 천하람 이주영 이기인 김정철
    """,
}

_PA_GROUPS = ("더불어민주당", "국민의힘", "조국혁신당", "개혁신당")
_PA_CUE = {"더불어민주당": "더불어민주당", "조국혁신당": "조국혁신당", "개혁신당": "개혁신당",
           "국민의힘": "국민의힘", "민주당": "더불어민주당", "국힘": "국민의힘", "혁신당": "조국혁신당",
           "與": "더불어민주당", "野": "국민의힘", "여당": "더불어민주당", "야당": "국민의힘",
           "민주": "더불어민주당"}
# 긴 것부터(‘개혁신당’ 안의 ‘혁신당’, ‘더불어민주당’ 안의 ‘민주당’이 먼저 걸리지 않게).
# '민주'는 뒤에 조사·문장부호·공백이 올 때만('민주노총'·'민주주의' 제외), '야당역·야당동'은 제외.
_PA_CUE_RE = re.compile(
    r"(?<![가-힣])(?:(더불어민주당|조국혁신당|개혁신당|국민의힘|민주당|국힘|혁신당|여당|야당(?![역동]))|(與|野)"
    r"|(민주)(?=[도는가의와,·\s\"“”'‘’…]|$))")
# 정당 단서 바로 뒤에 오면 그 정당은 '대상'(목적어)이다 — 발언·행위 주체가 아니다.
# 따옴표(발언)를 사이에 두면 대상이 아니다 — '野 "보은 인사" 공세'는 野가 공세하는 쪽. 그래서 따옴표 자리는 ◇로 남긴다.
# '에서'('與에서도 기조 전환 요구')는 출처라 주체로 본다.
_PA_OBJECT_RE = re.compile(r"[ \t]*(?:을|를|에게|에는|에(?!서)|겨냥|향해|향한|비판|직격|저격|때리|맹폭|공격|공세|탓)")
_PA_POS = r"(?:의원|대표|원내대표|최고위원|수석대변인|대변인|사무총장|위원장|정책위의장|원내수석부대표|당대표|비대위원장|전\s?대표|전\s?의원|시장|지사|구청장|당협위원장|시당위원장|장관|총리)"
_PA_QUOTES = [("\"", "\""), ("“", "”"), ("'", "'"), ("‘", "’"), ("「", "」")]
_PA_LEARNED = None


def _pa_people():
    """명단 + DB 학습분(제목의 '정당 이름 + 직함' / '이름 + 정당 + 직함'이 2번 이상, 한 정당이 80% 이상).
    명단이 학습분보다 우선한다. 학습은 프로세스당 한 번."""
    global _PA_LEARNED
    if _PA_LEARNED is not None:
        return _PA_LEARNED
    people = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        cnt = {}
        pre = re.compile(r"(?<![가-힣])(더불어민주당|민주당|국민의힘|국힘|조국혁신당|혁신당|개혁신당|與|野)\s*([가-힣]{3})\s*" + _PA_POS)
        post = re.compile(r"(?<![가-힣])([가-힣]{3})\s*(더불어민주당|민주당|국민의힘|국힘|조국혁신당|혁신당|개혁신당)\s*" + _PA_POS)
        for (t,) in conn.execute("SELECT title FROM articles"):
            for m in pre.finditer(t or ""):
                cnt.setdefault(m.group(2), {}).setdefault(_PA_CUE[m.group(1)], set()).add(t)
            for m in post.finditer(t or ""):
                cnt.setdefault(m.group(1), {}).setdefault(_PA_CUE[m.group(2)], set()).add(t)
        conn.close()
        for name, by in cnt.items():
            if name[-1] in "시당군구도위청부회처원":
                continue
            n = {g: len(ts) for g, ts in by.items()}
            g = max(n, key=n.get)
            if n[g] >= 2 and n[g] / sum(n.values()) >= 0.8:
                people[name] = g
    except Exception as e:
        print(f"[warn] 정당 인물 학습 실패: {e}")
    for g, names in PARTY_PEOPLE.items():
        for name in names.split():
            people[name] = g
    _PA_LEARNED = people
    return people


def _pa_dequote(s):
    """따옴표 안(발언 내용)을 지운다. 닫히지 않은 따옴표는 끝까지."""
    out, i = [], 0
    while i < len(s):
        ch = s[i]
        close = next((c for o, c in _PA_QUOTES if o == ch), None)
        if close is None:
            out.append(ch)
            i += 1
            continue
        j = s.find(close, i + 1)
        if j == -1:
            break
        out.append("◇")
        i = j + 1
    return "".join(out)


def party_actor(title):
    """제목의 발언·행위 주체 정당(섹션 이름) 또는 None."""
    s = strip_media_tail(clean(title or ""))
    s = re.sub(r"^\s*(?:[\[\(<【][^\]\)>】]{0,20}[\]\)>】]\s*)+", "", s).strip()
    if not s:
        return None
    def cue(m):
        return _PA_CUE[m.group(1) or m.group(2) or m.group(3)]
    # ① 맨 앞 정당 단서
    m = _PA_CUE_RE.match(s)
    if m:
        return cue(m)
    # ② 맨 앞 사람(이름 [직함] [정당 직함] 다음에 쉼표·따옴표·대시·공백)
    m = re.match(r"([가-힣]{2,4})(\s*" + _PA_POS + r")?\s*", s)
    if m:
        rest = s[m.end():]
        m2 = _PA_CUE_RE.match(rest)
        if m2 and re.match(r"\s*" + _PA_POS, rest[m2.end():]):
            return cue(m2)                       # '서지영 국민의힘 의원 - …'
        if rest[:1] in ",\"“'‘-–—:…" or m.group(2):
            g = _pa_people().get(m.group(1))
            if g:
                return g
    # ③ 따옴표 밖 첫 정당 단서(목적어 제외)
    d = _pa_dequote(s)
    for m in _PA_CUE_RE.finditer(d):
        if _PA_OBJECT_RE.match(d, m.end()):
            continue
        return cue(m)
    return None


def party_actor_group(title, kws):
    """GROUP_ASSIGN_HOOK — 정당 섹션 기사만(‘기타 단독’ 등은 원본 규칙)."""
    if not any(KEYWORD_GROUPS.get(k, k) in _PA_GROUPS for k in kws):
        return None
    return party_actor(title)


GROUP_ASSIGN_HOOK = party_actor_group
