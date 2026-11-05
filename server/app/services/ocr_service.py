"""识别服务：识图 / 识别视频。

两种模式：
- mode=itinerary：上传「行程截图/攻略」，识别城市+天数+景点，生成可编辑行程。
- mode=scene：上传风景照或旅行视频，识别地点并推荐同类/附近景点（给出景点）。

未配置视觉模型 key（vision_api_key）时返回结构化示例，保证整条链路可跑；
配置后自动走真实视觉模型（Qwen-VL / GPT-4o 等 OpenAI 兼容协议）。
"""
import logging
import os
import shutil
import tempfile

from fastapi.concurrency import run_in_threadpool

from app.ai.vision_client import vision_client
from app.config import settings
from app.services import plan_service

logger = logging.getLogger("ocr_service")

# 场景识别：让视觉模型输出结构化 JSON 的提示词
SCENE_SCHEMA = """你是旅游地标识别与景点推荐助手。严格只输出如下 JSON（不要多余文字）：
{"recognized":{"place":"识别出的地点名","city":"所在城市","description":"一句话简介","confidence":0.9},
"recommended_spots":[{"name":"景点名","category":"自然风光/人文历史/美食/网红打卡/休闲度假","reason":"推荐理由","duration_min":90,"ticket_price":0}]}
至少给出 5 个推荐景点。"""

# 行程截图：让视觉模型输出结构化 JSON 的提示词
ITINERARY_SCHEMA = """你是行程单 OCR 与解析助手。严格只输出如下 JSON（不要多余文字）：
{"city":"城市名","days":2,"spots":["景点1","景点2","景点3"]}
从图片中提取行程涉及的城市、天数和景点列表。"""


class OcrService:
    async def recognize(self, file_bytes: bytes, filename: str, mode: str) -> dict:
        is_video = filename.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm"))
        media_type = "video" if is_video else "image"

        if mode == "itinerary":
            return await self._recognize_itinerary(file_bytes, filename, media_type)
        return await self._recognize_scene(file_bytes, filename, media_type)

    # ---------- 行程截图 ----------
    async def _recognize_itinerary(self, file_bytes, filename, media_type) -> dict:
        if settings.vision_api_key:
            try:
                data = await vision_client.analyze([file_bytes], ITINERARY_SCHEMA)
                if data and data.get("city"):
                    city = data["city"]
                    days = int(data.get("days") or 2)
                    spots = data.get("spots") or []
                    trip = await self._build_trip(city, days)
                    return {
                        "mode": "itinerary",
                        "media_type": media_type,
                        "recognized": {"city": city, "days": days, "spots": spots},
                        "trip": trip,
                    }
                logger.warning("视觉模型行程解析异常，回退示例：%s", data)
            except Exception:
                logger.exception("行程识别异常，回退示例")
        # 示例数据（gen_trip 会打外部接口，必须离开事件循环）
        trip = await run_in_threadpool(
            plan_service.gen_trip, {"city": "杭州", "days": 2, "route_type": "popular"}
        )
        return {
            "mode": "itinerary",
            "media_type": media_type,
            "recognized": {"city": "杭州", "days": 2, "spots": ["西湖", "灵隐寺", "河坊街", "西溪湿地"]},
            "trip": {"id": "ocr", **trip},
        }

    # ---------- 识景 / 识视频 ----------
    async def _recognize_scene(self, file_bytes, filename, media_type) -> dict:
        images = [file_bytes] if media_type == "image" else self._extract_frames(file_bytes)
        if settings.vision_api_key and images:
            try:
                data = await vision_client.analyze(images, SCENE_SCHEMA)
                if data and data.get("recognized", {}).get("place"):
                    rec = data["recognized"]
                    spots = data.get("recommended_spots") or []
                    trip = await self._build_trip(rec.get("city") or "杭州", 2)
                    return {
                        "mode": "scene",
                        "media_type": media_type,
                        "recognized": rec,
                        "recommended_spots": spots,
                        "trip": trip,
                    }
                logger.warning("视觉模型场景解析异常，回退示例：%s", data)
            except Exception:
                logger.exception("场景识别异常，回退示例")
        # 示例数据
        return {
            "mode": "scene",
            "media_type": media_type,
            "recognized": {
                "place": "西湖",
                "city": "杭州",
                "description": "中国著名淡水湖，三面云山一面城，西湖十景享誉中外。",
                "confidence": 0.93,
            },
            "recommended_spots": [
                {"name": "断桥残雪", "category": "人文历史", "reason": "西湖十景之一，白堤起点，赏湖最佳机位", "duration_min": 60, "ticket_price": 0},
                {"name": "雷峰塔", "category": "人文历史", "reason": "登塔俯瞰西湖全景，傍晚夕照尤美", "duration_min": 90, "ticket_price": 40},
                {"name": "苏堤春晓", "category": "自然风光", "reason": "贯穿西湖的长堤，晨跑骑行皆宜", "duration_min": 80, "ticket_price": 0},
                {"name": "三潭印月", "category": "网红打卡", "reason": "需乘船登岛，一元纸币背面取景地", "duration_min": 120, "ticket_price": 55},
                {"name": "河坊街", "category": "美食", "reason": "南宋御街，小吃与老字号云集", "duration_min": 100, "ticket_price": 0},
            ],
            "trip": {"id": "ocr", **await run_in_threadpool(
                plan_service.gen_trip, {"city": "杭州", "days": 2, "route_type": "popular"}
            )},
        }

    # ---------- 工具 ----------
    async def _build_trip(self, city: str, days: int) -> dict:
        """用现有 AI 行程服务基于识别出的城市生成一份行程。"""
        try:
            from app.schemas import PlanFormReq

            req = PlanFormReq(
                city=city,
                days=days,
                crowd_type="朋友",
                transport_mode="地铁",
                route_type="popular",
                remark="由图片/视频识别自动生成",
            )
            return await plan_service.PlanService().generate_from_form(req)
        except Exception:
            logger.exception("基于识别结果生成行程失败，退回示例")
            return await run_in_threadpool(
                plan_service.gen_trip, {"city": city, "days": days, "route_type": "popular"}
            )

    def _extract_frames(self, video_bytes: bytes) -> list[bytes]:
        """从视频抽帧（best-effort）。无 ffmpeg 时返回空列表，由调用方回退示例。"""
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            logger.warning("未检测到 ffmpeg，视频识别回退示例（安装 ffmpeg 后可真识别）")
            return []
        try:
            with tempfile.TemporaryDirectory() as td:
                src = os.path.join(td, "in.mp4")
                with open(src, "wb") as f:
                    f.write(video_bytes)
                out = os.path.join(td, "frame_%03d.jpg")
                os.system(f'{ffmpeg} -y -i "{src}" -vf fps=1/15 -vframes 6 "{out}" >nul 2>&1')
                frames = []
                for i in range(1, 7):
                    p = os.path.join(td, f"frame_{i:03d}.jpg")
                    if os.path.exists(p):
                        with open(p, "rb") as f:
                            frames.append(f.read())
                return frames
        except Exception:
            logger.exception("视频抽帧失败")
            return []


ocr_service = OcrService()
