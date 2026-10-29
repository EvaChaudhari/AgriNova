"""Unified Voice / Vision / Text Chat Receptor Endpoint.

Implements strict architectural separation:
1. Deterministic hydrological (FAO-56) & hazard state engines run first.
2. Multimodal translation layer (STT/Vision/TTS).
3. Conversational AI grounded by authoritative ICAR Senior Agricultural Scientist prompt.
"""

import uuid
from typing import Any
from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
import httpx

from app.core.config import settings
from app.core.database import get_db
from app.models.profile import DeviceProfile
from app.models.plot import FarmPlot
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import ChatReceptorResponse
from app.services.context_builder import build_agricultural_context
from app.services.speech_service import SpeechService
from app.services.vision_service import LeafVisionService

router = APIRouter(prefix="/chat", tags=["Conversational Chat Receptor"])


ICAR_SYSTEM_PROMPT = """You are the Senior Chief Agronomist and ICAR Principal Scientist serving smallholder farmers in India via the Krishi Mitra digital platform.

CORE OPERATIONAL PRINCIPLES:
1. STRICT HAZARD COMPLIANCE: Deterministic hydrological and hazard engine directives take absolute precedence over farmer requests.
   - If STORM_FLOOD_MODE is active: You must categorically REFUSE and HALT any recommendation to spray chemical pesticides, fungicides, or apply top-dress fertilizers (urea/DAP). Advise clearing drainage furrows and monitoring field slopes.
   - If EL_NINO_DROUGHT_MODE is active: You must FORBID surface flood irrigation. Insist on night-time drip/sprinkler cycles and straw/biomass mulching.
2. ZERO-HALLUCINATION IPM POLICY: Never fabricate unverified pesticide mixtures. Recommend only Central Insecticides Board (CIB&RC) registered active ingredients with exact dilution (e.g. per 15-litre knapsack sprayer tank). Prioritize biological, mechanical, and cultural IPM first.
3. EMPATHETIC VERNACULAR COMMUNICATION: Respond respectfully, practically, and concisely in the farmer's preferred language. Use familiar Indian farming terminology (e.g., 'Kisan bhai', 'tanki' for 15L sprayer, 'bori' for 45kg bag) without scientific jargon.
4. ACTIONABLE CLARITY: Keep responses under 4 short, structured bullet points or sentences that are easy to hear when read aloud over voice TTS.
"""


def generate_deterministic_agri_response(
    query: str,
    context: dict[str, Any],
    language: str = "hi",
    vision_condition: str | None = None,
) -> str:
    """Deterministic scientific response generator when external LLM is offline or unconfigured.

    Guarantees zero-failure and strict hazard directive compliance.
    """
    hazard_state = context.get("hazard", {}).get("current_state", "NORMAL_MODE")
    restrictions = context.get("hazard", {}).get("enforced_restrictions", [])
    crop = context.get("crop_name", "कपास")
    stage = context.get("growth_stage", "फूल आने की अवस्था")
    hydro = context.get("hydrology", {})
    trigger = hydro.get("trigger", "HOLD")
    rec_depth = hydro.get("recommended_depth_mm", 0.0)

    # 1. Enforce STORM_FLOOD_MODE override
    if hazard_state == "STORM_FLOOD_MODE" or "HALT_ALL_CHEMICAL_SPRAYING" in restrictions:
        if language == "hi":
            return (
                f"सावधान किसान भाई! आगामी 24 घंटों में भारी वर्षा का अलर्ट है। "
                f"इस समय किसी भी कीटनाशक या खाद (यूरिया) का छिड़काव बिल्कुल न करें, वह पानी में बह जाएगा। "
                f"तुरंत खेत की मेड़ों के जल-निकास नाले खोलें ताकि पानी जमा न हो।"
            )
        elif language == "te":
            return (
                f"హెచ్చరిక రైతు సోదరా! రాబోయే 24 గంటల్లో భారీ వర్ష సూచన ఉంది. "
                f"ఇప్పుడు ఎలాంటి రసాయన మందులు లేదా ఎరువులు పిచికారీ చేయవద్దు. "
                f"మురుగు నీరు నిల్వ ఉండకుండా వెంటనే కాలువలు తెరవండి."
            )
        elif language == "mr":
            return (
                f"सावधान शेतकरी बंधू! पुढील 24 तासांत मुसळधार पावसाचा इशारा आहे. "
                f"सध्या कोणतीही रासायनिक औषध फवारणी किंवा खत देऊ नका. "
                f"पाण्याचा निचरा होण्यासाठी शेतातील चर त्वरित मोकळे करा."
            )
        else:
            return (
                f"Storm Alert: Heavy rainfall predicted within 24 hours. "
                f"Strictly halt all chemical pesticide spraying and fertilizer application immediately. "
                f"Clear all drainage furrows to prevent root asphyxiation."
            )

    # 2. Enforce EL_NINO_DROUGHT_MODE override
    if hazard_state == "EL_NINO_DROUGHT_MODE" or "FORBID_SURFACE_FLOOD_IRRIGATION" in restrictions:
        if language == "hi":
            return (
                f"किसान भाई, भूजल स्तर गहरा होने और कम बारिश के कारण खुला पानी (बाढ़ सिंचाई) देना मना है। "
                f"केवल रात के समय ड्रिप से पानी दें ताकि वाष्पीकरण न हो। "
                f"नमी बचाने के लिए कतारों के बीच पुआल या सूखी घास की पलवार (मल्चिंग) बिछाएं।"
            )
        elif language == "te":
            return (
                f"రైతు సోదరా, భూగర్భ జలాలు తగ్గడం వల్ల వరద పద్ధతిలో నీరు పెట్టకూడదు. "
                f"కేవలం రాత్రి వేళల్లో మాత్రమే డ్రిప్ ద్వారా నీటిని అందించండి. "
                f"తేమ ఆవిరి కాకుండా పంట వరుసల మధ్య ఎండుగడ్డితో మల్చింగ్ చేయండి."
            )
        else:
            return (
                f"Drought Advisory: Surface flood irrigation is forbidden due to critical aquifer depletion. "
                f"Operate drip irrigation exclusively during night hours and apply straw mulching to conserve root moisture."
            )

    # 3. Handle Leaf Pathology Vision Diagnosis
    if vision_condition and "Healthy" not in vision_condition:
        if language == "hi":
            return (
                f"पत्ती की जांच में {vision_condition} के लक्षण पाए गए हैं। "
                f"पहले 5% नीम तेल (NSKE) 50 मिली प्रति 15 लीटर टंकी में मिलाकर छिड़कें। "
                f"यदि प्रकोप अधिक हो, तो इमामेक्टिन बेंजोएट 5% SG (8 ग्राम प्रति टंकी) का प्रयोग करें।"
            )
        elif language == "te":
            return (
                f"ఆకు పరిశీలనలో {vision_condition} గమనించబడింది. "
                f"మొదట 5% వేప నూనెను 15 లీటర్ల ట్యాంకుకు 50 మి.లీ చొప్పున కలిపి పిచికారీ చేయండి. "
                f"ఉధృతి ఎక్కువగా ఉంటే సిఫార్సు చేసిన పురుగుమందు వాడండి."
            )
        else:
            return (
                f"Foliar diagnostic detected: {vision_condition}. "
                f"Initiate IPM with 5% Neem Seed Kernel Extract (50ml / 15L knapsack). "
                f"If pest pressure exceeds ETL, apply registered CIB-approved bio-pesticide."
            )

    # 4. Standard FAO-56 Hydrological Recommendation
    if trigger == "IRRIGATE":
        if language == "hi":
            return (
                f"आपकी {crop} की फसल ({stage}) में मिट्टी की नमी कम हो गई है। "
                f"आज {rec_depth} मिमी सिंचाई की आवश्यकता है। अपनी ड्रिप प्रणाली को 2 से 2.5 घंटे चलाएं।"
            )
        elif language == "te":
            return (
                f"మీ {crop} పంటకు నేలలో తేమ తగ్గింది. నేడు {rec_depth} మి.మీ నీటి తడులు అవసరం. "
                f"డ్రిప్ ద్వారా తగినంత సమయం నీరు అందించండి."
            )
        else:
            return (
                f"Hydrological engine status: IRRIGATE. "
                f"Soil root depletion has reached RAW threshold. Apply {rec_depth} mm irrigation today."
            )
    elif trigger == "DRAIN":
        if language == "hi":
            return f"खेत में अत्यधिक नमी है। किसी भी सिंचाई को रोकें और अतिरिक्त पानी बाहर निकालने की व्यवस्था करें।"
        else:
            return "Hydrological engine status: DRAIN. Soil is oversaturated. Pause all irrigation."
    else:
        if language == "hi":
            return (
                f"आपकी {crop} की फसल में नमी का स्तर बिल्कुल संतुलित है। "
                f"अगले 2 दिनों तक सिंचाई की कोई आवश्यकता नहीं है।"
            )
        elif language == "te":
            return f"మీ {crop} పంటలో తేమ సమతుల్యంగా ఉంది. ప్రస్తుతానికి నీరు పెట్టవలసిన అవసరం లేదు."
        else:
            return f"Hydrological status: HOLD. Soil root moisture is within safe buffer. Irrigation not required today."


async def call_llm_grounded_response(
    query_text: str,
    context: dict[str, Any],
    history: list[dict[str, str]],
    language: str,
) -> str:
    """Call Gemini API or Agri-SLM with full agricultural context injection."""
    if not settings.GEMINI_API_KEY:
        return generate_deterministic_agri_response(query_text, context, language)

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
        
        system_instructions = (
            f"{ICAR_SYSTEM_PROMPT}\n\n"
            f"CURRENT LIVE AGRICULTURAL CONTEXT:\n"
            f"- Device ID: {context.get('device_id')}\n"
            f"- Farmer Name: {context.get('farmer_name')}\n"
            f"- Preferred Language: {language}\n"
            f"- Crop: {context.get('crop_name')} ({context.get('variety')}), Stage: {context.get('growth_stage')}, DAS: {context.get('days_after_sowing')}\n"
            f"- Groundwater: {context.get('groundwater', {}).get('depth_mbgl')} mbgl ({context.get('groundwater', {}).get('source')})\n"
            f"- Soil Texture: {context.get('soil_texture')}, Nutrients: {context.get('soil_nutrients')}\n"
            f"- Weather Forecast: Temp Max {context.get('weather', {}).get('t_max')}C, 24h Rain: {context.get('weather', {}).get('rainfall_24h_mm')} mm\n"
            f"- Satellite Indices: NDVI {context.get('satellite', {}).get('ndvi')}, NDWI {context.get('satellite', {}).get('ndwi')}\n"
            f"- Hydrological Status: Trigger {context.get('hydrology', {}).get('trigger')}, Rec Depth: {context.get('hydrology', {}).get('recommended_depth_mm')} mm\n"
            f"- ACTIVE HAZARD STATE: {context.get('hazard', {}).get('current_state')}\n"
            f"- ENFORCED RESTRICTIONS: {context.get('hazard', {}).get('enforced_restrictions')}\n"
            f"- ACTIONABLE DIRECTIVES: {context.get('hazard', {}).get('actionable_directives')}\n"
        )

        contents = []
        for turn in history[-5:]:
            role = "user" if turn["sender"] == "USER" else "model"
            contents.append({"role": role, "parts": [{"text": turn["text"]}]})

        contents.append({"role": "user", "parts": [{"text": f"Farmer Question: {query_text}\nPlease answer in language: {language}"}]})

        payload = {
            "system_instruction": {"parts": [{"text": system_instructions}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,  # Low temperature for deterministic agronomic adherence
                "maxOutputTokens": 300,
            }
        }

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                reply = data["candidates"][0]["content"]["parts"][0]["text"]
                return reply.strip()
    except Exception:
        pass

    return generate_deterministic_agri_response(query_text, context, language)


@router.post("/receptor", response_model=ChatReceptorResponse)
async def chat_receptor_endpoint(
    request: Request,
    db: Session = Depends(get_db),
) -> ChatReceptorResponse:
    """Unified voice, vision, and text chat receptor endpoint.

    Handles multipart/form-data with file uploads or application/json payloads.
    Resolves conversational memory, grounds context, executes engines, and responds in voice/text.
    """
    content_type = request.headers.get("content-type", "")

    device_id: str = ""
    session_id: str | None = None
    query_text: str | None = None
    language: str | None = None
    audio_bytes: bytes | None = None
    image_bytes: bytes | None = None

    if "multipart/form-data" in content_type:
        form = await request.form()
        device_id = str(form.get("device_id", "")).strip()
        raw_session_id = form.get("session_id")
        if raw_session_id and str(raw_session_id).strip() and str(raw_session_id).strip() != "new":
            session_id = str(raw_session_id).strip()
        query_text = str(form.get("query_text", "")).strip() or None
        language = str(form.get("language", "")).strip() or None

        audio_entry = form.get("audio_file")
        if hasattr(audio_entry, "read"):
            audio_bytes = await audio_entry.read()  # type: ignore

        image_entry = form.get("image_file")
        if hasattr(image_entry, "read"):
            image_bytes = await image_entry.read()  # type: ignore
    else:
        # JSON body payload
        try:
            body = await request.json()
        except Exception:
            body = {}
        device_id = str(body.get("device_id", "")).strip()
        raw_session_id = body.get("session_id")
        if raw_session_id and str(raw_session_id).strip() and str(raw_session_id).strip() != "new":
            session_id = str(raw_session_id).strip()
        query_text = body.get("query_text")
        language = body.get("language")

    if not device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field 'device_id'.",
        )

    # 1. Resolve Device Profile
    profile = db.query(DeviceProfile).filter(DeviceProfile.device_id == device_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' is not onboarded. Call /api/v1/bootstrap/onboard first.",
        )

    target_lang = language or profile.preferred_language or "hi"

    # 2. Multimodal Speech Transcription (STT)
    if audio_bytes and len(audio_bytes) > 0:
        transcribed_text = await SpeechService.transcribe_audio(audio_bytes, target_lang)
        if transcribed_text:
            query_text = f"{query_text} {transcribed_text}".strip() if query_text else transcribed_text

    # 3. Multimodal Leaf Vision Diagnosis
    vision_condition = None
    vision_details = ""
    if image_bytes and len(image_bytes) > 0:
        diag = await LeafVisionService.diagnose_leaf(image_bytes, crop_hint="Cotton")
        vision_condition = diag.condition
        vision_details = (
            f"[Visual Symptom Analysis: {diag.condition} (Confidence: {diag.confidence * 100:.1f}%). "
            f"Symptoms: {', '.join(diag.symptoms)}. IPM: {', '.join(diag.ipm_recommendations[:2])}]"
        )
        query_text = f"{query_text} {vision_details}".strip() if query_text else vision_details

    if not query_text:
        query_text = "फसल की स्थिति और सिंचाई सलाह दीजिए।" if target_lang == "hi" else "Provide crop status and irrigation advisory."

    # 4. Conversational Session Resumption or Creation
    chat_session: ChatSession | None = None
    if session_id:
        chat_session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.device_id == device_id).first()

    if not chat_session:
        # Create new chat session with a fresh UUID
        new_session_id = str(uuid.uuid4())
        chat_session = ChatSession(
            id=new_session_id,
            device_id=device_id,
            title=f"Consultation - {query_text[:40]}",
        )
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)

    # 5. Load Session Turn History (Last 5 messages)
    history_records = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == chat_session.id)
        .order_by(ChatMessage.id.desc())
        .limit(5)
        .all()
    )
    history = []
    for msg in reversed(history_records):
        history.append({"sender": msg.sender, "text": msg.query_text})
        if msg.response_text:
            history.append({"sender": "ASSISTANT", "text": msg.response_text})

    # 6. Assemble Live Agricultural Context Packet
    active_plot = db.query(FarmPlot).filter(FarmPlot.device_id == device_id, FarmPlot.is_active == True).first()
    context_packet = await build_agricultural_context(db, profile, active_plot)
    context_dict = context_packet.to_dict()

    # 7. Ground Agri-SLM / Gemini LLM
    reply_text = await call_llm_grounded_response(query_text, context_dict, history, target_lang)

    # 8. Synthesize Speech (TTS)
    audio_base64_url = await SpeechService.synthesize_speech(reply_text, target_lang)

    # 9. Persist Turn to Chat History
    chat_msg = ChatMessage(
        session_id=chat_session.id,
        sender="USER",
        query_text=query_text,
        response_text=reply_text,
        audio_url=audio_base64_url[:60] + "..." if audio_base64_url else None,
        system_context_snapshot=context_dict,
        hazard_state=context_dict.get("hazard", {}).get("current_state"),
    )
    db.add(chat_msg)
    db.commit()

    return ChatReceptorResponse(
        session_id=chat_session.id,
        reply_text=reply_text,
        audio_base64_url=audio_base64_url,
        hazard_state=context_dict.get("hazard", {}).get("current_state", "NORMAL_MODE"),
        injected_context=context_dict,
    )

