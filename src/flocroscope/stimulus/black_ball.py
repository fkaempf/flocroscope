"""Black-ball stimulus.

Renders the testmodel.glb (black ball) using the same 3D rendering
pipeline as Fly3D.  This is functionally identical to the Fly 3D
stimulus but loads the ball model instead of the fly model.

Can be run standalone::

    python -m flocroscope.stimulus.black_ball [config.yaml]
"""

from __future__ import annotations

from pathlib import Path

from flocroscope.stimulus.fly_3d import Fly3DStimulus


class BlackBallStimulus(Fly3DStimulus):
    """3D black ball stimulus using testmodel.glb.

    Inherits all behaviour from Fly3DStimulus but overrides the
    model path to load the ball model.
    """
    pass


def _build_parser() -> "argparse.ArgumentParser":
    """Build the argument parser for the black ball CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the black ball stimulus (testmodel.glb).",
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=None,
        help="Path to a YAML configuration file.",
    )
    parser.add_argument(
        "--fps", "-f",
        type=int,
        default=None,
        help="Override target FPS.",
    )
    parser.add_argument(
        "--no-warp",
        action="store_true",
        default=False,
        help="Disable projector warp map even if configured.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--windowed",
        action="store_true",
        default=False,
        help="Run in a windowed (bordered) mode.",
    )
    group.add_argument(
        "--fullscreen",
        action="store_true",
        default=False,
        help="Run in borderless fullscreen mode.",
    )
    parser.add_argument(
        "--monitor", "-m",
        type=str,
        default=None,
        help="Monitor selection: 'left' or 'right'.",
    )
    return parser


def main() -> None:
    """CLI entry point for the black ball stimulus."""
    from flocroscope.config.loader import load_config
    from flocroscope.config.schema import _resolve_default_paths
    from flocroscope.logging_config import setup_logging

    setup_logging()

    parser = _build_parser()
    args = parser.parse_args()

    if args.config is not None:
        config = load_config(args.config)
    else:
        config = _resolve_default_paths()

    if args.fps is not None:
        config.display.target_fps = args.fps
    if args.no_warp:
        config.warp.mapx_path = ""
        config.warp.mapy_path = ""
    if args.windowed:
        config.display.borderless = False
    elif args.fullscreen:
        config.display.borderless = True
    if args.monitor is not None:
        config.display.monitor = args.monitor

    # Point to testmodel.glb instead of fly.glb
    root = Path(__file__).resolve().parents[3]
    config.fly_model.model_path = str(
        root / "assets" / "models" / "testmodel.glb"
    )

    stimulus = BlackBallStimulus(config=config)

    from flocroscope.session.session import Session
    session = Session(
        config=config,
        stimulus_type="BlackBallStimulus",
    )

    stimulus.run(
        target_fps=config.display.target_fps,
        session=session,
    )


if __name__ == "__main__":
    main()
