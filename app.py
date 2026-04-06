from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/run', methods=['POST'])
def run():
    data = request.json

    query = data.get("query", "simple")

    if query == "simple":
        tokens = 120
        ncu = 48
    elif query == "average":
        tokens = 200
        ncu = 120
    elif query == "multi":
        tokens = 300
        ncu = 260
    elif query == "agentic":
        tokens = 400
        ncu = 600
    else:
        tokens = 150
        ncu = 100

    return jsonify({
        "result_a": {
            "raw_tokens": tokens,
            "effective_tokens": int(tokens * 1.5),
            "ncu": ncu,
            "token_cost": round(tokens * 0.01, 2),
            "ncu_cost": round(ncu * 0.01, 2),
            "inflation_factor": round(ncu / tokens, 2),
            "savings_percent": int((1 - (ncu / tokens)) * 100)
        }
    })
if __name__ == "__main__":
    app.run(port=8000, debug=True)