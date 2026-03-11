"""GUI panel implementations.

Each panel is a standalone class with ``build()`` and ``update()``
methods for DearPyGui retained-mode rendering.  Panels are composed
by the main :class:`~flocroscope.gui.app.FlocroscopeApp`.
"""

from flocroscope.gui.panels.behaviour import BehaviourPanel
from flocroscope.gui.panels.calibration import CalibrationPanel
from flocroscope.gui.panels.comms import CommsPanel
from flocroscope.gui.panels.config_editor import ConfigEditorPanel
from flocroscope.gui.panels.fictrac import FicTracPanel
from flocroscope.gui.panels.flomington import FlomingtonPanel
from flocroscope.gui.panels.login import LoginPanel
from flocroscope.gui.panels.mapping import MappingPanel
from flocroscope.gui.panels.optogenetics import OptogeneticsPanel
from flocroscope.gui.panels.presets import PresetsPanel
from flocroscope.gui.panels.scanimage import ScanImagePanel
from flocroscope.gui.panels.session import SessionPanel
from flocroscope.gui.panels.stimulus import StimulusPanel
from flocroscope.gui.panels.tracking import TrackingPanel
from flocroscope.gui.panels.user_profile import UserProfilePanel

__all__ = [
    "BehaviourPanel",
    "CalibrationPanel",
    "CommsPanel",
    "ConfigEditorPanel",
    "FicTracPanel",
    "FlomingtonPanel",
    "LoginPanel",
    "MappingPanel",
    "OptogeneticsPanel",
    "PresetsPanel",
    "ScanImagePanel",
    "SessionPanel",
    "StimulusPanel",
    "TrackingPanel",
    "UserProfilePanel",
]
