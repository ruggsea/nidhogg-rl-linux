"""Interface every environment must satisfy (replay_stub.py, later nidenv.py)."""
from typing import Protocol, Tuple
import numpy as np

N_OBS = 34     # obs shape (34,): 8 base numbers + 2 x 13 nidobs fields (nidenv.py docstring); in [-2, 2]
N_ACTIONS = 7  # action int in 0..6 (keys)


class Env(Protocol):
    def reset(self) -> np.ndarray:
        """Start an episode; return obs of shape (N_OBS,)."""

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, dict]:
        """Return (obs, reward, done, info). info has 'outcome' in
        {'win','loss','undecided'} and 'tick'. done=True at episode end."""
