"""摘要のキーワード部分一致による勘定科目判定."""

from __future__ import annotations

import unicodedata

import pandas as pd

from .rules_db import FALLBACK_ACCOUNT, Rule


def normalize(text: object) -> str:
    """全角/半角・大文字/小文字の揺れを吸収する(NFKC + casefold)."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    return unicodedata.normalize("NFKC", str(text)).casefold()


def classify(description: object, rules: list[Rule]) -> tuple[str, str]:
    """優先度順にルールを評価し、最初にマッチした (勘定科目, キーワード) を返す.

    マッチしない場合は (雑費, "")。
    """
    target = normalize(description)
    if target:
        for rule in rules:
            if normalize(rule.keyword) in target:
                return rule.account, rule.keyword
    return FALLBACK_ACCOUNT, ""


def classify_frame(df: pd.DataFrame, rules: list[Rule]) -> pd.DataFrame:
    """取引明細に「勘定科目」「マッチキーワード」列を付与した DataFrame を返す."""
    ordered = sorted(rules, key=lambda r: r.id)
    results = [classify(d, ordered) for d in df["摘要"]]
    out = df.copy()
    out["勘定科目"] = [acc for acc, _ in results]
    out["マッチキーワード"] = [kw for _, kw in results]
    return out
