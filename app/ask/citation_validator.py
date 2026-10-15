def validate_citations(claims, evidence):
    authorized = {entry["id"] for entry in evidence}
    for claim in claims:
        if not claim.get("citations") or not set(claim["citations"]).issubset(authorized):
            raise ValueError("Provider returned a citation outside the authorized evidence set.")
