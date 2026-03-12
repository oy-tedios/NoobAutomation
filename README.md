# Confluence CLI

Confluence 페이지 자동 생성 도구

## 기능

- `cf weekly` : 주간업무보고 페이지 생성 (다음 미생성 주차 자동 탐색)
- `cf release` : iOS 릴리즈노트 생성
- `cf release-android` : Android 릴리즈노트 생성

## 설치

```bash
git clone https://github.com/oy-tedios/NoobAutomation.git
cd NoobAutomation
./install.sh
source ~/.zshrc
```

### Personal Access Token 설정

1. Confluence 접속: https://oyitsm.cj.net/confluence
2. 우측 상단 프로필 > 설정 > Personal Access Tokens
3. 토큰 생성 후 복사
4. `confluence_config.json` 파일에서 `token` 값 수정

```json
{
  "token": "여기에_발급받은_토큰_붙여넣기",
  ...
}
```

## 사용법

### 주간업무보고

```bash
cf weekly
```

- 다음 주 주간업무보고 페이지 생성
- 이미 생성된 주차는 건너뛰고 다음 미생성 주차 자동 탐색
- 월이 바뀌면 월 폴더 자동 생성

### 릴리즈노트

#### iOS
```bash
cf release          # 최신 버전 +0.1.0 자동 계산
cf release 3.50.0   # 버전 직접 지정
```

#### Android
```bash
cf release-android          # 최신 버전 +0.1.0 자동 계산
cf release-android 3.47.0   # 버전 직접 지정
```

## 요구사항

- Python 3
- requests 라이브러리 (`pip3 install requests`)

## 파일 구조

```
NoobAutomation/
├── cf                          # CLI 명령어
├── confluence_automation.py    # 메인 스크립트
└── confluence_config.json      # 설정 파일 (install.sh 실행 시 생성, git 제외)
```
