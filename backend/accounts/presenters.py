def user_payload(user) -> dict:
    profile = getattr(user, "profile", None)
    return {
        "id": str(user.public_id),
        "email": user.email,
        "phone": user.phone_e164,
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "surname": profile.surname if profile else None,
        "date_of_birth": profile.date_of_birth.isoformat() if profile else None,
        "created_at": user.created_at.isoformat(),
    }


def session_payload(session) -> dict:
    d = session.device
    return {
        "started_at": session.created_at.isoformat(),
        "last_activity_at": session.last_activity_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
        "auth_method": session.auth_method,
        "device": {
            "id": d.id,
            "label": d.label,
            "device_type": d.device_type,
            "browser": d.browser,
            "os": d.os,
        },
    }
