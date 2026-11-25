# -*- coding: utf-8 -*-
from typing import List, Any, Dict, Optional
import threading

from qgis.core import QgsApplication

from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.BaseTask import BaseTask
from ..config.LogUtils import LogUtils


class ParallelStep(BaseStep):
    """Composite step that executes independent steps in parallel."""

    def __init__(self, steps: List[BaseStep], description: Optional[str] = None):
        if not isinstance(steps, list):
            raise TypeError("ParallelStep expects a list of BaseStep instances")
        super().__init__()
        self._steps = steps
        self._description = description
        self.logger = LogUtils(tool="ParallelStep", class_name="ParallelStep")

    def name(self) -> str:
        if self._description:
            return f"Parallel[{self._description}]"
        names = ",".join([step.name() for step in self._steps])
        return f"Parallel[{names}]"

    def should_run(self, context: ExecutionContext) -> bool:
        return any(step.should_run(context) for step in self._steps)

    def create_task(self, context: ExecutionContext):
        task = _ParallelGroupTask(self._steps, context, self.name())
        # The engine calls create_task() on the main QGIS thread. Registering
        # child tasks here avoids calling the QGIS task manager from run().
        task.schedule_subtasks()
        return task

    def on_success(self, context: ExecutionContext, result: Any) -> None:
        try:
            context.set("parallel_result", result)
        except Exception as exc:
            self.logger.error(f"ParallelStep.on_success error: {exc}")

    def on_error(self, context: ExecutionContext, exception: Exception) -> None:
        try:
            context.add_error(exception)
        except Exception as exc:
            self.logger.error(f"ParallelStep.on_error error: {exc}")


class _ParallelGroupTask(BaseTask):
    """Waits for a group of already registered child tasks."""

    def __init__(
        self,
        steps: List[BaseStep],
        context: ExecutionContext,
        description: str = "ParallelGroup",
    ):
        super().__init__(description, tool_key=context.tool_key)
        self._steps = steps
        self._context = context
        self._lock = threading.Lock()
        self._pending = 0
        self._total = 0
        self._results: Dict[str, Any] = {}
        self._error: Optional[Exception] = None
        self._done_event = threading.Event()
        self._subtasks: List[BaseTask] = []
        self._prepared = False
        self.logger = LogUtils(
            tool="ParallelGroupTask", class_name="_ParallelGroupTask"
        )

    def schedule_subtasks(self) -> None:
        """Create and register child tasks from the main QGIS thread."""
        if self._prepared:
            return
        self._prepared = True

        with self._lock:
            for step in self._steps:
                try:
                    task = step.create_task(self._context)
                except Exception as exc:
                    self._error = exc
                    self.exception = exc
                    self._done_event.set()
                    break

                if task is None:
                    continue

                self._subtasks.append(task)
                task.on_success = self._make_success_handler(step)
                task.on_error = self._make_error_handler(step)
                self._pending += 1

            self._total = self._pending

        if self._error is not None:
            self._cancel_subtasks()
            return

        if not self._subtasks:
            self._done_event.set()
            return

        # This method is called by ParallelStep.create_task(), on the main
        # thread. Never move addTask() into a worker's run() method.
        for subtask in list(self._subtasks):
            try:
                QgsApplication.taskManager().addTask(subtask)
            except Exception as exc:
                with self._lock:
                    if self._error is None:
                        self._error = exc
                        self.exception = exc
                    self._done_event.set()
                self._cancel_subtasks()
                break

    def _make_success_handler(self, step: BaseStep):
        def _on_success(result):
            try:
                try:
                    step.on_success(self._context, result)
                except Exception as exc:
                    self.logger.error(f"substep on_success error: {exc}")

                with self._lock:
                    self._results[step.name()] = result
                    self._pending -= 1
                    completed = self._total - self._pending
                    is_done = self._pending <= 0
                    if is_done:
                        self._done_event.set()

                # Child finished() callbacks run on the QGIS main thread, so
                # this progress update never comes from imagery worker threads.
                try:
                    self.setProgress(int(completed * 100 / max(1, self._total)))
                except Exception as exc:
                    self.logger.error(f"Parallel progress update error: {exc}")
            except Exception as exc:
                self.logger.error(f"subtask success handler error: {exc}")

        return _on_success

    def _make_error_handler(self, step: BaseStep):
        def _on_error(exception):
            if not isinstance(exception, Exception):
                exception = Exception(str(exception or "Parallel child failed"))
            try:
                try:
                    step.on_error(self._context, exception)
                except Exception as exc:
                    self.logger.error(f"substep on_error error: {exc}")

                with self._lock:
                    if self._error is None:
                        self._error = exception
                        self.exception = exception
                    self._done_event.set()
                self._cancel_subtasks()
            except Exception as exc:
                self.logger.error(f"subtask error handler error: {exc}")

        return _on_error

    def _cancel_subtasks(self) -> None:
        for subtask in list(self._subtasks):
            try:
                subtask.cancel()
            except Exception as exc:
                self.logger.error(f"Error cancelling subtask: {exc}")

    def _run(self) -> bool:
        while not self._done_event.wait(0.05):
            if self.isCanceled():
                self._cancel_subtasks()
                self._done_event.set()
                break

        if self._error is not None:
            self.exception = self._error
            return False
        if self.isCanceled():
            self.exception = Exception("ParallelGroup cancelled")
            return False

        self.result = self._results.copy()
        self.setProgress(100)
        return True
