# Sample Vault For Tests

This committed mini vault exists so Hub_ML content checks can run without the
private Obsidian vault.

Run the end-to-end gate against this fixture:

```bash
VAULT_PATH=tests/fixtures/sample_vault python tools/check_content_gate.py --reaudit
```

Expected behavior: at least one topic passes and at least one topic fails. The
fixture is intentionally small, so it is not meant to represent full course
coverage.
