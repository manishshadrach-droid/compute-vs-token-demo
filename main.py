import random
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI(title="Token vs NCU Demo")

MAX_NCU_BUDGET = 15

MODEL_PROFILES: dict[str, dict[str, float]] = {
    "chatgpt": {"token_multiplier": 1.00, "ncu_weight": 1.00},
    "claude": {"token_multiplier": 1.03, "ncu_weight": 1.04},
    "gemini": {"token_multiplier": 0.97, "ncu_weight": 0.98},
}

MODEL_LABELS: dict[str, str] = {
    "chatgpt": "ChatGPT 5.2",
    "claude": "Claude 3.x",
    "gemini": "Gemini 3.0",
}

QUERY_PRESETS: dict[str, str] = {
    "simple": "Summarize this paragraph in one sentence.",
    "average": "Explain how APIs work with an example.",
    "multi": "Compare REST vs GraphQL and give use cases.",
    "agentic": "Plan a trip with budget, tools, and alternatives.",
}

QUERY_LABELS: dict[str, str] = {
    "simple": "Simple query",
    "average": "Average query",
    "multi": "Multi-step workflow",
    "agentic": "Agentic workflow",
}

SCENARIO_LABELS: dict[str, str] = {
    "A": "Similar tokens vs different compute",
    "B": "Different tokens vs similar compute",
}


def calculate_ncu(model_calls: int, retries: int, tool_calls: int, branching: int, latency_factor: float, ncu_weight: float) -> float:
    base = (
        model_calls * 1.2 +
        retries * 0.8 +
        tool_calls * 1.0 +
        branching * 0.9 +
        latency_factor * 0.5
    )

    # Normalization → makes NCU efficient as complexity increases
    normalization = 1 / (1 + (retries * 0.2 + tool_calls * 0.2 + branching * 0.15))

    return base * normalization * ncu_weight


def enforce_budget(model_calls: int, retries: int, tool_calls: int, branching: int, ncu_weight: float) -> tuple[int, int, int, bool]:
    adjusted = False

    while calculate_ncu(model_calls, retries, tool_calls, branching, latency_factor=3, ncu_weight=ncu_weight) > MAX_NCU_BUDGET:
        if retries > 0:
            retries -= 1
            adjusted = True
        elif tool_calls > 0:
            tool_calls -= 1
            adjusted = True
        else:
            break

    return model_calls, retries, tool_calls, adjusted

def model_tokens(base_tokens: int, token_multiplier: float) -> int:
    variation = random.randint(-3, 3)
    return max(1, int(round(base_tokens * token_multiplier + variation)))


def build_workflow(
    base_tokens: int,
    model_calls: int,
    retries: int,
    tool_calls: int,
    profile: dict[str, float],
    latency_factor: float | None = None,
    branching: int | None = None,
) -> dict[str, Any]:

    branching = random.randint(1, 3) if branching is None else branching

    calls, retries, tools, adjusted = enforce_budget(
        model_calls,
        retries,
        tool_calls,
        branching,
        profile["ncu_weight"],
    )
    
    print("PROFILE:", profile)
    latency = random.uniform(0, 3) if latency_factor is None else latency_factor

    ncu = calculate_ncu(
        calls,
        retries,
        tools,
        branching,
        latency,
        profile["ncu_weight"]
    )

    # ---- TOKENS ----
    raw_tokens = model_tokens(base_tokens, profile["token_multiplier"])

    # ---- INFLATION (NCU LOGIC SIMPLIFIED) ----
    complexity = (
    1
    + (retries * 0.6)
    + (tool_calls * 0.7)
    + (branching * 0.5)
    + (calls * 0.3)
)


    effective_tokens = int(raw_tokens * (complexity ** 1.4))

    # ---- COST MODEL ----
    TOKEN_RATE = 0.00002
    NCU_PRICE = 0.005

    token_cost = effective_tokens * TOKEN_RATE
    ncu_cost = ncu * NCU_PRICE

    savings = 0
    if token_cost > 0:
        savings = ((token_cost - ncu_cost) / token_cost) * 100

    return {
        "raw_tokens": int(raw_tokens),
        "effective_tokens": int(effective_tokens),
        "inflation_factor": round(effective_tokens / raw_tokens, 2),
        "ncu": round(ncu, 2),
        "token_cost": round(token_cost, 6),
        "ncu_cost": round(ncu_cost, 6),
        "savings_percent": round(savings, 2),

        "details": {
            "model_calls": calls,
            "retries": retries,
            "tool_calls": tools,
            "branching": branching,
        },
        "adjusted": adjusted,
    }


def build_comparison(model_label: str, query_label: str, scenario: str) -> dict[str, str]:
    return {
        "model": model_label,
        "query": query_label,
        "scenario": SCENARIO_LABELS.get(scenario, "Unknown scenario"),
    }


@app.get("/")
def home() -> FileResponse:
    return FileResponse("templates/index.html")


@app.post("/run")
def run(payload: dict[str, Any]) -> dict[str, Any]:
    scenario = str(payload.get("scenario", "A")).upper()
    model = str(payload.get("model", "chatgpt")).lower()
    query = str(payload.get("query", "simple")).lower()

    random.seed(f"{scenario}-{model}-{query}")

    profile = MODEL_PROFILES.get(model, MODEL_PROFILES["chatgpt"])
    model_label = MODEL_LABELS.get(model, MODEL_LABELS["chatgpt"])
    query_label = QUERY_LABELS.get(query, QUERY_LABELS["simple"])
    prompt = QUERY_PRESETS.get(query, QUERY_PRESETS["simple"])

    base_response: dict[str, Any] = {
        "scenario": scenario,
        "model": model,
        "model_label": model_label,
        "query": query,
        "comparison": build_comparison(model_label, query_label, scenario),
        "prompt": prompt,
    }

    # ---------------- SCENARIO A ----------------
    if scenario == "A":
        return {
            **base_response,
            "headline": "Same tokens, different execution complexity",
            "insight": "Token counts look similar, but NCU diverges due to execution mechanics.",
            "result_a": build_workflow(
                800,
                model_calls=1,
                retries=0,
                tool_calls=0,
                profile=profile,
            ),
            "result_b": build_workflow(
                1000,
                model_calls=4,
                retries=3,
                tool_calls=3,
                profile=profile,
            ),
        }

    # ---------------- SCENARIO B ----------------
    if scenario == "B":
        shared_latency = 2.0
        shared_branching = 3

        return {
            **base_response,
            "headline": "Different tokens, similar execution profile",
            "insight": "Token counts differ, but NCU remains stable while token cost inflates with complexity.",

            "result_a": build_workflow(
                1200,
                model_calls=3,
                retries=2,
                tool_calls=2,
                profile=profile,
                latency_factor=shared_latency,
                branching=shared_branching,
            ),

            "result_b": build_workflow(
                900,
                model_calls=3,
                retries=2,
                tool_calls=2,
                profile=profile,
                latency_factor=shared_latency,
                branching=shared_branching,
            ),
        }

    # ---------------- FALLBACK ----------------
    return {
        **base_response,
        "headline": "Invalid scenario",
        "insight": "Use scenario A or B.",
        "result_a": {},
        "result_b": {},
    }