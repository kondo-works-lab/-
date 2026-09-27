import pandas as pd
import pytest

from expense_journal.classifier import classify, classify_frame
from expense_journal.rules_db import Rule, get_rules


@pytest.fixture
def rules(tmp_path):
    return get_rules(tmp_path / "rules.db")


@pytest.mark.parametrize(
    "description, expected",
    [
        ("タクシー代 渋谷→品川", "旅費交通費"),
        ("Amazon Kindle ビジネス書", "新聞図書費"),
        ("Amazon コピー用紙", "消耗品費"),
        ("ゆうパック 郵便局", "荷造運賃"),
        ("取引先と会食", "接待交際費"),
        ("振込手数料", "支払手数料"),
        ("ガスト ランチ", "雑費"),  # 「ガス」誤マッチしない
        ("謎の支払い", "雑費"),
        ("", "雑費"),
    ],
)
def test_classify_seed_rules(rules, description, expected):
    assert classify(description, rules)[0] == expected


def test_normalizes_width_and_case(rules):
    # 全角英字・小文字でも一致する
    assert classify("amazon 文具", rules)[0] == "消耗品費"
    assert classify("SUICA チャージ", rules)[0] == "旅費交通費"


def test_first_rule_by_priority_wins():
    rules = [Rule(2, "会議", "会議費", ""), Rule(1, "会", "接待交際費", "")]
    df = pd.DataFrame({"摘要": ["会議 弁当"]})
    out = classify_frame(df, rules)
    assert out.loc[0, "勘定科目"] == "接待交際費"
    assert out.loc[0, "マッチキーワード"] == "会"


def test_nan_description_falls_back():
    assert classify(float("nan"), [Rule(1, "a", "x", "")]) == ("雑費", "")
