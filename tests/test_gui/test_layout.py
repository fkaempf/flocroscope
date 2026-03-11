"""Tests for GUI layout configuration.

Pure Python tests -- no DearPyGui required.
"""

from __future__ import annotations

import pytest

from flocroscope.gui.layout import (
    ExperimentMode,
    HARDWARE_SECTIONS,
    HardwareSection,
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


class TestHardwareSection:
    """Tests for the HardwareSection enum."""

    def test_all_sections_defined(self) -> None:
        assert len(HardwareSection) == 5

    def test_values(self) -> None:
        assert (
            HardwareSection.FICTRAC.value
            == "FicTrac / Treadmill"
        )
        assert HardwareSection.TRACKING.value == "Tracking"
        assert (
            HardwareSection.SCANIMAGE.value
            == "ScanImage / 2-Photon"
        )
        assert (
            HardwareSection.OPTOGENETICS.value
            == "Optogenetics / LED"
        )
        assert (
            HardwareSection.COMMUNICATIONS.value
            == "Communications"
        )

    def test_string_construction(self) -> None:
        assert (
            HardwareSection("FicTrac / Treadmill")
            is HardwareSection.FICTRAC
        )

    def test_sections_used_as_keys(self) -> None:
        """All HardwareSection values appear in HARDWARE_SECTIONS."""
        for hs in HardwareSection:
            assert hs in HARDWARE_SECTIONS


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

    # -- Behaviour mode: LED-only --
    def test_fictrac_not_in_behaviour(self) -> None:
        """Behaviour mode does not use FicTrac."""
        section = HARDWARE_SECTIONS[
            HardwareSection.FICTRAC
        ]
        assert ExperimentMode.BEHAVIOUR not in section

    def test_tracking_not_in_behaviour(self) -> None:
        """Behaviour mode does not use tracking."""
        section = HARDWARE_SECTIONS[
            HardwareSection.TRACKING
        ]
        assert ExperimentMode.BEHAVIOUR not in section

    def test_comms_not_in_behaviour(self) -> None:
        """Behaviour mode does not use comms section."""
        section = HARDWARE_SECTIONS[
            HardwareSection.COMMUNICATIONS
        ]
        assert ExperimentMode.BEHAVIOUR not in section

    def test_opto_in_behaviour(self) -> None:
        """Behaviour mode uses optogenetics (LED-only)."""
        section = HARDWARE_SECTIONS[
            HardwareSection.OPTOGENETICS
        ]
        assert ExperimentMode.BEHAVIOUR in section

    # -- VR mode: always FicTrac, tracking, comms --
    def test_fictrac_in_vr(self) -> None:
        """VR always requires FicTrac."""
        section = HARDWARE_SECTIONS[
            HardwareSection.FICTRAC
        ]
        assert ExperimentMode.VR in section

    def test_tracking_in_vr(self) -> None:
        section = HARDWARE_SECTIONS[
            HardwareSection.TRACKING
        ]
        assert ExperimentMode.VR in section

    def test_comms_in_vr(self) -> None:
        section = HARDWARE_SECTIONS[
            HardwareSection.COMMUNICATIONS
        ]
        assert ExperimentMode.VR in section

    def test_opto_not_in_vr(self) -> None:
        """VR does not show optogenetics by default."""
        section = HARDWARE_SECTIONS[
            HardwareSection.OPTOGENETICS
        ]
        assert ExperimentMode.VR not in section

    def test_scanimage_not_in_vr(self) -> None:
        """VR alone does not show ScanImage."""
        section = HARDWARE_SECTIONS[
            HardwareSection.SCANIMAGE
        ]
        assert ExperimentMode.VR not in section

    # -- 2P (imaging) mode: SI + opto + FicTrac + tracking --
    def test_scanimage_in_2p(self) -> None:
        section = HARDWARE_SECTIONS[
            HardwareSection.SCANIMAGE
        ]
        assert ExperimentMode.TWO_PHOTON in section

    def test_opto_in_2p(self) -> None:
        section = HARDWARE_SECTIONS[
            HardwareSection.OPTOGENETICS
        ]
        assert ExperimentMode.TWO_PHOTON in section

    def test_fictrac_in_2p(self) -> None:
        section = HARDWARE_SECTIONS[
            HardwareSection.FICTRAC
        ]
        assert ExperimentMode.TWO_PHOTON in section

    def test_tracking_in_2p(self) -> None:
        section = HARDWARE_SECTIONS[
            HardwareSection.TRACKING
        ]
        assert ExperimentMode.TWO_PHOTON in section

    def test_comms_in_2p(self) -> None:
        section = HARDWARE_SECTIONS[
            HardwareSection.COMMUNICATIONS
        ]
        assert ExperimentMode.TWO_PHOTON in section

    # -- VR+2P mode: everything --
    def test_fictrac_in_vr_2p(self) -> None:
        section = HARDWARE_SECTIONS[
            HardwareSection.FICTRAC
        ]
        assert ExperimentMode.TWO_PHOTON_VR in section

    def test_tracking_in_vr_2p(self) -> None:
        section = HARDWARE_SECTIONS[
            HardwareSection.TRACKING
        ]
        assert ExperimentMode.TWO_PHOTON_VR in section

    def test_scanimage_in_vr_2p(self) -> None:
        section = HARDWARE_SECTIONS[
            HardwareSection.SCANIMAGE
        ]
        assert ExperimentMode.TWO_PHOTON_VR in section

    def test_opto_in_vr_2p(self) -> None:
        section = HARDWARE_SECTIONS[
            HardwareSection.OPTOGENETICS
        ]
        assert ExperimentMode.TWO_PHOTON_VR in section

    def test_comms_in_vr_2p(self) -> None:
        section = HARDWARE_SECTIONS[
            HardwareSection.COMMUNICATIONS
        ]
        assert ExperimentMode.TWO_PHOTON_VR in section

    # -- Cross-cutting checks --
    def test_all_sections_have_entries(self) -> None:
        """Every HardwareSection key maps to a non-empty set."""
        for hs in HardwareSection:
            assert len(HARDWARE_SECTIONS[hs]) > 0

    def test_hardware_sections_count(self) -> None:
        """HARDWARE_SECTIONS has exactly 5 entries."""
        assert len(HARDWARE_SECTIONS) == 5

    def test_all_section_values_are_sets(self) -> None:
        """All values in HARDWARE_SECTIONS are sets."""
        for hs in HardwareSection:
            assert isinstance(HARDWARE_SECTIONS[hs], set)

    def test_all_section_values_contain_modes(self) -> None:
        """All sets contain only ExperimentMode members."""
        for hs in HardwareSection:
            for item in HARDWARE_SECTIONS[hs]:
                assert isinstance(item, ExperimentMode)


class TestLayoutCompleteness:
    """Cross-cutting tests to ensure layout is self-consistent."""

    def test_tab_visibility_keys_match_modes(self) -> None:
        """TAB_VISIBILITY keys are exactly the ExperimentMode set."""
        assert set(TAB_VISIBILITY.keys()) == set(ExperimentMode)

    def test_tab_visibility_values_subsets_of_tab(self) -> None:
        """Each visibility set is a subset of all Tab values."""
        all_tabs = set(Tab)
        for mode, tabs in TAB_VISIBILITY.items():
            assert tabs <= all_tabs, (
                f"Mode {mode} has unexpected tabs: "
                f"{tabs - all_tabs}"
            )

    def test_hardware_sections_keys_are_hardware_sections(
        self,
    ) -> None:
        """HARDWARE_SECTIONS keys match HardwareSection values."""
        assert set(HARDWARE_SECTIONS.keys()) == set(
            HardwareSection,
        )

    def test_2p_only_has_three_tabs(self) -> None:
        """2P mode has only Session, Hardware, Settings."""
        assert TAB_VISIBILITY[ExperimentMode.TWO_PHOTON] == {
            Tab.SESSION, Tab.HARDWARE, Tab.SETTINGS,
        }

    def test_behaviour_has_four_tabs(self) -> None:
        """Behaviour mode has 4 tabs (no Calibration)."""
        assert len(
            TAB_VISIBILITY[ExperimentMode.BEHAVIOUR],
        ) == 4

    def test_experiment_mode_is_str_enum(self) -> None:
        """ExperimentMode inherits from str."""
        for mode in ExperimentMode:
            assert isinstance(mode, str)

    def test_tab_is_str_enum(self) -> None:
        """Tab inherits from str."""
        for tab in Tab:
            assert isinstance(tab, str)

    def test_hardware_section_is_str_enum(self) -> None:
        """HardwareSection inherits from str."""
        for hs in HardwareSection:
            assert isinstance(hs, str)


class TestAppLayoutWiring:
    """Tests that app.py hardware section names match layout.py."""

    def test_app_hw_section_names_match_layout(self) -> None:
        """String keys used in app.py match HardwareSection values."""
        from flocroscope.gui.app import FlocroscopeApp  # noqa
        # These are the string keys used in _build_hardware_tab
        app_section_names = [
            "FicTrac / Treadmill",
            "Tracking",
            "ScanImage / 2-Photon",
            "Optogenetics / LED",
            "Communications",
        ]
        for name in app_section_names:
            result = HARDWARE_SECTIONS.get(name)
            assert result is not None, (
                f"App section '{name}' not found "
                f"in HARDWARE_SECTIONS"
            )

    def test_app_tab_tags_cover_all_tabs(self) -> None:
        """_TAB_TAGS in app.py covers every Tab enum member."""
        from flocroscope.gui.app import _TAB_TAGS
        for tab in Tab:
            assert tab in _TAB_TAGS

    def test_app_hw_indicators_are_known(self) -> None:
        """_HW_INDICATORS endpoint names are valid."""
        from flocroscope.gui.app import _HW_INDICATORS
        known_endpoints = {
            "fictrac", "scanimage", "led", "presenter",
        }
        for _, ep_name in _HW_INDICATORS:
            assert ep_name in known_endpoints, (
                f"Unknown endpoint: {ep_name}"
            )
