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


class HardwareSection(str, Enum):
    """Hardware collapsing section names in the Hardware tab."""

    FICTRAC = "FicTrac / Treadmill"
    TRACKING = "Tracking"
    SCANIMAGE = "ScanImage / 2-Photon"
    OPTOGENETICS = "Optogenetics / LED"
    COMMUNICATIONS = "Communications"


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
#
# Behaviour: LED-only experiments (no ball tracking, no presenter).
# VR: Always needs FicTrac (ball tracking is essential for VR),
#     plus tracking, comms, and optionally opto/scanimage.
# 2P (Imaging): ScanImage + optogenetics + FicTrac + tracking.
# VR+2P: Everything.
HARDWARE_SECTIONS: dict[str, set[ExperimentMode]] = {
    HardwareSection.FICTRAC: {
        ExperimentMode.VR,
        ExperimentMode.TWO_PHOTON,
        ExperimentMode.TWO_PHOTON_VR,
    },
    HardwareSection.TRACKING: {
        ExperimentMode.VR,
        ExperimentMode.TWO_PHOTON,
        ExperimentMode.TWO_PHOTON_VR,
    },
    HardwareSection.SCANIMAGE: {
        ExperimentMode.TWO_PHOTON,
        ExperimentMode.TWO_PHOTON_VR,
    },
    HardwareSection.OPTOGENETICS: {
        ExperimentMode.BEHAVIOUR,
        ExperimentMode.TWO_PHOTON,
        ExperimentMode.TWO_PHOTON_VR,
    },
    HardwareSection.COMMUNICATIONS: {
        ExperimentMode.VR,
        ExperimentMode.TWO_PHOTON,
        ExperimentMode.TWO_PHOTON_VR,
    },
}
