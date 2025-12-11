# services/storage_supabase.py
import uuid
import io
from supabase_client import supabase

BUCKET = "skin-scans"  # đổi nếu bạn đặt bucket khác

def upload_image_to_supabase(uid: str, image_bytes: bytes):
    """
    Upload raw JPEG bytes to Supabase Storage.
    Returns (visit_id, public_url)
    """
    if not isinstance(image_bytes, (bytes, bytearray)):
        raise TypeError("upload_image_to_supabase expects bytes")

    visit_id = str(uuid.uuid4())
    path = f"{uid}/{visit_id}.jpg"

    try:
        # Try uploading raw bytes (some SDK versions accept bytes)
        res = supabase.storage.from_(BUCKET).upload(path=path, file=image_bytes, file_options={"content-type":"image/jpeg"})
    except Exception:
        # Fallback to file-like object if SDK requires it
        buf = io.BytesIO(image_bytes)
        res = supabase.storage.from_(BUCKET).upload(path=path, file=buf, file_options={"content-type":"image/jpeg"})

    public = supabase.storage.from_(BUCKET).get_public_url(path)
    if isinstance(public, dict):
        url = public.get("publicUrl") or public.get("public_url")
    else:
        url = public

    return visit_id, url
