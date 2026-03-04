"""Queue adapters used by API and worker flows."""

from __future__ import annotations

import json


class RedisJobQueue:
    def __init__(self, redis_client, queue_name: str = "jobs"):
        self.redis_client = redis_client
        self.queue_name = queue_name

    def enqueue(self, payload: dict):
        self.redis_client.rpush(self.queue_name, json.dumps(payload))

    def dequeue(self):
        raw_payload = self.redis_client.lpop(self.queue_name)
        if raw_payload is None:
            return None
        if isinstance(raw_payload, bytes):
            raw_payload = raw_payload.decode("utf-8")
        return json.loads(raw_payload)
