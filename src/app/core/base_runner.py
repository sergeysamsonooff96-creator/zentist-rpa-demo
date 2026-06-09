from abc import ABC, abstractmethod
from typing import Any, Iterable


class BasePortalRunnerZX(ABC):
    def __init__(self, config: Any, logger: Any, repo: Any, run_id: str):
        self.config = config
        self.logger = logger
        self.repo = repo
        self.run_id = run_id

    @property
    @abstractmethod
    def portal_name(self) -> str:
        ...

    @abstractmethod
    def iter_items(self) -> Iterable[Any]:
        ...

    @abstractmethod
    async def process_item(self, item: Any) -> dict:
        ...

    async def run_job(self) -> None:
        self.logger.info(f"job_started portal={self.portal_name} run_id={self.run_id}")
        for item in self.iter_items():
            item_key = str(item)
            try:
                result = await self.process_item(item)
                self.repo.save_result(
                    portal=self.portal_name,
                    run_id=self.run_id,
                    item_key=item_key,
                    status="success",
                    payload=result,
                )
                self.logger.info(f"item_success portal={self.portal_name} item={item_key}")
            except Exception as exc:
                self.repo.save_result(
                    portal=self.portal_name,
                    run_id=self.run_id,
                    item_key=item_key,
                    status="failed",
                    reason=str(exc),
                )
                self.logger.error(f"item_failed portal={self.portal_name} item={item_key} error={exc}")
        self.logger.info(f"job_finished portal={self.portal_name} run_id={self.run_id}")