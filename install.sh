#!/bin/bash
# Confluence CLI 설치 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME"

echo "🚀 Confluence CLI 설치 중..."

# 파일 복사
cp "$SCRIPT_DIR/cf" "$INSTALL_DIR/cf"
cp "$SCRIPT_DIR/confluence_automation.py" "$INSTALL_DIR/confluence_automation.py"

# 설정 파일이 없으면 복사
if [ ! -f "$INSTALL_DIR/confluence_config.json" ]; then
    cp "$SCRIPT_DIR/confluence_config.example.json" "$INSTALL_DIR/confluence_config.json"
    echo "📝 설정 파일 생성됨: ~/confluence_config.json"
else
    echo "⚠️  설정 파일이 이미 존재합니다: ~/confluence_config.json (덮어쓰지 않음)"
fi

# 실행 권한 부여
chmod +x "$INSTALL_DIR/cf"

# PATH 설정 확인 및 추가
if ! grep -q 'export PATH="\$HOME:\$PATH"' ~/.zshrc 2>/dev/null; then
    echo 'export PATH="$HOME:$PATH"' >> ~/.zshrc
    echo "✅ PATH 설정 추가됨 (~/.zshrc)"
fi

echo ""
echo "✅ 설치 완료!"
echo ""
echo "📋 다음 단계:"
echo "  1. source ~/.zshrc  (또는 터미널 재시작)"
echo "  2. ~/confluence_config.json 파일에서 token 설정"
echo "     - Confluence > 프로필 > Personal Access Tokens에서 발급"
echo "  3. cf weekly 또는 cf release 명령어 사용"
echo ""
