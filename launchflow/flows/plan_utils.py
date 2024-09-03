import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Coroutine, List, Literal, Optional, Tuple, Union

import beaupy  # type: ignore
import rich

from launchflow import exceptions
from launchflow.cli.resource_utils import is_local_resource
from launchflow.flows.flow_utils import (
    OP_COLOR,
    EnvironmentRef,
    ResourceRef,
    ServiceRef,
)
from launchflow.flows.plan import FailedToPlan, Plan, ResourcePlan, ServicePlan
from launchflow.locks import Lock, LockOperation, OperationType, ReleaseReason
from launchflow.managers.environment_manager import EnvironmentManager


def print_plans(
    *plans: Union[
        ResourcePlan,
        ServicePlan,
        FailedToPlan,
    ],
    environment_manager: EnvironmentManager,
    console: rich.console.Console = rich.console.Console(),
):
    failed_plans: List[FailedToPlan] = []
    noop_plans: List[Union[ResourcePlan, ServicePlan]] = []
    valid_plans: List[Union[ResourcePlan, ServicePlan]] = []
    for plan in plans:
        if isinstance(plan, FailedToPlan):
            failed_plans.append(plan)
        elif plan.operation_type == "noop":
            noop_plans.append(plan)
        else:
            valid_plans.append(plan)

        # TODO: make this recursive so that we can support deeper levels of nesting
        if not isinstance(plan, FailedToPlan):
            for child_plan in plan.child_plans():
                if child_plan.operation_type == "noop":
                    noop_plans.append(child_plan)  # type: ignore

    # First we print the failed plans above the plan section
    for plan in failed_plans:
        console.print(
            f"[red]✗[/red] {plan.reference()} failed to plan:\n    {plan.error_message}"
        )

    # Then we print the noop plans
    if noop_plans and failed_plans:
        console.print()
    for plan in noop_plans:
        console.print(f"[green]✓[/green] {plan} is up to date.")

    if valid_plans:
        # Finally we print the plan section with plans that have work to do
        console.print()
        console.rule("[bold purple]plan")
        console.print()
        console.print(
            f"The following infrastructure changes will happen in {EnvironmentRef(environment_manager)}:\n"
        )
        for plan in valid_plans:
            plan.print_plan(console, left_padding=2)


async def select_plans(
    *plans: Union[
        ResourcePlan,
        ServicePlan,
        FailedToPlan,
    ],
    operation_type: Literal["create", "deploy", "promote"],
    environment_manager: EnvironmentManager,
    console: rich.console.Console = rich.console.Console(),
    confirm: bool = True,
) -> Union[None, List[Union[ResourcePlan, ServicePlan]]]:
    failed_plans: List[FailedToPlan] = []
    noop_plans: List[Union[ResourcePlan, ServicePlan]] = []
    valid_plans: List[Union[ResourcePlan, ServicePlan]] = []
    for plan in plans:
        if isinstance(plan, FailedToPlan):
            failed_plans.append(plan)
        elif plan.operation_type == "noop":
            noop_plans.append(plan)
        else:
            valid_plans.append(plan)

    if not valid_plans:
        return None  # The None is used to indicate that no valid plans were found

    if len(valid_plans) == 1:
        selected_plan = valid_plans[0]
        if isinstance(selected_plan, ResourcePlan):
            entity_ref = f"resource {ResourceRef(selected_plan.resource)}"
        elif isinstance(selected_plan, ServicePlan):
            entity_ref = f"service {ServiceRef(selected_plan.service)}"
        else:
            raise NotImplementedError(
                f"Got an unexpected plan type {type(selected_plan)}."
            )

        if not confirm:
            return [selected_plan]

        answer = beaupy.confirm(
            f"[bold]{selected_plan.operation_type.capitalize()}[/bold] {entity_ref} in {EnvironmentRef(environment_manager)}?"
        )
        if not answer:
            return []

        console.print(
            f"[bold]{selected_plan.operation_type.capitalize()}[/bold] {entity_ref} in {EnvironmentRef(environment_manager)}?"
        )
        console.print("[pink1]> Yes[/pink1]")
        console.print()
        return [selected_plan]

    if not confirm:
        return valid_plans

    console.print(
        f"Select the [bold][{OP_COLOR}]{operation_type}[/{OP_COLOR}][/bold] plans you want to execute in {EnvironmentRef(environment_manager)}:"
    )

    def preprocessor(plan: Union[ResourcePlan, ServicePlan]):
        if isinstance(plan, ResourcePlan):
            return f"[bold]{plan.operation_type.capitalize()}[/bold] resource {ResourceRef(plan.resource)}"
        elif isinstance(plan, ServicePlan):
            return f"[bold]{plan.operation_type.capitalize()}[/bold] service {ServiceRef(plan.service)}"
        else:
            raise NotImplementedError(f"Got an unexpected plan type {type(plan)}.")

    keyed_plans = {p.id: p for p in valid_plans}
    plans_to_print = [(key, preprocessor(plan)) for key, plan in keyed_plans.items()]

    selected_plans: List[Tuple[str, str]] = beaupy.select_multiple(
        options=plans_to_print,
        preprocessor=lambda x: x[1],
    )
    selected_plan_ids = set(plan[0] for plan in selected_plans)
    for plan in valid_plans:
        if plan.id in selected_plan_ids:
            if isinstance(plan, ResourcePlan):
                console.print(
                    f"[[pink1]✓[/pink1]] [pink1][bold]{plan.operation_type.capitalize()}[/bold] {plan.resource} selected[/pink1]"
                )
            elif isinstance(plan, ServicePlan):
                console.print(
                    f"[[pink1]✓[/pink1]] [pink1][bold]{plan.operation_type.capitalize()}[/bold] {plan.service} selected[/pink1]"
                )
        else:
            if isinstance(plan, ResourcePlan):
                console.print(
                    f"[ ] [grey50][bold]{plan.operation_type.capitalize()}[/bold] {plan.resource} not selected[/grey50]"
                )
            elif isinstance(plan, ServicePlan):
                console.print(
                    f"[ ] [grey50][bold]{plan.operation_type.capitalize()}[/bold] {plan.service} not selected[/grey50] "
                )

    console.print()
    return [keyed_plans[plan_id] for plan_id, _ in selected_plans]


def _build_lock_tasks_recursively(
    plans: List[Plan],
) -> List[Coroutine[Any, Any, Optional[Lock]]]:
    to_return = []
    for plan in plans:
        to_return.append(plan.lock_plan())
        to_return.extend(_build_lock_tasks_recursively(plan.child_plans()))
    return to_return


async def _lock_remote_plans(
    plans: List[Plan],
    environment_manager: EnvironmentManager,
):
    async with await environment_manager.lock_environment(
        operation=LockOperation(operation_type=OperationType.LOCK_ENVIRONMENT)
    ):
        return await asyncio.gather(*_build_lock_tasks_recursively(plans))


# TODO: add a progress spinner while locking it.
@asynccontextmanager
async def lock_plans(
    *plans: Plan,
    environment_manager: EnvironmentManager,
):
    local_plans = []
    remote_plans = []
    for plan in plans:
        if isinstance(plan, ResourcePlan) and is_local_resource(plan.resource):
            local_plans.append(plan)
        else:
            remote_plans.append(plan)

    lock_tasks: List[Coroutine[Any, Any, Optional[Lock]]] = []
    if local_plans:
        lock_tasks.extend(_build_lock_tasks_recursively(local_plans))  # type: ignore
    if remote_plans:
        lock_tasks.append(_lock_remote_plans(remote_plans, environment_manager))

    lock_results: List[Union[Optional[Lock], Exception]] = []
    try:
        lock_results = await asyncio.gather(*lock_tasks, return_exceptions=True)  # type: ignore
        exceptions_list = []
        for lock_or_exception in lock_results:
            if isinstance(lock_or_exception, Exception):
                exceptions_list.append(lock_or_exception)
                logging.error(
                    f"Failed to lock a plan: {lock_or_exception}", exc_info=True
                )
        if exceptions_list:
            raise exceptions.FailedToLockPlans(exceptions_list)
        yield
    finally:
        unlock_tasks = []
        for lock_or_exception in lock_results:
            if isinstance(lock_or_exception, Lock):
                # NOTE: The plans unlock themselves after a successful execution so this
                # will only be used in the case of an error. Technically this runs
                # everytime, but if a lock is already released it will just be a noop.
                unlock_tasks.append(lock_or_exception.release(ReleaseReason.ABANDONED))
        await asyncio.gather(*unlock_tasks)
