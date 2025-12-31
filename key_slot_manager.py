"""
Key Slot Manager Module.

This module manages the 200 key slots and their assignments to vehicles.
Includes support for sold vehicles and overflow slot assignment.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from slot_assignment_strategy import SlotAssignmentStrategy


@dataclass
class SlotAssignment:
    """
    Represents an assignment of a vehicle to a key slot.
    """

    slot_number: int
    vehicle_id: str
    license_plate: str
    purchase_price: float
    assigned_at: datetime
    vehicle_data: Optional[Dict[str, Any]] = None


@dataclass
class SoldVehicle:
    """
    Represents a sold vehicle awaiting key handover.
    """

    sold_slot: str  # v1 to v10
    vehicle_id: str
    license_plate: str
    purchase_price: float
    original_slot: int
    sold_at: datetime
    sold_price: Optional[float] = None
    buyer_info: Optional[Dict[str, Any]] = None


class KeySlotManager:
    """
    Manages 200 key slots and their assignments to vehicles.

    Features:
    - Price-based slot assignment with overflow to higher slots
    - 10 slots for sold vehicles awaiting handover
    - Duplicate prevention using license plate as primary key
    - Manual vehicle assignment support
    """

    SOLD_VEHICLE_SLOTS = 10  # Number of slots for sold vehicles

    def __init__(
        self,
        total_slots: int = 200,
        assignment_strategy: Optional[SlotAssignmentStrategy] = None
    ):
        """
        Initialize the key slot manager.

        Args:
            total_slots: Total number of slots available (default: 200)
            assignment_strategy: Strategy for determining slot ranges
        """
        self.total_slots = total_slots
        self.assignment_strategy = assignment_strategy

        # Main inventory slots (0 to total_slots-1)
        self.slots: Dict[int, Optional[SlotAssignment]] = {
            slot: None for slot in range(total_slots)
        }

        # Sold vehicles slots (separate from main inventory)
        self.sold_vehicles: List[Optional[SoldVehicle]] = [
            None for _ in range(self.SOLD_VEHICLE_SLOTS)
        ]

        # Index for quick license plate lookup
        self._license_plate_index: Dict[str, int] = {}

    def _normalize_license_plate(self, license_plate: str) -> str:
        """
        Normalize license plate for consistent comparison.

        Args:
            license_plate: The license plate to normalize

        Returns:
            Normalized license plate (uppercase, no spaces)
        """
        return license_plate.upper().replace(" ", "").replace("-", "")

    def is_duplicate_license_plate(self, license_plate: str) -> bool:
        """
        Check if a license plate already exists in the system.

        Args:
            license_plate: The license plate to check

        Returns:
            True if duplicate exists, False otherwise
        """
        normalized = self._normalize_license_plate(license_plate)

        # Check in main slots
        for assignment in self.slots.values():
            if assignment is not None:
                if self._normalize_license_plate(
                    assignment.license_plate
                ) == normalized:
                    return True

        # Check in sold vehicles
        for sold in self.sold_vehicles:
            if sold is not None:
                if self._normalize_license_plate(
                    sold.license_plate
                ) == normalized:
                    return True

        return False

    def is_slot_available(self, slot_number: int) -> bool:
        """
        Check if a specific slot is available.

        Args:
            slot_number: The slot number to check

        Returns:
            True if slot is available, False otherwise
        """
        if not 0 <= slot_number < self.total_slots:
            return False

        return self.slots[slot_number] is None

    def get_available_slot_in_range(
        self,
        min_slot: int,
        max_slot: int
    ) -> Optional[int]:
        """
        Find the first available slot within a given range.

        Args:
            min_slot: Minimum slot number (inclusive)
            max_slot: Maximum slot number (inclusive)

        Returns:
            Available slot number or None if no slot is available
        """
        for slot in range(min_slot, min(max_slot + 1, self.total_slots)):
            if self.is_slot_available(slot):
                return slot

        return None

    def get_highest_available_slot(self) -> Optional[int]:
        """
        Find the highest available slot number.

        Returns:
            Highest available slot number or None if all slots are full
        """
        for slot in range(self.total_slots - 1, -1, -1):
            if self.is_slot_available(slot):
                return slot
        return None

    def assign_vehicle_to_slot(
        self,
        slot_number: int,
        vehicle_id: str,
        license_plate: str,
        purchase_price: float,
        vehicle_data: Optional[Dict[str, Any]] = None,
        check_duplicate: bool = True
    ) -> bool:
        """
        Assign a vehicle to a specific slot.

        Args:
            slot_number: The slot number to assign
            vehicle_id: The vehicle identifier
            license_plate: The license plate number
            purchase_price: The purchase price of the vehicle
            vehicle_data: Optional additional vehicle data
            check_duplicate: Whether to check for duplicate license plates

        Returns:
            True if assignment successful, False otherwise
        """
        if not self.is_slot_available(slot_number):
            return False

        # Check for duplicate license plate
        if check_duplicate and self.is_duplicate_license_plate(license_plate):
            return False

        assignment = SlotAssignment(
            slot_number=slot_number,
            vehicle_id=vehicle_id,
            license_plate=license_plate,
            purchase_price=purchase_price,
            assigned_at=datetime.now(),
            vehicle_data=vehicle_data
        )

        self.slots[slot_number] = assignment
        return True

    def assign_vehicle(
        self,
        vehicle_id: str,
        license_plate: str,
        purchase_price: float,
        vehicle_data: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Assign a vehicle to an available slot based on the assignment strategy.
        If preferred range is full, assigns to highest available slot.

        Args:
            vehicle_id: The vehicle identifier
            license_plate: The license plate number
            purchase_price: The purchase price of the vehicle
            vehicle_data: Optional additional vehicle data

        Returns:
            Assigned slot number or None if no slot available or duplicate
        """
        # Check for duplicate license plate first
        if self.is_duplicate_license_plate(license_plate):
            return None

        if self.assignment_strategy is None:
            # Fallback: assign to first available slot
            for slot in range(self.total_slots):
                if self.is_slot_available(slot):
                    if self.assign_vehicle_to_slot(
                        slot, vehicle_id, license_plate,
                        purchase_price, vehicle_data, check_duplicate=False
                    ):
                        return slot
            return None

        # Try to assign in preferred range based on price
        min_slot, max_slot = self.assignment_strategy.get_slot_range(
            purchase_price
        )
        available_slot = self.get_available_slot_in_range(min_slot, max_slot)

        if available_slot is not None:
            if self.assign_vehicle_to_slot(
                available_slot, vehicle_id, license_plate,
                purchase_price, vehicle_data, check_duplicate=False
            ):
                return available_slot

        # Overflow: if preferred range is full, find highest available slot
        highest_slot = self.get_highest_available_slot()
        if highest_slot is not None:
            if self.assign_vehicle_to_slot(
                highest_slot, vehicle_id, license_plate,
                purchase_price, vehicle_data, check_duplicate=False
            ):
                return highest_slot

        return None

    def add_vehicle_manually(
        self,
        license_plate: str,
        purchase_price: float,
        vehicle_id: Optional[str] = None,
        preferred_slot: Optional[int] = None,
        vehicle_data: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Manually add a vehicle to the system.

        Args:
            license_plate: The license plate number (primary key)
            purchase_price: The purchase price of the vehicle
            vehicle_id: Optional vehicle ID (auto-generated if not provided)
            preferred_slot: Optional preferred slot number
            vehicle_data: Optional additional vehicle data

        Returns:
            Assigned slot number or None if failed (duplicate or no space)
        """
        # Check for duplicate
        if self.is_duplicate_license_plate(license_plate):
            print(f"Error: Vehicle with plate {license_plate} already exists")
            return None

        # Generate vehicle ID if not provided
        if vehicle_id is None:
            vehicle_id = f"MANUAL-{license_plate}"

        # If preferred slot is specified, try that first
        if preferred_slot is not None:
            if self.is_slot_available(preferred_slot):
                if self.assign_vehicle_to_slot(
                    preferred_slot, vehicle_id, license_plate,
                    purchase_price, vehicle_data, check_duplicate=False
                ):
                    return preferred_slot
            else:
                print(
                    f"Warning: Preferred slot {preferred_slot} not available, "
                    "assigning automatically"
                )

        # Auto-assign based on strategy
        return self.assign_vehicle(
            vehicle_id, license_plate, purchase_price, vehicle_data
        )

    def mark_vehicle_as_sold(
        self,
        license_plate: str,
        sold_price: Optional[float] = None,
        buyer_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Mark a vehicle as sold and move it to sold vehicle slots.

        Args:
            license_plate: The license plate of the sold vehicle
            sold_price: Optional sale price
            buyer_info: Optional buyer information

        Returns:
            True if successful, False otherwise
        """
        # Find the vehicle in main slots
        assignment = self.get_vehicle_by_license_plate(license_plate)

        if assignment is None:
            print(f"Error: Vehicle with plate {license_plate} not found")
            return False

        # Find available sold vehicle slot
        sold_slot_index = None
        for idx, sold in enumerate(self.sold_vehicles):
            if sold is None:
                sold_slot_index = idx
                break

        if sold_slot_index is None:
            print(
                "Error: No available slots for sold vehicles. "
                "Please complete pending handovers."
            )
            return False

        # Create sold vehicle record with slot name v1-v10
        sold_slot_name = f"v{sold_slot_index + 1}"
        sold_vehicle = SoldVehicle(
            sold_slot=sold_slot_name,
            vehicle_id=assignment.vehicle_id,
            license_plate=assignment.license_plate,
            purchase_price=assignment.purchase_price,
            original_slot=assignment.slot_number,
            sold_at=datetime.now(),
            sold_price=sold_price,
            buyer_info=buyer_info
        )

        # Move to sold vehicles
        self.sold_vehicles[sold_slot_index] = sold_vehicle

        # Release the original slot
        self.slots[assignment.slot_number] = None

        print(
            f"Vehicle {license_plate} marked as sold. "
            f"Key moved from slot {assignment.slot_number} to sold slot {sold_slot_name}."
        )
        return True

    def complete_vehicle_handover(self, license_plate: str) -> bool:
        """
        Complete the handover of a sold vehicle (key given to buyer).

        Args:
            license_plate: The license plate of the vehicle

        Returns:
            True if successful, False otherwise
        """
        normalized = self._normalize_license_plate(license_plate)

        for idx, sold in enumerate(self.sold_vehicles):
            if sold is not None:
                if self._normalize_license_plate(
                    sold.license_plate
                ) == normalized:
                    self.sold_vehicles[idx] = None
                    print(
                        f"Handover completed for {license_plate}. "
                        "Key removed from system."
                    )
                    return True

        print(f"Error: Vehicle {license_plate} not found in sold vehicles")
        return False

    def get_sold_vehicles(self) -> List[SoldVehicle]:
        """
        Get list of all sold vehicles awaiting handover.

        Returns:
            List of SoldVehicle objects
        """
        return [v for v in self.sold_vehicles if v is not None]

    def release_slot(self, slot_number: int) -> bool:
        """
        Release a slot, making it available for new assignments.

        Args:
            slot_number: The slot number to release

        Returns:
            True if slot was released, False otherwise
        """
        if not 0 <= slot_number < self.total_slots:
            return False

        if self.slots[slot_number] is None:
            return False

        self.slots[slot_number] = None
        return True

    def release_by_license_plate(self, license_plate: str) -> bool:
        """
        Release a slot by license plate.

        Args:
            license_plate: The license plate of the vehicle to release

        Returns:
            True if released, False otherwise
        """
        assignment = self.get_vehicle_by_license_plate(license_plate)
        if assignment is None:
            return False

        return self.release_slot(assignment.slot_number)

    def get_slot_assignment(self, slot_number: int) -> Optional[SlotAssignment]:
        """
        Get the assignment for a specific slot.

        Args:
            slot_number: The slot number

        Returns:
            SlotAssignment object or None if slot is empty
        """
        if not 0 <= slot_number < self.total_slots:
            return None

        return self.slots[slot_number]

    def get_vehicle_by_license_plate(
        self,
        license_plate: str
    ) -> Optional[SlotAssignment]:
        """
        Find a vehicle assignment by license plate.

        Args:
            license_plate: The license plate to search for

        Returns:
            SlotAssignment object or None if not found
        """
        normalized = self._normalize_license_plate(license_plate)

        for assignment in self.slots.values():
            if assignment is not None:
                if self._normalize_license_plate(
                    assignment.license_plate
                ) == normalized:
                    return assignment

        return None

    def get_available_slots_count(self) -> int:
        """
        Get the count of available slots.

        Returns:
            Number of available slots
        """
        return sum(1 for assignment in self.slots.values() if assignment is None)

    def get_occupied_slots_count(self) -> int:
        """
        Get the count of occupied slots.

        Returns:
            Number of occupied slots
        """
        return self.total_slots - self.get_available_slots_count()

    def get_sold_vehicles_count(self) -> int:
        """
        Get count of sold vehicles awaiting handover.

        Returns:
            Number of sold vehicles
        """
        return sum(1 for v in self.sold_vehicles if v is not None)

    def get_all_assignments(self) -> List[SlotAssignment]:
        """
        Get all current slot assignments.

        Returns:
            List of SlotAssignment objects
        """
        return [a for a in self.slots.values() if a is not None]
