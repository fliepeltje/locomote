from locomote.parser import Segment

from typing import Iterator

def generate_text_iter(from_text: str, to_text: str) -> Iterator[str]:
    yield from_text
    segments = Segment.from_sequences(from_text, to_text)
    text_modifiers = []
    for seg in segments:
        text_modifiers += seg.char_mods()
    for mod in text_modifiers:
        from_text = mod(from_text)
        yield from_text
    yield to_text