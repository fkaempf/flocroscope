"""GUI panel implementations.

Each panel is a standalone class with a ``draw()`` method that
renders its Dear ImGui content.  Panels are composed by the
main :class:`~virtual_reality.gui.app.VirtualRealityApp`.
"""

from virtual_reality.gui.panels.comms import CommsPanel
from virtual_reality.gui.panels.config_editor import ConfigEditorPanel
from virtual_reality.gui.panels.session import SessionPanel
from virtual_reality.gui.panels.stimulus import StimulusPanel

__all__ = [
    "CommsPanel",
    "ConfigEditorPanel",
    "SessionPanel",
    "StimulusPanel",
]
