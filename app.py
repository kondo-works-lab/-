"""経費精算・仕訳自動化ツール(ルールベース版)Streamlit UI.

起動: streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from expense_journal.classifier import classify_frame
from expense_journal.io import (
    InputError,
    read_statement,
    to_csv_bytes,
    to_excel_bytes,
    to_journal,
)
from expense_journal.rules_db import account_choices, get_rules

STEPS = ["1. アップロード", "2. 判定結果の確認・編集", "3. ダウンロード"]
CREDIT_ACCOUNTS = ["未払金", "現金", "普通預金", "未払費用", "役員借入金"]

st.set_page_config(page_title="経費精算・仕訳自動化", layout="wide")


@st.cache_data
def load_rules():
    return get_rules()


def go(step: int) -> None:
    st.session_state.step = step


def reset() -> None:
    for key in ("step", "classified", "confirmed", "filename"):
        st.session_state.pop(key, None)


st.session_state.setdefault("step", 0)
rules = load_rules()
accounts = account_choices(rules)

st.title("経費精算・仕訳自動化ツール")
st.caption("ルールベース判定・完全オフライン動作(取引明細は外部に送信されません)")
st.progress((st.session_state.step + 1) / len(STEPS), text=STEPS[st.session_state.step])

# ---- Step 1: アップロード ----
if st.session_state.step == 0:
    st.markdown("必須列: **日付 / 摘要 / 金額**(任意: 取引先)。CSV は UTF-8 / Shift_JIS に対応。")
    uploaded = st.file_uploader("取引明細ファイル", type=["csv", "xlsx"])
    if uploaded is not None:
        try:
            statement = read_statement(uploaded, uploaded.name)
        except InputError as e:
            st.error(str(e))
        else:
            st.success(f"{len(statement)} 件の取引を読み込みました。")
            st.dataframe(statement, hide_index=True, width="stretch")
            if st.button("勘定科目を自動判定", type="primary"):
                st.session_state.classified = classify_frame(statement, rules)
                st.session_state.filename = uploaded.name
                go(1)
                st.rerun()

    with st.expander(f"現在の仕訳ルール({len(rules)} 件・上から優先)"):
        st.dataframe(
            pd.DataFrame([r.__dict__ for r in rules]).rename(
                columns={"id": "優先度", "keyword": "キーワード", "account": "勘定科目", "note": "備考"}
            ),
            hide_index=True,
            width="stretch",
        )

# ---- Step 2: 判定結果の確認・編集 ----
elif st.session_state.step == 1:
    df: pd.DataFrame = st.session_state.classified
    unmatched = int((df["マッチキーワード"] == "").sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("取引件数", len(df))
    c2.metric("ルール一致", len(df) - unmatched)
    c3.metric("未一致(雑費)", unmatched)
    st.markdown("「勘定科目」列はクリックして修正できます。未一致の行は雑費になっています。")

    column_order = ["日付", "摘要"] + (["取引先"] if "取引先" in df.columns else []) + [
        "金額",
        "勘定科目",
        "マッチキーワード",
    ]
    edited = st.data_editor(
        df,
        column_order=column_order,
        disabled=[c for c in df.columns if c != "勘定科目"],
        column_config={
            "日付": st.column_config.DateColumn("日付", format="YYYY/MM/DD"),
            "金額": st.column_config.NumberColumn("金額", format="%d"),
            "勘定科目": st.column_config.SelectboxColumn("勘定科目", options=accounts, required=True),
            "マッチキーワード": st.column_config.TextColumn("マッチキーワード", help="空欄はルール未一致"),
        },
        hide_index=True,
        width="stretch",
        key="editor",
    )

    st.subheader("科目別合計")
    st.dataframe(
        edited.groupby("勘定科目", as_index=False)["金額"].sum().sort_values("金額", ascending=False),
        hide_index=True,
    )

    b1, b2 = st.columns([1, 5])
    if b1.button("← 戻る"):
        reset()
        st.rerun()
    if b2.button("確定", type="primary"):
        st.session_state.confirmed = edited
        go(2)
        st.rerun()

# ---- Step 3: ダウンロード ----
else:
    confirmed: pd.DataFrame = st.session_state.confirmed
    credit = st.selectbox("貸方勘定科目", CREDIT_ACCOUNTS, help="全仕訳の貸方に適用されます")
    journal = to_journal(confirmed, credit)
    st.dataframe(journal, hide_index=True, width="stretch")
    st.metric("合計金額", f"{journal['借方金額'].sum():,.0f} 円")

    stem = st.session_state.get("filename", "journal").rsplit(".", 1)[0]
    d1, d2, d3 = st.columns([1, 1, 4])
    d1.download_button(
        "CSV をダウンロード", to_csv_bytes(journal), f"{stem}_仕訳.csv", "text/csv", type="primary"
    )
    d2.download_button(
        "Excel をダウンロード",
        to_excel_bytes(journal),
        f"{stem}_仕訳.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    if d3.button("← 編集に戻る"):
        go(1)
        st.rerun()
    if st.button("最初からやり直す"):
        reset()
        st.rerun()
