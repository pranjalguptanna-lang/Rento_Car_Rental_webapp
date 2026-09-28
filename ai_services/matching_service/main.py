import re
from typing import List, Optional
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

app = FastAPI(title="Rento AI Natural-Language Vehicle Matching Microservice")

class VehicleMetadata(BaseModel):
    id: int
    make: str
    model: str
    is_ev: bool
    price_per_day: float
    location: Optional[str] = ""
    extras: Optional[List[str]] = []
    description: Optional[str] = ""

class MatchRequest(BaseModel):
    query: str
    vehicles: List[VehicleMetadata]
    top_k: Optional[int] = 5

class VehicleMatchResult(BaseModel):
    vehicle_id: int
    make: str
    model: str
    relevance_score: float
    matched_features: List[str]

    model_config = ConfigDict(from_attributes=True)

class MatchResponse(BaseModel):
    query: str
    matches: List[VehicleMatchResult]

@app.post("/match", response_model=MatchResponse)
def match_vehicles(req: MatchRequest):
    """
    NLP Vehicle Scorer & Matcher:
    Extracts user intent & keywords from free-text query (e.g. 'cheap EV for weekend with child seat in San Francisco')
    and computes weighted relevance scores against candidate vehicle metadata.
    """
    query_lower = req.query.lower()
    
    # Intent extraction
    wants_ev = bool(re.search(r'\b(ev|electric|tesla|nissan leaf|clean energy)\b', query_lower))
    wants_cheap = bool(re.search(r'\b(cheap|budget|affordable|low cost|economy)\b', query_lower))
    wants_luxury = bool(re.search(r'\b(luxury|premium|high end|sports|fast)\b', query_lower))
    
    # Extra features extraction
    extracted_keywords = re.findall(r'\b[a-zA-Z]{3,}\b', query_lower)
    
    results = []
    
    for v in req.vehicles:
        score = 0.0
        matched_features = []
        
        # 1. EV matching
        if wants_ev:
            if v.is_ev or "tesla" in v.make.lower() or "leaf" in v.model.lower():
                score += 35.0
                matched_features.append("EV/Electric")
            else:
                score -= 10.0
        
        # 2. Pricing intent
        if wants_cheap:
            if v.price_per_day <= 80.0:
                score += 25.0
                matched_features.append("Budget-friendly price")
            elif v.price_per_day > 150.0:
                score -= 15.0
                
        if wants_luxury:
            if v.price_per_day >= 120.0:
                score += 25.0
                matched_features.append("Premium/Luxury tier")
                
        # 3. Location matching
        if v.location and v.location.lower() in query_lower:
            score += 25.0
            matched_features.append(f"Location match ({v.location})")
            
        # 4. Keyword & Extras matching
        vehicle_text = f"{v.make} {v.model} {' '.join(v.extras or [])} {v.description or ''}".lower()
        for kw in set(extracted_keywords):
            if kw in ("cheap", "budget", "ev", "electric", "car", "rent", "rental"):
                continue
            if kw in vehicle_text:
                score += 15.0
                matched_features.append(f"Feature match: '{kw}'")
                
        # Baseline relevance if non-negative
        if score <= 0:
            score = 10.0

        results.append(VehicleMatchResult(
            vehicle_id=v.id,
            make=v.make,
            model=v.model,
            relevance_score=round(score, 2),
            matched_features=matched_features
        ))
        
    # Sort descending by relevance score
    results.sort(key=lambda x: x.relevance_score, reverse=True)
    
    return MatchResponse(
        query=req.query,
        matches=results[:req.top_k]
    )
