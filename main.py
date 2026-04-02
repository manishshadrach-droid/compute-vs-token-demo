import random
from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI(title="Token vs Compute Metering Demo")

# -------------------------
# CONFIG
# -------------------------
MAX_NCU_BUDGET = 15
TOKEN_RATE = 0.00001
COMPUTE_RATE = 0.01


# -------------------------
# CORE COMPUTE LOGIC
# -------------------------
def calculate_ncu(model_calls: int, retries: int, tool_calls: int, latency: float) -> float:
    return (model_calls * 2) + (retries * 1.5) + (tool_calls * 2) + latency


def enforce_budget(model_calls: int, retries: int, tool_calls: int):
    """
    Ensure worst-case execution (latency=3) stays within budget.
    """
    adjusted = False

    while calculate_ncu(model_calls, retries, tool_calls, 3) > MAX_NCU_BUDGET:
        if retries > 0:
            retries -= 1
            adjusted = True
        elif tool_calls > 0:
            tool_calls -= 1
            adjusted = True
        else:
            break

    return model_calls, retries, tool_calls, adjusted


# -------------------------
# WORKFLOW BUILDER
# -------------------------
def build_workflow(tokens: int, model_calls: int, retries: int, tool_calls: int, latency_override=None):
    calls, retries, tools, adjusted = enforce_budget(model_calls, retries, tool_calls)

    latency = latency_override if latency_override is not None else random.uniform(0, 3)

    ncu = calculate_ncu(calls, retries, tools, latency)

    return {
        "tokens": tokens,
        "token_cost": round(tokens * TOKEN_RATE, 5),
        "ncu": round(ncu, 2),
        "compute_cost": round(ncu * COMPUTE_RATE, 4),
        "adjusted": adjusted,
        "details": {
            "model_calls": calls,
            "retries": retries,
            "tool_calls": tools,
        },
    }


# -------------------------
# ROUTES
# -------------------------
@app.get("/")
def home():
    return FileResponse("index.html")


@app.post("/run")
def run(payload: dict):
    scenario = str(payload.get("scenario", "A")).upper()

    # -------------------------
    # SCENARIO A
    # SAME TOKENS, DIFFERENT WORK
    # -------------------------
    if scenario == "A":
        simple = build_workflow(
            tokens=random.randint(790, 810),
            model_calls=1,
            retries=0,
            tool_calls=0
        )

        agentic = build_workflow(
            tokens=random.randint(790, 810),
            model_calls=3,
            retries=2,
            tool_calls=2
        )

        ratio = round(agentic["ncu"] / simple["ncu"], 2) if simple["ncu"] > 0 else 0

        return {
            "scenario": "A",
            "message": "⚠ Same tokens, but significantly more actual work",
            "insight": f"{ratio}x more compute for similar tokens",
            "workflow_1": simple,
            "workflow_2": agentic
        }

    # -------------------------
    # SCENARIO B
    # DIFFERENT TOKENS, SAME WORK
    # -------------------------
    if scenario == "B":
        shared_latency = random.uniform(0, 3)

        high_token = build_workflow(
            tokens=1200,
            model_calls=2,
            retries=1,
            tool_calls=1,
            latency_override=shared_latency
        )

        lower_token = build_workflow(
            tokens=600,
            model_calls=2,
            retries=1,
            tool_calls=1,
            latency_override=shared_latency
        )

        diff = abs(high_token["ncu"] - lower_token["ncu"])

        return {
            "scenario": "B",
            "message": "⚠ Different tokens, but similar actual work",
            "insight": f"NCU difference is only {round(diff, 2)} despite token gap",
            "workflow_1": high_token,
            "workflow_2": lower_token
        }

    return {"error": "Invalid scenario"}