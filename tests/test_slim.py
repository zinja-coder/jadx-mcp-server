"""
Unit tests for Kotlin metadata slimming (src/server/slim.py).

Slimming must never change the line count of a dump. The server numbers lines
in `get_class_source(with_line_numbers=True)` from the same decompiled string
the plugin serves, and the plugin resolves `add_comment(line=N)` against that
string split on newlines, so a removed line would silently retarget a later
comment.

`tests/fixtures/jadx_kotlin_class_real.java` is an unmodified jadx 1.5.5 dump of
kotlin.Pair from kotlin-stdlib 2.2.20 (Apache-2.0). It is kept verbatim so the
assertions run against real decompiler output rather than a hand-made sample.
"""

import unittest
from pathlib import Path

from src.server.slim import SLIM_MARKER, slim_payload, slim_source

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# A coroutine class as JADX writes it. The annotation strings hold the things
# that break a naive paren matcher: descriptors with parentheses, braces,
# escaped quotes and $ names.
COROUTINE_DUMP = """package com.example;

/* JADX INFO: compiled from: Repo.kt */
/* JADX INFO: loaded from: classes.dex */
@DebugMetadata(c = "com.example.Repo$refresh$1", f = "Repo.kt", i = {0, 0, 1}, l = {42, 51}, m = "invokeSuspend", n = {"$this$launch", "page", "it"}, s = {"L$0", "I$0", "L$1"})
final class Repo$refresh$1 extends kotlin.coroutines.jvm.internal.SuspendLambda implements kotlin.jvm.functions.Function2<kotlinx.coroutines.CoroutineScope, kotlin.coroutines.Continuation<? super kotlin.Unit>, java.lang.Object> {
    int I$0;

    @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
    public final kotlin.coroutines.Continuation<kotlin.Unit> create(java.lang.Object obj, kotlin.coroutines.Continuation<?> continuation) {
        return new Repo$refresh$1(null);
    }
}"""

# Two lines of annotation whose strings contain parentheses, braces and an
# escaped quote, followed by the declaration that must stay on its line.
MULTILINE_DUMP = """@Metadata(mv = {1, 9, 0},
    d2 = {"Lcom/x/Y;", "(I)V", "()V", "say(\\"hi\\")"})
public final class Y {
    @Override
    public String toString() {
        return "(I)V";
    }
}"""


def _line_count(text: str) -> int:
    return text.count("\n")


class SlimSourceTests(unittest.TestCase):
    def test_real_jadx_kotlin_dump_is_slimmed(self):
        code = (FIXTURES / "jadx_kotlin_class_real.java").read_text(encoding="utf-8")

        self.assertIn("@Metadata(", code)
        slimmed = slim_source(code)

        self.assertNotIn("@Metadata(", slimmed)
        self.assertEqual(_line_count(slimmed), _line_count(code))
        # The declaration the annotation was attached to is untouched.
        self.assertIn("public final /* data */ class Pair<A, B> implements Serializable {", slimmed)
        # Only compiler metadata goes; real annotations stay.
        self.assertIn("@NotNull", slimmed)
        self.assertIn("@Nullable", slimmed)
        # This dump is ~46% metadata, so the saving has to be large.
        saved = 1 - (len(slimmed) / len(code))
        self.assertGreater(saved, 0.4, f"only {saved:.1%} saved")

    def test_real_dump_keeps_every_other_line_identical(self):
        code = (FIXTURES / "jadx_kotlin_class_real.java").read_text(encoding="utf-8")
        slimmed = slim_source(code)

        before = code.split("\n")
        after = slimmed.split("\n")
        self.assertEqual(len(before), len(after))
        for index, (old, new) in enumerate(zip(before, after), start=1):
            if "@Metadata(" in old:
                # Replaced in place, so the line keeps its position.
                self.assertTrue(new.startswith(SLIM_MARKER), f"line {index}: {new!r}")
            else:
                self.assertEqual(old, new, f"line {index} changed")

    def test_coroutine_metadata_is_slimmed(self):
        slimmed = slim_source(COROUTINE_DUMP)

        self.assertNotIn("@DebugMetadata(", slimmed)
        self.assertEqual(_line_count(slimmed), _line_count(COROUTINE_DUMP))
        self.assertIn("final class Repo$refresh$1 extends", slimmed)
        self.assertIn("@Override", slimmed)
        # JADX INFO lines are informational, not compiler payload: they stay.
        self.assertIn("/* JADX INFO: compiled from: Repo.kt */", slimmed)

    def test_multiline_annotation_keeps_line_count_and_declaration(self):
        slimmed = slim_source(MULTILINE_DUMP)
        after = slimmed.split("\n")

        self.assertNotIn("@Metadata(", slimmed)
        self.assertEqual(_line_count(slimmed), _line_count(MULTILINE_DUMP))
        self.assertEqual(after[0], SLIM_MARKER)
        # The declaration keeps its line index, which is what the numbering
        # contract needs: it was line 3 before and is still line 3.
        self.assertEqual(after[2], "public final class Y {")
        self.assertEqual(MULTILINE_DUMP.split("\n")[2], "public final class Y {")
        self.assertIn('return "(I)V";', slimmed)

    def test_metadata_inside_string_literal_is_left_alone(self):
        code = 'class A {\n    String s = "@Metadata(d1 = {\\"keep me\\"})";\n}\n'
        self.assertEqual(slim_source(code), code)

    def test_metadata_inside_comments_is_left_alone(self):
        code = "// @Metadata(d1 = {}) in a line comment\n/* @DebugMetadata(c = \"x\") */\nclass A {}\n"
        self.assertEqual(slim_source(code), code)

    def test_lookalike_annotations_are_left_alone(self):
        code = '@MyMetadata(k = 1)\n@MetadataHolder\n@DebugMetadatas\nclass A {}\n'
        self.assertEqual(slim_source(code), code)

    def test_qualified_annotation_names_are_slimmed(self):
        code = '@kotlin.Metadata(mv = {1, 9, 0}, d1 = {"\\u0000"})\nclass A {}\n'
        slimmed = slim_source(code)
        self.assertNotIn("@kotlin.Metadata(", slimmed)
        self.assertEqual(_line_count(slimmed), _line_count(code))
        self.assertIn("class A {}", slimmed)

        debug = '@kotlin.coroutines.jvm.internal.DebugMetadata(c = "A$f$1")\nclass B {}\n'
        self.assertNotIn("@DebugMetadata(", slim_source(debug))

    def test_inline_annotation_keeps_rest_of_the_line(self):
        code = "@Metadata(k = 1) public final class A {}\n"
        slimmed = slim_source(code)

        self.assertEqual(slimmed, f"{SLIM_MARKER} public final class A {{}}\n")
        self.assertEqual(_line_count(slimmed), _line_count(code))

    def test_unterminated_metadata_is_returned_unchanged(self):
        code = '@Metadata(d1 = {"never closed\nclass A {}\n'
        self.assertEqual(slim_source(code), code)

    def test_plain_java_dump_is_a_noop(self):
        code = "package a;\n\nclass A {\n    String s = \"nope\";\n}\n"
        self.assertIs(slim_source(code), code)

    def test_slimming_is_idempotent(self):
        code = (FIXTURES / "jadx_kotlin_class_real.java").read_text(encoding="utf-8")
        once = slim_source(code)
        self.assertEqual(slim_source(once), once)


class SlimPayloadTests(unittest.TestCase):
    METADATA = '@Metadata(mv = {1, 9, 0}, d1 = {"\\u0000\\n\\u0002"}, d2 = {"Lcom/x;", "()V"})\nclass A {}\n'

    def test_class_dump_shape(self):
        # /class-source is plain text, so get_from_jadx wraps it as "response".
        result = slim_payload({"response": self.METADATA})
        self.assertNotIn("@Metadata(", result["response"])
        self.assertEqual(sorted(result), ["response"])

    def test_current_class_and_activity_shape(self):
        for key in ("content", "code"):
            result = slim_payload({"name": "com.x.A", "type": "code/java", key: self.METADATA})
            self.assertNotIn("@Metadata(", result[key], key)
            self.assertEqual(result["name"], "com.x.A")

    def test_paginated_class_list_is_slimmed_per_class(self):
        result = slim_payload(
            {
                "classes": [
                    {"name": "com.x.A", "type": "code/java", "content": self.METADATA},
                    {"name": "com.x.B", "type": "code/java", "content": self.METADATA},
                ],
                "total": 2,
            }
        )
        self.assertEqual(result["total"], 2)
        self.assertEqual(len(result["classes"]), 2)
        for entry in result["classes"]:
            self.assertNotIn("@Metadata(", entry["content"])

    def test_strings_under_other_keys_are_never_touched(self):
        payload = {"name": "@Metadata(k = 1)", "error": "@Metadata(k = 1)"}
        self.assertIs(slim_payload(payload), payload)

    def test_bare_string_payload_is_slimmed(self):
        self.assertNotIn("@Metadata(", slim_payload(self.METADATA))

    def test_payload_without_metadata_is_returned_as_is(self):
        payload = {"response": "class A {}"}
        self.assertIs(slim_payload(payload), payload)


if __name__ == "__main__":
    unittest.main()
