__version__ = "1.0.0"

# re-export for tests that import from src.automateddl
from .automateddl import AutomatedDL

__all__ = ["__version__", "AutomatedDL"]
