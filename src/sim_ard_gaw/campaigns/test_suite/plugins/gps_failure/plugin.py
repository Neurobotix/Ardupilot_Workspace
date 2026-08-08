"""Plugin assembly for the gps_failure lane."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...core.analysis import AnalyzerChain
from ...core.attempt_runner import AttemptRunner, StagedStrategy
from ...core.case_generator import CaseGenerator
from ...core.manifest import Manifest
from . import defaults
from .analyzers import GpsFailureAnalyzer, GpsFailureVerdictPolicy
from .case_generator import GpsFailureCaseGenerator
from .config import GpsFailureConfig
from .control import GpsFailureMissionControl
from .environment import GpsFailureEnvironment
from .manifest import GpsFailureManifest
from .monitor import GpsFailureMonitor
from .stimulus import GpsFailureStimulus


@dataclass
class GpsFailurePlugin:
    config: GpsFailureConfig
    case_generator: CaseGenerator
    environment: GpsFailureEnvironment
    manifest: Manifest

    def attempt_runner(self) -> AttemptRunner:
        return AttemptRunner(
            environment=self.environment,
            strategy=StagedStrategy(
                stimulus=GpsFailureStimulus(self.config),
                control=GpsFailureMissionControl(self.config),
                monitor=GpsFailureMonitor(self.config),
                analyzers=AnalyzerChain([GpsFailureAnalyzer()]),
                verdict_policy=GpsFailureVerdictPolicy(),
            ),
            manifest=self.manifest,
            artifact_root=self.config.campaign_root,
            prewrite_running_record=True,
        )

    def attempt_dir_factory(self):
        def _factory(
            manifest: Manifest,
            case,
            attempt_index: int | None = None,
        ) -> Path:
            idx = (
                int(attempt_index)
                if attempt_index is not None
                else manifest.next_attempt_index(case)
            )
            return defaults.attempt_dir(self.config.campaign_root, case.case_id, idx)

        return _factory


def build_plugin(config: GpsFailureConfig | None = None) -> GpsFailurePlugin:
    if config is None:
        config = GpsFailureConfig()
    return GpsFailurePlugin(
        config=config,
        case_generator=GpsFailureCaseGenerator(config),
        environment=GpsFailureEnvironment(config),
        manifest=GpsFailureManifest(config.campaign_root),
    )
