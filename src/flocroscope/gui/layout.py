"""Layout configuration: experiment mode -> tab/panel mapping.

Defines which tabs and hardware sections are visible for each
experiment type, so the GUI shows only what is relevant.
"""

from __future__ import annotations

from enum import Enum


class ExperimentMode(str, Enum):
    """Supported experiment types."""

    BEHAVIOUR = "Behaviour"
    VR = "VR"
    TWO_PHOTON = "2P"
    TWO_PHOTON_VR = "VR+2P"


class Tab(str, Enum):
    """Workflow-oriented GUI tabs."""

    SESSION = "Session"
    STIMULUS = "Stimulus"
    HARDWARE = "Hardware"
    CALIBRATION = "Calibration"
    SETTINGS = "Settings"


# Which tabs are visible for each experiment mode.
TAB_VISIBILITY: dict[ExperimentMode, set[Tab]] = {
    ExperimentMode.BEHAVIOUR: {
        Tab.SESSION,
        Tab.STIMULUS,
        Tab.HARDWARE,
        Tab.SETTINGS,
    },
    ExperimentMode.VR: {
        Tab.SESSION,
        Tab.STIMULUS,
        Tab.HARDWARE,
        Tab.CALIBRATION,
        Tab.SETTINGS,
    },
    ExperimentMode.TWO_PHOTON: {
        Tab.SESSION,
        Tab.HARDWARE,
        Tab.SETTINGS,
    },
    ExperimentMode.TWO_PHOTON_VR: {
        Tab.SESSION,
        Tab.STIMULUS,
        Tab.HARDWARE,
        Tab.CALIBRATION,
        Tab.SETTINGS,
    },
}


# Which hardware collapsing sections appear in the Hardware tab
# for each experiment mode.
HARDWARE_SECTIONS: dict[str, set[ExperimentMode]] = {
    "FicTrac / Treadmill": {
        ExperimentMode.BEHAVIOUR,
        ExperimentMode.VR,
        ExperimentMode.TWO_PHOTON_VR,
    },
    "Tracking": {
        ExperimentMode.BEHAVIOUR,
        ExperimentMode.VR,
        ExperimentMode.TWO_PHOTON_VR,
    },
    "ScanImage / 2-Photon": {
        ExperimentMode.TWO_PHOTON,
        ExperimentMode.TWO_PHOTON_VR,
    },
    "Optogenetics / LED": {
        ExperimentMode.BEHAVIOUR,
        ExperimentMode.VR,
        ExperimentMode.TWO_PHOTON,
        ExperimentMode.TWO_PHOTON_VR,
    },
    "Communications": {
        ExperimentMode.BEHAVIOUR,
        ExperimentMode.VR,
        ExperimentMode.TWO_PHOTON,
        ExperimentMode.TWO_PHOTON_VR,
    },
}
