"""索引构建：语料 + 各城市真实候选景点 → embedding → 索引文件。

放成模块而不是留在 CLI 里，是为了能被测试覆盖：扩城市这件事一旦写错
（比如 POI 与语料重复计数、新城市进不了 detect_city），线上是静默劣化的。
"""
import time
from collections import defaultdict

from kb import candidates, corpus, embedder, retriever

# 现有语料是杭州/成都/西安/苏州/重庆/厦门/长沙/南京/上海 9 城，这批是要补的
EXTRA_CITIES = ["北京", "广州", "深圳", "武汉", "天津", "青岛",
                "洛阳", "昆明", "张家界", "三亚", "黄山", "珠海"]
POI_INTERVAL = 0.4  # 秒：高德 key 实测连打 6 次就 CUQPS_HAS_EXCEEDED_THE_LIMIT


def target_cities(cities: list[str] | None = None) -> list[str]:
    if cities:
        return [c.strip() for c in cities if c.strip()]
    base = sorted(corpus.load_spots().keys())
    return base + [c for c in EXTRA_CITIES if c not in base]


def build_docs(cities: list[str], use_poi: bool = True, interval: float = POI_INTERVAL,
               on_city=None) -> list[dict]:
    """每个城市的文档 = 语料文档 + 候选池里语料没覆盖的景点。

    语料在前：它有玩法、机位、预约信息；POI 只有存在性、地址、坐标、评分。
    """
    by_city: dict[str, list] = defaultdict(list)
    for d in corpus.build_docs():
        by_city[d["city"]].append(d)

    docs: list[dict] = []
    for city in cities:
        own = by_city.get(city, [])
        docs.extend(own)
        extras: list[dict] = []
        if use_poi:
            pool = candidates.city_pool(city)
            extras = [corpus.poi_doc(i, city) for i in pool if candidates.find(own, i["name"]) is None]
            if pool:
                time.sleep(interval)
        docs.extend(extras)
        if on_city:
            on_city(city, len(own), len(extras))

    return corpus.merge_docs(docs)


def build_and_save(cities: list[str] | None = None, use_poi: bool = True, on_city=None) -> retriever.Index:
    """构建并落盘。embedding 不可用时抛 RuntimeError——建索引是显式运维动作，不该静默半成功。"""
    docs = build_docs(target_cities(cities), use_poi=use_poi, on_city=on_city)
    if not embedder.configured():
        raise RuntimeError("未配置 embedding / 视觉模型 key，无法建索引")
    index = retriever.build_index(docs)
    retriever.save_index(index)
    retriever.reset_caches()
    return index
