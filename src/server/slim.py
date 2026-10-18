"""
JADX MCP Server - Kotlin metadata slimming

Strips the Kotlin compiler metadata that JADX writes into decompiled source
(`@Metadata(d1 = {...}, d2 = {...})` on classes, `@DebugMetadata(...)` on
coroutines classes) before a dump is handed to the MCP client.

Why: those annotations are compiler IR, not code. On Kotlin APKs they are
routinely 25-50% of a class dump, so a few parallel `get_class_source` calls
can burn an LLM context window.

Safety rule: the line count must not change. `add_comment` resolves `line=N`
against the same decompiled string the plugin served, split on newlines, so a
removed line would silently retarget a later comment. A stripped annotation is
therefore replaced in place by a short marker plus the same newlines it held,
and any pass that would change the line count is discarded before a caller can
see it.

Author: Jafar Pathan (zinja-coder@github)
License: See LICENSE file
"""

from typing import Any, Iterator, Optional, Tuple

__all__ = ["SLIM_MARKER", "SOURCE_KEYS", "slim_source", "slim_payload"]

#: Kotlin compiler metadata annotations, by simple name. `<pkg>.<name>(...)`
#: with one of these names is stripped; every other annotation is left alone.
_METADATA_NAMES = frozenset({"Metadata", "DebugMetadata"})

#: Stands in for a stripped annotation so the code around it keeps its shape.
SLIM_MARKER = '/*[slimmed: Kotlin metadata]*/'

#: Payload keys under which the plugin serves decompiled source.
SOURCE_KEYS = ("response", "content", "code")

_WS = " \t\r\n"


def _skip_quoted(code: str, start: int, quote: str) -> Optional[int]:
    """Index just past the closing `quote`, or None when it never closes."""
    i = start + 1
    n = len(code)
    while i < n:
        char = code[i]
        if char == "\\":
            i += 2
            continue
        if char == quote:
            return i + 1
        i += 1
    return None


def _annotation_name_end(code: str, at: int) -> Optional[int]:
    """Index just past a Kotlin metadata annotation name, else None.

    `at` indexes the '@'. The name may be package qualified
    (`@kotlin.Metadata(...)`, `@kotlin.coroutines.jvm.internal.DebugMetadata`)
    or bare (`@Metadata(...)`), so each dot separated segment is walked and the
    last one decides.
    """
    i = at + 1
    n = len(code)
    while True:
        segment = i
        while i < n and (code[i].isalnum() or code[i] in "_$"):
            i += 1
        if i == segment:
            return None
        name = code[segment:i]
        if i < n and code[i] == ".":
            i += 1
            continue
        return i if name in _METADATA_NAMES else None


def _call_end(code: str, open_paren: int) -> Optional[int]:
    """Index just past the ')' matching `open_paren`, or None if unbalanced.

    Parenthesis counting ignores anything inside string/char literals and
    comments, because the metadata payload is full of both: `d2` holds
    descriptors like `"(I)V"`, and `d1` holds escaped text.
    """
    depth = 0
    i = open_paren
    n = len(code)
    while i < n:
        char = code[i]
        if char == '"':
            i = _skip_quoted(code, i, '"')
            if i is None:
                return None
        elif char == "'":
            i = _skip_quoted(code, i, "'")
            if i is None:
                return None
        elif char == "/" and i + 1 < n and code[i + 1] == "/":
            newline = code.find("\n", i)
            if newline < 0:
                return None
            i = newline
        elif char == "/" and i + 1 < n and code[i + 1] == "*":
            close = code.find("*/", i + 2)
            if close < 0:
                return None
            i = close + 2
        elif char == "(":
            depth += 1
            i += 1
        elif char == ")":
            depth -= 1
            i += 1
            if depth == 0:
                return i
        else:
            i += 1
    return None


def _metadata_spans(code: str) -> Iterator[Tuple[int, int]]:
    """Yield (start, end) of every metadata annotation call, in order.

    The source is lexed once so an `@Metadata(` that only appears inside a
    string literal or a comment is not mistaken for a real annotation. Returns
    nothing if the text cannot be lexed, so an odd dump is left untouched.
    """
    i = 0
    n = len(code)
    while i < n:
        char = code[i]
        if char == '"':
            i = _skip_quoted(code, i, '"')
            if i is None:
                return
        elif char == "'":
            i = _skip_quoted(code, i, "'")
            if i is None:
                return
        elif char == "/" and i + 1 < n and code[i + 1] == "/":
            newline = code.find("\n", i)
            i = n if newline < 0 else newline
        elif char == "/" and i + 1 < n and code[i + 1] == "*":
            close = code.find("*/", i + 2)
            if close < 0:
                return
            i = close + 2
        elif char == "@":
            name_end = _annotation_name_end(code, i)
            call_end = None
            if name_end is not None:
                probe = name_end
                while probe < n and code[probe] in _WS:
                    probe += 1
                if probe < n and code[probe] == "(":
                    call_end = _call_end(code, probe)
                    if call_end is None:
                        return
            if call_end is None:
                i += 1
            else:
                yield i, call_end
                i = call_end
        else:
            i += 1


def slim_source(code: str) -> str:
    """Return `code` with Kotlin metadata annotations stripped out.

    The line count never changes: each annotation is replaced by a short marker
    plus the newlines it contained, so `line=N` from a numbered dump still
    addresses the same line in JADX. Anything that cannot be trimmed safely is
    returned unchanged.
    """
    if not code or "Metadata" not in code:
        return code

    spans = list(_metadata_spans(code))
    if not spans:
        return code

    out = []
    previous = 0
    for start, end in spans:
        out.append(code[previous:start])
        out.append(SLIM_MARKER + "\n" * code.count("\n", start, end))
        previous = end
    out.append(code[previous:])
    slimmed = "".join(out)

    # Belt and braces: a line count change would shift comment line numbers,
    # so an unexpected result is never handed back.
    if slimmed.count("\n") != code.count("\n"):
        return code
    return slimmed


def slim_payload(value: Any, keys: Tuple[str, ...] = SOURCE_KEYS) -> Any:
    """Slim the decompiled source inside a plugin response.

    Covers the shapes the tools read: a bare source string, a dict carrying the
    source under one of `keys` (`response` for the plain-text class dump,
    `content` for the current-class / main-activity / classes dumps, `code` for
    the method dump), and the paginated dicts that hold a list of class entries.
    Strings under any other key are never touched.
    """
    if isinstance(value, str):
        return slim_source(value)
    if isinstance(value, dict):
        out = {}
        changed = False
        for key, item in value.items():
            if key in keys and isinstance(item, str):
                new_item = slim_source(item)
            elif isinstance(item, (dict, list)):
                new_item = slim_payload(item, keys)
            else:
                new_item = item
            changed = changed or new_item is not item
            out[key] = new_item
        return out if changed else value
    if isinstance(value, list):
        out = []
        changed = False
        for item in value:
            new_item = slim_payload(item, keys) if isinstance(item, (dict, list)) else item
            changed = changed or new_item is not item
            out.append(new_item)
        return out if changed else value
    return value
