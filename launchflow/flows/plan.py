import asyncio
from dataclasses import dataclass, field
from typing import Dict, Generic, List, Optional, TypeVar, Union

import rich
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Column
from rich.tree import Tree

from launchflow.flows.flow_utils import ResourceRef, ServiceRef
from launchflow.locks import Lock
from launchflow.resource import Resource
from launchflow.service import Service

T = TypeVar("T", bound="Plan")


@dataclass
class Result(Generic[T]):
    plan: T
    success: bool
    error_message: Optional[str] = field(default=None, init=False)


@dataclass
class FailedToPlan:
    resource: Optional[Resource] = None
    service: Optional[Service] = None
    error_message: str = ""

    def __post_init__(self):
        if not self.resource and not self.service:
            raise ValueError("Either resource or service must be provided")

    def reference(self) -> Union[ResourceRef, ServiceRef]:
        if self.resource:
            return ResourceRef(self.resource)
        return ServiceRef(self.service)  # type: ignore


@dataclass
class FlowResult:
    success: bool
    plan_results: List[Result]
    failed_plans: List[FailedToPlan]


@dataclass
class Plan:
    resource_or_service: Union[Resource, Service]
    depends_on: List["Plan"]
    verbose: bool

    def __str__(self):
        if isinstance(self.resource_or_service, Resource):
            return (
                f"{self.operation_type.title()} {ResourceRef(self.resource_or_service)}"
            )
        return f"{self.operation_type.title()} {ServiceRef(self.resource_or_service)}"

    def reference(self) -> Union[ResourceRef, ServiceRef]:
        if isinstance(self.resource_or_service, Resource):
            return ResourceRef(self.resource_or_service)
        return ServiceRef(self.resource_or_service)

    @property
    def operation_type(self) -> str:
        raise NotImplementedError

    @property
    def id(self):
        return f"{self.operation_type}-{self.resource_or_service.name}"

    async def lock_plan(self) -> Optional[Lock]:
        raise NotImplementedError

    def child_plans(self) -> List["Plan"]:
        return []

    def print_plan(
        self,
        console: rich.console.Console = rich.console.Console(),
        left_padding: int = 0,
    ):
        raise NotImplementedError

    async def abandon_plan(self, reason: str) -> Result:
        raise NotImplementedError

    async def execute_plan(
        self,
        tree: Tree,
        dependency_results: List[Result],
    ) -> Result:
        raise NotImplementedError

    def pending_message(self):
        return f"{self} is pending"

    def task_message(self):
        return f"Executing {self}"

    def success_message(self):
        return f"{self} succeeded"


class ResourcePlan(Plan):
    def __post_init__(self):
        if not isinstance(self.resource_or_service, Resource):
            raise ValueError("resource_or_service must be a Resource")

    @property
    def resource(self) -> Resource:
        return self.resource_or_service  # type: ignore


class ServicePlan(Plan):
    def __post_init__(self):
        if not isinstance(self.resource_or_service, Service):
            raise ValueError("resource_or_service must be a Service")

    @property
    def service(self) -> Service:
        return self.resource_or_service  # type: ignore


async def execute_plans(
    plans: List[Plan],
    tree: Tree,
) -> List[Result]:
    plan_id_to_plan: Dict[str, Plan] = {plan.id: plan for plan in plans}
    plan_tasks: Dict[str, asyncio.Task] = {}

    async def _execute_with_dependencies(dependency: Plan) -> Result:
        if dependency.id in plan_tasks:
            return await plan_tasks[dependency.id]

        async def task():
            # SETUP
            dependency_tasks: List[asyncio.Task] = []
            spinner_column = SpinnerColumn(finished_text="[green]✓[/green]")
            progress = Progress(
                spinner_column,
                TextColumn("{task.description}", table_column=Column(overflow="fold")),
                TimeElapsedColumn(),
            )
            subtree = tree.add(progress)
            task_id = progress.add_task(
                dependency.pending_message(), start=False, total=1
            )

            # PENDING
            for dep in dependency.depends_on:
                if dep.id not in plan_id_to_plan:
                    progress.start_task(task_id)
                    spinner_column.finished_text = "[yellow]⚠[/yellow]"
                    progress.update(
                        task_id,
                        description=f"{dependency} canceled due to missing dependency: {dep}",
                        completed=1,
                    )
                    progress.stop_task(task_id)
                    for dep_task in dependency_tasks:
                        dep_task.cancel()

                    return await dependency.abandon_plan(f"Missing dependency: {dep}")

                dep_task = asyncio.create_task(_execute_with_dependencies(dep))
                dependency_tasks.append(dep_task)

            # CHECK DEPENDENCY RESULTS
            dependency_results: List[Result] = await asyncio.gather(*dependency_tasks)
            if not all(result.success for result in dependency_results):
                progress.start_task(task_id)
                spinner_column.finished_text = "[yellow]⚠[/yellow]"
                progress.update(
                    task_id,
                    description=f"{dependency} canceled due to dependency failure",
                    completed=1,
                )
                progress.stop_task(task_id)
                return await dependency.abandon_plan("Dependency failure")

            # EXECUTE PLAN
            progress.start_task(task_id)
            progress.update(task_id, description=dependency.task_message())
            result = await dependency.execute_plan(subtree, dependency_results)
            if not result.success:
                spinner_column.finished_text = "[red]✗[/red]"
                failure_message = f"{dependency} failed"
                if result.error_message:
                    failure_message += f": {result.error_message}"
                progress.update(task_id, description=failure_message, completed=1)
            else:
                progress.update(
                    task_id, description=dependency.success_message(), completed=1
                )

            # DONE
            return result

        plan_tasks[dependency.id] = asyncio.create_task(task())
        return await plan_tasks[dependency.id]

    results = await asyncio.gather(
        *[_execute_with_dependencies(plan) for plan in plans]
    )
    return results
