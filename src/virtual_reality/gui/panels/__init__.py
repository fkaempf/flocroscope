"""GUI panel implementations.

Each panel is a standalone class with a ``draw()`` method that
renders its Dear ImGui content.  Panels are composed by the
main :class:`~virtual_reality.gui.app.VirtualRealityApp`.
"""

from virtual_reality.gui.panels.behaviour import BehaviourPanel
from virtual_reality.gui.panels.calibration import CalibrationPanel
from virtual_reality.gui.panels.comms import CommsPanel
from virtual_reality.gui.panels.config_editor import ConfigEditorPanel
from virtual_reality.gui.panels.fictrac import FicTracPanel
from virtual_reality.gui.panels.flomington import FlomingtonPanel
from virtual_reality.gui.panels.mapping import MappingPanel
from virtual_reality.gui.panels.optogenetics import OptogeneticsPanel
from virtual_reality.gui.panels.scanimage import ScanImagePanel
from virtual_reality.gui.panels.session import SessionPanel
from virtual_reality.gui.panels.stimulus import StimulusPanel
from virtual_reality.gui.panels.tracking import TrackingPanel

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
