"""
Headless fallback backend for the JADX MCP server.

The upstream architecture requires jadx-GUI running with the jadx-ai-mcp
plugin (HTTP on port 8650). When that endpoint refuses connections, this
module lets the same server keep working: it decompiles the APK once with
the headless jadx CLI and serves the class/resource/search tools straight
from the decompiled tree on disk.

Enabled two ways — no per-APK configuration required:
    * the MCP tool ``headless_set_apk(apk_path)`` — points the backend at
      any APK for this session and starts its decompile in the background
      (the general path; also used to retry or refresh);
    * the static default ``JADX_MCP_HEADLESS_APK`` env var — for pinned
      workflows that always analyze the same APK.

    JADX_MCP_JADX_BIN       — optional jadx binary (default: "jadx" on PATH)
    JADX_MCP_HEADLESS_REFRESH=1 — force a fresh decompile of the cached APK

The decompile is cached under ~/.cache/jadx-mcp-headless/<apk-stem>/ and
reused across sessions. Endpoints that genuinely need the live GUI
(current-class, selected-text, smali-of-class, rename, debug, comments)
return a clear gui_required error instead of pretending.

Honest limits, also surfaced per-result as ``"headless": true``:
    * methods/fields are parsed from the Java source text (best-effort)
    * xrefs and keyword searches are text greps (approximate)
    * smali is not produced by the jadx CLI — use apktool
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger("jadx-mcp-server.headless")

APK_ENV = "JADX_MCP_HEADLESS_APK"
BIN_ENV = "JADX_MCP_JADX_BIN"
REFRESH_ENV = "JADX_MCP_HEADLESS_REFRESH"

CACHE_ROOT = Path(os.environ.get("JADX_MCP_HOME", str(Path.home() / ".cache"))) / "jadx-mcp-headless"

MAX_GREP_MATCHES = 500

# Endpoints that only the live JADX-GUI plugin can serve
GUI_REQUIRED_ENDPOINTS = {
    "current-class", "selected-text", "smali-of-class",
    "rename-class", "rename-method", "rename-field", "rename-package", "rename-variable",
    "debug-get-stack-frames", "debug-get-threads", "debug-get-variables",
    "add-comment", "list-comments",
}

# Reported by the jadx_mode tool
last_mode: Dict[str, Any] = {"mode": "unknown", "detail": "no call made yet"}

# Runtime APK override (set by the headless_set_apk tool) and its lifecycle.
# Priority: runtime override > JADX_MCP_HEADLESS_APK env. The decompile runs
# in a background thread: headless_set_apk returns immediately and tools
# called before it finishes report "decompilation in progress" honestly.
_runtime: Dict[str, Any] = {"apk": None}
_status: Dict[str, Any] = {"state": "idle", "apk": None, "detail": ""}
import threading  # noqa: E402


def active_apk() -> Optional[str]:
    return _runtime["apk"] or os.environ.get(APK_ENV) or None


def set_apk(apk_path: str, refresh: bool = False) -> Dict[str, Any]:
    """Point the headless backend at any APK and start its decompile.

    Returns immediately; the decompile runs in a daemon thread. Call
    jadx_mode to check state (idle → decompiling → ready | failed).
    """
    path = Path(apk_path)
    if not path.is_file():
        return {"error": f"APK not found: {apk_path}", "headless": True}
    if _status["state"] == "decompiling" and _status["apk"] == str(path) and not refresh:
        return {"status": "already_running", "apk": str(path), "headless": True,
                "note": "a decompile of this APK is already in progress — check jadx_mode"}
    _runtime["apk"] = str(path)
    _status.update({"state": "decompiling", "apk": str(path),
                    "detail": "headless decompile started" if not refresh else "refreshing decompile"})
    if refresh:
        shutil.rmtree(_cache_dir(), ignore_errors=True)
    thread = threading.Thread(target=_bg_decompile, daemon=True)
    thread.start()
    return {
        "status": "started",
        "apk": str(path),
        "cache_dir": str(_cache_dir()),
        "headless": True,
        "note": ("decompiling in the background — check jadx_mode; tools "
                 "report 'decompilation in progress' until it is ready"),
    }


def _bg_decompile() -> None:
    try:
        info = _decompile_locked()
        _status.update({"state": "ready", "detail": info})
        log.info("headless decompile ready: %s", info)
    except HeadlessUnavailable as exc:
        _status.update({"state": "failed", "detail": str(exc)})
        log.error("headless decompile failed: %s", exc)


class HeadlessUnavailable(Exception):
    """Headless fallback cannot proceed (no APK configured, jadx missing, decompile failed)."""


def configured() -> bool:
    return bool(os.environ.get(APK_ENV))


def _cache_dir() -> Path:
    apk = active_apk() or ""
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", Path(apk).stem or "apk") if apk else "apk"
    return CACHE_ROOT / stem


def _sources_dir() -> Path:
    return _cache_dir() / "sources"


def _resources_dir() -> Path:
    return _cache_dir() / "resources"


def gui_required(endpoint: str) -> Dict[str, Any]:
    return {
        "error": (
            f"'{endpoint}' needs the live JADX-GUI plugin (headless mode is active). "
            "Open the APK in JADX-GUI with the AI MCP plugin, or use a tool that "
            "works headless."
        ),
        "headless": True,
        "gui_required": True,
    }


def _decompile_locked() -> Dict[str, Any]:
    """Synchronous decompile-or-reuse; called from a worker thread."""
    apk = active_apk()
    if not apk:
        raise HeadlessUnavailable(
            "JADX-GUI is not running and no headless APK is set. "
            "Call the headless_set_apk tool with the target APK path "
            f"(or set {APK_ENV} as a static default)."
        )
    if not Path(apk).is_file():
        raise HeadlessUnavailable(f"{APK_ENV} points at a missing file: {apk}")

    out = _cache_dir()
    fresh = os.environ.get(REFRESH_ENV) == "1"
    if fresh and out.exists():
        shutil.rmtree(out, ignore_errors=True)
    if not (_sources_dir().exists() and any(_sources_dir().rglob("*.java"))):
        out.mkdir(parents=True, exist_ok=True)
        jadx_bin = os.environ.get(BIN_ENV, "jadx")
        cmd = [jadx_bin, "-d", str(out), "--no-imports", apk]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        except FileNotFoundError as exc:
            raise HeadlessUnavailable(
                f"jadx binary not found ('{jadx_bin}'). Install jadx or set {BIN_ENV}."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise HeadlessUnavailable("headless jadx decompile timed out after 1800s") from exc
        if proc.returncode != 0:
            raise HeadlessUnavailable(
                f"headless jadx decompile failed (exit {proc.returncode}): "
                f"{(proc.stderr or proc.stdout).strip()[:500]}"
            )
        log.info("headless decompile complete: %s", out)
    java_files = list(_sources_dir().rglob("*.java"))
    return {
        "apk": apk,
        "cache_dir": str(out),
        "classes": len(java_files),
        "fresh": fresh,
    }


def ensure_decompiled() -> Dict[str, Any]:
    """Async-safe: run the (cached) decompile in a worker thread."""
    return _decompile_locked()


def _class_path(class_name: str) -> Optional[Path]:
    """Resolve com.example.Foo (+ optional $Inner) to its .java file."""
    rel = class_name.replace(".", "/")
    for candidate in (
        _sources_dir() / f"{rel}.java",
        _sources_dir() / f"{rel.replace('$', '/')}.java",
    ):
        if candidate.is_file():
            return candidate
    if "$" in class_name:
        outer = _sources_dir() / f"{class_name.split('$')[0].replace('.', '/')}.java"
        if outer.is_file():
            return outer  # inner class decompiled inline in the outer file
    return None


def _all_java_files() -> list[Path]:
    return sorted(_sources_dir().rglob("*.java")) if _sources_dir().exists() else []


def _class_name_of(path: Path) -> str:
    rel = path.relative_to(_sources_dir()).with_suffix("")
    return ".".join(rel.parts)


def _read_class(class_name: str) -> tuple[Path, str]:
    path = _class_path(class_name)
    if path is None:
        raise HeadlessUnavailable(
            f"class '{class_name}' not found in the headless decompile — "
            "use get_all_classes to list what exists."
        )
    return path, path.read_text(encoding="utf-8", errors="replace")


def _slice_page(items: list, params: Dict[str, Any]) -> list:
    offset = int(params.get("offset", 0) or 0)
    count = int(params.get("count", 0) or 0)
    return items[offset:] if count <= 0 else items[offset:offset + count]


# ── Java-source parsing (best-effort, text-based) ─────────────────────────

_METHOD_RX = re.compile(
    r"^\s*(?:@\w+(?:\([^)]*\))?\s+)*"
    r"(?:public|protected|private|static|final|abstract|synchronized|native|default)"
    r"[^\n{;=]*?\b(?P<name>\w+)\s*\((?P<args>[^)]*)\)\s*(?:throws\s+[\w.$,\s]+)?\s*\{"
)
_FIELD_RX = re.compile(
    r"^\s*(?:public|protected|private|static|final|transient|volatile)"
    r"[^\n()=;{]*\s+\w+\s*(?:=[^;\n]*)?;"
)


def _parse_methods(source: str) -> list[Dict[str, Any]]:
    out = []
    for i, line in enumerate(source.splitlines()):
        m = _METHOD_RX.match(line)
        if m:
            out.append({
                "name": m.group("name"),
                "signature": line.strip().rstrip("{").strip(),
                "line": i + 1,
            })
    return out


def _parse_fields(source: str) -> list[Dict[str, Any]]:
    out = []
    for i, line in enumerate(source.splitlines()):
        if _METHOD_RX.match(line):
            continue  # a declaration line with a { is a method, not a field
        if _FIELD_RX.match(line) and "(" not in line:
            out.append({"declaration": line.strip(), "line": i + 1})
    return out


def _extract_method_source(source: str, method_name: str) -> Optional[str]:
    """Brace-matched extraction of one method's source, or None.

    Declaration lines (per _METHOD_RX) are preferred so a call site inside
    another method does not shadow the real declaration.
    """
    lines = source.splitlines()
    candidates = [i for i, line in enumerate(lines)
                  if (m := _METHOD_RX.match(line)) and m.group("name") == method_name]
    if not candidates:
        candidates = [i for i, line in enumerate(lines)
                      if re.search(rf"\b{re.escape(method_name)}\s*\(", line)]
    for i in candidates:
        depth = 0
        started = False
        buf = []
        for j in range(i, len(lines)):
            buf.append(lines[j])
            for ch in lines[j]:
                if ch == "{":
                    depth += 1
                    started = True
                elif ch == "}":
                    depth -= 1
            if started and depth <= 0:
                return "\n".join(buf)
    return None


# ── endpoint handlers (sync; run in worker threads) ───────────────────────

def _h_class_source(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    class_name = params.get("class_name", "")
    path, source = _read_class(class_name)
    return {
        "response": source,
        "class_name": class_name,
        "source_path": str(path),
        "note": "served from the headless jadx decompile",
    }


def _h_all_classes(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    names = [_class_name_of(p) for p in _all_java_files()]
    return {"classes": _slice_page(sorted(names), params), "total": len(names)}


def _h_methods_of_class(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    class_name = params.get("class_name", "")
    _, source = _read_class(class_name)
    methods = _parse_methods(source)
    return {
        "class_name": class_name,
        "methods": methods,
        "total": len(methods),
        "note": "parsed from Java source text (best-effort)",
    }


def _h_fields_of_class(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    class_name = params.get("class_name", "")
    _, source = _read_class(class_name)
    fields = _parse_fields(source)
    return {
        "class_name": class_name,
        "fields": fields,
        "total": len(fields),
        "note": "parsed from Java source text (best-effort)",
    }


def _h_method_by_name(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    class_name = params.get("class_name", "")
    method_name = params.get("method_name", "")
    _, source = _read_class(class_name)
    code = _extract_method_source(source, method_name)
    if code is None:
        return {
            "error": f"method '{method_name}' not found in '{class_name}' (headless text extraction)",
            "headless": True,
        }
    return {
        "class_name": class_name,
        "method_name": method_name,
        "source": code,
        "note": "brace-matched extraction from the decompiled Java source",
    }


def _grep_sources(pattern: str) -> list[Dict[str, Any]]:
    rx = re.compile(re.escape(pattern), re.IGNORECASE)
    matches = []
    for path in _all_java_files():
        try:
            for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if rx.search(line):
                    matches.append({
                        "class_name": _class_name_of(path),
                        "file": str(path),
                        "line": i,
                        "snippet": line.strip()[:240],
                    })
                    if len(matches) >= MAX_GREP_MATCHES:
                        return matches
        except OSError:
            continue
    return matches


def _h_search_method(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    name = params.get("method_name", "")
    seen: set = set()
    matches = []
    for m in _grep_sources(name):
        if m["class_name"] in seen:
            continue
        seen.add(m["class_name"])
        matches.append({"class_name": m["class_name"], "first_seen": m["snippet"], "file": m["file"]})
    return {
        "method_name": name,
        "matches": matches,
        "total": len(matches),
        "note": "text-based search over the headless decompile (approximate)",
    }


def _h_search_classes(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    term = params.get("search_term", "")
    package = params.get("package", "")
    scopes = {s.strip() for s in (params.get("search_in", "code") or "code").split(",")}
    classes = []
    for path in _all_java_files():
        cname = _class_name_of(path)
        if package and not cname.startswith(package):
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        hit = None
        if "class" in scopes and term.lower() in cname.lower():
            hit = {"class_name": cname, "scope": "class", "snippet": cname}
        elif "code" in scopes and term.lower() in source.lower():
            for i, line in enumerate(source.splitlines(), 1):
                if term.lower() in line.lower():
                    hit = {"class_name": cname, "scope": "code", "line": i, "snippet": line.strip()[:240]}
                    break
        elif "method" in scopes and term.lower() in {m["name"].lower() for m in _parse_methods(source)}:
            hit = {"class_name": cname, "scope": "method", "snippet": f"method named '{term}'"}
        elif "field" in scopes and term.lower() in {f["declaration"].split()[-1].lstrip("*").rstrip(";").lower()
                                                     for f in _parse_fields(source)}:
            hit = {"class_name": cname, "scope": "field", "snippet": f"field mentioning '{term}'"}
        if hit:
            classes.append(hit)
            if len(classes) >= MAX_GREP_MATCHES:
                break
    return {"classes": _slice_page(classes, params), "total": len(classes), "headless_note": "text-based"}


def _h_xrefs(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    # text-based approximation: grep the symbol across sources
    symbol = (params.get("method_name") or params.get("field_name")
              or params.get("class_name") or "")
    simple = symbol.split(".")[-1].split("$")[-1]
    refs = [
        m for m in _grep_sources(simple)
        if m["class_name"] != params.get("class_name") or m["line"]
    ]
    refs = [r for r in refs if not (r["class_name"] == params.get("class_name", "")
                                    and re.search(rf"\b{re.escape(simple)}\b", r["snippet"])
                                    and "(" in r["snippet"] and params.get("method_name"))]
    return {
        "references": _slice_page(refs, params),
        "total": len(refs),
        "note": "text-based xrefs over the headless decompile (approximate — no call-graph)",
    }


def _h_manifest(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    path = _resources_dir() / "AndroidManifest.xml"
    if not path.is_file():
        raise HeadlessUnavailable(
            "AndroidManifest.xml not in the decompile resources — jadx runs with "
            "--no-res? Re-run with JADX_MCP_HEADLESS_REFRESH=1."
        )
    return {"content": path.read_text(encoding="utf-8", errors="replace"), "headless": True}


def _h_strings(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    strings = []
    values_dir = _resources_dir() / "res"
    for path in sorted(values_dir.glob("values*/strings.xml")) if values_dir.exists() else []:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in re.finditer(r'<string name="([^"]+)"[^>]*>(.*?)</string>', text, re.S):
            strings.append({"file": str(path), "name": m.group(1), "value": m.group(2).strip()})
    return {"strings": _slice_page(strings, params), "total": len(strings)}


def _h_resource_file(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    name = params.get("file_name", "")
    path = (_resources_dir() / name).resolve()
    if not str(path).startswith(str(_resources_dir().resolve())):
        return {"error": "path traversal refused", "headless": True}
    if not path.is_file():
        return {"error": f"resource '{name}' not found in the decompile", "headless": True}
    try:
        content = path.read_text(encoding="utf-8")
        binary = False
    except UnicodeDecodeError:
        content = path.read_bytes().decode("utf-8", errors="replace")
        binary = True
    return {
        "file_name": name,
        "content": content,
        "binary": binary,
        "note": "binary resources are decoded with replacement characters",
    }


def _h_package_tree(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for path in _all_java_files():
        parts = path.relative_to(_sources_dir()).parts[:-1]
        pkg = ".".join(parts)
        counts[pkg] = counts.get(pkg, 0) + 1
    packages = [
        {"name": pkg, "class_count": n, "is_likely_library": pkg.split(".")[0] in
         {"android", "androidx", "kotlin", "kotlinx", "com.google", "org.jetbrains", "org.apache", "io.reactivex"}}
        for pkg, n in sorted(counts.items(), key=lambda kv: -kv[1])
    ]
    return {
        "total_classes": sum(counts.values()),
        "total_packages": len(packages),
        "packages": packages,
    }


def _h_main_app_classes_names(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    manifest = (_resources_dir() / "AndroidManifest.xml")
    pkg = ""
    if manifest.is_file():
        m = re.search(r'<manifest[^>]*package="([^"]+)"', manifest.read_text(encoding="utf-8", errors="replace"))
        pkg = m.group(1) if m else ""
    names = sorted(c for c in (_class_name_of(p) for p in _all_java_files()) if pkg and c.startswith(pkg + "."))
    return {"package": pkg, "classes": names, "total": len(names)}


def _h_main_app_classes_code(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    names = _h_main_app_classes_names({}, info)["classes"]
    items = []
    for cname in names:
        try:
            _, source = _read_class(cname)
        except HeadlessUnavailable:
            continue
        items.append({"class_name": cname, "source": source})
    return {"classes": _slice_page(items, params), "total": len(items)}


def _h_main_activity(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    manifest_path = _resources_dir() / "AndroidManifest.xml"
    if not manifest_path.is_file():
        raise HeadlessUnavailable("AndroidManifest.xml not in the decompile resources")
    text = manifest_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(
        r'<activity[^>]*android:name="([^"]+)"[^>]*>(?:(?!</activity>).)*?'
        r'<action\s+android:name="android\.intent\.action\.MAIN"',
        text, re.S)
    if not m:
        return {"error": "no MAIN/LAUNCHER activity found in the manifest", "headless": True}
    cname = m.group(1).lstrip(".")
    if "." not in cname:
        pkg_m = re.search(r'<manifest[^>]*package="([^"]+)"', text)
        cname = f"{pkg_m.group(1)}.{cname}" if pkg_m else cname
    _, source = _read_class(cname)
    return {"class_name": cname, "source": source, "headless": True}


def _h_cache_stats(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    files = _all_java_files()
    mb = sum(f.stat().st_size for f in files if f.is_file()) / 1e6
    return {
        "headless": True,
        "cache_dir": str(_cache_dir()),
        "cached_classes": len(files),
        "original_mb": round(mb, 2),
        "note": "headless backend: the GUI's in-memory cache does not apply",
    }


def _h_clear_cache(params: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    if _cache_dir().exists():
        shutil.rmtree(_cache_dir(), ignore_errors=True)
    return {"status": "ok", "headless": True, "note": "headless decompile cache cleared"}


_GET_HANDLERS = {
    "class-source": _h_class_source,
    "all-classes": _h_all_classes,
    "methods-of-class": _h_methods_of_class,
    "fields-of-class": _h_fields_of_class,
    "method-by-name": _h_method_by_name,
    "search-method": _h_search_method,
    "search-classes-by-keyword": _h_search_classes,
    "xrefs-to-class": _h_xrefs,
    "xrefs-to-method": _h_xrefs,
    "xrefs-to-field": _h_xrefs,
    "manifest": _h_manifest,
    "strings": _h_strings,
    "get-resource-file": _h_resource_file,
    "package-tree": _h_package_tree,
    "main-application-classes-names": _h_main_app_classes_names,
    "main-application-classes-code": _h_main_app_classes_code,
    "main-activity": _h_main_activity,
    "cache-stats": _h_cache_stats,
    "clear-cache": _h_clear_cache,  # POST; the one mutating endpoint headless can serve
}


def _handle_sync(endpoint: str, params: Dict[str, Any], post: bool) -> Dict[str, Any]:
    """Worker-thread body for handle_get / handle_post."""
    if endpoint in GUI_REQUIRED_ENDPOINTS or (post and endpoint != "clear-cache"):
        return gui_required(endpoint)
    # runtime APK lifecycle: report honestly while the background decompile runs
    if _runtime["apk"] and _status["apk"] == _runtime["apk"]:
        if _status["state"] == "decompiling":
            return {
                "error": "headless decompilation is still in progress — "
                         "check the jadx_mode tool and retry shortly.",
                "headless": True,
            }
        if _status["state"] == "failed":
            return {
                "error": f"{_status['detail']} (call headless_set_apk again to retry)",
                "headless": True,
            }
    try:
        info = _decompile_locked()
    except HeadlessUnavailable as exc:
        return {"error": str(exc), "headless": True}
    handler = _GET_HANDLERS.get(endpoint)
    if handler is None:
        return gui_required(endpoint)
    try:
        result = handler(params or {}, info)
    except HeadlessUnavailable as exc:
        return {"error": str(exc), "headless": True}
    if isinstance(result, dict):
        result.setdefault("headless", True)
    return result


async def handle_get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    last_mode.update({"mode": "headless", "detail": f"served '{endpoint}' from the headless decompile"})
    return await asyncio.to_thread(_handle_sync, endpoint, params or {}, False)


async def handle_post(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    last_mode.update({"mode": "headless", "detail": f"POST '{endpoint}'"})
    return await asyncio.to_thread(_handle_sync, endpoint, params or {}, True)


def mode_report() -> Dict[str, Any]:
    report = dict(last_mode)
    report["configured"] = bool(active_apk())
    report["apk"] = active_apk() or ""
    report["runtime_override"] = _runtime["apk"] or ""
    report["state"] = _status["state"]
    report["cache_dir"] = str(_cache_dir())
    return report
