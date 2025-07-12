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

    # ✅ 결과 저장
    if team_code:
        file_path = f"data/{team_code}.json"
        os.makedirs("data", exist_ok=True)

        # 기존 데이터 로드
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    raw_data = json.load(f)
                except json.JSONDecodeError:
                    raw_data = []
        else:
            raw_data = []

        # 동일 이름 제거 후 새 결과 추가
        raw_data = [entry for entry in raw_data if entry["name"] != username]
        raw_data.append({
            "name": username,
            "scores": result_scores,
            "type": user_type
        })

        # 다시 저장
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)

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
    # 유형별 개수 정리
    type_rank = sorted(type_counts.items(), key=lambda x: -x[1])
    type_order = {t: i for i, (t, _) in enumerate(type_rank)}  # 유형에 순위 부여

    # 정렬 기준: ① 유형 등장 순위 ② 이름순
    member_summaries = sorted([
        (entry["name"], entry["type"], get_short_summary(entry["type"]))
        for entry in data
    ], key=lambda x: (type_order.get(x[1], 999), x[0]))



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


team_combination_summaries = {
    "리더형+조율형": {
        "summary": "리더형의 추진력과 조율형의 협업 능력이 조화를 이루며, 명확한 방향성과 부드러운 팀워크가 공존하는 팀입니다.",
        "structure": "리더형이 방향성을 제시하고 조율형이 팀 내 의견을 중재하며, 전체적인 밸런스를 유지합니다."
    },
    "리더형+분석형": {
        "summary": "리더형의 결단력과 분석형의 신중함이 어우러져 실천 가능한 전략을 도출하는 팀입니다.",
        "structure": "리더형이 전진하고 분석형이 리스크를 검토하며, 실행과 안전성 간의 균형을 이룹니다."
    },
    "리더형+창의형": {
        "summary": "리더형의 추진력과 창의형의 아이디어가 결합되어 도전적이면서 혁신적인 분위기를 형성합니다.",
        "structure": "창의형의 비정형적 사고를 리더형이 실행 가능한 방향으로 이끕니다."
    },
    "리더형+헌신형": {
        "summary": "리더형의 책임감과 헌신형의 배려심이 결합되어 신뢰감 있는 팀을 만듭니다.",
        "structure": "리더형이 리딩하고 헌신형이 지원하며, 안정적인 실행력이 발휘됩니다."
    },
    "리더형+실행형": {
        "summary": "목표 지향성과 실행력이 극대화된 팀으로, 빠른 결정과 행동으로 성과를 추구합니다.",
        "structure": "리더형이 방향을 제시하고 실행형이 즉각 실행하며, 속도감 있는 문화가 조성됩니다."
    },
    "조율형+리더형": {
        "summary": "조율형이 갈등을 최소화하며 리더형의 결단력을 보완하는 팀입니다.",
        "structure": "리더형이 중심을 잡고 조율형이 팀 내 소통을 부드럽게 만듭니다."
    },
    "조율형+분석형": {
        "summary": "팀 내 안정성과 논리적 접근이 특징인 팀으로, 신중한 결정과 배려가 공존합니다.",
        "structure": "분석형이 데이터를 통해 논리를 세우고 조율형이 인간적인 측면에서 조화를 이룹니다."
    },
    "조율형+창의형": {
        "summary": "조율형의 배려와 창의형의 유연함이 결합되어 부드럽고 새로운 시도를 추구하는 팀입니다.",
        "structure": "창의형이 아이디어를 제시하고 조율형이 팀원 간 공감대를 형성해 추진합니다."
    },
    "조율형+헌신형": {
        "summary": "배려와 협력이 강조된 팀으로, 감정적 안정감이 높고 갈등이 적습니다.",
        "structure": "조율형과 헌신형이 상호 존중하며 조화롭게 업무를 추진합니다."
    },
    "조율형+실행형": {
        "summary": "조율형의 협업 능력과 실행형의 실천력이 조화를 이루며 실현력 있는 팀 문화를 형성합니다.",
        "structure": "조율형이 방향을 정리하고 실행형이 이를 신속하게 실현합니다."
    },
    "분석형+리더형": {
        "summary": "리더형의 추진력과 분석형의 전략적 사고가 조화를 이루는 팀입니다.",
        "structure": "분석형이 검토 후 리더형이 실행함으로써 정밀하면서도 빠른 결정을 유도합니다."
    },
    "분석형+조율형": {
        "summary": "데이터 기반 의사결정과 감정적 조율이 어우러져 균형 있는 결과를 만드는 팀입니다.",
        "structure": "분석형이 논리 구조를 잡고 조율형이 인간관계를 다집니다."
    },
    "분석형+창의형": {
        "summary": "논리와 창의가 함께 존재하는 팀으로, 혁신적인 아이디어를 현실화시킬 가능성이 높습니다.",
        "structure": "창의형이 가능성을 제안하고 분석형이 실행 가능성을 검토합니다."
    },
    "분석형+헌신형": {
        "summary": "조용하고 신중한 팀 분위기에서 신뢰를 기반으로 성과를 도출하는 팀입니다.",
        "structure": "분석형이 이성을, 헌신형이 감성을 책임지며 조화로운 의사결정을 돕습니다."
    },
    "분석형+실행형": {
        "summary": "계획과 실행이 함께 작동하는 팀으로, 높은 생산성을 자랑합니다.",
        "structure": "분석형이 계획을 세우고 실행형이 빠르게 수행합니다."
    },
    "창의형+리더형": {
        "summary": "아이디어를 실현 가능한 결과로 이끄는 팀으로, 혁신을 주도합니다.",
        "structure": "창의형이 새로운 길을 제시하고 리더형이 그것을 추진합니다."
    },
    "창의형+조율형": {
        "summary": "유연한 사고와 감성적 리더십이 결합된 팀으로, 다양성을 수용합니다.",
        "structure": "창의형이 아이디어를 펼치고 조율형이 이를 팀에 조화시킵니다."
    },
    "창의형+분석형": {
        "summary": "비정형적 사고와 체계적 사고가 조화를 이루며, 혁신과 실용을 함께 추구합니다.",
        "structure": "창의형이 아이디어를 던지고 분석형이 그것을 구체화합니다."
    },
    "창의형+헌신형": {
        "summary": "팀 분위기를 부드럽게 만들면서 창의적인 시도를 장려하는 팀입니다.",
        "structure": "창의형이 방향을 제시하고 헌신형이 이를 뒷받침합니다."
    },
    "창의형+실행형": {
        "summary": "새로운 아이디어를 빠르게 실현할 수 있는 능력을 지닌 팀입니다.",
        "structure": "창의형이 아이디어를 제시하고 실행형이 즉시 행동으로 옮깁니다."
    },
    "헌신형+리더형": {
        "summary": "신뢰 기반의 팀워크가 강하며, 리더형의 추진력과 헌신형의 배려가 조화를 이룹니다.",
        "structure": "리더형이 결정하고 헌신형이 분위기를 유지하며 팀 안정성을 보장합니다."
    },
    "헌신형+조율형": {
        "summary": "상호 배려와 감정적 안정성이 돋보이며, 공동체 의식이 강한 팀입니다.",
        "structure": "조율형이 조화로운 소통을 주도하고 헌신형이 뒷받침합니다."
    },
    "헌신형+분석형": {
        "summary": "논리와 배려의 조합으로 안정적인 결과를 도출하는 팀입니다.",
        "structure": "분석형이 사실 기반으로 판단하고 헌신형이 정서적 지지를 제공합니다."
    },
    "헌신형+창의형": {
        "summary": "창의성과 따뜻함이 어우러져 인간적인 혁신을 추구하는 팀입니다.",
        "structure": "창의형이 실험을 제안하고 헌신형이 팀을 안정화시킵니다."
    },
    "헌신형+실행형": {
        "summary": "실행력과 배려가 균형을 이루는 팀으로, 부드러운 추진력이 강점입니다.",
        "structure": "실행형이 주도적으로 추진하고 헌신형이 조율합니다."
    },
    "실행형+리더형": {
        "summary": "결과 중심의 팀으로 빠른 실행과 목표 달성에 강점을 보입니다.",
        "structure": "리더형이 전체 목표를 잡고 실행형이 구체적 과업을 수행합니다."
    },
    "실행형+조율형": {
        "summary": "추진력과 공감능력이 조화를 이루는 팀입니다.",
        "structure": "실행형이 행동으로 이끌고 조율형이 팀 내 감정을 조정합니다."
    },
    "실행형+분석형": {
        "summary": "계획과 행동이 적절히 배합된 팀으로, 효과적인 성과를 창출합니다.",
        "structure": "분석형이 계획을 검토하고 실행형이 이를 실현합니다."
    },
    "실행형+창의형": {
        "summary": "창의적 발상을 빠르게 실현하는 팀으로, 혁신 실행력이 높습니다.",
        "structure": "창의형이 아이디어를 생산하고 실행형이 즉각 실행합니다."
    },
    "실행형+헌신형": {
        "summary": "성과 중심의 실천력과 배려 기반의 팀워크가 조화를 이룹니다.",
        "structure": "실행형이 중심을 잡고 헌신형이 분위기를 유지합니다."
    }
}

def generate_team_summary(type_counts):
    total = sum(type_counts.values())
    if total == 0:
        return "", "팀 분석 데이터를 찾을 수 없습니다.", "", "", ""

    percentages = {k: v / total * 100 for k, v in type_counts.items()}
    sorted_types = sorted(percentages.items(), key=lambda x: x[1], reverse=True)
    main_type = sorted_types[0][0]
    main_percent = sorted_types[0][1]
    second_type = sorted_types[1][0] if len(sorted_types) > 1 else None

    # 1. 팀 구성 특성 분석
    if main_percent >= 80:
        trait_text = f"이 팀은 '{main_type}' 성향이 매우 강하게 나타나는 집중형 팀입니다. 특정 방향으로 빠르게 움직일 수 있지만 시야가 편중될 수 있습니다."
    elif second_type and percentages[second_type] >= 30:
        trait_text = f"이 팀은 '{main_type}'와 '{second_type}' 유형이 혼합된 구조로, 두 특성이 조화를 이루며 협업합니다."
    else:
        trait_text = "이 팀은 다양한 성격 유형으로 구성되어 있어 유연하고 다각적인 사고가 가능한 균형형 팀입니다."

    # 2. 팀 분석 요약
    if main_percent >= 80:
        summary = f"이 팀은 모든 구성원이 '{main_type}' 유형으로 구성되어 있어 매우 일관된 성향을 보입니다. {main_type} 유형의 강점은 {type_strengths[main_type]}입니다. 하지만 {type_weaknesses[main_type]} 측면에서는 주의가 필요합니다."
    elif second_type and percentages[second_type] >= 30:
        summary = (
            f"이 팀은 '{main_type}'({percentages[main_type]:.0f}%)와 '{second_type}'({percentages[second_type]:.0f}%) 유형이 주를 이루며, "
            f"두 유형의 특성이 균형 있게 섞여 있습니다. {main_type}은 {type_strengths[main_type]}, "
            f"{second_type}은 {type_strengths[second_type]} 측면에서 강점을 가집니다."
        )
    else:
        summary = "이 팀은 다양한 성격 유형으로 구성되어 있어 창의성과 균형 잡힌 접근이 기대됩니다."

    # 3. 추천 전략
    recommendation_text = ""
    if main_type in type_recommendations:
        recommendation_text = "\n".join(type_recommendations[main_type])

    # 4. 상세 해석 (30개 조합 상세 설명)
    detailed_descriptions = {
        "리더형+조율형": "명확한 목표 설정과 감정 조율이 균형을 이루는 팀입니다. 빠른 결정을 내리는 리더형과 구성원의 감정과 의견을 조율하는 조율형이 상호 보완되어 유연하면서도 추진력 있는 팀 문화를 형성합니다.",
        "리더형+분석형": "리더형의 추진력과 분석형의 신중함이 결합된 팀입니다. 전략 수립과 실행의 균형이 잘 잡히지만, 리더형의 빠른 진행과 분석형의 검토 사이에 충돌이 발생할 수 있습니다.",
        "리더형+창의형": "리더형의 방향성과 창의형의 아이디어가 결합된 혁신적인 팀입니다. 과감한 실행이 가능하지만, 세부 실행력 부족에 유의해야 합니다.",
        "리더형+헌신형": "리더형이 방향을 제시하고 헌신형이 팀의 분위기를 유지하는 이상적인 조합입니다. 다만 권한과 책임의 불균형이 발생할 수 있습니다.",
        "리더형+실행형": "목표 지향적이고 빠른 실행을 중시하는 팀입니다. 결과 중심의 성과를 낼 수 있으나, 감정적 배려나 협의가 부족할 수 있습니다.",
        "조율형+리더형": "조율형이 리더형의 추진력을 부드럽게 조율하는 구조입니다. 팀워크와 속도의 균형을 이룰 수 있으나, 주도권의 경계가 모호해질 수 있습니다.",
        "조율형+분석형": "의견 조율과 신중한 판단이 강조되는 안정적인 팀입니다. 다만 속도나 실행력이 떨어질 수 있습니다.",
        "조율형+창의형": "감정 조율과 창의적 사고가 결합되어 팀 내 소통이 풍부하고 유연합니다. 실행력이 부족할 수 있으니 명확한 추진이 필요합니다.",
        "조율형+헌신형": "배려와 조화가 강조된 부드러운 팀 분위기를 갖습니다. 갈등은 적지만 결단력 부족이 단점이 될 수 있습니다.",
        "조율형+실행형": "조율형의 협업력과 실행형의 추진력이 결합되어 실현 가능성이 높은 팀입니다. 감정과 속도의 균형이 핵심입니다.",
        "분석형+리더형": "분석형의 근거 있는 판단과 리더형의 실행력이 결합되어 전략적이고 실용적인 팀입니다. 속도와 논리의 균형이 필요합니다.",
        "분석형+조율형": "분석과 조율의 조합으로, 설득력 있고 배려 깊은 커뮤니케이션이 가능한 팀입니다. 결정을 미루는 경향에는 주의가 필요합니다.",
        "분석형+창의형": "체계성과 창의성이 조화를 이루어 혁신적인 아이디어를 논리적으로 구현할 수 있는 팀입니다. 실행 속도 조절이 필요합니다.",
        "분석형+헌신형": "신뢰 기반의 조용하고 안정적인 협업이 가능하며, 조심스러운 결정과 배려가 특징입니다. 추진력이 약할 수 있습니다.",
        "분석형+실행형": "분석을 바탕으로 신속하게 실현하는 실행력이 결합되어 안정적이면서도 결과 중심적인 팀입니다.",
        "창의형+리더형": "아이디어 중심의 창의형이 리더형의 추진력과 결합되어 도전적인 목표를 설정하고 추진하는 데 강점을 보입니다.",
        "창의형+조율형": "창의형의 유연한 사고와 조율형의 감성적 소통이 조화를 이루며 새로운 시도를 안전하게 추진할 수 있습니다.",
        "창의형+분석형": "창의적 발상과 체계적 검토가 함께 작동해 실현 가능한 혁신을 이끌 수 있습니다. 다만 속도감은 떨어질 수 있습니다.",
        "창의형+헌신형": "팀 분위기를 부드럽게 이끄는 헌신형과 도전적인 창의형이 조화를 이루어 따뜻하면서도 새로운 시도를 즐기는 팀을 만듭니다.",
        "창의형+실행형": "기발한 아이디어를 빠르게 실현하는 데 강한 팀입니다. 다만 방향성이 명확하지 않으면 비효율이 발생할 수 있습니다.",
        "헌신형+리더형": "분위기를 중시하는 헌신형과 리더형의 방향성이 결합되어 안정성과 추진력을 동시에 추구합니다.",
        "헌신형+조율형": "정서적 안정과 팀워크가 뛰어난 팀입니다. 갈등은 적으나 실행력이 다소 떨어질 수 있습니다.",
        "헌신형+분석형": "배려와 신중함이 강조되어 실수가 적은 팀을 구성할 수 있습니다. 다만 결단력 있는 행동이 부족할 수 있습니다.",
        "헌신형+창의형": "부드럽고 유연한 분위기 속에서 다양한 시도가 가능한 팀입니다. 실행이나 마감 측면에서 보완이 필요할 수 있습니다.",
        "헌신형+실행형": "헌신형의 팀 중심성과 실행형의 추진력이 조화를 이루며, 조화로운 실행이 가능한 팀입니다.",
        "실행형+리더형": "빠른 실행과 명확한 목표 설정이 결합되어 결과 중심의 강력한 팀입니다. 팀원 의견 수렴이 부족할 수 있습니다.",
        "실행형+조율형": "실행형의 추진력과 조율형의 배려가 만나 실행과 감정 조율의 균형 잡힌 팀이 됩니다.",
        "실행형+분석형": "실행의 속도와 분석의 신중함이 조화를 이루어 안정적이고 효과적인 실행이 가능합니다.",
        "실행형+창의형": "빠른 실행과 창의적 아이디어가 결합되어 새로운 프로젝트를 즉시 시작할 수 있는 팀입니다.",
        "실행형+헌신형": "결과 중심의 실행형과 배려 중심의 헌신형이 만나 균형 잡힌 협업을 이룹니다."
    }

    # 5. 소통 및 갈등 구조 해석 (이 부분을 새로 추가!)
    communication_templates = {
    "리더형+조율형": "리더형의 단호함과 조율형의 부드러움이 충돌할 수 있습니다. 리더형은 속도와 추진을, 조율형은 공감과 중재를 중시하므로 결정 과정에서 갈등이 발생할 수 있습니다.",
    "리더형+분석형": "리더형은 빠른 결정과 추진을 선호하고, 분석형은 신중한 검토를 중요시합니다. 속도와 정확성 간의 균형이 필요합니다.",
    "리더형+창의형": "리더형은 방향성과 실행에 집중하고, 창의형은 유연한 사고와 아이디어를 선호합니다. 계획의 일관성과 유연성 사이에서 충돌이 있을 수 있습니다.",
    "리더형+헌신형": "리더형의 추진력이 헌신형에게 압박으로 느껴질 수 있으며, 헌신형은 과도한 책임 회피나 수동적인 자세를 취할 수 있습니다.",
    "리더형+실행형": "두 유형 모두 목표 지향적이고 실행을 중시하므로 빠르게 움직일 수 있지만, 리더십 충돌이나 과도한 경쟁이 발생할 수 있습니다.",

    "조율형+리더형": "조율형은 협조와 중재를, 리더형은 추진과 통제를 중시합니다. 리더형의 강한 의견이 조율형에게 부담이 될 수 있습니다.",
    "조율형+분석형": "조율형의 유연성과 분석형의 신중함은 상호 보완이 되지만, 결정을 미루거나 소극적인 소통이 될 위험이 있습니다.",
    "조율형+창의형": "창의형의 다양한 아이디어가 조율형에게 과부하로 느껴질 수 있으며, 정리되지 않은 생각들이 소통의 혼란을 초래할 수 있습니다.",
    "조율형+헌신형": "두 유형 모두 배려심이 강해 겉으로는 평화로워 보이나, 갈등을 회피하거나 솔직한 의견 교환이 부족할 수 있습니다.",
    "조율형+실행형": "조율형은 공감과 조화를, 실행형은 속도와 결과를 중시합니다. 소통 과정에서 우선순위 충돌이 발생할 수 있습니다.",

    "분석형+리더형": "분석형은 충분한 검토를, 리더형은 빠른 실행을 중시합니다. 분석형은 리더형의 급한 결정에 스트레스를 받을 수 있습니다.",
    "분석형+조율형": "분석형의 논리성과 조율형의 감성은 균형이 될 수 있으나, 소통이 간접적이고 결정을 미루는 경향이 생길 수 있습니다.",
    "분석형+창의형": "창의형의 직관적인 접근이 분석형에게는 비논리적으로 느껴질 수 있으며, 정리 방식의 차이가 갈등으로 이어질 수 있습니다.",
    "분석형+헌신형": "헌신형은 배려 중심이고 분석형은 사실 중심이어서 감정과 데이터 사이에서 이해 충돌이 발생할 수 있습니다.",
    "분석형+실행형": "실행형은 빠른 행동을, 분석형은 검토를 중시합니다. 소통 속도와 정보 전달 방식에 차이가 발생할 수 있습니다.",

    "창의형+리더형": "창의형은 새로운 아이디어를, 리더형은 명확한 방향을 중시합니다. 주도권과 계획 방식의 차이로 긴장이 생길 수 있습니다.",
    "창의형+조율형": "창의형의 확산적 사고가 조율형에게 혼란을 줄 수 있으며, 조율형은 이를 지나치게 정리하려다 갈등이 발생할 수 있습니다.",
    "창의형+분석형": "창의형은 직관적으로, 분석형은 논리적으로 접근합니다. 서로의 접근 방식이 비효율적으로 느껴질 수 있습니다.",
    "창의형+헌신형": "창의형은 자유를, 헌신형은 관계와 조화를 중시합니다. 의견 충돌 시 헌신형이 침묵하거나 피로감을 느낄 수 있습니다.",
    "창의형+실행형": "아이디어 중심의 창의형과 실행 중심의 실행형이 충돌할 수 있습니다. 실행형은 창의형의 변화무쌍함에 혼란을 느낄 수 있습니다.",

    "헌신형+리더형": "리더형의 명확한 지시가 헌신형에게 지나치게 강하게 다가올 수 있으며, 헌신형은 의견을 숨기거나 수동적으로 대할 수 있습니다.",
    "헌신형+조율형": "두 유형 모두 갈등 회피 성향이 있어 솔직한 피드백이 부족할 수 있으며, 쌓인 불만이 뒤늦게 폭발할 가능성이 있습니다.",
    "헌신형+분석형": "헌신형은 감정 중심, 분석형은 논리 중심이기 때문에 의사소통에서 공감 부족이나 단절이 발생할 수 있습니다.",
    "헌신형+창의형": "창의형은 변화와 유연함을 추구하고, 헌신형은 안정과 배려를 중시합니다. 속도와 감정 처리 방식의 차이로 충돌할 수 있습니다.",
    "헌신형+실행형": "헌신형은 과정을, 실행형은 결과를 중시합니다. 실행형의 직설적인 표현이 헌신형에게 상처가 될 수 있습니다.",

    "실행형+리더형": "두 유형 모두 추진력이 강해 방향이 일치하면 강력한 팀이 되지만, 리더십 충돌이나 통제 방식의 차이로 갈등이 생길 수 있습니다.",
    "실행형+조율형": "실행형의 속도와 조율형의 감정 조절이 상충할 수 있습니다. 실행형은 조율형의 신중함을 느리게 느낄 수 있습니다.",
    "실행형+분석형": "실행형은 즉각적 실행을, 분석형은 신중한 검토를 중시합니다. 결정 속도와 정보 신뢰도에 대한 의견 차이가 생길 수 있습니다.",
    "실행형+창의형": "실행형은 즉시 행동을, 창의형은 아이디어 구상을 선호합니다. 실행 우선순위에 대한 불일치가 발생할 수 있습니다.",
    "실행형+헌신형": "실행형의 강한 추진이 헌신형에게 부담이 될 수 있으며, 헌신형은 조율 없는 결과 중심 접근에 피로를 느낄 수 있습니다."
    }


    types = ['리더형', '조율형', '분석형', '창의형', '헌신형', '실행형']
    pair_key = f"{main_type}+{second_type}"
    if pair_key in team_combination_summaries:
        detailed_text = team_combination_summaries[pair_key]["summary"]
        communication_text = team_combination_summaries[pair_key]["structure"]
    else:
        # fallback
        detailed_text = f"이 팀은 {main_type} 중심의 특성이 뚜렷하게 나타나는 구조입니다."
        communication_text = f"{main_type} 유형의 커뮤니케이션 스타일이 팀 내 소통 방식에 큰 영향을 미칠 수 있습니다."


    detailed_text = detailed_descriptions.get(pair_key, "")

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