"""
Core functions for the simplified ZeroShotENGINE (SPIN version).
This version is fully local, using Ollama as the only model provider.
"""

__all__ = [
    "initialize_model",
    "set_zeroshot_parameters",
    "iterative_zeroshot_classification",
    "validate_combined_predictions",
    "display_label_flowchart",
]

from .base import initialize_model
from .izsc import (
    set_zeroshot_parameters,
    iterative_zeroshot_classification,
)
from .validate import validate_combined_predictions
from .visualization import display_label_flowchart
from .ollama import setup_ollama
