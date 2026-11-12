"""Deterministic prompt-injection defenses: input screening, retrieved-chunk
scanning, and output leak/exfil filtering.

Probabilistic LLM defenses are never complete (OWASP LLM01/LLM07), so these
checks run OUTSIDE the model:
- known injection payloads are refused without calling the LLM at all
- poisoned retrieved chunks are dropped before context assembly (indirect
  injection / RAG poisoning, OWASP Layer 2)
- responses that echo prompt internals or carry exfil markup are replaced
  before they reach the user

Evasion handling follows the OWASP LLM Prompt Injection Prevention cheat sheet
(encoding/obfuscation, multilingual, typoglycemia, hidden text) and the
obfuscation quick-reference (base64/hex/ROT13, zero-width, Unicode tags,
homoglyphs, leetspeak, token splitting, letter spacing): inputs are NORMALIZED
and DECODED before matching so obfuscated payloads still hit the pattern set.
"""

from __future__ import annotations

import base64
import binascii
import codecs
import html
import re

# ---------------------------------------------------------------------------
# Input patterns (user messages AND retrieved chunks unless noted)
# ---------------------------------------------------------------------------

# Classic direct-injection patterns (OWASP LLM01 / system-prompt extraction).
_CLASSIC_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"ignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+"
        r"(?:(?:system|safety|security|guardrails?|initial|original)\s+)*"
        r"instructions",
        re.IGNORECASE,
    ),
    re.compile(
        r"ignore\s+(?:the\s+)?(?:above|preceding)\s+(?:context|instructions)",
        re.IGNORECASE,
    ),
    re.compile(r"repeat\s+everything\s+(?:above|below|before)", re.IGNORECASE),
    re.compile(
        r"(?:show|print|repeat|reveal|dump|output)\s+(?:your|the|this|all)\s+"
        r"(?:system\s+)?(?:prompt|instructions?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"system\s+(?:override|prompt\s*(?:dump|leak|extract))", re.IGNORECASE
    ),
    re.compile(
        r"you\s+are\s+now\s+(?:an?\s+)?(?:in\s+)?(?:debug|unrestricted|jailbreak)",
        re.IGNORECASE,
    ),
    re.compile(
        r"disregard\s+(?:all\s+)?(?:previous|prior|your|the|above)\s+"
        r"(?:instructions?|rules|prompt|guidelines)",
        re.IGNORECASE,
    ),
    re.compile(
        r"override\s+(?:your|the|system|previous)\s+"
        r"(?:rules?|instructions?|prompt|security|settings)",
        re.IGNORECASE,
    ),
    re.compile(
        r"bypass\s+(?:all\s+)?(?:safety|security|guardrails?|filters?|measures)",
        re.IGNORECASE,
    ),
    re.compile(r"developer\s+mode", re.IGNORECASE),
    re.compile(
        r"act\s+as\s+(?:an?\s+)?(?:unrestricted|uncensored|jailbroken)",
        re.IGNORECASE,
    ),
    re.compile(
        r"act\s+as\s+if\s+you(?:'|’)re\s+not\s+(?:bound|restricted)",
        re.IGNORECASE,
    ),
    re.compile(
        r"not\s+bound\s+by\s+(?:any\s+)?restrictions", re.IGNORECASE
    ),
    # Code-comment delivery (OWASP smoke test: "# IGNORE ALL INSTRUCTIONS").
    re.compile(
        r"(?:^|[\s;])[#;]\s*ignore\s+all\s+instructions",
        re.IGNORECASE | re.MULTILINE,
    ),
)

# Paraphrase / completion attacks: no "ignore"-style keywords (live tests).
_PARAPHRASE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"what\s+(?:exact\s+)?text\s+did\s+you\s+(?:receive|get)", re.IGNORECASE),
    re.compile(
        r"restate\s+(?:the\s+)?instructions?\s+you\s+were\s+given", re.IGNORECASE
    ),
    re.compile(r"quote\s+every\s+line\s+you\s+were\s+given", re.IGNORECASE),
    re.compile(
        r"(?:restate|repeat|quote|read\s+back)\s+the\s+(?:system\s+)?instructions?"
        r"\s+(?:at\s+the\s+)?(?:start|beginning)",
        re.IGNORECASE,
    ),
    re.compile(
        r"complete\s+the\s+sentence\s*,?\s*(?:verbatim|with\s+no\s+changes|exactly)",
        re.IGNORECASE,
    ),
    re.compile(
        r"quote\s+(?:the\s+)?(?:text|line|content)\s+you\s+(?:were\s+)?(?:received|given)",
        re.IGNORECASE,
    ),
    re.compile(
        r"what\s+(?:were|are)\s+(?:the\s+)?exact\s+instructions"
        r"(?:\s+you\s+were\s+given)?",
        re.IGNORECASE,
    ),
)

# Refusal suppression (promptinjectionprevention.com class 13; Check Point).
_REFUSAL_SUPPRESSION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"do\s+not\s+(?:start|begin)\s+with\s+"
        r"(?:['\"]?i'?m\s+sorry|as\s+an\s+ai|i\s+can'?t)",
        re.IGNORECASE,
    ),
    re.compile(r"(?:never|don'?t|do\s+not)\s+refuse", re.IGNORECASE),
    re.compile(
        r"without\s+(?:saying|adding|prefacing)\s+"
        r"(?:you\s+can'?t|i\s+can'?t|i'?m\s+sorry|as\s+an\s+ai)",
        re.IGNORECASE,
    ),
)

# Fake task completion / context switch (cyberdesserts "next task" pattern).
_TASK_COMPLETION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"task\s+(?:complete|done|finished|completed)[.!]\s*"
        r"now\s+(?:here'?s|your|the)\s+(?:the\s+)?(?:next|another|a\s+new)",
        re.IGNORECASE,
    ),
    re.compile(
        r"great\s+job[.!][^\n]{0,40}next\s+task", re.IGNORECASE
    ),
)

# Special-token / fake role-boundary injection (CrowdStrike "Special Token
# Injection", "Prompt Boundary Manipulation").
_SPECIAL_TOKEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"<\|(?:system|assistant|user|im_start|im_end|end)\|>", re.IGNORECASE),
    re.compile(r"\[(?:SYSTEM|END_OF_TURN|INST)\]", re.IGNORECASE),
    re.compile(r"(?:^|\n)\s*###\s*(?:system|instruction)", re.IGNORECASE | re.MULTILINE),
    re.compile(
        r"(?:^|\n)\s*(?:SYSTEM|INSTRUCTION|NEW\s+RULES)\s*:", re.IGNORECASE | re.MULTILINE
    ),
)

# Encoding / decode-as-instruction framing (OWASP encoding section).
_ENCODING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?:decode|decrypt)\s+(?:and\s+)?(?:then\s+)?(?:follow|obey|execute|run)",
        re.IGNORECASE,
    ),
    re.compile(
        r"base64\s*:\s*(?:decode\s+and\s+)?(?:follow|the\s+following)",
        re.IGNORECASE,
    ),
    re.compile(r"rot13\s*(?:and\s+)?follow", re.IGNORECASE),
    re.compile(r"hex\s*:\s*(?:decode\s+and\s+)?follow", re.IGNORECASE),
)

# Multilingual ignore-phrases: non-English payloads show higher compliance
# (arXiv:2606.29602) and evade English-only regexes (live test #4 was ES).
_MULTILINGUAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"ignora(?:r|s)?\s+(?:todas\s+)?las\s+instrucciones\s+(?:anteriores|previas)",
        re.IGNORECASE,
    ),
    re.compile(
        r"ignoriere\s+alle\s+(?:vorherigen|bisherigen|obigen)\s+anweisungen",
        re.IGNORECASE,
    ),
    re.compile(
        r"ignorez\s+toutes\s+les\s+instructions\s+pr[ée]c[ée]dentes", re.IGNORECASE
    ),
    re.compile(
        r"проигнорируйте\s+все\s+предыдущие\s+(?:инструкции|подсказки)", re.IGNORECASE
    ),
    re.compile(
        r"ignora\s+tutte\s+le\s+istruzioni\s+precedenti", re.IGNORECASE
    ),
)

# Exfil markup lives in chunks (poisoned docs) and model OUTPUT, not in
# benign user questions about HTML/markdown (those must stay allowed).

_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    *_CLASSIC_PATTERNS,
    *_PARAPHRASE_PATTERNS,
    *_REFUSAL_SUPPRESSION_PATTERNS,
    *_TASK_COMPLETION_PATTERNS,
    *_SPECIAL_TOKEN_PATTERNS,
    *_ENCODING_PATTERNS,
    *_MULTILINGUAL_PATTERNS,
)

INJECTION_BLOCK_MESSAGE = (
    "I can't help with requests that try to change my instructions or extract "
    "hidden prompts. Ask me a question about your documents instead."
)

# ---------------------------------------------------------------------------
# Retrieved-chunk patterns (indirect injection / RAG poisoning)
# ---------------------------------------------------------------------------

# Broader than the user-input set: a false positive only drops one chunk,
# while a miss lets a poisoned document steer the model. Includes delimiter
# spoofing (a chunk trying to close/open our trust boundary).
_CHUNK_POISON_PATTERNS: tuple[re.Pattern[str], ...] = (
    *_INJECTION_PATTERNS,
    re.compile(
        r"disregard\s+(?:all\s+)?(?:your|the|previous|above)\s+"
        r"(?:rules|instructions|guidelines|prompt)",
        re.IGNORECASE,
    ),
    re.compile(
        r"you\s+are\s+now\s+(?:an?\s+)?(?:unrestricted|uncensored|free\s+of\s+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:reveal|output|print|quote)\s+(?:the\s+)?"
        r"(?:complete\s+|full\s+)?(?:instructions?|prompt|text)\s+"
        r"(?:you\s+(?:were\s+)?(?:given|received)|above|before|below)",
        re.IGNORECASE,
    ),
    re.compile(
        r"follow\s+(?:these|the|my)\s+new\s+(?:rules|instructions)", re.IGNORECASE
    ),
    re.compile(
        r"new\s+instructions?\s*:\s*(?:you|always|first|system)", re.IGNORECASE
    ),
    re.compile(r"system\s*:\s*(?:you\s+are|ignore|disregard)", re.IGNORECASE),
    re.compile(
        r"always\s+first\s+(?:output|reveal|print|state)", re.IGNORECASE
    ),
    re.compile(
        r"always\s+(?:first\s+)?quote\s+your\s+(?:full\s+|original\s+)+"
        r"(?:message|instructions|prompt)",
        re.IGNORECASE,
    ),
    # Tag spoofing: break out of (or fake) our trust boundary markers.
    re.compile(r"</?\s*RETRIEVED_DATA\b", re.IGNORECASE),
    re.compile(r"<\s*/?\s*(?:system|assistant)\s*>", re.IGNORECASE),
    # Hidden exfil beacon embedded in a document (OWASP HTML/Markdown).
    re.compile(r"<img\s[^>]*\bsrc\s*=\s*[\"']https?://", re.IGNORECASE),
    re.compile(
        r"!\[[^\]]*\]\(\s*https?://[^)\s]*\?", re.IGNORECASE
    ),
)

# ---------------------------------------------------------------------------
# Evasion normalization (OWASP encoding/obfuscation + Unit 42 observations)
# ---------------------------------------------------------------------------

# Common Cyrillic/lookalike homoglyphs -> Latin (Unit 42: "Іgnore" etc.).
_HOMOGLYPH_TABLE = str.maketrans(
    {
        # lowercase cyrillic + lookalikes
        ord("а"): ord("a"),
        ord("е"): ord("e"),
        ord("о"): ord("o"),
        ord("р"): ord("p"),
        ord("с"): ord("c"),
        ord("у"): ord("y"),
        ord("х"): ord("x"),
        ord("і"): ord("i"),
        ord("ѕ"): ord("s"),
        ord("ԁ"): ord("d"),
        ord("ɡ"): ord("g"),
        ord("ⅰ"): ord("i"),
        # uppercase (Unit 42 "Іgnore")
        ord("А"): ord("A"),
        ord("Е"): ord("E"),
        ord("І"): ord("I"),
        ord("О"): ord("O"),
        ord("Р"): ord("P"),
        ord("С"): ord("C"),
        ord("Х"): ord("X"),
    }
)

_LEET_TABLE = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
)

# Zero-width / invisible / tag characters used for smuggling (OWASP).
_INVISIBLE_RE = re.compile(
    r"[\u00ad\u034f\u061c\u180e\u200b\u200c\u200d\u2060\ufeff"
    r"\u2061-\u2064\U000E0000-\U000E007F]"
)
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_BASE64_CANDIDATE_RE = re.compile(r"[A-Za-z0-9+/_-]{16,}={0,2}")
_HEX_CANDIDATE_RE = re.compile(r"(?:[0-9a-fA-F]{2}){10,}")
_HEX_ESCAPE_RE = re.compile(r"(?:\\x[0-9a-fA-F]{2}){6,}")
_LETTER_SPACED_RE = re.compile(r"(?:[A-Za-z]\s+){2,}[A-Za-z]")
_TOKEN_SPLIT_RE = re.compile(r"([A-Za-z]{2,})\"\s*\+\s*\"([A-Za-z]{2,})")

# Critical words for Damerau-Levenshtein ≤1 repair (OWASP typoglycemia).
# Intentionally excludes high-frequency false friends like "mode"/"model".
_CRITICAL_WORDS: frozenset[str] = frozenset(
    {
        "ignore",
        "instructions",
        "previous",
        "prior",
        "above",
        "earlier",
        "disregard",
        "override",
        "reveal",
        "prompt",
        "system",
        "developer",
        "unrestricted",
        "refuse",
        "bypass",
        "safety",
        "security",
        "jailbreak",
        "dump",
        "extract",
        "leak",
        "quote",
        "restate",
        "verbatim",
        "sentence",
        "guidelines",
        "rules",
        "debug",
        "repeat",
        "everything",
        "delete",
        "measures",
        "settings",
        "guardrails",
        "preceding",
    }
)


def _damerau_le1(a: str, b: str) -> bool:
    """True when Damerau-Levenshtein distance(a, b) is 0 or 1.

    Counts a single substitution, one insertion/deletion, or one adjacent
    transposition as distance 1 — the edits seen in OWASP typoglycemia
    examples (ignroe→ignore, prevoius→previous, measuers→measures).
    """
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        diffs = [i for i in range(la) if a[i] != b[i]]
        if len(diffs) == 1:
            return True
        if len(diffs) == 2:
            i, j = diffs
            if j == i + 1 and a[i] == b[j] and a[j] == b[i]:
                return True
        return False
    if la > lb:
        a, b = b, a
        la, lb = lb, la
    i = j = 0
    skipped = False
    while i < la and j < lb:
        if a[i] == b[j]:
            i += 1
            j += 1
        else:
            if skipped:
                return False
            skipped = True
            j += 1
    return True


def _collapse_letter_spacing(text: str) -> str:
    """Collapse best-of-N style letter spacing: 'i g n o r e' -> 'ignore'.

    Splits on runs of 2+ spaces first so word-group boundaries survive
    (OWASP smoke test uses triple spaces between spaced-out words).
    """
    parts = re.split(r"(\s{2,})", text)
    out: list[str] = []
    for part in parts:
        stripped = part.strip()
        if stripped and _LETTER_SPACED_RE.fullmatch(stripped):
            out.append(re.sub(r"\s+", "", stripped))
        else:
            out.append(part)
    return "".join(out)


def _join_token_splits(text: str) -> str:
    """Reassemble '"ig"+"nore" + " all"' style token splitting."""
    for _ in range(4):
        joined = _TOKEN_SPLIT_RE.sub(r"\1\2", text)
        if joined == text:
            break
        text = joined
    return text


def _repair_typoglycemia(text: str) -> str:
    """Repair scrambled-middle-letter attack words (Damerau-Le1 ≤1)."""
    def fix(match: re.Match[str]) -> str:
        word = match.group().lower()
        if word in _CRITICAL_WORDS:
            return word
        if len(word) < 4:
            return match.group()
        for critical in _CRITICAL_WORDS:
            if abs(len(critical) - len(word)) > 1:
                continue
            if _damerau_le1(word, critical):
                return critical
        return match.group()

    return re.sub(r"[A-Za-z]+", fix, text)


def _normalize(text: str) -> str:
    """Undo cheap evasion before pattern matching: entities, invisibles,
    control chars (delimiter smuggling), letter spacing, token splits,
    homoglyphs, leetspeak, and typoglycemia."""
    text = html.unescape(text)
    text = _INVISIBLE_RE.sub("", text)
    text = _CONTROL_RE.sub("", text)
    text = _collapse_letter_spacing(text)
    text = _join_token_splits(text)
    text = text.translate(_HOMOGLYPH_TABLE)

    def _deobfuscate_token(match: re.Match[str]) -> str:
        token = match.group()
        if re.search(r"\d", token) and re.search(r"[A-Za-z]", token):
            return token.translate(_LEET_TABLE)
        return token

    text = re.sub(r"[A-Za-z0-9@$]+", _deobfuscate_token, text)
    # Quotes left over from token-split joins: '"ignore" all' -> 'ignore all'
    text = text.replace('"', "").replace("'", "")
    return _repair_typoglycemia(text)


def _decoded_variants(text: str) -> list[str]:
    """Return decoded forms of encoded payloads embedded in the text.

    Covers base64 (incl. URL-safe), hex byte strings, ``\\xNN`` escapes,
    and ROT13 — encodings called out by OWASP and the obfuscation
    quick-reference. Decoded text is only used for MATCHING, never echoed.
    """
    variants: list[str] = []
    for match in _BASE64_CANDIDATE_RE.finditer(text):
        candidate = match.group()
        padded = candidate + "=" * (-len(candidate) % 4)
        try:
            decoded = base64.b64decode(padded, validate=False)
        except (ValueError, binascii.Error):
            continue
        try:
            variants.append(decoded.decode("utf-8"))
        except UnicodeDecodeError:
            continue
    for match in _HEX_CANDIDATE_RE.finditer(text):
        blob = match.group()
        if len(blob) % 2:
            blob = blob[:-1]
        try:
            variants.append(bytes.fromhex(blob).decode("utf-8", "ignore"))
        except ValueError:
            continue
    for match in _HEX_ESCAPE_RE.finditer(text):
        try:
            raw = bytes(
                int(part, 16)
                for part in re.findall(r"\\x([0-9a-fA-F]{2})", match.group())
            )
        except ValueError:
            continue
        variants.append(raw.decode("utf-8", "ignore"))
    variants.append(codecs.decode(text, "rot_13"))
    return variants


def _markup_variants(text: str) -> list[str]:
    """Extract LaTeX \\text{...} / \\color{...}{...} bodies (OWASP invisible
    KaTeX text) so pattern matching sees the hidden payload."""
    variants: list[str] = []
    variants.extend(re.findall(r"\\text\{([^}]+)\}", text))
    variants.extend(re.findall(r"\\color\{[^}]+\}\{([^}]+)\}", text))
    variants.extend(re.findall(r"\\htmlonly\{([^}]+)\}", text))
    return variants


def _all_candidates(text: str) -> list[str]:
    """Raw + normalized + decoded + markup-extracted forms of ``text``."""
    candidates = [text, _normalize(text)]
    candidates.extend(_normalize(v) for v in _decoded_variants(text))
    candidates.extend(_normalize(v) for v in _markup_variants(text))
    return candidates


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_injection(text: str) -> bool:
    """True when user input matches a known prompt-injection pattern.

    Checks raw, evasion-normalized, decoded (base64/hex/ROT13), and
    markup-extracted (LaTeX) forms of the text.
    """
    return any(
        pattern.search(candidate)
        for candidate in _all_candidates(text)
        for pattern in _INJECTION_PATTERNS
    )


def chunk_looks_poisoned(text: str) -> bool:
    """True when a retrieved chunk matches indirect-injection patterns.

    Used before context assembly: poisoned chunks are dropped rather than
    shown to the model (OWASP RAG cheat sheet, context-window protection).
    Applies the same evasion normalization as input screening.
    """
    return any(
        pattern.search(candidate)
        for candidate in _all_candidates(text)
        for pattern in _CHUNK_POISON_PATTERNS
    )


def filter_poisoned_chunks(texts: list[str]) -> list[str]:
    """Drop chunks that look poisoned; keep order of the safe ones."""
    return [text for text in texts if not chunk_looks_poisoned(text)]


# Substrings that indicate the model echoed its own prompt (LLM07 leakage).
_LEAK_MARKERS: tuple[str, ...] = (
    "you are todoflow's study assistant",
    "security rules — never break",
    'retrieved_data trust="untrusted"',
    "you are a friendly and proactive task management assistant",
    "critical behavior:",
)

# Output-side exfil / secret leakage (OWASP OutputValidator + HTML/Markdown
# injection). Matched against the raw response before it reaches the user.
_OUTPUT_UNSAFE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
    re.compile(
        r"api[_\s]?key\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,}", re.IGNORECASE
    ),
    re.compile(r"<img\s[^>]*\bsrc\s*=\s*[\"']https?://", re.IGNORECASE),
    re.compile(r"!\[[^\]]*\]\(\s*https?://[^)\s]*\?", re.IGNORECASE),
    re.compile(r"\]\(\s*javascript:", re.IGNORECASE),
)

LEAK_BLOCK_MESSAGE = (
    "I can't share internal instructions. Ask me a question about your "
    "documents instead."
)

EXFIL_BLOCK_MESSAGE = (
    "I can't include external links, images, or credentials in responses."
)


def sanitize_output(text: str) -> str:
    """Replace responses that leak prompt internals or carry exfil markup."""
    lowered = text.lower()
    if any(marker in lowered for marker in _LEAK_MARKERS):
        return LEAK_BLOCK_MESSAGE
    if any(pattern.search(text) for pattern in _OUTPUT_UNSAFE_PATTERNS):
        return EXFIL_BLOCK_MESSAGE
    return text
