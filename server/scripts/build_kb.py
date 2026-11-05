#!/usr/bin/env python
"""检索索引 / embedding 缓存的命令行入口。

真正的逻辑在 kb/index_builder.py 与 kb/embedder.py，这里只做参数编排，便于测试。

用法（在 server 目录下）：
    # —— 建 / 重建向量索引 ——
    venv/Scripts/python.exe scripts/build_kb.py --dry-run            # 只统计语料，不调外部接口
    venv/Scripts/python.exe scripts/build_kb.py                      # 语料 9 城 + 内置 12 城 POI
    venv/Scripts/python.exe scripts/build_kb.py --no-poi             # 只索引手写语料
    venv/Scripts/python.exe scripts/build_kb.py --cities 北京,广州     # 指定城市

    # —— 单独重建 embedding 缓存 ——
    venv/Scripts/python.exe scripts/build_kb.py --rebuild-embed-cache

    # —— 体检：索引 / 缓存 / 配置是否就绪 ——
    venv/Scripts/python.exe scripts/build_kb.py --status

**为什么需要 `--rebuild-embed-cache`**：
`embed_cache.json` 被 .gitignore 排除、不受版本控制。它一旦被清空或损坏
（误操作、磁盘满、并发写截断），检索不会报错，只会静默退回关键词匹配，
而且没有任何现成命令能把它补回来——只能手工写脚本。这个子命令就是补这个缺口：
不重新拉 POI、不写 Milvus，只用现有索引里的文档文本重新向量化，几分钟即可恢复。
"""
import argparse
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_DIR))

from kb import embedder, index_builder, retriever  # noqa: E402


def _rebuild_embed_cache() -> int:
    """用现有索引的文档文本重新向量化，重建 embed_cache.json。

    只读 Milvus 集合里的文档，不改向量、不拉高德 POI。
    """
    idx = retriever.load_index()
    if idx is None:
        print(f"Milvus 集合 {retriever.collection_name()} 里没有文档，请先跑一次不带参数的 build_kb.py")
        return 2
    if not embedder.configured():
        print("未配置 embedding / 视觉模型 key，无法重建缓存（先填 .env）")
        return 2

    docs = idx.docs
    texts = [d["text"] for d in docs if d.get("text")]
    if not texts:
        print("索引里没有可向量化的文本，放弃")
        return 2

    before = len(embedder._load_cache())
    print(f"索引文档 {len(docs)} 条，其中可向量化 {len(texts)} 条")
    print(f"当前缓存 {before} 条，开始重建（只补缺失的，已命中的不会重复请求）...")

    vecs = embedder.embed(texts)
    if not vecs or len(vecs) != len(texts):
        print("embedding 接口返回不完整，缓存未更新（原有缓存保持原样）")
        return 3

    embedder._flush_cache()
    after = len(embedder._load_cache())
    print(f"重建完成：缓存 {before} → {after} 条")
    print(f"文件: {embedder.CACHE_FILE} ({embedder.CACHE_FILE.stat().st_size / 1024 / 1024:.1f} MB)")
    return 0


def _status() -> int:
    """索引 / 缓存 / 凭据体检，返回非 0 表示有必须处理的问题。"""
    problems = 0

    st = retriever.status()
    print("—— 检索索引 ——")
    for k in ("engine", "milvus_configured", "docs", "indexed", "index_size", "dim"):
        print(f"  {k}: {st[k]}")
    if not st["milvus_configured"]:
        print("  ⚠️ 未配置 KB_MILVUS_URI，向量检索整体不可用 —— 本地填 ./kb/corpus/milvus.db，"
              "容器里填 http://milvus:19530")
        problems += 1
    elif not st["indexed"]:
        print("  ⚠️ Milvus 集合里没有文档，检索会退回关键词匹配 —— 跑 scripts/build_kb.py")
        problems += 1

    print("—— embedding 缓存 ——")
    cache = embedder._load_cache()
    print(f"  条目: {len(cache)}")
    print(f"  文件: {embedder.CACHE_FILE} "
          f"({embedder.CACHE_FILE.stat().st_size / 1024 / 1024:.1f} MB)"
          if embedder.CACHE_FILE.exists() else "  文件: 不存在")
    if not cache:
        print("  ⚠️ 缓存为空 —— 跑 scripts/build_kb.py --rebuild-embed-cache")
        problems += 1
    if not embedder.configured():
        print("  ⚠️ 未配置 embedding / 视觉模型 key，向量检索不可用")
        problems += 1

    print("—— 凭据 ——")
    for name, ok in (("GAODE_WEB_KEY（天气/POI/公交）", bool(_setting("gaode_web_key"))),):
        print(f"  {name}: {'已配置' if ok else '未配置（走内置兜底）'}")

    print()
    print("结论:", "就绪" if problems == 0 else f"{problems} 项待处理")
    return 0 if problems == 0 else 1


def _setting(name: str):
    from app.config import settings
    return getattr(settings, name, "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只统计文档数，不调 embedding")
    ap.add_argument("--no-poi", action="store_true", help="只索引手写语料，不拉高德候选池")
    ap.add_argument("--cities", default="", help="逗号分隔；默认 = 语料城市 + 内置 12 城")
    ap.add_argument("--rebuild-embed-cache", action="store_true",
                    help="用现有索引的文本重建 embedding 缓存（不重新拉 POI、不写 Milvus）")
    ap.add_argument("--status", action="store_true", help="体检索引 / 缓存 / 凭据是否就绪")
    args = ap.parse_args()

    if args.rebuild_embed_cache:
        return _rebuild_embed_cache()
    if args.status:
        return _status()

    cities = index_builder.target_cities(
        [c for c in args.cities.split(",") if c.strip()] or None)
    use_poi = not args.no_poi and not args.dry_run
    if args.dry_run and not args.no_poi:
        print("（dry-run 不拉高德，只统计语料部分）")

    print(f"目标城市 {len(cities)} 个，POI 扩池={'开' if use_poi else '关'}")
    docs = index_builder.build_docs(
        cities, use_poi=use_poi,
        on_city=lambda c, a, b: print(f"  {c}: 语料{a} + POI新增{b} = {a + b}"),
    )

    # 注意 +1：漏了它统计恒为 0，--dry-run 会打出「文档总数 129 类型 {spot: 0}」
    # 这种自相矛盾的输出，看着像没拉到数据
    kinds: dict[str, int] = {}
    sources: dict[str, int] = {}
    for d in docs:
        kinds[d["kind"]] = kinds.get(d["kind"], 0) + 1
        src = d.get("meta", {}).get("source") or "corpus"
        sources[src] = sources.get(src, 0) + 1
    print(f"文档总数 {len(docs)}  类型 {kinds}  来源 {sources}")

    if args.dry_run:
        print("--dry-run 结束，未调用 embedding 接口")
        return 0
    if not embedder.configured():
        print("未配置 embedding / 视觉模型 key，无法建索引（先填 .env）")
        return 2

    index = retriever.build_index(docs)
    retriever.save_index(index)
    retriever.reset_caches()
    print(f"索引已写入 Milvus 集合 {retriever.collection_name()}  dim={index.dim} docs={len(index)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
