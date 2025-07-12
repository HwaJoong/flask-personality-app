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


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        username = request.form.get('username')
        session['username'] = username
        return redirect(url_for('team'))
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

from flask import render_template

@app.route("/result")
def result():
    answers = session.get('answers')
    if not answers:
        return redirect(url_for('question'))

    # 점수 계산
    result_scores = calculate_scores(answers)  # {"창의형": 10, ...}
    user_type = determine_type(result_scores)  # 가장 높은 유형

    # 설명 구성
    description = get_description(user_type)

    # 상세 설명 추가 (detail 키를 넣어줘야 result.html이 정상 작동)
    description["detail"] = {
        "strengths": type_strengths.get(user_type, "강점 정보 없음"),
        "challenges": type_weaknesses.get(user_type, "도전 과제 정보 없음"),
        "working_style": get_working_style(user_type),
        "stress_response": get_stress_response(user_type)
    }

    username = session.get('username', '사용자')
    labels = list(result_scores.keys())

    team_code = session.get("team_code")

    return render_template("result.html",
                           username=username,
                           description=description,
                           result_scores=result_scores,
                           labels=labels,
                           team_code=team_code)


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

    # 이름 기준 중복 제거
    unique_entries = {entry["name"]: entry for entry in raw_data}
    data = list(unique_entries.values())

    # 유형 개수 집계
    type_counts = {}
    for entry in data:
        t = entry['type']
        type_counts[t] = type_counts.get(t, 0) + 1

    # ✅ 이름만 추출해서 ㄱㄴㄷ 순 정렬
    sorted_names = sorted([entry["name"] for entry in data])

    # 개인 성향 요약 포함된 멤버 정보 생성
    member_summaries = sorted([
        (entry["name"], entry["type"], get_short_summary(entry["type"]))
        for entry in data
    ], key=lambda x: x[0])  # 이름 기준 정렬


    # 팀 분석 텍스트 생성
    trait_text, summary, detailed_text, communication_text, recommendation_text = generate_team_summary(type_counts)

    return render_template(
        "team_result.html",
        team_code=team_code,
        type_counts=type_counts,
        total=len(data),
        sorted_names=sorted_names,               # ✅ 이름만 따로 전달
        trait_text=trait_text,
        summary=summary,
        detailed_text=detailed_text,
        communication_text=communication_text,
        recommendation_text=recommendation_text,
        member_summaries=member_summaries        # 표에서 이름 + 유형 + 요약용
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
    return descriptions.get(user_type, {"title": "알 수 없음", "summary": "", "style": [], "partner": ""})


type_strengths = {
    "리더형": "방향 설정과 추진력, 결단력 있는 리더십",
    "조율형": "갈등 조율 능력과 팀워크 중심의 실행력",
    "창의형": "새로운 아이디어 도출과 유연한 사고",
    "분석형": "체계적인 문제 해결 능력",
    "실행형": "빠른 실행력과 결과 중심의 태도",
    "헌신형": "타인의 감정에 대한 공감력과 팀 내 화합 촉진"
}



type_weaknesses = {
    "리더형": "타인의 의견을 충분히 반영하지 못하거나 지시적으로 비칠 수 있음",
    "조율형": "과도한 타협으로 인해 결단력 부족 가능성",
    "분석형": "감정적 요소 간과 및 유연성 부족 가능성",
    "창의형": "세부 실행력 부족, 현실성 검토가 부족할 수 있음",
    "헌신형": "자기 주장 부족과 책임 회피 경향이 생길 수 있음",
    "실행형": "충분한 검토 없이 성급한 행동으로 이어질 수 있음"
}



type_recommendations = {
    "조율형": [
        "중요한 결정에서 우유부단하지 않도록 명확한 리더십을 보완하세요.",
        "다양한 의견을 수렴하되, 실행력을 확보하는 구조를 만들면 좋습니다."
    ],
    "창의형": [
        "아이디어 실행 전, 타당성 검토를 위한 검토 단계를 도입하세요.",
        "구체적인 일정과 실행 계획을 세워 팀원들과 공유하세요."
    ],
    "분석형": [
        "완벽한 분석보다는 실행 타이밍도 고려해보세요.",
        "감성형이나 조율형과 함께 일하면 균형이 잡힐 수 있습니다."
    ],
    "실행형": [
        "결정 전에 팀원 간 사전 검토 및 역할 분담을 명확히 하세요.",
        "다른 관점(창의형/분석형)의 피드백을 수용하면 더 안정적인 결과로 이어집니다."
    ],
    "헌신형": [
        "자신의 의견도 분명하게 표현하세요.",
        "책임 있는 역할도 두려워하지 말고 도전해보세요."
    ],
    "리더형": [
        "타인의 의견을 수렴하려는 태도를 기르면 협업이 더 원활해집니다.",
        "권한 위임을 통해 팀원들의 자율성을 살려보세요."
    ]
}
def get_working_style(user_type):
    styles = {
        "창의형": "자유롭고 유연한 환경을 선호하며, 틀에 박힌 방식보다는 새로움을 추구",
        "조율형": "타인의 의견을 조율하고 조화를 이루는 방식으로 업무를 추진",
        "분석형": "논리적 근거와 분석 중심의 문제 해결을 선호",
        "실행형": "명확한 목표와 빠른 결과 중심의 업무 방식 선호",
        "헌신형": "팀과의 관계와 분위기를 중시하며 협력적인 환경을 선호",
        "리더형": "목표 중심으로 계획하고, 팀을 이끄는 역할을 선호"
    }
    return styles.get(user_type, "정보 없음")

def get_stress_response(user_type):
    responses = {
        "창의형": "지속적 반복 작업, 엄격한 규칙 속에서 동기 저하 및 스트레스 발생",
        "조율형": "갈등이 장기화될 경우 스트레스 증가, 비협조적인 분위기에 취약",
        "분석형": "불확실한 정보와 감정적인 환경에서 스트레스를 느낌",
        "실행형": "계획에 없던 변경 상황에서 스트레스를 받을 수 있음",
        "헌신형": "갈등 상황이나 무시당하는 환경에서 스트레스를 느낌",
        "리더형": "권한 부재나 목표 부재 시 동기 저하 및 스트레스 발생"
    }
    return responses.get(user_type, "정보 없음")



def generate_team_summary(type_counts):
    total = sum(type_counts.values())
    if total == 0:
        return "", "팀 분석 데이터를 찾을 수 없습니다.", ""

    percentages = {k: v / total * 100 for k, v in type_counts.items()}
    sorted_types = sorted(percentages.items(), key=lambda x: x[1], reverse=True)
    main_type, main_percent = sorted_types[0]

    # 1. 팀 구성 특성 분석
    if main_percent >= 80:
        trait_text = f"이 팀은 '{main_type}' 성향이 매우 강하게 나타나는 집중형 팀입니다. 특정 방향으로 빠르게 움직일 수 있지만 시야가 편중될 수 있습니다."
    elif len(sorted_types) >= 2 and sorted_types[1][1] >= 30:
        second_type = sorted_types[1][0]
        trait_text = f"이 팀은 '{main_type}'와 '{second_type}' 유형이 혼합된 구조로, 두 특성이 조화를 이루며 협업합니다."
    else:
        trait_text = "이 팀은 다양한 성격 유형으로 구성되어 있어 유연하고 다각적인 사고가 가능한 균형형 팀입니다."

    # 2. 팀 분석 요약
    summary_parts = []
    if main_percent >= 80:
        summary_parts.append(f"이 팀은 모든 구성원이 '{main_type}' 유형으로 구성되어 있어 매우 일관된 성향을 보입니다.")
        summary_parts.append(f"{main_type} 유형의 강점은 {type_strengths[main_type]}입니다.")
        summary_parts.append(f"하지만 {type_weaknesses[main_type]} 측면에서는 주의가 필요합니다.")
    elif len(sorted_types) >= 2 and sorted_types[1][1] >= 30:
        second_type, second_percent = sorted_types[1]
        summary_parts.append(f"이 팀은 '{main_type}'({main_percent:.0f}%)와 '{second_type}'({second_percent:.0f}%) 유형이 주를 이루며, 두 유형의 특성이 균형 있게 섞여 있습니다.")
        summary_parts.append(f"{main_type}은 {type_strengths[main_type]}, {second_type}은 {type_strengths[second_type]} 측면에서 강점을 가집니다.")
    else:
        summary_parts.append("이 팀은 다양한 성격 유형으로 구성되어 있어 창의성과 균형 잡힌 접근이 기대됩니다.")
    summary = " ".join(summary_parts)

    # 3. 추천 행동 전략
    recommendations = type_recommendations.get(main_type, [])
    recommendation_text = "\n".join(recommendations)

    # 4. 상세 해석
    detailed_text = (
        f"'{main_type}' 성향이 강한 이 팀은 실행 중심의 목표 달성형 팀 분위기를 가질 가능성이 높습니다. "
        "의사결정이 빠르고 추진력이 강하지만, 감정적 조율이나 다양한 관점 반영은 부족할 수 있습니다. "
        "불확실한 상황보다는 명확한 목표가 있는 업무에 더 강한 성과를 낼 수 있습니다."
    )

    communication_text = (
    f"{main_type} 중심의 팀은 효율성과 빠른 실행을 중시하는 만큼, 커뮤니케이션에서도 속도와 명확함을 중요하게 여깁니다. "
    "반면, 감정 기반 피드백이나 비판을 에둘러 말하는 방식에는 익숙하지 않아 갈등이 표면화되기 쉽습니다. "
    "실수나 지연에 대한 피드백은 직설적으로 표현될 수 있어, 감성형/조율형 구성원이 위축될 수 있습니다. "
    "팀 내 심리적 안전감을 유지하려면, 정기적인 감정 공유와 피드백 룰(예: 비난 대신 제안 방식)을 도입하는 것이 도움이 됩니다."
)

    return trait_text, summary, detailed_text, communication_text, recommendation_text



def get_short_summary(user_type):
    summaries = {
        '창의형': '아이디어와 새로운 시도를 즐깁니다.',
        '실행형': '실행력과 빠른 결과 도출을 중시합니다.',
        '분석형': '논리적 사고와 문제 해결에 강합니다.',
        '헌신형': '팀의 분위기와 조화를 중시합니다.',
        '조율형': '중재와 균형, 감정 조율에 능합니다.',
        '리더형': '목표를 향해 이끄는 결단력과 추진력이 강합니다.'
    }
    return summaries.get(user_type, '')




if __name__ == '__main__':
    app.run(debug=True)