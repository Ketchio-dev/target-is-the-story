# 제출 체크리스트 — LexHack 2026

마감 **2026-09-27 17:00 EDT**. 규정: 작동하는 프로토타입 + 영상 **3분 이하** + 저장소 +
**AI 사용 고지**. 심사 Real-World Impact 25 % · Technical 25 % · UX(비법률가 기준) 20 % · Innovation.

## 1. 제출 전 저장소 확인

- [ ] 새 폴더에 클론해서 `python3 src/parse_reports.py && python3 src/parse_standards.py &&
      python3 src/analyze.py && python3 src/export_web.py` 가 **그대로 돈다**
      (데이터가 커밋돼 있어야 한다 — 원격이 죽어도 심사위원 손에서 돌아야 한다)
- [ ] `python3 src/check.py` → **28/28**
- [ ] `python3 src/sabotage.py` → **23/23 검출, 놓침 0**
- [ ] `web/index.html` 을 **더블클릭**해서 열린다 (서버 없이)
- [ ] README 의 수치가 `analyze.py` 출력과 같다 (검사가 본다 — 손으로 확인할 필요 없다)

## 2. 영상

- [ ] `_workflow/video/hackathon-video/out/target-is-the-story.mp4` — **2:41** (상한 3:00 ✓)
- [ ] **끝까지 본다.** 검사가 못 보는 것: 말투, 그림이 말과 맞는지
- [ ] 업로드 (YouTube 또는 Vimeo). **게시는 사람이 한다**
- [ ] 공개 범위 확인 — 비공개면 심사위원이 못 본다

## 3. UX 항목 (배점 20 %, 비법률가 기준)

- [ ] 법률 용어를 모르는 사람이 페이지를 열었을 때 **첫 화면에서 요지가 잡히는지** 확인
- [ ] 24시간 대 240일 대비가 스크롤 없이 보이는지

## 4. Devpost 폼

- [ ] tagline — `devpost.md` 의 A/B/C 중 택 1
- [ ] 본문 — `devpost.md` 붙여넣기 (맨 위 안내 블록은 지운다)
- [ ] **Inspiration 을 사람이 채웠는지 확인.** 비어 있으면 제출하지 않는다
- [ ] 저장소 링크
- [ ] 영상 링크
- [ ] **AI 사용 고지** — `ai-disclosure.md` (필수 항목이다)
- [ ] 라이브 링크 (GitHub Pages 로 `web/` 게시)

## 5. 사람만 할 수 있는 것

- [ ] Inspiration 문단
- [ ] tagline 택 1
- [ ] 영상 시청 후 업로드
- [ ] 저장소 커밋·푸시
- [ ] 제출 버튼

## 6. 제출 후

- [ ] 제출물 링크가 로그아웃 상태에서 열리는지 확인
- [ ] 마감 전까지는 몇 번이든 고칠 수 있다
