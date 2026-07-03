#!/usr/bin/env python3
"""Unit tests for the deterministic core of pulido.
No network / no Ollama: ollama_chat is exercised only via a monkeypatched urlopen.
Run: python3 tests/test_pulido.py   (or: pytest)
"""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pulido  # noqa: E402


class TestGlossary(unittest.TestCase):
    def test_default_fixes(self):
        rules = pulido.load_glossary(user_path="")  # "" => no user file
        out = pulido.apply_glossary("i used cloud code and chat gpt", rules)
        self.assertIn("Claude Code", out)
        self.assertIn("ChatGPT", out)

    def test_word_boundaries(self):
        rules = pulido.load_glossary(user_path="")
        self.assertEqual(pulido.apply_glossary("encloud coded stays", rules), "encloud coded stays")

    def test_case_insensitive(self):
        rules = pulido.load_glossary(user_path="")
        self.assertEqual(pulido.apply_glossary("CLOUD CODE", rules), "Claude Code")

    def test_user_glossary_merges_over_default(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"penguin ally": "Penguin Alley"}, f)
            path = f.name
        try:
            rules = pulido.load_glossary(user_path=path)
            out = pulido.apply_glossary("cloud code at penguin ally", rules)
            self.assertIn("Claude Code", out)     # default still applies
            self.assertIn("Penguin Alley", out)   # user entry applied
        finally:
            os.unlink(path)


class TestSanitize(unittest.TestCase):
    def test_strips_think_blocks(self):
        self.assertEqual(pulido.sanitize("<think>reasoning</think>hola"), "hola")

    def test_strips_wrapping_quotes(self):
        self.assertEqual(pulido.sanitize('"hola mundo"'), "hola mundo")
        self.assertEqual(pulido.sanitize("“hola”"), "hola")

    def test_keeps_inner_quotes(self):
        self.assertEqual(pulido.sanitize('di "hola" fuerte'), 'di "hola" fuerte')

    def test_collapses_blank_lines(self):
        self.assertEqual(pulido.sanitize("a\n\n\n\nb"), "a\n\nb")


class TestModes(unittest.TestCase):
    def test_all_modes_present(self):
        for m in ("clean", "prompt", "teams-es", "teams-en", "linkedin", "notes"):
            self.assertIn(m, pulido.MODES)
            self.assertTrue(pulido.MODES[m]["desc"])
            self.assertTrue(pulido.MODES[m]["prompt"])

    def test_build_system_contains_base_and_mode(self):
        s = pulido.build_system("teams-es")
        self.assertIn("ONLY the cleaned text", s)
        self.assertIn("Spanish", s)

    def test_voice_modes_ban_em_dashes(self):
        for m in ("teams-es", "teams-en", "linkedin"):
            self.assertIn("em dash", pulido.build_system(m).lower())


class TestOllamaChat(unittest.TestCase):
    def _fake_response(self, content):
        body = json.dumps({"message": {"role": "assistant", "content": content}}).encode()
        resp = mock.MagicMock()
        resp.read.return_value = body
        resp.__enter__ = lambda s: s
        resp.__exit__ = mock.MagicMock(return_value=False)
        return resp

    def test_payload_and_extraction(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["payload"] = json.loads(req.data.decode())
            return self._fake_response("  limpio  ")

        with mock.patch.object(pulido.request, "urlopen", fake_urlopen):
            out = pulido.ollama_chat("m1", "sys", "raw", "http://x:1")
        self.assertEqual(out, "  limpio  ")
        p = captured["payload"]
        self.assertEqual(p["model"], "m1")
        self.assertFalse(p["stream"])
        self.assertFalse(p["think"])
        self.assertEqual(p["messages"][1]["content"], "raw")
        self.assertEqual(captured["url"], "http://x:1/api/chat")

    def test_retries_without_think_on_error(self):
        calls = []

        def fake_urlopen(req, timeout=None):
            payload = json.loads(req.data.decode())
            calls.append(payload)
            if "think" in payload:
                raise pulido.error.HTTPError(
                    req.full_url, 400, "bad", {},
                    io.BytesIO(b'{"error":"model does not support think"}'),
                )
            return self._fake_response("ok")

        with mock.patch.object(pulido.request, "urlopen", fake_urlopen):
            out = pulido.ollama_chat("m1", "sys", "raw", "http://x:1")
        self.assertEqual(out, "ok")
        self.assertEqual(len(calls), 2)
        self.assertNotIn("think", calls[1])


class TestEnsureLocal(unittest.TestCase):
    def test_refuses_remote(self):
        with self.assertRaises(SystemExit):
            pulido.ensure_local("http://evil.example.com:11434")

    def test_refuses_dns_loopback_lookalike(self):
        # a hostname that merely starts with 127. is not a loopback IP
        with self.assertRaises(SystemExit):
            pulido.ensure_local("http://127.evil.example:11434")

    def test_allows_loopback(self):
        self.assertEqual(pulido.ensure_local("http://localhost:11434"), "http://localhost:11434")
        self.assertEqual(pulido.ensure_local("http://127.0.0.1:9999"), "http://127.0.0.1:9999")
        self.assertEqual(pulido.ensure_local("http://127.5.5.5:11434"), "http://127.5.5.5:11434")
        self.assertEqual(pulido.ensure_local("http://[::1]:11434"), "http://[::1]:11434")


class TestClipboard(unittest.TestCase):
    def test_get_surfaces_subprocess_failure(self):
        fail = mock.MagicMock(returncode=1, stdout="", stderr="Error: no display")
        with mock.patch.object(pulido, "_clip_cmds", return_value=(["xclip"], ["xclip"])), \
             mock.patch.object(pulido.subprocess, "run", return_value=fail):
            with self.assertRaises(SystemExit):
                pulido.clipboard_get()

    def test_get_raises_when_no_tool(self):
        with mock.patch.object(pulido, "_clip_cmds", return_value=(None, None)):
            with self.assertRaises(SystemExit):
                pulido.clipboard_get()


class TestMain(unittest.TestCase):
    def test_stdin_to_stdout(self):
        with mock.patch.object(pulido, "ollama_chat", return_value="<think>x</think>Hola, Claude Code."), \
             mock.patch.object(pulido.sys, "stdin", io.StringIO("hola cloud code")), \
             mock.patch.object(pulido.sys, "stdout", new_callable=io.StringIO) as out:
            rc = pulido.main(["--mode", "clean"])
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue().strip(), "Hola, Claude Code.")

    def test_whitespace_stdin_fails_even_with_clipboard(self):
        with mock.patch.object(pulido.sys, "stdin", io.StringIO("   ")), \
             mock.patch.object(pulido, "clipboard_get", return_value="contenido real"), \
             mock.patch.object(pulido, "ollama_chat") as chat:
            rc = pulido.main(["--mode", "clean"])
        self.assertEqual(rc, 1)
        chat.assert_not_called()

    def test_empty_stdin_falls_back_to_clipboard(self):
        written = {}
        with mock.patch.object(pulido, "ollama_chat", return_value="listo"), \
             mock.patch.object(pulido.sys, "stdin", io.StringIO("")), \
             mock.patch.object(pulido, "clipboard_get", return_value="hola cloud code"), \
             mock.patch.object(pulido, "clipboard_set", side_effect=lambda t: written.setdefault("out", t)), \
             mock.patch.object(pulido.sys, "stdout", new_callable=io.StringIO):
            rc = pulido.main(["--mode", "clean"])
        self.assertEqual(rc, 0)
        self.assertEqual(written["out"], "listo")

    def test_list_modes(self):
        with mock.patch.object(pulido.sys, "stdout", new_callable=io.StringIO) as out:
            rc = pulido.main(["--list-modes"])
        self.assertEqual(rc, 0)
        self.assertIn("teams-es", out.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
