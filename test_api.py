import urllib.request
import urllib.parse
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://127.0.0.1:8000'

def req(path, data=None):
    url = BASE + path
    if data is not None:
        payload = json.dumps(data).encode('utf-8')
        r = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    else:
        r = urllib.request.Request(url)
    with urllib.request.urlopen(r) as res:
        return json.loads(res.read().decode('utf-8'))

print('=== 1. Testing GET /api/segments ===')
segs = req('/api/segments')
print(f"Total Segments: {len(segs['segments'])}, Total Soal: {segs['total_questions']}")
assert len(segs['segments']) == 6, 'Should have 6 segments'
assert segs['total_questions'] >= 215, 'Should have at least 215 questions'

print('\n=== 2. Testing GET /api/quiz?segment=verbal&limit=5 ===')
quiz = req('/api/quiz?segment=verbal&limit=5')
print(f"Quiz questions returned: {len(quiz['questions'])}")
assert len(quiz['questions']) == 5, 'Should return 5 questions'
q1 = quiz['questions'][0]
print(f"Q1: {q1['question'][:80]}...")
print(f"Options count: {len(q1['options'])}")
print(f"Correct Answer: {q1['correct_answer']}")
assert len(q1['options']) >= 2, 'Should have options'

print('\n=== 3. Testing POST /api/quiz/check ===')
check_res = req('/api/quiz/check', {'question_id': q1['id'], 'selected_option': q1['correct_answer']})
print(f"Checked correct: {check_res['is_correct']}")
assert check_res['is_correct'] is True, 'Should be correct'

check_res_wrong = req('/api/quiz/check', {'question_id': q1['id'], 'selected_option': 'WRONG'})
print(f"Checked wrong: {check_res_wrong['is_correct']}")
assert check_res_wrong['is_correct'] is False, 'Should be incorrect'

print('\n=== 4. Testing POST /api/quiz/submit ===')
submit_payload = {
    'segment_id': 'verbal',
    'score': 4,
    'total': 5,
    'accuracy': 80.0,
    'time_spent_sec': 65,
    'details': [{'question_id': q1['id'], 'selected': q1['correct_answer'], 'is_correct': True}]
}
sub_res = req('/api/quiz/submit', submit_payload)
print(f"Submitted quiz: History ID {sub_res['history_id']}, Evaluation: {sub_res['evaluation']}")
assert sub_res['score'] == 4

print('\n=== 5. Testing GET /api/stats ===')
stats = req('/api/stats')
print(f"Stats: total quizzes {stats['total_quizzes']}, avg accuracy {stats['average_accuracy']}%")
assert stats['total_quizzes'] >= 1

print('\n=== 6. Testing GET /api/questions (Search) ===')
search_res = req('/api/questions?q=sinonim&limit=3')
print(f"Search found: {search_res['count']} questions")
assert search_res['count'] >= 1

print('\n=== 7. Testing POST /api/questions (Add Custom Question) ===')
new_q = {
    'segment_id': 'verbal',
    'subsegment': 'Sinonim Uji Coba',
    'question': 'Sinonim dari kata KOLABORATIF adalah...',
    'options': [
        {'key': 'A', 'text': 'Individualis'},
        {'key': 'B', 'text': 'Bekerja bersama'},
        {'key': 'C', 'text': 'Menolak bantuan'},
        {'key': 'D', 'text': 'Menyendiri'}
    ],
    'correct_answer': 'B',
    'explanation': 'Kolaboratif berasal dari kata kolaborasi yang berarti bekerja sama secara aktif.',
    'source': 'Pengujian Otomatis'
}
add_res = req('/api/questions', new_q)
print(f"Add question result: {add_res['message']} (ID: {add_res['id']})")
assert add_res['success'] is True

print('\n=== 8. Testing POST /api/bookmarks ===')
bm_res = req('/api/bookmarks', {'question_id': q1['id']})
print(f"Bookmark toggled: {bm_res}")

print('\n>>> ALL 8 BACKEND AND DATABASE SUITES PASSED FLAWLESSLY! <<<')
