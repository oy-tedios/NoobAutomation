#!/bin/bash
# Confluence CLI 설치 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Confluence CLI 설치 중..."

# 설정 파일이 없으면 생성
if [ ! -f "$SCRIPT_DIR/confluence_config.json" ]; then
    cat > "$SCRIPT_DIR/confluence_config.json" << 'EOF'
{
  "confluence_url": "https://oyitsm.cj.net/confluence",
  "token": "여기에_Personal_Access_Token_입력",
  "weekly_report": {
    "parent_page_id": "193994798",
    "template_id": "197558273",
    "space_key": "CJOLIVE"
  },
  "release_note": {
    "ios": {
      "parent_page_id": "318845645",
      "template_id": "322732035",
      "space_key": "CJOLIVE"
    },
    "android": {
      "parent_page_id": "318845652",
      "template_id": "322732033",
      "space_key": "CJOLIVE"
    }
  }
}
EOF
    echo "📝 설정 파일 생성됨: $SCRIPT_DIR/confluence_config.json"
else
    echo "⚠️  설정 파일이 이미 존재합니다 (덮어쓰지 않음)"
fi

# 실행 권한 부여
chmod +x "$SCRIPT_DIR/cf"

# PATH 설정 확인 및 추가
if ! grep -q "export PATH=\"$SCRIPT_DIR:\$PATH\"" ~/.zshrc 2>/dev/null; then
    echo "export PATH=\"$SCRIPT_DIR:\$PATH\"" >> ~/.zshrc
    echo "✅ PATH 설정 추가됨 (~/.zshrc)"
fi

echo ""
echo "✅ 설치 완료!"
echo ""
echo "📋 다음 단계:"
echo "  1. source ~/.zshrc  (또는 터미널 재시작)"
echo "  2. $SCRIPT_DIR/confluence_config.json 파일에서 token 설정"
echo "     - Confluence > 프로필 > Personal Access Tokens에서 발급"
echo "  3. cf weekly 또는 cf release 명령어 사용"
echo ""
