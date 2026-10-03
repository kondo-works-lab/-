"""仕訳ルールを保持する SQLite データベースの操作."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "rules.db"
FALLBACK_ACCOUNT = "雑費"

# (keyword, account, note)。リスト順が優先度(id 昇順)になる。
# 部分一致のため、より具体的なキーワードを先に置く(例:「Kindle」を「Amazon」より前)。
# 短い英字(au, ANA 等)や汎用語(ガス→ガスト等)は誤マッチしやすいので避けている。
SEED_RULES: list[tuple[str, str, str]] = [
    # 旅費交通費
    ("タクシー", "旅費交通費", ""),
    ("JR", "旅費交通費", ""),
    ("新幹線", "旅費交通費", ""),
    ("電車", "旅費交通費", ""),
    ("バス", "旅費交通費", ""),
    ("Suica", "旅費交通費", "交通系ICチャージ"),
    ("PASMO", "旅費交通費", "交通系ICチャージ"),
    ("航空", "旅費交通費", ""),
    ("全日空", "旅費交通費", ""),
    ("日本航空", "旅費交通費", ""),
    ("ホテル", "旅費交通費", "出張宿泊"),
    ("宿泊", "旅費交通費", "出張宿泊"),
    ("駐車場", "旅費交通費", ""),
    ("高速", "旅費交通費", "高速道路料金"),
    # 荷造運賃(「郵便」より前:「郵便局 ゆうパック」を運賃と判定するため)
    ("宅急便", "荷造運賃", ""),
    ("ヤマト運輸", "荷造運賃", ""),
    ("佐川", "荷造運賃", ""),
    ("ゆうパック", "荷造運賃", ""),
    ("送料", "荷造運賃", ""),
    # 通信費
    ("携帯", "通信費", ""),
    ("ドコモ", "通信費", ""),
    ("KDDI", "通信費", ""),
    ("ソフトバンク", "通信費", ""),
    ("インターネット", "通信費", ""),
    ("プロバイダ", "通信費", ""),
    ("切手", "通信費", ""),
    ("郵便", "通信費", ""),
    ("サーバー", "通信費", "レンタルサーバー等"),
    ("ドメイン", "通信費", ""),
    # 新聞図書費(「Amazon」より前)
    ("書籍", "新聞図書費", ""),
    ("書店", "新聞図書費", ""),
    ("新聞", "新聞図書費", ""),
    ("雑誌", "新聞図書費", ""),
    ("Kindle", "新聞図書費", ""),
    # 研修費
    ("セミナー", "研修費", ""),
    ("研修", "研修費", ""),
    ("講座", "研修費", ""),
    # 会議費(金額基準の自動振り分けは MVP 対象外)
    ("会議", "会議費", ""),
    ("打ち合わせ", "会議費", ""),
    ("打合せ", "会議費", ""),
    ("カフェ", "会議費", ""),
    ("スターバックス", "会議費", ""),
    ("ドトール", "会議費", ""),
    # 接待交際費
    ("接待", "接待交際費", ""),
    ("会食", "接待交際費", ""),
    ("懇親会", "接待交際費", ""),
    ("お中元", "接待交際費", ""),
    ("お歳暮", "接待交際費", ""),
    ("手土産", "接待交際費", ""),
    ("慶弔", "接待交際費", ""),
    # 福利厚生費
    ("健康診断", "福利厚生費", ""),
    ("社員旅行", "福利厚生費", ""),
    ("福利厚生", "福利厚生費", ""),
    # 広告宣伝費
    ("広告", "広告宣伝費", ""),
    ("Google Ads", "広告宣伝費", ""),
    ("チラシ", "広告宣伝費", ""),
    ("名刺", "広告宣伝費", ""),
    # 支払手数料
    ("振込手数料", "支払手数料", ""),
    ("手数料", "支払手数料", ""),
    ("税理士", "支払手数料", ""),
    # 外注費
    ("外注", "外注費", ""),
    ("業務委託", "外注費", ""),
    ("クラウドワークス", "外注費", ""),
    ("ランサーズ", "外注費", ""),
    # 水道光熱費
    ("電気代", "水道光熱費", ""),
    ("電気料金", "水道光熱費", ""),
    ("電力", "水道光熱費", ""),
    ("ガス代", "水道光熱費", ""),
    ("ガス料金", "水道光熱費", ""),
    ("東京ガス", "水道光熱費", ""),
    ("大阪ガス", "水道光熱費", ""),
    ("水道", "水道光熱費", ""),
    # 地代家賃
    ("家賃", "地代家賃", ""),
    ("賃料", "地代家賃", ""),
    ("コワーキング", "地代家賃", ""),
    ("レンタルオフィス", "地代家賃", ""),
    # 租税公課
    ("収入印紙", "租税公課", ""),
    ("印紙", "租税公課", ""),
    ("固定資産税", "租税公課", ""),
    ("自動車税", "租税公課", ""),
    # 消耗品費
    ("文具", "消耗品費", ""),
    ("文房具", "消耗品費", ""),
    ("コピー用紙", "消耗品費", ""),
    ("トナー", "消耗品費", ""),
    ("インク", "消耗品費", ""),
    ("ヨドバシ", "消耗品費", ""),
    ("ビックカメラ", "消耗品費", ""),
    ("アスクル", "消耗品費", ""),
    ("Amazon", "消耗品費", "書籍は新聞図書費へ手動修正"),
    ("アマゾン", "消耗品費", "書籍は新聞図書費へ手動修正"),
    ("100均", "消耗品費", ""),
    ("ダイソー", "消耗品費", ""),
    # 雑費(明示的に雑費とするもの)
    ("クリーニング", "雑費", ""),
]


@dataclass(frozen=True)
class Rule:
    id: int
    keyword: str
    account: str
    note: str


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_db(conn: sqlite3.Connection) -> None:
    """rules テーブルを作成し、空であれば初期データを投入する."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY,
            keyword TEXT NOT NULL,
            account TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT ''
        )
        """
    )
    (count,) = conn.execute("SELECT COUNT(*) FROM rules").fetchone()
    if count == 0:
        conn.executemany(
            "INSERT INTO rules (id, keyword, account, note) VALUES (?, ?, ?, ?)",
            [(i, kw, acc, note) for i, (kw, acc, note) in enumerate(SEED_RULES, start=1)],
        )
    conn.commit()


def load_rules(conn: sqlite3.Connection) -> list[Rule]:
    rows = conn.execute("SELECT id, keyword, account, note FROM rules ORDER BY id ASC").fetchall()
    return [Rule(*row) for row in rows]


def get_rules(db_path: Path | str = DEFAULT_DB_PATH) -> list[Rule]:
    with connect(db_path) as conn:
        init_db(conn)
        return load_rules(conn)


def account_choices(rules: list[Rule]) -> list[str]:
    """画面の選択肢用に、ルールに出現する勘定科目を出現順で重複なく返す(雑費は必ず含む)."""
    seen = dict.fromkeys(r.account for r in rules)
    seen.setdefault(FALLBACK_ACCOUNT, None)
    return list(seen)
