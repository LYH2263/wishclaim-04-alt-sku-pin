from app.db import connect

SCHEMA = """
CREATE TABLE IF NOT EXISTS wishes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, note TEXT, status TEXT,
  claimer TEXT, claimed_at TEXT, expires_at TEXT, data_quality TEXT,
  skus TEXT, selected_sku TEXT
);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
"""

def _has_column(c, table, col):
    return any(r["name"] == col for r in c.execute(f"PRAGMA table_info({table})"))

def init_db():
    c = connect()
    c.executescript(SCHEMA)
    # 轻量迁移：旧库补列
    if not _has_column(c, "wishes", "skus"):
        c.execute("ALTER TABLE wishes ADD COLUMN skus TEXT")
    if not _has_column(c, "wishes", "selected_sku"):
        c.execute("ALTER TABLE wishes ADD COLUMN selected_sku TEXT")
    # 旧单愿望回填为一条备选，保证改造前数据可按单备选默认选中兼容
    from app.modules.sku_options import encode_skus
    c.execute("UPDATE wishes SET skus='[]' WHERE skus IS NULL OR skus=''")
    for r in c.execute("SELECT id, title FROM wishes WHERE skus='[]'").fetchall():
        c.execute("UPDATE wishes SET skus=? WHERE id=?",
                  (encode_skus([{"title": r["title"] or "", "estimated_price": ""}]), r["id"]))
    c.commit()
    if c.execute("SELECT COUNT(*) c FROM wishes").fetchone()["c"] == 0:
        c.executemany(
            "INSERT INTO wishes(title,note,status,claimer,claimed_at,expires_at,data_quality,skus,selected_sku) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            [
                ("机械键盘", "红轴", "open", None, None, None, "clean",
                 '[{"title":"Keychron K8 红轴","estimated_price":"380"},'
                 '{"title":"罗技 MX Mechanical","estimated_price":"699"},'
                 '{"title":"RK R75","estimated_price":"199"}]', None),
                ("围巾", "羊毛", "open", None, None, None, "clean",
                 '[{"title":"羊绒围巾","estimated_price":"260"}]', None),
                ("脏愿望-空标题", "", "open", None, None, None, "dirty",
                 '[{"title":"","estimated_price":""}]', None),
                ("过期锁样例", "应被TTL释放", "claimed", "ghost", "2020-01-01T00:00:00+00:00",
                 "2020-01-01T01:00:00+00:00", "dirty",
                 '[{"title":"旧钉选样例","estimated_price":"50"}]',
                 '{"title":"旧钉选样例","estimated_price":"50","sku_index":0}'),
            ],
        )
        c.execute("INSERT INTO settings(key,value) VALUES ('ttl_seconds','86400')")
        c.execute("INSERT INTO settings(key,value) VALUES ('wall_title','暖粉愿望墙')")
        c.commit()
    c.close()
