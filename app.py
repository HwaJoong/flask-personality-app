from flask import Flask, render_template, request, redirect, url_for
from collections import defaultdict, Counter
import random
import string

app = Flask(__name__)
user_data = {}
team_results = defaultdict(list)

# 성향 유형 분류 기준 (각 유형별 점수 범위 기반 임의 로직)
def classify_type(scores):
    total = sum(scores)
    avg = total / len(scores)

    if avg >= 4.5:
        return "혁신형"
    elif avg >= 3.8:
        return "창의형"
    elif avg >= 3.0:
        return "조율형"
    elif avg >= 2.5:
        return "실행형"
    elif avg >= 2.0:
        return "분석형"
    else:
        return "신중형"

# ✅ 팀 요약 문장 생성 함수
def generate_team_summary(type_counts):
    total = sum(type_counts.values())
    sorted_types = sorted(type_counts.items(), key=lambda x: -x[1])
    top_type, top_count = sorted_types[0]

    diversity = len([count for count in type_counts.values() if count > 0])
    max_ratio = top_count / total

    summary = f"이 팀은 '{top_type}' 유형이 가장 많아 해당 성향이 팀 분위기에 큰 영향을 미칩니다. "

    if diversity >= 5 and max_ratio < 0.5:
        summary += "전체적으로 다양한 성향이 고르게 분포되어 있어 팀 내 다양한 시각과 유연한 협업이 기대됩니다. "
    elif max_ratio >= 0.6:
        summary += "특정 유형에 편중되어 있어 팀 문화가 한 방향으로 치우칠 가능성이 있습니다. "

    if "분석형" not in type_counts or type_counts.get("분석형", 0) == 0:
        summary += "또한 분석형 유형이 부족하여, 데이터 기반 판단에서 약점을 보일 수 있습니다. "

    summary += "각 유형의 장점을 살리고 보완점을 인지하여 협력하면 더 높은 시너지를 낼 수 있습니다."
    return summary

# 초기 이름 입력
@app.route("/", methods=["GET", "POST"])
def name():
    if request.method == "POST":
        username = request.form["username"]
        user_data["username"] = username
        return redirect(url_for("set_team_code"))
    return render_template("name.html")

# 팀 코드 설정
@app.route("/set_team_code", methods=["GET", "POST"])
def set_team_code():
    if request.method == "POST":
        code = request.form["team_code"].strip()
        user_data["team_code"] = code if code else None
        return redirect(url_for("question"))
    return render_template("team.html")

# 질문 리스트
questions = [
    "당신은 새로운 아이디어를 제시하는 것을 즐깁니다.",
    "팀원들과 의견을 조율하는 것을 잘합니다.",
    "데이터나 논리에 기반한 판단을 선호합니다.",
    "계획보다는 즉흥적인 행동을 더 선호합니다.",
    "문제를 창의적으로 해결하려는 편입니다.",
    "팀 내에서 갈등을 중재하는 역할을 자주 합니다.",
    "세부 사항까지 신경 써서 일을 처리합니다.",
    "도전적인 목표에 열정을 가지고 임합니다.",
    "타인의 감정을 잘 공감하고 배려합니다.",
    "정해진 절차나 규칙을 잘 따릅니다.",
    "새로운 방식으로 업무를 접근하려 합니다.",
    "팀워크를 중시하며 함께 하는 것을 즐깁니다.",
    "객관적인 자료를 수집하고 분석하는 것을 선호합니다.",
    "리스크를 감수하고 변화를 추구합니다.",
    "갈등 상황에서도 차분하게 대처하려고 합니다.",
    "정확성과 철저함을 중요하게 생각합니다."
]

# 질문 페이지
@app.route("/question", methods=["GET", "POST"])
def question():
    if "responses" not in user_data:
        user_data["responses"] = []

    if request.method == "POST":
        q_index = int(request.form["q"])
        score = int(request.form["score"])
        user_data["responses"].append(score)

        if q_index + 1 >= len(questions):
            return redirect(url_for("result"))
        else:
            return render_template("question.html", q=q_index + 1, question=questions[q_index + 1], questions=questions)

    return render_template("question.html", q=0, question=questions[0], questions=questions)

# 개인 결과
@app.route("/result")
def result():
    scores = user_data.get("responses", [])
    username = user_data.get("username", "이름없음")
    team_code = user_data.get("team_code", None)

    if not scores:
        return redirect(url_for("question"))

    user_type = classify_type(scores)

    if team_code:
        team_results[team_code].append((username, user_type))

    return render_template("result.html", name=username, user_type=user_type)

# 팀 결과 보기
@app.route("/team_result/<code>")
def team_result(code):
    if code not in team_results:
        return render_template("team_result.html", error="해당 팀 코드에 대한 결과가 없습니다.", total=0)

    members = team_results[code]
    type_counts = Counter([t for _, t in members])
    summary = generate_team_summary(type_counts)

    return render_template("team_result.html",
                           team_code=code,
                           total=len(members),
                           members=members,
                           type_counts=type_counts,
                           summary=summary)

# 팀 코드 생성
@app.route("/generate_team_code")
def generate_team_code():
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return {"code": code}

# 팀 코드 유효성 확인
@app.route("/check_team_code/<code>", methods=["HEAD"])
def check_team_code(code):
    if code in team_results:
        return '', 200
    return '', 404

if __name__ == "__main__":
    app.run(debug=True)
