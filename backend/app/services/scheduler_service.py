import json
from datetime import datetime, timezone
from google.cloud import tasks_v2

from app.core.config import settings


class SchedulerService:
    def __init__(self) -> None:
        self.client = tasks_v2.CloudTasksClient()

    def schedule_publish(self, draft_id: str, publish_at_utc: datetime) -> str:
        parent = self.client.queue_path(
            settings.gcp_project_id,
            settings.cloud_tasks_location,
            settings.cloud_tasks_queue,
        )
        body = json.dumps({"draft_id": draft_id}).encode()

        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{settings.cloud_run_base_url}/api/publish/from-scheduler",
                "headers": {"Content-Type": "application/json"},
                "body": body,
            },
            "schedule_time": {
                "seconds": int(publish_at_utc.replace(tzinfo=timezone.utc).timestamp())
            },
        }
        created = self.client.create_task(parent=parent, task=task)
        return created.name
