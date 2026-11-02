"""Proactive Farmer Notification & Advisory Alert Service.

Generates timely hazard alerts, irrigation refill notices, and roadmap checkpoint reminders
localized in the farmer's preferred regional language (Hindi, Marathi, Telugu, English).
"""

from datetime import date, datetime, timezone
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.models.workflows import FarmerNotification

logger = logging.getLogger("agrinova.notifications")


class NotificationService:
    """Localized alert generator and notification store manager."""

    LOCALIZED_TEMPLATES: dict[str, dict[str, dict[str, str]]] = {
        "WEATHER_HAZARD": {
            "hi": {
                "title": "चेतावनी: भारी वर्षा का पूर्वानुमान ({rainfall_mm} मिमी)",
                "body": "अगले 24 घंटों में भारी बारिश की संभावना है। कृपया तुरंत खेत की जलनिकासी नालियों को साफ करें और कीटनाशक छिड़काव रोक दें।",
            },
            "mr": {
                "title": "धोका इशारा: मुसळधार पावसाचा अंदाज ({rainfall_mm} मिमी)",
                "body": "पुढील २४ तासांत मुसळधार पावसाची शक्यता आहे. शेतातील पाण्याचा निचरा करण्यासाठी चर मोकळे करा आणि औषध फवारणी थांबवा.",
            },
            "te": {
                "title": "హెచ్చరిక: భారీ వర్ష సూచన ({rainfall_mm} మి.మీ)",
                "body": "రాబోయే 24 గంటల్లో భారీ వర్షం కురిసే అవకాశం ఉంది. దయచేసి పొలంలో నీటి పారుదల కాలువలను శుభ్రం చేయండి మరియు మందుల పిచికారీని నిలిపివేయండి.",
            },
            "en": {
                "title": "Warning: Heavy Rainfall Forecast ({rainfall_mm} mm)",
                "body": "Heavy precipitation expected in next 24 hours. Clear field drainage channels immediately and suspend all pesticide/foliar spraying.",
            },
        },
        "IRRIGATION_DUE": {
            "hi": {
                "title": "सिंचाई की आवश्यकता: मिट्टी की नमी कम है",
                "body": "फसल की जड़ क्षेत्र में पानी की कमी हो गई है। फसल को पानी के तनाव से बचाने के लिए तुरंत सिंचाई करें।",
            },
            "mr": {
                "title": "पाणी देण्याची वेळ: जमिनीतील ओलावा संपला आहे",
                "body": "पिकाच्या मुळांच्या कार्यक्षेत्रातील ओलावा कमी झाला आहे. पाण्याचा ताण टाळण्यासाठी त्वरित पिकास पाणी द्यावे.",
            },
            "te": {
                "title": "నీటిపారుదల అవసరం: నేలలో తేమ తగ్గింది",
                "body": "మొక్కల వేరు ప్రాంతంలో నీటి కొరత ఏర్పడింది. పంట ఎండిపోకుండా వెంటనే నీటిపారుదల అందించండి.",
            },
            "en": {
                "title": "Irrigation Due: Soil Moisture Deficit",
                "body": "Root zone water depletion has exceeded the readily available threshold. Schedule irrigation to prevent yield loss.",
            },
        },
        "ROADMAP_CHECKPOINT": {
            "hi": {
                "title": "महत्वपूर्ण कृषि कार्य: {checkpoint_title}",
                "body": "आपकी फसल के लिए '{checkpoint_title}' का समय आ गया है ({target_date})। आवश्यक खाद एवं कीट प्रबंधन की तैयारी करें।",
            },
            "mr": {
                "title": "महत्त्वाचे शेती काम: {checkpoint_title}",
                "body": "आपल्या पिकासाठी '{checkpoint_title}' ची वेळ आली आहे ({target_date}). खत व्यवस्थापन आणि योग्य कृती करा.",
            },
            "te": {
                "title": "ముఖ్యమైన వ్యవసాయ పని: {checkpoint_title}",
                "body": "మీ పంట కోసం '{checkpoint_title}' సమయం వచ్చింది ({target_date}). అవసరమైన ఎరువులు మరియు సస్యరక్షణ చర్యలు చేపట్టండి.",
            },
            "en": {
                "title": "Scheduled Agronomic Task: {checkpoint_title}",
                "body": "Time for '{checkpoint_title}' on {target_date}. Prepare required inputs and perform stage-specific field operations.",
            },
        },
    }

    @classmethod
    def create_hazard_alert(
        cls,
        db: Session,
        device_id: str,
        plot_id: Optional[int],
        rainfall_mm: float,
        language: str = "hi",
    ) -> FarmerNotification:
        """Create high-priority storm/flood hazard alert."""
        lang = language.lower() if language.lower() in ("hi", "mr", "te", "en") else "hi"
        tmpl = cls.LOCALIZED_TEMPLATES["WEATHER_HAZARD"][lang]

        title = tmpl["title"].format(rainfall_mm=round(rainfall_mm, 1))
        body = tmpl["body"].format(rainfall_mm=round(rainfall_mm, 1))

        notif = FarmerNotification(
            device_id=device_id,
            plot_id=plot_id,
            notification_type="WEATHER_HAZARD",
            priority="URGENT" if rainfall_mm >= 75.0 else "HIGH",
            title=title,
            body=body,
            language=lang,
            channel="IN_APP",
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        logger.info("Created WEATHER_HAZARD alert %d for device %s", notif.id, device_id)
        return notif

    @classmethod
    def create_irrigation_alert(
        cls,
        db: Session,
        device_id: str,
        plot_id: Optional[int],
        language: str = "hi",
    ) -> FarmerNotification:
        """Create irrigation due alert."""
        lang = language.lower() if language.lower() in ("hi", "mr", "te", "en") else "hi"
        tmpl = cls.LOCALIZED_TEMPLATES["IRRIGATION_DUE"][lang]

        notif = FarmerNotification(
            device_id=device_id,
            plot_id=plot_id,
            notification_type="IRRIGATION_DUE",
            priority="HIGH",
            title=tmpl["title"],
            body=tmpl["body"],
            language=lang,
            channel="IN_APP",
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    @classmethod
    def create_checkpoint_reminder(
        cls,
        db: Session,
        device_id: str,
        plot_id: Optional[int],
        checkpoint_title: str,
        target_date: date,
        language: str = "hi",
    ) -> FarmerNotification:
        """Create roadmap milestone reminder."""
        lang = language.lower() if language.lower() in ("hi", "mr", "te", "en") else "hi"
        tmpl = cls.LOCALIZED_TEMPLATES["ROADMAP_CHECKPOINT"][lang]

        title = tmpl["title"].format(checkpoint_title=checkpoint_title, target_date=target_date.isoformat())
        body = tmpl["body"].format(checkpoint_title=checkpoint_title, target_date=target_date.isoformat())

        notif = FarmerNotification(
            device_id=device_id,
            plot_id=plot_id,
            notification_type="ROADMAP_CHECKPOINT",
            priority="ROUTINE",
            title=title,
            body=body,
            language=lang,
            channel="IN_APP",
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    @classmethod
    def list_notifications(
        cls,
        db: Session,
        device_id: str,
        unread_only: bool = False,
    ) -> list[FarmerNotification]:
        """Fetch notifications ordered by creation date descending."""
        query = db.query(FarmerNotification).filter(FarmerNotification.device_id == device_id)
        if unread_only:
            query = query.filter(FarmerNotification.is_read == False)
        return query.order_by(FarmerNotification.created_at.desc(), FarmerNotification.id.desc()).all()

    @classmethod
    def mark_as_read(
        cls,
        db: Session,
        notification_id: int,
        device_id: Optional[str] = None,
    ) -> FarmerNotification:
        """Mark notification as read."""
        query = db.query(FarmerNotification).filter(FarmerNotification.id == notification_id)
        if device_id:
            query = query.filter(FarmerNotification.device_id == device_id)
        notif = query.first()
        if not notif:
            raise ValueError(f"Notification {notification_id} not found.")

        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notif)
        return notif

