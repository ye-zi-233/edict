# 延迟导入，避免 python -m app.workers.xxx 时产生 sys.modules 循环警告
def __getattr__(name):
    if name in ("OrchestratorWorker", "run_orchestrator"):
        from .orchestrator_worker import OrchestratorWorker, run_orchestrator
        return {"OrchestratorWorker": OrchestratorWorker, "run_orchestrator": run_orchestrator}[name]
    if name in ("DispatchWorker", "run_dispatcher"):
        from .dispatch_worker import DispatchWorker, run_dispatcher
        return {"DispatchWorker": DispatchWorker, "run_dispatcher": run_dispatcher}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "OrchestratorWorker",
    "run_orchestrator",
    "DispatchWorker",
    "run_dispatcher",
]
