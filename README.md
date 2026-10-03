# Wishclaim · 礼物愿望认领

发布 → 认领锁定（互斥+TTL）→ 核销/释放。

| 服务 | 端口 |
| --- | --- |
| 前端 | 5200 |
| API | 10200 |

```bash
docker compose up --build
pytest backend/app/tests
```

0-1：`wish_comment` / `secret_santa` / `price_cap`。

## 多备选 SKU 钉选

- 发愿望可挂 1～5 条备选（标题+估价，2～5 为常态，单条兼容旧单愿望）；不传 `skus` 则按遗留单愿望处理。
- 未认领：墙卡显示备选个数，详情展开全部；认领必须显式选中一条（仅一条时缺省选中）。
- 认领写入 `selected_sku` 快照。**拍板：认领后墙卡 / 详情 / 我的认领三路一致，只展示钉选一条**，不再列出其余备选。
- 认领后发布者增删备选（`PUT /api/wishes/{id}/skus`）不改写已钉快照；释放/TTL 过期会清除快照。
- 零备选（如无标题遗留脏数据）或索引越界 → 认领 409，锁保持不变。

模块：`modules/sku_options`（备选校验）· `engines/claim_lock`（钉选写锁 `resolve_pin`）· `modules/sku_projection`（三路投影 + 遗留回退）。
