"""Tests for GUI layout configuration.

Pure Python tests -- no DearPyGui required.
"""

from __future__ import annotations

import pytest

from flocroscope.gui.layout import (
    ExperimentMode,
    HARDWARE_SECTIONS,
    Tab,
    TAB_VISIBILITY,
)


class TestExperimentMode:
    """Tests for the ExperimentMode enum."""

    def test_all_modes_defined(self) -> None:
        assert len(ExperimentMode) == 4

    def test_values(self) -> None:
        assert ExperimentMode.BEHAVIOUR.value == "Behaviour"
        assert ExperimentMode.VR.value == "VR"
        assert ExperimentMode.TWO_PHOTON.value == "2P"
        assert ExperimentMode.TWO_PHOTON_VR.value == "VR+2P"

    def test_string_construction(self) -> None:
        assert ExperimentMode("VR") is ExperimentMode.VR
        assert (
            ExperimentMode("VR+2P")
            is ExperimentMode.TWO_PHOTON_VR
        )

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            ExperimentMode("invalid")


class TestTab:
    """Tests for the Tab enum."""

    def test_all_tabs_defined(self) -> None:
        assert len(Tab) == 5

    def test_values(self) -> None:
        assert Tab.SESSION.value == "Session"
        assert Tab.STIMULUS.value == "Stimulus"
        assert Tab.HARDWARE.value == "Hardware"
        assert Tab.CALIBRATION.value == "Calibration"
        assert Tab.SETTINGS.value == "Settings"


class TestTabVisibility:
    """Tests for TAB_VISIBILITY mapping."""

    def test_all_modes_have_entry(self) -> None:
        for mode in ExperimentMode:
            assert mode in TAB_VISIBILITY

    def test_session_always_visible(self) -> None:
        for mode in ExperimentMode:
            assert Tab.SESSION in TAB_VISIBILITY[mode]

    def test_settings_always_visible(self) -> None:
        for mode in ExperimentMode:
            assert Tab.SETTINGS in TAB_VISIBILITY[mode]

    def test_hardware_always_visible(self) -> None:
        for mode in ExperimentMode:
            assert Tab.HARDWARE in TAB_VISIBILITY[mode]

    def test_stimulus_not_in_2p(self) -> None:
        assert Tab.STIMULUS not in TAB_VISIBILITY[
            ExperimentMode.TWO_PHOTON
        ]

    def test_stimulus_in_behaviour(self) -> None:
        assert Tab.STIMULUS in TAB_VISIBILITY[
            ExperimentMode.BEHAVIOUR
        ]

    def test_stimulus_in_vr(self) -> None:
        assert Tab.STIMULUS in TAB_VISIBILITY[
            ExperimentMode.VR
        ]

    def test_calibration_in_vr(self) -> None:
        assert Tab.CALIBRATION in TAB_VISIBILITY[
            ExperimentMode.VR
        ]

    def test_calibration_not_in_behaviour(self) -> None:
        assert Tab.CALIBRATION not in TAB_VISIBILITY[
            ExperimentMode.BEHAVIOUR
        ]

    def test_calibration_in_2p_vr(self) -> None:
        assert Tab.CALIBRATION in TAB_VISIBILITY[
            ExperimentMode.TWO_PHOTON_VR
        ]

    def test_vr_has_all_tabs(self) -> None:
        assert TAB_VISIBILITY[ExperimentMode.VR] == set(Tab)

    def test_2p_vr_has_all_tabs(self) -> None:
        assert (
            TAB_VISIBILITY[ExperimentMode.TWO_PHOTON_VR]
            == set(Tab)
        )


class TestHardwareSections:
    """Tests for HARDWARE_SECTIONS mapping."""

    def test_fictrac_in_behaviour(self) -> None:
        section = HARDWARE_SECTIONS["FicTrac / Treadmill"]
        assert ExperimentMode.BEHAVIOUR in section
        assert ExperimentMode.VR in section
        assert ExperimentMode.TWO_PHOTON_VR in section

    def test_fictrac_not_in_2p(self) -> None:
        section = HARDWARE_SECTIONS["FicTrac / Treadmill"]
        assert ExperimentMode.TWO_PHOTON not in section

    def test_scanimage_in_2p(self) -> None:
        section = HARDWARE_SECTIONS["ScanImage / 2-Photon"]
        assert ExperimentMode.TWO_PHOTON in section
        assert ExperimentMode.TWO_PHOTON_VR in section

    def test_opto_in_all_modes(self) -> None:
        section = HARDWARE_SECTIONS["Optogenetics / LED"]
        for mode in ExperimentMode:
            assert mode in section

    def test_comms_in_all_modes(self) -> None:
        section = HARDWARE_SECTIONS["Communications"]
        for mode in ExperimentMode:
            assert mode in section

    def test_tracking_in_treadmill_modes(self) -> None:
        section = HARDWARE_SECTIONS["Tracking"]
        assert ExperimentMode.BEHAVIOUR in section
        assert ExperimentMode.VR in section
        assert ExperimentMode.TWO_PHOTON_VR in section
        assert ExperimentMode.TWO_PHOTON not in section
