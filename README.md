# ExploreMate · Adaptive Eco-Travel Guide & Pondicherry Explorer

ExploreMate is an adaptive, eco-friendly travel guide web application built for the **ZÉPHYR Hackathon**. It features real-time meteorological adaptation, verified Pondicherry heritage data, DEFRA-benchmarked carbon footprint calculations, interactive OpenStreetMap mapping with transit hubs, crowd-level rush hour warnings, Bayesian rating & review analytics, and a grounded Gemini AI chatbot.

---

## 🌟 Upgraded Capabilities & Features

### 1. Rebranding & Custom Logo
- Fully rebranded across all templates, styles, endpoints, and scripts to **ExploreMate**.
- User's logo integrated in both desktop and mobile navbar at `/assets/logo.png` and `/static/logo.png`, with proper `alt="ExploreMate Logo"` and favicon support.

### 2. Search Behavior (Pondicherry & Puducherry Only)
- Robust fuzzy matching supports `"Pondicherry"`, `"Puducherry"`, `"pondy"`, `"puducheri"`, and case/spacing variations.
- **Strict Scope Guard**: Searching any unsupported destination (e.g., Paris, Goa, Tokyo) displays an accessible, centered notice:
  > *"Paris will be developed in the future. ExploreMate currently supports Pondicherry only."*
  Pondicherry results are never mistakenly displayed for other cities.

### 3. Centered Interactive Modal
- Replaced old top-of-screen popup with a centered dialog modal:
  - Accessible `role="dialog"` and `aria-modal="true"`.
  - Keyboard focus trapping (`Tab` and `Shift + Tab` cycle inside the modal).
  - Closes cleanly via `Esc` key, close button, or clicking outside on the backdrop.
  - Smooth scale & fade animation; restores previous focus on dismissal.

### 4. Real Pictures & Image Licensing (Strict)
- **Zero AI-generated photos**.
- Sourced authentic photographs from **Wikimedia Commons** and verified Pondicherry heritage collections (including user reference photo for White Town).
- Every photo displays its exact credit, license (`CC BY-SA 4.0`, `CC BY 3.0`, etc.), and source URL directly underneath.

### 5. Accurate Dining & Accommodation Data
- Stored in unified `data/pondicherry.json`.
- Exact prices in INR (`₹`) with a `last_verified` date for each item.
- Opening/closing hours with real-time dynamic **"Open now / Closed"** badges.
- **Proximity Search**: Endpoint `/api/restaurants/near-route` calculates and ranks restaurants situated between any two selected attractions.

### 6. Official Booking Links
- Direct "Book now" / "Reserve Table" buttons opening official portals in new tabs (`target="_blank" rel="noopener noreferrer"`):
  - **Hotels**: Booking.com, MakeMyTrip, and hotel official websites.
  - **Dining**: Google Maps table reservations and direct call links.
  - **Trains**: IRCTC Official Portal for Puducherry Railway Station (`PDY`).
  - **Buses**: redBus, PRTC, and TNSTC for the New Interstate Bus Terminal.

### 7. Interactive Map & Transit Hubs (Free Leaflet + OSM)
- Free OpenStreetMap integration via Leaflet (no paid keys required).
- Pinpoints all attractions, Puducherry Railway Station (PDY), and Main Bus Stands.
- **"Locate Me" GPS button**: Zooms to user coordinates and calculates distance and walking times to the nearest railway station and bus stands.
- **"Get Directions"**: Opens turn-by-turn navigation in Google Maps.

### 8. "Before You Go" Cultural Guidelines & Safety Numbers
- For every attraction: Dress code, entry fees, timings, photography restrictions, best time to visit, things to avoid, and accessibility accommodations.
- Verified emergency numbers:
  - **Police**: 100
  - **Ambulance**: 108
  - **Fire**: 101
  - **Women Helpline**: 1091
  - **Tourist Helpline**: 1363
  - **Puducherry Tourism HQ**: +91 413 2234500
  - **Nearest 24/7 Hospital** mapped for every location.

### 9. Crowd / Rush Times & Smart Itinerary Builder
- Hourly crowd estimates (Low, Medium, High) for weekdays and weekends.
- Automatic rush hour alerts when an attraction falls during peak density.
- Includes meal slots (Breakfast, Lunch, Dinner) with open verified restaurants.
- Solid opaque display box with action buttons to **Save Plan** (locally), **Print Plan** (`window.print()`), and **Share Plan**.

### 10. Gemini AI Chatbot (Live Context Aware)
- Free tier Google Gemini integration via modern backend endpoint `POST /api/chat`.
- Built using the official `google-genai` Python SDK (`v2.29.0`) targeting `gemini-2.5-flash`.
- API key is kept secure on the backend and **never exposed to frontend code**.
- Grounded in `data/pondicherry.json`: answers questions regarding exact prices, timings, crowds, and safety numbers.
- **Live Itinerary Modification**: Chatbot can add or remove stops from the itinerary on request.
- Built-in in-memory rate limiting (max 30 requests/min per IP) and input validation.

### 11. Dark & Light Theme Toggle
- Accessible navbar button toggling between dark and light themes using CSS variables.
- Saves choice in `localStorage`.
- Anti-flicker `<head>` script ensures zero screen flash on load.
- Honors `prefers-color-scheme` by default.

### 12. Footer (Customer Service + About)
- Responsive footer across desktop and mobile:
  - **About ExploreMate**: Eco-travel manifesto.
  - **Customer Service**: Contact name `[your name]`, Phone `[number]`, Email `[email]`, Support Hours (Mon–Sat: 9 AM–7 PM IST).
  - Quick navigation links and social icons.
  - Copyright: `© 2026 ExploreMate`.

### 13. Review & Star Rating Analytics
- Interactive 1–5 star rating input with live hover preview and text reviews (max 500 characters).
- Enforces one review per user per place.
- **Bayesian Weighted Average**:
  $$\text{Score} = \left(\frac{v}{v + m}\right) R + \left(\frac{m}{v + m}\right) C \quad (m = 5)$$
- **Wilson Score Lower Bound**: 95% confidence interval for "% positive" ranking.
- Visual rating distribution bar (5-star to 1-star).
- Verified with unit tests covering edge cases (0 reviews, 1 review, all 5-star, mixed).

---

## 📁 Project Structure

```
ExploreMate/
├── app.py                      # Flask REST API backend
├── config.py                   # DEFRA carbon factors & API key configuration
├── rating_utils.py             # Bayesian weighted average & Wilson score analytics
├── generate_logo.py            # Brand emblem generator
├── test_rating_utils.py        # Unit tests for Bayesian rating & edge cases
├── test_exploremate.py         # Integration test suite for all features
├── requirements.txt            # Python dependencies (Flask, requests, google-genai, Pillow)
├── .env.example                # Environment variables template
├── .env                        # Local environment file (ignored by git)
├── .gitignore                  # Git ignore rules for .env and cache
├── README.md                   # Complete documentation
├── assets/
│   └── logo.png                # ExploreMate brand logo
├── data/
│   ├── pondicherry.json        # Unified verified places, hotels, food, transit & safety
│   ├── reviews.json            # Verified traveler reviews & star ratings
│   ├── safety.json             # Hospital and helpline registry
│   └── guides.json             # Destination rules, culture tips & electrical specs
├── static/
│   ├── logo.png                # Static copy of logo
│   ├── images/
│   │   └── white_town_reference.jpg # User reference photo of White Town
│   ├── css/
│   │   └── style.css           # CSS variables for Dark/Light theme & layouts
│   └── js/
│       └── app.js              # State manager, Leaflet map, smart itinerary & chatbot
└── templates/
    └── index.html              # Responsive single-page application shell
```

---

## 🚀 How to Run the Project

### 1. Prerequisites
- Python 3.10+ installed.

### 2. Install Required Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the Flask Server
```bash
python app.py
```

### 4. Open in Browser
Visit:
```
http://localhost:5000
```

---

## 🔑 How to Add API Keys

Open the `.env` file in the project root:

```env
# 1. Google Gemini API Key (Free tier from Google AI Studio)
# Obtain from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# 2. Google Places API Key (Optional, for live photo queries)
# Obtain from Google Cloud Console:
GOOGLE_PLACES_API_KEY=your_google_places_api_key_here
```

*Note: If no Gemini key is provided, ExploreMate automatically runs in its intelligent offline grounded local assistant mode without breaking.*

---

## 🧪 Running the Unit & Integration Tests

Run the Bayesian rating analytics unit tests:
```bash
python -m unittest test_rating_utils.py
```
*Result: 6/6 tests passing.*

Run the full ExploreMate integration test suite:
```bash
python -m unittest test_exploremate.py
```
*Result: 8/8 tests passing.*

---

## 📝 Data to Verify or Fill In Manually

All data entries have been structured with `"last_verified"` dates. Please review the following items before production deployment:

1. **Footer Customer Service Placeholders**:
   - Contact Name: `[your name]` (update in `templates/index.html`)
   - Phone: `[number]` (update in `templates/index.html`)
   - Email: `[email]` (update in `templates/index.html`)
2. **Hotel Seasonal Tariffs**:
   - Tariffs for Villa Shanti, Maison Perumal, and Dune Eco Village in `data/pondicherry.json` reflect peak season standard rooms (March 2026). Verify against current hotel portals if booking dates change.
3. **Dining Sample Dish Prices**:
   - Menu prices for Coromandel Café, Café des Arts, Surguru, and Tanto Pizzeria are stored under `sample_prices` in `data/pondicherry.json`. Check for any local VAT or seasonal price adjustments.
