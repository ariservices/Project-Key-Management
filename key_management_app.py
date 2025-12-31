"""
Key Management Application Module.

This module provides the main application class that orchestrates
the integration between Autoflex10 API and the key slot management system.
"""

from typing import Optional, Dict, Any, List
from autoflex_api_client import AutoflexAPIClient
from key_slot_manager import KeySlotManager, SlotAssignment, SoldVehicle
from slot_assignment_strategy import PriceBasedSlotStrategy


class KeyManagementApp:
    """
    Main application class for automated key management system.

    Integrates Autoflex10 API with the key slot management system
    to automatically assign vehicles to slots based on purchase price.

    Features:
    - Automatic slot assignment based on price tiers
    - Overflow to highest available slot when tier is full
    - Manual vehicle addition with duplicate prevention
    - Sold vehicle tracking with 10 dedicated slots
    """

    def __init__(
        self,
        api_client: Optional[AutoflexAPIClient] = None,
        slot_manager: Optional[KeySlotManager] = None,
        assignment_strategy: Optional[PriceBasedSlotStrategy] = None
    ):
        """
        Initialize the key management application.

        Args:
            api_client: Autoflex10 API client instance
            slot_manager: Key slot manager instance
            assignment_strategy: Strategy for slot assignment
        """
        self.api_client = api_client or AutoflexAPIClient()
        self.assignment_strategy = (
            assignment_strategy or
            PriceBasedSlotStrategy()
        )
        self.slot_manager = (
            slot_manager or
            KeySlotManager(assignment_strategy=self.assignment_strategy)
        )

    def authenticate(self) -> bool:
        """
        Authenticate with the Autoflex10 API.

        Returns:
            True if authentication successful, False otherwise
        """
        return self.api_client.authenticate()

    def process_new_vehicle(
        self,
        vehicle_id: str,
        license_plate: str,
        purchase_price: float,
        vehicle_data: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Process a newly added vehicle and assign it to an available slot.

        Args:
            vehicle_id: The vehicle identifier
            license_plate: The license plate number
            purchase_price: The purchase price of the vehicle
            vehicle_data: Optional additional vehicle data

        Returns:
            Assigned slot number or None if assignment failed
        """
        # Check if vehicle is already assigned (duplicate prevention)
        existing_assignment = self.slot_manager.get_vehicle_by_license_plate(
            license_plate
        )

        if existing_assignment is not None:
            return existing_assignment.slot_number

        # Assign vehicle to slot (with overflow support)
        assigned_slot = self.slot_manager.assign_vehicle(
            vehicle_id=vehicle_id,
            license_plate=license_plate,
            purchase_price=purchase_price,
            vehicle_data=vehicle_data
        )

        if assigned_slot is not None:
            print(
                f"Vehicle {license_plate} assigned to slot {assigned_slot} "
                f"(Price: €{purchase_price:,.2f})"
            )
        else:
            print(
                f"Failed to assign vehicle {license_plate}: "
                "No available slots"
            )

        return assigned_slot

    def add_vehicle_manually(
        self,
        license_plate: str,
        purchase_price: float,
        vehicle_id: Optional[str] = None,
        preferred_slot: Optional[int] = None,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        color: Optional[str] = None
    ) -> Optional[int]:
        """
        Manually add a vehicle to the system.

        Args:
            license_plate: The license plate number (primary key)
            purchase_price: The purchase price of the vehicle
            vehicle_id: Optional vehicle ID
            preferred_slot: Optional preferred slot number
            brand: Optional vehicle brand
            model: Optional vehicle model
            color: Optional vehicle color

        Returns:
            Assigned slot number or None if failed
        """
        vehicle_data = {}
        if brand:
            vehicle_data['brand'] = brand
        if model:
            vehicle_data['model'] = model
        if color:
            vehicle_data['color'] = color

        slot = self.slot_manager.add_vehicle_manually(
            license_plate=license_plate,
            purchase_price=purchase_price,
            vehicle_id=vehicle_id,
            preferred_slot=preferred_slot,
            vehicle_data=vehicle_data if vehicle_data else None
        )

        if slot is not None:
            print(
                f"✓ Vehicle {license_plate} manually added to slot {slot} "
                f"(Price: €{purchase_price:,.2f})"
            )
        else:
            print(f"✗ Failed to add vehicle {license_plate}")

        return slot

    def sell_vehicle(
        self,
        license_plate: str,
        sold_price: Optional[float] = None,
        buyer_name: Optional[str] = None
    ) -> bool:
        """
        Mark a vehicle as sold and move key to sold vehicles area.

        Args:
            license_plate: The license plate of the sold vehicle
            sold_price: Optional sale price
            buyer_name: Optional buyer name

        Returns:
            True if successful, False otherwise
        """
        buyer_info = None
        if buyer_name:
            buyer_info = {'name': buyer_name}

        return self.slot_manager.mark_vehicle_as_sold(
            license_plate=license_plate,
            sold_price=sold_price,
            buyer_info=buyer_info
        )

    def complete_handover(self, license_plate: str) -> bool:
        """
        Complete the handover of a sold vehicle.
        Key is removed from the system.

        Args:
            license_plate: The license plate of the vehicle

        Returns:
            True if successful, False otherwise
        """
        return self.slot_manager.complete_vehicle_handover(license_plate)

    def get_sold_vehicles(self) -> List[SoldVehicle]:
        """
        Get list of sold vehicles awaiting handover.

        Returns:
            List of SoldVehicle objects
        """
        return self.slot_manager.get_sold_vehicles()

    def find_vehicle(self, license_plate: str) -> Optional[Dict[str, Any]]:
        """
        Find a vehicle by license plate.

        Args:
            license_plate: The license plate to search for

        Returns:
            Dictionary with vehicle info or None if not found
        """
        # Check in main slots
        assignment = self.slot_manager.get_vehicle_by_license_plate(license_plate)
        if assignment is not None:
            return {
                'status': 'in_stock',
                'slot_number': assignment.slot_number,
                'license_plate': assignment.license_plate,
                'purchase_price': assignment.purchase_price,
                'assigned_at': assignment.assigned_at.isoformat(),
                'vehicle_data': assignment.vehicle_data
            }

        # Check in sold vehicles
        for sold in self.slot_manager.sold_vehicles:
            if sold is not None:
                normalized_search = license_plate.upper().replace(" ", "").replace("-", "")
                normalized_plate = sold.license_plate.upper().replace(" ", "").replace("-", "")
                if normalized_search == normalized_plate:
                    return {
                        'status': 'sold',
                        'sold_slot': sold.sold_slot,
                        'original_slot': sold.original_slot,
                        'license_plate': sold.license_plate,
                        'purchase_price': sold.purchase_price,
                        'sold_at': sold.sold_at.isoformat(),
                        'sold_price': sold.sold_price
                    }

        return None

    def sync_vehicles_from_autoflex(self) -> Dict[str, Any]:
        """
        Synchronize vehicles from Autoflex10 and assign them to slots.
        Automatically detects sold vehicles and moves them to sold slots.

        Returns:
            Dictionary with sync results including added, sold, and skipped counts
        """
        # Get all vehicles with pagination
        vehicles = self.api_client.get_all_vehicles()

        if not vehicles:
            print("No vehicles found or failed to retrieve from Autoflex10")
            return {
                'total': 0,
                'added': 0,
                'sold_detected': 0,
                'skipped': 0,
                'results': []
            }

        print(f"Found {len(vehicles)} vehicles in Autoflex10")
        results = []
        added_count = 0
        sold_detected_count = 0
        skipped_count = 0

        for vehicle in vehicles:
            vehicle_id = vehicle.get('vehicle_id')
            license_plate = vehicle.get('license_plate')
            purchase_price = vehicle.get('purchase_price')
            is_sold = vehicle.get('is_sold', 0)

            if not vehicle_id or not license_plate:
                continue

            # Handle None or invalid purchase_price
            if purchase_price is None:
                purchase_price = 0.0
            else:
                try:
                    purchase_price = float(purchase_price)
                except (ValueError, TypeError):
                    purchase_price = 0.0

            # Check if vehicle is marked as sold in Autoflex
            try:
                is_sold = int(is_sold) == 1
            except (ValueError, TypeError):
                is_sold = False

            # Check if vehicle already exists in system
            existing = self.slot_manager.get_vehicle_by_license_plate(license_plate)

            if is_sold:
                # Vehicle is sold in Autoflex
                if existing is not None:
                    # Move to sold slots if not already there
                    success = self.slot_manager.mark_vehicle_as_sold(
                        license_plate=license_plate
                    )
                    if success:
                        sold_detected_count += 1
                        results.append({
                            'vehicle_id': vehicle_id,
                            'license_plate': license_plate,
                            'action': 'sold_detected',
                            'success': True
                        })
                    else:
                        results.append({
                            'vehicle_id': vehicle_id,
                            'license_plate': license_plate,
                            'action': 'sold_failed',
                            'success': False
                        })
                else:
                    # Already sold and not in system, skip
                    skipped_count += 1
                continue

            # Vehicle not sold - assign to slot if not already assigned
            if existing is not None:
                skipped_count += 1
                continue

            assigned_slot = self.process_new_vehicle(
                vehicle_id=vehicle_id,
                license_plate=license_plate,
                purchase_price=purchase_price,
                vehicle_data=vehicle
            )

            if assigned_slot is not None:
                added_count += 1
                results.append({
                    'vehicle_id': vehicle_id,
                    'license_plate': license_plate,
                    'action': 'added',
                    'slot': assigned_slot,
                    'success': True
                })
            else:
                results.append({
                    'vehicle_id': vehicle_id,
                    'license_plate': license_plate,
                    'action': 'add_failed',
                    'success': False
                })

        return {
            'total': len(vehicles),
            'added': added_count,
            'sold_detected': sold_detected_count,
            'skipped': skipped_count,
            'results': results
        }

    def get_slot_status(self, slot_number: int) -> Optional[Dict[str, Any]]:
        """
        Get the status of a specific slot.

        Args:
            slot_number: The slot number to query

        Returns:
            Dictionary with slot status information or None
        """
        assignment = self.slot_manager.get_slot_assignment(slot_number)

        if assignment is None:
            return {
                'slot_number': slot_number,
                'status': 'available',
                'vehicle_id': None,
                'license_plate': None
            }

        return {
            'slot_number': slot_number,
            'status': 'occupied',
            'vehicle_id': assignment.vehicle_id,
            'license_plate': assignment.license_plate,
            'purchase_price': assignment.purchase_price,
            'assigned_at': assignment.assigned_at.isoformat()
        }

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get overall system status.

        Returns:
            Dictionary with system status information
        """
        return {
            'total_slots': self.slot_manager.total_slots,
            'available_slots': self.slot_manager.get_available_slots_count(),
            'occupied_slots': self.slot_manager.get_occupied_slots_count(),
            'sold_vehicles_pending': self.slot_manager.get_sold_vehicles_count(),
            'sold_vehicle_slots_available': (
                self.slot_manager.SOLD_VEHICLE_SLOTS -
                self.slot_manager.get_sold_vehicles_count()
            ),
            'is_authenticated': self.api_client.token is not None
        }

    def print_slot_overview(self) -> None:
        """
        Print a formatted overview of all slot assignments.
        """
        assignments = self.slot_manager.get_all_assignments()
        sold = self.slot_manager.get_sold_vehicles()

        # Group by slot range
        high_price = []
        medium_price = []
        low_price = []

        for a in assignments:
            if a.slot_number < 50:
                high_price.append(a)
            elif a.slot_number < 100:
                medium_price.append(a)
            else:
                low_price.append(a)

        print("\n" + "=" * 80)
        print("OVERZICHT SLOT TOEWIJZINGEN")
        print("=" * 80)

        print(f"\n📦 SLOTS 0-49 (Premium > €3000): {len(high_price)} voertuigen")
        print("-" * 80)
        for a in sorted(high_price, key=lambda x: x.slot_number):
            print(
                f"  Slot {a.slot_number:3d} | {a.license_plate:12s} | "
                f"€{a.purchase_price:,.2f}"
            )

        print(f"\n📦 SLOTS 50-99 (Midden €1500-3000): {len(medium_price)} voertuigen")
        print("-" * 80)
        for a in sorted(medium_price, key=lambda x: x.slot_number):
            print(
                f"  Slot {a.slot_number:3d} | {a.license_plate:12s} | "
                f"€{a.purchase_price:,.2f}"
            )

        print(f"\n📦 SLOTS 100-199 (Budget < €1500): {len(low_price)} voertuigen")
        print("-" * 80)
        for a in sorted(low_price, key=lambda x: x.slot_number):
            print(
                f"  Slot {a.slot_number:3d} | {a.license_plate:12s} | "
                f"€{a.purchase_price:,.2f}"
            )

        if sold:
            print(f"\n🚗 VERKOCHT (wachtend op overdracht): {len(sold)} voertuigen")
            print("-" * 80)
            for s in sold:
                sold_price_str = (
                    f"€{s.sold_price:,.2f}" if s.sold_price else "N/A"
                )
                print(
                    f"  Slot {s.sold_slot:3s} | {s.license_plate:12s} | "
                    f"Verkocht: {sold_price_str} | Was slot: {s.original_slot}"
                )

        print("\n" + "=" * 80)
        status = self.get_system_status()
        print(f"TOTAAL: {status['occupied_slots']} bezet / {status['total_slots']} slots")
        print(f"BESCHIKBAAR: {status['available_slots']} slots")
        print(f"VERKOCHT (wachtend): {status['sold_vehicles_pending']} / 10 slots")
        print("=" * 80)
