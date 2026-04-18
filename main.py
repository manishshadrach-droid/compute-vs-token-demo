from typing import Any
from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI(title="Token vs NCU Demo")

MODEL_PROFILES = {
    "chatgpt": {"token_multiplier": 1.00, "ncu_weight": 1.00},
    "gemini": {"token_multiplier": 0.97, "ncu_weight": 0.98},
}

MODEL_LABELS = {
    "chatgpt": "ChatGPT 5.2",
    "gemini": "Gemini 3.0",
}

PROMPT_PAIRS = {
    "simple": {
        "A": "Rewrite the sentence in plain English. The company will commence operations next quarter.",
        "B": "Rewrite and explain the sentence in plain English. The company will commence operations next quarter.",
    },
    "reasoning": {
        "A": "A product costs 20 and sells for 30. Calculate profit.",
        "B": "A product costs 20 and sells for 30. Calculate profit and margin with steps.",
    },
    "multi": {
        "A": "Summarize this paragraph about AI efficiency.",
        "B": "Summarize this paragraph and extract two insights about AI efficiency.",
    },
    "agentic": {
        "A": "Plan a one-day Chicago business trip.",
        "B": "Plan a one-day Chicago business trip and adjust for delays.",
    },
}


def calculate_ncu(model_calls, retries, tools, branching, latency, weight):
    base = (
        model_calls * 1.5
        + retries * 1.2
        + tools * 1.3
        + branching * 1.1
        + latency * 0.7
    )
    norm = 1 / (1 + retries * 0.2 + tools * 0.2 + branching * 0.15)
    return round(base * norm * weight, 2)


def build(tokens, model_calls, retries, tools, branching, profile):
    return {
        "tokens": int(tokens * profile["token_multiplier"]),
        "ncu": calculate_ncu(
            model_calls,
            retries,
            tools,
            branching,
            2.0,
            profile["ncu_weight"],
        ),
    }


def scenario_same_tokens():
    p = MODEL_PROFILES["chatgpt"]
    return (
        build(950, 1, 0, 0, 1, p),
        build(950, 5, 3, 3, 3, p),
    )


def scenario_diff_tokens():
    p = MODEL_PROFILES["chatgpt"]
    a = build(1150, 3, 2, 2, 2, p)
    b = build(900, 3, 2, 2, 2, p)

    shared = min(a["ncu"], b["ncu"])
    a["ncu"] = shared
    b["ncu"] = shared
    return a, b


def scenario_model():
    a = build(1000, 3, 1, 2, 2, MODEL_PROFILES["chatgpt"])
    b = build(1000, 3, 1, 2, 2, MODEL_PROFILES["gemini"])

    shared = min(a["ncu"], b["ncu"])
    a["ncu"] = shared
    b["ncu"] = shared
    return a, b


@app.get("/")
def home():
    return FileResponse("templates/index.html")


@app.post("/run")
def run(payload: dict[str, Any]):
    scenario = payload.get("scenario", "same_tokens")
    task = payload.get("task", "simple")

    prompts = PROMPT_PAIRS.get(task, PROMPT_PAIRS["simple"])

    if scenario == "same_tokens":
        left, right = scenario_same_tokens()
        headline = "Same Tokens ≠ Same Compute"
        left_model = MODEL_LABELS["chatgpt"]
        right_model = MODEL_LABELS["chatgpt"]

    elif scenario == "diff_tokens":
        left, right = scenario_diff_tokens()
        headline = "Different Tokens ≠ Different Compute"
        left_model = MODEL_LABELS["chatgpt"]
        right_model = MODEL_LABELS["chatgpt"]

    else:
        left, right = scenario_model()
        headline = "Same Compute ≠ Same Tokens"
        left_model = MODEL_LABELS["chatgpt"]
        right_model = MODEL_LABELS["gemini"]

    return {
        "headline": headline,
        "left": {
            "model": left_model,
            "prompt": prompts["A"],
            "tokens": left["tokens"],
            "ncu": left["ncu"],
        },
        "right": {
            "model": right_model,
            "prompt": prompts["B"],
            "tokens": right["tokens"],
            "ncu": right["ncu"],
        },
    }