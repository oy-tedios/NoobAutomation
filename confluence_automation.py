#!/usr/bin/env python3
"""
Confluence 자동화 스크립트
- 주간업무보고 페이지 생성
- iOS 릴리즈노트 페이지 생성
"""

import json
import re
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path

warnings.filterwarnings("ignore", message="urllib3 v2 only supports")

import requests

# 설정 파일 경로
CONFIG_PATH = Path(__file__).parent / "confluence_config.json"


def load_config():
    """설정 파일 로드"""
    if not CONFIG_PATH.exists():
        print(f"❌ 설정 파일이 없습니다: {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    if config["token"] == "여기에_Personal_Access_Token_입력":
        print("❌ confluence_config.json에서 token을 설정해주세요!")
        sys.exit(1)

    return config


class ConfluenceAPI:
    """Confluence Server API 클라이언트"""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })

    def get_page(self, page_id: str) -> dict:
        """페이지 정보 조회"""
        url = f"{self.base_url}/rest/api/content/{page_id}"
        resp = self.session.get(url, params={"expand": "body.storage,version"})
        resp.raise_for_status()
        return resp.json()

    def get_children(self, page_id: str) -> list:
        """하위 페이지 목록 조회"""
        url = f"{self.base_url}/rest/api/content/{page_id}/child/page"
        resp = self.session.get(url, params={"limit": 100})
        resp.raise_for_status()
        return resp.json().get("results", [])

    def get_template(self, template_id: str) -> dict:
        """템플릿 정보 조회 (experimental API 사용)"""
        url = f"{self.base_url}/rest/experimental/template/{template_id}"
        resp = self.session.get(url, params={"expand": "body"})
        resp.raise_for_status()
        return resp.json()

    def create_page(self, space_key: str, parent_id: str, title: str, body: str) -> dict:
        """새 페이지 생성"""
        url = f"{self.base_url}/rest/api/content"
        data = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "ancestors": [{"id": parent_id}],
            "body": {
                "storage": {
                    "value": body,
                    "representation": "storage"
                }
            }
        }
        resp = self.session.post(url, json=data)
        resp.raise_for_status()
        return resp.json()

    def find_or_create_page(self, space_key: str, parent_id: str, title: str, body: str = "") -> dict:
        """페이지 찾기 또는 생성"""
        children = self.get_children(parent_id)
        for child in children:
            if child["title"] == title:
                return child

        # 없으면 생성
        return self.create_page(space_key, parent_id, title, body if body else "<p></p>")


def get_week_info(target_date: datetime = None, weeks_ahead: int = 1) -> dict:
    """주간 정보 계산 (월~금 기준, 목요일 기준으로 월 결정)"""
    if target_date is None:
        target_date = datetime.now()

    # N주 후 기준으로 계산
    target_date = target_date + timedelta(days=7 * weeks_ahead)

    # 이번 주 월요일 찾기
    monday = target_date - timedelta(days=target_date.weekday())
    friday = monday + timedelta(days=4)
    thursday = monday + timedelta(days=3)

    # 목요일 기준으로 월 결정
    base_month = thursday.month
    base_year = thursday.year

    # 해당 월의 첫 번째 월요일 찾기
    first_of_month = datetime(base_year, base_month, 1)
    days_until_monday = (7 - first_of_month.weekday()) % 7
    if first_of_month.weekday() == 0:
        first_monday = first_of_month
    else:
        first_monday = first_of_month + timedelta(days=days_until_monday)

    # 첫 번째 월요일이 다음 달이면 이전 주를 1주차로 계산
    if first_monday.month != base_month:
        first_monday = first_monday - timedelta(days=7)

    # 주차 계산
    week_num = ((monday - first_monday).days // 7) + 1
    if week_num <= 0:
        week_num = 1

    return {
        "year": base_year,
        "month": base_month,
        "week_num": week_num,
        "monday": monday,
        "friday": friday,
        "month_folder": f"{base_year % 100}년 {base_month:02d}월",
        "title": f"{week_num}주차 ({monday.month:02d}/{monday.day:02d}-{friday.month:02d}/{friday.day:02d})",
    }


def get_weekday_dates(monday: datetime) -> list:
    """월~금 날짜와 요일 리스트 반환"""
    days = ["월", "화", "수", "목", "금"]
    result = []
    for i, day in enumerate(days):
        date = monday + timedelta(days=i)
        result.append(f"{day} ({date.month:02d}/{date.day:02d})")
    return result


def create_weekly_report(api: ConfluenceAPI, config: dict):
    """주간업무보고 페이지 생성"""
    print("📋 주간업무보고 페이지 생성 중...")

    weekly_config = config["weekly_report"]
    space_key = weekly_config["space_key"]

    # 다음 미생성 주차 찾기 (최대 52주까지 탐색)
    weeks_ahead = 1
    week_info = None

    while weeks_ahead <= 52:
        week_info = get_week_info(weeks_ahead=weeks_ahead)

        # 연도별 페이지 찾기 (예: 커머스플랫폼개발팀 - 2026년 주간 업무)
        year_page_title = f"커머스플랫폼개발팀 - {week_info['year']}년 주간 업무"
        parent_children = api.get_children(weekly_config["parent_page_id"])

        year_page = None
        for child in parent_children:
            if child["title"] == year_page_title:
                year_page = child
                break

        if not year_page:
            # 연도 페이지가 없으면 아직 생성 안 된 주차
            break

        # 월별 폴더 확인
        year_page_id = year_page["id"]
        year_children = api.get_children(year_page_id)

        month_folder = None
        for child in year_children:
            if child["title"] == week_info["month_folder"]:
                month_folder = child
                break

        if not month_folder:
            # 월 폴더가 없으면 아직 생성 안 된 주차
            break

        # 해당 주차 페이지가 있는지 확인
        month_children = api.get_children(month_folder["id"])
        page_exists = False
        for child in month_children:
            if child["title"] == week_info["title"]:
                page_exists = True
                break

        if not page_exists:
            # 해당 주차가 없으면 이걸 생성
            break

        # 이미 있으면 다음 주 확인
        weeks_ahead += 1

    if weeks_ahead > 52:
        print("❌ 생성할 주차를 찾을 수 없습니다 (52주 이상 탐색)")
        return

    print(f"📅 생성할 주차: {week_info['title']} ({weeks_ahead}주 후)")

    # 연도별 페이지 찾기 또는 생성
    year_page_title = f"커머스플랫폼개발팀 - {week_info['year']}년 주간 업무"
    parent_children = api.get_children(weekly_config["parent_page_id"])

    year_page = None
    for child in parent_children:
        if child["title"] == year_page_title:
            year_page = child
            break

    if not year_page:
        print(f"📁 '{year_page_title}' 페이지를 생성합니다...")
        year_page = api.create_page(
            space_key,
            weekly_config["parent_page_id"],
            year_page_title,
            "<p></p>"
        )

    year_page_id = year_page["id"]

    # 월별 폴더 찾기 또는 생성
    month_folder = api.find_or_create_page(
        space_key,
        year_page_id,
        week_info["month_folder"]
    )
    print(f"📁 월 폴더: {week_info['month_folder']}")

    # 템플릿 가져오기
    template = api.get_template(weekly_config["template_id"])
    template_body = template.get("body", {}).get("storage", {}).get("value", "")

    # 템플릿 내 날짜 치환
    monday = week_info["monday"]
    friday = week_info["friday"]
    last_friday = monday - timedelta(days=3)  # 지난주 금요일

    # 날짜 포맷팅
    def fmt_date(d):
        return f"{d.month:02d}/{d.day:02d}"

    # 템플릿의 MM/dd 또는 숫자 날짜 패턴을 실제 날짜로 치환
    body = template_body

    # 지난주 금요일
    body = re.sub(r"지난주 금\s*\(MM/dd\)", f"지난주 금({fmt_date(last_friday)})", body)
    body = re.sub(r"지난주 금\s*\(\d{2}/\d{2}\)", f"지난주 금({fmt_date(last_friday)})", body)

    # 월~금 날짜 치환 (MM/dd 패턴 또는 기존 숫자 패턴)
    # 금요일은 "지난주 금"과 구분하기 위해 negative lookbehind 사용
    days = ["월", "화", "수", "목", "금"]
    for i, day in enumerate(days):
        date = monday + timedelta(days=i)
        if day == "금":
            # "지난주 금"이 아닌 경우만 치환
            body = re.sub(rf"(?<!지난주 )(?<!지난주)금\s*\(MM/dd\)", f"금 ({fmt_date(date)})", body)
            body = re.sub(rf"(?<!지난주 )(?<!지난주)금\s*\(\d{{2}}/\d{{2}}\)", f"금 ({fmt_date(date)})", body)
        else:
            # MM/dd 문자열 패턴
            body = re.sub(rf"{day}\s*\(MM/dd\)", f"{day} ({fmt_date(date)})", body)
            # 기존 숫자 패턴
            body = re.sub(rf"{day}\s*\(\d{{2}}/\d{{2}}\)", f"{day} ({fmt_date(date)})", body)

    # 페이지 생성
    new_page = api.create_page(
        space_key,
        month_folder["id"],
        week_info["title"],
        body
    )

    page_url = f"{config['confluence_url']}/pages/viewpage.action?pageId={new_page['id']}"
    print(f"✅ 생성 완료: {week_info['title']}")
    print(f"🔗 {page_url}")


def get_latest_version(api: ConfluenceAPI, parent_page_id: str, platform: str = "ios") -> tuple:
    """최신 버전 조회"""
    children = api.get_children(parent_page_id)

    if platform == "ios":
        version_pattern = re.compile(r"iOS\s+(\d+)\.(\d+)\.(\d+)-\d+")
    else:
        # Android v3.45.0-260331 형식 지원
        version_pattern = re.compile(r"Android\s+v?(\d+)\.(\d+)\.(\d+)-\d+")

    latest = (0, 0, 0)

    for child in children:
        match = version_pattern.search(child["title"])
        if match:
            version = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            if version > latest:
                latest = version

    return latest


def increment_version(version: tuple, increment_type: str = "minor") -> str:
    """버전 증가"""
    major, minor, patch = version

    if increment_type == "major":
        return f"{major + 1}.0.0"
    elif increment_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif increment_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        return f"{major}.{minor + 1}.0"


def create_release_note(api: ConfluenceAPI, config: dict, platform: str = "ios", version: str = None):
    """릴리즈노트 페이지 생성"""
    platform_name = "iOS" if platform == "ios" else "Android"
    print(f"📱 {platform_name} 릴리즈노트 페이지 생성 중...")

    release_config = config["release_note"][platform]
    space_key = release_config["space_key"]
    parent_id = release_config["parent_page_id"]

    # 버전 결정
    if not version:
        latest = get_latest_version(api, parent_id, platform)
        if latest == (0, 0, 0):
            print("❌ 기존 버전을 찾을 수 없습니다. 버전을 직접 입력해주세요.")
            version = input("버전 입력 (예: 3.49.0): ").strip()
        else:
            version = increment_version(latest, "minor")
            print(f"📌 최신 버전: {latest[0]}.{latest[1]}.{latest[2]}")
            print(f"📌 새 버전: {version}")
            confirm = input("이 버전으로 생성할까요? (Y/n/직접입력): ").strip()
            if confirm.lower() == "n":
                return
            elif confirm and confirm.lower() != "y":
                version = confirm

    # 날짜 계산: 기준점에서 버전 차이만큼 2주씩 증가
    if platform == "ios":
        base_version = (3, 48, 0)
        base_date = datetime(2026, 5, 4)  # iOS 3.48.0 배포일 (월요일)
    else:
        base_version = (3, 46, 0)
        base_date = datetime(2026, 4, 6)  # Android v3.46.0-260406

    # 버전 파싱
    version_parts = tuple(map(int, version.split(".")))

    # 마이너 버전 차이 계산 (패치 버전은 날짜 변경 없음)
    minor_diff = version_parts[1] - base_version[1]

    # 메이저 버전이 다르면 계산 조정 필요할 수 있음
    if version_parts[0] != base_version[0]:
        # 메이저 버전 변경 시 수동 입력 요청
        print(f"⚠️  메이저 버전이 변경되었습니다. 배포 날짜를 직접 입력해주세요.")
        date_input = input("배포 날짜 (YYMMDD): ").strip()
        date_str = date_input
    else:
        release_date = base_date + timedelta(weeks=2 * minor_diff)
        date_str = release_date.strftime("%y%m%d")

    # Android는 v 접두사 사용
    if platform == "android":
        title = f"{platform_name} v{version}-{date_str}"
    else:
        title = f"{platform_name} {version}-{date_str}"
    print(f"📅 배포 예정일: {date_str}")

    # 이미 존재하는지 확인
    children = api.get_children(parent_id)
    for child in children:
        if child["title"] == title:
            print(f"⚠️  이미 존재하는 페이지입니다: {title}")
            page_url = f"{config['confluence_url']}/pages/viewpage.action?pageId={child['id']}"
            print(f"🔗 {page_url}")
            return

    # 템플릿 가져오기
    template = api.get_template(release_config["template_id"])
    template_body = template.get("body", {}).get("storage", {}).get("value", "")

    # 버전 치환 (템플릿 내 버전 패턴)
    body = template_body

    # 1. 버전명 치환: 3.XX.0 → 3.49.0
    body = body.replace("3.XX.0", version)

    # 2. 지라 쿼리 버전 치환: "배포버전" ~ "3.XX.0*" → "배포버전" ~ "3.49.0*"
    body = re.sub(r'"배포버전"\s*~\s*"3\.XX\.0\*"', f'"배포버전" ~ "{version}*"', body)

    # 3. 플랫폼명 치환 (Android 템플릿에 iOS가 있을 경우 대비)
    if platform == "android":
        body = body.replace("iOS", "Android")

    # 페이지 생성
    new_page = api.create_page(
        space_key,
        parent_id,
        title,
        body
    )

    page_url = f"{config['confluence_url']}/pages/viewpage.action?pageId={new_page['id']}"
    print(f"✅ 생성 완료: {title}")
    print(f"🔗 {page_url}")


def main():
    """메인 함수"""
    config = load_config()
    api = ConfluenceAPI(config["confluence_url"], config["token"])

    print("=" * 50)
    print("🚀 Confluence 자동화 도구")
    print("=" * 50)
    print()
    print("1. 주간업무보고 생성")
    print("2. iOS 릴리즈노트 생성")
    print("3. 종료")
    print()

    choice = input("선택: ").strip()

    if choice == "1":
        create_weekly_report(api, config)
    elif choice == "2":
        create_release_note(api, config)
    elif choice == "3":
        print("👋 종료합니다.")
    else:
        print("❌ 잘못된 선택입니다.")


if __name__ == "__main__":
    # CLI 인자로 직접 실행 가능
    if len(sys.argv) > 1:
        config = load_config()
        api = ConfluenceAPI(config["confluence_url"], config["token"])

        if sys.argv[1] == "weekly":
            create_weekly_report(api, config)
        elif sys.argv[1] == "release":
            platform = sys.argv[2] if len(sys.argv) > 2 else "ios"
            version = sys.argv[3] if len(sys.argv) > 3 else None
            create_release_note(api, config, platform, version)
        else:
            print(f"❌ 알 수 없는 명령: {sys.argv[1]}")
            print("사용법: python confluence_automation.py [weekly|release] [ios|android] [version]")
    else:
        main()
