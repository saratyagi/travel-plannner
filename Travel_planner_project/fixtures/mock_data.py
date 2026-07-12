"""Realistic mock responses for all external API calls. Active when USE_MOCK_DATA env var is set."""

import json
import re

# ── Destination detection ─────────────────────────────────────────────────────

_CITY_KEYWORDS: dict[str, list[str]] = {
    "paris":  ["paris", "france", "cdg", "charles de gaulle"],
    "tokyo":  ["tokyo", "japan", "nrt", "narita", "haneda"],
    "bali":   ["bali", "indonesia", "denpasar", "dps", "ubud", "seminyak"],
    "dubai":  ["dubai", "uae", "dxb"],
    "london": ["london", "heathrow", "lhr", "gatwick", "lgw"],
}


def get_mock_destination(text: str) -> str:
    t = text.lower()
    for dest, keywords in _CITY_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return dest
    return "paris"


# ── Trip params (for extract_trip_params) ─────────────────────────────────────

_MOCK_PARAMS: dict[str, dict] = {
    "paris": {
        "origin": "New Delhi", "destination": "Paris",
        "start_date": "2026-08-10", "end_date": "2026-08-17",
        "trip_length_days": 7, "travelers": 2,
        "cabin_class": "economy", "hotel_pref": "any", "budget_ceiling_usd": None,
    },
    "tokyo": {
        "origin": "London", "destination": "Tokyo",
        "start_date": "2026-09-05", "end_date": "2026-09-15",
        "trip_length_days": 10, "travelers": 1,
        "cabin_class": "economy", "hotel_pref": "mid", "budget_ceiling_usd": None,
    },
    "bali": {
        "origin": "Sydney", "destination": "Bali",
        "start_date": "2026-07-20", "end_date": "2026-07-27",
        "trip_length_days": 7, "travelers": 2,
        "cabin_class": "economy", "hotel_pref": "any", "budget_ceiling_usd": 3000,
    },
    "dubai": {
        "origin": "Mumbai", "destination": "Dubai",
        "start_date": "2026-10-01", "end_date": "2026-10-06",
        "trip_length_days": 5, "travelers": 2,
        "cabin_class": "economy", "hotel_pref": "luxury", "budget_ceiling_usd": None,
    },
    "london": {
        "origin": "New York", "destination": "London",
        "start_date": "2026-11-10", "end_date": "2026-11-17",
        "trip_length_days": 7, "travelers": 1,
        "cabin_class": "premium_economy", "hotel_pref": "mid", "budget_ceiling_usd": None,
    },
}

MOCK_HARD_QUESTION = (
    "Where will you be flying from, and what dates are you thinking? "
    "Even a rough idea like 'mid-August for a week from Mumbai' works great!"
)

MOCK_SOFT_QUESTION = (
    "How many people will be travelling? "
    "I can proceed assuming solo travel if you prefer — just say 'skip' and I'll get started."
)


def get_mock_trip_params(text: str) -> str:
    """Parse the user's actual text and only fill in fields that are explicitly mentioned.
    Unmentioned fields are left null so validate_fields() triggers clarification questions."""
    dest = get_mock_destination(text)
    scenario = _MOCK_PARAMS[dest]

    params: dict = {
        "origin": None,
        "destination": scenario["destination"],
        "start_date": None,
        "end_date": None,
        "trip_length_days": None,
        "travelers": None,
        "cabin_class": "economy",
        "hotel_pref": "any",
        "budget_ceiling_usd": None,
    }

    t = text.lower()

    # Origin — look for "from [City]" pattern (case-insensitive)
    m = re.search(
        r'\bfrom\s+([A-Za-z][A-Za-z\s]{1,25}?)(?=\s+to\b|\s+for\b|\s*,|\s*$)',
        text,
        re.IGNORECASE,
    )
    if m:
        params["origin"] = m.group(1).strip().title()

    # Travelers — explicit number + person keyword
    m = re.search(
        r'(\d+)\s*(?:people|persons?|travelers?|travellers?|adults?|passengers?|pax|guests?)',
        t,
    )
    if m:
        params["travelers"] = int(m.group(1))
    elif re.search(r'\bsolo\b|\balone\b|\bjust\s*me\b|\bmyself\b|\bone\s+person\b', t):
        params["travelers"] = 1
    elif re.search(r'\bcouple\b|\btwo\s+of\s+us\b', t):
        params["travelers"] = 2

    # Trip length — "N days" or "N nights" or "N weeks"
    m = re.search(r'(\d+)\s*(?:days?|nights?)', t)
    if m:
        params["trip_length_days"] = int(m.group(1))
    else:
        m = re.search(r'(\d+)\s*weeks?', t)
        if m:
            params["trip_length_days"] = int(m.group(1)) * 7

    # Dates — keep scenario dates only when trip_length_days was explicitly found
    if params["trip_length_days"] is not None:
        params["start_date"] = scenario["start_date"]
        params["end_date"] = scenario["end_date"]

    # Cabin class
    if re.search(r'\bbusiness\s*class\b', t):
        params["cabin_class"] = "business"
    elif re.search(r'\bfirst\s*class\b', t):
        params["cabin_class"] = "first"
    elif re.search(r'\bpremium\s*economy\b', t):
        params["cabin_class"] = "premium_economy"

    # Hotel preference
    if re.search(r'\bluxury\b|\b5[\-\s]?star\b|\bfive[\-\s]?star\b', t):
        params["hotel_pref"] = "luxury"
    elif re.search(r'\bbudget\b|\bcheap\b|\bhostel\b|\bbackpack', t):
        params["hotel_pref"] = "budget"
    elif re.search(r'\bmid[\-\s]?range\b|\bmoderate\b', t):
        params["hotel_pref"] = "mid"

    # Budget ceiling
    m = re.search(r'\$\s*(\d[\d,]*)|\b(\d[\d,]+)\s*(?:usd|dollars?|bucks?)\b', t)
    if m:
        amount = (m.group(1) or m.group(2)).replace(",", "")
        params["budget_ceiling_usd"] = float(amount)

    return json.dumps(params)


# ── Flights ───────────────────────────────────────────────────────────────────

_MOCK_FLIGHTS: dict[str, list] = {
    "paris": [
        {
            "label": "cheapest",
            "airline": "IndiGo / Air Arabia",
            "route_summary": "DEL → SHJ → CDG (2 stops)",
            "layovers": 2,
            "duration": "15h 20m",
            "price_estimate_usd": 490,
            "source_note": "IndiGo codeshare via Sharjah — Aug 2026 low-season estimate",
        },
        {
            "label": "balanced",
            "airline": "Emirates",
            "route_summary": "DEL → DXB → CDG (1 stop)",
            "layovers": 1,
            "duration": "11h 55m",
            "price_estimate_usd": 830,
            "source_note": "Emirates EK510/EK073, economy class — Aug 2026",
        },
        {
            "label": "premium",
            "airline": "Air France",
            "route_summary": "DEL → CDG (nonstop)",
            "layovers": 0,
            "duration": "8h 50m",
            "price_estimate_usd": 3100,
            "source_note": "Air France AF218 business class La Suite — Aug 2026",
        },
    ],
    "tokyo": [
        {
            "label": "cheapest",
            "airline": "AirAsia X",
            "route_summary": "LHR → KUL → NRT (1 stop)",
            "layovers": 1,
            "duration": "18h 30m",
            "price_estimate_usd": 620,
            "source_note": "AirAsia X D7 via Kuala Lumpur — Sep 2026 estimate",
        },
        {
            "label": "balanced",
            "airline": "Finnair",
            "route_summary": "LHR → HEL → NRT (1 stop)",
            "layovers": 1,
            "duration": "13h 40m",
            "price_estimate_usd": 980,
            "source_note": "Finnair AY135/AY073, economy class — Sep 2026",
        },
        {
            "label": "premium",
            "airline": "Japan Airlines",
            "route_summary": "LHR → NRT (nonstop)",
            "layovers": 0,
            "duration": "12h 0m",
            "price_estimate_usd": 4200,
            "source_note": "JAL JL43 business class Sky Suite — Sep 2026",
        },
    ],
    "bali": [
        {
            "label": "cheapest",
            "airline": "Jetstar",
            "route_summary": "SYD → DPS (nonstop)",
            "layovers": 0,
            "duration": "6h 15m",
            "price_estimate_usd": 290,
            "source_note": "Jetstar JQ7, economy basic — Jul 2026 peak estimate",
        },
        {
            "label": "balanced",
            "airline": "Qantas",
            "route_summary": "SYD → DPS (nonstop)",
            "layovers": 0,
            "duration": "6h 20m",
            "price_estimate_usd": 520,
            "source_note": "Qantas QF43, economy flex — Jul 2026",
        },
        {
            "label": "premium",
            "airline": "Garuda Indonesia",
            "route_summary": "SYD → DPS (nonstop)",
            "layovers": 0,
            "duration": "6h 10m",
            "price_estimate_usd": 1650,
            "source_note": "Garuda GA715, business class — Jul 2026",
        },
    ],
    "dubai": [
        {
            "label": "cheapest",
            "airline": "Air India Express",
            "route_summary": "BOM → DXB (nonstop)",
            "layovers": 0,
            "duration": "3h 10m",
            "price_estimate_usd": 195,
            "source_note": "Air India Express IX344, economy — Oct 2026 estimate",
        },
        {
            "label": "balanced",
            "airline": "Air India",
            "route_summary": "BOM → DXB (nonstop)",
            "layovers": 0,
            "duration": "3h 15m",
            "price_estimate_usd": 340,
            "source_note": "Air India AI931, economy flex — Oct 2026",
        },
        {
            "label": "premium",
            "airline": "Emirates",
            "route_summary": "BOM → DXB (nonstop)",
            "layovers": 0,
            "duration": "3h 5m",
            "price_estimate_usd": 1800,
            "source_note": "Emirates EK191, business class fully-flat bed — Oct 2026",
        },
    ],
    "london": [
        {
            "label": "cheapest",
            "airline": "Norse Atlantic Airways",
            "route_summary": "JFK → LGW (nonstop)",
            "layovers": 0,
            "duration": "7h 10m",
            "price_estimate_usd": 310,
            "source_note": "Norse Atlantic N0701, economy light — Nov 2026 estimate",
        },
        {
            "label": "balanced",
            "airline": "Virgin Atlantic",
            "route_summary": "JFK → LHR (nonstop)",
            "layovers": 0,
            "duration": "7h 0m",
            "price_estimate_usd": 720,
            "source_note": "Virgin Atlantic VS3, premium economy — Nov 2026",
        },
        {
            "label": "premium",
            "airline": "British Airways",
            "route_summary": "JFK → LHR (nonstop)",
            "layovers": 0,
            "duration": "6h 55m",
            "price_estimate_usd": 4500,
            "source_note": "British Airways BA175, First Class — Nov 2026",
        },
    ],
}


def get_mock_flights_json(text: str) -> str:
    return json.dumps(_MOCK_FLIGHTS[get_mock_destination(text)])


# ── Hotels ────────────────────────────────────────────────────────────────────

_MOCK_HOTELS: dict[str, list] = {
    "paris": [
        {
            "label": "budget",
            "name": "Hôtel du Globe Saint-Germain",
            "area": "Saint-Germain-des-Prés, 6th arrondissement",
            "nightly_rate_usd": 95,
            "amenities": ["Free WiFi", "Daily Housekeeping", "Air Conditioning", "24h Reception"],
            "source_note": "Booking.com — Aug 2026 rates",
        },
        {
            "label": "mid_range",
            "name": "Mercure Paris Opera Grands Boulevards",
            "area": "Grands Boulevards, 9th arrondissement",
            "nightly_rate_usd": 185,
            "amenities": ["Free WiFi", "Breakfast Included", "Bar & Lounge", "Air Conditioning"],
            "source_note": "Accor Hotels — Aug 2026 rates",
        },
        {
            "label": "luxury",
            "name": "Hôtel Plaza Athénée",
            "area": "Avenue Montaigne, 8th arrondissement",
            "nightly_rate_usd": 1050,
            "amenities": ["Free WiFi", "Alain Ducasse Restaurant (3★)", "Dior Institute Spa", "Butler Service", "Rooftop Terrace"],
            "source_note": "Dorchester Collection — Aug 2026 rates",
        },
    ],
    "tokyo": [
        {
            "label": "budget",
            "name": "K's House Tokyo Asakusa",
            "area": "Asakusa, Taitō-ku",
            "nightly_rate_usd": 45,
            "amenities": ["Free WiFi", "Shared Kitchen", "Coin Laundry", "24h Reception", "Luggage Storage"],
            "source_note": "Hostelworld.com — Sep 2026 rates",
        },
        {
            "label": "mid_range",
            "name": "Shinjuku Granbell Hotel",
            "area": "Shinjuku, Tokyo",
            "nightly_rate_usd": 165,
            "amenities": ["Free WiFi", "Rooftop Terrace Bar", "Smart TV", "Concierge", "Daily Cleaning"],
            "source_note": "Granbell Hotels — Sep 2026 rates",
        },
        {
            "label": "luxury",
            "name": "Park Hyatt Tokyo",
            "area": "Nishi-Shinjuku, Shinjuku",
            "nightly_rate_usd": 680,
            "amenities": ["Free WiFi", "Peak Lounge & Bar (52nd fl.)", "Club on the Park Spa & Pool", "New York Grill Restaurant", "Panoramic City Views"],
            "source_note": "Park Hyatt Tokyo — Sep 2026 rates",
        },
    ],
    "bali": [
        {
            "label": "budget",
            "name": "Kampung Kecil Guest House",
            "area": "Ubud, Gianyar Regency",
            "nightly_rate_usd": 28,
            "amenities": ["Free WiFi", "Shared Pool", "Breakfast Included", "Rice Field Views", "Fan Cooling"],
            "source_note": "Agoda.com — Jul 2026 rates",
        },
        {
            "label": "mid_range",
            "name": "Katamama Hotel",
            "area": "Seminyak, Badung",
            "nightly_rate_usd": 220,
            "amenities": ["Free WiFi", "Private Plunge Pool Suite", "Cuca Restaurant", "Spa", "Airport Transfer", "Daily Breakfast"],
            "source_note": "Katamama Hotel — Jul 2026 rates",
        },
        {
            "label": "luxury",
            "name": "Four Seasons Resort Bali at Sayan",
            "area": "Sayan, Ubud",
            "nightly_rate_usd": 780,
            "amenities": ["Free WiFi", "Infinity Pool (Ayung River views)", "Healing Village Spa", "Jati Bar & Terrace", "Butler Service", "Jungle Trekking"],
            "source_note": "Four Seasons Bali — Jul 2026 rates",
        },
    ],
    "dubai": [
        {
            "label": "budget",
            "name": "Rove Downtown Dubai",
            "area": "Downtown Dubai, near Burj Khalifa",
            "nightly_rate_usd": 85,
            "amenities": ["Free WiFi", "Outdoor Pool", "The Daily Bar & Kitchen", "Fitness Centre", "Metro Access"],
            "source_note": "Rove Hotels — Oct 2026 rates",
        },
        {
            "label": "mid_range",
            "name": "Mövenpick Hotel Jumeirah Lakes Towers",
            "area": "JLT, Dubai Marina",
            "nightly_rate_usd": 195,
            "amenities": ["Free WiFi", "Rooftop Pool & Lounge", "Spice Emporium Restaurant", "Fitness Centre", "Marina Views"],
            "source_note": "Mövenpick Hotels — Oct 2026 rates",
        },
        {
            "label": "luxury",
            "name": "Atlantis The Palm",
            "area": "Palm Jumeirah",
            "nightly_rate_usd": 620,
            "amenities": ["Free WiFi", "Aquaventure Waterpark Access", "Nobu Restaurant", "Spa by Guerlain", "Private Beach", "20+ Restaurants & Bars"],
            "source_note": "Atlantis Hotel — Oct 2026 rates",
        },
    ],
    "london": [
        {
            "label": "budget",
            "name": "YHA London St Pancras",
            "area": "King's Cross, Camden",
            "nightly_rate_usd": 65,
            "amenities": ["Free WiFi", "Fully Equipped Kitchen", "Bar & Café", "24h Reception", "Luggage Storage"],
            "source_note": "YHA.org.uk — Nov 2026 rates",
        },
        {
            "label": "mid_range",
            "name": "citizenM Tower of London",
            "area": "Tower Hill, City of London",
            "nightly_rate_usd": 195,
            "amenities": ["Free WiFi", "24h Food & Drink", "MoodPad Room Control", "Free Netflix & Spotify", "Tower of London Views"],
            "source_note": "citizenM Hotels — Nov 2026 rates",
        },
        {
            "label": "luxury",
            "name": "Claridge's",
            "area": "Mayfair, Westminster",
            "nightly_rate_usd": 850,
            "amenities": ["Free WiFi", "Fera at Claridge's (1 Michelin star)", "The Painter's Room Bar", "24h In-Room Dining", "Butler Service", "Art Deco Interiors"],
            "source_note": "Claridge's — Nov 2026 rates",
        },
    ],
}


def get_mock_hotels_json(text: str) -> str:
    return json.dumps(_MOCK_HOTELS[get_mock_destination(text)])


# ── Attractions ───────────────────────────────────────────────────────────────

_MOCK_ATTRACTIONS: dict[str, list] = {
    "paris": [
        {
            "name": "Eiffel Tower",
            "category": "Landmark",
            "description": "Gustave Eiffel's 1889 iron marvel soars 330 m over the Seine and offers a breath-taking 360° panorama of Paris from its glass-floored summit.",
            "estimated_cost_usd": 31,
            "cost_note": "€29.40 (~$31) summit ticket — book 2–3 months in advance",
        },
        {
            "name": "Louvre Museum",
            "category": "Museum",
            "description": "The world's most-visited museum houses 35,000 works including the Mona Lisa, Venus de Milo, and the Winged Victory of Samothrace across 72,735 m².",
            "estimated_cost_usd": 22,
            "cost_note": "€22 (~$22) adult — free on first Sunday of each month",
        },
        {
            "name": "Palace of Versailles",
            "category": "Palace",
            "description": "Louis XIV's magnificent Sun King palace features the dazzling Hall of Mirrors, 700 rooms, and 800 hectares of formal French gardens — a half-day trip from Paris.",
            "estimated_cost_usd": 21,
            "cost_note": "€20 (~$21) day pass — 40 min by RER C from central Paris",
        },
        {
            "name": "Musée d'Orsay",
            "category": "Museum",
            "description": "A spectacular Beaux-Arts railway station converted into a museum holding the world's finest Impressionist collection — Monet, Renoir, Van Gogh, and Degas.",
            "estimated_cost_usd": 16,
            "cost_note": "€16 (~$16) — reduced on Thursday evenings after 18:00",
        },
        {
            "name": "Sacré-Cœur & Montmartre",
            "category": "Church",
            "description": "The gleaming white Romano-Byzantine basilica crowns the highest hill in Paris, surrounded by artists' studios and cobblestone streets once home to Picasso and Dalí.",
            "estimated_cost_usd": 0,
            "cost_note": "Free entry — dome climb €7 (~$7.40) for extra-panoramic views",
        },
    ],
    "tokyo": [
        {
            "name": "Senso-ji Temple",
            "category": "Temple",
            "description": "Tokyo's oldest Buddhist temple in Asakusa draws 30 million visitors a year to its iconic Kaminarimon Thunder Gate, five-storey pagoda, and Nakamise shopping street.",
            "estimated_cost_usd": 0,
            "cost_note": "Free entry — open 24h (main hall 6:00–17:00); omamori charms from ¥500 (~$3)",
        },
        {
            "name": "teamLab Planets TOKYO",
            "category": "Museum",
            "description": "A walk-through digital art installation where you wade barefoot through a mirrored universe of infinite flowers and light — Tokyo's most Instagrammed venue.",
            "estimated_cost_usd": 32,
            "cost_note": "¥3,200 (~$21) weekday / ¥4,800 (~$32) weekend — advance booking essential",
        },
        {
            "name": "Shinjuku Gyoen National Garden",
            "category": "Park",
            "description": "A serene 144-acre oasis blending French formal, English landscape, and traditional Japanese garden styles — Tokyo's premier cherry-blossom viewing spot each March.",
            "estimated_cost_usd": 3,
            "cost_note": "¥500 (~$3) adult entry — open Tue–Sun 9:00–16:30",
        },
        {
            "name": "Tsukiji Outer Market",
            "category": "Market",
            "description": "Tokyo's legendary seafood street market open since the 1930s, serving the city's freshest tuna sashimi, tamagoyaki omelettes, and grilled scallops by 7am.",
            "estimated_cost_usd": 0,
            "cost_note": "Free to browse — budget ¥1,500–3,000 (~$10–20) for tasting",
        },
        {
            "name": "Tokyo Skytree",
            "category": "Landmark",
            "description": "At 634 m, Japan's tallest structure offers two glass observation decks with 100-km views across the entire Kanto Plain on a clear day.",
            "estimated_cost_usd": 22,
            "cost_note": "¥2,100 (~$14) Tembo Deck (350m) / ¥3,400 (~$22) including Tembo Galleria (450m)",
        },
    ],
    "bali": [
        {
            "name": "Tanah Lot Sea Temple",
            "category": "Temple",
            "description": "A 16th-century Hindu sea temple perched on a dramatic rocky outcrop that becomes an island at high tide — Bali's most iconic sunset landmark and spiritual site.",
            "estimated_cost_usd": 4,
            "cost_note": "IDR 60,000 (~$4) foreign visitor entry — best visited 17:00–19:00 for sunset",
        },
        {
            "name": "Tegallalang Rice Terraces",
            "category": "Park",
            "description": "UNESCO-listed cascading emerald rice paddies sculpted over centuries using Bali's ancient subak cooperative irrigation — most magical at sunrise with low mist.",
            "estimated_cost_usd": 2,
            "cost_note": "IDR 20,000–30,000 (~$1.50–2) voluntary entry — swing experience IDR 150,000 (~$10) extra",
        },
        {
            "name": "Ubud Monkey Forest",
            "category": "Park",
            "description": "A sacred Hindu forest sanctuary housing 700+ long-tailed macaques among 186 species of trees and three ancient 14th-century moss-covered temples in the heart of Ubud.",
            "estimated_cost_usd": 5,
            "cost_note": "IDR 80,000 (~$5) adult — open daily 9:00–18:00; secure your belongings",
        },
        {
            "name": "Uluwatu Temple & Kecak Fire Dance",
            "category": "Temple",
            "description": "A clifftop sea temple perched 70 m above crashing Indian Ocean surf, followed by a mesmerising sunset Kecak fire dance performed by 50 bare-chested chanters.",
            "estimated_cost_usd": 11,
            "cost_note": "IDR 50,000 (~$3) temple + IDR 150,000 (~$8) Kecak dance — begins at 18:00",
        },
        {
            "name": "Seminyak Beach",
            "category": "Beach",
            "description": "Bali's most stylish stretch of volcanic black-sand beach, lined with luxury villa hotels, open-air beach clubs, and rooftop sunset bars — the island's glamour epicentre.",
            "estimated_cost_usd": 0,
            "cost_note": "Free beach access — beach club day passes IDR 200,000–500,000 (~$12–30) include food credit",
        },
    ],
    "dubai": [
        {
            "name": "Burj Khalifa Observation Deck",
            "category": "Landmark",
            "description": "The world's tallest building at 828 m offers a vertiginous 360° city-to-desert-to-sea panorama from Level 124/125, with interactive telescopes and a glass floor.",
            "estimated_cost_usd": 40,
            "cost_note": "AED 149 (~$40) Level 124/125 — book online 48h ahead for up to 30% discount",
        },
        {
            "name": "Dubai Mall & Dubai Fountain",
            "category": "Market",
            "description": "The world's largest mall by total area hosts 1,200 stores, an Olympic ice rink, and the Dubai Fountain — 275 m of water jets choreographed to music every 30 min after dark.",
            "estimated_cost_usd": 0,
            "cost_note": "Free entry — fountain shows daily from 18:00; indoor ski slope AED 280 (~$76)",
        },
        {
            "name": "Al Fahidi Historic District & Dubai Creek",
            "category": "Museum",
            "description": "Dubai's oldest surviving neighbourhood — a labyrinth of wind-tower coral-plaster merchants' houses, galleries, and the Dubai Museum, reached by AED 1 Abra water taxi.",
            "estimated_cost_usd": 1,
            "cost_note": "Free to explore — Dubai Museum AED 3 (~$1); Abra Creek crossing AED 1 (~$0.27)",
        },
        {
            "name": "Museum of the Future",
            "category": "Museum",
            "description": "An architectural icon clad in 1,024 stainless-steel panels bearing Arabic calligraphy, with seven immersive floors transporting visitors to life in 2071.",
            "estimated_cost_usd": 27,
            "cost_note": "AED 100 (~$27) adult — timed entry slots; book at least a week ahead",
        },
        {
            "name": "Palm Jumeirah & Atlantis Aquaventure",
            "category": "Beach",
            "description": "The world's largest man-made island shaped like a palm frond, home to Atlantis resort with 105 waterslides, a private beach, and the Lost Chambers Aquarium.",
            "estimated_cost_usd": 90,
            "cost_note": "AED 330 (~$90) Aquaventure day pass — free JBR Beach as budget alternative",
        },
    ],
    "london": [
        {
            "name": "The British Museum",
            "category": "Museum",
            "description": "Over 8 million objects spanning 2 million years of human history, including the Rosetta Stone, Elgin Marbles, Sutton Hoo Helmet, and Egyptian mummies — all completely free.",
            "estimated_cost_usd": 0,
            "cost_note": "Free permanent collection — special exhibitions £24–27 (~$29–33)",
        },
        {
            "name": "Tower of London",
            "category": "Castle",
            "description": "A 1,000-year-old Thames-side fortress guarding the Crown Jewels, with Beefeater Yeoman Warder guided tours, six resident ravens, and views from the medieval battlements.",
            "estimated_cost_usd": 38,
            "cost_note": "£32.90 (~$38) adult — book online to skip queues; combined tickets with Tower Bridge available",
        },
        {
            "name": "Borough Market",
            "category": "Market",
            "description": "London's oldest and most famous food market near London Bridge, open since 1014, now home to 100+ stalls with artisan cheeses, fresh pasta, and street food from 30 countries.",
            "estimated_cost_usd": 0,
            "cost_note": "Free to browse — budget £15–30 (~$18–36) for a generous tasting lunch",
        },
        {
            "name": "Tate Modern",
            "category": "Museum",
            "description": "The world's most-visited modern art museum in a converted Bankside power station, displaying 70,000 works by Picasso, Warhol, and Rothko with sweeping Thames views.",
            "estimated_cost_usd": 0,
            "cost_note": "Free permanent collection — special exhibitions ~£22 (~$26)",
        },
        {
            "name": "Buckingham Palace & St. James's Park",
            "category": "Palace",
            "description": "The King's official 775-room London residence — Changing of the Guard ceremony daily at 11am in summer, and St. James's Park is London's most beautiful royal park.",
            "estimated_cost_usd": 0,
            "cost_note": "Changing of the Guard & park free — State Rooms £40 (~$47) in Aug/Sep only",
        },
    ],
}


def get_mock_attractions_json(text: str) -> str:
    return json.dumps(_MOCK_ATTRACTIONS[get_mock_destination(text)])


# ── Budget estimates ──────────────────────────────────────────────────────────

_MOCK_BUDGETS: dict[str, dict] = {
    "paris": {  # 2 travelers, 7 nights
        "flights_usd":         {"low": 980,  "mid": 1660, "high": 6200},
        "hotel_usd":           {"low": 665,  "mid": 1295, "high": 7350},
        "food_usd":            {"low": 490,  "mid": 980,  "high": 2590},
        "local_transport_usd": {"low": 210,  "mid": 448,  "high": 910},
        "activities_usd":      {"low": 420,  "mid": 910,  "high": 2100},
        "buffer_usd":          {"low": 277,  "mid": 529,  "high": 1915},
        "total_usd":           {"low": 3042, "mid": 5822, "high": 21065},
        "uncertain_categories": ["activities — estimated from typical Paris visitor spend"],
    },
    "tokyo": {  # 1 traveler, 10 nights
        "flights_usd":         {"low": 620,  "mid": 980,  "high": 4200},
        "hotel_usd":           {"low": 450,  "mid": 1650, "high": 6800},
        "food_usd":            {"low": 350,  "mid": 800,  "high": 2000},
        "local_transport_usd": {"low": 200,  "mid": 400,  "high": 800},
        "activities_usd":      {"low": 150,  "mid": 350,  "high": 800},
        "buffer_usd":          {"low": 177,  "mid": 418,  "high": 1460},
        "total_usd":           {"low": 1947, "mid": 4598, "high": 16060},
        "uncertain_categories": ["food — JPY/USD rate may shift; yen remains historically weak"],
    },
    "bali": {  # 2 travelers, 7 nights
        "flights_usd":         {"low": 580,  "mid": 1040, "high": 3300},
        "hotel_usd":           {"low": 196,  "mid": 1540, "high": 5460},
        "food_usd":            {"low": 245,  "mid": 490,  "high": 1225},
        "local_transport_usd": {"low": 140,  "mid": 280,  "high": 560},
        "activities_usd":      {"low": 140,  "mid": 280,  "high": 700},
        "buffer_usd":          {"low": 130,  "mid": 363,  "high": 1125},
        "total_usd":           {"low": 1431, "mid": 3993, "high": 12370},
        "uncertain_categories": ["hotel — Jul peak season; prices 25% lower in shoulder season"],
    },
    "dubai": {  # 2 travelers, 5 nights
        "flights_usd":         {"low": 390,  "mid": 680,  "high": 3600},
        "hotel_usd":           {"low": 425,  "mid": 975,  "high": 3100},
        "food_usd":            {"low": 175,  "mid": 400,  "high": 1000},
        "local_transport_usd": {"low": 100,  "mid": 200,  "high": 500},
        "activities_usd":      {"low": 200,  "mid": 400,  "high": 1000},
        "buffer_usd":          {"low": 129,  "mid": 266,  "high": 920},
        "total_usd":           {"low": 1419, "mid": 2921, "high": 10120},
        "uncertain_categories": ["activities — Dubai attraction prices vary; book ahead for discounts"],
    },
    "london": {  # 1 traveler, 7 nights
        "flights_usd":         {"low": 310,  "mid": 720,  "high": 4500},
        "hotel_usd":           {"low": 455,  "mid": 1365, "high": 5950},
        "food_usd":            {"low": 350,  "mid": 700,  "high": 1750},
        "local_transport_usd": {"low": 140,  "mid": 224,  "high": 448},
        "activities_usd":      {"low": 150,  "mid": 350,  "high": 800},
        "buffer_usd":          {"low": 141,  "mid": 336,  "high": 1345},
        "total_usd":           {"low": 1546, "mid": 3695, "high": 14793},
        "uncertain_categories": ["flights — GBP/USD rate sensitive in Nov 2026"],
    },
}


def get_mock_budget_json(text: str) -> str:
    return json.dumps(_MOCK_BUDGETS[get_mock_destination(text)])


# ── Web search results ────────────────────────────────────────────────────────

_MOCK_SEARCH: dict[str, str] = {
    "paris": (
        "Featured answer: Paris is the world's most visited city, attracting over 30 million tourists annually.\n"
        "Knowledge graph: Paris — Capital of France; City of Light; renowned for the Eiffel Tower, Louvre, and world-class cuisine.\n"
        "• Top Paris Attractions 2026 | Lonely Planet: Eiffel Tower summit €29.40, Louvre €22, Palace of Versailles €20 day pass, Musée d'Orsay €16. Sacré-Cœur and Notre-Dame (fully reopened Dec 2024) are free. [Source: https://www.lonelyplanet.com/france/paris]\n"
        "• Flights to Paris Aug 2026 | Skyscanner: DEL→CDG from ₹38,000 (~$460) on IndiGo/Air Arabia via Sharjah; Emirates via Dubai from ₹69,000 (~$830); Air France nonstop from ₹2,58,000 (~$3,070). [Source: https://www.skyscanner.com]\n"
        "• Best Paris Hotels 2026 | Booking.com: Budget from €85/night (Hôtel du Globe, Saint-Germain), mid-range €170/night (Mercure Opera), luxury €950/night (Plaza Athénée). August is peak season — book 2 months ahead. [Source: https://www.booking.com/city/fr/paris.html]\n"
        "• August in Paris | Time Out: Many Parisians leave in August — shorter museum queues. Average 24°C (75°F). Paris Plages beach along the Seine open Jul–Aug. [Source: https://www.timeout.com/paris]\n"
        "• Paris Budget Guide | Nomadic Matt: Daily budget traveller €70–100/day; mid-range €180–280; luxury €500+. Picnic lunches from €8 by the Seine. Free museum Sundays first of each month. [Source: https://www.nomadicmatt.com/travel-guides/paris-travel-guide]"
    ),
    "tokyo": (
        "Featured answer: Tokyo is the world's most populous metropolis with 37 million people and the #1 TripAdvisor destination five years running.\n"
        "Knowledge graph: Tokyo — Capital of Japan; most Michelin-starred restaurant city globally; home of teamLab, anime culture, and cherry blossoms.\n"
        "• Top Tokyo Attractions 2026 | Japan Guide: Senso-ji Temple (Asakusa, free), teamLab Planets ¥4,800 (~$32), Shinjuku Gyoen ¥500 (~$3), Tokyo Skytree ¥3,400 (~$22), Tsukiji Outer Market (free). [Source: https://www.japan-guide.com/e/e2164.html]\n"
        "• Tokyo Flights Sep 2026 | Google Flights: LHR→NRT from £490 (~$620) AirAsia X via Kuala Lumpur; Finnair via Helsinki £780 (~$980); JAL nonstop business £3,300 (~$4,200). [Source: https://flights.google.com]\n"
        "• Tokyo Hotels Sep 2026 | Booking.com: K's House Asakusa hostel from $45/night; Shinjuku Granbell Hotel $165/night; Park Hyatt Tokyo from $680/night. [Source: https://www.booking.com/city/jp/tokyo.html]\n"
        "• Tokyo Food Costs | Eater: Ramen ¥800–1,200 ($5–8); conveyor-belt sushi ¥110/plate; kaiseki dinner ¥15,000–30,000 ($100–200). [Source: https://tokyo.eater.com]\n"
        "• September Tokyo | JMA: Post-typhoon season, avg 26°C (79°F), clear skies, lower crowds than March cherry blossom peak. Silver Week 23 Sep 2026 — book early. [Source: https://www.jma.go.jp]"
    ),
    "bali": (
        "Featured answer: Bali welcomed 6.3 million international visitors in 2025, making it Indonesia's top destination and one of Asia's most beloved island escapes.\n"
        "Knowledge graph: Bali — Indonesian island province; known for Hindu temples, rice terraces, surf breaks, and wellness retreats.\n"
        "• Top Bali Attractions 2026 | Culture Trip: Tanah Lot IDR 60,000 (~$4), Tegallalang IDR 30,000 (~$2), Ubud Monkey Forest IDR 80,000 (~$5), Uluwatu Kecak Dance IDR 150,000 (~$9), Seminyak Beach (free). [Source: https://theculturetrip.com/asia/indonesia/bali]\n"
        "• Bali Flights Jul 2026 | Skyscanner: SYD→DPS from A$380 (~$290) Jetstar nonstop; Qantas from A$680 (~$520). Peak July holidays — book 3+ months ahead. [Source: https://www.skyscanner.com/routes/syd/dps]\n"
        "• Bali Hotels Jul 2026 | Agoda: Ubud guesthouse from IDR 450,000 ($28)/night; Seminyak villa with pool from IDR 3,500,000 ($220)/night; Four Seasons Sayan from IDR 12,500,000 ($780)/night. [Source: https://www.agoda.com/bali]\n"
        "• Bali Budget 2026 | Broke Backpacker: $40–60/day budget (guesthouse + warung meals + scooter IDR 80,000/day). Avoid July if budget-conscious — peak prices 30% higher. [Source: https://www.thebrokebackpacker.com/bali-budget]\n"
        "• Bali July Weather: Dry season peak (May–Sep), avg 27°C (81°F), low humidity. Best beach and trekking conditions but peak crowds and prices. [Source: https://www.bali-indonesia.com/weather]"
    ),
    "dubai": (
        "Featured answer: Dubai received 17.15 million international overnight visitors in 2024, ranking it 4th in the world and the Middle East's undisputed tourism capital.\n"
        "Knowledge graph: Dubai — Emirate of UAE; home to Burj Khalifa (828m world's tallest), the world's largest mall, and Burj Al Arab.\n"
        "• Top Dubai Attractions 2026 | Visit Dubai: Burj Khalifa Level 124/125 AED 149 (~$40), Dubai Mall & Fountain (free), Al Fahidi District (free), Museum of the Future AED 100 (~$27), Aquaventure AED 330 (~$90). [Source: https://www.visitdubai.com]\n"
        "• Dubai Flights Oct 2026 | Emirates.com: BOM→DXB from ₹16,000 (~$195) Air India Express nonstop; Air India economy ₹28,000 (~$340); Emirates business ₹1,50,000 (~$1,800). [Source: https://www.emirates.com]\n"
        "• Dubai Hotels Oct 2026 | Marriott: Rove Downtown from AED 310 ($85)/night; Mövenpick JLT AED 715 ($195)/night; Atlantis The Palm AED 2,280 ($621)/night. October ideal — mild 30–33°C after searing summer. [Source: https://www.marriott.com]\n"
        "• Dubai October | Dubai Calendar: Dubai Fitness Challenge (1–30 Oct, free citywide events). Average 33°C day / 25°C night — swimwear weather at beaches. [Source: https://www.dubaicalendar.com]\n"
        "• Dubai Budget Tips | Condé Nast: Metro from AED 2 ($0.54), shawarma AED 5 ($1.36), free JBR Beach. Budget travellers can manage AED 400–600 ($109–163)/day. [Source: https://www.cntraveller.com/dubai]"
    ),
    "london": (
        "Featured answer: London attracted 21.7 million international visitors in 2024, making it Europe's most visited city and one of the world's great cultural capitals.\n"
        "Knowledge graph: London — Capital of the UK; home to the British Museum, Tate Modern, Tower of London, Buckingham Palace, and the West End theatre scene.\n"
        "• Top London Attractions 2026 | Visit London: British Museum (free), Tate Modern (free), Tower of London £32.90 (~$38), Buckingham Palace State Rooms £40 (~$47), Borough Market (free). [Source: https://www.visitlondon.com]\n"
        "• NYC→London Flights Nov 2026 | Google Flights: JFK→LGW from $310 Norse Atlantic nonstop; Virgin Atlantic premium economy JFK→LHR $720; British Airways First Class $4,500. Nov off-peak = better fares. [Source: https://flights.google.com]\n"
        "• London Hotels Nov 2026 | Hotels.com: YHA St Pancras from £55 ($65)/night; citizenM Tower of London from £165 ($195)/night; Claridge's Mayfair from £720 ($850)/night. Nov off-peak = 15–25% below summer. [Source: https://uk.hotels.com]\n"
        "• London November | Time Out: Bonfire Night fireworks 5 Nov, Remembrance Sunday 8 Nov, Christmas lights switch-on mid-Nov. Avg 9°C (48°F) — pack layers and a waterproof. [Source: https://www.timeout.com/london]\n"
        "• London Budget | Culture Trip: Free museums save £50+/day. 7-day Oyster travel card from £35 (~$41). Pre-theatre set menus from £25 (~$30). Daily mid-range budget £120–180/day. [Source: https://theculturetrip.com/europe/united-kingdom/england/london]"
    ),
}


def get_mock_search_result(query: str) -> str:
    return _MOCK_SEARCH[get_mock_destination(query)]


# ── Image URLs (picsum.photos — deterministic seeds, always available) ────────

_MOCK_IMAGES: dict[str, list[str]] = {
    "paris":  [
        "https://picsum.photos/seed/paris-eiffel/800/450",
        "https://picsum.photos/seed/paris-louvre/800/450",
        "https://picsum.photos/seed/paris-versailles/800/450",
        "https://picsum.photos/seed/paris-dorsay/800/450",
        "https://picsum.photos/seed/paris-montmartre/800/450",
    ],
    "tokyo":  [
        "https://picsum.photos/seed/tokyo-sensoji/800/450",
        "https://picsum.photos/seed/tokyo-teamlab/800/450",
        "https://picsum.photos/seed/tokyo-gyoen/800/450",
        "https://picsum.photos/seed/tokyo-tsukiji/800/450",
        "https://picsum.photos/seed/tokyo-skytree/800/450",
    ],
    "bali":   [
        "https://picsum.photos/seed/bali-tanahlot/800/450",
        "https://picsum.photos/seed/bali-terraces/800/450",
        "https://picsum.photos/seed/bali-monkey/800/450",
        "https://picsum.photos/seed/bali-uluwatu/800/450",
        "https://picsum.photos/seed/bali-seminyak/800/450",
    ],
    "dubai":  [
        "https://picsum.photos/seed/dubai-burjkhalifa/800/450",
        "https://picsum.photos/seed/dubai-mall/800/450",
        "https://picsum.photos/seed/dubai-creek/800/450",
        "https://picsum.photos/seed/dubai-future/800/450",
        "https://picsum.photos/seed/dubai-palm/800/450",
    ],
    "london": [
        "https://picsum.photos/seed/london-britishmuseum/800/450",
        "https://picsum.photos/seed/london-tower/800/450",
        "https://picsum.photos/seed/london-borough/800/450",
        "https://picsum.photos/seed/london-tate/800/450",
        "https://picsum.photos/seed/london-palace/800/450",
    ],
}

_image_idx: dict[str, int] = {}


def get_mock_image_url(query: str) -> str:
    dest = get_mock_destination(query)
    urls = _MOCK_IMAGES[dest]
    i = _image_idx.get(dest, 0)
    _image_idx[dest] = (i + 1) % len(urls)
    return urls[i]


# ── Reports ───────────────────────────────────────────────────────────────────

_MOCK_REPORTS: dict[str, str] = {
    "paris": """\
# Trip Plan: New Delhi → Paris
**Dates:** 2026-08-10 – 2026-08-17 (7 nights) | **Travelers:** 2

## ✈️ Flight Options
| Option | Airline | Route | Duration | Price (est.) |
|---|---|---|---|---|
| 1 (Cheapest) | IndiGo / Air Arabia | DEL → SHJ → CDG (2 stops) | 15h 20m | ₹41,200 (~$490/person) |
| 2 (Balanced) | Emirates | DEL → DXB → CDG (1 stop) | 11h 55m | ₹69,700 (~$830/person) |
| 3 (Premium) | Air France | DEL → CDG (nonstop) | 8h 50m | ₹2,60,400 (~$3,100/person) |

## 🏨 Hotel Options
| Option | Name | Area | Nightly Rate | Notes |
|---|---|---|---|---|
| 1 (Budget) | Hôtel du Globe Saint-Germain | Saint-Germain-des-Prés | ₹7,980/night (~$95) | Free WiFi, Air Conditioning |
| 2 (Mid-range) | Mercure Paris Opera Grands Boulevards | Grands Boulevards, 9th | ₹15,540/night (~$185) | Breakfast Included, Bar & Lounge |
| 3 (Luxury) | Hôtel Plaza Athénée | Avenue Montaigne, 8th | ₹88,200/night (~$1,050) | Alain Ducasse Restaurant, Dior Spa |

## 💰 Estimated Budget (2 travelers, 7 nights)
| Category | Low | Mid | High |
|---|---|---|---|
| Flights | ₹82,300 | ₹1,39,400 | ₹5,20,800 |
| Hotel | ₹55,900 | ₹1,08,800 | ₹6,17,400 |
| Food | ₹41,200 | ₹82,300 | ₹2,17,600 |
| Local Transport | ₹17,600 | ₹37,600 | ₹76,400 |
| Activities | ₹35,300 | ₹76,400 | ₹1,76,400 |
| Buffer (10%) | ₹23,300 | ₹44,500 | ₹1,60,900 |
| **Total** | **₹2,55,600** | **₹4,89,000** | **₹17,69,500** |

*Exchange rate used: 1 USD = ₹84.00 (live rate)*

## ✅ Final Recommendation
**Book Emirates economy (DEL → DXB → CDG, ₹69,700/person) + Mercure Paris Opera (₹15,540/night)** for a classic Paris holiday. The Emirates 1-stop routing via Dubai offers excellent in-flight service and a convenient layover. Mercure Opera's central 9th-arrondissement location gives metro access to every major sight within 20 minutes, with breakfast included to keep daily costs down. Total mid-range cost: approximately **₹4,89,000 (~$5,822) for 2 people** — outstanding value for 7 nights in the City of Light.
""",
    "tokyo": """\
# Trip Plan: London → Tokyo
**Dates:** 2026-09-05 – 2026-09-15 (10 nights) | **Travelers:** 1

## ✈️ Flight Options
| Option | Airline | Route | Duration | Price (est.) |
|---|---|---|---|---|
| 1 (Cheapest) | AirAsia X | LHR → KUL → NRT (1 stop) | 18h 30m | ₹52,100 (~$620) |
| 2 (Balanced) | Finnair | LHR → HEL → NRT (1 stop) | 13h 40m | ₹82,300 (~$980) |
| 3 (Premium) | Japan Airlines | LHR → NRT (nonstop) | 12h 0m | ₹3,52,800 (~$4,200) |

## 🏨 Hotel Options
| Option | Name | Area | Nightly Rate | Notes |
|---|---|---|---|---|
| 1 (Budget) | K's House Tokyo Asakusa | Asakusa, Taitō-ku | ₹3,800/night (~$45) | Shared Kitchen, Coin Laundry |
| 2 (Mid-range) | Shinjuku Granbell Hotel | Shinjuku, Tokyo | ₹13,900/night (~$165) | Rooftop Terrace Bar, Smart TV |
| 3 (Luxury) | Park Hyatt Tokyo | Nishi-Shinjuku | ₹57,100/night (~$680) | Peak Lounge 52F, Heated Pool 49F |

## 💰 Estimated Budget (1 traveler, 10 nights)
| Category | Low | Mid | High |
|---|---|---|---|
| Flights | ₹52,100 | ₹82,300 | ₹3,52,800 |
| Hotel | ₹37,800 | ₹1,38,600 | ₹5,71,200 |
| Food | ₹29,400 | ₹67,200 | ₹1,68,000 |
| Local Transport | ₹16,800 | ₹33,600 | ₹67,200 |
| Activities | ₹12,600 | ₹29,400 | ₹67,200 |
| Buffer (10%) | ₹14,900 | ₹35,100 | ₹1,22,600 |
| **Total** | **₹1,63,600** | **₹3,86,200** | **₹13,49,000** |

*Exchange rate used: 1 USD = ₹84.00 (live rate)*

## ✅ Final Recommendation
**Book Finnair economy (LHR → HEL → NRT, ₹82,300) + Shinjuku Granbell Hotel (₹13,900/night)** for the best Tokyo experience at a sensible price. Finnair's Helsinki routing is 5 hours faster than the Kuala Lumpur connection and uses a comfortable Airbus A350. The Granbell's Shinjuku location puts you steps from Tokyo's best nightlife, department stores, and transport links to Nikko and Mount Fuji. Total mid-range cost: approximately **₹3,86,200 (~$4,598) per person** for 10 extraordinary nights in one of the world's greatest cities.
""",
    "bali": """\
# Trip Plan: Sydney → Bali
**Dates:** 2026-07-20 – 2026-07-27 (7 nights) | **Travelers:** 2

## ✈️ Flight Options
| Option | Airline | Route | Duration | Price (est.) |
|---|---|---|---|---|
| 1 (Cheapest) | Jetstar | SYD → DPS (nonstop) | 6h 15m | ₹24,400 (~$290/person) |
| 2 (Balanced) | Qantas | SYD → DPS (nonstop) | 6h 20m | ₹43,700 (~$520/person) |
| 3 (Premium) | Garuda Indonesia | SYD → DPS (nonstop) | 6h 10m | ₹1,38,600 (~$1,650/person) |

## 🏨 Hotel Options
| Option | Name | Area | Nightly Rate | Notes |
|---|---|---|---|---|
| 1 (Budget) | Kampung Kecil Guest House | Ubud, Gianyar | ₹2,400/night (~$28) | Shared Pool, Breakfast, Rice Field Views |
| 2 (Mid-range) | Katamama Hotel | Seminyak, Badung | ₹18,500/night (~$220) | Private Plunge Pool Suite, Cuca Restaurant |
| 3 (Luxury) | Four Seasons Resort at Sayan | Sayan, Ubud | ₹65,500/night (~$780) | Infinity Pool, Healing Village Spa |

## 💰 Estimated Budget (2 travelers, 7 nights)
| Category | Low | Mid | High |
|---|---|---|---|
| Flights | ₹48,700 | ₹87,400 | ₹2,77,200 |
| Hotel | ₹16,500 | ₹1,29,400 | ₹4,58,600 |
| Food | ₹20,600 | ₹41,200 | ₹1,03,000 |
| Local Transport | ₹11,800 | ₹23,500 | ₹47,000 |
| Activities | ₹11,800 | ₹23,500 | ₹58,800 |
| Buffer (10%) | ₹10,900 | ₹30,500 | ₹94,500 |
| **Total** | **₹1,20,300** | **₹3,35,500** | **₹10,39,100** |

*Exchange rate used: 1 USD = ₹84.00 (live rate)*

## ✅ Final Recommendation
**Book Qantas economy (SYD → DPS, ₹43,700/person) + Katamama Hotel Seminyak (₹18,500/night)** for a quintessential Bali holiday. Qantas offers far superior in-flight service and flexible fare conditions versus Jetstar's basic product — worth the modest premium for a 6-hour flight. Katamama's private plunge-pool suites in Seminyak put you at the heart of Bali's best dining and beach clubs, with easy day-trip access to Ubud. Total mid-range cost: approximately **₹3,35,500 (~$3,993) for 2 people** — outstanding value for 7 nights in paradise.
""",
    "dubai": """\
# Trip Plan: Mumbai → Dubai
**Dates:** 2026-10-01 – 2026-10-06 (5 nights) | **Travelers:** 2

## ✈️ Flight Options
| Option | Airline | Route | Duration | Price (est.) |
|---|---|---|---|---|
| 1 (Cheapest) | Air India Express | BOM → DXB (nonstop) | 3h 10m | ₹16,400 (~$195/person) |
| 2 (Balanced) | Air India | BOM → DXB (nonstop) | 3h 15m | ₹28,600 (~$340/person) |
| 3 (Premium) | Emirates | BOM → DXB (nonstop) | 3h 5m | ₹1,51,200 (~$1,800/person) |

## 🏨 Hotel Options
| Option | Name | Area | Nightly Rate | Notes |
|---|---|---|---|---|
| 1 (Budget) | Rove Downtown Dubai | Downtown, near Burj Khalifa | ₹7,100/night (~$85) | Outdoor Pool, Bar & Kitchen, Metro Access |
| 2 (Mid-range) | Mövenpick JLT | JLT, Dubai Marina | ₹16,400/night (~$195) | Rooftop Pool, Marina Views |
| 3 (Luxury) | Atlantis The Palm | Palm Jumeirah | ₹52,100/night (~$620) | Aquaventure, Nobu, Private Beach |

## 💰 Estimated Budget (2 travelers, 5 nights)
| Category | Low | Mid | High |
|---|---|---|---|
| Flights | ₹32,800 | ₹57,100 | ₹3,02,400 |
| Hotel | ₹35,700 | ₹81,900 | ₹2,60,400 |
| Food | ₹14,700 | ₹33,600 | ₹84,000 |
| Local Transport | ₹8,400 | ₹16,800 | ₹42,000 |
| Activities | ₹16,800 | ₹33,600 | ₹84,000 |
| Buffer (10%) | ₹10,800 | ₹22,300 | ₹77,300 |
| **Total** | **₹1,19,200** | **₹2,45,300** | **₹8,50,100** |

*Exchange rate used: 1 USD = ₹84.00 (live rate)*

## ✅ Final Recommendation
**Book Air India economy flex (BOM → DXB, ₹28,600/person) + Mövenpick JLT (₹16,400/night)** for the ideal Dubai city-break. Air India flex fares include checked baggage and free date change — essential on a short trip. The Mövenpick's rooftop pool, marina views, and easy metro/tram access to Downtown Dubai and Dubai Mall deliver genuine 4-star quality at a competitive price. Total mid-range cost: approximately **₹2,45,300 (~$2,921) for 2 people** — excellent value for 5 nights just a 3-hour flight from Mumbai.
""",
    "london": """\
# Trip Plan: New York → London
**Dates:** 2026-11-10 – 2026-11-17 (7 nights) | **Travelers:** 1

## ✈️ Flight Options
| Option | Airline | Route | Duration | Price (est.) |
|---|---|---|---|---|
| 1 (Cheapest) | Norse Atlantic Airways | JFK → LGW (nonstop) | 7h 10m | ₹26,000 (~$310) |
| 2 (Balanced) | Virgin Atlantic | JFK → LHR (nonstop, premium eco.) | 7h 0m | ₹60,500 (~$720) |
| 3 (Premium) | British Airways | JFK → LHR (nonstop, First Class) | 6h 55m | ₹3,78,000 (~$4,500) |

## 🏨 Hotel Options
| Option | Name | Area | Nightly Rate | Notes |
|---|---|---|---|---|
| 1 (Budget) | YHA London St Pancras | King's Cross, Camden | ₹5,500/night (~$65) | Kitchen, Bar & Café, 24h Reception |
| 2 (Mid-range) | citizenM Tower of London | Tower Hill, City of London | ₹16,400/night (~$195) | Tower Views, Free Netflix & Spotify |
| 3 (Luxury) | Claridge's | Mayfair, Westminster | ₹71,400/night (~$850) | Michelin Restaurant, Butler Service |

## 💰 Estimated Budget (1 traveler, 7 nights)
| Category | Low | Mid | High |
|---|---|---|---|
| Flights | ₹26,000 | ₹60,500 | ₹3,78,000 |
| Hotel | ₹38,200 | ₹1,14,600 | ₹5,00,200 |
| Food | ₹29,400 | ₹58,800 | ₹1,47,000 |
| Local Transport | ₹11,800 | ₹18,800 | ₹37,600 |
| Activities | ₹12,600 | ₹29,400 | ₹67,200 |
| Buffer (10%) | ₹11,800 | ₹28,200 | ₹1,13,000 |
| **Total** | **₹1,29,800** | **₹3,10,300** | **₹12,43,000** |

*Exchange rate used: 1 USD = ₹84.00 (live rate)*

## ✅ Final Recommendation
**Book Virgin Atlantic premium economy (JFK → LHR, ₹60,500) + citizenM Tower of London (₹16,400/night)** for a stylish November London break. Virgin's premium economy on the 7-hour transatlantic flight offers real legroom and a significantly more comfortable seat than Norse Atlantic's basic product — worth the upgrade. citizenM's cantilevered rooms with direct Tower of London views deliver a premium feel at a mid-range price, and its Southbank location puts the British Museum, Borough Market, and Tate Modern within walking distance. Total mid-range cost: approximately **₹3,10,300 (~$3,695) per person** — a thorough London experience at excellent value.
""",
}


def get_mock_report(text: str) -> str:
    return _MOCK_REPORTS[get_mock_destination(text)]
