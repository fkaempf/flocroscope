"""GUI panel implementations.

Each panel is a standalone class with a ``draw()`` method that
renders its Dear ImGui content.  Panels are composed by the
main :class:`~flocroscope.gui.app.FlocroscopeApp`.
"""

from flocroscope.gui.panels.behaviour import BehaviourPanel
from flocroscope.gui.panels.calibration import CalibrationPanel
from flocroscope.gui.panels.comms import CommsPanel
from flocroscope.gui.panels.config_editor import ConfigEditorPanel
from flocroscope.gui.panels.fictrac import FicTracPanel
from flocroscope.gui.panels.flomington import FlomingtonPanel
from flocroscope.gui.panels.mapping import MappingPanel
from flocroscope.gui.panels.optogenetics import OptogeneticsPanel
from flocroscope.gui.panels.scanimage import ScanImagePanel
from flocroscope.gui.panels.session import SessionPanel
from flocroscope.gui.panels.stimulus import StimulusPanel
from flocroscope.gui.panels.tracking import TrackingPanel

__all__ = [
    "BehaviourPanel",
    "CalibrationPanel",
    "CommsPanel",
    "ConfigEditorPanel",
    "FicTracPanel",
    "FlomingtonPanel",
    "MappingPanel",
    "OptogeneticsPanel",
    "ScanImagePanel",
    "SessionPanel",
    "StimulusPanel",
    "TrackingPanel",
]
