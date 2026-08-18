# 완니 (วันนี้)

매일 아침 8시(KST), 카카오톡 "나와의 채팅방"으로 태국어 표현 카드 3장을 자동 발송하는 개인 서비스.

- 콘텐츠: `data/expressions.csv` (day × slot, 한국어·태국어·독음·단어분해)
- 렌더: `render.py` — headless Chrome으로 1080×1350 PNG (Pillow는 태국어 성조 셰이핑 불가라 배제)
- 발송: `kakao.py` — 이미지 업로드 API + `talk/memo/default/send` 피드 템플릿
- 스케줄: `.github/workflows/daily.yml` — 07:40 KST 기동 → 08:00 정각 발송
- 토큰: 리프레시 토큰을 `TOKEN_KEY`로 AES 암호화해 `state/tokens.enc`에 보관, 회전 시 봇이 자동 커밋

## Phase 0 — 최초 1회 설정 (약 30분)

1. **카카오 앱 생성** — [developers.kakao.com](https://developers.kakao.com) → 내 애플리케이션 → 애플리케이션 추가
   - [앱 설정 > 앱 키]에서 **REST API 키** 복사
   - [제품 설정 > 카카오 로그인] **활성화**, Redirect URI에 `http://localhost:8899/callback` 등록
   - [제품 설정 > 카카오 로그인 > 동의항목] **카카오톡 메시지 전송(talk_message)** 을 "선택 동의"로 설정
   - [앱 설정 > 보안]에서 Client Secret 상태 확인 (사용 시 함께 준비)
2. **토큰 발급** — 이 리포 루트에서:
   ```bash
   KAKAO_REST_KEY=<REST키> TOKEN_KEY=<.env의 키> python3 get_token.py
   ```
   브라우저 동의 → `tokens.json`(로컬) + `state/tokens.enc` 생성.
3. **GitHub Secrets 등록** — `KAKAO_REST_KEY`, `TOKEN_KEY`, (있으면) `KAKAO_CLIENT_SECRET`
4. **테스트 발송** — Actions 탭 → daily-send → Run workflow. 카드 3장 도착 확인.
5. `state/tokens.enc` 커밋·푸시.

## 로컬 사용

```bash
python3 render.py --day 8            # 카드만 렌더 (out/)
python3 daily.py --dry-run           # 오늘자 렌더만
python3 daily.py --day 1             # 즉시 발송 (tokens.json 필요)
```
