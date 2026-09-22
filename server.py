import os
import sys
import json
import random
import sqlite3
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DB_PATH = "paragon_quiz.db"

app = FastAPI(title="Paragon Scholarship Quiz Learning API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Models
class CheckAnswerRequest(BaseModel):
    question_id: str
    selected_option: str

class QuizSubmitRequest(BaseModel):
    segment_id: str
    score: int
    total: int
    accuracy: float
    time_spent_sec: int
    details: List[Dict[str, Any]]

class NewQuestionRequest(BaseModel):
    segment_id: str
    subsegment: str
    question: str
    options: List[Dict[str, str]]
    correct_answer: str
    explanation: str
    source: Optional[str] = "User Custom Question"

class BookmarkRequest(BaseModel):
    question_id: str

@app.get("/api/segments")
def list_segments():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT s.id, s.name, s.icon, s.description, s.badge, s.order_num,
           COUNT(q.id) as question_count
    FROM segments s
    LEFT JOIN questions q ON s.id = q.segment_id
    GROUP BY s.id
    ORDER BY s.order_num
    """)
    rows = cur.fetchall()
    
    segments = []
    for r in rows:
        seg_id = r["id"]
        # get subsegments for this segment
        cur.execute("SELECT DISTINCT subsegment FROM questions WHERE segment_id = ? ORDER BY subsegment", (seg_id,))
        subs = [sub_row["subsegment"] for sub_row in cur.fetchall()]
        
        segments.append({
            "id": r["id"],
            "name": r["name"],
            "icon": r["icon"],
            "description": r["description"],
            "badge": r["badge"],
            "order_num": r["order_num"],
            "question_count": r["question_count"],
            "subsegments": subs
        })
    
    # Also total questions count
    cur.execute("SELECT COUNT(*) FROM questions")
    total_q = cur.fetchone()[0]
    
    conn.close()
    return {"segments": segments, "total_questions": total_q}

@app.get("/api/quiz")
def get_quiz(
    segment: Optional[str] = Query("all", description="Segment ID or 'all'"),
    subsegment: Optional[str] = Query(None, description="Optional subsegment filter"),
    limit: Optional[int] = Query(10, description="Max number of questions"),
    shuffle: Optional[bool] = Query(True, description="Whether to randomize questions")
):
    conn = get_db()
    cur = conn.cursor()
    
    query = "SELECT id, segment_id, subsegment, question, options_json, correct_answer, explanation, source FROM questions WHERE 1=1"
    params = []
    
    if segment and segment != "all":
        query += " AND segment_id = ?"
        params.append(segment)
        
    if subsegment:
        query += " AND subsegment = ?"
        params.append(subsegment)
        
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    
    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "segment_id": r["segment_id"],
            "subsegment": r["subsegment"],
            "question": r["question"],
            "options": json.loads(r["options_json"]),
            "correct_answer": r["correct_answer"],
            "explanation": r["explanation"],
            "source": r["source"]
        })
        
    if shuffle:
        random.shuffle(items)
        
    if limit and limit > 0 and len(items) > limit:
        items = items[:limit]
        
    return {
        "count": len(items),
        "segment": segment,
        "subsegment": subsegment,
        "questions": items
    }

@app.post("/api/quiz/check")
def check_answer(req: CheckAnswerRequest):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT correct_answer, explanation FROM questions WHERE id = ?", (req.question_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
        
    correct = row["correct_answer"].strip().upper()
    user_choice = req.selected_option.strip().upper()
    is_correct = (user_choice == correct)
    
    return {
        "question_id": req.question_id,
        "is_correct": is_correct,
        "correct_answer": correct,
        "explanation": row["explanation"]
    }

@app.post("/api/quiz/submit")
def submit_quiz(req: QuizSubmitRequest):
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
    INSERT INTO quiz_history (segment_id, score, total, accuracy, time_spent_sec, details_json)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        req.segment_id,
        req.score,
        req.total,
        req.accuracy,
        req.time_spent_sec,
        json.dumps(req.details, ensure_ascii=False)
    ))
    history_id = cur.lastrowid
    conn.commit()
    conn.close()
    
    # determine evaluation feedback badge
    if req.accuracy >= 90:
        evaluation = "🌟 Istimewa! Kemampuan Anda sangat kompetitif untuk lolos Paragon Scholarship & MT."
        badge = "Exceptional Paragon Scholar"
    elif req.accuracy >= 75:
        evaluation = "👍 Sangat Baik! Anda telah menguasai sebagian besar pola soal psikotes Paragon."
        badge = "Strong Candidate"
    elif req.accuracy >= 55:
        evaluation = "📈 Cukup Baik. Tingkatkan kecepatan dan ketelitian dengan latihan segmen berkala."
        badge = "On Track"
    else:
        evaluation = "💪 Perlu Latihan Tambahan. Pelajari pembahasan setiap butir soal untuk memahami polanya."
        badge = "Keep Practicing"
        
    return {
        "history_id": history_id,
        "score": req.score,
        "total": req.total,
        "accuracy": req.accuracy,
        "time_spent_sec": req.time_spent_sec,
        "evaluation": evaluation,
        "badge": badge
    }

@app.get("/api/history")
def get_history(limit: int = 15):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT h.id, h.segment_id, s.name as segment_name, s.icon as segment_icon,
           h.score, h.total, h.accuracy, h.time_spent_sec, h.completed_at
    FROM quiz_history h
    LEFT JOIN segments s ON h.segment_id = s.id
    ORDER BY h.id DESC
    LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    
    history = [dict(r) for r in rows]
    return {"history": history}

@app.get("/api/stats")
def get_user_stats():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*), AVG(accuracy), SUM(total), SUM(score) FROM quiz_history")
    row = cur.fetchone()
    total_quizzes = row[0] or 0
    avg_acc = round(row[1] or 0.0, 1)
    total_answered = row[2] or 0
    total_correct = row[3] or 0
    
    # stats per segment
    cur.execute("""
    SELECT h.segment_id, s.name, s.icon, COUNT(*) as sessions, AVG(h.accuracy) as avg_acc, MAX(h.score) as best_score
    FROM quiz_history h
    LEFT JOIN segments s ON h.segment_id = s.id
    GROUP BY h.segment_id
    """)
    seg_stats = [dict(r) for r in cur.fetchall()]
    
    cur.execute("SELECT COUNT(*) FROM bookmarks")
    bookmark_count = cur.fetchone()[0]
    
    conn.close()
    return {
        "total_quizzes": total_quizzes,
        "average_accuracy": avg_acc,
        "total_answered": total_answered,
        "total_correct": total_correct,
        "bookmarks_count": bookmark_count,
        "segment_stats": seg_stats
    }

@app.get("/api/questions")
def search_questions(
    q: Optional[str] = None,
    segment: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    conn = get_db()
    cur = conn.cursor()
    
    sql = "SELECT id, segment_id, subsegment, question, options_json, correct_answer, explanation, source FROM questions WHERE 1=1"
    params = []
    
    if q:
        sql += " AND (question LIKE ? OR subsegment LIKE ? OR explanation LIKE ?)"
        term = f"%{q}%"
        params.extend([term, term, term])
        
    if segment and segment != "all":
        sql += " AND segment_id = ?"
        params.append(segment)
        
    sql += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cur.execute(sql, params)
    rows = cur.fetchall()
    
    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "segment_id": r["segment_id"],
            "subsegment": r["subsegment"],
            "question": r["question"],
            "options": json.loads(r["options_json"]),
            "correct_answer": r["correct_answer"],
            "explanation": r["explanation"],
            "source": r["source"]
        })
        
    conn.close()
    return {"questions": items, "count": len(items)}

@app.post("/api/questions")
def add_question(req: NewQuestionRequest):
    conn = get_db()
    cur = conn.cursor()
    
    # generate id
    new_id = f"custom_{int(random.random() * 1000000)}"
    cur.execute("""
    INSERT INTO questions (id, segment_id, subsegment, question, options_json, correct_answer, explanation, source)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        new_id,
        req.segment_id,
        req.subsegment,
        req.question,
        json.dumps(req.options, ensure_ascii=False),
        req.correct_answer.upper(),
        req.explanation,
        req.source
    ))
    conn.commit()
    conn.close()
    
    return {"success": True, "id": new_id, "message": "Soal berhasil ditambahkan ke database!"}

@app.post("/api/bookmarks")
def toggle_bookmark(req: BookmarkRequest):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT question_id FROM bookmarks WHERE question_id = ?", (req.question_id,))
    exists = cur.fetchone()
    
    if exists:
        cur.execute("DELETE FROM bookmarks WHERE question_id = ?", (req.question_id,))
        is_bookmarked = False
    else:
        cur.execute("INSERT INTO bookmarks (question_id) VALUES (?)", (req.question_id,))
        is_bookmarked = True
        
    conn.commit()
    conn.close()
    return {"question_id": req.question_id, "bookmarked": is_bookmarked}

# Mount static frontend
os.makedirs("public", exist_ok=True)
os.makedirs(os.path.join("public", "data"), exist_ok=True)
app.mount("/static", StaticFiles(directory="public"), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join("public", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Paragon Quiz API running. Frontend index.html not yet created."}

@app.get("/style.css")
def serve_css():
    return FileResponse(os.path.join("public", "style.css"))

@app.get("/app.js")
def serve_js():
    return FileResponse(os.path.join("public", "app.js"))

@app.get("/data/{file_name}")
def serve_data(file_name: str):
    path = os.path.join("public", "data", file_name)
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

