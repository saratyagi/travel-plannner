import json
from datetime import datetime

from agents.base import run_agent
from models.schemas import TripRequest

REPORT_SYSTEM = """You are a travel writing expert. Assemble a polished markdown travel plan from the structured data provided.

You will be given a USD→INR exchange rate. Show ALL prices in Indian Rupees (₹) as the primary currency, with the USD amount in brackets.
Use Indian number formatting: ₹1,05,000 not ₹105,000. Round INR to the nearest hundred.

Follow this EXACT format:

# Trip Plan: {Origin} → {Destination}
**Dates:** {start_date} – {end_date} ({nights} nights) | **Travelers:** {travelers}

## ✈️ Flight Options
| Option | Airline | Route | Duration | Price (est.) |
|---|---|---|---|---|
| 1 (Cheapest) | ... | ... | ... | ₹... (~$...) |
| 2 (Balanced) | ... | ... | ... | ₹... (~$...) |
| 3 (Premium) | ... | ... | ... | ₹... (~$...) |

## 🏨 Hotel Options
| Option | Name | Area | Nightly Rate | Notes |
|---|---|---|---|---|
| 1 (Budget) | ... | ... | ₹.../night (~$...) | amenities |
| 2 (Mid-range) | ... | ... | ₹.../night (~$...) | amenities |
| 3 (Luxury) | ... | ... | ₹.../night (~$...) | amenities |

## 💰 Estimated Budget
| Category | Low | Mid | High |
|---|---|---|---|
| Flights | ₹... | ₹... | ₹... |
| Hotel | ₹... | ₹... | ₹... |
| Food | ₹... | ₹... | ₹... |
| Local Transport | ₹... | ₹... | ₹... |
| Activities | ₹... | ₹... | ₹... |
| Buffer (10%) | ₹... | ₹... | ₹... |
| **Total** | **₹...** | **₹...** | **₹...** |

*Exchange rate used: 1 USD = ₹{rate} (live rate)*

## ✅ Final Recommendation
[Recommend one specific flight + hotel combo. State the total mid-range cost in ₹ (and USD). Explain the choice in 2–3 sentences.]

Rules:
- If budget_ceiling_usd is set and mid total exceeds it, add a ⚠️ **Budget Warning** before Final Recommendation
- Return ONLY the markdown — no preamble, no closing remarks"""


async def generate_report(
    trip: TripRequest, flights: list, hotels: list, budget: dict, inr_rate: float = 84.0
) -> str:
    try:
        nights = (
            datetime.strptime(trip.end_date, "%Y-%m-%d")
            - datetime.strptime(trip.start_date, "%Y-%m-%d")
        ).days
    except Exception:
        nights = 7

    system = REPORT_SYSTEM.replace("{rate}", f"{inr_rate:.2f}")

    assumptions_note = ""
    if trip.assumptions:
        assumptions_note = f"\nAssumptions applied: {'; '.join(trip.assumptions)}\n"

    prompt = (
        f"Generate the travel report from this data.\n"
        f"Exchange rate: 1 USD = ₹{inr_rate:.2f}\n"
        f"{assumptions_note}\n"
        f"TripRequest:\n{json.dumps({**trip.dict(), 'nights': nights}, indent=2)}\n\n"
        f"FlightOptions:\n{json.dumps(flights, indent=2)}\n\n"
        f"HotelOptions:\n{json.dumps(hotels, indent=2)}\n\n"
        f"BudgetEstimate:\n{json.dumps(budget, indent=2)}\n\n"
        f"If any assumptions were applied, add a line '*Assumed: [assumption list]*' directly under the trip header."
    )

    return await run_agent(system, prompt, use_tools=False, max_tokens=4096, fast=True, agent_name="report")
