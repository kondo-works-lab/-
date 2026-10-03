import io
from pathlib import Path

import pandas as pd
import pytest

from expense_journal.classifier import classify_frame
from expense_journal.io import InputError, read_statement, to_csv_bytes, to_excel_bytes, to_journal
from expense_journal.rules_db import get_rules

SAMPLE = Path(__file__).resolve().parent.parent / "sample" / "sample_statement.csv"


def _csv(text: str, encoding="utf-8") -> io.BytesIO:
    return io.BytesIO(text.encode(encoding))


def test_read_sample_csv():
    with SAMPLE.open("rb") as f:
        df = read_statement(f, SAMPLE.name)
    assert list(df.columns) == ["日付", "摘要", "金額", "取引先"]
    assert len(df) == 12
    assert df.loc[0, "金額"] == 2480


def test_read_shift_jis_and_amount_formats():
    text = "日付,摘要,金額\n2026-09-01,タクシー,\"￥1,200\"\n2026/9/2,文具,300円\n"
    df = read_statement(_csv(text, "cp932"), "a.csv")
    assert df["金額"].tolist() == [1200, 300]
    assert str(df.loc[1, "日付"]) == "2026-09-02"


def test_missing_required_column():
    with pytest.raises(InputError, match="金額"):
        read_statement(_csv("日付,摘要\n2026/09/01,x\n"), "a.csv")


def test_invalid_rows_reported():
    with pytest.raises(InputError, match="日付を解釈できない行: 3"):
        read_statement(_csv("日付,摘要,金額\n2026/09/01,a,1\nfoo,b,2\n"), "a.csv")


def test_unsupported_extension():
    with pytest.raises(InputError):
        read_statement(_csv(""), "a.txt")


def test_excel_roundtrip_and_journal(tmp_path):
    src = pd.DataFrame({"日付": ["2026/09/01"], "摘要": ["タクシー"], "金額": ["1000"]})
    buf = io.BytesIO()
    src.to_excel(buf, index=False)
    buf.seek(0)
    df = read_statement(buf, "a.xlsx")
    classified = classify_frame(df, get_rules(tmp_path / "r.db"))
    journal = to_journal(classified, "未払金")
    assert journal.iloc[0].to_dict() == {
        "日付": "2026/09/01",
        "借方勘定科目": "旅費交通費",
        "借方金額": 1000,
        "貸方勘定科目": "未払金",
        "貸方金額": 1000,
        "摘要": "タクシー",
    }
    assert to_csv_bytes(journal).startswith(b"\xef\xbb\xbf")
    assert pd.read_excel(io.BytesIO(to_excel_bytes(journal))).shape == (1, 6)
