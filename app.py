from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import uuid
import os
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# 질문 목록
questions = [
    "나는 새로운 아이디어를 생각해내는 것을 좋아한다.",
    "복잡한 문제를 해결할 때 창의적인 접근을 시도하는 편이다.",
    "감정보다는 논리적으로 결정을 내리는 편이다.",
    "다른 사람의 감정에 민감하게 반응한다.",
    "계획 없이 즉흥적으로 행동하는 것을 좋아한다.",
    "체계적으로 일정을 관리하고 계획하는 편이다.",
    "혼자 조용히 일할 때 에너지가 충전된다.",
    "사람들과 함께 활동할 때 에너지가 올라간다.",
    "실제 경험이나 관찰을 통해 배우는 것을 선호한다.",
    "이론이나 개념을 통해 전체를 이해하는 걸 선호한다.",
    "결정할 때 주변 사람의 의견을 적극 반영하는 편이다.",
    "객관적 기준에 따라 판단하는 편이다.",
    "일을 마감 직전에 몰아서 하는 경우가 많다.",
    "계획한 일을 미리미리 처리하려고 노력한다.",
    "새로운 환경에서도 쉽게 적응하고 사람들과 어울릴 수 있다.",
    "익숙한 환경에서 안정적으로 일하는 걸 선호한다."
]

@app.route('/')
def home():
    return render_template('name.html')

@app.route('/name', methods=['GET', 'POST'])
def name():
    if request.method == 'POST':
        username = request.form.get('username')
        session['username'] = username
        return redirect(url_for('team'))
    return render_template('name.html')

@app.route('/team')
def team():
    return render_template('team.html')

@app.route('/generate_team_code')
def generate_team_code():
    import string, random
    existing_codes = set()
    if os.path.exists("data"):
        for filename in os.listdir("data"):
            if filename.endswith(".json"):
                existing_codes.add(filename.replace(".json", "").upper())

    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if code not in existing_codes:
            break

    return jsonify({'code': code})

@app.route('/set_team_code', methods=['POST'])
def set_team_code():
    team_code = request.form.get('team_code')
    session['team_code'] = team_code.strip() if team_code and team_code.strip() else None
    session.pop('answers', None)
    return redirect(url_for('question'))

@app.route('/question', methods=['GET', 'POST'])
def question():
    if request.method == 'POST':
        q = int(request.form['q'])
        score = int(request.form['score'])

        answers = session.get('answers', [])
        answers.append(score)
        session['answers'] = answers

        q += 1
        if q >= len(questions):
            return redirect(url_for('result'))
        return render_template('question.html', q=q, question=questions[q], questions=questions)
    else:
        if 'answers' not in session:
            session['answers'] = []
        return render_template('question.html', q=0, question=questions[0], questions=questions)

@app.route('/result')
def result():
    answers = session.get("answers", [])
    if not answers or len(answers) != len(questions):
        return redirect(url_for('question'))

    result_scores = calculate_scores(answers)
    user_type = determine_type(result_scores)
    description = get_description(user_type)

    team_code = session.get('team_code')
    username = session.get('username')

    if team_code and username:
        os.makedirs("data", exist_ok=True)
        file_path = f"data/{team_code}.json"

        entry = {
            "name": username,
            "type": user_type,
            "scores": result_scores
        }

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []

        data = [d for d in data if d.get("name") != username]
        data.append(entry)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return render_template(
        "result.html",
        description=description,
        result_scores=result_scores,
        labels=list(result_scores.keys()),
        team_code=team_code,
        username=username
    )

@app.route('/check_team_code/<team_code>', methods=['HEAD'])
def check_team_code(team_code):
    file_path = f"data/{team_code}.json"
    if os.path.exists(file_path):
        return '', 200  # OK
    else:
        return '', 404  # Not Found

@app.route('/team_result/<team_code>')
def team_result(team_code):
    file_path = f"data/{team_code}.json"
    if not os.path.exists(file_path):
        return f"팀 코드 '{team_code}'에 대한 데이터가 없습니다."

    with open(file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    unique_entries = {}
    for entry in raw_data:
        unique_entries[entry["name"]] = entry
    data = list(unique_entries.values())

    type_counts = {}
    for entry in data:
        t = entry['type']
        type_counts[t] = type_counts.get(t, 0) + 1

    members = [(entry["name"], entry["type"]) for entry in data]

    total = len(data)
    most_common = max(type_counts, key=type_counts.get)
    percent = (type_counts[most_common] / total) * 100

    if percent >= 70:
        summary = f"이 팀은 '{most_common}' 유형이 전체의 {percent:.0f}%를 차지합니다. 한 방향으로 강한 실행력이 기대되지만, 다양성이나 균형 측면에선 보완이 필요할 수 있습니다."
    elif percent >= 40:
        summary = f"'{most_common}' 유형이 많은 편이지만 다른 유형도 혼합되어 있습니다. 비교적 균형 잡힌 협업이 가능할 것입니다."
    else:
        summary = "팀 구성원이 다양한 유형으로 고르게 분포되어 있어, 유연한 시각과 다양한 접근이 기대되는 균형 잡힌 팀입니다."

    return render_template(
        "team_result.html",
        team_code=team_code,
        type_counts=type_counts,
        summary=summary,
        members=members,
        total=len(data)
    )

# 분석 함수들
def calculate_scores(answers):
    types = ['리더형', '조율형', '분석형', '창의형', '헌신형', '실행형']
    scores = {}
    for i, t in enumerate(types):
        scores[t] = sum(answers[i*3:(i+1)*3])
    return scores

def determine_type(scores):
    return max(scores, key=scores.get)

def get_description(user_type):
    descriptions = {
        '창의형': {
            'title': '창의형 (Innovator)',
            'summary': '새로운 아이디어와 접근을 즐깁니다.',
            'style': ['자율적인 환경 선호', '도전적 과제에 열정'],
            'partner': '실행형과 잘 맞습니다.\n분석형과도 균형을 이룹니다.'
        },
        '실행형': {
            'title': '실행형 (Executor)',
            'summary': '실행력과 집중력이 뛰어납니다.',
            'style': ['명확한 목표 설정', '계획 실행에 강함'],
            'partner': '창의형과 함께할 때 시너지가 큽니다.'
        },
        '분석형': {
            'title': '분석형 (Analyzer)',
            'summary': '체계적이고 근거 있는 접근을 중시합니다.',
            'style': ['데이터 기반 사고', '위험 회피 및 구조화'],
            'partner': '창의형과 조화를 이룹니다.'
        },
        '헌신형': {
            'title': '헌신형 (Supporter)',
            'summary': '타인을 배려하고 팀 분위기를 좋게 만듭니다.',
            'style': ['공감 능력 뛰어남', '지원 역할에 강점'],
            'partner': '리더형, 조율형과 좋은 조합'
        },
        '조율형': {
            'title': '조율형 (Coordinator)',
            'summary': '의견을 조율하고 팀 균형을 맞춥니다.',
            'style': ['중재 능력', '상황에 따른 유연한 대응'],
            'partner': '헌신형과 함께할 때 협업이 원활합니다.'
        },
        '리더형': {
            'title': '리더형 (Leader)',
            'summary': '방향 제시와 책임을 지는 것을 좋아합니다.',
            'style': ['결단력 있음', '목표 지향적'],
            'partner': '헌신형, 실행형과 시너지가 큽니다.'
        }
    }
    return descriptions[user_type]

if __name__ == '__main__':
    app.run(debug=True)
