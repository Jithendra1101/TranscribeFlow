"""
summarize.py  –  Reusable summarization module using T5-base (Hugging Face)
T5-base gives noticeably better summaries than T5-small while staying lightweight.
Can also be run directly as a standalone demo script.
"""

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

# t5-base: ~250 MB, same architecture as t5-small but 3× more parameters.
# Better abstraction and coherence than t5-small, still fast on CPU.
MODEL_NAME = "t5-base"
MAX_INPUT_TOKENS = 512

# Lazy-loaded model and tokenizer
_tokenizer = None
_model = None


def _load_model():
    """Load and cache the T5-base tokenizer and model."""
    global _tokenizer, _model
    if _tokenizer is None or _model is None:
        print(f"⏳ Loading {MODEL_NAME} from Hugging Face (first run may take a moment)...")
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
        _model.eval()
        print("✅ T5-base model ready.")
    return _tokenizer, _model


def summarize_text(text: str, max_length: int = 150, min_length: int = 40) -> str:
    """
    Summarize *text* using the T5-base model.

    Args:
        text:       The input text to summarize.
        max_length: Maximum token length of the generated summary.
        min_length: Minimum token length of the generated summary.

    Returns:
        Summary string, or an empty string if input is blank.
    """
    if not text or not text.strip():
        return ""

    # T5 requires the 'summarize: ' task prefix
    clean_text = "summarize: " + " ".join(text.split())

    # If input is very short, relax min_length to avoid redundant padding
    word_count = len(clean_text.split())
    effective_min = min(min_length, max(10, word_count // 3))

    tokenizer, model = _load_model()

    inputs = tokenizer(
        clean_text,
        return_tensors="pt",
        max_length=MAX_INPUT_TOKENS,
        truncation=True,
    )

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_length=max_length,
            min_length=effective_min,
            length_penalty=2.0,
            num_beams=4,
            no_repeat_ngram_size=3,   # prevents copying n-grams verbatim
            early_stopping=True,
        )

    return tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()


# ---------------------------------------------------------------------------
# Standalone demo – only runs when executed directly: python summarize.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    demo_text = """
    The increase in global temperatures has led to more frequent and severe weather events,
    posing a significant threat to ecosystems and human societies. One of the major impacts
    of climate change is the rise in sea levels, which results from the melting of polar ice
    caps and glaciers. Coastal areas are particularly vulnerable, as they face higher risks
    of flooding, storm surges, and erosion. Additionally, the warming atmosphere can hold
    more moisture, leading to intense and unpredictable precipitation patterns. This variability
    can cause both severe droughts and devastating floods, affecting agricultural productivity
    and water resources. The effects of climate change are widespread, influencing not only
    the environment but also the socio-economic stability of communities. For example, changing
    weather patterns can disrupt food supply chains, increase the prevalence of diseases, and
    force people to migrate from their homes. To mitigate these effects, countries are investing
    in adaptive infrastructure, developing early warning systems, and implementing policies to
    reduce greenhouse gas emissions.
    """

    print("🧠 Summary:", summarize_text(demo_text))