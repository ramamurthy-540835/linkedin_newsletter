from fastapi import APIRouter

from app.models.schemas import ScheduleRequest
from app.services.scheduler_service import SchedulerService

router = APIRouter()
service = SchedulerService()


@router.post("")
async def schedule_post(req: ScheduleRequest) -> dict:
    task_name = service.schedule_publish(req.draft_id, req.publish_at_utc)
    return {"task_name": task_name, "draft_id": req.draft_id, "publish_at_utc": req.publish_at_utc}
