from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator, List, Optional

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table


def build_step_progress():
    return Progress(
        TextColumn("  "),
        SpinnerColumn("runner", finished_text=""),
        TextColumn("[bold purple]{task.description}"),
        TimeElapsedColumn(),
    )


def build_deploy_progress():
    return Progress(
        TextColumn("  "),
        TimeElapsedColumn(),
        BarColumn(),
        TextColumn("({task.completed} of {task.total} steps done)"),
    )


def build_service_progress():
    return Progress(
        SpinnerColumn(finished_text=""),
        TextColumn("[bold]{task.description}"),
    )


def build_overall_progress():
    return Progress(
        TimeElapsedColumn(),
        BarColumn(),
        TextColumn("{task.completed}/{task.total} {task.description}"),
    )


def build_completion_message():
    return Progress(
        TextColumn("[bold]{task.description}"),
    )


@dataclass
class WorkflowProgress:
    service: str
    overall_progress: Progress
    overall_task_id: Any
    num_steps: int
    service_progress: Progress = field(default_factory=lambda: build_service_progress())
    step_progress: Progress = field(default_factory=lambda: build_step_progress())
    deploy_progress: Progress = field(default_factory=lambda: build_deploy_progress())
    completion_message: Progress = field(
        default_factory=lambda: build_completion_message()
    )
    infrastructure_logs: Optional[str] = field(default=None)
    service_task_id: Any = field(init=False)
    deploy_task_id: Any = field(default=None, init=False)
    # this is lazily setup so we do type ignore here
    logs_table: Table = field(default=None, init=False)  # type: ignore

    def __post_init__(self):
        self.service_task_id = self.service_progress.add_task(
            f"Deploying {self.service}", total=self.num_steps
        )
        self.logs_table = Table(title="", show_header=True, box=None, padding=(0, 1))
        self.logs_table.add_column("", overflow="fold")
        if self.infrastructure_logs:
            self.logs_table.add_row(
                f"[bold]View infrastructure logs at[/bold]: {self.infrastructure_logs}"
            )

    def start(self, start_description: str, end_description: str, steps: int):
        self.deploy_task_id = self.deploy_progress.add_task(
            start_description, total=steps
        )
        self.update(end_description)

    def done(self):
        self.service_progress.update(self.overall_task_id, completed=self.num_steps)

    @contextmanager
    def step(self, start_description: str, end_description: str) -> Generator:
        step_task_id = self.step_progress.add_task(start_description, total=1)
        failed = False
        try:
            yield self
        except Exception as e:
            failed = True
            self.step_progress.update(
                step_task_id,
                description=f"[red]✗ {start_description} failed[/red]",
                completed=1,
            )
            raise e
        finally:
            if not failed:
                self.step_progress.update(
                    step_task_id,
                    description=f"[green]✓ {end_description}[/green]",
                    completed=1,
                )
                self.deploy_progress.update(self.deploy_task_id, advance=1)

    def update(self, description: str, failed=False):
        self.service_progress.update(self.service_task_id, description=description)
        if failed:
            self.service_progress.update(self.overall_task_id, completed=self.num_steps)

    def complete(self, message: str):
        self.completion_message.add_task(message, total=None)

    def add_logs_row(self, name: str, path: str):
        self.logs_table.add_row(f"[bold]View {name} logs at[/bold]: {path}")


class FlowLogger:
    def __init__(self, count: int):
        self.overall_progress = build_overall_progress()
        self.overall_task_id = self.overall_progress.add_task(
            "workflows completed", total=count
        )
        self.panels: List[Panel] = []

    def __enter__(self):
        self.live = Live(refresh_per_second=4, vertical_overflow="visible")
        self.live.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.live.__exit__(exc_type, exc_value, traceback)

    @contextmanager
    def start_workflow(
        self, service: str, num_steps: int, infrastructure_logs: str
    ) -> Generator[WorkflowProgress, None, None]:
        workflow_progress = WorkflowProgress(
            service,
            self.overall_progress,
            self.overall_task_id,
            num_steps,
            infrastructure_logs=infrastructure_logs,
        )
        panel = Panel(
            Group(
                workflow_progress.service_progress,
                workflow_progress.step_progress,
                workflow_progress.deploy_progress,
                workflow_progress.completion_message,
                workflow_progress.logs_table,
            ),
            title=f"[bold]{service}",
        )
        self.panels.append(panel)
        self.update_live_display()
        try:
            workflow_progress.start(
                f"Deploying {service}", f"{service} deployed", steps=num_steps
            )
            yield workflow_progress
        finally:
            workflow_progress.done()
            self.overall_progress.update(self.overall_task_id, advance=1)
            self.update_live_display()

    def update_live_display(self):
        overall_group = Group(*self.panels, self.overall_progress)
        self.live.update(overall_group)
