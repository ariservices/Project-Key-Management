"""
Web Application for Key Management System.

Provides a responsive web interface for managing vehicle keys.
Features automatic synchronization with Autoflex10 API.
"""

import threading
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from autoflex_api_client import AutoflexAPIClient
from key_management_app import KeyManagementApp

app = Flask(__name__)

# Global app instance (initialized on first request)
key_app = None

# Auto-sync configuration
AUTO_SYNC_ENABLED = True
AUTO_SYNC_INTERVAL = 300  # 5 minutes in seconds (configurable)
last_sync_time = None
last_sync_result = None
sync_thread = None
sync_lock = threading.Lock()


def get_app():
    """Get or create the KeyManagementApp instance."""
    global key_app
    if key_app is None:
        key_app = KeyManagementApp(
            api_client=AutoflexAPIClient(
                api_key='276AB0BF-FC21-48B1-BF97-131D2B1FA3A1',
                username='88888-autobedrijfhelder-api',
                password='kIE9iiAVK15SGm'
            )
        )
    return key_app


def perform_sync():
    """Perform synchronization with Autoflex10."""
    global last_sync_time, last_sync_result

    with sync_lock:
        key_mgmt = get_app()

        # Authenticate first
        if not key_mgmt.authenticate():
            last_sync_result = {'success': False, 'error': 'Authentication failed'}
            return last_sync_result

        result = key_mgmt.sync_vehicles_from_autoflex()
        last_sync_time = datetime.now()
        last_sync_result = {
            'success': True,
            'timestamp': last_sync_time.isoformat(),
            **result
        }
        print(f"[Auto-Sync] {last_sync_time}: {result['added']} added, "
              f"{result['sold_detected']} sold detected, {result['skipped']} skipped")
        return last_sync_result


def auto_sync_worker():
    """Background worker for automatic synchronization."""
    while AUTO_SYNC_ENABLED:
        try:
            perform_sync()
        except Exception as e:
            print(f"[Auto-Sync] Error: {e}")

        # Wait for next sync interval
        time.sleep(AUTO_SYNC_INTERVAL)


def start_auto_sync():
    """Start the automatic sync background thread."""
    global sync_thread
    if sync_thread is None or not sync_thread.is_alive():
        sync_thread = threading.Thread(target=auto_sync_worker, daemon=True)
        sync_thread.start()
        print(f"[Auto-Sync] Started with interval of {AUTO_SYNC_INTERVAL} seconds")


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Get system status."""
    key_mgmt = get_app()
    return jsonify(key_mgmt.get_system_status())


@app.route('/api/sync', methods=['POST'])
def api_sync():
    """Manually trigger sync with Autoflex."""
    result = perform_sync()

    if not result.get('success'):
        return jsonify(result), 401

    return jsonify(result)


@app.route('/api/sync/status')
def api_sync_status():
    """Get auto-sync status and last sync info."""
    return jsonify({
        'auto_sync_enabled': AUTO_SYNC_ENABLED,
        'sync_interval_seconds': AUTO_SYNC_INTERVAL,
        'sync_interval_minutes': AUTO_SYNC_INTERVAL // 60,
        'last_sync_time': last_sync_time.isoformat() if last_sync_time else None,
        'last_sync_result': last_sync_result
    })


@app.route('/api/slots')
def api_slots():
    """Get all slot assignments."""
    key_mgmt = get_app()
    assignments = key_mgmt.slot_manager.get_all_assignments()

    slots = []
    for a in assignments:
        brand = ''
        model = ''
        color = ''
        if a.vehicle_data:
            brand = a.vehicle_data.get('brand', '')
            model = a.vehicle_data.get('model', '')
            color = a.vehicle_data.get('color', '')

        slots.append({
            'slot': a.slot_number,
            'license_plate': a.license_plate,
            'purchase_price': a.purchase_price,
            'brand': brand,
            'model': model,
            'color': color,
            'assigned_at': a.assigned_at.isoformat()
        })

    return jsonify(sorted(slots, key=lambda x: x['slot']))


@app.route('/api/sold')
def api_sold():
    """Get sold vehicles awaiting handover."""
    key_mgmt = get_app()
    sold = key_mgmt.get_sold_vehicles()

    vehicles = []
    for s in sold:
        brand = ''
        model = ''
        color = ''
        if s.vehicle_data:
            brand = s.vehicle_data.get('brand', '')
            model = s.vehicle_data.get('model', '')
            color = s.vehicle_data.get('color', '')

        vehicles.append({
            'sold_slot': s.sold_slot,
            'license_plate': s.license_plate,
            'purchase_price': s.purchase_price,
            'sold_price': s.sold_price,
            'original_slot': s.original_slot,
            'sold_at': s.sold_at.isoformat(),
            'brand': brand,
            'model': model,
            'color': color
        })

    return jsonify(vehicles)


@app.route('/api/search/<license_plate>')
def api_search(license_plate):
    """Search for a vehicle by license plate."""
    key_mgmt = get_app()
    result = key_mgmt.find_vehicle(license_plate)

    if result is None:
        return jsonify({'found': False})

    return jsonify({'found': True, **result})


@app.route('/api/vehicle', methods=['POST'])
def api_add_vehicle():
    """Add a vehicle manually."""
    data = request.json
    key_mgmt = get_app()

    license_plate = data.get('license_plate', '').strip().upper()
    purchase_price = float(data.get('purchase_price', 0))
    brand = data.get('brand', '')
    model = data.get('model', '')
    color = data.get('color', '')

    if not license_plate:
        return jsonify({'success': False, 'error': 'Kenteken is verplicht'}), 400

    slot = key_mgmt.add_vehicle_manually(
        license_plate=license_plate,
        purchase_price=purchase_price,
        brand=brand,
        model=model,
        color=color
    )

    if slot is not None:
        return jsonify({'success': True, 'slot': slot})
    else:
        return jsonify({
            'success': False,
            'error': 'Kon voertuig niet toevoegen (mogelijk duplicaat)'
        }), 400


@app.route('/api/sell', methods=['POST'])
def api_sell():
    """Mark a vehicle as sold."""
    data = request.json
    key_mgmt = get_app()

    license_plate = data.get('license_plate', '').strip()
    sold_price = data.get('sold_price')
    buyer_name = data.get('buyer_name', '')

    if sold_price:
        sold_price = float(sold_price)

    success = key_mgmt.sell_vehicle(
        license_plate=license_plate,
        sold_price=sold_price,
        buyer_name=buyer_name
    )

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({
            'success': False,
            'error': 'Kon voertuig niet verkopen'
        }), 400


@app.route('/api/handover', methods=['POST'])
def api_handover():
    """Complete vehicle handover."""
    data = request.json
    key_mgmt = get_app()

    license_plate = data.get('license_plate', '').strip()

    success = key_mgmt.complete_handover(license_plate)

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({
            'success': False,
            'error': 'Kon overdracht niet voltooien'
        }), 400


if __name__ == '__main__':
    # Start auto-sync in background
    start_auto_sync()

    # Run initial sync on startup
    print("[Startup] Running initial sync...")
    perform_sync()

    app.run(debug=True, host='0.0.0.0', port=5050, use_reloader=False)

