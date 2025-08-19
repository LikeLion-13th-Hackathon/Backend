from django.shortcuts import render
from django.http import JsonResponse
from google import genai
from google.genai import types as genai_types
import os
from django.conf import settings
from rest_framework.views import APIView 
from rest_framework.response import Response
from rest_framework import status
from .serializers import ChatRequestSerializer, FeedbackClassifySerializer, TopicSerializer
from typing import Dict, List, Tuple
import re
import json
from .models import FeedbackTag, Feedback, Topic

DEFAULT_THREAD_ID = "default"

ROLE_GUIDES = {
    "store": """[ROLE=STORE]
- 가게 직원 시점으로 응답
- 바로 직전의 요청 내용과 관련된 대화 응답 3가지 한국어로 생성
- 이번 턴에는 오직 STORE 역할만 수행하고, USER 문장을 출력하지 말 것.""",
    "user": """[ROLE=USER]
- 고객 시점으로 응답
- 바로 직전의 요청 내용과 관련된 대화 응답 3가지 한국어로 생성
- 이번 턴에는 오직 USER 역할만 수행하고, STORE 문장을 출력하지 말 것."""
}

REVIEW_GUIDE = (
"규칙:\n"
"{review_top2}, {dietary_top2}, Spicy level-{spicy_top}와 관련된 대화 좀 더 많이 생성할 것"
)

# 키가 없으면 명시적 에러
GEMINI_API_KEY = getattr(settings, "GEMINI_API_KEY", None)
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in settings.")


MODEL_NAME = "gemini-2.0-flash"

def get_threads(session):
    if "chat_threads" not in session:
        session["chat_threads"] = {}
    if not session.session_key:
        session.save()
    return session["chat_threads"]

def ensure_thread(session, thread_id: str | None):
    threads = get_threads(session)
    tid = thread_id or DEFAULT_THREAD_ID
    if tid not in threads:
        threads[tid] = []
    return tid, threads[tid]

def set_thread(session, thread_id, history):
    threads = get_threads(session)
    threads[thread_id] = history
    session["chat_threads"] = threads
    session.modified = True

def delete_thread(session, thread_id):
    threads = get_threads(session)
    if thread_id in threads:
        del threads[thread_id]
        session["chat_threads"] = threads
        session.modified = True

def clear_all_threads(session):
    session["chat_threads"] = {}
    session.modified = True

def get_role(request):
    role = (request.data.get("role") or "store").strip().lower()
    if role not in ("store", "user"):
        role = "store"
    return role

def normalize_turn(turn):
    role = turn.get("role")
    parts = turn.get("parts", [])
    norm_parts = []
    for p in parts:
        if isinstance(p, dict) and "text" in p:
            norm_parts.append({"text": str(p["text"])})
        elif isinstance(p, str):
            norm_parts.append({"text": p})
    # 최소 1개 보장
    if not norm_parts:
        norm_parts = [{"text": ""}]
    return {"role": role, "parts": norm_parts}

def normalize_category(counts: Dict[str, int]) -> Dict[str, float]:
    total = sum(counts.values())
    return {k: (v / total if total > 0 else 0.0) for k, v in counts.items()}

def top_k_keys(d: dict, k: int):
    # 값(value) 내림차순, 동률이면 키 오름차순으로 안정적으로 선택
    return [key for key, _ in sorted(d.items(), key=lambda kv: (-kv[1], kv))[:k]]

class TopicListView(APIView):
    def get(self, request):
        category = request.query_params.get("category")
        qs = Topic.objects.all()
        if category:
            qs = qs.filter(category=category)
        serializer = TopicSerializer(qs, many=True)
        return Response(serializer.data)

class AiChatView(APIView):
    # 채팅 시작
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_user_input = serializer.validated_data["message"].strip()
        category = request.data.get("category")
        topic = request.data.get("topic")
        retry = bool(request.data.get("retry"))

        review_tags= {"Delicious": 42, "Clean": 18, "Recommended": 27, "Hard to find": 100, "Spacious": 12, "English spoken": 9}
        dietary_restrictions= {"Vegan": 8, "Pork-free": 20, "Beef-free": 4, "Nut-free": 2}
        spicy_level= {"Mild": 10, "Medium": 35, "Spicy": 15, "Very Spicy": 6}

        # 상위 k개 키
        review_top2 = top_k_keys(review_tags, 2)
        dietary_top2 = top_k_keys(dietary_restrictions, 2)
        spicy_top = top_k_keys(spicy_level, 1)

        # 첫 요청: category에 속하는 가게 입장에서 topic과 관련된 대화를 시작하는 3가지 한국어 대화 생성해.
        prompt = (
            '각 항목은 {korean, romanization, english_gloss} 필드를 포함해. '
            "romanization 필드는 라틴 알파벳(ASCII A-Z/a-z), 공백과 기본 구두점만 허용. 한글/숫자/기타 기호가 하나라도 포함되면 응답은 무효이며 즉시 재생성. "
            # "romanization와 english_gloss는 '영어'로만 출력. 한국어 절대 금지 "
            "romanization must use Latin letters only (ASCII A-Z/a-z), spaces, and basic punctuation. Do not include any Korean characters or digits. "
            "english_gloss must be in English (ASCII letters), no Korean. "
            '각 korean은 15자 이내. '
            f'각 대화는 {category}, 특히 {topic}과 매우 강한 연관성 '
            '플레이스홀더(OO, XX, [ ], ___, ( ), { })가 들어가는 응답 금지 '
            '가게의 특정 메뉴와 품목과 관련된 질문 금지 '
            "'fresh'=신선식품 "
        )

        # 역할 파라미터 수신
        role = get_role(request)
        role_guide = ROLE_GUIDES[role]
        review_guide = REVIEW_GUIDE.format(review_top2=review_top2, dietary_top2=dietary_top2, spicy_top=spicy_top)

        # 프론트에서 요청할 때 thread_id에 topic을 넣어줘야 함!
        thread_id = (request.data.get("thread_id") or DEFAULT_THREAD_ID).strip()
        thread_id, history = ensure_thread(request.session, thread_id)

        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # 히스토리에 최근 N턴만 저장
        recent_n_roles = 10
        trimmed = history[-recent_n_roles:] if len(history) > recent_n_roles else history
        contents = []

        contents = []
        # 재지시 문구 추가
        if retry:
            contents.append({"role": "user", "parts": [{"text": f"이전 출력과 다른 새로운 대화 3개를 {role} 입장에서 생성. 표현/내용 중복 금지."}]})
        contents.append({"role": "user", "parts": [{"text": role_guide}]}) # 가이드 먼저
        # contents.append({"role":"user","parts":[{"text": review_guide}]})
        contents.extend([normalize_turn(t) for t in trimmed]) # 과거 히스토리
        contents.append({"role": "user", "parts": [{"text": raw_user_input}]}) # 원문
        contents.append({"role": "user", "parts": [{"text": prompt}]}) # 출력 규칙

        response_schema = genai_types.Schema(
            type=genai_types.Type.ARRAY,
            items=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={
                    "korean": genai_types.Schema(type=genai_types.Type.STRING),
                    "romanization": genai_types.Schema(type=genai_types.Type.STRING),
                    "english_gloss": genai_types.Schema(type=genai_types.Type.STRING),
                },
                required=["korean", "romanization", "english_gloss"],
            )
        )
        
        # 모델 호출
        resp = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": response_schema,
            },
        )

        reply_text = (resp.text or "").strip() or ""

        parsed = getattr(resp, "parsed", None)
        if parsed is None:
            reply_text = (resp.text or "").strip() or ""
            try:
                parsed = json.loads(reply_text)
            except Exception:
                parsed = []

        dialogue = []
        for item in parsed:
            dialogue.append({
                "role": role,
                "korean": item.get("korean", ""),
                "romanization": item.get("romanization", ""),
                "english_gloss": item.get("english_gloss", ""),
            })

        # 히스토리 업데이트(반드시 role/parts의 원시 형태로 저장)
        history.append({"role": "user", "parts": [{"text": f"[{role.upper()}] {raw_user_input}"}]})
        history.append({"role": "user", "parts": [{"text": role_guide}]}) 
        # history.append({"role":"user","parts":[{"text": review_guide}]})
        history.append({"role": "user", "parts": [{"text": prompt}]})
        history.append({"role": "model", "parts": [{"text": reply_text}]})
        set_thread(request.session, thread_id, history)

        return Response(
            {
                "dialogue": dialogue,
                "history": history,
                "role": role,
                "used_prompt": prompt,
                "raw_user_input": raw_user_input,  
                "category": category,
                "topic": topic,
                "thread_id": thread_id,
            },
            status=status.HTTP_200_OK,
        )
    
    # 단일 스레드 삭제
    def delete(self, request):
        thread_id = (request.data.get("thread_id") or request.query_params.get("thread_id") or "").strip()
        if not thread_id:
            return Response({"detail": "thread_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        threads = get_threads(request.session)
        if thread_id not in threads:
            return Response({"detail": f"thread_id '{thread_id}' not found", "threads_index": list(threads.keys())}, status=status.HTTP_404_NOT_FOUND)

        delete_thread(request.session, thread_id)
        return Response({"detail": "deleted", "thread_id": thread_id, "threads_index": list(get_threads(request.session).keys())}, status=status.HTTP_200_OK)

# 전체 스레드 삭제 (채팅 종료)
class ClearAllThreadsView(APIView):
    def post(self, request):
        clear_all_threads(request.session)
        return Response({"detail": "all threads cleared", "threads_index": []}, status=status.HTTP_200_OK)

class FeedbackView(APIView):
    def build_tag_classify_prompt(self, allowed_pos: List[str], allowed_neg: List[str], allowed_neu: List[str], thumbs: bool, comment: str) -> str:
            pos_lines = "\n".join(f"- {t}" for t in allowed_pos) or "- (none)"
            neg_lines = "\n".join(f"- {t}" for t in allowed_neg) or "- (none)"
            neu_lines = "\n".join(f"- {t}" for t in allowed_neu) or "- (none)"

            # 같은 모델을 쓰되, 분류 지시만 제공. 발명 금지, 최대 3개, JSON 강제.
            return (
                "You are a tag classifier for AI response feedback.\n"
                "Choose up to 3 tags ONLY from the allowed lists.\n"
                "- Do NOT invent new tags or variants.\n"
                "- Prefer precision over recall. If unsure, choose fewer.\n"
                "- You may include both positive and negative, but the total must be ≤3.\n"
                "- If it doesn't fit, you may use neutral 'other' only when necessary.\n"
                "- If the user’s utterance is inappropriate (including profanity or vulgar language), categorize it as “spam.\n\n"
                f"Allowed positive tags:\n{pos_lines}\n\n"
                f"Allowed negative tags:\n{neg_lines}\n\n"
                f"Allowed neutral tags:\n{neu_lines}\n\n"
                "Input:\n"
                f"- thumbs: {str(thumbs).lower()}\n"
                f"- comment: \"\"\"{comment.strip()}\"\"\"\n\n"
            )
    def filter_and_limit_tags(self, result: Dict[str, List[str]], allowed_pos: List[str], allowed_neg: List[str], allowed_neu: List[str], limit: int = 3) -> List[str]:
        pos = [t for t in result.get("positive", []) if t in allowed_pos]
        neg = [t for t in result.get("negative", []) if t in allowed_neg]
        neu = [t for t in result.get("neutral", []) if t in allowed_neu]

        merged = []
        for t in pos + neg + neu:
            if t not in merged:
                merged.append(t)
        return merged[:limit]
    

    def post(self, request):
        # 로그인 필수 추가 permission_classes = [IsAuthenticated]

        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # 1) 입력 검증
        ser = FeedbackClassifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        thumbs = ser.validated_data["thumbs"]
        comment = ser.validated_data["comment"]

        # 2) 허용 태그 목록 로드 (Admin에서 미리 등록된 값들)
        allowed = list(Tag.objects.values("id", "polarity", "tag"))
        allowed_pos = [t["tag"] for t in allowed if t["polarity"] == "positive"]
        allowed_neg = [t["tag"] for t in allowed if t["polarity"] == "negative"]
        allowed_neu = [t["tag"] for t in allowed if t["polarity"] == "neutral"]
        name_to_id = {t["tag"]: t["id"] for t in allowed}
                
        prompt = self.build_tag_classify_prompt(allowed_pos, allowed_neg, allowed_neu, thumbs, comment)
        
        response_schema = genai_types.Schema(
            type=genai_types.Type.OBJECT,
            properties={
                "positive": genai_types.Schema(
                    type=genai_types.Type.ARRAY,
                    items=genai_types.Schema(type=genai_types.Type.STRING),
                ),
                "negative": genai_types.Schema(
                    type=genai_types.Type.ARRAY,
                    items=genai_types.Schema(type=genai_types.Type.STRING),
                ),
                "neutral": genai_types.Schema(
                    type=genai_types.Type.ARRAY,
                    items=genai_types.Schema(type=genai_types.Type.STRING),
                ),
            },
            required=["positive", "negative", "neutral"],
        )

        # 3) 모델 호출
        resp = client.models.generate_content(
            model=MODEL_NAME,
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            config={
                "response_mime_type": "application/json",
                "response_schema": response_schema,
            },
        )

        text = (getattr(resp, "text", None) or "").strip()
        try:
            data = json.loads(text) if text else {}
        except Exception:
            data = {}

        result = {
            "positive": data.get("positive", []) if isinstance(data, dict) else [],
            "negative": data.get("negative", []) if isinstance(data, dict) else [],
            "neutral": data.get("neutral", []) if isinstance(data, dict) else [],
        }

        # 4) 화이트리스트 검증 + 최대 3개 제한
        chosen_names = self.filter_and_limit_tags(result, allowed_pos, allowed_neg, allowed_neu, limit=3)
        chosen_ids = [name_to_id[n] for n in chosen_names if n in name_to_id]

        # 5) Feedback에 저장
        fb = Feedback.objects.create(
            user=request.user,
            thumbs=thumbs,
            comment=comment[:500],
        )
        if chosen_ids:
            fb.tags.set(chosen_ids)

        # 6) 응답
        return Response(
            {
                "id": fb.id,
                "user": fb.user.id if fb.user_id else None,
                "thumbs": fb.thumbs,
                "feedback_comment": fb.comment,
                "auto_tags": [{"id": name_to_id[n], "tag": n} for n in chosen_names if n in name_to_id],
                "tags": [{"id": t.id, "polarity": t.polarity, "tag": t.tag} for t in fb.tags.all()],
                "raw_result": result, 
            },
            status=status.HTTP_201_CREATED,
        )

