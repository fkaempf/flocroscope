"""High-level calibration pipeline orchestrator.

Chains the full calibration workflow:

1. Chessboard detection and fisheye K/D/xi calibration.
2. Structured-light projector-camera mapping.
3. Optional sparse dot-grid refinement.
4. Warp map output.

The public entry point is :func:`run_calibration_pipeline`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CalibrationResult:
    """Result of the full calibration pipeline.

    Attributes:
        mapx: Final projector-to-camera X map.
        mapy: Final projector-to-camera Y map.
        valid_mask: Boolean validity mask.
        K: Camera intrinsic matrix (if calibration ran).
        D: Distortion coefficients (if calibration ran).
        xi: MEI fisheye parameter (``None`` for pinhole).
    """

    mapx: np.ndarray
    mapy: np.ndarray
    valid_mask: np.ndarray
    K: np.ndarray | None = None
    D: np.ndarray | None = None
    xi: float | None = None


def save_maps(
    mapx: np.ndarray,
    mapy: np.ndarray,
    valid_mask: np.ndarray,
    output_dir: str | Path,
    experimental: bool = False,
) -> None:
    """Save warp maps and validity mask to disk.

    Args:
        mapx: Projector-to-camera X map.
        mapy: Projector-to-camera Y map.
        valid_mask: Boolean validity mask.
        output_dir: Output directory.
        experimental: If True, save as ``mapx.experimental.npy``.
    """
    d = Path(output_dir)
    d.mkdir(parents=True, exist_ok=True)

    suffix = ".experimental" if experimental else ""
    np.save(str(d / f"mapx{suffix}.npy"), mapx)
    np.save(str(d / f"mapy{suffix}.npy"), mapy)
    np.save(str(d / f"valid.mask{suffix}.npy"), valid_mask)
    logger.info("Saved warp maps to %s", d)


def load_maps(
    directory: str | Path,
    experimental: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load warp maps from disk.

    Args:
        directory: Directory containing map files.
        experimental: If True, load ``mapx.experimental.npy`` variant.

    Returns:
        ``(mapx, mapy, valid_mask)``.
    """
    d = Path(directory)
    suffix = ".experimental" if experimental else ""
    mapx = np.load(str(d / f"mapx{suffix}.npy"))
    mapy = np.load(str(d / f"mapy{suffix}.npy"))

    valid_path = d / f"valid.mask{suffix}.npy"
    if valid_path.exists():
        valid_mask = np.load(str(valid_path)).astype(bool)
    else:
        valid_mask = np.isfinite(mapx) & np.isfinite(mapy)

    return mapx, mapy, valid_mask


def _build_parser() -> "argparse.ArgumentParser":
    """Build the argument parser for the calibration pipeline CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Run the projector-camera calibration pipeline. "
            "Requires hardware (camera + projector)."
        ),
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a YAML config file to load defaults from.",
    )
    parser.add_argument(
        "--camera",
        type=str,
        choices=["alvium", "flir", "none"],
        default=None,
        help="Camera type to use for calibration.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["fisheye", "pinhole"],
        default=None,
        help="Calibration mode.",
    )
    parser.add_argument(
        "--proj-w",
        type=int,
        default=None,
        help="Projector width in pixels.",
    )
    parser.add_argument(
        "--proj-h",
        type=int,
        default=None,
        help="Projector height in pixels.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save calibration results.",
    )
    return parser


def main() -> None:
    """CLI entry point for the calibration pipeline."""
    import argparse

    from virtual_reality.logging_config import setup_logging

    setup_logging()

    parser = _build_parser()
    args = parser.parse_args()

    # Load config if provided, otherwise use defaults
    if args.config is not None:
        from virtual_reality.config.loader import load_config
        config = load_config(args.config)
    else:
        from virtual_reality.config.schema import VirtualRealityConfig
        config = VirtualRealityConfig()

    # Apply CLI overrides
    if args.camera is not None:
        config.calibration.camera_type = args.camera
    if args.mode is not None:
        config.calibration.mode = args.mode
    if args.proj_w is not None:
        config.calibration.proj_w = args.proj_w
    if args.proj_h is not None:
        config.calibration.proj_h = args.proj_h

    logger.info(
        "Calibration pipeline: camera=%s mode=%s proj=%dx%d",
        config.calibration.camera_type,
        config.calibration.mode,
        config.calibration.proj_w,
        config.calibration.proj_h,
    )

    if args.output_dir is not None:
        logger.info("Output directory: %s", args.output_dir)

    print(
        "Calibration pipeline requires hardware (camera + projector).\n"
        "Use the GUI or call run_calibration_pipeline() from Python."
    )


if __name__ == "__main__":
    main()
