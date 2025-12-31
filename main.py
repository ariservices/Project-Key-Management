"""
Main Entry Point for Key Management Application.

This script provides a command-line interface for the key management system.
"""

import sys
from key_management_app import KeyManagementApp


def main():
    """
    Main entry point for the application.
    """
    app = KeyManagementApp()

    # Authenticate with Autoflex10 API
    print("Authenticating with Autoflex10 API...")
    if not app.authenticate():
        print("ERROR: Authentication failed. Please check your credentials.")
        sys.exit(1)

    print("Authentication successful!")

    # Display system status
    status = app.get_system_status()
    print(f"\nSystem Status:")
    print(f"  Total Slots: {status['total_slots']}")
    print(f"  Available Slots: {status['available_slots']}")
    print(f"  Occupied Slots: {status['occupied_slots']}")

    # Sync vehicles from Autoflex10
    print("\nSyncing vehicles from Autoflex10...")
    results = app.sync_vehicles_from_autoflex()

    if results:
        successful = sum(1 for r in results if r['success'])
        print(f"\nSync Results: {successful}/{len(results)} vehicles assigned")
    else:
        print("No vehicles found or sync failed.")

    # Example: Process a new vehicle manually
    # Uncomment and modify as needed:
    # app.process_new_vehicle(
    #     vehicle_id="example-123",
    #     license_plate="ABC-123",
    #     purchase_price=2500.0
    # )


if __name__ == "__main__":
    main()


