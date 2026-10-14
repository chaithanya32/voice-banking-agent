
from faster_whisper import WhisperModel


_model = None


def get_model():
    global _model

    if _model is None:
        _model = WhisperModel(
            "base",
            device="cpu",
            compute_type="int8",
        )

    return _model


def transcribe_audio(audio_path: str) -> str:
    """Convert an audio file into text."""

    model = get_model()

    segments, _ = model.transcribe(
    audio_path,
    language=None,
    beam_size=5,
    vad_filter=True,
    condition_on_previous_text=False,
    initial_prompt=(
    "Voice banking commands in English, Hindi, and Hinglish. "
    "Registered recipients: Ravi Kumar, Priya Sharma, Rahul Reddy. "
    "Amounts may be spoken in rupees, Hindi, or Hinglish. "
    "Examples: Pay 500 rupees to Ravi Kumar. "
    "Ravi Kumar ko paanch sau rupaye bhejo. "
    "Ravi Kumar ko 500 rupaye bhejna. "
    "Yes, no, haan, nahi, cancel the payment."
),
)


    text = " ".join(
        segment.text.strip()
        for segment in segments
    ).strip()

    return text
