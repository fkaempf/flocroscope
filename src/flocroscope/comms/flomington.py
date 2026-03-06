"""Flomington integration (placeholder).

Future integration with the Flomington Drosophila stock management
system (https://floriankaempf.com/flomington/) for linking virtual
reality experimental sessions to fly stocks, crosses, and collected
animals.

Flomington is a lab-internal web app (React 18 + Supabase + Tailwind)
that manages the full lifecycle of Drosophila genetics work: stock
maintenance (flip scheduling, temperature tracking), cross management
(8-stage lifecycle from setup through screening), virgin banking, and
label printing with QR codes.  It runs as a StatiCrypt-encrypted
single-page app on GitHub Pages with real-time Supabase sync across
7 lab members.

Technical details for future implementation:
    - **Backend**: Supabase (Postgres + real-time subscriptions).
      Use ``supabase-py`` SDK to query the ``stocks`` and ``crosses``
      tables.  Field names are camelCase in JS / snake_case in Postgres
      — explicit field maps (STOCK_FIELD_MAP, CROSS_FIELD_MAP) handle
      translation.
    - **Sync protocol**: Changes are auto-pushed with 3s debounce.
      Real-time subscriptions (``postgres_changes`` channel) propagate
      updates instantly.  A ``markEdited()`` mechanism flags locally-
      modified records for 10s to prevent overwrites.
    - **QR deep links**: Labels encode ``?s=<8-char-id-prefix>`` URLs.
      Our scanner should parse this prefix to look up stocks/crosses.

Planned integration points:
    - **Stock lookup**: Query fly genotype, source (BDSC/VDRC/Kyoto),
      genetic tags (GAL4, UAS, Split-GAL4, CsChrimson, GCaMP, etc.),
      and maintenance info from Flomington's Supabase backend.
    - **Cross linking**: Associate an experimental session with a
      specific cross (identified by cross ID), including parent
      genotypes, cross status, and experiment type (2P, 2P+VR,
      Optogenetics, Behavior, etc.).
    - **Auto-tagging**: When a fly is presented for an experiment,
      scan its QR label to auto-populate session metadata with
      stock name, genotype, cross parents, and age.
    - **Results push**: After an experiment, push trial summary
      data (session duration, number of trials, stimulus type)
      back to Flomington as cross notes or experiment records.
    - **Ripening awareness**: Respect Flomington's ripening logic
      (3 days for optogenetics/retinal, 5 days for GCaMP expression)
      to warn if a fly is used before it's ready.

Cross lifecycle stages (in order):
    1. ``set up`` — cross physically assembled
    2. ``waiting for virgins`` — F0 developing
    3. ``collecting virgins`` — virgin females being collected
    4. ``waiting for progeny`` — F1 developing
    5. ``collecting progeny`` — F1 adults collected
    6. ``ripening`` — 3d (optogenetics/retinal) or 5d (GCaMP)
    7. ``screening`` — phenotype selection
    8. ``done`` — experiment complete

Temperature-based timelines (25°C):
    - Virgin collection: day 9–11 post-setup
    - Progeny collection: day 11–15 post-setup
    (At 18°C: days 17–19 and 19–23 respectively)

Data model maps to Flomington's Supabase tables:
    - ``stocks`` table → :class:`FlyStock`
    - ``crosses`` table → :class:`FlyCross`

This module is a placeholder — all methods log warnings and return
defaults until the Supabase API integration is implemented.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Cross lifecycle stages in order.
CROSS_STATUSES = [
    "set up",
    "waiting for virgins",
    "collecting virgins",
    "waiting for progeny",
    "collecting progeny",
    "ripening",
    "screening",
    "done",
]

# Ripening duration by experiment context (days).
RIPENING_DAYS = {
    "optogenetics": 3,  # retinal uptake
    "calcium_imaging": 5,  # GCaMP expression
    "default": 0,  # skip ripening
}


@dataclass
class FlomingtonConfig:
    """Configuration for Flomington integration.

    Attributes:
        enabled: Whether Flomington integration is active.
        supabase_url: Supabase project URL.
        supabase_anon_key: Supabase anonymous/public API key.
        auto_tag: Automatically tag sessions with fly metadata
            when a QR code is scanned.
        user: Current user name in Flomington (for ownership).
    """

    enabled: bool = False
    supabase_url: str = ""
    supabase_anon_key: str = ""
    auto_tag: bool = True
    user: str = ""


@dataclass
class FlyStock:
    """A Drosophila stock record from Flomington.

    Represents one maintained fly genotype in the lab's collection.

    Attributes:
        stock_id: Unique 8-character Flomington ID.
        name: Human-readable stock name.
        genotype: Full genotype string.
        source: Origin database (Bloomington, VDRC, Kyoto, Other).
        source_id: ID in the source database.
        flybase_id: FlyBase gene/allele identifier.
        janelia_line: Janelia line identifier (if applicable).
        collection: Named group/category.
        temperature: Storage temperature (``"25C"``, ``"18C"``,
            ``"RT"``).
        copies: Number of active vial copies.
        maintainer: Lab member responsible for flipping.
        genetic_tags: Auto-detected markers (GAL4, UAS, GCaMP,
            CsChrimson, balancers, etc.).
        notes: Free-form notes.
    """

    stock_id: str = ""
    name: str = ""
    genotype: str = ""
    source: str = ""
    source_id: str = ""
    flybase_id: str = ""
    janelia_line: str = ""
    collection: str = ""
    temperature: str = "25C"
    copies: int = 1
    maintainer: str = ""
    genetic_tags: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class FlyCross:
    """A cross record from Flomington.

    Tracks the full lifecycle of a genetic cross through 8 stages:
    set up → waiting for virgins → collecting virgins →
    waiting for progeny → collecting progeny → ripening →
    screening → done.

    Attributes:
        cross_id: Unique 8-character Flomington ID.
        virgin_parent: Stock name of the virgin parent.
        virgin_genotype: Genotype of the virgin parent.
        male_parent: Stock name of the male parent.
        male_genotype: Genotype of the male parent.
        status: Current lifecycle stage.
        experiment_type: Planned experiment (``"2P"``, ``"2P+VR"``,
            ``"Optogenetics"``, ``"Behavior"``, ``"VR"``, etc.).
        experiment_date: Scheduled experiment date (ISO format).
        temperature: Cross temperature (``"25C"`` or ``"18C"``).
        setup_date: Date the cross was set up (ISO format).
        owner: Lab member who owns this cross.
        notes: Free-form notes.
    """

    cross_id: str = ""
    virgin_parent: str = ""
    virgin_genotype: str = ""
    male_parent: str = ""
    male_genotype: str = ""
    status: str = "set up"
    experiment_type: str = ""
    experiment_date: str = ""
    temperature: str = "25C"
    setup_date: str = ""
    owner: str = ""
    notes: str = ""


class FlomingtonClient:
    """Client for the Flomington Supabase backend.

    Placeholder — all methods log warnings and return defaults.
    The actual implementation will use the ``supabase-py`` SDK
    to query the ``stocks`` and ``crosses`` tables.

    Args:
        config: Flomington configuration.
    """

    def __init__(self, config: FlomingtonConfig) -> None:
        self._config = config
        self._connected = False

    def connect(self) -> bool:
        """Connect to the Flomington Supabase backend.

        Returns:
            True if connection succeeded.
        """
        if not self._config.supabase_url:
            logger.info(
                "Flomington: no Supabase URL configured, skipping",
            )
            return False
        logger.warning(
            "FlomingtonClient.connect() — not yet implemented",
        )
        return False

    def disconnect(self) -> None:
        """Close the connection."""
        self._connected = False

    def get_stock(self, stock_id: str) -> FlyStock | None:
        """Retrieve a stock record by ID.

        Args:
            stock_id: Flomington stock identifier (8-char prefix
                from QR code is sufficient).

        Returns:
            The stock record, or None if not found.
        """
        logger.warning(
            "FlomingtonClient.get_stock(%s) — not yet implemented",
            stock_id,
        )
        return None

    def get_cross(self, cross_id: str) -> FlyCross | None:
        """Retrieve a cross record by ID.

        Args:
            cross_id: Flomington cross identifier.

        Returns:
            The cross record, or None if not found.
        """
        logger.warning(
            "FlomingtonClient.get_cross(%s) — not yet implemented",
            cross_id,
        )
        return None

    def search_stocks(
        self, query: str, limit: int = 10,
    ) -> list[FlyStock]:
        """Search stocks by name or genotype.

        Args:
            query: Search string (matched against name and genotype).
            limit: Maximum results to return.

        Returns:
            List of matching stocks (empty if not implemented).
        """
        logger.warning(
            "FlomingtonClient.search_stocks(%s) — "
            "not yet implemented",
            query,
        )
        return []

    def get_crosses_for_experiment(
        self, experiment_type: str,
    ) -> list[FlyCross]:
        """Get crosses ready for a specific experiment type.

        Filters to crosses in the 'ripening' or 'screening' stage
        with the matching experiment type.

        Args:
            experiment_type: One of ``"2P"``, ``"2P+VR"``,
                ``"Optogenetics"``, ``"Behavior"``, ``"VR"``, etc.

        Returns:
            List of matching crosses (empty if not implemented).
        """
        logger.warning(
            "FlomingtonClient.get_crosses_for_experiment(%s) — "
            "not yet implemented",
            experiment_type,
        )
        return []

    def tag_session(
        self,
        session_id: str,
        stock_id: str = "",
        cross_id: str = "",
    ) -> bool:
        """Link an experimental session to a stock or cross.

        Args:
            session_id: Local session identifier.
            stock_id: Flomington stock ID (if testing a stock fly).
            cross_id: Flomington cross ID (if testing F1 progeny).

        Returns:
            True if tagging succeeded.
        """
        logger.warning(
            "FlomingtonClient.tag_session(%s, stock=%s, cross=%s)"
            " — not yet implemented",
            session_id, stock_id, cross_id,
        )
        return False

    def push_results(
        self,
        session_id: str,
        metadata: dict[str, Any],
    ) -> bool:
        """Push experimental results to Flomington.

        Appends experiment summary as a note on the linked cross
        or stock record.

        Args:
            session_id: Local session identifier.
            metadata: Trial/session metadata (stimulus type,
                duration, trial count, etc.).

        Returns:
            True if push succeeded.
        """
        logger.warning(
            "FlomingtonClient.push_results(%s) — "
            "not yet implemented",
            session_id,
        )
        return False

    @property
    def connected(self) -> bool:
        """Whether the client is connected to Supabase."""
        return self._connected
