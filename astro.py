import json
import requests

from config import (
    PROKERALA_CLIENT_ID,
    PROKERALA_CLIENT_SECRET,
    GEOCODE_URL,
    APP_NS,
    redis_client
)


# ==============================
# FULL ASTRO PIPELINE
# ==============================
def run_full_astro_pipeline(details: dict):
    try:
        print("\n================ ASTRO PIPELINE START =================")
        print("INPUT DETAILS:", details)

        user_id = details.get("user_id")
        dob = details.get("dob")
        tob = details.get("tob")
        pob = details.get("pob")

        datetime_str = f"{dob}T{tob}:00+05:30"
        print("DATETIME:", datetime_str)

        # ---------------- GEO ----------------
        print("\n📍 Geocoding...")
        geo_res = requests.get(
            GEOCODE_URL,
            params={"q": pob, "format": "json", "limit": 1},
            headers={"User-Agent": "astro-ai"},
            verify=False
        )

        if geo_res.status_code != 200 or not geo_res.json():
            raise Exception("Geocoding failed")

        lat = geo_res.json()[0]["lat"]
        lon = geo_res.json()[0]["lon"]
        coordinates = f"{lat},{lon}"
        print("📍 Geocode SUCCESS:", coordinates)

        # ---------------- TOKEN ----------------
        print("\n🔑 Fetching Access Token...")
        token_res = requests.post(
            "https://api.prokerala.com/token",
            data={
                "grant_type": "client_credentials",
                "client_id": PROKERALA_CLIENT_ID,
                "client_secret": PROKERALA_CLIENT_SECRET
            },
            verify=False
        )

        if token_res.status_code != 200:
            raise Exception(f"Token Error: {token_res.text}")

        token = token_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("🔑 Token SUCCESS")

        params = {
            "ayanamsa": 1,
            "coordinates": coordinates,
            "datetime": datetime_str
        }

        # ---------------- API CALLS ----------------
        print("\n🪐 Calling Planet API...")
        planet_res = requests.get(
            "https://api.prokerala.com/v2/astrology/planet-position",
            headers=headers, params=params, verify=False
        )
        planet_data = planet_res.json()

        print("🌙 Calling Birth API...")
        birth_res = requests.get(
            "https://api.prokerala.com/v2/astrology/birth-details",
            headers=headers, params=params, verify=False
        )
        birth_data = birth_res.json()

        print("📜 Calling Kundli API...")
        kundli_res = requests.get(
            "https://api.prokerala.com/v2/astrology/kundli/advanced",
            headers=headers, params=params, verify=False
        ).json()

        # ---------------- VALIDATION ----------------
        if "data" not in planet_data:
            raise Exception(f"Planet API Error: {planet_data}")
        if "data" not in birth_data:
            raise Exception(f"Birth API Error: {birth_data}")
        if "data" not in kundli_res:
            raise Exception(f"Kundli API Error: {kundli_res}")

        print("\n✅ ALL API CALLS SUCCESS")

        # ---------------- BUILD & STORE PROFILE ----------------
        print("\n🧠 Building FULL ASTRO PROFILE...")
        profile = build_full_astro_profile(birth_data, planet_data, kundli_res, user_id=user_id)

        if not profile:
            raise Exception("Profile build failed")

        key = f"{APP_NS}:chart:{user_id}"
        redis_client.setex(key, 86400, json.dumps(profile))

        print("\n💾 STORED FULL ASTRO PROFILE")
        print(f"🔑 KEY: {key}")
        print(f"📊 PLANETS: {len(profile['chart']['planets'])}")
        print(f"🧘 YOGA GROUPS: {list(profile['yogas'].keys())}")
        print(f"⏳ DASHA COUNT: {len(profile['dasha']['mahadasha_timeline'])}")
        print("================ ASTRO PIPELINE COMPLETE =================\n")

        return profile

    except Exception as e:
        print("\n❌ ASTRO PIPELINE ERROR:", str(e))
        print("================ ASTRO PIPELINE FAILED =================\n")
        return None


# ==============================
# PROFILE BUILDER
# ==============================
def build_full_astro_profile(birth_data, planet_data, kundli_data, user_id):
    print("\n🚀 BUILDING FULL ASTRO PROFILE")

    try:
        # BIRTH
        b = birth_data["data"]
        birth = {
            "nakshatra": {
                "name": b["nakshatra"]["name"],
                "pada": b["nakshatra"]["pada"],
                "lord": {
                    "name": b["nakshatra"]["lord"]["name"],
                    "vedic": b["nakshatra"]["lord"]["vedic_name"]
                }
            },
            "moon_sign": b["chandra_rasi"]["name"],
            "sun_sign": b["soorya_rasi"]["name"],
            "zodiac": b["zodiac"]["name"],
            "traits": b.get("additional_info", {})
        }
        print("✅ Birth parsed")

        # PLANETS
        planets = {}
        house_map = {}
        lagna = {}

        for p in planet_data["data"]["planet_position"]:
            name = p["name"].lower()

            if name == "ascendant":
                lagna = {
                    "sign": p["rasi"]["name"],
                    "lord": p["rasi"]["lord"]["name"],
                    "degree": round(p["degree"], 2)
                }
                continue

            entry = {
                "house": p["position"],
                "sign": p["rasi"]["name"],
                "sign_lord": p["rasi"]["lord"]["name"],
                "degree": round(p["degree"], 2),
                "longitude": round(p["longitude"], 2),
                "retrograde": p["is_retrograde"]
            }
            planets[name] = entry
            house_map.setdefault(str(p["position"]), []).append(name)

        print("✅ Planets parsed")

        # NODES
        nodes = {
            "rahu": planets.pop("rahu", None),
            "ketu": planets.pop("ketu", None)
        }

        # DOSHA
        dosha = {"mangal": kundli_data["data"]["mangal_dosha"]}
        print("✅ Dosha parsed")

        # YOGAS
        yogas = {}
        for group in kundli_data["data"]["yoga_details"]:
            key = group["name"].lower().split()[0]
            yogas[key] = [
                {
                    "name": y["name"],
                    "active": y["has_yoga"],
                    "description": y["description"]
                }
                for y in group["yoga_list"]
            ]
        print("✅ Yogas parsed")

        # DASHA
        dasha = {
            "current_balance": {
                "lord": kundli_data["data"]["dasha_balance"]["lord"]["name"],
                "remaining": kundli_data["data"]["dasha_balance"]["description"]
            },
            "mahadasha_timeline": [
                {
                    "planet": d["name"],
                    "start": d["start"],
                    "end": d["end"],
                    "antardasha_count": len(d.get("antardasha", []))
                }
                for d in kundli_data["data"]["dasha_periods"][:5]
            ]
        }
        print("✅ Dasha parsed")

        profile = {
            "meta": {"generated_for": user_id},
            "birth": birth,
            "chart": {
                "lagna": lagna,
                "planets": planets,
                "nodes": nodes,
                "house_occupancy": house_map
            },
            "dosha": dosha,
            "yogas": yogas,
            "dasha": dasha
        }

        print("🔥 FULL ASTRO PROFILE READY")
        return profile

    except Exception as e:
        print("❌ ERROR BUILDING ASTRO PROFILE:", str(e))
        return None
