"""Abstract base class that every quantum memory protocol must implement."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
import numpy as np


@dataclass
class SimulationResult:
    """Container for results returned by any memory protocol simulation."""
    E: np.ndarray                   # Electric field  [time, z]
    P: np.ndarray                   # Polarisation     [time, z]
    S: np.ndarray                   # Spin wave        [time, z]
    z: np.ndarray = None            # Spatial grid     [z]
    t: np.ndarray = None            # Time sample grid [time]
    rabi_profile: np.ndarray = None # Control field vs dense time grid
    t_dense: np.ndarray = None      # Dense time grid matching rabi_profile
    E_real: Optional[np.ndarray] = None   # Re(E) signed  [time, z]
    P_real: Optional[np.ndarray] = None   # Re(P) signed  [time, z]
    S_real: Optional[np.ndarray] = None   # Re(S) signed  [time, z]
    metrics: dict = field(default_factory=dict)
    protocol: str = "unknown"

    # Convenience accessors
    @property
    def n_time(self) -> int:
        return self.t.shape[0]

    @property
    def n_z(self) -> int:
        return self.z.shape[0]


class BaseMemoryProtocol(ABC):
    """
    Every protocol (EIT, AFC, GEM …) subclasses this and implements `run`.
    The GUI calls `run(progress_cb)` in a worker thread.
    """

    #: Human-readable name shown in the GUI tab header
    NAME: str = "Unnamed Protocol"
    #: Short description shown in the sidebar
    DESCRIPTION: str = ""

    @abstractmethod
    def run(
        self,
        params: dict[str, Any],
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> SimulationResult:
        """
        Execute the simulation.

        Parameters
        ----------
        params : dict
            Protocol-specific parameter dictionary.
        progress_callback : callable(int) | None
            Called with integer percent 0–100 during the simulation so the
            GUI can update a progress bar.

        Returns
        -------
        SimulationResult
        """

    @abstractmethod
    def default_params(self) -> dict[str, Any]:
        """Return a dict of default simulation parameters."""

    @abstractmethod
    def param_schema(self) -> list[dict]:
        """
        Return a list of parameter descriptors used by the GUI to build the
        control panel automatically.

        Each descriptor is a dict with keys:
          name       str   – parameter key (matches default_params)
          label      str   – display label
          type       str   – 'float' | 'int' | 'choice'
          min        num   – minimum value (float/int types)
          max        num   – maximum value
          step       num   – spinbox step
          decimals   int   – decimal places (float type)
          choices    list  – allowed values (choice type)
          unit       str   – unit string shown next to the spinbox
          group      str   – collapsible group name in the control panel
          tooltip    str   – mouse-over help text
        """
