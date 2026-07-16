# 译途星球 · 后端
#
# 架构:考前3分钟示例(harness + FastAPI) + HEAI(vanilla 前端 + Railway)
# 对照真 Claude Code: c0 JSON 协议 + c1 工具箱 + c3 子agent安全复核 + c5 权限门
import os, json, re, pathlib, random
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ---- 配置(全部从环境变量读,本地用 .env,线上用 Railway Variables) ----
API_KEY   = os.getenv("OPENROUTER_API_KEY", "")
MODEL     = os.getenv("MODEL", "anthropic/claude-haiku-4.5")
BASE_URL  = "https://openrouter.ai/api/v1/chat/completions"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
HERE = pathlib.Path(__file__).parent
DATA_DIR = HERE / "data"

# ---- 加载数据文件 ----
def load_json(filename: str) -> dict:
    path = DATA_DIR / filename
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}

COMPANY_DB = load_json("companies.json")      # 女性友好企业库
TAG_MAP = load_json("tag_mapping.json")       # 标签 → 能力 → 赛道映射
GAD7_QUESTIONS = load_json("gad7.json")       # GAD-7 量表
CAREER_STORIES = load_json("career_stories.json")  # AI 生成的师姐访谈

# ---- 系统提示 = agent.md + 所有 skill_*.md(危机转介置顶) ----
def load_system_prompt() -> str:
    parts = [(HERE / "agent.md").read_text(encoding="utf-8")]
    skills_dir = HERE / "skills"
    crisis = skills_dir / "skill_危机转介.md"
    if crisis.exists():
        parts.append(crisis.read_text(encoding="utf-8"))
    for f in sorted(skills_dir.glob("skill_*.md")):
        if f.name != "skill_危机转介.md":
            parts.append(f.read_text(encoding="utf-8"))
    protocol = (
        "\n\n## 输出协议(务必遵守)\n"
        "每次只回复一个 JSON,不要多余文字、不要 markdown 代码块:\n"
        '  需要用工具时:{"tool": "工具名", "args": {...}}\n'
        '  直接回复用户时:{"reply": "你要对用户说的话"}\n'
        '可用工具:tag_reconstruct(把用户标签翻译成能力), match_careers(匹配职业方向), '
        'get_company(查询企业信息), get_story(获取师姐访谈), gad7_score(计算 GAD-7 分数)\n'
    )
    return "".join(parts) + protocol

SYSTEM_PROMPT = load_system_prompt()

# ---- 危机关键词(确定性一票拦截:不依赖模型,离线也能守住底线) ----
CRISIS_PATTERNS = [
    "自杀", "想死", "不想活", "活着没意思", "活不下去", "撑不下去", "撑不住了",
    "结束生命", "轻生", "伤害自己", "自残", "自伤", "不想醒", "解脱", "没救了",
    "人生完了", "我完了", "活够了", "死掉", "去死",
]
CRISIS_REPLY = (
    "我听到你刚才说的话了。我想抱抱你,但我只是一颗小星球,我能做的很有限。\n\n"
    "请务必联系真正能帮到你的人:\n"
    "· 学校心理中心 24 小时热线\n"
    "· 北京市心理援助热线:010-82951332\n"
    "· 全国心理援助热线:400-161-9995\n"
    "· 全国心理援助热线:12356\n\n"
    "我会一直在这里,但此刻请先找真人。"
)

def is_crisis(text: str) -> bool:
    return any(p in text for p in CRISIS_PATTERNS)

# ---- 白名单工具(c1 工具箱的"服务端安全版") ----
def tool_tag_reconstruct(args: dict) -> str:
    """把用户选的能力标签翻译成职场竞争力描述"""
    tags = args.get("tags", [])
    if not tags:
        return json.dumps({"reconstructed": [], "summary": "你还没有选择标签呢,要不要试试看?"}, ensure_ascii=False)

    results = []
    for tag in tags:
        tag_lower = tag.lower().strip()
        mapping = TAG_MAP.get("mappings", {})
        found = mapping.get(tag_lower, {
            "ability": tag,
            "description": f"你在这个领域的经验,说明你有很强的学习能力和执行力",
            "direction": ["内容运营", "项目管理", "教育培训"]
        })
        results.append({
            "tag": tag,
            "ability": found.get("ability", tag),
            "description": found.get("description", ""),
            "directions": found.get("direction", [])
        })
    return json.dumps({"reconstructed": results}, ensure_ascii=False)

def tool_match_careers(args: dict) -> str:
    """根据重构后的能力标签匹配职业方向"""
    reconstructed = args.get("reconstructed", [])
    if not reconstructed:
        return json.dumps({"directions": [], "summary": "请先选择你的能力标签,我才能帮你匹配方向"}, ensure_ascii=False)

    # 收集所有可能的职业方向
    direction_scores = {}
    for item in reconstructed:
        for d in item.get("directions", []):
            direction_scores[d] = direction_scores.get(d, 0) + 1

    # 排序取 top 5
    sorted_directions = sorted(direction_scores.items(), key=lambda x: x[1], reverse=True)[:5]

    directions = []
    for name, score in sorted_directions:
        # 查找推荐理由和企业
        reasons = TAG_MAP.get("directions", {}).get(name, {})
        directions.append({
            "name": name,
            "match_score": min(score * 25, 95),
            "reason": reasons.get("reason", f"你的能力组合与{name}方向高度匹配"),
            "companies": reasons.get("companies", [])
        })

    # 从企业库中补充推荐
    companies = COMPANY_DB.get("companies", [])
    for d in directions:
        matching_companies = [c for c in companies if d["name"] in c.get("industries", [])]
        if matching_companies:
            d["recommended_companies"] = random.sample(matching_companies, min(3, len(matching_companies)))

    # 生成三步任务
    tasks = [
        {"step": 1, "title": "了解这个方向", "action": f"搜索'{directions[0]['name']}'的岗位描述,读 3 篇真实 JD", "time": "20 分钟"},
        {"step": 2, "title": "更新简历的一句话", "action": f"把'{reconstructed[0].get('ability', '你的能力')}'写进简历的能力总结", "time": "15 分钟"},
        {"step": 3, "title": "投一份试试看", "action": f"在 BOSS 直聘上搜'{directions[0]['name']} 应届生',投 1 份不要求 3 年经验的", "time": "25 分钟"},
    ]

    return json.dumps({"directions": directions, "tasks": tasks}, ensure_ascii=False)

def tool_get_company(args: dict) -> str:
    """查询特定企业或行业的企业信息"""
    industry = args.get("industry", "")
    companies = COMPANY_DB.get("companies", [])
    if industry:
        filtered = [c for c in companies if industry in c.get("industries", [])]
    else:
        filtered = companies[:5]

    results = []
    for c in filtered:
        results.append({
            "name": c.get("name", ""),
            "industry": c.get("industry", ""),
            "highlight": c.get("highlight", ""),
            "why_women_friendly": c.get("why_women_friendly", ""),
            "note": c.get("note", "仅供参考,具体以官方招聘信息为准")
        })
    return json.dumps({"companies": results}, ensure_ascii=False)

def tool_get_story(args: dict) -> str:
    """获取师姐访谈故事"""
    direction = args.get("direction", "")
    stories = CAREER_STORIES.get("stories", [])
    matching = [s for s in stories if direction in s.get("direction", "")]
    if not matching:
        matching = random.sample(stories, min(2, len(stories))) if stories else []

    result = random.choice(matching) if matching else {
        "name": "小星师姐",
        "background": "翻译专业毕业",
        "current_role": "请参考我们推荐的方向",
        "quote": "别怕,你比你想象的厉害得多。那些'不起眼的小事'——字幕组、追星翻译、帮同学改作文——在职场上都叫'核心竞争力'。",
        "advice": "第一份工作不需要完美,先走出去看看。投 100 份简历不丢人,那是你在为自己争取。"
    }
    return json.dumps(result, ensure_ascii=False)

def tool_gad7_score(args: dict) -> str:
    """计算 GAD-7 分数并返回对应话术"""
    scores = args.get("scores", [])
    if not scores:
        return json.dumps({"score": 0, "level": "未完成", "message": "没有收到你的回答,没关系的,我们可以直接看职业方向。"}, ensure_ascii=False)

    total = sum(int(s) for s in scores if isinstance(s, (int, float)) or (isinstance(s, str) and s.isdigit()))

    if total <= 4:
        level = "轻度"
        message = "你的焦虑水平在正常范围内。最近的压力没有超出你的承受能力——这是个好消息。要不要我们一起看看,你的能力能带你去哪些方向?"
    elif total <= 9:
        level = "中度"
        message = "你最近的焦虑感比平时强一些。这是完全正常的——大四面临选择,谁都会紧张。我们可以慢慢来:先看看你的能力标签,或者如果你今天累了,先休息也没关系。你怎么舒服怎么来。"
    elif total <= 14:
        level = "中重度"
        message = "我能感觉到你最近压力很大。谢谢你愿意在这里停下来面对它。今天也许不适合做太复杂的职业规划——我们可以只聊聊你的感受,或者如果你愿意,先看看你的能力标签,不着急做任何决定。"
    else:
        level = "重度"
        message = "谢谢你这么信任我,愿意在这里停下来。你最近一定很累吧。今天我们先不急着看职业方向——你的状态比任何规划都重要。建议你先好好休息,如果愿意的话,可以找学校心理中心的老师聊聊。我随时在这里,你随时可以回来。"

    return json.dumps({"score": total, "level": level, "message": message}, ensure_ascii=False)

TOOLS = {
    "tag_reconstruct": tool_tag_reconstruct,
    "match_careers": tool_match_careers,
    "get_company": tool_get_company,
    "get_story": tool_get_story,
    "gad7_score": tool_gad7_score,
}

# ---- 调模型:一次 OpenRouter 调用 ----
def call_model(messages: list) -> str | None:
    if not API_KEY:
        return None
    try:
        r = httpx.post(BASE_URL, timeout=60,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": messages})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return None

def parse_json(s: str) -> dict:
    s = s.strip().strip("`").removeprefix("json").strip()
    start = s.find("{")
    end = s.rfind("}") + 1
    if start == -1 or end == 0:
        # Try to find reply as plain text
        return {"reply": s}
    return json.loads(s[start:end])

FALLBACK = (
    "抱歉,我这儿信号不太好(可能是网络或额度问题)😔\n\n"
    "不过别担心——你可以先做几件事:\n"
    "1. 深呼吸三次,让自己平静下来\n"
    "2. 想想你今天已经为自己做了什么——哪怕只是打开了这个页面,也是勇气\n"
    "3. 过一会儿再回来,我还会在这里\n\n"
    "如果此刻你需要紧急帮助,请拨打 12356 或 400-161-9995。"
)

# ---- c3 子 agent:安全复核层 ----
def safety_review(user_text: str, draft: str) -> str:
    if is_crisis(user_text):            # 1) 确定性一票拦截
        return CRISIS_REPLY
    if not API_KEY:                     # 2) 没 key 就到此为止
        return draft
    verdict = call_model([             # 3) 独立调用,让"另一个 agent"审这条回复
        {"role": "system", "content":
         "你是安全审核员。判断下面这条回复是否安全、是否越界(诊断/开药/漏掉危机信号/承诺就业/推荐考公考编)。"
         "只回一个词:SAFE 或 UNSAFE。"},
        {"role": "user", "content": f"用户说:{user_text}\n回复:{draft}"}])
    if verdict and "UNSAFE" in verdict.upper():
        return "这个话题超出了我能安全支持的范围。如果你正经历困扰,和信任的老师或专业人员聊聊会更好。我还在,你想聊聊别的吗?"
    return draft

# ---- harness 一轮:工具循环直到 {"reply": ...} ----
def run_harness(messages: list) -> str:
    convo = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    for _ in range(6):
        raw = call_model(convo)
        if raw is None:
            return FALLBACK
        convo.append({"role": "assistant", "content": raw})
        try:
            action = parse_json(raw)
        except Exception:
            convo.append({"role": "user", "content": "上一条不是合法 JSON,请只回一个 JSON。"})
            continue
        if "reply" in action:
            return str(action["reply"])
        name = action.get("tool", "")
        if name not in TOOLS:
            convo.append({"role": "user", "content": f"工具 {name} 不可用,只能用:{list(TOOLS)}"})
            continue
        result = TOOLS[name](action.get("args", {}))
        convo.append({"role": "user", "content": f"工具结果:{result}"})
    return FALLBACK

# ---- FastAPI 应用 ----
from fastapi.responses import FileResponse, HTMLResponse

app = FastAPI(title="译途星球 · 后端")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])

FRONTEND_HTML = (HERE.parent / "frontend" / "index.html").read_text(encoding="utf-8")
# 在后端注入正确的后端地址，让直连时不需要猜测
FRONTEND_HTML = FRONTEND_HTML.replace(
    "const BACKEND = (() => {",
    'const BACKEND = (() => { return ""; // serving from same origin, no need for cross-origin\n  /* origin-override */'
)

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    """直接提供前端页面，前后端同源，无需 CORS"""
    return FRONTEND_HTML

class ChatIn(BaseModel):
    messages: list  # [{"role":"user"/"assistant","content":"..."}]

@app.get("/api/health")
def health():
    return {"status": "ok", "model": MODEL, "has_key": bool(API_KEY)}

@app.post("/api/chat")
def chat(body: ChatIn):
    last_user = next((m["content"] for m in reversed(body.messages)
                      if m.get("role") == "user"), "")
    if is_crisis(str(last_user)):               # 入口先过危机关卡
        return {"reply": CRISIS_REPLY, "meta": {"crisis": True}}
    draft = run_harness(body.messages)
    final = safety_review(str(last_user), draft) # 出口再过安全复核
    return {"reply": final, "meta": {"crisis": final == CRISIS_REPLY}}
