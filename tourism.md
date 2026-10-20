
Build a working prototype website called "EcoNav": an adaptive, eco-friendly travel guide. Start with a short plan, then build in the phases below. Make sure each phase runs before starting the next.

TECH
- Python Flask backend + plain HTML/CSS/JavaScript frontend (no heavy frameworks).
- API-first: the backend exposes clean JSON endpoints (/api/...) so a mobile app can reuse them later. Frontend must be responsive and mobile-first.
- API keys in a .env file (provide .env.example). Add a README with run steps.
- If any external API fails, fall back to static data so the demo never breaks.

DATA
- Pondicherry is the fully built destination, using static JSON files: places.json, stay.json, food.json, safety.json, guides.json.
- Each place has: name, interest (heritage / nature / history / shopping), indoor (true/false), image, rating + short review summary, opening hours, lat/long, nearby place ids.
- The app splits all places into two groups, indoor and outdoor. Interest filters sit on top of that split.
- The search bar accepts any city. For Pondicherry use the static data. For other cities, use Open-Meteo geocoding + weather, and show a friendly "full guide coming soon" for places.
- Weather: Open-Meteo (no key needed).

FEATURES
Phase 1: Home + places
- Home page: logo, search bar, 3 interest chips (Heritage, Nature, History).
- Interest filter: Heritage shows the ashram and related places, Nature shows beaches, History shows the French streets.
- Place page: image, rating and review summary, opening hours with an "Open now / Closed" badge, nearby places, and a short mall/shopping section.

Phase 2: Live itinerary + weather pivot
- Time-slotted day itinerary (morning, afternoon, evening) with the forecast for each slot and what to wear.
- If the forecast shows rain or thunderstorm, automatically swap outdoor stops for indoor ones and show a clear banner, e.g. "Rain expected at 3 PM, plan switched to indoor."
- Add a "Simulate rain" toggle for demos.
- When the plan switches, also surface the Stay and Food tabs.

Phase 3: Stay and Food
- Stay: compare 4-5 accommodations by price per night, rating and area (sortable by price).
- Food: must-try restaurants with a one-line description.

Phase 4: Carbon footprint + sustainability
- For any route between two places, show estimated CO2 per mode: walk, cycle, bus, train, car.
- Keep emission factors in one config file, label them "estimates", and cite DEFRA as the source.
- When the user picks the lowest-carbon option, play a confetti animation (canvas-confetti) and show a running "CO2 saved" counter.

Phase 5: Safety, rules and chatbot
- Safety page: nearby hospitals (name, phone, distance) and basic helpline numbers (emergency, ambulance, police, highway). Read them from safety.json only and never invent numbers. Mark sample entries "verify before use".
- "Before you go" page per destination: local rules, culture tips, and electrical plug type and voltage compared with India. Read from guides.json, with a note to verify with official sources.
- Floating chatbot button that calls the Gemini API through the backend. Ground answers in the app's own data, and reply politely if no key is set.

UI/UX
- Dark mode only, clean and uncluttered. It must not feel overwhelming.
- Rules: one main action per screen, card-based layout, generous spacing, show at most 3-4 items per section with a "See more" button, readable font sizes.
- Use an eco-friendly accent colour (teal or green) on a dark background. Pick one distinctive font pairing.
- Use the logo from /static/logo.png in the header.
- Smooth, subtle transitions only.

Output: a runnable project with a clear folder structure and sample data for Pondicherry.
