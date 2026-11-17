"""Tests for the headless fallback backend (src/server/headless.py).

The fixtures are a fake jadx decompile tree (sources/ + resources/) — no
jadx binary and no GUI involved. The config.py seam is exercised too:
a ConnectError must route get_from_jadx into the headless handlers.
"""

import asyncio
import os
import re
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.server import headless  # noqa: E402

# captured before any fixture patches module attributes
REAL_DECOMPILE = headless._decompile_locked

SAMPLE_JAVA = """package com.example.app;

public class MainActivity {
    private static final String TAG = "MainActivity";
    public int counter = 0;

    public void onCreate() {
        start();
    }

    private int start() {
        return counter;
    }
}
"""


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """A fake jadx decompile tree + env pointing the headless backend at it."""
    sources = tmp_path / "proj" / "sources"
    resources = tmp_path / "proj" / "resources"
    (sources / "com/example/app").mkdir(parents=True)
    (resources / "res" / "values").mkdir(parents=True)
    (sources / "com/example/app/MainActivity.java").write_text(SAMPLE_JAVA)
    (sources / "com/example/app/Util.java").write_text(
        "package com.example.app;\npublic class Util {\n    public Util() {\n    }\n}\n")
    (resources / "AndroidManifest.xml").write_text(
        '<manifest package="com.example.app">\n<application>\n'
        '<activity android:name=".MainActivity">'
        '<intent-filter><action android:name="android.intent.action.MAIN"/>'
        '</intent-filter></activity></application></manifest>\n')
    (resources / "res/values/strings.xml").write_text(
        '<resources><string name="app_name">Demo</string></resources>\n')
    monkeypatch.setenv("JADX_MCP_HEADLESS_APK", str(tmp_path / "demo.apk"))
    monkeypatch.setattr(headless, "CACHE_ROOT", tmp_path / "cache")
    # point the cache at the pre-built tree (skip the jadx CLI entirely)
    monkeypatch.setattr(headless, "_cache_dir", lambda: tmp_path / "proj")
    monkeypatch.setattr(headless, "_decompile_locked", lambda: {"apk": "demo.apk", "classes": 2})
    return tmp_path


# ── tree-backed handlers ──────────────────────────────────────────────────

def test_class_source_reads_file(tree):
    out = headless._handle_sync("class-source", {"class_name": "com.example.app.MainActivity"}, False)
    assert "headless" in out
    assert "public class MainActivity" in out["response"]
    assert out["source_path"].endswith("MainActivity.java")


def test_class_source_missing_class_is_honest(tree):
    out = headless._handle_sync("class-source", {"class_name": "com.example.app.Ghost"}, False)
    assert "error" in out
    assert "get_all_classes" in out["error"]


def test_all_classes_and_pagination(tree):
    out = headless._handle_sync("all-classes", {"offset": 0, "count": 0}, False)
    assert out["total"] == 2
    assert out["classes"] == ["com.example.app.MainActivity", "com.example.app.Util"]
    paged = headless._handle_sync("all-classes", {"offset": 1, "count": 1}, False)
    assert paged["classes"] == ["com.example.app.Util"]


def test_methods_and_fields_parsed(tree):
    out = headless._handle_sync("methods-of-class", {"class_name": "com.example.app.MainActivity"}, False)
    names = [m["name"] for m in out["methods"]]
    assert "onCreate" in names and "start" in names
    fields = headless._handle_sync("fields-of-class", {"class_name": "com.example.app.MainActivity"}, False)
    decls = " ".join(f["declaration"] for f in fields["fields"])
    assert "TAG" in decls and "counter" in decls


def test_method_by_name_brace_matched(tree):
    out = headless._handle_sync(
        "method-by-name", {"class_name": "com.example.app.MainActivity", "method_name": "start"}, False)
    assert out["source"].strip().startswith("private int start()")
    assert "return counter" in out["source"]


def test_manifest_and_strings(tree):
    manifest = headless._handle_sync("manifest", {}, False)
    assert 'package="com.example.app"' in manifest["content"]
    strings = headless._handle_sync("strings", {"offset": 0, "count": 0}, False)
    assert strings["strings"][0]["name"] == "app_name"
    assert strings["strings"][0]["value"] == "Demo"


def test_main_activity_resolved_from_manifest(tree):
    out = headless._handle_sync("main-activity", {}, False)
    assert out["class_name"] == "com.example.app.MainActivity"
    assert "public class MainActivity" in out["source"]


def test_xrefs_are_text_based_and_exclude_the_definition_file_check(tree):
    out = headless._handle_sync(
        "xrefs-to-method", {"class_name": "com.example.app.MainActivity", "method_name": "start"}, False)
    assert "approximate" in out["note"]  # text-based, no call graph — labeled honestly
    assert isinstance(out["references"], list)


def test_package_tree_shape(tree):
    out = headless._handle_sync("package-tree", {}, False)
    assert out["total_classes"] == 2
    pkg = out["packages"][0]
    assert pkg["name"] == "com.example.app" and pkg["class_count"] == 2
    assert pkg["is_likely_library"] is False


def test_main_app_classes_filtered_by_manifest_package(tree):
    out = headless._handle_sync("main-application-classes-names", {}, False)
    assert out["package"] == "com.example.app"
    assert out["classes"] == ["com.example.app.MainActivity", "com.example.app.Util"]


def test_resource_file_and_traversal_refusal(tree):
    out = headless._handle_sync("get-resource-file", {"file_name": "res/values/strings.xml"}, False)
    assert "Demo" in out["content"]
    evil = headless._handle_sync("get-resource-file", {"file_name": "../../../etc/passwd"}, False)
    assert "refused" in evil["error"]


# ── GUI-required endpoints degrade honestly ───────────────────────────────

@pytest.mark.parametrize("endpoint", ["current-class", "selected-text", "smali-of-class",
                                      "rename-method", "debug-get-threads", "add-comment"])
def test_gui_required_endpoints(tree, endpoint):
    out = headless._handle_sync(endpoint, {}, False)
    assert out["gui_required"] is True
    assert "JADX-GUI" in out["error"]


def test_gui_required_post(tree):
    out = headless._handle_sync("rename-class", {}, True)
    assert out["gui_required"] is True


def test_clear_cache_post_is_handled(tree, tmp_path):
    cache = tmp_path / "cache" / "demo"
    cache.mkdir(parents=True)
    monkey_old = headless._cache_dir
    headless._cache_dir = lambda: cache
    try:
        out = headless._handle_sync("clear-cache", {}, True)
        assert out["status"] == "ok"
        assert not cache.exists()
    finally:
        headless._cache_dir = monkey_old


# ── unconfigured / failed decompile ───────────────────────────────────────

def test_unconfigured_reports_how_to_enable(tmp_path, monkeypatch):
    monkeypatch.delenv("JADX_MCP_HEADLESS_APK", raising=False)
    monkeypatch.setattr(headless, "_cache_dir", lambda: tmp_path / "c")
    monkeypatch.setattr(headless, "_decompile_locked", REAL_DECOMPILE)
    out = headless._handle_sync("class-source", {"class_name": "x"}, False)
    assert "JADX_MCP_HEADLESS_APK" in out["error"]


# ── the config.py seam: ConnectError routes to headless ───────────────────

def test_get_from_jadx_falls_back_on_connect_error(tree):
    from src.server import config

    async def run():
        return await config.get_from_jadx("all-classes", {"offset": 0, "count": 0})

    # port 1 refuses connections instantly — no GUI plugin there
    monkey_old = config.JADX_HTTP_BASE
    config.JADX_HTTP_BASE = "http://127.0.0.1:1"
    try:
        result = asyncio.run(run())
    finally:
        config.JADX_HTTP_BASE = monkey_old
    assert result.get("total") == 2
    assert result.get("headless") is True


def test_connect_error_without_apk_config_reports_setup_hint(tree, monkeypatch):
    from src.server import config

    monkeypatch.delenv("JADX_MCP_HEADLESS_APK", raising=False)
    # the tree fixture patched both; restore the real ones for this test
    monkeypatch.setattr(headless, "_decompile_locked", REAL_DECOMPILE)
    real_cache_dir = lambda: headless.CACHE_ROOT / re.sub(  # noqa: E731
        r"[^A-Za-z0-9._-]", "_", Path(os.environ.get("JADX_MCP_HEADLESS_APK", "apk")).stem)
    monkeypatch.setattr(headless, "_cache_dir", real_cache_dir)

    async def run():
        return await config.get_from_jadx("class-source", {"class_name": "x"})

    monkey_old = config.JADX_HTTP_BASE
    config.JADX_HTTP_BASE = "http://127.0.0.1:1"
    try:
        result = asyncio.run(run())
    finally:
        config.JADX_HTTP_BASE = monkey_old
    assert "error" in result
    assert "JADX_MCP_HEADLESS_APK" in result["error"]
