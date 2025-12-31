# 🔑 Sleutelbeheer Systeem

Automatisch sleutelbeheer systeem voor autobedrijven, geïntegreerd met Autoflex10 API.

## Features

- **200 slots** voor sleutels, ingedeeld op aankoopprijs
- **Automatische synchronisatie** met Autoflex10
- **10 verkocht-slots** (v1-v10) voor auto's die wachten op overdracht
- **Responsive web interface** - werkt op telefoon en desktop
- **Duplicate preventie** - kenteken als primary key

## Slot Indeling

| Categorie | Slots | Aankoopprijs |
|-----------|-------|--------------|
| Premium | 0-49 | > €3000 |
| Midden | 50-99 | €1500 - €3000 |
| Budget | 100-199 | < €1500 |
| Verkocht | v1-v10 | Wachtend op overdracht |

## Installatie

```bash
# Installeer dependencies
pip3 install -r requirements.txt

# Start de web applicatie
python3 web_app.py
```

Open vervolgens http://localhost:5000 in je browser.

## Project Structuur

```
Project Key Management/
├── web_app.py              # Flask web server
├── templates/
│   └── index.html          # Responsive UI
├── autoflex_api_client.py  # Autoflex10 API client
├── key_management_app.py   # Hoofdapplicatie logica
├── key_slot_manager.py     # Slot beheer
├── slot_assignment_strategy.py  # Prijs-gebaseerde toewijzing
├── main.py                 # CLI interface
├── requirements.txt        # Python dependencies
└── README.md
```

## Gebruik

### Web Interface

1. Start de server: `python3 web_app.py`
2. Open http://localhost:5000
3. Gebruik de tabs om te navigeren:
   - **Slots** - Bekijk alle toegewezen sleutels
   - **Verkocht** - Beheer verkochte auto's
   - **Toevoegen** - Handmatig auto toevoegen
   - **Sync** - Synchroniseer met Autoflex10

### CLI Interface

```bash
python3 main.py
```

### Python API

```python
from key_management_app import KeyManagementApp

app = KeyManagementApp()

# Handmatig toevoegen
app.add_vehicle_manually('XX-123-YY', 5000.0)

# Zoeken
app.find_vehicle('XX-123-YY')

# Verkopen
app.sell_vehicle('XX-123-YY', sold_price=6500.0)

# Overdracht voltooien
app.complete_handover('XX-123-YY')
```

## API Endpoints

| Method | Endpoint | Beschrijving |
|--------|----------|--------------|
| GET | `/api/status` | Systeem status |
| GET | `/api/slots` | Alle slot toewijzingen |
| GET | `/api/sold` | Verkochte voertuigen |
| GET | `/api/search/<kenteken>` | Zoek voertuig |
| POST | `/api/vehicle` | Voeg voertuig toe |
| POST | `/api/sell` | Markeer als verkocht |
| POST | `/api/handover` | Voltooien overdracht |
| POST | `/api/sync` | Sync met Autoflex10 |

## Configuratie

Autoflex10 credentials kunnen worden ingesteld via environment variables:

```bash
export AUTOFLEX_API_KEY="your-api-key"
export AUTOFLEX_USERNAME="your-username"
export AUTOFLEX_PASSWORD="your-password"
```

Of maak een `.env` bestand in de project root.
