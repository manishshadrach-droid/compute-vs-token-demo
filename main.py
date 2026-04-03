import random
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Token vs NCU Demo")

MAX_NCU_BUDGET = 15

# MODEL PROFILES
MODEL_PROFILES = {
    "chatgpt": {"token_multiplier": 1.00, "ncu_weight": 1.00},
    "claude": {"token_multiplier": 1.05, "ncu_weight": 1.03},
    "gemini": {"token_multiplier": 0.95, "ncu_weight": 0.98},
}

# QUERY BANK
QUERY_BANK = {
    "simple": {
        "prompt": "Summarize this paragraph in one sentence.",
        "response": "A concise summary capturing the core idea."
    },
    "average": {
        "prompt": "Explain how APIs work with an example.",
        "response": "APIs allow systems to communicate, like a weather app fetching data."
    },
    "multi": {
        "prompt": "Compare REST vs GraphQL and give use cases.",
        "response": "REST uses fixed endpoints, GraphQL enables flexible queries."
    },
    "agentic": {
        "prompt": "Plan a trip with budget, tools, and alternatives.",
        "response": "Includes flights, hotels, tools, and backup options if plans change."
    }
}


def calculate_ncu(model_calls, retries, tool_calls, branching, latency, weight):
    base = (model_calls * 2) + (retries * 1.5) + (tool_calls * 2) + branching + latency
    return base * weight


def enforce_budget(model_calls, retries, tool_calls, branching, weight):
    adjusted = False

    while calculate_ncu(model_calls, retries, tool_calls, branching, 3, weight) > MAX_NCU_BUDGET:
        if retries > 0:
            retries -= 1
            adjusted = True
        elif tool_calls > 0:
            tool_calls -= 1
            adjusted = True
        else:
            break

    return model_calls, retries, tool_calls, adjusted


def model_tokens(base_tokens, multiplier):
    return max(1, int(base_tokens * multiplier + random.randint(-20, 20)))


def build_workflow(base_tokens, model_calls, retries, tool_calls, profile, latency=None, branching=None):
    branching = branching if branching is not None else random.randint(1, 3)

    calls, retries, tools, adjusted = enforce_budget(
        model_calls, retries, tool_calls, branching, profile["ncu_weight"]
    )

    latency = latency if latency is not None else random.uniform(0, 3)

    ncu = calculate_ncu(calls, retries, tools, branching, latency, profile["ncu_weight"])

    return {
        "tokens": model_tokens(base_tokens, profile["token_multiplier"]),
        "ncu": round(ncu, 2),
        "details": {
            "model_calls": calls,
            "retries": retries,
            "tool_calls": tools,
            "branching": branching
        },
        "adjusted": adjusted
    }


@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html") as f:
        return f.read()


@app.post("/run")
def run(payload: dict):

    scenario = payload.get("scenario", "A")
    model = payload.get("model", "chatgpt")
    query = payload.get("query", "simple")

    profile = MODEL_PROFILES.get(model, MODEL_PROFILES["chatgpt"])
    query_data = QUERY_BANK.get(query, QUERY_BANK["simple"])

    prompt = query_data["prompt"]
    response_text = query_data["response"]

    # SCENARIO A
    if scenario == "A":
        w1 = build_workflow(800, 1, 0, 0, profile)
        w2 = build_workflow(800, 3, 2, 2, profile)

        ratio = round(w2["ncu"] / w1["ncu"], 2)

        return {
            "scenario": "A",
            "prompt": prompt,
            "response": response_text,
            "message": "⚠ Same tokens, but significantly more actual work",
            "insight": f"⚡ {ratio}x more compute due to execution complexity",
            "workflow_1": w1,
            "workflow_2": w2
        }

    # SCENARIO B (STRONG TOKEN GAP)
    if scenario == "B":
        shared_latency = random.uniform(0, 3)
        shared_branching = random.randint(1, 3)

        w1 = build_workflow(1600, 2, 1, 1, profile, shared_latency, shared_branching)
        w2 = build_workflow(400, 2, 1, 1, profile, shared_latency, shared_branching)

        token_gap = abs(w1["tokens"] - w2["tokens"])

        return {
            "scenario": "B",
            "prompt": prompt,
            "response": response_text,
            "message": "⚠ Different tokens, same actual work",
            "insight": f"⚡ Same execution, but {token_gap} token difference",
            "workflow_1": w1,
            "workflow_2": w2
        }

    return {"error": "Invalid scenario"}