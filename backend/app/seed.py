import json
from datetime import datetime, timedelta, timezone
from app.db import connect

def init_db():
    c = connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS wishes(
      id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, note TEXT, status TEXT,
      claimer TEXT, claimed_at TEXT, expires_at TEXT, data_quality TEXT,
      selected_sku TEXT
    );
    CREATE TABLE IF NOT EXISTS wish_skus(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      wish_id INTEGER NOT NULL, idx INTEGER NOT NULL,
      title TEXT NOT NULL, price REAL
    );
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
    """)
    # 老库迁移：补 selected_sku 列
    cols = [r["name"] for r in c.execute("PRAGMA table_info(wishes)")]
    if "selected_sku" not in cols:
        c.execute("ALTER TABLE wishes ADD COLUMN selected_sku TEXT")
    if c.execute("SELECT COUNT(*) c FROM wishes").fetchone()["c"] == 0:
        now = datetime.now(timezone.utc)
        pinned = {"idx": 1, "title": "Bose QC45", "price": 1899.0}
        c.executemany(
            "INSERT INTO wishes(title,note,status,claimer,claimed_at,expires_at,data_quality,selected_sku)"
            " VALUES (?,?,?,?,?,?,?,?)",
            [
                ("机械键盘", "红轴", "open", None, None, None, "clean", None),
                ("围巾", "羊毛", "open", None, None, None, "clean", None),
                ("脏愿望-空标题", "", "open", None, None, None, "dirty", None),
                ("过期锁样例", "应被TTL释放", "claimed", "ghost", "2020-01-01T00:00:00+00:00",
                 "2020-01-01T01:00:00+00:00", "dirty", None),
                ("蓝牙耳机", "已认领·钉选演示", "claimed", "alice",
                 now.isoformat(), (now + timedelta(days=1)).isoformat(), "clean",
                 json.dumps(pinned, ensure_ascii=False)),
            ],
        )
        c.executemany(
            "INSERT INTO wish_skus(wish_id,idx,title,price) VALUES (?,?,?,?)",
            [
                (1, 0, "Keychron K2 红轴", 349.0),
                (1, 1, "IKBC C87", 259.0),
                (1, 2, "RK87 三模", 199.0),
                (2, 0, "羊绒围巾 驼色", 299.0),
                (2, 1, "羊毛围巾 灰色", 129.0),
                (5, 0, "Sony WH-1000XM5", 2499.0),
                (5, 1, "Bose QC45", 1899.0),
            ],
        )
        c.execute("INSERT INTO settings(key,value) VALUES ('ttl_seconds','86400')")
        c.execute("INSERT INTO settings(key,value) VALUES ('wall_title','暖粉愿望墙')")
        c.commit()
    c.close()
