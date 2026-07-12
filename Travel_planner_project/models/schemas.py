from pydantic import BaseModel
from typing import List, Literal, Optional


class TripRequest(BaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    trip_length_days: Optional[int] = None
    travelers: int = 1
    cabin_class: Literal["economy", "premium_economy", "business", "first"] = "economy"
    hotel_pref: Literal["budget", "mid", "luxury", "any"] = "any"
    budget_ceiling_usd: Optional[float] = None
    assumptions: List[str] = []


class FlightOption(BaseModel):
    label: Literal["cheapest", "balanced", "premium"]
    airline: str
    route_summary: str
    layovers: int
    duration: str
    price_estimate_usd: float
    source_note: str


class HotelOption(BaseModel):
    label: Literal["budget", "mid_range", "luxury"]
    name: str
    area: str
    nightly_rate_usd: float
    amenities: List[str]
    source_note: str


class BudgetRange(BaseModel):
    low: float
    mid: float
    high: float


class BudgetEstimate(BaseModel):
    flights_usd: BudgetRange
    hotel_usd: BudgetRange
    food_usd: BudgetRange
    local_transport_usd: BudgetRange
    activities_usd: BudgetRange
    buffer_usd: BudgetRange
    total_usd: BudgetRange
    uncertain_categories: List[str]


class PlanRequest(BaseModel):
    message: str
    partial_params: Optional[dict] = None
    conversation_history: Optional[list[dict]] = None
