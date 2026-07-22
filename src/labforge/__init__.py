"""
labforge: wrap plain Python functions into a small scientific desktop app,
following the theory -> simulation -> visualization -> analysis workflow.

Lab collects the registrations and launches the app; Param specifies a kwarg's
control; ScanResult is what a parameter scan hands to viz and analysis
functions; style is the optional house figure treatment; palette exposes the
active theme's colours; themes lists what open(theme=...) accepts.
"""

from .figures import palette, style
from .lab import Lab
from .param import Param
from .scan import ScanResult
from .theme import names as themes

__all__ = ["Lab", "Param", "ScanResult", "style", "palette", "themes"]
