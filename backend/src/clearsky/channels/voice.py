"""Voice notes: speech-to-text (STT_PROVIDER) and Hindi voice replies (TTS_PROVIDER=polly).

STT providers:
  transcribe  Amazon Transcribe batch job on S3 (MEDIA_BUCKET), polled ≤ TRANSCRIBE_TIMEOUT_S (90 s)
  openai      any OpenAI-compatible POST {base}/audio/transcriptions (STT_MODEL_ID, STT_API_KEY or LLM_API_KEY)
  none        voice notes get a "please type" reply
"""

from __future__ import annotations

import re
import struct
import time
import uuid
from typing import Any

import boto3
import httpx

from clearsky.config import get_optional_secret, get_settings, presigned_get_url
from clearsky.logging import get_logger

log = get_logger(child="voice")
OPENAI_DEFAULT_BASE = "https://api.openai.com/v1"


class VoiceUnavailable(RuntimeError):
    """STT is not configured (STT_PROVIDER=none) or not usable."""


class VoiceTooLong(ValueError):
    pass


def ogg_duration_seconds(data: bytes) -> float | None:
    """Duration of an Ogg Opus/Vorbis file from the last page's granule position (48 kHz for Opus)."""
    idx = data.rfind(b"OggS")
    if idx < 0 or len(data) < idx + 14:
        return None
    granule = struct.unpack_from("<q", data, idx + 6)[0]
    if granule <= 0:
        return None
    rate = 48000
    if b"vorbis" in data[:200]:
        vorbis = data.find(b"\x01vorbis")
        if vorbis >= 0 and len(data) >= vorbis + 16:
            rate = struct.unpack_from("<I", data, vorbis + 12)[0] or 48000
    return round(granule / rate, 2)


def check_length(data: bytes) -> float | None:
    seconds = ogg_duration_seconds(data)
    if seconds is not None and seconds > get_settings().max_voice_seconds:
        raise VoiceTooLong(f"{seconds:.0f}s")
    return seconds


def transcribe(data: bytes, msg_id: str, mime_type: str = "audio/ogg") -> str:
    s = get_settings()
    check_length(data)
    if s.stt_provider == "transcribe":
        return _transcribe_aws(data, msg_id)
    if s.stt_provider == "openai":
        return _transcribe_openai(data, mime_type)
    raise VoiceUnavailable("STT_PROVIDER=none")


def _job_name(msg_id: str) -> str:
    return "clearsky-" + re.sub(r"[^0-9a-zA-Z._-]", "-", msg_id)[:150] + "-" + uuid.uuid4().hex[:6]


def _transcribe_aws(data: bytes, msg_id: str) -> str:
    s = get_settings()
    if not s.media_bucket:
        raise VoiceUnavailable("MEDIA_BUCKET is not set")
    s3 = boto3.client("s3", region_name=s.aws_region)
    key = f"media/in/{msg_id}.ogg"
    s3.put_object(Bucket=s.media_bucket, Key=key, Body=data, ContentType="audio/ogg")
    tr: Any = boto3.client("transcribe", region_name=s.aws_region)  # language/voice come from config
    name = _job_name(msg_id)
    out_key = f"transcripts/{name}.json"
    tr.start_transcription_job(
        TranscriptionJobName=name,
        Media={"MediaFileUri": f"s3://{s.media_bucket}/{key}"},
        MediaFormat="ogg",
        LanguageCode=s.transcribe_language,
        OutputBucketName=s.media_bucket,
        OutputKey=out_key,
    )
    deadline = time.monotonic() + s.transcribe_timeout_s
    while time.monotonic() < deadline:
        job = tr.get_transcription_job(TranscriptionJobName=name)["TranscriptionJob"]
        status = job["TranscriptionJobStatus"]
        if status == "COMPLETED":
            import json

            body = s3.get_object(Bucket=s.media_bucket, Key=out_key)["Body"].read()
            transcripts = json.loads(body)["results"]["transcripts"]
            return " ".join(t["transcript"] for t in transcripts).strip()
        if status == "FAILED":
            raise VoiceUnavailable(job.get("FailureReason", "transcription failed"))
        time.sleep(1.5)
    raise VoiceUnavailable("transcription timed out")


def _transcribe_openai(data: bytes, mime_type: str) -> str:
    s = get_settings()
    if not s.stt_model_id:
        raise VoiceUnavailable("STT_PROVIDER=openai needs STT_MODEL_ID")
    key = get_optional_secret("STT_API_KEY") or get_optional_secret("LLM_API_KEY")
    if not key:
        raise VoiceUnavailable("STT_PROVIDER=openai needs STT_API_KEY (or LLM_API_KEY)")
    base = (s.stt_base_url or s.llm_base_url or OPENAI_DEFAULT_BASE).rstrip("/")
    ext = "ogg" if "ogg" in mime_type else mime_type.split("/")[-1]
    resp = httpx.post(
        f"{base}/audio/transcriptions",
        headers={"Authorization": f"Bearer {key}"},
        data={"model": s.stt_model_id, "language": "hi"},
        files={"file": (f"voice.{ext}", data, mime_type)},
        timeout=60,
    )
    if resp.status_code >= 400:
        raise VoiceUnavailable(f"STT API {resp.status_code}")
    return str(resp.json().get("text", "")).strip()


_EMOJI = re.compile("[\U0001f300-\U0001faff☀-➿✅❌]")


def synthesize(text: str, msg_id: str) -> str | None:
    """Polly mp3 → S3 → presigned URL (1 h). None when TTS is off or MEDIA_BUCKET is missing."""
    s = get_settings()
    if s.tts_provider != "polly" or not s.media_bucket:
        return None
    speech = _EMOJI.sub("", text).strip()
    if not speech:
        return None
    polly: Any = boto3.client("polly", region_name=s.aws_region)
    audio = polly.synthesize_speech(
        Text=speech[:2900],
        VoiceId=s.polly_voice,
        Engine=s.polly_engine,
        LanguageCode="hi-IN",
        OutputFormat="mp3",
    )["AudioStream"].read()
    s3 = boto3.client("s3", region_name=s.aws_region)
    key = f"media/out/{msg_id}.mp3"
    s3.put_object(Bucket=s.media_bucket, Key=key, Body=audio, ContentType="audio/mpeg")
    return presigned_get_url(s.media_bucket, key, 3600)
