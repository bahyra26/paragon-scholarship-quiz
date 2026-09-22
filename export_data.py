import sqlite3, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect('paragon_quiz.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Export fresh JSON
cur.execute('''
SELECT s.id, s.name, s.icon, s.description,
       GROUP_CONCAT(DISTINCT q.subsegment) as subsegments,
       COUNT(q.id) as question_count
FROM segments s
LEFT JOIN questions q ON q.segment_id = s.id
GROUP BY s.id
ORDER BY s.id
''')
segments = []
for row in cur.fetchall():
    seg = dict(row)
    seg['subsegments'] = seg['subsegments'].split(',') if seg['subsegments'] else []
    seg['badge'] = str(seg['question_count']) + ' Soal'
    segments.append(seg)

cur.execute('SELECT id, segment_id, subsegment, question, options_json, correct_answer, explanation, source FROM questions ORDER BY segment_id, subsegment, id')
questions = []
for row in cur.fetchall():
    q = dict(row)
    q['options'] = json.loads(q['options_json'])
    del q['options_json']
    questions.append(q)

total = len(questions)
data = {
    'segments': segments,
    'questions': questions,
    'total_questions': total
}

os.makedirs('public/data', exist_ok=True)
with open('public/data/quiz_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('Exported ' + str(total) + ' questions in ' + str(len(segments)) + ' segments')
for seg in segments:
    print('  ' + seg['id'] + ': ' + str(seg['question_count']) + ' soal - ' + seg['name'])
