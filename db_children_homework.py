import os
import sys
import json
import sqlite3
from datetime import datetime, date

# Directory setup
current_dir = os.path.dirname(os.path.abspath(__file__))
LOCAL_DB_PATH = os.path.join(current_dir, "homework.db")
TEMPLATES_EXPORT_PATH = os.path.join(current_dir, "templates_export.json")

# Default to independent local homework.db (or custom path from env)
DB_PATH = os.environ.get("CHILDREN_DB_PATH", LOCAL_DB_PATH)

DEFAULT_CATEGORIES = [
	"♟️ 教妹妹围棋",
	"📖 语文天地",
	"📐 数学探索",
	"🔤 英语口语",
	"🏃 体育运动",
	"🔬 科学思维",
	"📚 每日阅读"
]

MEMBERS = [
	{"student_no": "PYP001", "name": "潘翼芃", "role": "哥哥 / 围棋小老师", "gender": "男", "grade": "五年级", "class_name": "成长小分队", "parent_name": "爸爸妈妈", "parent_phone": "13800000001"},
	{"student_no": "PYN002", "name": "潘一柠", "role": "妹妹 / 学习小能手", "gender": "女", "grade": "二年级", "class_name": "成长小分队", "parent_name": "爸爸妈妈", "parent_phone": "13800000002"}
]

# 围棋教学关卡体系（初级、中级、高级三阶段进阶路线）
WEIQI_STAGES = [
	{
		"stage_id": "beginner",
		"level_num": 1,
		"name": "初级阶段（第 1-2 月）：能下完一盘棋",
		"short_name": "初级阶段：能下完一盘棋",
		"tag": "入门筑基",
		"icon": "🟢",
		"duration": "第 1-2 月",
		"goal": "从零到“能完整下完一盘 9 路棋，知道怎么算胜负”。",
		"core_progress": "从“不会下”到“能下完”",
		"checklist": [
			"能独立下完 9 路棋",
			"能数子判断胜负",
			"吃子题正确率达到 80%"
		],
		"modules": [
			{"order": 1, "name": "规则入门", "content": "气、提子、禁着点、打劫", "timeline": "第 1-2 周"},
			{"order": 2, "name": "吃子技巧", "content": "双叫吃、征子、枷吃、倒扑", "timeline": "第 3-5 周"},
			{"order": 3, "name": "终局计算", "content": "数子法、判断胜负", "timeline": "第 6 周"},
			{"order": 4, "name": "9路实战", "content": "完整下完一盘 9 路棋", "timeline": "第 7-8 周"}
		]
	},
	{
		"stage_id": "intermediate",
		"level_num": 2,
		"name": "中级阶段（第 3-4 月）：死活入门 + 13 路实战",
		"short_name": "中级阶段：死活入门与13路实战",
		"tag": "死活攻防",
		"icon": "🟡",
		"duration": "第 3-4 月",
		"goal": "从“能下完”到“能判断一块棋的死活”。",
		"core_progress": "从“乱下”到“能看出死活”",
		"checklist": [
			"能判断直三、弯三、直四、弯四的死活",
			"13 路棋能下完",
			"死活题正确率达到 75%"
		],
		"modules": [
			{"order": 1, "name": "基础死活型", "content": "直三、弯三、直四、弯四、方四、丁四", "timeline": "第 1-3 周"},
			{"order": 2, "name": "做眼与破眼", "content": "真假眼判断、做眼方法、破眼方法", "timeline": "第 4-5 周"},
			{"order": 3, "name": "简单对杀", "content": "数气、对杀基本判断", "timeline": "第 6 周"},
			{"order": 4, "name": "13路实战", "content": "完整下完一盘 13 路棋", "timeline": "第 7-8 周"}
		]
	},
	{
		"stage_id": "advanced",
		"level_num": 3,
		"name": "高级阶段（第 5-6 月）：19 路对弈 + 综合实战",
		"short_name": "高级阶段：19路对弈与综合实战",
		"tag": "全局对弈",
		"icon": "🟣",
		"duration": "第 5-6 月",
		"goal": "从“会判断死活”到“能和哥哥完整对弈一盘 19 路棋”。",
		"core_progress": "从“能下”到“能对弈”",
		"checklist": [
			"能完整下完 19 路棋",
			"能判断常见死活型",
			"知道角→边→中腹的优先级",
			"能和哥哥对弈一盘（让 2-4 子）"
		],
		"modules": [
			{"order": 1, "name": "布局常识", "content": "角→边→中腹、星位小飞挂", "timeline": "第 1-2 周"},
			{"order": 2, "name": "连接与分断", "content": "基本连接方法、分断技巧", "timeline": "第 3-4 周"},
			{"order": 3, "name": "官子入门", "content": "先手后手、简单目数计算", "timeline": "第 5 周"},
			{"order": 4, "name": "19路实战", "content": "完整对弈 + 复盘", "timeline": "第 6-8 周"}
		]
	}
]

# Load structured Weiqi Curriculum with board puzzles if available
CURRICULUM_JSON_PATH = os.path.join(current_dir, "weiqi_templates_curriculum.json")
try:
	with open(CURRICULUM_JSON_PATH, "r", encoding="utf-8") as f:
		_curriculum_data = json.load(f)
		WEIQI_CURRICULUM = _curriculum_data.get("stages", WEIQI_STAGES)
except Exception:
	WEIQI_CURRICULUM = WEIQI_STAGES

def get_db_connection(db_path=DB_PATH):
	"""Returns a connection to the SQLite database with row_factory set."""
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	return conn

def init_db(db_path=DB_PATH):
	"""Initializes the database tables and guarantees correct schema."""
	conn = get_db_connection(db_path)
	cursor = conn.cursor()

	# Check and migrate templates table if schema was old (subject vs category)
	try:
		cursor.execute("PRAGMA table_info(templates)")
		cols = [col["name"] for col in cursor.fetchall()]
		if cols and 'category' not in cols:
			cursor.execute("DROP TABLE IF EXISTS templates")
	except Exception:
		pass

	# Check and migrate homework table if schema was old
	try:
		cursor.execute("PRAGMA table_info(homework)")
		hw_cols = [col["name"] for col in cursor.fetchall()]
		if hw_cols and 'category' not in hw_cols:
			cursor.execute("DROP TABLE IF EXISTS submissions")
			cursor.execute("DROP TABLE IF EXISTS homework")
	except Exception:
		pass

	# Check and migrate students table
	try:
		cursor.execute("PRAGMA table_info(students)")
		st_cols = [col["name"] for col in cursor.fetchall()]
		if st_cols and 'flowers' not in st_cols:
			cursor.execute("DROP TABLE IF EXISTS submissions")
			cursor.execute("DROP TABLE IF EXISTS students")
		elif st_cols and 'avatar' not in st_cols:
			cursor.execute("ALTER TABLE students ADD COLUMN avatar VARCHAR(20) DEFAULT '👤'")
			cursor.execute("UPDATE students SET avatar = '👦' WHERE name = '潘翼芃'")
			cursor.execute("UPDATE students SET avatar = '👧' WHERE name = '潘一柠'")
	except Exception:
		pass

	# Check and migrate submissions table for subtasks_status
	try:
		cursor.execute("PRAGMA table_info(submissions)")
		sub_cols = [col["name"] for col in cursor.fetchall()]
		if sub_cols and 'subtasks_status' not in sub_cols:
			cursor.execute("ALTER TABLE submissions ADD COLUMN subtasks_status TEXT DEFAULT '[]'")
	except Exception:
		pass

	# Check and migrate weiqi_lessons table
	try:
		cursor.execute("PRAGMA table_info(weiqi_lessons)")
		w_cols = [col["name"] for col in cursor.fetchall()]
		if w_cols:
			if 'teacher_name' not in w_cols:
				cursor.execute("ALTER TABLE weiqi_lessons ADD COLUMN teacher_name VARCHAR(50) DEFAULT '潘翼芃'")
			if 'student_name' not in w_cols:
				cursor.execute("ALTER TABLE weiqi_lessons ADD COLUMN student_name VARCHAR(50) DEFAULT '潘一柠'")
			if 'status' not in w_cols:
				cursor.execute("ALTER TABLE weiqi_lessons ADD COLUMN status VARCHAR(30) DEFAULT 'completed'")
	except Exception:
		pass

	# 1. Homework / Tasks Table
	cursor.execute("""
		CREATE TABLE IF NOT EXISTS homework (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title VARCHAR(150) NOT NULL,
			category VARCHAR(50) NOT NULL,
			assignee VARCHAR(50) DEFAULT '全员',
			due_date DATE NOT NULL,
			due_time VARCHAR(20) DEFAULT '20:00',
			content TEXT NOT NULL,
			requirements TEXT,
			reward_flowers INTEGER DEFAULT 1,
			status VARCHAR(30) DEFAULT 'published',
			wechat_text TEXT,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	""")

	# 2. Reusable Quick Templates Table
	cursor.execute("""
		CREATE TABLE IF NOT EXISTS templates (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name VARCHAR(100) NOT NULL,
			category VARCHAR(50) NOT NULL,
			assignee VARCHAR(50) DEFAULT '全员',
			content TEXT NOT NULL,
			requirements TEXT,
			reward_flowers INTEGER DEFAULT 1,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	""")

	# 3. Members / Children Table
	cursor.execute("""
		CREATE TABLE IF NOT EXISTS students (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			student_no VARCHAR(50) UNIQUE,
			name VARCHAR(50) NOT NULL,
			role VARCHAR(50) DEFAULT '队员',
			gender VARCHAR(10) DEFAULT '男',
			grade VARCHAR(50) DEFAULT '五年级',
			class_name VARCHAR(50) DEFAULT '成长小分队',
			flowers INTEGER DEFAULT 0,
			stars INTEGER DEFAULT 0,
			parent_name VARCHAR(50),
			parent_phone VARCHAR(50),
			status VARCHAR(20) DEFAULT 'active'
		)
	""")

	# 4. Student Task Submissions & Check-ins Table
	cursor.execute("""
		CREATE TABLE IF NOT EXISTS submissions (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			homework_id INTEGER NOT NULL,
			student_id INTEGER NOT NULL,
			student_name VARCHAR(50) NOT NULL,
			subtasks_status TEXT DEFAULT '[]',
			status VARCHAR(30) DEFAULT 'pending',
			score VARCHAR(20),
			remark TEXT,
			submitted_at TIMESTAMP,
			FOREIGN KEY (homework_id) REFERENCES homework(id) ON DELETE CASCADE,
			FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
			UNIQUE (homework_id, student_id)
		)
	""")

	# 5. Weiqi Lessons Progress Table (教妹妹围棋专属记录)
	cursor.execute("""
		CREATE TABLE IF NOT EXISTS weiqi_lessons (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			level INTEGER NOT NULL,
			lesson_title VARCHAR(150) NOT NULL,
			teacher_name VARCHAR(50) DEFAULT '潘翼芃',
			student_name VARCHAR(50) DEFAULT '潘一柠',
			teaching_content TEXT NOT NULL,
			sister_feedback TEXT,
			star_rating INTEGER DEFAULT 5,
			lesson_date DATE NOT NULL,
			status VARCHAR(30) DEFAULT 'completed',
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	""")

	# Create indexes
	cursor.execute("CREATE INDEX IF NOT EXISTS idx_hw_due_date ON homework(due_date)")
	cursor.execute("CREATE INDEX IF NOT EXISTS idx_hw_category ON homework(category)")
	cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_hw_id ON submissions(homework_id)")
	cursor.execute("CREATE INDEX IF NOT EXISTS idx_weiqi_date ON weiqi_lessons(lesson_date)")

	conn.commit()

	# Seed members if empty
	cursor.execute("SELECT COUNT(*) FROM students")
	if cursor.fetchone()[0] == 0:
		seed_default_members(cursor)
		conn.commit()

	# Seed default templates ONLY if empty (preserves user-edited & cloned templates)
	cursor.execute("SELECT COUNT(*) FROM templates")
	if cursor.fetchone()[0] == 0:
		if os.path.exists(TEMPLATES_EXPORT_PATH):
			conn.close()
			import_templates_from_json(db_path, TEMPLATES_EXPORT_PATH)
			conn = get_db_connection(db_path)
			cursor = conn.cursor()
		else:
			seed_default_templates(cursor)
			conn.commit()
			conn.close()
			export_templates_to_json(db_path, TEMPLATES_EXPORT_PATH)
			conn = get_db_connection(db_path)
			cursor = conn.cursor()

	# Seed initial tasks & weiqi lessons
	cursor.execute("SELECT COUNT(*) FROM homework")
	if cursor.fetchone()[0] == 0:
		seed_sample_tasks(cursor)
		conn.commit()

	cursor.execute("SELECT COUNT(*) FROM weiqi_lessons")
	if cursor.fetchone()[0] == 0:
		seed_sample_weiqi_lessons(cursor)
		conn.commit()

	conn.close()

def seed_default_members(cursor):
	"""Populates 潘翼芃 and 潘一柠 with 0 initial reward flowers and stars."""
	for m in MEMBERS:
		flowers = 0
		stars = 0
		cursor.execute("""
			INSERT INTO students (student_no, name, role, gender, grade, class_name, flowers, stars, parent_name, parent_phone)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		""", (m["student_no"], m["name"], m["role"], m["gender"], m["grade"], m["class_name"], flowers, stars, m["parent_name"], m["parent_phone"]))

def reset_all_flowers_and_stars(db_path=DB_PATH):
	"""Resets flowers and stars for all members to 0."""
	conn = get_db_connection(db_path)
	cursor = conn.cursor()
	cursor.execute("UPDATE students SET flowers = 0, stars = 0")
	conn.commit()
	conn.close()

def seed_default_templates(cursor):
	"""Populates preset homework templates grouped by categories with 初级、中级、高级 Weiqi stages."""
	templates = [
		# ========================================================
		# ♟️ 教妹妹围棋 (初级阶段：第1-2月 · 能下完一盘棋)
		# ========================================================
		(
			"♟️ 围棋·初级模板1-1：认识棋盘与气",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥带妹妹认识 9 路棋盘：天元、星位、边、角。\n2. 哥哥摆一颗黑子，带妹妹数它的气（中间 4 气、边上 3 气、角上 2 气）。\n3. 哥哥出 5 道题：指出每颗棋子的气在哪里。\n4. 兄妹玩“数气比赛”：哥哥摆子，妹妹抢答气数，答对得 1 分。",
			"【阶段检验】妹妹能独立数出中间、边上、角上棋子的气。\n【温馨提示】答对积极给予击掌鼓励！",
			2
		),
		(
			"♟️ 围棋·初级模板1-2：提子与禁着点",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆一颗只剩 1 气的白子，问妹妹：“下哪里能提掉它？”\n2. 妹妹找到位置后，哥哥讲解“提子”的规则。\n3. 哥哥摆出“禁着点”的例子（下进去自己没气），让妹妹判断能不能下。\n4. 出 5 道题：判断哪些位置可以下、哪些不能下。",
			"【阶段检验】妹妹能说出“下进去自己没气就不能下”。",
			2
		),
		(
			"♟️ 围棋·初级模板1-3：打劫",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出最简单的打劫形状。\n2. 妹妹提子后，哥哥想马上提回，问：“这样可以吗？”\n3. 讲解规则：打劫后必须先在别处下一手，才能提回。\n4. 兄妹实战演练 3 次打劫过程。",
			"【阶段检验】妹妹能说出“打劫不能马上提回，要先找劫材”。",
			2
		),
		(
			"♟️ 围棋·初级模板2-1：双叫吃",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出两颗白子，各剩 2 气，中间有一个共同的气点。\n2. 引导妹妹找到那个“一子打两处”的位置。\n3. 出 5 道双叫吃题，妹妹独立找点。\n4. 兄妹下 1 盘 9 路吃子棋，鼓励用双叫吃。",
			"【阶段检验】妹妹能独立找出双叫吃的点。",
			2
		),
		(
			"♟️ 围棋·初级模板2-2：征子",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出最简单的征子形状，一步一步带妹妹追。\n2. 让妹妹自己追一遍，哥哥在旁边提示方向。\n3. 哥哥摆出“征子不利”的例子（前方有接应），问：“还能征吗？”\n4. 出 5 道征子题：判断能不能征掉。",
			"【阶段检验】妹妹能追征 3 步以上，能看出前方有子时不能征。",
			2
		),
		(
			"♟️ 围棋·初级模板2-3：枷吃",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出枷吃形状，问：“不紧气能吃到吗？”\n2. 演示枷吃：从外面罩住，对方跑不掉。\n3. 出 5 道枷吃题，妹妹找罩的位置。\n4. 和征子对比：什么时候用征、什么时候用枷。",
			"【阶段检验】妹妹能区分征子和枷吃的使用场景。",
			2
		),
		(
			"♟️ 围棋·初级模板2-4：倒扑",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥在棋盘一路摆出白棋虎口死活（黑子：A1, A2, B3, C3, D2, E1；白子：B1, B2, C2, D1）。\n2. 引导妹妹观察 C1 虎口：“如果黑棋送一个子到 C1 虎口，会发生什么？”\n3. 妹妹执黑演练 3 步倒扑：黑1送吃(C1) ➔ 白2提吃 ➔ 黑3倒扑全提白棋整块！\n4. 总结口诀：“送子入虎口，倒扑全拿走！”",
			"【阶段检验】妹妹能独立摆出 C1 倒扑并说出口诀。",
			2
		),
		(
			"♟️ 围棋·初级模板3-1：数子法入门",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥在 9 路棋盘上摆一个简单终局局面。\n2. 带妹妹数黑棋围的地盘 + 黑子数。\n3. 再数白棋，比较谁多。\n4. 出 3 道简单数子题，妹妹独立数。",
			"【阶段检验】妹妹能独立数完 9 路棋盘并说出谁赢。",
			2
		),
		(
			"♟️ 围棋·初级模板3-2：判断胜负",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥讲解：9 路棋盘共 81 点，超过 40.5 就赢。\n2. 摆出 3 个终局局面，让妹妹判断输赢。\n3. 兄妹下 1 盘 9 路棋，下完后一起数子。\n4. 妹妹自己宣布结果。",
			"【阶段检验】妹妹能自己数子并宣布“黑棋赢几子”。",
			2
		),
		(
			"♟️ 围棋·初级模板4-1：完整下完一盘",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥让 9 子，和妹妹下 1 盘 9 路棋。\n2. 过程中哥哥不纠正，下完后一起复盘。\n3. 复盘只讲 1 个点：比如“这步棋如果下这里会更好”。\n4. 连下 3 盘，每盘只讲 1 个点。",
			"【阶段检验】妹妹能独立下完 3 盘 9 路棋。",
			3
		),
		(
			"♟️ 围棋·初级模板4-2：吃子小游戏",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 规则：9 路盘，先吃到 3 颗子获胜。\n2. 哥哥让 4 子，和妹妹玩 3 局。\n3. 每局结束后问：“刚才哪一步吃得最漂亮？”\n4. 输赢都夸具体的一步。",
			"【阶段检验】妹妹能在游戏中主动使用双叫吃、征子等技巧。",
			2
		),
		(
			"♟️ 围棋·初级模板4-3：阶段性对弈",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥让 6 子，和妹妹下 1 盘完整 9 路棋。\n2. 下完后一起数子，妹妹宣布结果。\n3. 哥哥问 3 个问题：\n   - 这盘你吃得最开心的是哪步？\n   - 哪块棋你觉得死了但还活着？\n   - 下次想改进什么？\n4. 记录结果，作为进入中级的依据。",
			"【阶段检验】能下完、能数子、能说出 1 个改进点。\n【核心进步】妹妹达成从“不会下”到“能下完”里程碑！",
			3
		),

		# ========================================================
		# ♟️ 教妹妹围棋 (中级阶段：第3-4月 · 死活入门 + 13路实战)
		# ========================================================
		(
			"♟️ 围棋·中级模板1-1：直三与弯三",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出直三形状（三个空点连成直线），问：“这块棋是死是活？”\n2. 让妹妹试着做眼，哥哥应对破眼，演示“直三是死棋”。\n3. 再摆弯三，同样演示一遍。\n4. 出 5 道题：判断是直三还是弯三，说出死活。",
			"【阶段检验】妹妹能一眼认出直三、弯三，并说出“死棋”。",
			2
		),
		(
			"♟️ 围棋·中级模板1-2：直四与弯四",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出直四，问：“和直三有什么不一样？”\n2. 让妹妹试着破眼，发现破不掉，得出“直四是活棋”。\n3. 再摆弯四，同样演示。\n4. 出 5 道题：混合直三、弯三、直四、弯四，判断死活。",
			"【阶段检验】妹妹能区分“三死四活”。",
			2
		),
		(
			"♟️ 围棋·中级模板1-3：方四与丁四",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出方四（四个空点围成正方形），问：“几个眼？”\n2. 演示方四做不出两只眼，是死棋。\n3. 再摆丁四，演示对方先下则死、自己先下则活。\n4. 出 5 道题：判断方四、丁四的死活。",
			"【阶段检验】妹妹能说出“方四是死棋，丁四看谁先下”。",
			2
		),
		(
			"♟️ 围棋·中级模板1-4：死活型综合练习",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥把六种形状（直三、弯三、直四、弯四、方四、丁四）混在一起摆 10 道题。\n2. 妹妹独立判断死活，哥哥记录正确率。\n3. 错题重新摆一遍，让妹妹自己找出错在哪。\n4. 正确率低于 70% 就回到对应模板重练。",
			"【阶段检验】10 道题正确率 75% 以上。",
			3
		),
		(
			"♟️ 围棋·中级模板2-1：真眼与假眼",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出一个真眼、一个假眼，问：“哪个是真的？”\n2. 讲解判断方法：看眼角有没有被对方占。\n3. 出 5 道题：判断真假眼。\n4. 妹妹自己摆一个真眼、一个假眼给哥哥看。",
			"【阶段检验】妹妹能说出“眼角被占就是假眼”。",
			2
		),
		(
			"♟️ 围棋·中级模板2-2：做眼方法",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出一块只有一只眼的棋，问：“怎么做出第二只眼？”\n2. 引导妹妹找到做眼的位置。\n3. 出 5 道做眼题，妹妹独立找点。\n4. 实战中鼓励妹妹主动做眼。",
			"【阶段检验】妹妹能在 5 道题中做对 4 道。",
			2
		),
		(
			"♟️ 围棋·中级模板2-3：破眼方法",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出对方快要做活的棋，问：“下哪里能破眼？”\n2. 讲解“先占眼角”“从外面缩小”两种破眼思路。\n3. 出 5 道破眼题，妹妹独立找点。\n4. 和做眼题混合练习，区分“我是做眼还是破眼”。",
			"【阶段检验】妹妹能区分做眼和破眼，正确率 75%。",
			2
		),
		(
			"♟️ 围棋·中级模板3-1：数气",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出两块对杀的黑白棋，问：“各几气？”\n2. 带妹妹数气：外气、内气、公气。\n3. 出 5 道数气题。\n4. 得出规则：气多的一方对杀赢。",
			"【阶段检验】妹妹能独立数出对杀双方的气。",
			2
		),
		(
			"♟️ 围棋·中级模板3-2：对杀基本判断",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出 3 种对杀局面：气多、气少、气相同。\n2. 让妹妹判断：“能杀吗？还是要跑？”\n3. 讲解“气相同看谁先下”。\n4. 出 5 道对杀判断题。",
			"【阶段检验】妹妹能判断“气多杀、气少跑、气同看先后”。",
			2
		),
		(
			"♟️ 围棋·中级模板4-1：13路完整对弈",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥让 6 子，和妹妹下 1 盘 13 路棋。\n2. 过程中哥哥不纠正，下完后一起数子。\n3. 复盘只讲 1 个死活相关的点。\n4. 连下 3 盘，每盘只讲 1 个点。",
			"【阶段检验】妹妹能独立下完 3 盘 13 路棋。",
			3
		),
		(
			"♟️ 围棋·中级模板4-2：死活专项复盘",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 下完棋后，哥哥找出盘中一块有死活问题的棋。\n2. 问妹妹：“这块棋是死是活？为什么？”\n3. 让妹妹重新摆一遍，试着做活或杀棋。\n4. 记录妹妹的判断正确率。",
			"【阶段检验】妹妹能指出盘中 1-2 处死活问题。",
			2
		),
		(
			"♟️ 围棋·中级模板4-3：阶段性对弈",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥让 4 子，和妹妹下 1 盘完整 13 路棋。\n2. 下完后一起数子，妹妹宣布结果。\n3. 哥哥问 3 个问题：\n   - 这盘你判断对了哪块棋的死活？\n   - 哪块棋判断错了？\n   - 下次想改进什么？\n4. 记录结果，作为进入高级的依据。",
			"【阶段检验】能下完、能数子、能说出 1 个死活判断。\n【核心进步】妹妹达成从“乱下”到“能看出死活”里程碑！",
			3
		),

		# ========================================================
		# ♟️ 教妹妹围棋 (高级阶段：第5-6月 · 19路对弈 + 综合实战)
		# ========================================================
		(
			"♟️ 围棋·高级模板1-1：角→边→中腹",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥在 19 路棋盘上摆出空棋盘，问：“先下哪里？”\n2. 讲解“金角银边草肚皮”：角最容易围地，边次之，中腹最难。\n3. 摆出 3 个布局例子，让妹妹指出哪步下得好。\n4. 妹妹自己在空棋盘上摆 4 步，哥哥点评。",
			"【阶段检验】妹妹能说出“先占角，再占边，最后中腹”。",
			2
		),
		(
			"♟️ 围棋·高级模板1-2：星位与小飞挂",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥指出棋盘上的星位，让妹妹数一共有几个。\n2. 摆出“星位小飞挂”的形状，讲解这是最基础的接触。\n3. 让妹妹自己摆一遍星位 + 小飞挂。\n4. 出 3 道题：指出星位在哪、小飞挂下在哪。",
			"【阶段检验】妹妹能独立摆出星位小飞挂。",
			2
		),
		(
			"♟️ 围棋·高级模板1-3：布局实战",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥让 4 子，和妹妹下 1 盘 19 路棋，只下前 20 手。\n2. 下完后问：“这 20 手，哪几步占了角？”\n3. 讲解妹妹布局中的 1 个问题。\n4. 重复 3 次，每次只讲 1 个点。",
			"【阶段检验】妹妹前 10 手能主动占角。",
			3
		),
		(
			"♟️ 围棋·高级模板2-1：基本连接",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出两块快被分断的棋，问：“怎么连？”\n2. 讲解“粘”“虎”“尖”三种连接方法。\n3. 出 5 道连接题，妹妹找连接点。\n4. 实战中鼓励妹妹主动连接。",
			"【阶段检验】妹妹能用 3 种方法连接。",
			2
		),
		(
			"♟️ 围棋·高级模板2-2：分断技巧",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出对方两块棋，问：“下哪里能切断？”\n2. 讲解“断”“扳断”“冲断”三种方法。\n3. 出 5 道分断题，妹妹找断点。\n4. 和连接题混合练习，区分“我该连还是该断”。",
			"【阶段检验】妹妹能区分连接和分断，正确率 75%。",
			2
		),
		(
			"♟️ 围棋·高级模板2-3：连接与分断实战",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥让 4 子，和妹妹下 1 盘 19 路棋。\n2. 下完后找出盘中 1 处连接或分断的问题。\n3. 问妹妹：“这步如果下这里会怎样？”\n4. 重复 3 次。",
			"【阶段检验】妹妹能指出盘中 1 处连接或分断问题。",
			3
		),
		(
			"♟️ 围棋·高级模板3-1：先手与后手",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出两个官子：一个先手、一个后手。\n2. 问：“先下哪个？”\n3. 讲解“先手可以继续下，后手会被对方抢”。\n4. 出 5 道题：判断先手还是后手。",
			"【阶段检验】妹妹能区分先手和后手官子。",
			2
		),
		(
			"♟️ 围棋·高级模板3-2：简单目数计算",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥摆出一个简单官子，问：“这步值几目？”\n2. 带妹妹数：自己增加几目 + 对方减少几目。\n3. 出 5 道目数计算题。\n4. 实战中让妹妹判断“下哪里最大”。",
			"【阶段检验】妹妹能算出 3 目以内的官子价值。",
			2
		),
		(
			"♟️ 围棋·高级模板4-1：完整19路对弈",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥让 4 子，和妹妹下 1 盘完整 19 路棋。\n2. 下完后一起数子，妹妹宣布结果。\n3. 复盘只讲 1 个点。\n4. 连下 3 盘，每盘只讲 1 个点。",
			"【阶段检验】妹妹能独立下完 3 盘 19 路棋。",
			4
		),
		(
			"♟️ 围棋·高级模板4-2：综合复盘",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 下完棋后，哥哥找出 4 个点：1 个布局问题、1 个死活问题、1 个连接/分断问题、1 个官子问题。\n2. 每个点只讲 2 分钟。\n3. 问妹妹：“这 4 个点，哪个你下次能改？”\n4. 记录妹妹的回答。",
			"【阶段检验】妹妹能说出 1 个下次要改进的点。",
			3
		),
		(
			"♟️ 围棋·高级模板4-3：最终对弈",
			"♟️ 教妹妹围棋",
			"潘翼芃 (指导妹妹)",
			"1. 哥哥让 2 子，和妹妹下 1 盘完整 19 路棋。\n2. 下完后一起数子，妹妹宣布结果。\n3. 哥哥问 3 个问题：\n   - 这盘你下得最满意的是哪步？\n   - 哪块棋你判断对了死活？\n   - 6 个月里你最大的进步是什么？\n4. 记录结果，作为 6 个月学习的总结。",
			"【阶段检验】能完整对弈一盘、能数子、能说出自己的进步。\n【核心进步】妹妹达成从“能下”到“能对弈”终极里程碑！",
			5
		),

		# ========================================================
		# 📖 语文天地
		# ========================================================
		(
			"📖 语文·五年级：古诗文拓展背诵与小练笔",
			"📖 语文天地",
			"潘翼芃 (哥哥)",
			"1. 熟读并有感情背诵古诗《示儿》《题临安邸》，理解作者爱国情怀。\n2. 规范抄写课文核心生字词 3 遍。\n3. 围绕课文主题完成 100 字随堂小练笔。",
			"字迹工整规范，背诵要求流利有节奏感，小练笔文通字顺。",
			1
		),
		(
			"📖 语文·二年级：生字注音抄写与课文感情朗读",
			"📖 语文天地",
			"潘一柠 (妹妹)",
			"1. 认真抄写语文课文生字（每个字写2遍拼音、3遍汉字，组2个词语）。\n2. 听录音有感情朗读课文 2 遍，注意断句和语气。\n3. 哥哥负责检查妹妹的拼音声调是否准确。",
			"笔画顺序正确，书写端正整洁；朗读声音洪亮清晰。",
			1
		),

		# ========================================================
		# 📐 数学探索
		# ========================================================
		(
			"📐 数学·五年级：小数四则混合运算与应用题",
			"📐 数学探索",
			"潘翼芃 (哥哥)",
			"1. 完成 20 道小数乘除法口算与简便运算练习。\n2. 独立解答 3 道相遇问题或几何面积综合应用题。\n3. 认真检查草稿本，标注易错点。",
			"运算步骤清晰，严谨验算，注意小数点的正确位置。",
			1
		),
		(
			"📐 数学·二年级：百以内加减法与表内乘法口诀",
			"📐 数学探索",
			"潘一柠 (妹妹)",
			"1. 背诵乘法口诀表（抽背 6~9 的乘法口诀）。\n2. 完成《口算天天练》1 页（100以内加减法混合练习）。\n3. 哥哥当考官抽查 5 道心算题。",
			"口诀熟练快速，计算准确无误，家长或哥哥核对打钩。",
			1
		),

		# ========================================================
		# 🔤 英语口语
		# ========================================================
		(
			"🔤 英语·五年级：课文深度朗读与核心单词造句",
			"🔤 英语口语",
			"潘翼芃 (哥哥)",
			"1. 跟读 Unit 课文对话音频 3 遍，模仿地道语音语调。\n2. 选取 5 个重点核心词汇各造 1 个完整英文句子。\n3. 录制一段 1 分钟课文朗读音频。",
			"发音准确自然，句子语法结构正确，标点规范。",
			1
		),
		(
			"🔤 英语·二年级：自然拼读与英语绘本跟读",
			"🔤 英语口语",
			"潘一柠 (妹妹)",
			"1. 跟读分级英语绘本 1 本，练习 Phonics 自然拼读发音。\n2. 认读绘本中的 6 个重点单词，并在哥哥面前大声朗读。\n3. 与哥哥进行 1 组简单的日常英文问答。",
			"敢于大声开口，发音清晰可爱，哥哥给予积极鼓励！",
			1
		),

		# ========================================================
		# 🏃 体育运动
		# ========================================================
		(
			"🏃 体育·一分钟计时跳绳与核心体能",
			"🏃 体育运动",
			"全员",
			"1. 充分热身后进行一分钟跳绳计时测试 3 组，记录个人最高成绩。\n2. 开合跳 50 次，仰卧起坐 25 次。\n3. 运动后进行全身肌肉静态拉伸放松 5 分钟。",
			"穿好运动鞋，运动前后注意安全热身与适量补水。",
			1
		),
		(
			"🏃 体育·网球挥拍练习与敏捷步伐",
			"🏃 体育运动",
			"全员",
			"1. 正手与反手徒手挥拍练习各 30 次，体会发力与引拍动作。\n2. 灵敏步伐移动（并步、跨步）练习 3 组。\n3. 与家人进行网球击球练习或体能小游戏。",
			"动作规范舒展，注意握拍手法与击球点选择。",
			2
		),

		# ========================================================
		# 🔬 科学思维
		# ========================================================
		(
			"🔬 科学·植物生长观察与科学小日记",
			"🔬 科学思维",
			"全员",
			"1. 观察家中种植的植物幼苗，测量株高并记录叶片数量变化。\n2. 在观察记录本上写下 3 句观察心得，并配上手绘简图。\n3. 兄妹分享自己的科学新发现。",
			"记录真实数据，图文并茂，培养细致观察的科学探索精神。",
			1
		),

		# ========================================================
		# 📚 每日阅读
		# ========================================================
		(
			"📚 阅读·名著整本书伴读与好词摘抄",
			"📚 每日阅读",
			"全员",
			"1. 专注自主阅读课外书籍不少于 25 分钟（保持安静与专注）。\n2. 摘抄 2 个优美句子或成语并标注出处。\n3. 用 1 分钟向家人复述今天读到的精彩小故事。",
			"保持端正坐姿与良好视距，摘抄字迹端正清晰。",
			1
		)
	]
	cursor.executemany("""
		INSERT INTO templates (name, category, assignee, content, requirements, reward_flowers)
		VALUES (?, ?, ?, ?, ?, ?)
	""", templates)

def export_templates_to_json(db_path=DB_PATH, json_path=TEMPLATES_EXPORT_PATH):
	"""Exports all current templates from SQLite database into Git-tracked JSON file."""
	try:
		conn = get_db_connection(db_path)
		cursor = conn.cursor()
		cursor.execute("SELECT id, name, category, assignee, content, requirements, reward_flowers FROM templates ORDER BY id ASC")
		rows = cursor.fetchall()
		conn.close()

		templates_list = [dict(r) for r in rows]
		with open(json_path, "w", encoding="utf-8") as f:
			json.dump(templates_list, f, ensure_ascii=False, indent=2)
		return {"success": True, "count": len(templates_list), "path": json_path}
	except Exception as e:
		return {"success": False, "error": str(e)}

def import_templates_from_json(db_path=DB_PATH, json_path=TEMPLATES_EXPORT_PATH):
	"""Imports / restores templates from Git-tracked JSON file into SQLite database."""
	if not os.path.exists(json_path):
		return {"success": False, "error": f"JSON 模板文件不存在: {json_path}"}
	try:
		with open(json_path, "r", encoding="utf-8") as f:
			templates_list = json.load(f)

		if not isinstance(templates_list, list) or len(templates_list) == 0:
			return {"success": False, "error": "JSON 模板数据为空或格式不正确"}

		conn = get_db_connection(db_path)
		cursor = conn.cursor()
		cursor.execute("DELETE FROM templates")
		for t in templates_list:
			cursor.execute("""
				INSERT INTO templates (name, category, assignee, content, requirements, reward_flowers)
				VALUES (?, ?, ?, ?, ?, ?)
			""", (
				t.get("name", "未命名模板"),
				t.get("category", "♟️ 教妹妹围棋"),
				t.get("assignee", "全员"),
				t.get("content", ""),
				t.get("requirements", ""),
				int(t.get("reward_flowers", 1))
			))
		conn.commit()
		conn.close()
		return {"success": True, "count": len(templates_list), "message": f"🎉 成功从 Git 文件导入 {len(templates_list)} 个任务模板！"}
	except Exception as e:
		return {"success": False, "error": str(e)}

def seed_sample_tasks(cursor):
	"""Populates sample tasks with emphasis on Go tutoring."""
	today_str = date.today().strftime('%Y-%m-%d')

	title = "【今日小分队任务】♟️ 哥哥教妹妹围棋：吃子手筋与9路盘实战"
	category = "♟️ 教妹妹围棋"
	assignee = "潘翼芃 & 潘一柠"
	content = "1. 哥哥指导妹妹学习‘双叫吃’和‘抱吃’技巧，讲解如何一眼发现吃子点。\n2. 妹妹完成哥哥布置的 5 道吃子死活练习题。\n3. 兄妹两人进行 1 盘 9 路棋盘友谊对弈，哥哥进行复盘点拨。"
	requirements = "小老师潘翼芃认真指导，妹妹潘一柠专注思考；任务完成后兄妹各奖励 2 朵小红花 🌸！"
	reward = 2

	wechat_text = format_wechat_task(
		title=title,
		category=category,
		assignee=assignee,
		due_date=today_str,
		due_time="20:30",
		content=content,
		requirements=requirements,
		reward_flowers=reward
	)

	cursor.execute("""
		INSERT INTO homework (title, category, assignee, due_date, due_time, content, requirements, reward_flowers, status, wechat_text)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'published', ?)
	""", (title, category, assignee, today_str, "20:30", content, requirements, reward, wechat_text))
	
	hw_id = cursor.lastrowid

	# Create submissions for 潘翼芃 and 潘一柠
	cursor.execute("SELECT id, name FROM students")
	students = cursor.fetchall()
	for s in students:
		cursor.execute("""
			INSERT INTO submissions (homework_id, student_id, student_name, status, score, remark, submitted_at)
			VALUES (?, ?, ?, 'completed', 'A+', '兄妹合作非常棒，围棋吃子练习全对！', ?)
		""", (hw_id, s["id"], s["name"], datetime.now()))

def seed_sample_weiqi_lessons(cursor):
	"""Populates sample Weiqi teaching records."""
	today_str = date.today().strftime('%Y-%m-%d')
	cursor.execute("""
		INSERT INTO weiqi_lessons (level, lesson_title, teacher_name, student_name, teaching_content, sister_feedback, star_rating, lesson_date, status)
		VALUES (1, '第1阶段第1周：规则入门（气、提子与禁着点）', '潘翼芃', '潘一柠', '带领妹妹学习9路棋盘的天元与星位，用黑白子教学数气，掌握了1气叫吃和提子的方法，并讲解了禁着点。', '妹妹学得很认真，能快速指出哪颗棋子只有1口气并成功提掉！', 5, ?, 'completed')
	""", (today_str,))

def format_wechat_task(title, category, assignee, due_date, due_time, content, requirements, reward_flowers=1):
	"""
	Formats task into an attractive WeChat Group announcement for 潘翼芃 潘一柠 任务小分队.
	"""
	lines = [
		"═══════════════════════════════",
		f"🎖️ 【潘翼芃 潘一柠任务小分队播报】",
		f"📌 任务类别: {category}",
		f"🎯 任务主题: {title}",
		f"👦 执行队员: {assignee}",
		f"📅 截止时间: {due_date} {due_time} 前",
		f"🌸 奖励红花: 完成奖励 +{reward_flowers} 朵小红花",
		"───────────────────────────────",
		"📝 【任务详细内容】:"
	]

	for item in content.strip().split("\n"):
		if item.strip():
			lines.append(f"  {item.strip()}")

	if requirements and requirements.strip():
		lines.extend([
			"───────────────────────────────",
			"💡 【小分队温馨提示与要求】:"
		])
		for req in requirements.strip().split("\n"):
			if req.strip():
				lines.append(f"  • {req.strip()}")

	lines.extend([
		"───────────────────────────────",
		"🌟 互相帮助，共同进步！完成后在小分队系统打卡领小红花哦~",
		"═══════════════════════════════"
	])
	return "\n".join(lines)
