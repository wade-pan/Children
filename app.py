import os
import sys
import json
import socket
from datetime import datetime, date
from flask import Flask, render_template, request, jsonify, make_response, session, send_file

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
	sys.path.insert(0, current_dir)

def get_all_local_ips():
	"""Discovers active local IPv4 addresses safely and quickly without blocking DNS resolution."""
	ips = set()
	probe_targets = ['8.8.8.8', '192.168.31.1', '192.168.0.1', '1.1.1.1']
	for target in probe_targets:
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			s.settimeout(0.05)
			s.connect((target, 80))
			ip = s.getsockname()[0]
			if ip and not ip.startswith('127.'):
				ips.add(ip)
			s.close()
		except Exception:
			pass
	return sorted(list(ips))

from db_children_homework import (
	init_db, get_db_connection, format_wechat_task, reset_all_flowers_and_stars,
	export_templates_to_json, import_templates_from_json, TEMPLATES_EXPORT_PATH,
	DEFAULT_CATEGORIES, WEIQI_STAGES, WEIQI_CURRICULUM, DB_PATH
)

# Load configuration
CONFIG_PATH = os.path.join(current_dir, "config.json")
try:
	with open(CONFIG_PATH, "r", encoding="utf-8") as f:
		config_data = json.load(f)
except Exception:
	config_data = {
		"app_name": "PanFamilyTaskForce",
		"app_title": "潘翼芃 潘一柠任务小分队系统",
		"host": "0.0.0.0",
		"port": 5088,
		"default_grade": "五年级 & 二年级",
		"default_class": "阳光成长小分队",
		"categories": DEFAULT_CATEGORIES
	}

# Initialize Flask App
app = Flask(__name__, template_folder=os.path.join(current_dir, "templates"))
app.secret_key = "pan_task_force_family_secret_key_2026"
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

# Initialize SQLite database on startup
init_db(DB_PATH)

@app.route("/")
def index():
	"""Renders the main children task force dashboard."""
	current_u = session.get("user")
	user_profile = None
	if current_u and "users" in config_data and current_u in config_data["users"]:
		u_info = dict(config_data["users"][current_u])
		u_info.pop("password", None)
		u_info["username"] = current_u
		user_profile = u_info

	response = make_response(render_template(
		"index.html",
		cfg=config_data,
		app_config=config_data,
		config=config_data,
		current_user=user_profile,
		today=date.today().strftime("%Y-%m-%d"),
		weiqi_stages=WEIQI_STAGES,
		weiqi_curriculum=WEIQI_STAGES
	))
	response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
	return response

# ==========================================
# 0. User Authentication & Permissions APIs
# ==========================================

@app.route("/api/login", methods=["POST"])
def login_api():
	"""
	Authenticates user:
	  - patrick / patrick123 (潘翼芃 · 哥哥 · 五年级) -> only today's tasks & rewards
	  - penny / penny123 (潘一柠 · 妹妹 · 二年级) -> only today's tasks & rewards
	  - admin / admin123 (家长 / 老师) -> all features
	"""
	try:
		data = request.json or {}
		username = str(data.get("username", "")).strip().lower()
		password = str(data.get("password", "")).strip()

		users_map = config_data.get("users", {})
		if username not in users_map:
			return jsonify({"success": False, "error": "用户名不存在，请检查后重试"})

		user_record = users_map[username]
		if user_record.get("password") != password:
			return jsonify({"success": False, "error": "密码错误，请重新输入"})

		# Store in session
		session["user"] = username
		session["role"] = user_record.get("role", "child")

		user_profile = dict(user_record)
		user_profile.pop("password", None)
		user_profile["username"] = username

		return jsonify({
			"success": True,
			"user": user_profile,
			"message": f"欢迎回来，{user_profile.get('name')}！"
		})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

@app.route("/api/current_user", methods=["GET"])
def get_current_user_api():
	"""Returns the currently logged-in user session."""
	username = session.get("user")
	users_map = config_data.get("users", {})
	if username and username in users_map:
		u_info = dict(users_map[username])
		u_info.pop("password", None)
		u_info["username"] = username
		return jsonify({"success": True, "logged_in": True, "user": u_info})
	return jsonify({"success": True, "logged_in": False, "user": None})

@app.route("/api/logout", methods=["POST"])
def logout_api():
	"""Logs out the current user session."""
	session.clear()
	return jsonify({"success": True, "message": "已安全退出登录"})

# ==========================================
# 1. 教妹妹围棋 (Go Tutoring) Dedicated APIs
# ==========================================

@app.route("/api/weiqi/curriculum", methods=["GET"])
def get_weiqi_curriculum():
	"""Returns the structured 5-stage Go curriculum."""
	return jsonify({"success": True, "curriculum": WEIQI_CURRICULUM})

@app.route("/api/weiqi/lessons", methods=["GET"])
def get_weiqi_lessons():
	"""Fetches all Go teaching lessons between 潘翼芃 and 潘一柠."""
	try:
		conn = get_db_connection()
		cursor = conn.cursor()
		cursor.execute("SELECT * FROM weiqi_lessons ORDER BY lesson_date DESC, id DESC")
		lessons = [dict(row) for row in cursor.fetchall()]
		conn.close()
		return jsonify({"success": True, "lessons": lessons, "count": len(lessons)})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

@app.route("/api/weiqi/lessons", methods=["POST"])
def create_weiqi_lesson():
	"""Creates a new Go teaching session record and awards flowers/stars."""
	try:
		data = request.json or {}
		level = int(data.get("level", 1))
		lesson_title = data.get("lesson_title", "").strip()
		teaching_content = data.get("teaching_content", "").strip()
		sister_feedback = data.get("sister_feedback", "").strip()
		star_rating = int(data.get("star_rating", 5))
		lesson_date = data.get("lesson_date", date.today().strftime("%Y-%m-%d"))
		reward_flowers = int(data.get("reward_flowers", 2))

		if not lesson_title or not teaching_content:
			return jsonify({"success": False, "error": "课程标题与教学内容不能为空"})

		conn = get_db_connection()
		cursor = conn.cursor()

		cursor.execute("""
			INSERT INTO weiqi_lessons (level, lesson_title, teacher_name, student_name, teaching_content, sister_feedback, star_rating, lesson_date, status)
			VALUES (?, ?, '潘翼芃', '潘一柠', ?, ?, ?, ?, 'completed')
		""", (level, lesson_title, teaching_content, sister_feedback, star_rating, lesson_date))
		lesson_id = cursor.lastrowid

		# Award reward flowers & stars to both 潘翼芃 and 潘一柠
		cursor.execute("""
			UPDATE students
			SET flowers = flowers + ?, stars = stars + ?
			WHERE name IN ('潘翼芃', '潘一柠')
		""", (reward_flowers, star_rating * 2))

		conn.commit()
		conn.close()

		return jsonify({
			"success": True,
			"lesson_id": lesson_id,
			"message": f"🎉 围棋教学打卡成功！哥哥与妹妹各获得 {reward_flowers} 朵小红花 🌸！"
		})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

# ==========================================
# 2. Tasks & Homework Assignments APIs
# ==========================================

@app.route("/api/homework", methods=["GET"])
def get_homework_list():
	"""Fetches list of published tasks/homework with subtasks and submission statistics."""
	try:
		category = request.args.get("category")
		status = request.args.get("status")
		due_date = request.args.get("date")

		conn = get_db_connection()
		cursor = conn.cursor()

		query = "SELECT * FROM homework WHERE 1=1"
		params = []

		if category and category != "all":
			query += " AND category = ?"
			params.append(category)
		if status and status != "all":
			query += " AND status = ?"
			params.append(status)
		if due_date:
			query += " AND due_date = ?"
			params.append(due_date)

		query += " ORDER BY due_date DESC, id DESC"
		cursor.execute(query, tuple(params))
		homework_rows = cursor.fetchall()

		results = []
		for hw in homework_rows:
			hw_dict = dict(hw)
			
			# Parse subtask lines from content
			subtasks = [line.strip() for line in str(hw["content"]).split("\n") if line.strip()]
			hw_dict["subtasks"] = subtasks
			hw_dict["subtasks_count"] = len(subtasks)

			# Query submissions for members
			cursor.execute("""
				SELECT sub.*, st.student_no, st.role, st.grade
				FROM submissions sub
				JOIN students st ON st.id = sub.student_id
				WHERE sub.homework_id = ?
				ORDER BY st.id ASC
			""", (hw["id"],))
			
			subs_list = []
			for s_row in cursor.fetchall():
				s_dict = dict(s_row)
				s_dict["avatar"] = "👦" if s_dict.get("student_name") == "潘翼芃" else "👧"
				try:
					st_status = json.loads(s_dict["subtasks_status"] or "[]")
				except Exception:
					st_status = []
				while len(st_status) < len(subtasks):
					st_status.append(False)
				s_dict["subtasks_status"] = st_status
				s_dict["completed_subtasks_count"] = sum(1 for x in st_status[:len(subtasks)] if x)
				subs_list.append(s_dict)
				
			hw_dict["member_submissions"] = subs_list

			# Compute overall stats
			total_s = len(subs_list)
			completed_s = sum(1 for s in subs_list if s["status"] == "completed")
			pending_s = total_s - completed_s
			completion_rate = round((completed_s / total_s * 100), 1) if total_s > 0 else 0

			hw_dict["stats"] = {
				"total": total_s,
				"completed": completed_s,
				"pending": pending_s,
				"completion_rate": completion_rate
			}
			results.append(hw_dict)

		conn.close()
		return jsonify({"success": True, "count": len(results), "homeworks": results})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

@app.route("/api/tasks/toggle_subtask", methods=["POST"])
def toggle_subtask_api():
	"""
	Toggles completion of an individual subtask item.
	Awards 1 flower (+5 stars) per completed subtask.
	Special rule: If category is Weiqi (♟️ 教妹妹围棋), BOTH 潘翼芃 and 潘一柠 receive the flower!
	When all subtasks are finished, the task is marked as fully completed.
	"""
	try:
		data = request.json or {}
		homework_id = data.get("homework_id")
		student_id = data.get("student_id")
		subtask_idx = int(data.get("subtask_idx", 0))
		is_completed = bool(data.get("completed", True))

		conn = get_db_connection()
		cursor = conn.cursor()

		cursor.execute("SELECT * FROM homework WHERE id = ?", (homework_id,))
		hw = cursor.fetchone()
		if not hw:
			conn.close()
			return jsonify({"success": False, "error": "任务不存在"})

		subtasks = [l.strip() for l in str(hw["content"]).split("\n") if l.strip()]
		total_subtasks = max(1, len(subtasks))

		cursor.execute("SELECT * FROM submissions WHERE homework_id = ? AND student_id = ?", (homework_id, student_id))
		sub = cursor.fetchone()
		if not sub:
			cursor.execute("SELECT name FROM students WHERE id = ?", (student_id,))
			st_name_row = cursor.fetchone()
			st_name = st_name_row["name"] if st_name_row else "队员"
			cursor.execute("INSERT INTO submissions (homework_id, student_id, student_name, status, subtasks_status) VALUES (?, ?, ?, 'pending', '[]')",
			               (homework_id, student_id, st_name))
			cursor.execute("SELECT * FROM submissions WHERE homework_id = ? AND student_id = ?", (homework_id, student_id))
			sub = cursor.fetchone()

		try:
			status_list = json.loads(sub["subtasks_status"] or "[]")
		except Exception:
			status_list = []

		while len(status_list) < total_subtasks:
			status_list.append(False)

		old_state = bool(status_list[subtask_idx]) if subtask_idx < len(status_list) else False
		status_list[subtask_idx] = is_completed

		flower_delta = 0
		if is_completed and not old_state:
			flower_delta = 1
		elif not is_completed and old_state:
			flower_delta = -1

		is_weiqi = "围棋" in str(hw["category"]) or "围棋" in str(hw["title"])

		if flower_delta != 0:
			if is_weiqi:
				# Special rule: If Weiqi, BOTH 潘翼芃 and 潘一柠 get the flower!
				cursor.execute("""
					UPDATE students
					SET flowers = MAX(0, flowers + ?), stars = MAX(0, stars + ?)
					WHERE name IN ('潘翼芃', '潘一柠')
				""", (flower_delta, flower_delta * 5))
			else:
				cursor.execute("""
					UPDATE students
					SET flowers = MAX(0, flowers + ?), stars = MAX(0, stars + ?)
					WHERE id = ?
				""", (flower_delta, flower_delta * 5, student_id))

		# Check if all subtasks are finished
		all_done = (len(status_list) > 0 and all(status_list[:total_subtasks]))
		new_status = "completed" if all_done else "pending"
		submitted_at = datetime.now() if all_done else None

		cursor.execute("""
			UPDATE submissions
			SET subtasks_status = ?, status = ?, submitted_at = ?
			WHERE homework_id = ? AND student_id = ?
		""", (json.dumps(status_list), new_status, submitted_at, homework_id, student_id))

		conn.commit()
		conn.close()

		msg = "🎉 该小任务已完成，已发放 +1 朵小红花 🌸！" if is_completed else "已取消该小任务勾选"
		if all_done:
			msg = "🏆 太棒了！全部小任务完成，今日任务打卡成功！"
		if is_weiqi and flower_delta > 0:
			msg += " (♟️ 围棋教学任务：哥哥与妹妹双方各获得 +1 朵小红花 🌸！)"

		return jsonify({
			"success": True,
			"all_completed": all_done,
			"completed_count": sum(1 for s in status_list[:total_subtasks] if s),
			"total_count": total_subtasks,
			"subtasks_status": status_list,
			"message": msg
		})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

@app.route("/api/tasks/complete_all_subtasks", methods=["POST"])
def complete_all_subtasks_api():
	"""Marks all subtasks of a homework as completed for the student."""
	try:
		data = request.json or {}
		homework_id = data.get("homework_id")
		student_id = data.get("student_id")

		conn = get_db_connection()
		cursor = conn.cursor()

		cursor.execute("SELECT * FROM homework WHERE id = ?", (homework_id,))
		hw = cursor.fetchone()
		if not hw:
			conn.close()
			return jsonify({"success": False, "error": "任务不存在"})

		subtasks = [l.strip() for l in str(hw["content"]).split("\n") if l.strip()]
		total_subtasks = max(1, len(subtasks))

		cursor.execute("SELECT * FROM submissions WHERE homework_id = ? AND student_id = ?", (homework_id, student_id))
		sub = cursor.fetchone()
		
		try:
			status_list = json.loads(sub["subtasks_status"] or "[]") if sub else []
		except Exception:
			status_list = []
		while len(status_list) < total_subtasks:
			status_list.append(False)

		# Count how many newly completed
		newly_done = sum(1 for i in range(total_subtasks) if not status_list[i])
		status_list = [True] * total_subtasks

		is_weiqi = "围棋" in str(hw["category"]) or "围棋" in str(hw["title"])

		if newly_done > 0:
			if is_weiqi:
				cursor.execute("""
					UPDATE students
					SET flowers = MAX(0, flowers + ?), stars = MAX(0, stars + ?)
					WHERE name IN ('潘翼芃', '潘一柠')
				""", (newly_done, newly_done * 5))
			else:
				cursor.execute("""
					UPDATE students
					SET flowers = MAX(0, flowers + ?), stars = MAX(0, stars + ?)
					WHERE id = ?
				""", (newly_done, newly_done * 5, student_id))

		cursor.execute("""
			UPDATE submissions
			SET subtasks_status = ?, status = 'completed', submitted_at = CURRENT_TIMESTAMP
			WHERE homework_id = ? AND student_id = ?
		""", (json.dumps(status_list), homework_id, student_id))

		conn.commit()
		conn.close()

		msg = f"🏆 任务全部打卡完成！共奖励 +{newly_done} 朵小红花 🌸！"
		if is_weiqi:
			msg += " (♟️ 兄妹双方均获得红花奖励！)"

		return jsonify({"success": True, "message": msg})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

def resolve_assigned_students(assignee_str, cursor):
	"""
	Resolves which students are assigned based on assignee string.
	Returns list of student rows.
	"""
	assignee_str = str(assignee_str or "").strip()
	cursor.execute("SELECT id, name FROM students WHERE status = 'active' ORDER BY id ASC")
	all_students = cursor.fetchall()

	has_pyp = ("潘翼芃" in assignee_str) or ("哥哥" in assignee_str) or ("patrick" in assignee_str.lower())
	has_pyn = ("潘一柠" in assignee_str) or ("妹妹" in assignee_str) or ("penny" in assignee_str.lower())

	# Explicit dual assignments
	if ("全员" in assignee_str) or ("共同" in assignee_str) or (has_pyp and has_pyn):
		return all_students
	elif has_pyp and not has_pyn:
		return [s for s in all_students if "潘翼芃" in s["name"] or s["id"] == 1]
	elif has_pyn and not has_pyp:
		return [s for s in all_students if "潘一柠" in s["name"] or s["id"] == 2]
	return all_students

@app.route("/api/homework", methods=["POST"])
def create_homework():
	"""Creates a new task and formats WeChat announcement text."""
	try:
		data = request.json or {}
		title = data.get("title", "").strip()
		category = data.get("category", "♟️ 教妹妹围棋")
		assignee = data.get("assignee", "潘翼芃 & 潘一柠")
		due_date = data.get("due_date", date.today().strftime("%Y-%m-%d"))
		due_time = data.get("due_time", "20:00")
		content = data.get("content", "").strip()
		requirements = data.get("requirements", "").strip()
		reward_flowers = int(data.get("reward_flowers", 1))

		if not title:
			return jsonify({"success": False, "error": "任务标题不能为空"})
		if not content:
			return jsonify({"success": False, "error": "任务详细内容不能为空"})

		wechat_text = format_wechat_task(
			title=title,
			category=category,
			assignee=assignee,
			due_date=due_date,
			due_time=due_time,
			content=content,
			requirements=requirements,
			reward_flowers=reward_flowers
		)

		subtasks = [line.strip() for line in content.split("\n") if line.strip()]

		conn = get_db_connection()
		cursor = conn.cursor()

		cursor.execute("""
			INSERT INTO homework (title, category, assignee, due_date, due_time, content, requirements, reward_flowers, status, wechat_text)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'published', ?)
		""", (title, category, assignee, due_date, due_time, content, requirements, reward_flowers, wechat_text))
		
		hw_id = cursor.lastrowid

		# Initialize submissions strictly for assigned members
		assigned_students = resolve_assigned_students(assignee, cursor)
		for s in assigned_students:
			cursor.execute("""
				INSERT INTO submissions (homework_id, student_id, student_name, status, subtasks_status)
				VALUES (?, ?, ?, 'pending', ?)
			""", (hw_id, s["id"], s["name"], json.dumps([False] * len(subtasks))))

		conn.commit()
		conn.close()

		return jsonify({
			"success": True,
			"homework_id": hw_id,
			"wechat_text": wechat_text,
			"message": "任务发布成功！已同步推送至小分队名单"
		})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

@app.route("/api/homework/<int:hw_id>", methods=["GET"])
def get_homework_detail(hw_id):
	"""Retrieves detail of a specific task along with member check-in statuses."""
	try:
		conn = get_db_connection()
		cursor = conn.cursor()

		cursor.execute("SELECT * FROM homework WHERE id = ?", (hw_id,))
		hw_row = cursor.fetchone()
		if not hw_row:
			conn.close()
			return jsonify({"success": False, "error": "任务记录不存在"})

		hw_dict = dict(hw_row)

		cursor.execute("""
			SELECT sub.*, st.student_no, st.gender, st.grade, st.role, st.flowers, st.stars
			FROM submissions sub
			JOIN students st ON st.id = sub.student_id
			WHERE sub.homework_id = ?
			ORDER BY st.id ASC
		""", (hw_id,))
		submissions = [dict(row) for row in cursor.fetchall()]

		conn.close()
		return jsonify({
			"success": True,
			"homework": hw_dict,
			"submissions": submissions
		})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

@app.route("/api/homework/<int:hw_id>", methods=["PUT", "POST"])
@app.route("/api/homework/<int:hw_id>/update", methods=["POST", "PUT"])
def update_homework(hw_id):
	"""Updates an existing published task and reconciles subtask completion statuses."""
	try:
		data = request.json or {}
		title = data.get("title", "").strip()
		category = data.get("category", "♟️ 教妹妹围棋")
		assignee = data.get("assignee", "潘翼芃 & 潘一柠")
		due_date = data.get("due_date") or date.today().strftime("%Y-%m-%d")
		due_time = data.get("due_time") or "20:00"
		content = data.get("content", "").strip()
		requirements = data.get("requirements", "").strip()
		reward_flowers = int(data.get("reward_flowers", 1))

		if not title:
			return jsonify({"success": False, "error": "任务标题不能为空"})
		if not content:
			return jsonify({"success": False, "error": "任务详细内容不能为空"})

		wechat_text = format_wechat_task(
			title=title,
			category=category,
			assignee=assignee,
			due_date=due_date,
			due_time=due_time,
			content=content,
			requirements=requirements,
			reward_flowers=reward_flowers
		)

		subtasks = [line.strip() for line in content.split("\n") if line.strip()]
		new_subtask_count = len(subtasks)

		conn = get_db_connection()
		cursor = conn.cursor()

		cursor.execute("""
			UPDATE homework
			SET title = ?, category = ?, assignee = ?, due_date = ?, due_time = ?,
			    content = ?, requirements = ?, reward_flowers = ?, wechat_text = ?,
			    updated_at = CURRENT_TIMESTAMP
			WHERE id = ?
		""", (title, category, assignee, due_date, due_time, content, requirements, reward_flowers, wechat_text, hw_id))

		# Reconcile submissions strictly for assigned members
		assigned_students = resolve_assigned_students(assignee, cursor)
		assigned_student_ids = [s["id"] for s in assigned_students]

		# Delete submissions for students no longer assigned
		if assigned_student_ids:
			placeholders = ','.join(['?'] * len(assigned_student_ids))
			cursor.execute(f"DELETE FROM submissions WHERE homework_id = ? AND student_id NOT IN ({placeholders})", (hw_id, *assigned_student_ids))

		# Ensure each assigned student has a submission record
		for s in assigned_students:
			cursor.execute("SELECT id, subtasks_status FROM submissions WHERE homework_id = ? AND student_id = ?", (hw_id, s["id"]))
			sub_row = cursor.fetchone()
			if not sub_row:
				cursor.execute("""
					INSERT INTO submissions (homework_id, student_id, student_name, status, subtasks_status)
					VALUES (?, ?, ?, 'pending', ?)
				""", (hw_id, s["id"], s["name"], json.dumps([False] * new_subtask_count)))
			else:
				# Adjust subtasks_status length if count changed
				try:
					status_list = json.loads(sub_row["subtasks_status"] or "[]")
				except Exception:
					status_list = []
				if len(status_list) < new_subtask_count:
					status_list.extend([False] * (new_subtask_count - len(status_list)))
				elif len(status_list) > new_subtask_count:
					status_list = status_list[:new_subtask_count]
				
				if new_subtask_count > 0 and all(status_list):
					sub_status = "completed"
				elif any(status_list):
					sub_status = "in_progress"
				else:
					sub_status = "pending"

				cursor.execute("""
					UPDATE submissions
					SET subtasks_status = ?, status = ?
					WHERE id = ?
				""", (json.dumps(status_list), sub_status, sub_row["id"]))

		conn.commit()
		conn.close()

		return jsonify({
			"success": True,
			"message": f"💾 任务【{title}】已成功更新！",
			"wechat_text": wechat_text
		})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

@app.route("/api/homework/<int:hw_id>", methods=["DELETE"])
def delete_homework(hw_id):
	"""Deletes a task and its submission records."""
	try:
		conn = get_db_connection()
		cursor = conn.cursor()
		cursor.execute("DELETE FROM submissions WHERE homework_id = ?", (hw_id,))
		cursor.execute("DELETE FROM homework WHERE id = ?", (hw_id,))
		conn.commit()
		conn.close()
		return jsonify({"success": True, "message": "任务已成功删除"})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

# ==========================================
# 3. Member Roster & Rewards APIs
# ==========================================

@app.route("/api/members", methods=["GET"])
def get_members():
	"""Fetches 潘翼芃 and 潘一柠 profiles, flower counts, and star points."""
	try:
		conn = get_db_connection()
		cursor = conn.cursor()
		cursor.execute("SELECT * FROM students WHERE status = 'active' ORDER BY id ASC")
		members = [dict(row) for row in cursor.fetchall()]
		conn.close()
		return jsonify({"success": True, "members": members})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

@app.route("/api/members/reward", methods=["POST"])
def award_member_flowers():
	"""Manually awards or adjusts flowers and stars for a member."""
	try:
		data = request.json or {}
		member_id = data.get("member_id")
		flowers_delta = int(data.get("flowers", 1))
		stars_delta = int(data.get("stars", 5))

		if not member_id:
			return jsonify({"success": False, "error": "Missing member_id"})

		conn = get_db_connection()
		cursor = conn.cursor()
		cursor.execute("""
			UPDATE students
			SET flowers = MAX(0, flowers + ?), stars = MAX(0, stars + ?)
			WHERE id = ?
		""", (flowers_delta, stars_delta, member_id))
		conn.commit()
		conn.close()

		return jsonify({"success": True, "message": "⭐ 积分与红花已成功调整！"})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

# ==========================================
# 4. Student Check-in & Submissions APIs
# ==========================================

@app.route("/api/submissions/update", methods=["POST"])
def update_submission():
	"""Updates member's task check-in status, score rating, and awards flowers if completed."""
	try:
		data = request.json or {}
		submission_id = data.get("submission_id")
		status = data.get("status", "completed")
		score = data.get("score", "A+")
		remark = data.get("remark", "")

		if not submission_id:
			return jsonify({"success": False, "error": "Missing submission_id"})

		conn = get_db_connection()
		cursor = conn.cursor()

		# Check previous status to avoid duplicate flower awards
		cursor.execute("SELECT student_id, homework_id, status FROM submissions WHERE id = ?", (submission_id,))
		sub_row = cursor.fetchone()
		if not sub_row:
			conn.close()
			return jsonify({"success": False, "error": "Submission not found"})

		prev_status = sub_row["status"]
		student_id = sub_row["student_id"]
		homework_id = sub_row["homework_id"]

		submitted_at = datetime.now() if status in ["completed", "correcting"] else None

		cursor.execute("""
			UPDATE submissions
			SET status = ?, score = ?, remark = ?, submitted_at = ?
			WHERE id = ?
		""", (status, score, remark, submitted_at, submission_id))

		# If newly completed, award task flowers to student
		if status == "completed" and prev_status != "completed":
			cursor.execute("SELECT reward_flowers FROM homework WHERE id = ?", (homework_id,))
			hw_flower_row = cursor.fetchone()
			flowers_to_add = hw_flower_row["reward_flowers"] if hw_flower_row else 1
			cursor.execute("UPDATE students SET flowers = flowers + ?, stars = stars + ? WHERE id = ?", (flowers_to_add, flowers_to_add * 5, student_id))

		conn.commit()
		conn.close()

		return jsonify({"success": True, "message": "打卡状态更新成功！"})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

# ==========================================
# 5. Templates APIs
# ==========================================

@app.route("/api/templates", methods=["GET"])
def get_templates():
	"""Returns all reusable quick templates."""
	try:
		conn = get_db_connection()
		cursor = conn.cursor()
		cursor.execute("SELECT * FROM templates ORDER BY id ASC")
		templates = [dict(row) for row in cursor.fetchall()]
		conn.close()
		return jsonify({"success": True, "templates": templates})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

def auto_git_sync_templates():
	"""
	Automatically exports templates to templates_export.json, commits,
	and pushes directly to the remote Git repository upon saving.
	"""
	try:
		export_templates_to_json()
		import subprocess
		ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		cmd = f'git -C "{current_dir}" add templates_export.json weiqi_templates_curriculum.json config.json templates/index.html && git -C "{current_dir}" commit -m "auto: sync template changes to git [{ts_str}]" && git -C "{current_dir}" push origin main'
		subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	except Exception:
		pass

@app.route("/api/templates", methods=["POST"])
def create_template():
	"""Creates a new task template and automatically syncs to Git."""
	try:
		data = request.json or {}
		name = data.get("name", "").strip()
		category = data.get("category", "♟️ 教妹妹围棋").strip()
		assignee = data.get("assignee", "全员").strip()
		content = data.get("content", "").strip()
		requirements = data.get("requirements", "").strip()
		reward_flowers = int(data.get("reward_flowers", 1))

		if not name:
			return jsonify({"success": False, "error": "模板名称不能为空"})
		if not content:
			return jsonify({"success": False, "error": "模板任务内容不能为空"})

		conn = get_db_connection()
		cursor = conn.cursor()
		cursor.execute("""
			INSERT INTO templates (name, category, assignee, content, requirements, reward_flowers)
			VALUES (?, ?, ?, ?, ?, ?)
		""", (name, category, assignee, content, requirements, reward_flowers))
		tpl_id = cursor.lastrowid
		conn.commit()
		conn.close()

		# Auto-export to templates_export.json and auto-sync to Git
		auto_git_sync_templates()

		return jsonify({"success": True, "template_id": tpl_id, "message": f"🎉 模板【{name}】创建成功并已自动同步推送到 Git！"})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

@app.route("/api/templates/<int:template_id>", methods=["PUT", "POST"])
def update_template(template_id):
	"""Updates an existing task template and auto-syncs to Git."""
	try:
		data = request.json or {}
		name = data.get("name", "").strip()
		category = data.get("category", "♟️ 教妹妹围棋").strip()
		assignee = data.get("assignee", "全员").strip()
		content = data.get("content", "").strip()
		requirements = data.get("requirements", "").strip()
		reward_flowers = int(data.get("reward_flowers", 1))

		if not name:
			return jsonify({"success": False, "error": "模板名称不能为空"})
		if not content:
			return jsonify({"success": False, "error": "模板任务内容不能为空"})

		conn = get_db_connection()
		cursor = conn.cursor()
		cursor.execute("""
			UPDATE templates
			SET name = ?, category = ?, assignee = ?, content = ?, requirements = ?, reward_flowers = ?
			WHERE id = ?
		""", (name, category, assignee, content, requirements, reward_flowers, template_id))
		conn.commit()
		conn.close()

		# Auto-export to templates_export.json and auto-sync to Git
		auto_git_sync_templates()

		return jsonify({"success": True, "message": f"💾 模板【{name}】修改已成功保存并自动同步推送到 Git！"})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

@app.route("/api/templates/<int:template_id>", methods=["DELETE"])
def delete_template(template_id):
	"""Deletes a task template and auto-syncs to Git."""
	try:
		conn = get_db_connection()
		cursor = conn.cursor()
		cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
		conn.commit()
		conn.close()

		# Auto-export and auto-sync to Git
		auto_git_sync_templates()

		return jsonify({"success": True, "message": "🗑️ 模板已成功删除并已自动同步至 Git"})
	except Exception as e:
		return jsonify({"success": False, "error": str(e)})

def check_is_admin():
	"""Checks whether the currently active session belongs to an admin."""
	return session.get("role") == "admin"

@app.route("/api/templates/export", methods=["POST"])
def export_templates_api():
	"""Manually triggers export of templates from SQLite to templates_export.json (Admin only)."""
	if not check_is_admin():
		return jsonify({"success": False, "error": "🔒 权限不足：只有家长管理员 (Admin) 可以执行 Git 导出！"}), 403

	res = export_templates_to_json()
	if res.get("success"):
		return jsonify({"success": True, "count": res.get("count"), "message": f"📤 成功导出 {res.get('count')} 个模板至 Git 文件 templates_export.json！"})
	return jsonify({"success": False, "error": res.get("error", "导出失败")})

@app.route("/api/templates/import", methods=["POST"])
def import_templates_api():
	"""Manually imports templates from templates_export.json into SQLite database (Admin only)."""
	if not check_is_admin():
		return jsonify({"success": False, "error": "🔒 权限不足：只有家长管理员 (Admin) 可以从 Git 文件恢复！"}), 403

	res = import_templates_from_json()
	return jsonify(res)

@app.route("/api/templates/download", methods=["GET"])
def download_templates_json():
	"""Downloads templates_export.json directly (Admin only)."""
	if not check_is_admin():
		return jsonify({"success": False, "error": "🔒 权限不足：只有管理员可以下载备份"}), 403

	export_templates_to_json()
	if os.path.exists(TEMPLATES_EXPORT_PATH):
		return send_file(TEMPLATES_EXPORT_PATH, as_attachment=True, download_name="templates_export.json")
	return jsonify({"success": False, "error": "文件不存在"})

@app.route("/api/git/push", methods=["POST"])
def git_push_api():
	"""
	Executes Git Commit and Push to remote repository.
	Strictly restricted to Admin role.
	"""
	if not check_is_admin():
		return jsonify({"success": False, "error": "🔒 权限不足：只有家长管理员 (Admin) 可以执行 Git Push！"}), 403

	try:
		import subprocess
		# 1. Ensure latest templates are exported to JSON
		export_templates_to_json()

		# 2. Run git commit & push
		ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		cmd = f'git -C "{current_dir}" add templates_export.json weiqi_templates_curriculum.json config.json templates/index.html && git -C "{current_dir}" commit -m "update: sync custom templates by admin [{ts_str}]" && git -C "{current_dir}" push origin main'
		
		proc = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=25)
		
		# If working tree was clean / nothing new to commit
		if proc.returncode != 0 and ("nothing to commit" in proc.stdout or "nothing to commit" in proc.stderr):
			# Try push only
			push_proc = subprocess.run(f'git -C "{current_dir}" push origin main', shell=True, text=True, capture_output=True, timeout=25)
			return jsonify({
				"success": True,
				"message": "✅ 模板与文件已经是最新状态，远程 Git 已同步！",
				"details": push_proc.stdout or push_proc.stderr
			})
		elif proc.returncode == 0:
			return jsonify({
				"success": True,
				"message": "🎉 成功将最新模板和修改提交并推送到 GitHub 远程仓库！",
				"details": proc.stdout
			})
		else:
			err_msg = proc.stderr or proc.stdout
			return jsonify({"success": False, "error": f"Git Push 失败: {err_msg}"})
	except Exception as e:
		return jsonify({"success": False, "error": f"执行 Git Push 出错: {str(e)}"})

if __name__ == "__main__":
	try:
		reconfig = getattr(sys.stdout, "reconfigure", None)
		if callable(reconfig):
			reconfig(line_buffering=True)
	except Exception:
		pass

	host = config_data.get("host", "0.0.0.0")
	port = int(config_data.get("port", 5088))
	extra_ip = config_data.get("extra_access_ip", "192.168.31.13")
	local_ips = get_all_local_ips()

	print("=" * 65, flush=True)
	print("🏆 潘翼芃 潘一柠任务小分队系统 (Task Force Hub) 已就绪启动", flush=True)
	print(f"📍 本地访问地址: http://localhost:{port}", flush=True)
	print(f"📍 本地 127 地址: http://127.0.0.1:{port}", flush=True)
	if extra_ip:
		print(f"📍 31网段手机/iPad/电脑访问(端口映射入口): http://{extra_ip}:{port} ⭐", flush=True)
	print(f"📍 0网段本地直连地址: http://192.168.0.25:{port}", flush=True)
	if local_ips:
		for ip in local_ips:
			if ip not in ["192.168.0.25", extra_ip]:
				print(f"📍 局域网网卡 IP: http://{ip}:{port}", flush=True)
	print("=" * 65, flush=True)
	app.run(host=host, port=port, debug=False, threaded=True)
