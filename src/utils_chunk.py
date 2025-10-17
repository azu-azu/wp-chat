import re
JP_SPLIT = re.compile(r'(?<=[。！？\?])\s*')

def sentence_chunks(text: str, size=900, overlap=150):
    sents = JP_SPLIT.split(text)
    buf = ""
    for s in sents:
        if not s:
            continue
        if len(buf) + len(s) <= size:
            buf += s
        else:
            if buf:
                yield buf
            # overlap は最後の一部を引き継ぐ
            buf = (buf[-overlap:] if overlap < len(buf) else "") + s
    if buf:
        yield buf
