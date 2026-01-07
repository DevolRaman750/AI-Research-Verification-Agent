from abc import ABC, abstractmethod
from typing import Any, Dict


class Environment(ABC):
    """
    Base Environment Interface (TEA-compliant)
    """

    @abstractmethod
    def reset(self) -> None:
        """Reset environment state"""
        pass

    @abstractmethod
    def observe(self) -> Dict[str, Any]:
        """Return current environment state"""
        pass
