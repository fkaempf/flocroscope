"""Hardware integration test stubs.

These tests require physical hardware (cameras, projector, FicTrac,
LED controller, ScanImage) and are automatically skipped in CI by
the ``hardware`` marker defined in ``conftest.py``.

Each stub documents the expected test behaviour so that the full
hardware integration tests can be filled in when running on a rig.
"""

from __future__ import annotations

import pytest


@pytest.mark.hardware
class TestFicTracLive:
    """Live FicTrac treadmill connection tests.

    Requires a running FicTrac instance streaming data on the
    configured TCP port (default ``localhost:2000``).
    """

    def test_connect_and_receive_frame(self) -> None:
        """Connect to FicTrac, start the receiver, and poll one frame.

        Expected behaviour:
        - ``FicTracReceiver.start()`` connects within 5 seconds.
        - ``receiver.connected`` becomes ``True``.
        - ``receiver.poll()`` returns a ``FicTracFrame`` with a
          non-zero ``frame_count``.
        - ``receiver.stop()`` disconnects cleanly.
        """

    def test_reconnect_after_disconnect(self) -> None:
        """Verify the receiver reconnects if FicTrac restarts.

        Expected behaviour:
        - After the initial connection is dropped, the background
          thread retries and ``connected`` becomes ``True`` again
          within 5 seconds.
        """


@pytest.mark.hardware
class TestCamAlviumCapture:
    """Live Alvium camera capture tests.

    Requires an Allied Vision Alvium camera connected via USB3
    or GigE, and the Vimba X GenTL producer installed.
    """

    def test_grab_single_frame(self) -> None:
        """Open the Alvium camera and capture one frame.

        Expected behaviour:
        - ``CamAlvium().start()`` succeeds without raising.
        - ``cam.grab()`` returns a numpy array with ``ndim >= 2``
          and ``dtype == np.uint8``.
        - ``cam.stop()`` releases the hardware cleanly.
        """

    def test_exposure_setting(self) -> None:
        """Set exposure time and verify it takes effect.

        Expected behaviour:
        - After setting ``exposure_ms=20.0``, the captured frame's
          mean intensity should differ from the default exposure.
        """


@pytest.mark.hardware
class TestCamFlirCapture:
    """Live FLIR/Spinnaker camera capture tests.

    Requires a FLIR camera connected via USB3, the Spinnaker SDK
    installed, and the ``rotpy`` Python package available.
    """

    def test_grab_single_frame(self) -> None:
        """Open the FLIR camera and capture one frame.

        Expected behaviour:
        - ``CamRotPy().start()`` succeeds without raising.
        - ``cam.grab()`` returns a numpy array with ``ndim >= 2``
          and ``dtype == np.uint8``.
        - ``cam.stop()`` releases the hardware cleanly.
        """

    def test_gain_setting(self) -> None:
        """Set analog gain and verify it takes effect.

        Expected behaviour:
        - After setting ``gain_db=12.0``, the captured frame's
          mean intensity should differ from the default gain.
        """


@pytest.mark.hardware
class TestLedController:
    """Live LED controller tests.

    Requires a ZMQ subscriber (Arduino/ESP32) listening on the
    configured port (default ``tcp://*:5001``).
    """

    def test_send_on_off(self) -> None:
        """Send on/off commands and verify no exceptions.

        Expected behaviour:
        - ``LedController().start()`` binds the ZMQ PUB socket.
        - ``led.on(intensity=0.5)`` and ``led.off()`` complete
          without raising.
        - ``led.connected`` is ``True`` while the socket is bound.
        - ``led.stop()`` closes the socket cleanly.
        """

    def test_send_pulse(self) -> None:
        """Send a pulse command with specified duration.

        Expected behaviour:
        - ``led.pulse(intensity=1.0, duration_ms=50)`` publishes
          a JSON message with the correct fields.
        - The subscriber device triggers the LED for approximately
          50 ms (verified externally with a photodiode).
        """


@pytest.mark.hardware
class TestScanImageSync:
    """Live ScanImage synchronization tests.

    Requires a MATLAB ScanImage instance (or mock client) that
    connects to the TCP server and sends newline-delimited JSON.
    """

    def test_accept_connection_and_receive_trial_event(self) -> None:
        """Start the server, accept a client, and receive an event.

        Expected behaviour:
        - ``ScanImageSync().start()`` begins listening on port 5000.
        - A test TCP client connects and sends a ``trial_start`` JSON.
        - ``sync.poll()`` returns a list containing a ``TrialEvent``
          with ``event_type == "trial_start"``.
        - ``sync.stop()`` shuts down the server cleanly.
        """

    def test_handles_invalid_json(self) -> None:
        """Verify malformed JSON lines are skipped without crashing.

        Expected behaviour:
        - The server logs a warning for invalid lines.
        - ``sync.poll()`` returns an empty list for those lines.
        - Valid messages arriving afterward are still processed.
        """


@pytest.mark.hardware
@pytest.mark.gpu
class TestFullStimulusRun:
    """Full stimulus rendering integration test.

    Requires a display/projector, OpenGL GPU context, and optionally
    a connected camera for warp verification. Marked as both
    ``hardware`` and ``gpu`` so it is skipped in all headless CI
    environments.
    """

    def test_3d_fly_renders_one_frame(self) -> None:
        """Initialize the 3D fly renderer and draw one frame.

        Expected behaviour:
        - Pygame window opens at the configured resolution.
        - The GLB model loads and renders without shader errors.
        - The warp map is applied correctly (projector correction).
        - At least one frame completes without raising.
        - Cleanup shuts down OpenGL and pygame cleanly.
        """

    def test_2d_sprite_renders_one_frame(self) -> None:
        """Initialize the 2D sprite stimulus and draw one frame.

        Expected behaviour:
        - Sprite images load from the configured path.
        - The sprite is blitted at the correct arena position.
        - The warp shader transforms the output.
        - At least one frame completes without raising.
        """

    def test_warp_map_identity_produces_no_distortion(self) -> None:
        """Render with an identity warp map and verify output.

        Expected behaviour:
        - With ``mapx[y,x] = x`` and ``mapy[y,x] = y``, the
          rendered output matches the un-warped reference within
          a 1-pixel tolerance.
        """
