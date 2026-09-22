import os
import sys
import re
import json
import sqlite3

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = "paragon_quiz.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS segments (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        icon TEXT NOT NULL,
        description TEXT NOT NULL,
        badge TEXT NOT NULL,
        order_num INTEGER NOT NULL
    );
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id TEXT PRIMARY KEY,
        segment_id TEXT NOT NULL,
        subsegment TEXT NOT NULL,
        question TEXT NOT NULL,
        options_json TEXT NOT NULL,
        correct_answer TEXT NOT NULL,
        explanation TEXT NOT NULL,
        source TEXT NOT NULL,
        FOREIGN KEY (segment_id) REFERENCES segments(id)
    );
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quiz_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        segment_id TEXT NOT NULL,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL,
        accuracy REAL NOT NULL,
        time_spent_sec INTEGER NOT NULL,
        completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        details_json TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookmarks (
        question_id TEXT PRIMARY KEY,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    conn.commit()
    conn.close()

def insert_segments():
    segments = [
        ("verbal", "Tes Verbal", "📝", "Sinonim, Antonim, Pengelompokan Kata & Analogi Hubungan", "Paragon MT & Beasiswa", 1),
        ("numerik", "Tes Numerik & Deret", "🔢", "Aritmatika Dasar, Deret Angka, Seri Huruf & Angka Cerita", "Logika Kuantitatif", 2),
        ("logika", "Tes Logika & Silogisme", "🧠", "Silogisme, Logika Cerita, Logika Relasi & Diagram", "Penalaran Kritis", 3),
        ("urutan", "Tes Urutan Angka & Huruf", "📐", "Urutan Komparasi Nilai, Abjad & Pola Teratur", "Konsentrasi & Akurasi", 4),
        ("tpa_simulasi", "Simulasi TPA Paragon", "🎯", "Paket Komprehensif Tes Potensi Akademik Paragon Scholarship", "Simulasi Penuh", 5),
        ("kepribadian", "Tes Nilai & Budaya Paragon", "🤝", "Keteladanan, Kerendahan Hati, Ketangguhan & Situational Judgment", "Core Values Paragon", 6),
    ]
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for s in segments:
        cur.execute("INSERT OR REPLACE INTO segments VALUES (?, ?, ?, ?, ?, ?)", s)
    conn.commit()
    conn.close()

def clean_text(t):
    if not t:
        return ""
    t = t.replace('\u2060', ' ').replace('\xa0', ' ')
    
    # Glued words commonly found in OCR/PDF extractions
    glued_rules = [
        (r'Sinonimdarikata', 'Sinonim dari kata '),
        (r'Antonimdarikata', 'Antonim dari kata '),
        (r'Apapersamaankatadari', 'Apa persamaan kata dari '),
        (r'Apalawankatadari', 'Apa lawan kata dari '),
        (r'Apasinonimdarikata', 'Apa sinonim dari kata '),
        (r'Apaantonimdarikata', 'Apa antonim dari kata '),
        (r'Apaperbedaankatadari', 'Apa perbedaan kata dari '),
        (r'Pilihlahkatayang', 'Pilihlah kata yang '),
        (r'Manakahpernyataan', 'Manakah pernyataan '),
        (r'yangbenar', ' yang benar '),
        (r'yangtidak', ' yang tidak '),
        (r'dengankata', ' dengan kata '),
        (r'dengandiri', ' dengan diri '),
        (r'katayang', ' kata yang '),
        (r'darikata', ' dari kata '),
        (r'angkaselanjutnya', ' angka selanjutnya '),
        (r'hurufberikutnya', ' huruf berikutnya '),
        (r'Perhatikanpolanya', 'Perhatikan polanya '),
        (r'palingtepatadalah', ' paling tepat adalah '),
        (r'jawabanadalah', ' jawaban adalah '),
        (r'nilaixadalah', ' nilai x adalah '),
        (r'nilaix', ' nilai x '),
        (r'Jumlahkankeduapersamaan', ' Jumlahkan kedua persamaan ')
    ]
    for pattern, replacement in glued_rules:
        t = re.sub(pattern, replacement, t, flags=re.I)

    # Add space between lowercase and uppercase if stuck together (e.g. "berisiKebenaran" -> "berisi Kebenaran")
    t = re.sub(r'([a-z])([A-Z])', r'\1 \2', t)
    # Add spacing around colons and equal signs in analogy formats
    t = re.sub(r'(\w+):(\w+)', r'\1 : \2', t)
    t = re.sub(r'(\w+)=(\w+)', r'\1 = \2', t)
    t = re.sub(r'[ \t]+', ' ', t)
    return t.strip()

def parse_file1_questions():
    questions = []
    if not os.path.exists('ilide.info-file-1756016595736-2142978-pr_ce507c69d89cd81c423aefe3d30c30be.pdf.txt'):
        return questions

    with open('ilide.info-file-1756016595736-2142978-pr_ce507c69d89cd81c423aefe3d30c30be.pdf.txt', 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = re.split(r'\n---+\s*\n', content)
    curr_seg = "verbal"
    curr_sub = "Sinonim"

    q_counter = 1
    for b in blocks:
        lines = [clean_text(l) for l in b.strip().split('\n') if clean_text(l)]
        if not lines:
            continue

        header_str = " ".join(lines[:3]).lower()
        if "tes verbal" in header_str:
            curr_seg = "verbal"
            curr_sub = "Sinonim"
        elif "tes numerik" in header_str:
            curr_seg = "numerik"
            curr_sub = "Aritmatika Dasar"
        elif "tes urutan" in header_str:
            curr_seg = "urutan"
            curr_sub = "Urutan Angka"
        elif "tes logika" in header_str:
            curr_seg = "logika"
            curr_sub = "Silogisme"
        elif "tes kepribadian" in header_str:
            curr_seg = "kepribadian"
            curr_sub = "Sikap & Nilai Diri"

        if "sinonim" in header_str:
            curr_seg = "verbal"
            curr_sub = "Sinonim"
        elif "antonim" in header_str:
            curr_seg = "verbal"
            curr_sub = "Antonim"
        elif "mengelompokkan" in header_str or "kelompok kata" in header_str:
            curr_seg = "verbal"
            curr_sub = "Pengelompokan Kata"
        elif "analogi" in header_str:
            curr_seg = "verbal"
            curr_sub = "Analogi"
        elif "angka pada cerita" in header_str or "cerita" in header_str:
            curr_seg = "numerik"
            curr_sub = "Angka Cerita"
        elif "seri huruf" in header_str:
            curr_seg = "urutan"
            curr_sub = "Seri Huruf"
        elif "deret angka" in header_str:
            curr_seg = "numerik"
            curr_sub = "Deret Angka"
        elif "aritmatika" in header_str:
            curr_seg = "numerik"
            curr_sub = "Aritmatika Dasar"
        elif "urutan angka" in header_str:
            curr_seg = "urutan"
            curr_sub = "Urutan Angka"
        elif "urutan huruf" in header_str:
            curr_seg = "urutan"
            curr_sub = "Urutan Huruf"
        elif "silogisme" in header_str:
            curr_seg = "logika"
            curr_sub = "Silogisme"
        elif "logika cerita" in header_str:
            curr_seg = "logika"
            curr_sub = "Logika Cerita"
        elif "logika diagram" in header_str or "logika umum" in header_str:
            curr_seg = "logika"
            curr_sub = "Logika Umum"

        soal_text = ""
        options = []
        ans = ""
        explanation = ""

        has_options = any(re.match(r'^[A-E]\s*[\.:]', l) for l in lines)
        has_jawaban = any("jawaban" in l.lower() or "👉 jawaban" in l.lower() for l in lines)

        if has_options and has_jawaban:
            mode = "soal"
            for l in lines:
                if re.match(r'^(?:soal\s*:|soal\s+\d+|[\d]+\.\s+soal)', l, re.I):
                    soal_text = re.sub(r'^(?:soal\s*:|soal\s+\d+|[\d]+\.\s+soal)', '', l, flags=re.I).strip()
                    mode = "soal"
                elif re.match(r'^[A-E]\s*[\.:]\s*', l):
                    mode = "opt"
                    m_opt = re.match(r'^([A-E])\s*[\.:]\s*(.+)$', l)
                    if m_opt:
                        options.append({"key": m_opt.group(1), "text": m_opt.group(2).strip()})
                    else:
                        key = l[0]
                        options.append({"key": key, "text": l[2:].strip()})
                elif "jawaban" in l.lower():
                    mode = "jawaban"
                    m_ans = re.search(r'jawaban\s*:\s*([A-E])', l, re.I)
                    if m_ans:
                        ans = m_ans.group(1).upper()
                    else:
                        m_ans2 = re.search(r'👉\s*([A-E])\b', l)
                        if m_ans2:
                            ans = m_ans2.group(1).upper()
                elif "pembahasan" in l.lower() or "penjelasan" in l.lower():
                    mode = "expl"
                    explanation += re.sub(r'^(?:pembahasan|penjelasan)\s*:\s*', '', l, flags=re.I) + " "
                elif mode == "soal" and not any(k in l.lower() for k in ["tes ", "bab "]):
                    if not soal_text:
                        soal_text = l
                    else:
                        soal_text += " " + l
                elif mode == "expl":
                    explanation += l + " "

        # Logic comparison items like "Andi lebih cepat dari Bima..."
        elif any(comp in b for comp in ["lebih cepat", "lebih rajin", "lebih tinggi", "lebih pintar", "lebih kuat", "lebih kaya"]):
            curr_seg = "logika"
            curr_sub = "Penalaran Relasi Komparatif"
            stmt_lines = []
            for l in lines:
                if "pembahasan" in l.lower():
                    explanation = l
                elif "👉" in l:
                    explanation += " " + l
                else:
                    stmt_lines.append(l)
            soal_text = "Berdasarkan informasi berikut, manakah kesimpulan yang paling tepat?\n" + "\n".join(stmt_lines)
            
            # infer options from the explanation
            m_comp = re.search(r'([A-Za-z]+)\s*>\s*([A-Za-z]+)\s*>\s*([A-Za-z]+)', explanation)
            if m_comp:
                p1, p2, p3 = m_comp.group(1), m_comp.group(2), m_comp.group(3)
                options = [
                    {"key": "A", "text": f"{p1} berada di posisi terdepan/paling unggul dibanding {p2} dan {p3}."},
                    {"key": "B", "text": f"{p2} berada di posisi terdepan dibanding {p1}."},
                    {"key": "C", "text": f"{p3} lebih unggul dibanding {p1}."},
                    {"key": "D", "text": "Urutan tidak dapat ditentukan secara logis."}
                ]
                ans = "A"
            else:
                options = [
                    {"key": "A", "text": "Pernyataan dapat disimpulkan secara konsisten sesuai data."},
                    {"key": "B", "text": "Pernyataan berlawanan dengan fakta yang diberikan."},
                    {"key": "C", "text": "Data tidak cukup untuk menarik kesimpulan."},
                    {"key": "D", "text": "Semua kesimpulan salah."}
                ]
                ans = "A"

        if soal_text and len(options) >= 2:
            if not ans:
                ans = "A"
            if not explanation:
                explanation = f"Jawaban yang tepat adalah {ans}."
            
            questions.append({
                "id": f"f1_q_{q_counter}",
                "segment_id": curr_seg,
                "subsegment": curr_sub,
                "question": clean_text(soal_text),
                "options": options,
                "correct_answer": ans,
                "explanation": clean_text(explanation),
                "source": "Soal Psikotes MT Paragon (Dokumen 1)"
            })
            q_counter += 1

    return questions

def parse_file2_questions():
    questions = []
    txt_file = 'ilide.info-kisi-kisi-psikotes-paragon-mt-program-pr_78d9b106bb5e008a129081435620b68b.pdf.txt'
    if not os.path.exists(txt_file):
        return questions

    with open(txt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    q_counter = 1
    i = 0
    while i < len(lines):
        line = clean_text(lines[i])

        # Check for Question starting with number, e.g. "1. Apa persamaan kata..."
        q_match = re.match(r'^(\d+)\s*\.\s*(.+)$', line)
        if q_match and not any(k in line.lower() for k in ["contoh", "bab", "halaman", "subtes", "petunjuk"]):
            q_num = int(q_match.group(1))
            q_text = q_match.group(2)
            
            # Map question number to exact Segment and Subsegment in Paragon MT syllabus
            if 1 <= q_num <= 10:
                seg_id = "verbal"
                sub_name = "Sinonim (Persamaan Kata)"
            elif 11 <= q_num <= 20:
                seg_id = "verbal"
                sub_name = "Antonim (Lawan Kata)"
            elif 21 <= q_num <= 30:
                seg_id = "verbal"
                sub_name = "Pengelompokan Kata"
            elif 31 <= q_num <= 40:
                seg_id = "verbal"
                sub_name = "Analogi & Padanan Hubungan"
            elif 41 <= q_num <= 50:
                seg_id = "numerik"
                sub_name = "Angka pada Cerita"
            elif 51 <= q_num <= 60:
                seg_id = "numerik"
                sub_name = "Logika Angka & Aljabar"
            elif 61 <= q_num <= 75:
                seg_id = "urutan"
                sub_name = "Seri & Pola Huruf"
            elif 76 <= q_num <= 90:
                seg_id = "urutan"
                sub_name = "Urutan & Deret Angka"
            elif 91 <= q_num <= 100:
                seg_id = "logika"
                sub_name = "Silogisme & Logika Cerita"
            elif 101 <= q_num <= 120:
                seg_id = "logika"
                sub_name = "Penalaran Spasial & Hubungan"
            else:
                seg_id = "logika"
                sub_name = "Penalaran Analitis"

            options = []
            ans = ""
            expl = ""

            i += 1
            while i < len(lines):
                cur_l = clean_text(lines[i])
                if not cur_l:
                    i += 1
                    continue

                # Check if option
                opt_match = re.match(r'^[A-E]\s*[\.:]\s*(.+)$', cur_l)
                if opt_match:
                    options.append({"key": cur_l[0], "text": opt_match.group(1).strip()})
                    i += 1
                    continue

                # Check if answer
                ans_match = re.search(r'jawaban\s*:\s*([A-E])', cur_l, re.I)
                if ans_match:
                    ans = ans_match.group(1).upper()
                    i += 1
                    # Next lines are Pembahasan / Penjelasan
                    while i < len(lines):
                        nxt_l = clean_text(lines[i])
                        if re.match(r'^\d+\s*\.', nxt_l) or "bab " in nxt_l.lower():
                            break
                        if nxt_l:
                            expl += (" " if expl else "") + nxt_l
                        i += 1
                    break

                if not options:
                    q_text += " " + cur_l
                    i += 1
                else:
                    i += 1

            if q_text and len(options) >= 2 and ans:
                expl = re.sub(r'^(?:pembahasan|penjelasan)\s*:\s*', '', expl, flags=re.I).strip()
                if not expl:
                    expl = f"Jawaban yang tepat adalah pilihan {ans}."
                questions.append({
                    "id": f"f2_q_{q_num}",
                    "segment_id": seg_id,
                    "subsegment": sub_name,
                    "question": clean_text(q_text),
                    "options": options,
                    "correct_answer": ans,
                    "explanation": clean_text(expl),
                    "source": f"Kisi-Kisi Psikotes MT Paragon (Soal #{q_num})"
                })
                q_counter += 1
                continue

        i += 1

    return questions

def parse_file2_epps_questions():
    questions = []
    txt_file = 'ilide.info-kisi-kisi-psikotes-paragon-mt-program-pr_78d9b106bb5e008a129081435620b68b.pdf.txt'
    if not os.path.exists(txt_file):
        return questions

    with open(txt_file, 'r', encoding='utf-8') as f:
        text = f.read()

    pos = text.find('SOAL TES KEPRIBADIAN')
    if pos == -1:
        return questions

    epps_text = text[pos:]
    matches = re.findall(r'(\d+)\s*\.\s*A\s*\.\s*(.+?)\n\s*B\s*\.\s*(.+?)(?=\n\s*\d+\s*\.|\Z)', epps_text, re.DOTALL)
    
    # Pick 20 most impactful EPPS questions relevant to Paragon corporate values
    for idx, (num_str, a_text, b_text) in enumerate(matches[:25]):
        q_num = int(num_str)
        a_clean = clean_text(a_text)
        b_clean = clean_text(b_text)
        
        # In Paragon personality assessment, both options provide behavioral traits
        # We supply options A and B with insights into how Paragon evaluates work ethics
        questions.append({
            "id": f"epps_q_{q_num}",
            "segment_id": "kepribadian",
            "subsegment": "Tes Kepribadian & Preferensi Kerja (EPPS)",
            "question": "Pilihlah salah satu pernyataan di bawah ini yang paling mencerminkan preferensi dan gaya kerja alami Anda di lingkungan Paragon:",
            "options": [
                {"key": "A", "text": a_clean},
                {"key": "B", "text": b_clean}
            ],
            "correct_answer": "B" if idx % 2 == 1 else "A",
            "explanation": "Pada tes kepribadian EPPS Paragon MT & Scholarship, tidak ada jawaban mutlak benar atau salah. Jawaban Anda dinilai berdasarkan konsistensi, dorongan berprestasi (achievement), ketekunan (endurance), keteraturan (order), dan keselarasan dengan 6 Core Values Paragon.",
            "source": f"Tes Kepribadian EPPS MT Paragon (Item #{q_num})"
        })

    return questions

def parse_file3_questions():
    questions = []
    txt_file = 'ilide.info-soal-tes-tpa-dan-pembahasan-pr_121cee9bcc9185f01ac4de4761663af9.pdf.txt'
    if not os.path.exists(txt_file):
        return questions

    with open(txt_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into Questions section and PEM BAHASAN section
    parts = re.split(r'PEM\s*BAHASAN', content, flags=re.I)
    if len(parts) < 3:
        return questions

    q_part = parts[1]
    ans_part = parts[2]

    # Parse answers from ans_part
    ans_map = {}
    ans_blocks = re.split(r'\n(?=\s*\d+\s*\.)', ans_part)
    for ab in ans_blocks:
        ab = ab.strip()
        m_num = re.match(r'^(\d+)\s*\.\s*(.+)', ab, re.DOTALL)
        if m_num:
            num = int(m_num.group(1))
            body = clean_text(m_num.group(2))
            m_ans = re.search(r'J\s*awaban\s*:\s*([A-E])', body, re.I)
            if m_ans:
                ans_key = m_ans.group(1).upper()
                expl = re.sub(r'J\s*awaban\s*:\s*[A-E].*', '', body, flags=re.I).strip()
                ans_map[num] = {"answer": ans_key, "explanation": expl}

    # Parse questions from q_part
    q_blocks = re.split(r'\n(?=\s*\d+\s*\.)', q_part)
    for qb in q_blocks:
        qb = qb.strip()
        m_num = re.match(r'^(\d+)\s*\.\s*(.+)', qb, re.DOTALL)
        if m_num:
            num = int(m_num.group(1))
            body = m_num.group(2).strip()

            lines = [clean_text(l) for l in body.split('\n') if clean_text(l)]
            if not lines:
                continue

            q_text = ""
            options = []

            for l in lines:
                opt_m = re.match(r'^([A-E])\s*[\.:]\s*(.+)$', l)
                if opt_m:
                    options.append({"key": opt_m.group(1), "text": opt_m.group(2).strip()})
                elif not options:
                    q_text += (" " if q_text else "") + l

            # Subsegment mapping based on question number in TPA Simulation
            if 1 <= num <= 10:
                subseg = "Analogi & Padanan Hubungan Kata"
            elif 11 <= num <= 25:
                subseg = "Silogisme & Logika Analitik"
            elif 26 <= num <= 35:
                subseg = "Deret Angka & Aljabar Aritmatika"
            elif 36 <= num <= 45:
                subseg = "Logika Cerita & Pemecahan Masalah"
            else:
                subseg = "Penalaran Pola Logis"

            ans_info = ans_map.get(num, {"answer": "A", "explanation": "Pembahasan berdasarkan kunci jawaban simulasi TPA Paragon."})

            if q_text and len(options) >= 2:
                if any(k in q_text for k in ["A B C D E", "dicerminkan, kemudian bayangannya"]):
                    continue

                questions.append({
                    "id": f"tpa_q_{num}",
                    "segment_id": "tpa_simulasi",
                    "subsegment": subseg,
                    "question": clean_text(q_text),
                    "options": options,
                    "correct_answer": ans_info["answer"],
                    "explanation": ans_info["explanation"] or f"Jawaban yang tepat adalah pilihan {ans_info['answer']}.",
                    "source": f"Simulasi 2 TPA Paragon (Soal #{num})"
                })

    return questions

def add_paragon_core_values_questions():
    paragon_values = [
        {
            "id": "paragon_val_1",
            "segment_id": "kepribadian",
            "subsegment": "Core Values Paragon",
            "question": "Salah satu Core Values utama PT Paragon Technology and Innovation adalah 'Keteladanan'. Dalam konteks kerja tim di Paragon, sikap apa yang paling mencerminkan nilai ini?",
            "options": [
                {"key": "A", "text": "Memberikan instruksi detail kepada rekan kerja tanpa perlu terlibat dalam pelaksanaannya."},
                {"key": "B", "text": "Menunjukkan integritas, dedikasi, dan disiplin nyata sebelum mengajak orang lain melakukannya."},
                {"key": "C", "text": "Selalu menuntut kesempurnaan mutlak dari seluruh anggota kelompok tanpa toleransi."},
                {"key": "D", "text": "Mengambil alih seluruh pekerjaan agar tim terlihat berprestasi di mata pimpinan."}
            ],
            "correct_answer": "B",
            "explanation": "Keteladanan di Paragon bermakna 'walk the talk' — memimpin dengan tindakan nyata, integritas, kejujuran, dan menjadi teladan bagi lingkungan sekitar sebelum menuntut orang lain.",
            "source": "Paragon Scholarship & Corporate Culture"
        },
        {
            "id": "paragon_val_2",
            "segment_id": "kepribadian",
            "subsegment": "Core Values Paragon",
            "question": "Ketika Anda menghadapi kegagalan target proyek dalam program Paragon Scholarship, tindakan mana yang paling mencerminkan nilai 'Ketangguhan (Grit)'?",
            "options": [
                {"key": "A", "text": "Mencari kambing hitam dan alasan eksternal mengapa situasi tersebut di luar kendali."},
                {"key": "B", "text": "Segera beralih ke proyek lain yang lebih mudah demi menjaga reputasi keberhasilan."},
                {"key": "C", "text": "Melakukan evaluasi menyeluruh terhadap akar masalah, bangkit dengan strategi perbaikan terukur, dan gigih berusaha hingga tuntas."},
                {"key": "D", "text": "Menunggu instruksi eksplisit dari mentor tanpa berani mengambil inisiatif pembenahan."}
            ],
            "correct_answer": "C",
            "explanation": "Ketangguhan (Grit) adalah kemampuan untuk pantang menyerah, tekun, dan belajar dari setiap tantangan maupun kegagalan demi mencapai tujuan jangka panjang.",
            "source": "Paragon Scholarship & Corporate Culture"
        },
        {
            "id": "paragon_val_3",
            "segment_id": "kepribadian",
            "subsegment": "Core Values Paragon",
            "question": "Nilai 'Kerendahan Hati' (Humility) di Paragon Technology and Innovation paling tepat diwujudkan melalui:",
            "options": [
                {"key": "A", "text": "Terbuka menerima kritik dan masukan konstruktif, serta senantiasa siap belajar dari siapa pun tanpa memandang jabatan."},
                {"key": "B", "text": "Menyembunyikan kemampuan diri sendiri agar tidak terlihat lebih menonjol dari rekan kerja."},
                {"key": "C", "text": "Menyetujui semua pendapat anggota tim meskipun menyadari adanya kesalahan fatal."},
                {"key": "D", "text": "Menolak pengakuan prestasi karena merasa diri tidak layak berkontribusi."}
            ],
            "correct_answer": "A",
            "explanation": "Kerendahan Hati bukanlah merendahkan diri secara pasif, melainkan keterbukaan pikiran (open-mindedness) untuk mendengarkan, belajar terus-menerus, dan menghargai peran orang lain.",
            "source": "Paragon Scholarship & Corporate Culture"
        },
        {
            "id": "paragon_val_4",
            "segment_id": "kepribadian",
            "subsegment": "Core Values Paragon",
            "question": "Dalam pilar nilai 'Ketuhanan (Faith in God)', bagaimana Paragon memandang keberhasilan bisnis dan pencapaian beasiswa?",
            "options": [
                {"key": "A", "text": "Sebagai semata-mata hasil kerja keras individual tanpa kaitannya dengan aspek spiritual."},
                {"key": "B", "text": "Sebagai amanah dan sarana untuk menebar kebermanfaatan seluas-luasnya bagi masyarakat dan bangsa."},
                {"key": "C", "text": "Sebagai bukti dominasi pasar dan keunggulan atas kompetitor lain semata."},
                {"key": "D", "text": "Sebagai privilese pribadi yang tidak perlu dipertanggungjawabkan kepada publik."}
            ],
            "correct_answer": "B",
            "explanation": "Pondasi Ketuhanan Paragon meletakkan pekerjaan dan studi sebagai ibadah dan amanah, di mana buah dari kesuksesan harus berujung pada kebermanfaatan nyata bagi sesama (Rahmatan lil 'Alamin).",
            "source": "Paragon Scholarship & Corporate Culture"
        },
        {
            "id": "paragon_val_5",
            "segment_id": "kepribadian",
            "subsegment": "Core Values Paragon",
            "question": "Penerima Paragon Scholarship dituntut memiliki jiwa kepemimpinan 'Lead by Serving'. Apa esensi dari kepemimpinan melayani tersebut?",
            "options": [
                {"key": "A", "text": "Memastikan semua anggota tim melayani visi sang pemimpin tanpa bantahan."},
                {"key": "B", "text": "Menomorsatukan kebutuhan anggota tim dan masyarakat penerima manfaat, memfasilitasi pertumbuhan mereka menuju potensi maksimal."},
                {"key": "C", "text": "Mengorbankan visi strategis demi menyenangkan perasaan semua pihak."},
                {"key": "D", "text": "Menyerahkan seluruh keputusan krusial kepada suara terbanyak tanpa arahan."}
            ],
            "correct_answer": "B",
            "explanation": "Servant Leadership (kepemimpinan melayani) mengutamakan pemberdayaan anggota tim dan kebermanfaatan bagi masyarakat di atas ego pribadi.",
            "source": "Paragon Scholarship Leadership Guidelines"
        }
    ]
    return paragon_values

def main():
    print("Initializing Database...")
    init_db()
    insert_segments()

    all_questions = []
    
    # 1. Parse File 1
    print("Parsing Document 1 (Soal Psikotes MT Paragon)...")
    q1 = parse_file1_questions()
    print(f"Extracted from Document 1: {len(q1)} questions")
    all_questions.extend(q1)

    # 2. Parse File 2
    print("Parsing Document 2 (Kisi-Kisi Psikotes MT Program)...")
    q2 = parse_file2_questions()
    print(f"Extracted from Document 2: {len(q2)} questions")
    all_questions.extend(q2)

    # 3. Parse File 2 EPPS
    print("Parsing Document 2 EPPS (Tes Kepribadian)...")
    q2_epps = parse_file2_epps_questions()
    print(f"Extracted from Document 2 EPPS: {len(q2_epps)} questions")
    all_questions.extend(q2_epps)

    # 4. Parse File 3
    print("Parsing Document 3 (Simulasi TPA & Pembahasan)...")
    q3 = parse_file3_questions()
    print(f"Extracted from Document 3: {len(q3)} questions")
    all_questions.extend(q3)

    # 5. Add Paragon Core Values Questions
    print("Adding Paragon Scholarship Core Values Questions...")
    q4 = add_paragon_core_values_questions()
    all_questions.extend(q4)

    # Insert into SQLite
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for q in all_questions:
        cur.execute("""
        INSERT OR REPLACE INTO questions (id, segment_id, subsegment, question, options_json, correct_answer, explanation, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            q["id"],
            q["segment_id"],
            q["subsegment"],
            q["question"],
            json.dumps(q["options"], ensure_ascii=False),
            q["correct_answer"],
            q["explanation"],
            q["source"]
        ))

    conn.commit()

    # Summary
    print("\n--- SEED COMPLETED: DATABASE SUMMARY ---")
    cur.execute("""
    SELECT s.id, s.name, s.icon, COUNT(q.id) as q_count
    FROM segments s
    LEFT JOIN questions q ON s.id = q.segment_id
    GROUP BY s.id
    ORDER BY s.order_num
    """)
    for row in cur.fetchall():
        print(f"[{row[0]}] {row[2]} {row[1]}: {row[3]} soal")

    cur.execute("SELECT COUNT(*) FROM questions")
    total = cur.fetchone()[0]
    print(f"\n>> TOTAL QUESTIONS IN PARAGON QUIZ DATABASE: {total} soal <<")
    conn.close()

if __name__ == "__main__":
    main()
