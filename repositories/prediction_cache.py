import json
import logging
from typing import Optional

from app.clients import get_redis_client
from models.ads import PredictResponse, ModerationResultResponse

logger = logging.getLogger(__name__)


class PredictionCacheStorage:
    """Storage для кэширования результатов предсказаний в Redis."""

    SYNC_KEY_PREFIX = "prediction:item"
    ASYNC_KEY_PREFIX = "prediction:task"
    # 15 минут: этого хватает, чтобы сгладить всплески повторных запросов
    # по одному item_id и снизить нагрузку на модель, при этом риск устаревшего
    # результата остается ограниченным для меняющихся объявлений.
    TTL_SECONDS = 15 * 60
    # Для async polling держим TTL короче: статусы pending/completed могут
    # быстро меняться, поэтому 5 минут достаточно для снижения нагрузки на БД
    # без заметного риска отдавать устаревший статус слишком долго.
    ASYNC_TTL_SECONDS = 5 * 60

    @staticmethod
    def _sync_key(item_id: int) -> str:
        return f"{PredictionCacheStorage.SYNC_KEY_PREFIX}:{item_id}"

    @staticmethod
    def _async_key(task_id: int) -> str:
        return f"{PredictionCacheStorage.ASYNC_KEY_PREFIX}:{task_id}"

    async def get(self, item_id: int) -> Optional[PredictResponse]:
        """Получить предсказание из кэша по item_id."""
        try:
            redis_client = get_redis_client()
            if not redis_client.is_started():
                return None

            raw_payload = await redis_client.get_client().get(self._sync_key(item_id))
            if not raw_payload:
                return None

            payload = json.loads(raw_payload)
            return PredictResponse(
                is_violation=bool(payload["is_violation"]),
                probability=float(payload["probability"]),
            )
        except Exception as e:
            logger.warning(f"Не удалось прочитать кэш предсказания для item_id={item_id}: {e}")
            return None

    async def set(self, item_id: int, prediction: PredictResponse) -> None:
        """Сохранить предсказание в кэш с TTL."""
        try:
            redis_client = get_redis_client()
            if not redis_client.is_started():
                return

            payload = json.dumps(
                {
                    "is_violation": prediction.is_violation,
                    "probability": prediction.probability,
                }
            )
            await redis_client.get_client().set(self._sync_key(item_id), payload, ex=self.TTL_SECONDS)
        except Exception as e:
            logger.warning(f"Не удалось записать кэш предсказания для item_id={item_id}: {e}")

    async def get_moderation_result(self, task_id: int) -> Optional[ModerationResultResponse]:
        """Получить результат асинхронной модерации из кэша по task_id."""
        try:
            redis_client = get_redis_client()
            if not redis_client.is_started():
                return None

            raw_payload = await redis_client.get_client().get(self._async_key(task_id))
            if not raw_payload:
                return None

            payload = json.loads(raw_payload)
            return ModerationResultResponse(
                task_id=int(payload["task_id"]),
                status=str(payload["status"]),
                is_violation=payload.get("is_violation"),
                probability=payload.get("probability"),
                error_message=payload.get("error_message"),
            )
        except Exception as e:
            logger.warning(f"Не удалось прочитать кэш async результата для task_id={task_id}: {e}")
            return None

    async def set_moderation_result(self, result: ModerationResultResponse) -> None:
        """Сохранить результат асинхронной модерации в кэш с TTL."""
        try:
            redis_client = get_redis_client()
            if not redis_client.is_started():
                return

            payload = json.dumps(
                {
                    "task_id": result.task_id,
                    "status": result.status,
                    "is_violation": result.is_violation,
                    "probability": result.probability,
                    "error_message": result.error_message,
                }
            )
            await redis_client.get_client().set(
                self._async_key(result.task_id),
                payload,
                ex=self.ASYNC_TTL_SECONDS,
            )
        except Exception as e:
            logger.warning(f"Не удалось записать кэш async результата для task_id={result.task_id}: {e}")
