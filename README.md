# Mapin — Backend

Mapin은 전통시장 안내와 한국어 대화 연습 서비스입니다. 시장, 가게, 메뉴 정보를 보여 주고, 방문 전에 AI 가게 직원과 짧은 한국어 대화를 연습할 수 있습니다.

- LIKELION 중앙대학교 해커톤, 2025.07–08
- 6명: 백엔드 2, 프론트엔드 2, PM 1, 디자인 1
- 이 저장소: Django REST API

## 기술 스택

| 분야 | 스택 |
| --- | --- |
| 언어 / 프레임워크 | Python 3.12, Django 5.2, Django REST Framework |
| 인증 | JWT (`djangorestframework-simplejwt`) |
| 데이터베이스 | MySQL (AWS RDS, PyMySQL). 로컬에서는 EC2 SSH 터널로 접속 |
| 스토리지 | AWS S3 (boto3, presigned URL 업로드) |
| AI | Google Gemini (`gemini-2.0-flash`, `gemini-2.0-flash-lite`), `google-genai` |
| OCR | NAVER CLOVA OCR (영수증 모델) |
| 기타 | Pillow (이미지 처리), RapidFuzz (주소 유사도), Poetry |

## 주요 기능

### 1. AI 대화 상대 (`ai/views.py`)

사용자가 카테고리, 주제(예: 신선식품 구매), 가게를 고르면 Gemini가 선택한 역할(가게 직원 또는 손님)의 답변 **3개**를 제안합니다.

- **구조화된 출력.** JSON 응답 스키마로 모델을 호출합니다. 답변마다 `korean`, `romanization`, `english_gloss` 세 필드가 있습니다.
- **가게 컨텍스트.** 선택한 가게의 메뉴를 **최대 3개** 프롬프트에 넣고, 그 메뉴만 언급하게 합니다. 등록된 메뉴가 없으면 특정 메뉴를 언급하지 못하게 합니다.
- **대화 기록.** 대화 스레드는 Django 세션에 저장합니다. 요청마다 **최근 기록 10개**를 함께 보냅니다.
- **재생성.** `retry: true`로 요청하면 이전 답변과 겹치지 않는 새 답변 3개를 만들게 합니다.

### 2. 사용자 평가를 프롬프트에 반영하는 피드백 루프 (`ai/views.py`, `ai/models.py`)

1. 사용자가 AI 답변에 좋아요/싫어요와 코멘트를 남깁니다.
2. `gemini-2.0-flash-lite`가 피드백을 **최대 3개 태그**로 분류합니다. 태그는 Django Admin에 등록한 목록(긍정/부정/중립) 안에서만 고릅니다. 목록에 없는 태그는 서버에서 버립니다.
3. 피드백과 태그를 저장합니다.
4. 대화 요청마다 태그 사용 횟수를 집계합니다. **긍정 상위 3개**는 강화하고 **부정 상위 3개**는 보완하라는 지시를 프롬프트에 넣습니다. 중립 태그는 제외합니다.

### 3. 영수증으로 가게 찾기 (`receipts/views.py`)

사용자가 영수증 사진을 올리면 어느 시장 가게의 영수증인지 찾습니다.

1. **1MB 이하 JPEG로 압축.** 이미지를 RGB JPEG로 바꿉니다. 원본 해상도에서 품질을 85 → 50으로 먼저 낮춥니다. 그래도 1MB를 넘으면 해상도를 90% → 50%로 줄이며 품질 단계를 다시 시도합니다.
2. **OCR.** JPEG를 CLOVA OCR로 보냅니다. 가게 이름, 주소, 결제 일시, 총액을 OCR 원본 결과와 함께 저장하고, 이미지는 S3에 올립니다.
3. **주소 정규화.** `normalize_address`가 바깥 괄호, 괄호 안 내용, 쉼표와 마침표를 지우고 공백을 정리합니다. `서울특별시`, `서울시`는 `서울`로 바꿉니다.
4. **유사도 비교.** 모든 가게에 대해 영수증 주소를 도로명 주소, 지번 주소와 각각 비교합니다. 점수는 RapidFuzz의 `max(ratio, partial_ratio)`이고, 둘 중 높은 점수를 그 가게의 점수로 씁니다.
5. 점수 **상위 5개 가게**를 반환합니다.

### 기타 API

회원가입/로그인(JWT), 시장, 가게(필터·정렬), 메뉴, 가게 리뷰(태그·좋아요), 프로필 이미지(S3 presigned URL), 리워드 포인트.

## 프로젝트 구조

```
config/     설정, 루트 URL
accounts/   사용자, JWT 인증, 리워드
ai/         AI 대화, 피드백 태그 분류, 주제
receipts/   영수증 OCR, 가게 매칭
markets/ stores/ menu/   시장 데이터 (+ 데이터 적재 커맨드)
reviews/    가게 리뷰, 태그, 좋아요
image/      프로필 이미지 업로드 (S3)
```

## 실행 방법

### 요구 사항

- Python 3.12
- Poetry
- MySQL

### 1. 설치

```bash
poetry install
poetry run pip install google-genai rapidfuzz
```

`google-genai`와 `rapidfuzz`는 코드에서 쓰지만 `pyproject.toml`에 없어서 따로 설치합니다.

### 2. `secrets.json` 설정

설정값은 프로젝트 루트의 `secrets.json`에서 읽습니다(git에서 제외됨). 필요한 키는 다음과 같습니다.

| 키 | 용도 |
| --- | --- |
| `SECRET_KEY` | Django secret key |
| `DB_NAME`, `USER`, `DB_PW`, `HOST`, `PORT` | MySQL 연결 |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | S3 |
| `X_OCR_SECRET` | CLOVA OCR |
| `GEMINI_API_KEY` | Gemini |
| `EC2_HOST`, `EC2_USER`, `EC2_KEY_PATH`, `RDS_HOST` | SSH 터널 (`run_with_tunnel.py`에서만 사용) |

### 3. 마이그레이션과 데이터 적재

```bash
poetry run python manage.py migrate
poetry run python manage.py load_market_data   # 시장 데이터 생성
poetry run python manage.py load_stores        # S3의 가게 CSV 적재
poetry run python manage.py load_menus         # S3의 메뉴 CSV 적재
```

`load_stores`와 `load_menus`는 프로젝트 S3 버킷의 CSV 파일을 읽습니다.

### 4. 실행

```bash
poetry run python manage.py runserver
```

EC2 SSH 터널(로컬 포트 3307)로 RDS에 접속하려면 Django 명령을 래퍼로 실행합니다.

```bash
poetry run python run_with_tunnel.py runserver
```
