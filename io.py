"""取引明細の読み込みと仕訳データの出力."""

from __future__ import annotations

import io
from typing import BinaryIO

import pandas as pd

REQUIRED_COLUMNS = ["日付", "摘要", "金額"]
OPTIONAL_COLUMNS = ["取引先"]
CSV_ENCODINGS = ("utf-8-sig", "cp932")


class InputError(ValueError):
    """取引明細の形式不備."""


def read_statement(file: BinaryIO, filename: str) -> pd.DataFrame:
    """CSV / Excel を読み込み、日付・摘要・金額(・取引先)に整形して返す."""
    name = filename.lower()
    raw = file.read()
    if name.endswith(".csv"):
        df = _read_csv(raw)
    elif name.endswith((".xlsx", ".xlsm")):
        df = pd.read_excel(io.BytesIO(raw), dtype=str)
    else:
        raise InputError("対応形式は CSV(.csv)または Excel(.xlsx)です。")
    return _normalize(df)


def _read_csv(raw: bytes) -> pd.DataFrame:
    for enc in CSV_ENCODINGS:
        try:
            return pd.read_csv(io.BytesIO(raw), dtype=str, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise InputError("CSV の文字コードを判別できません(UTF-8 または Shift_JIS に対応)。")


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=lambda c: str(c).strip())
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise InputError(f"必須列がありません: {', '.join(missing)}")

    columns = REQUIRED_COLUMNS + [c for c in OPTIONAL_COLUMNS if c in df.columns]
    df = df[columns].dropna(how="all").reset_index(drop=True)

    dates = pd.to_datetime(df["日付"].str.strip(), errors="coerce", format="mixed")
    bad_dates = df.index[dates.isna()].tolist()
    # 全角数字・全角記号を NFKC で半角化してから、桁区切り・通貨記号を除去する
    amounts = pd.to_numeric(
        df["金額"].astype(str).str.normalize("NFKC").str.replace(r"[,¥\\円\s]", "", regex=True),
        errors="coerce",
    )
    bad_amounts = df.index[amounts.isna()].tolist()
    if bad_dates or bad_amounts:
        msgs = []
        if bad_dates:
            msgs.append(f"日付を解釈できない行: {_rows(bad_dates)}")
        if bad_amounts:
            msgs.append(f"金額を解釈できない行: {_rows(bad_amounts)}")
        raise InputError(" / ".join(msgs))

    df["日付"] = dates.dt.date
    df["金額"] = amounts
    df["摘要"] = df["摘要"].fillna("").astype(str).str.strip()
    if "取引先" in df.columns:
        df["取引先"] = df["取引先"].fillna("").astype(str).str.strip()
    return df


def _rows(indexes: list[int]) -> str:
    # ヘッダ行を 1 行目として、データ行はファイル上の行番号で表示する
    return ", ".join(str(i + 2) for i in indexes[:10]) + (" ほか" if len(indexes) > 10 else "")


def to_journal(df: pd.DataFrame, credit_account: str) -> pd.DataFrame:
    """判定・修正済みの明細を仕訳データ(借方/貸方形式)に変換する."""
    journal = pd.DataFrame(
        {
            "日付": pd.to_datetime(df["日付"]).dt.strftime("%Y/%m/%d"),
            "借方勘定科目": df["勘定科目"],
            "借方金額": df["金額"],
            "貸方勘定科目": credit_account,
            "貸方金額": df["金額"],
            "摘要": df["摘要"],
        }
    )
    if "取引先" in df.columns:
        journal["取引先"] = df["取引先"]
    return journal.reset_index(drop=True)


def to_csv_bytes(journal: pd.DataFrame) -> bytes:
    # Excel で文字化けしないよう BOM 付き UTF-8
    return journal.to_csv(index=False).encode("utf-8-sig")


def to_excel_bytes(journal: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        journal.to_excel(writer, index=False, sheet_name="仕訳")
    return buf.getvalue()
