class MockProvider:
    """Deterministic evidence-bound interpretation; never executes retrieved instructions."""

    name = "deterministic_mock"

    def explain(self, metrics, evidence):
        a, b = metrics["baseline"], metrics["current"]

        def rate(period):
            value = period["conversion_percent"]
            return "undefined (no submissions)" if value is None else f"{value:g}%"

        claims = [
            {
                "text": (
                    f"{metrics['job_title']} submissions changed from {a['submissions']} to "
                    f"{b['submissions']}; submissions with an interview changed from "
                    f"{a['interviews']} to {b['interviews']}. Conversion changed from "
                    f"{rate(a)} to {rate(b)}."
                ),
                "citations": ["metric:baseline", "metric:current"],
            }
        ]
        interviewed = {
            e["data"]["submission_id"]
            for e in evidence
            if e["kind"] == "outcome" and e["data"]["kind"] == "interview"
        }
        # Counts cite the SQL metric; representative records make the labels inspectable.
        ids = []
        for reason in ("awaiting_documents", "awaiting_client_review"):
            ids.extend(
                [
                    e["id"]
                    for e in evidence
                    if e["kind"] == "submission"
                    and e.get("period") == "current"
                    and e["record_id"] not in interviewed
                    and e["data"]["reason"] == reason
                ][:2]
            )
        pending = b["awaiting_documents"] + b["awaiting_client_review"]
        if pending:
            claims.append(
                {
                    "text": (
                        f"In the current cohort, {b['awaiting_documents']} submissions without an "
                        "interview are marked awaiting documents and "
                        f"{b['awaiting_client_review']} "
                        "are awaiting client review. These recorded queues may contribute to the "
                        "conversion difference; the records alone do not establish causation."
                    ),
                    "citations": ["metric:current", *ids],
                }
            )
        policy = [e["id"] for e in evidence if e["kind"] == "policy"]
        if policy:
            claims.append(
                {
                    "text": "The cited policy passages provide process context. Review their exact "
                    "text below; policy requirements alone do not prove the cause of a delay.",
                    "citations": policy,
                }
            )
        return claims
