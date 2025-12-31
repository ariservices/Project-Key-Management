"""
Slot Assignment Strategy Module.

This module defines the strategy for assigning cars to key slots
based on purchase price criteria.
"""

from typing import Optional, Tuple
from abc import ABC, abstractmethod


class SlotAssignmentStrategy(ABC):
    """
    Abstract base class for slot assignment strategies.
    """

    @abstractmethod
    def get_slot_range(self, purchase_price: float) -> Tuple[int, int]:
        """
        Determine the slot range for a given purchase price.

        Args:
            purchase_price: The purchase price of the car

        Returns:
            Tuple of (min_slot, max_slot) inclusive
        """
        pass


class PriceBasedSlotStrategy(SlotAssignmentStrategy):
    """
    Strategy for assigning slots based on purchase price tiers.

    Slots are divided into tiers:
    - Slots 0-50: Cars purchased above €3000
    - Slots 50-100: Cars purchased above €1500 (but <= €3000)
    - Slots 100-199: Cars purchased below €1500
    """

    def __init__(
        self,
        high_price_threshold: float = 3000.0,
        medium_price_threshold: float = 1500.0,
        high_price_slots: Tuple[int, int] = (0, 50),
        medium_price_slots: Tuple[int, int] = (50, 100),
        low_price_slots: Tuple[int, int] = (100, 199)
    ):
        """
        Initialize the price-based slot assignment strategy.

        Args:
            high_price_threshold: Minimum price for high-tier slots (default: €3000)
            medium_price_threshold: Minimum price for medium-tier slots (default: €1500)
            high_price_slots: Slot range for high-price cars (default: 0-50)
            medium_price_slots: Slot range for medium-price cars (default: 50-100)
            low_price_slots: Slot range for low-price cars (default: 100-199)
        """
        self.high_price_threshold = high_price_threshold
        self.medium_price_threshold = medium_price_threshold
        self.high_price_slots = high_price_slots
        self.medium_price_slots = medium_price_slots
        self.low_price_slots = low_price_slots

    def get_slot_range(self, purchase_price: float) -> Tuple[int, int]:
        """
        Determine the slot range for a given purchase price.

        Args:
            purchase_price: The purchase price of the car

        Returns:
            Tuple of (min_slot, max_slot) inclusive
        """
        if purchase_price >= self.high_price_threshold:
            return self.high_price_slots

        if purchase_price >= self.medium_price_threshold:
            return self.medium_price_slots

        return self.low_price_slots

