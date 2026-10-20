/**
 * ExploreMate - Adaptive Eco-Travel Guide & Pondicherry Explorer
 * Core JavaScript Application Controller
 */

// Application State
const state = {
  currentCity: "Pondicherry",
  cityData: null,
  activeTab: "placesTab",
  activeInterest: "all",
  rainSimulated: false,
  co2SavedTotal: parseFloat(localStorage.getItem("exploremate_co2_saved") || "0.0"),
  seeMoreOutdoor: false,
  seeMoreIndoor: false,
  allPlaces: [],
  outdoorPlaces: [],
  indoorPlaces: [],
  currentPlaceModalId: null,
  staySort: "price_asc",
  lastFocusedElement: null,
  mapInstance: null,
  mapMarkers: []
};

// ==========================================
// INITIALIZATION
// ==========================================

document.addEventListener("DOMContentLoaded", () => {
  initThemeToggle();
  initEventListeners();
  updateCo2SavedPill();
  loadCityData("Pondicherry");
});

// ==========================================
// THEME TOGGLE (Task 3 / 11)
// ==========================================

function initThemeToggle() {
  const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
  updateThemeIcon(currentTheme);

  const themeBtn = document.getElementById("themeToggleBtn");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const active = document.documentElement.getAttribute("data-theme") || "dark";
      const nextTheme = active === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", nextTheme);
      localStorage.setItem("exploremate_theme", nextTheme);
      updateThemeIcon(nextTheme);

      // Re-invalidate map size if map initialized
      if (state.mapInstance) {
        state.mapInstance.invalidateSize();
      }
    });
  }
}

function updateThemeIcon(theme) {
  const icon = document.getElementById("themeIcon");
  if (icon) {
    if (theme === "light") {
      icon.className = "fa-solid fa-sun";
      icon.style.color = "#f59e0b";
    } else {
      icon.className = "fa-solid fa-moon";
      icon.style.color = "#f8fafc";
    }
  }
}

// ==========================================
// EVENT LISTENERS
// ==========================================

function initEventListeners() {
  // Brand logo home link
  document.getElementById("brandHomeLink").addEventListener("click", (e) => {
    e.preventDefault();
    document.getElementById("citySearchInput").value = "Pondicherry";
    loadCityData("Pondicherry");
    switchTab("placesTab");
  });

  // Footer home link
  document.getElementById("footerLinkHome").addEventListener("click", (e) => {
    e.preventDefault();
    switchTab("placesTab");
  });

  document.getElementById("footerLinkAbout").addEventListener("click", (e) => {
    e.preventDefault();
    alert("ExploreMate is an adaptive eco-travel prototype built for the ZÉPHYR Hackathon, promoting zero-carbon exploration in Puducherry.");
  });

  document.getElementById("footerLinkPrivacy").addEventListener("click", (e) => {
    e.preventDefault();
    alert("ExploreMate Privacy: All review data is stored locally in demo mode. No tracking cookies used.");
  });

  document.getElementById("footerLinkTerms").addEventListener("click", (e) => {
    e.preventDefault();
    alert("ExploreMate Terms: Travel guidelines and safety helplines are provided for educational and trip planning assistance.");
  });

  // Search form submission (Task 2)
  document.getElementById("searchForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const query = document.getElementById("citySearchInput").value.trim();
    if (query) {
      loadCityData(query);
    }
  });

  // Unsupported city return button
  document.getElementById("returnPondyBtn").addEventListener("click", () => {
    document.getElementById("citySearchInput").value = "Pondicherry";
    loadCityData("Pondicherry");
  });

  // Rain simulation buttons
  document.getElementById("simulateRainToggle").addEventListener("click", toggleRainSimulation);
  const itineraryRainBtn = document.getElementById("toggleRainItineraryBtn");
  if (itineraryRainBtn) {
    itineraryRainBtn.addEventListener("click", toggleRainSimulation);
  }

  // Pivot banner quick action button
  document.getElementById("pivotQuickActionBtn").addEventListener("click", () => {
    switchTab("itineraryTab");
  });

  // Tab navigation buttons
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      switchTab(targetTab);
    });
  });

  // Interest chip filters
  document.querySelectorAll(".chip-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".chip-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.activeInterest = btn.getAttribute("data-interest");
      renderPlacesGrids();
    });
  });

  // See More toggles
  document.getElementById("outdoorSeeMoreBtn").addEventListener("click", () => {
    state.seeMoreOutdoor = !state.seeMoreOutdoor;
    renderPlacesGrids();
  });

  document.getElementById("indoorSeeMoreBtn").addEventListener("click", () => {
    state.seeMoreIndoor = !state.seeMoreIndoor;
    renderPlacesGrids();
  });

  // Stay sorting selector
  document.getElementById("staySortSelect").addEventListener("change", (e) => {
    state.staySort = e.target.value;
    loadStayData();
  });

  // Carbon calculator route selectors
  document.getElementById("carbonFromSelect").addEventListener("change", onCarbonRouteChange);
  document.getElementById("carbonToSelect").addEventListener("change", onCarbonRouteChange);

  // Map Locate Me button
  document.getElementById("locateMeBtn").addEventListener("click", locateUserOnMap);

  // Itinerary Save, Print, Share buttons
  document.getElementById("saveItineraryBtn").addEventListener("click", saveItineraryToLocal);
  document.getElementById("printItineraryBtn").addEventListener("click", () => window.print());
  document.getElementById("shareItineraryBtn").addEventListener("click", shareItinerary);

  // Review Form Character Counter
  const reviewText = document.getElementById("reviewCommentText");
  if (reviewText) {
    reviewText.addEventListener("input", () => {
      document.getElementById("reviewCharCount").innerText = `${reviewText.value.length} / 500`;
    });
  }

  // Review Form Submit (Task 5 / 13)
  document.getElementById("submitReviewForm").addEventListener("submit", handleReviewSubmit);

  // Modal Close & Click outside (Task 3)
  document.getElementById("closePlaceModalBtn").addEventListener("click", closePlaceModal);
  document.getElementById("placeModalOverlay").addEventListener("click", (e) => {
    if (e.target.id === "placeModalOverlay") {
      closePlaceModal();
    }
  });

  // Esc key closes modal & focus trap (Task 3)
  window.addEventListener("keydown", handleModalKeydown);

  // Chatbot floating button and close (Task 10)
  document.getElementById("chatbotTriggerBtn").addEventListener("click", () => {
    const panel = document.getElementById("chatbotPanel");
    panel.classList.toggle("open");
  });

  document.getElementById("closeChatbotBtn").addEventListener("click", () => {
    document.getElementById("chatbotPanel").classList.remove("open");
  });

  document.getElementById("chatForm").addEventListener("submit", handleChatSubmit);
}

// ==========================================
// SEARCH & CITY DATA (Task 2)
// ==========================================

async function loadCityData(cityName) {
  try {
    const res = await fetch(`/api/city?q=${encodeURIComponent(cityName)}`);
    const data = await res.json();
    state.cityData = data;

    const hero = document.getElementById("destinationHero");
    const unsupportedCard = document.getElementById("unsupportedCityCard");
    const mainTabs = ["placesTab", "itineraryTab", "mapTab", "stayTab", "foodTab", "carbonTab", "safetyTab"];

    // STRICT TASK 2:
    // If the city is NOT Pondicherry/Puducherry, do NOT show Pondicherry content!
    if (!data.supported) {
      hero.classList.add("hidden");
      document.querySelector(".nav-tabbar").classList.add("hidden");
      mainTabs.forEach(id => document.getElementById(id).classList.add("hidden"));

      unsupportedCard.classList.remove("hidden");
      document.getElementById("unsupportedCityMessage").innerText = data.message;
      return;
    }

    // Supported: Pondicherry / Puducherry
    unsupportedCard.classList.add("hidden");
    hero.classList.remove("hidden");
    document.querySelector(".nav-tabbar").classList.remove("hidden");
    
    // Switch to active tab (default placesTab)
    switchTab(state.activeTab || "placesTab");

    state.currentCity = data.destination;
    state.allPlaces = data.places.all;
    state.indoorPlaces = data.places.indoor;
    state.outdoorPlaces = data.places.outdoor;

    updateHeroSection(data);
    populateCarbonSelectors(data.places.all);
    renderPlacesGrids();
    loadItineraryData();
    loadStayData();
    loadFoodData();
    loadSafetyData();
    loadTransitHubs(data.transit_hubs);
    initOrUpdateLeafletMap(data.places.all, data.transit_hubs);
    fetchCarbonData();
  } catch (err) {
    console.error("Failed to load city data:", err);
  }
}

function updateHeroSection(data) {
  document.getElementById("heroCityName").innerText = data.destination;
  document.getElementById("heroTagline").innerText = data.tagline;

  if (data.weather && data.weather.current) {
    const curr = data.weather.current;
    document.getElementById("heroWeatherTemp").innerText = `${curr.temperature}°C`;
    document.getElementById("heroWeatherCondition").innerText = curr.weather.description;
    
    const iconElem = document.getElementById("heroWeatherIcon");
    iconElem.className = `fa-solid ${curr.weather.icon} fa-2x text-teal`;
  }
}

// ==========================================
// PLACES & INTEREST FILTERING (Task 1, 4)
// ==========================================

function isOpenNow(openingHours) {
  if (!openingHours || openingHours.open_hour === undefined) return { isOpen: true, label: "Open Now" };
  const currentHour = new Date().getHours();
  const openH = openingHours.open_hour;
  const closeH = openingHours.close_hour;

  if (openH === 0 && closeH === 24) {
    return { isOpen: true, label: "Open 24/7" };
  }

  if (currentHour >= openH && currentHour < closeH) {
    return { isOpen: true, label: "Open Now" };
  } else {
    return { isOpen: false, label: "Closed" };
  }
}

function renderPlacesGrids() {
  const interest = state.activeInterest;

  let filteredOutdoor = state.outdoorPlaces;
  if (interest !== "all") {
    filteredOutdoor = filteredOutdoor.filter(p => p.interest.toLowerCase() === interest);
  }

  let filteredIndoor = state.indoorPlaces;
  if (interest !== "all") {
    filteredIndoor = filteredIndoor.filter(p => p.interest.toLowerCase() === interest);
  }

  document.getElementById("outdoorCountBadge").innerText = `${filteredOutdoor.length} Places`;
  document.getElementById("indoorCountBadge").innerText = `${filteredIndoor.length} Places`;

  const outdoorLimit = state.seeMoreOutdoor ? filteredOutdoor.length : 3;
  const indoorLimit = state.seeMoreIndoor ? filteredIndoor.length : 3;

  renderCardList("outdoorGrid", filteredOutdoor.slice(0, outdoorLimit));
  renderCardList("indoorGrid", filteredIndoor.slice(0, indoorLimit));

  const outdoorMoreBtn = document.getElementById("outdoorSeeMoreBtn");
  const outdoorMoreWrapper = document.getElementById("outdoorSeeMoreWrapper");
  if (filteredOutdoor.length > 3) {
    outdoorMoreWrapper.classList.remove("hidden");
    outdoorMoreBtn.innerHTML = state.seeMoreOutdoor
      ? `<span>Show less</span> <i class="fa-solid fa-chevron-up"></i>`
      : `<span>See more outdoor places (${filteredOutdoor.length - 3} more)</span> <i class="fa-solid fa-chevron-down"></i>`;
  } else {
    outdoorMoreWrapper.classList.add("hidden");
  }

  const indoorMoreBtn = document.getElementById("indoorSeeMoreBtn");
  const indoorMoreWrapper = document.getElementById("indoorSeeMoreWrapper");
  if (filteredIndoor.length > 3) {
    indoorMoreWrapper.classList.remove("hidden");
    indoorMoreBtn.innerHTML = state.seeMoreIndoor
      ? `<span>Show less</span> <i class="fa-solid fa-chevron-up"></i>`
      : `<span>See more indoor places (${filteredIndoor.length - 3} more)</span> <i class="fa-solid fa-chevron-down"></i>`;
  } else {
    indoorMoreWrapper.classList.add("hidden");
  }
}

function renderCardList(containerId, places) {
  const container = document.getElementById(containerId);
  if (places.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; padding: 2rem; text-align: center; color: var(--text-dim); background: var(--bg-card); border-radius: var(--radius-md);">
        No sights found matching "${state.activeInterest}".
      </div>
    `;
    return;
  }

  container.innerHTML = places.map(p => {
    const status = isOpenNow(p.opening_hours);
    const badgeClass = status.isOpen ? "badge-open" : "badge-closed";
    const envBadge = p.indoor 
      ? `<span class="badge badge-indoor"><i class="fa-solid fa-house-chimney"></i> Indoor</span>` 
      : `<span class="badge badge-outdoor"><i class="fa-solid fa-sun"></i> Outdoor</span>`;

    return `
      <article class="place-card" onclick="openPlaceModal('${p.id}')" style="cursor: pointer;" tabindex="0" role="button" aria-label="View details for ${p.name}">
        <div class="card-img-wrapper">
          <img src="${p.image}" alt="${p.name}" class="card-img" loading="lazy">
          <div class="image-credit-tag"><i class="fa-solid fa-camera"></i> ${p.image_credit || 'Verified Photo'}</div>
          <div class="card-badges">
            ${envBadge}
            <span class="badge ${badgeClass}"><i class="fa-solid fa-circle" style="font-size: 6px; vertical-align: middle; margin-right: 3px;"></i>${status.label}</span>
          </div>
        </div>
        <div class="card-body">
          <div class="card-title-row">
            <h3 class="card-title">${p.name}</h3>
            <div class="rating-badge">
              <i class="fa-solid fa-star"></i> ${p.rating}
            </div>
          </div>
          <p class="card-text">${p.review_summary}</p>
          <div class="card-meta">
            <span><i class="fa-regular fa-clock"></i> ${p.opening_hours ? p.opening_hours.display : 'Daily'}</span>
            <span class="text-teal" style="font-weight: 600;">Explore details <i class="fa-solid fa-arrow-right"></i></span>
          </div>
        </div>
      </article>
    `;
  }).join("");
}

// ==========================================
// CENTERED MODAL & REVIEWS (Task 3, 5, 13)
// ==========================================

async function openPlaceModal(placeId) {
  state.currentPlaceModalId = placeId;
  state.lastFocusedElement = document.activeElement;

  try {
    const res = await fetch(`/api/places/${placeId}`);
    const data = await res.json();
    if (data.status !== "success") return;

    const p = data.place;
    const modal = document.getElementById("placeModalOverlay");

    document.getElementById("modalPlaceImg").src = p.image;
    document.getElementById("modalImageCreditTag").innerHTML = `
      <i class="fa-solid fa-camera"></i> ${p.image_credit} · <a href="${p.image_source_url}" target="_blank" rel="noopener noreferrer">${p.image_license}</a>
    `;
    document.getElementById("modalPlaceName").innerText = p.name;
    document.getElementById("modalPlaceRating").innerHTML = `<i class="fa-solid fa-star"></i> <span>${p.rating}</span>`;
    document.getElementById("modalPlaceReviewSummary").innerText = p.review_summary;
    document.getElementById("modalPlaceHours").innerText = p.opening_hours ? p.opening_hours.display : "Daily Opening";

    const status = isOpenNow(p.opening_hours);
    const badgeElem = document.getElementById("modalPlaceOpenBadge");
    badgeElem.innerText = status.label;
    badgeElem.className = `badge ${status.isOpen ? "badge-open" : "badge-closed"}`;

    // Crowd Peak Info
    const crowdBadge = document.getElementById("modalCrowdBadge");
    if (p.crowd_levels) {
      crowdBadge.innerText = `Rush Hours: ${p.crowd_levels.rush_hours}`;
    }

    // Guidelines Box (Task 8)
    const g = p.guidelines || {};
    document.getElementById("modalGuidelinesBox").innerHTML = `
      <h4 style="font-size: 0.95rem; margin-bottom: 0.5rem; color: var(--teal-accent);">
        <i class="fa-solid fa-circle-info"></i> Visitor Guidelines & Rules
      </h4>
      <div style="font-size: 0.84rem; display: grid; gap: 0.35rem; color: var(--text-muted);">
        <div><strong>Dress Code:</strong> ${g.dress_code || 'Casual'}</div>
        <div><strong>Entry Fee:</strong> ${g.entry_fee || 'Free'}</div>
        <div><strong>Photography:</strong> ${g.photography_rules || 'Allowed'}</div>
        <div><strong>Best Time:</strong> ${g.best_time_to_visit || 'Morning'}</div>
        <div><strong>Accessibility:</strong> ${g.accessibility || 'Accessible'}</div>
      </div>
    `;

    // Nearby Attractions
    const nearbyContainer = document.getElementById("modalNearbyList");
    if (p.nearby_places && p.nearby_places.length > 0) {
      nearbyContainer.innerHTML = p.nearby_places.map(n => `
        <span class="nearby-pill" onclick="openPlaceModal('${n.id}')" style="background: rgba(125,125,125,0.1); padding: 0.35rem 0.75rem; border-radius: var(--radius-full); font-size: 0.8rem; cursor: pointer; display: inline-flex; align-items: center; gap: 0.35rem;">
          <i class="fa-solid ${n.indoor ? 'fa-house-chimney text-teal' : 'fa-sun text-emerald'}"></i>
          ${n.name} (★${n.rating})
        </span>
      `).join("");
    } else {
      nearbyContainer.innerHTML = `<span style="color: var(--text-dim); font-size: 0.8rem;">No immediate sights mapped.</span>`;
    }

    // Nearby Restaurants & Accommodations with Distance & Walking Time
    const servicesContainer = document.getElementById("modalNearbyServicesList");
    let servicesHtml = "";
    if (p.nearby_restaurants && p.nearby_restaurants.length > 0) {
      servicesHtml += p.nearby_restaurants.map(r => `
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.3rem 0; border-bottom: 1px solid var(--border-subtle);">
          <div>
            <strong>${r.name}</strong> (${r.cuisine})
            <div style="font-size: 0.78rem; color: var(--teal-accent);"><i class="fa-solid fa-person-walking"></i> ${r.distance_km} km (~${r.walking_minutes} min walk)</div>
          </div>
          <a href="${r.booking_url}" target="_blank" rel="noopener noreferrer" class="see-more-btn" style="padding: 0.2rem 0.6rem; font-size: 0.72rem;">Table</a>
        </div>
      `).join("");
    }
    servicesContainer.innerHTML = servicesHtml || "<span>No immediate dining mapped.</span>";

    // Load and render Bayesian Reviews (Task 5 / 13)
    loadPlaceReviews(placeId);

    // Open Modal and Trap Focus
    modal.classList.add("open");
    document.getElementById("closePlaceModalBtn").focus();
  } catch (err) {
    console.error("Failed to load place details:", err);
  }
}

function closePlaceModal() {
  const modal = document.getElementById("placeModalOverlay");
  modal.classList.remove("open");
  if (state.lastFocusedElement) {
    state.lastFocusedElement.focus();
  }
}

function handleModalKeydown(e) {
  const modal = document.getElementById("placeModalOverlay");
  if (!modal.classList.contains("open")) return;

  // Esc key closes modal (Task 3)
  if (e.key === "Escape") {
    closePlaceModal();
    return;
  }

  // Focus trap inside modal (Task 3)
  if (e.key === "Tab") {
    const dialog = document.getElementById("placeModalDialog");
    const focusable = dialog.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusable.length === 0) return;

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (e.shiftKey) {
      if (document.activeElement === first) {
        last.focus();
        e.preventDefault();
      }
    } else {
      if (document.activeElement === last) {
        first.focus();
        e.preventDefault();
      }
    }
  }
}

// ==========================================
// REVIEWS & BAYESIAN RANKING (Task 5 / 13)
// ==========================================

async function loadPlaceReviews(placeId) {
  try {
    const res = await fetch(`/api/reviews?place_id=${placeId}`);
    const data = await res.json();
    if (data.status !== "success") return;

    const an = data.analytics;
    document.getElementById("modalBayesianScore").innerText = an.bayesian_rating.toFixed(2);
    document.getElementById("modalWilsonScore").innerText = `${an.wilson_positive_score}%`;
    document.getElementById("modalReviewAverage").innerText = an.simple_average.toFixed(1);
    document.getElementById("modalReviewCount").innerText = an.total_reviews;

    // Render 5-to-1 Star Distribution Bar
    const distContainer = document.getElementById("modalRatingDistribution");
    const bk = an.distribution.breakdown;
    distContainer.innerHTML = [5, 4, 3, 2, 1].map(star => `
      <div class="rating-distribution-bar">
        <span style="width: 45px;">${star} star</span>
        <div class="progress-track">
          <div class="progress-fill" style="width: ${bk[star].percentage}%;"></div>
        </div>
        <span style="width: 35px; text-align: right; color: var(--text-dim);">${bk[star].count}</span>
      </div>
    `).join("");

    // Render review items
    const listContainer = document.getElementById("modalReviewsList");
    if (data.reviews.length === 0) {
      listContainer.innerHTML = `<div style="font-size: 0.85rem; color: var(--text-dim); padding: 0.5rem 0;">Be the first verified traveler to leave a review!</div>`;
    } else {
      listContainer.innerHTML = data.reviews.map(r => `
        <div class="review-card-item">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
            <strong>${r.user_name}</strong>
            <span style="color: #facc15; font-size: 0.85rem;">${'★'.repeat(r.rating)}${'☆'.repeat(5 - r.rating)}</span>
          </div>
          <p style="font-size: 0.84rem; color: var(--text-muted); margin-bottom: 0.3rem;">${r.review_text}</p>
          <div style="font-size: 0.74rem; color: var(--text-dim);">${r.date}</div>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error("Failed to load reviews:", err);
  }
}

async function handleReviewSubmit(e) {
  e.preventDefault();
  const placeId = state.currentPlaceModalId;
  const authorName = document.getElementById("reviewAuthorName").value.trim();
  const authorEmail = document.getElementById("reviewAuthorEmail").value.trim();
  const reviewText = document.getElementById("reviewCommentText").value.trim();
  const ratingInput = document.querySelector('input[name="rating"]:checked');

  if (!ratingInput) {
    alert("Please select a star rating between 1 and 5.");
    return;
  }

  const payload = {
    place_id: placeId,
    user_name: authorName,
    user_email: authorEmail,
    rating: parseInt(ratingInput.value),
    review_text: reviewText
  };

  try {
    const res = await fetch("/api/reviews", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();

    if (res.status === 200 && result.status === "success") {
      alert("🎉 Thank you! Your review has been verified and added to the Bayesian ranking.");
      document.getElementById("submitReviewForm").reset();
      document.getElementById("reviewCharCount").innerText = "0 / 500";
      loadPlaceReviews(placeId);
    } else {
      alert(result.message || "Failed to submit review.");
    }
  } catch (err) {
    alert("Connection error while submitting review.");
  }
}

// ==========================================
// LEAFLET MAP & TRANSIT (Task 7)
// ==========================================

function initOrUpdateLeafletMap(places, transitHubs) {
  const mapElement = document.getElementById("mapView");
  if (!mapElement) return;

  // Initialize if not already done
  if (!state.mapInstance && typeof L !== "undefined") {
    state.mapInstance = L.map("mapView").setView([11.9338, 79.8358], 13);

    // OpenStreetMap Free Tile Layer
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19
    }).addTo(state.mapInstance);
  }

  if (!state.mapInstance) return;

  // Clear previous markers
  state.mapMarkers.forEach(m => state.mapInstance.removeLayer(m));
  state.mapMarkers = [];

  // Add Attraction Markers
  places.forEach(p => {
    const marker = L.marker([p.lat, p.long]).addTo(state.mapInstance);
    marker.bindPopup(`
      <div style="font-family: var(--font-body); max-width: 200px;">
        <strong style="font-size: 0.95rem;">${p.name}</strong>
        <div style="font-size: 0.8rem; margin: 0.2rem 0;">★ ${p.rating} · ${p.interest}</div>
        <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 0.4rem;">${p.opening_hours.display}</div>
        <div style="display: flex; gap: 0.4rem;">
          <button onclick="openPlaceModal('${p.id}')" style="padding: 0.25rem 0.5rem; background: #0d9488; color: #fff; border: none; border-radius: 4px; font-size: 0.75rem; cursor: pointer;">Details</button>
          <a href="https://www.google.com/maps/dir/?api=1&destination=${p.lat},${p.long}" target="_blank" rel="noopener noreferrer" style="padding: 0.25rem 0.5rem; background: #059669; color: #fff; border-radius: 4px; font-size: 0.75rem; text-decoration: none;">Directions</a>
        </div>
      </div>
    `);
    state.mapMarkers.push(marker);
  });

  // Add Transit Markers (Railway Station & Bus Stand)
  if (transitHubs) {
    (transitHubs.railway_stations || []).forEach(r => {
      const trainMarker = L.circleMarker([r.lat, r.lon], {
        color: "#e11d48",
        fillColor: "#f43f5e",
        fillOpacity: 0.8,
        radius: 8
      }).addTo(state.mapInstance);
      trainMarker.bindPopup(`<strong>${r.name}</strong><br><span style="font-size:0.8rem;">${r.address}</span><br><a href="${r.booking_url}" target="_blank">IRCTC Booking</a>`);
      state.mapMarkers.push(trainMarker);
    });

    (transitHubs.bus_stands || []).forEach(b => {
      const busMarker = L.circleMarker([b.lat, b.lon], {
        color: "#2563eb",
        fillColor: "#3b82f6",
        fillOpacity: 0.8,
        radius: 8
      }).addTo(state.mapInstance);
      busMarker.bindPopup(`<strong>${b.name}</strong><br><span style="font-size:0.8rem;">${b.address}</span><br><a href="${b.booking_url}" target="_blank">Bus Portal</a>`);
      state.mapMarkers.push(busMarker);
    });
  }

  state.mapInstance.invalidateSize();
}

function locateUserOnMap() {
  if (!navigator.geolocation) {
    alert("Geolocation is not supported by your browser.");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const userLat = pos.coords.latitude;
      const userLon = pos.coords.longitude;

      if (state.mapInstance) {
        state.mapInstance.setView([userLat, userLon], 14);
        const userMarker = L.marker([userLat, userLon]).addTo(state.mapInstance);
        userMarker.bindPopup("<strong>You are here!</strong>").openPopup();
        state.mapMarkers.push(userMarker);
      }

      // Calculate distance to Puducherry Railway Station (11.9304, 79.8306)
      const rDist = haversineDistance(userLat, userLon, 11.9304, 79.8306);
      const bDist = haversineDistance(userLat, userLon, 11.9351, 79.8197);
      alert(`📍 GPS Located! Distance to Puducherry Railway Station: ${rDist} km (~${Math.round((rDist/4.5)*60)} min walk). Distance to New Bus Stand: ${bDist} km.`);
    },
    () => {
      alert("Unable to retrieve your location. Check GPS permissions.");
    }
  );
}

function haversineDistance(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) ** 2;
  return (2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))).toFixed(2);
}

function loadTransitHubs(transitHubs) {
  const container = document.getElementById("transitHubsGrid");
  if (!transitHubs || !container) return;

  const railways = transitHubs.railway_stations || [];
  const buses = transitHubs.bus_stands || [];

  container.innerHTML = [
    ...railways.map(r => `
      <div class="transit-card">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.4rem;">
          <strong><i class="fa-solid fa-train text-rose-500"></i> ${r.name}</strong>
          <span class="badge badge-indoor">${r.code}</span>
        </div>
        <p style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 0.5rem;">${r.address}</p>
        <p style="font-size: 0.78rem; color: var(--text-dim); margin-bottom: 0.6rem;">${r.notes}</p>
        <a href="${r.booking_url}" target="_blank" rel="noopener noreferrer" class="see-more-btn" style="padding: 0.35rem 0.85rem; font-size: 0.78rem;">
          <i class="fa-solid fa-ticket"></i> Book on IRCTC
        </a>
      </div>
    `),
    ...buses.map(b => `
      <div class="transit-card">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.4rem;">
          <strong><i class="fa-solid fa-bus text-teal"></i> ${b.name}</strong>
          <span class="badge badge-outdoor">${b.code}</span>
        </div>
        <p style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 0.5rem;">${b.address}</p>
        <p style="font-size: 0.78rem; color: var(--text-dim); margin-bottom: 0.6rem;">${b.notes}</p>
        <a href="${b.booking_url}" target="_blank" rel="noopener noreferrer" class="see-more-btn" style="padding: 0.35rem 0.85rem; font-size: 0.78rem;">
          <i class="fa-solid fa-ticket"></i> Book Bus Ticket
        </a>
      </div>
    `)
  ].join("");
}

// ==========================================
// SMART ITINERARY BUILDER (Task 9)
// ==========================================

async function loadItineraryData() {
  try {
    const res = await fetch(`/api/itinerary?rain_simulated=${state.rainSimulated}&_t=${Date.now()}`);
    const data = await res.json();
    if (data.status !== "success") return;

    renderSmartTimeline(data);
    handlePivotBanner(data);
  } catch (err) {
    console.error("Failed to load itinerary data:", err);
  }
}

function renderSmartTimeline(data) {
  const container = document.getElementById("itineraryTimelineList");
  if (!container) return;

  container.innerHTML = data.stops.map((stop, idx) => {
    const p = stop.place || {};
    const crowdClass = stop.crowd_level === "High" ? "crowd-badge-high" : (stop.crowd_level === "Medium" ? "crowd-badge-medium" : "crowd-badge-low");
    const food = stop.suggested_food || {};
    const rest = food.restaurant || {};
    const leg = stop.leg_to_next;

    return `
      <div class="timeline-item" data-stop-slot="${stop.slot}">
        <div class="timeline-marker">${idx + 1}</div>
        
        <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1.15rem; box-shadow: var(--shadow-card);">
          <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.4rem;">
            <div>
              <span class="badge ${crowdClass}"><i class="fa-solid fa-users"></i> ${stop.crowd_level} Crowd</span>
              <span style="font-size: 0.82rem; font-weight: 700; color: var(--teal-accent); margin-left: 0.4rem;">${stop.label}</span>
            </div>
            <div style="display: flex; gap: 0.4rem; align-items: center;">
              <span class="badge ${stop.indoor ? 'badge-indoor' : 'badge-open'}">
                <i class="fa-solid ${stop.indoor ? 'fa-house-chimney' : 'fa-sun'}"></i> ${stop.indoor ? 'Indoor' : 'Outdoor'}
              </span>
              <span class="badge ${stop.swapped ? 'swapped-badge' : 'badge-open'}">${stop.swapped ? 'Swapped to indoor: rain' : 'Scheduled'}</span>
            </div>
          </div>

          <h3 style="font-size: 1.15rem; margin-bottom: 0.3rem;">${p.name || stop.title}</h3>

          ${stop.swapped ? `
            <div style="margin-bottom: 0.5rem; font-size: 0.8rem; color: #b45309; background: rgba(245, 158, 11, 0.12); padding: 0.4rem 0.65rem; border-radius: var(--radius-sm); border-left: 3px solid #f59e0b;">
              <strong>Swapped from:</strong> <span style="text-decoration: line-through;">${stop.original_place}</span> · <em>${stop.swap_reason}</em>
            </div>
          ` : ''}

          <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.6rem;">${stop.tip}</p>

          ${stop.is_rush_hour ? `
            <div class="rush-warning-strip">
              <i class="fa-solid fa-triangle-exclamation"></i> Rush Hour Alert: Peak tourist density expected during this slot. Consider visiting earlier.
            </div>
          ` : ''}

          <!-- Suggested Meal Slot -->
          ${rest.name ? `
            <div style="margin-top: 0.75rem; padding: 0.6rem 0.85rem; background: var(--bg-card-subtle); border-radius: var(--radius-sm); border-left: 3px solid var(--teal-accent); font-size: 0.82rem;">
              <strong><i class="fa-solid fa-utensils text-teal"></i> ${food.meal}: ${rest.name}</strong> (${rest.cuisine})
              <div style="color: var(--text-dim); margin-top: 0.2rem;">${food.timing_note} · <a href="${rest.booking_url}" target="_blank" rel="noopener noreferrer">View Menu / Reserve</a></div>
            </div>
          ` : ''}

          <div style="margin-top: 0.75rem; display: flex; align-items: center; justify-content: space-between; font-size: 0.8rem; color: var(--text-dim);">
            <span><i class="fa-solid fa-shirt text-emerald"></i> ${stop.clothing}</span>
            <button onclick="openPlaceModal('${p.id}')" class="see-more-btn" style="padding: 0.25rem 0.75rem; font-size: 0.75rem;">View Spot</button>
          </div>
        </div>

        ${idx < data.stops.length - 1 && leg ? `
          <div class="timeline-transit-gap" style="display: flex; flex-direction: column; align-items: center; gap: 0.35rem; margin: 0.75rem 0;">
            <i class="fa-solid fa-arrow-down text-teal"></i>
            <div style="width: 100%; max-width: 580px; background: var(--bg-card-subtle); border: 1px dashed var(--border-subtle); border-radius: var(--radius-sm); padding: 0.65rem 0.95rem; font-size: 0.8rem;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                <span><strong>Leg:</strong> ${p.name} &rarr; ${data.stops[idx + 1].place.name}</span>
                <span class="text-teal" style="font-weight: 700;"><i class="fa-solid fa-route"></i> ${leg.distance_text} (estimated)</span>
              </div>
              <div style="display: flex; gap: 0.75rem; flex-wrap: wrap; color: var(--text-muted); font-size: 0.76rem;">
                <span><i class="fa-solid fa-person-walking"></i> Walk: ${leg.travel_times.walk_min} min ${leg.walk_recommended ? '' : '<strong style="color: #e11d48;">(Not recommended on foot)</strong>'}</span>
                <span><i class="fa-solid fa-bicycle"></i> Cycle: ${leg.travel_times.cycle_min} min</span>
                <span><i class="fa-solid fa-car"></i> Car: ${leg.travel_times.car_min} min</span>
                <span><i class="fa-solid fa-bus"></i> Bus: ~${leg.travel_times.bus_min} min (estimated)</span>
              </div>
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }).join("");
}


function handlePivotBanner(data) {
  const banner = document.getElementById("pivotAlertBanner");
  const stayBtn = document.getElementById("navStayBtn");
  const foodBtn = document.getElementById("navFoodBtn");

  if (data.is_pivoted) {
    banner.classList.remove("hidden");
    document.getElementById("pivotBannerTitle").innerText = "Weather Adaptation Active";
    document.getElementById("pivotBannerText").innerText = data.banner_message;
    stayBtn.classList.add("highlight-surfaced");
    foodBtn.classList.add("highlight-surfaced");
  } else {
    banner.classList.add("hidden");
    stayBtn.classList.remove("highlight-surfaced");
    foodBtn.classList.remove("highlight-surfaced");
  }
}

function toggleRainSimulation() {
  state.rainSimulated = !state.rainSimulated;
  const toggleBtn = document.getElementById("simulateRainToggle");
  const toggleText = document.getElementById("rainToggleText");
  const itineraryRainBtn = document.getElementById("toggleRainItineraryBtn");

  if (state.rainSimulated) {
    toggleBtn.classList.add("active");
    toggleText.innerText = "Simulating Rain (Active)";
    if (itineraryRainBtn) itineraryRainBtn.classList.add("active");
  } else {
    toggleBtn.classList.remove("active");
    toggleText.innerText = "Simulate Rain";
    if (itineraryRainBtn) itineraryRainBtn.classList.remove("active");
  }

  loadItineraryData();
}

function saveItineraryToLocal() {
  localStorage.setItem("exploremate_saved_itinerary", JSON.stringify({
    date: new Date().toISOString(),
    rain_pivoted: state.rainSimulated
  }));
  alert("💾 Itinerary successfully saved to your browser! Accessible anytime.");
}

function shareItinerary() {
  if (navigator.share) {
    navigator.share({
      title: "ExploreMate Pondicherry Itinerary",
      text: "Check out my eco-friendly, weather-adaptive itinerary for Puducherry on ExploreMate!",
      url: window.location.href
    }).catch(() => {});
  } else {
    navigator.clipboard.writeText(window.location.href);
    alert("📋 Itinerary link copied to your clipboard!");
  }
}

// ==========================================
// STAY & FOOD (Tasks 5, 6)
// ==========================================

async function loadStayData() {
  try {
    const res = await fetch(`/api/stay?sort=${state.staySort}`);
    const data = await res.json();
    if (data.status !== "success") return;

    const container = document.getElementById("stayCardsGrid");
    container.innerHTML = data.accommodations.map(s => `
      <article class="stay-card">
        <div class="card-img-wrapper" style="height: 180px;">
          <img src="${s.image}" alt="${s.name}" class="card-img" loading="lazy">
          <div class="image-credit-tag"><i class="fa-solid fa-camera"></i> ${s.image_credit}</div>
          <div class="card-badges">
            <span class="badge badge-indoor"><i class="fa-solid fa-leaf"></i> Eco-Stay</span>
            <div class="rating-badge">
              <i class="fa-solid fa-star"></i> ${s.rating}
            </div>
          </div>
        </div>
        <div class="card-body">
          <div class="card-title-row">
            <h3 class="card-title">${s.name}</h3>
          </div>
          <div style="font-size: 0.82rem; color: var(--teal-accent); margin-bottom: 0.3rem;">
            <i class="fa-solid fa-location-dot"></i> ${s.area}
          </div>
          <p class="card-text">${s.description}</p>
          <div style="font-size: 0.78rem; color: var(--emerald-accent); background: rgba(16,185,129,0.1); padding: 0.35rem 0.6rem; border-radius: var(--radius-sm); margin-bottom: 0.8rem;">
            <i class="fa-solid fa-seedling"></i> ${s.eco_badge}
          </div>
          <div class="card-meta">
            <div>
              <span style="font-size: 1.2rem; font-weight: 800; color: var(--text-main);">₹${s.price_per_night.toLocaleString()}</span>
              <span style="font-size: 0.75rem; color: var(--text-dim);"> / night (verified ${s.last_verified})</span>
            </div>
            <a href="${s.booking_url}" target="_blank" rel="noopener noreferrer" class="see-more-btn" style="padding: 0.35rem 0.9rem;">
              Book Now <i class="fa-solid fa-arrow-up-right-from-square"></i>
            </a>
          </div>
        </div>
      </article>
    `).join("");
  } catch (err) {
    console.error("Failed to load stay data:", err);
  }
}

async function loadFoodData() {
  try {
    const res = await fetch("/api/food");
    const data = await res.json();
    if (data.status !== "success") return;

    const container = document.getElementById("foodCardsGrid");
    container.innerHTML = data.restaurants.map(f => {
      const prices = f.sample_prices || {};
      const sampleItems = Object.entries(prices)
        .filter(([k]) => k !== "currency" && k !== "last_verified")
        .map(([k, v]) => `${k.replace(/_/g, ' ')}: ₹${v}`)
        .join(' · ');

      return `
        <article class="food-card">
          <div class="card-img-wrapper" style="height: 170px;">
            <img src="${f.image}" alt="${f.name}" class="card-img" loading="lazy">
            <div class="image-credit-tag"><i class="fa-solid fa-camera"></i> ${f.image_credit}</div>
            <div class="card-badges">
              <span class="badge badge-outdoor">${f.cuisine}</span>
              <div class="rating-badge">
                <i class="fa-solid fa-star"></i> ${f.rating}
              </div>
            </div>
          </div>
          <div class="card-body">
            <div class="card-title-row">
              <h3 class="card-title">${f.name}</h3>
            </div>
            <div style="font-size: 0.82rem; color: var(--text-dim); margin-bottom: 0.3rem;">
              <i class="fa-solid fa-location-dot"></i> ${f.area} · <i class="fa-regular fa-clock"></i> ${f.opening_hours.display}
            </div>
            <p class="card-text">${f.description}</p>
            <div style="font-size: 0.78rem; color: var(--text-muted); background: var(--bg-card-subtle); padding: 0.35rem 0.6rem; border-radius: var(--radius-sm); margin-bottom: 0.75rem;">
              <strong>Sample Prices:</strong> ${sampleItems || 'Verified ₹ prices available'}
            </div>
            <div class="card-meta">
              <span style="font-size: 0.75rem; color: var(--text-dim);"><i class="fa-solid fa-phone"></i> ${f.phone}</span>
              <a href="${f.booking_url}" target="_blank" rel="noopener noreferrer" class="see-more-btn" style="padding: 0.3rem 0.85rem; font-size: 0.78rem;">
                Reserve Table <i class="fa-solid fa-arrow-up-right-from-square"></i>
              </a>
            </div>
          </div>
        </article>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to load food data:", err);
  }
}

// ==========================================
// CARBON ROUTE & NEARBY DINING (Tasks 4, 5)
// ==========================================

function populateCarbonSelectors(places) {
  const fromSelect = document.getElementById("carbonFromSelect");
  const toSelect = document.getElementById("carbonToSelect");

  const optionsHtml = places.map((p, idx) => `
    <option value="${p.id}" ${idx === 0 ? "selected" : ""}>${p.name}</option>
  `).join("");

  const toOptionsHtml = places.map((p, idx) => `
    <option value="${p.id}" ${idx === 2 ? "selected" : ""}>${p.name}</option>
  `).join("");

  fromSelect.innerHTML = optionsHtml;
  toSelect.innerHTML = toOptionsHtml;
}

function onCarbonRouteChange() {
  fetchCarbonData();
  fetchRouteRestaurants();
}

async function fetchCarbonData() {
  const fromId = document.getElementById("carbonFromSelect").value;
  const toId = document.getElementById("carbonToSelect").value;

  try {
    const res = await fetch(`/api/carbon?from_id=${fromId}&to_id=${toId}`);
    const data = await res.json();
    if (data.status !== "success") return;

    renderCarbonModes(data);
    fetchRouteRestaurants();
  } catch (err) {
    console.error("Failed to load carbon calculation:", err);
  }
}

function renderCarbonModes(data) {
  document.getElementById("calcDistanceDisplay").innerText = `${data.route.distance_km} km`;
  document.getElementById("calcBaselineCarDisplay").innerText = `${data.baseline_car_co2_kg} kg CO2`;
  document.getElementById("defraCitationText").innerText = `${data.source_citation}. Label: ${data.label}.`;

  const container = document.getElementById("carbonModesGrid");
  container.innerHTML = data.modes.map(m => `
    <div class="mode-card ${m.is_lowest_carbon ? 'is-lowest' : ''}">
      <div>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
          <div class="mode-icon-circle">
            <i class="fa-solid ${m.icon}"></i>
          </div>
          <span class="badge ${m.is_lowest_carbon ? 'badge-open' : 'badge-indoor'}">${m.badge}</span>
        </div>
        <h4 style="font-size: 1.1rem; margin-bottom: 0.2rem;">${m.name}</h4>
        <div style="font-size: 0.8rem; color: var(--text-dim); margin-bottom: 0.8rem;">
          Est. Travel Time: <strong>~${m.estimated_minutes} min</strong>
        </div>
        <div style="display: flex; align-items: baseline; gap: 0.4rem; margin-bottom: 0.5rem;">
          <span class="mode-emission-val">${m.co2_kg}</span>
          <span style="font-size: 0.82rem; color: var(--text-muted);">kg CO2e (${data.label})</span>
        </div>
        <div style="font-size: 0.78rem; color: ${m.co2_saved_vs_car_kg > 0 ? 'var(--emerald-accent)' : 'var(--text-dim)'};">
          ${m.co2_saved_vs_car_kg > 0 ? `<i class="fa-solid fa-arrow-down"></i> Saves ${m.co2_saved_vs_car_kg} kg vs car` : 'Reference vehicle'}
        </div>
      </div>
      <button class="choose-mode-btn" onclick="selectTransitMode('${m.mode}', ${m.co2_saved_vs_car_kg}, ${m.is_lowest_carbon})">
        ${m.is_lowest_carbon ? '<i class="fa-solid fa-award"></i> Choose Lowest Carbon' : 'Select Transit Mode'}
      </button>
    </div>
  `).join("");
}

function selectTransitMode(modeKey, savedKg, isLowest) {
  if (isLowest) {
    if (typeof confetti === "function") {
      confetti({
        particleCount: 90,
        spread: 80,
        origin: { y: 0.65 },
        colors: ["#10b981", "#14b8a6", "#34d399", "#2dd4bf"]
      });
    }

    state.co2SavedTotal += (savedKg > 0 ? savedKg : 0.85);
    localStorage.setItem("exploremate_co2_saved", state.co2SavedTotal.toFixed(2));
    updateCo2SavedPill();

    alert(`🎉 Brilliant eco choice! You chose zero-carbon transit and saved ${savedKg} kg of CO2 on this route!`);
  } else {
    alert(`Transit option selected. Consider walking or cycling for zero-carbon emissions!`);
  }
}

function updateCo2SavedPill() {
  const display = document.getElementById("globalCo2SavedDisplay");
  if (display) {
    display.innerText = state.co2SavedTotal.toFixed(2);
  }
}

async function fetchRouteRestaurants() {
  const fromId = document.getElementById("carbonFromSelect").value;
  const toId = document.getElementById("carbonToSelect").value;

  try {
    const res = await fetch(`/api/restaurants/near-route?place1=${fromId}&place2=${toId}`);
    const data = await res.json();
    if (data.status !== "success") return;

    const grid = document.getElementById("routeRestaurantsGrid");
    grid.innerHTML = data.restaurants.slice(0, 3).map(r => `
      <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 0.85rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
          <strong>${r.name}</strong>
          <span style="font-size: 0.8rem; color: #facc15;">★ ${r.rating}</span>
        </div>
        <div style="font-size: 0.8rem; color: var(--teal-accent); margin-bottom: 0.4rem;">
          <i class="fa-solid fa-route"></i> Avg distance: ${r.average_distance_km} km
        </div>
        <p style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 0.5rem;">${r.description}</p>
        <a href="${r.booking_url}" target="_blank" rel="noopener noreferrer" class="see-more-btn" style="padding: 0.2rem 0.6rem; font-size: 0.72rem;">Table Details</a>
      </div>
    `).join("");
  } catch (err) {
    console.error("Failed to load route restaurants:", err);
  }
}

// ==========================================
// "BEFORE YOU GO" & SAFETY (Task 8)
// ==========================================

async function loadSafetyData() {
  try {
    const res = await fetch("/api/safety");
    const data = await res.json();
    if (data.status !== "success") return;

    const safety = data.data;
    const official = data.official_numbers || {};

    // Helplines Grid
    document.getElementById("helplinesGrid").innerHTML = `
      <div class="place-card" style="padding: 1.1rem;">
        <div style="display: flex; justify-content: space-between;"><strong>Police Control Room</strong><span class="badge badge-warning">verified</span></div>
        <div style="font-size: 1.4rem; font-weight: 800; color: var(--teal-accent); margin: 0.4rem 0;"><a href="tel:${official.police || '100'}">📞 ${official.police || '100'}</a></div>
        <p style="font-size: 0.8rem; color: var(--text-dim);">Puducherry Police 24/7 Dispatch</p>
      </div>
      <div class="place-card" style="padding: 1.1rem;">
        <div style="display: flex; justify-content: space-between;"><strong>Ambulance Emergency</strong><span class="badge badge-warning">verified</span></div>
        <div style="font-size: 1.4rem; font-weight: 800; color: var(--teal-accent); margin: 0.4rem 0;"><a href="tel:${official.ambulance || '108'}">📞 ${official.ambulance || '108'}</a></div>
        <p style="font-size: 0.8rem; color: var(--text-dim);">Toll-free Medical Ambulance</p>
      </div>
      <div class="place-card" style="padding: 1.1rem;">
        <div style="display: flex; justify-content: space-between;"><strong>Fire & Rescue</strong><span class="badge badge-warning">verified</span></div>
        <div style="font-size: 1.4rem; font-weight: 800; color: var(--teal-accent); margin: 0.4rem 0;"><a href="tel:${official.fire || '101'}">📞 ${official.fire || '101'}</a></div>
        <p style="font-size: 0.8rem; color: var(--text-dim);">Disaster & Fire Rescue</p>
      </div>
      <div class="place-card" style="padding: 1.1rem;">
        <div style="display: flex; justify-content: space-between;"><strong>Women Helpline</strong><span class="badge badge-warning">verified</span></div>
        <div style="font-size: 1.4rem; font-weight: 800; color: var(--teal-accent); margin: 0.4rem 0;"><a href="tel:${official.women_helpline || '1091'}">📞 ${official.women_helpline || '1091'}</a></div>
        <p style="font-size: 0.8rem; color: var(--text-dim);">24/7 Safety & Assistance for Women</p>
      </div>
      <div class="place-card" style="padding: 1.1rem;">
        <div style="display: flex; justify-content: space-between;"><strong>Tourist Police Desk</strong><span class="badge badge-warning">verified</span></div>
        <div style="font-size: 1.4rem; font-weight: 800; color: var(--teal-accent); margin: 0.4rem 0;"><a href="tel:${official.tourist_helpline || '1363'}">📞 ${official.tourist_helpline || '1363'}</a></div>
        <p style="font-size: 0.8rem; color: var(--text-dim);">National & UT Tourist Assistance</p>
      </div>
      <div class="place-card" style="padding: 1.1rem;">
        <div style="display: flex; justify-content: space-between;"><strong>Puducherry Tourism HQ</strong><span class="badge badge-warning">verified</span></div>
        <div style="font-size: 1.4rem; font-weight: 800; color: var(--teal-accent); margin: 0.4rem 0;"><a href="tel:${official.puducherry_tourism || '+914132234500'}">📞 ${official.puducherry_tourism || '+91 413 2234500'}</a></div>
        <p style="font-size: 0.8rem; color: var(--text-dim);">Department of Tourism Official Desk</p>
      </div>
    `;

    // Hospitals Grid
    document.getElementById("hospitalsGrid").innerHTML = safety.hospitals.map(h => `
      <div class="place-card" style="padding: 1.1rem;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem;">
          <h4 style="font-size: 1rem;">${h.name}</h4>
          <span class="badge badge-warning">${h.badge}</span>
        </div>
        <div style="font-size: 0.85rem; color: var(--emerald-accent); margin: 0.35rem 0;">
          <i class="fa-solid fa-location-arrow"></i> ${h.distance}
        </div>
        <p style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 0.6rem;">${h.address}</p>
        <div style="font-size: 0.9rem; font-weight: 700;">
          <a href="tel:${h.phone}"><i class="fa-solid fa-phone"></i> ${h.phone}</a>
        </div>
      </div>
    `).join("");

    // Place Guidelines Grid
    if (state.allPlaces && state.allPlaces.length > 0) {
      document.getElementById("placeGuidelinesGrid").innerHTML = state.allPlaces.map(p => {
        const g = p.guidelines || {};
        return `
          <div class="place-card" style="padding: 1.15rem;">
            <h4 style="font-size: 1.05rem; margin-bottom: 0.4rem; color: var(--teal-accent);">
              ${p.name}
            </h4>
            <div style="font-size: 0.84rem; display: grid; gap: 0.35rem; color: var(--text-muted);">
              <div><strong>Timings:</strong> ${g.timings || p.opening_hours.display}</div>
              <div><strong>Dress Code:</strong> ${g.dress_code || 'Casual'}</div>
              <div><strong>Entry Fee:</strong> ${g.entry_fee || 'Free'}</div>
              <div><strong>Photography:</strong> ${g.photography_rules || 'Permitted'}</div>
              <div><strong>Avoid:</strong> ${g.things_to_avoid || 'Littering'}</div>
              <div><strong>Accessibility:</strong> ${g.accessibility || 'Accessible'}</div>
            </div>
          </div>
        `;
      }).join("");
    }
  } catch (err) {
    console.error("Failed to load safety data:", err);
  }
}

// ==========================================
// GEMINI CHATBOT INTERACTION (Task 10)
// ==========================================

async function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("chatInput");
  const msg = input.value.trim();
  if (!msg) return;

  const messagesContainer = document.getElementById("chatMessages");

  const userBubble = document.createElement("div");
  userBubble.className = "chat-bubble user";
  userBubble.innerText = msg;
  messagesContainer.appendChild(userBubble);

  input.value = "";
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  const loadingBubble = document.createElement("div");
  loadingBubble.className = "chat-bubble assistant";
  loadingBubble.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ExploreMate is thinking...`;
  messagesContainer.appendChild(loadingBubble);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: msg,
        itinerary_stops: state.allPlaces ? state.allPlaces.map(p => p.id) : []
      })
    });
    const data = await res.json();
    loadingBubble.remove();

    const assistantBubble = document.createElement("div");
    assistantBubble.className = "chat-bubble assistant";
    assistantBubble.innerText = data.reply || "Sorry, I couldn't process that query.";
    messagesContainer.appendChild(assistantBubble);

    // If chatbot issued an itinerary action (Task 10)
    if (data.itinerary_action) {
      handleChatbotItineraryAction(data.itinerary_action);
    }

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  } catch (err) {
    loadingBubble.remove();
    const errorBubble = document.createElement("div");
    errorBubble.className = "chat-bubble assistant";
    errorBubble.innerText = "ExploreMate assistant offline. Local verified guides remain available.";
    messagesContainer.appendChild(errorBubble);
  }
}

function handleChatbotItineraryAction(action) {
  if (!action || !action.place_id) return;
  alert(`✨ Itinerary Updated by ExploreMate AI: Action "${action.action}" applied for spot ${action.place_id} in slot ${action.slot}!`);
  loadItineraryData();
}

// ==========================================
// TAB SWITCHING UTILITY
// ==========================================

function switchTab(tabId) {
  state.activeTab = tabId;

  document.querySelectorAll(".tab-btn").forEach(btn => {
    if (btn.getAttribute("data-tab") === tabId) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  document.querySelectorAll(".tab-page").forEach(page => {
    if (page.id === tabId) {
      page.classList.remove("hidden");
    } else {
      page.classList.add("hidden");
    }
  });

  // Invalidate map size if switching to Map Tab
  if (tabId === "mapTab" && state.mapInstance) {
    setTimeout(() => {
      state.mapInstance.invalidateSize();
    }, 200);
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}
