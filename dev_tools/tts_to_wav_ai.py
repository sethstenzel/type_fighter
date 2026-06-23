
# uv run python tts_to_wav_ai.py -i ..\src\lessons\lesson_1\lesson_1_instructions.txt -o ..\src\lessons\lesson_1\lesson_1_instructions.wav --style playful --speed 1.1 --voice am_michael
# uv run python tts_to_wav_ai.py -i ..\src\lessons\lesson_1\lesson_1_intro.txt -o ..\src\lessons\lesson_1\lesson_1_intro.wav --style playful --speed 1.1
from __future__ import annotations

import argparse
from pathlib import Path

import soundfile as sf
from kokoro import KPipeline


"""
Kokoro-82M language codes:

American English:
- lang_code="a"

British English:
- lang_code="b"

Common voices:

American female:
- af_bella
- af_sarah
- af_nicole
- af_sky

American male:
- am_adam
- am_michael

British female:
- bf_emma
- bf_isabella
- bf_alice

British male:
- bm_george
"""


DEFAULT_VOICE = "af_heart"
DEFAULT_LANG_CODE = "a"
DEFAULT_SAMPLE_RATE = 24000


def apply_style(text: str, style: str | None) -> str:
    text = text.strip()

    if not style:
        return text

    return text


def read_text_file(input_file: str | Path) -> str:
    input_path = Path(input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if not input_path.is_file():
        raise ValueError(f"Input path is not a file: {input_path}")

    return input_path.read_text(encoding="utf-8")


def make_voice_file(
    text: str,
    output_file: str | Path = "project_voice.wav",
    voice: str = DEFAULT_VOICE,
    lang_code: str = DEFAULT_LANG_CODE,
    speed: float = 1.0,
) -> Path:
    text = text.strip()

    if not text:
        raise ValueError("Text cannot be empty.")

    output_path = Path(output_file)

    if output_path.suffix.lower() != ".wav":
        output_path = output_path.with_suffix(".wav")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    pipeline = KPipeline(lang_code=lang_code)

    generator = pipeline(
        text,
        voice=voice,
        speed=speed,
        split_pattern=r"\n+",
    )

    audio_chunks = []

    for index, (_graphemes, _phonemes, audio) in enumerate(generator):
        print(f"Generated chunk {index + 1}")
        audio_chunks.append(audio)

    if not audio_chunks:
        raise RuntimeError("No audio was generated.")

    # Avoid requiring numpy explicitly in your code if the package already returns arrays.
    if len(audio_chunks) == 1:
        final_audio = audio_chunks[0]
    else:
        import numpy as np

        final_audio = np.concatenate(audio_chunks)

    sf.write(output_path, final_audio, DEFAULT_SAMPLE_RATE)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a WAV file from text using Kokoro-82M."
    )

    parser.add_argument(
        "text",
        nargs="?",
        help="Text to convert to speech. Omit this when using -i/--input.",
    )

    parser.add_argument(
        "-i",
        "--input",
        help="Input text file, for example text.txt.",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="project_voice.wav",
        help="Output WAV file path. Default: project_voice.wav",
    )

    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help=f"Voice name. Default: {DEFAULT_VOICE}.",
    )

    parser.add_argument(
        "--lang-code",
        default=DEFAULT_LANG_CODE,
        help="Kokoro language code. Use 'a' for American English, 'b' for British English. Default: b.",
    )

    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speech speed. Try 1.05 to 1.25 for happier/playful delivery.",
    )

    parser.add_argument(
        "--style",
        choices=["playful", "excited", "calm"],
        help="Optional speaking style helper.",
    )

    args = parser.parse_args()

    if args.input and args.text:
        parser.error("Use either direct text or -i/--input, not both.")

    if args.input:
        text = read_text_file(args.input)
    elif args.text:
        text = args.text
    else:
        parser.error("Provide text directly or use -i/--input with a text file.")

    text = apply_style(text, args.style)

    wav_path = make_voice_file(
        text=text,
        output_file=args.output,
        voice=args.voice,
        lang_code=args.lang_code,
        speed=args.speed,
    )

    print(f"Created WAV file: {wav_path}")


if __name__ == "__main__":
    main()