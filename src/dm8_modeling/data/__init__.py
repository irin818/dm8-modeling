"""Read-only experimental session parsing and alignment; legacy imports remain valid."""
from .schema import Session, SessionPaths, StimulusData, ResponseData, ClockData, AlignedSession
from .discovery import discover_sessions
from .clocks import _read_clock, _read_playback_time, associate_imaging_with_updates
from .response import _read_results
from .stimulus import _sha256, verify_binary_stimulus_package
from .alignment import align_session

__all__ = ["Session", "SessionPaths", "StimulusData", "ResponseData", "ClockData", "AlignedSession", "discover_sessions", "align_session", "verify_binary_stimulus_package", "associate_imaging_with_updates"]
