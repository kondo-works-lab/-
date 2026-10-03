from expense_journal.rules_db import SEED_RULES, account_choices, connect, get_rules, init_db


def test_seed_has_16_accounts_including_fallback(tmp_path):
    rules = get_rules(tmp_path / "rules.db")
    assert len(rules) == len(SEED_RULES)
    assert [r.id for r in rules] == sorted(r.id for r in rules)
    assert len(set(account_choices(rules))) == 16
    assert "雑費" in account_choices(rules)


def test_init_does_not_reseed_existing_table(tmp_path):
    path = tmp_path / "rules.db"
    with connect(path) as conn:
        init_db(conn)
        conn.execute("DELETE FROM rules WHERE id > 1")
        conn.commit()
        init_db(conn)
        assert conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0] == 1
