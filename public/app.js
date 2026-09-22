/**
 * PARAGON SCHOLARSHIP QUIZ PLATFORM • APPLICATION CONTROLLER
 * Full-stack interactive quiz logic, Web Audio API synthesis,
 * Speech synthesis, bottom-sheet review modal, and REST API integration.
 */

// Application State
const state = {
  currentView: 'dashboard',
  segments: [],
  selectedSegmentId: null,
  selectedSegmentObj: null,
  selectedSubsegment: '',
  selectedLimit: 10,
  selectedTimerSec: 30,
  
  // Active Quiz State
  quizQuestions: [],
  currentIndex: 0,
  selectedOption: null,
  userAnswers: [], // { question_id, selected, is_correct, question, options, correct_answer, explanation }
  
  // Timer State
  timerId: null,
  timeRemaining: 0,
  quizStartTime: null,
  
  // Audio state
  soundEnabled: true,
  audioCtx: null,

  // Offline / Vercel Static Dataset Cache
  allQuestionsData: null
};

// ==========================================================================
// 0. PASSWORD GATE SECURITY ("persebayaselamanya")
// ==========================================================================
const ACCESS_PASSCODE = 'persebayaselamanya';

function checkGateAuth() {
  const gate = document.getElementById('password-gate');
  const input = document.getElementById('gate-password-input');
  const stored = localStorage.getItem('paragon_passcode_auth');

  if (stored === ACCESS_PASSCODE) {
    if (gate) gate.classList.add('unlocked');
  } else {
    if (gate) {
      gate.classList.remove('unlocked');
      if (input) setTimeout(() => input.focus(), 250);
    }
  }
}

function handleUnlockSubmit(event) {
  if (event) event.preventDefault();
  const input = document.getElementById('gate-password-input');
  const msg = document.getElementById('gate-msg');
  const card = document.getElementById('gate-card');
  const gate = document.getElementById('password-gate');
  const val = (input ? input.value : '').trim().toLowerCase();

  if (val === ACCESS_PASSCODE) {
    playCorrectTone();
    if (card) card.classList.add('success-card');
    if (msg) {
      msg.className = 'gate-msg success';
      msg.textContent = '✅ Akses Diterima! Selamat belajar 🎓✨';
    }
    localStorage.setItem('paragon_passcode_auth', ACCESS_PASSCODE);
    setTimeout(() => {
      if (gate) gate.classList.add('unlocked');
      showToast('Selamat datang di Portal Kuis Paragon! 🎓');
    }, 450);
  } else {
    playWrongTone();
    if (card) {
      card.classList.remove('shake-card');
      void card.offsetWidth;
      card.classList.add('shake-card');
    }
    if (msg) {
      msg.className = 'gate-msg error';
      msg.textContent = '⚠️ Kode sandi salah! Periksa kembali.';
    }
    if (input) {
      input.select();
      input.focus();
    }
  }
}

function lockApp() {
  localStorage.removeItem('paragon_passcode_auth');
  const gate = document.getElementById('password-gate');
  const input = document.getElementById('gate-password-input');
  const msg = document.getElementById('gate-msg');
  const card = document.getElementById('gate-card');
  if (card) {
    card.classList.remove('success-card', 'shake-card');
  }
  if (input) input.value = '';
  if (msg) {
    msg.className = 'gate-msg';
    msg.textContent = '';
  }
  if (gate) gate.classList.remove('unlocked');
  showToast('Aplikasi telah dikunci 🔒');
  if (input) setTimeout(() => input.focus(), 250);
}

function togglePasswordVisibility() {
  const input = document.getElementById('gate-password-input');
  const eyeIcon = document.getElementById('gate-eye-icon');
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    if (eyeIcon) {
      eyeIcon.innerHTML = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line>';
    }
  } else {
    input.type = 'password';
    if (eyeIcon) {
      eyeIcon.innerHTML = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>';
    }
  }
}

window.handleUnlockSubmit = handleUnlockSubmit;
window.lockApp = lockApp;
window.togglePasswordVisibility = togglePasswordVisibility;

// Helper to fetch static data fallback (for Vercel & Offline)
async function getStaticQuizData() {
  if (state.allQuestionsData) return state.allQuestionsData;
  const paths = [
    'data/quiz_data.json',
    '/data/quiz_data.json',
    '/static/data/quiz_data.json',
    'public/data/quiz_data.json'
  ];
  for (const p of paths) {
    try {
      const res = await fetch(p);
      if (res.ok) {
        state.allQuestionsData = await res.json();
        return state.allQuestionsData;
      }
    } catch (e) {}
  }
  return null;
}

// ==========================================================================
// 1. SOUND SYNTHESIZER (WEB AUDIO API - ZERO EXTERNAL ASSET DEPENDENCY)
// ==========================================================================
function getAudioContext() {
  if (!state.audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (AudioContextClass) {
      state.audioCtx = new AudioContextClass();
    }
  }
  if (state.audioCtx && state.audioCtx.state === 'suspended') {
    state.audioCtx.resume();
  }
  return state.audioCtx;
}

function playSelectTone() {
  if (!state.soundEnabled) return;
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(480, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(620, ctx.currentTime + 0.08);
    gain.gain.setValueAtTime(0.12, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.08);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.09);
  } catch (e) {
    console.warn('Audio play error:', e);
  }
}

function playCorrectTone() {
  if (!state.soundEnabled) return;
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6 major chord
    notes.forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(freq, ctx.currentTime + idx * 0.07);
      gain.gain.setValueAtTime(0.18, ctx.currentTime + idx * 0.07);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + idx * 0.07 + 0.28);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(ctx.currentTime + idx * 0.07);
      osc.stop(ctx.currentTime + idx * 0.07 + 0.3);
    });
  } catch (e) {
    console.warn('Audio play error:', e);
  }
}

function playWrongTone() {
  if (!state.soundEnabled) return;
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const notes = [260, 220];
    notes.forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(freq, ctx.currentTime + idx * 0.12);
      gain.gain.setValueAtTime(0.12, ctx.currentTime + idx * 0.12);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + idx * 0.12 + 0.18);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(ctx.currentTime + idx * 0.12);
      osc.stop(ctx.currentTime + idx * 0.12 + 0.2);
    });
  } catch (e) {
    console.warn('Audio play error:', e);
  }
}

// Text to speech (speechSynthesis)
function speakCurrentQuestion() {
  if (!('speechSynthesis' in window)) {
    showToast('Fitur suara tidak didukung browser ini.');
    return;
  }
  window.speechSynthesis.cancel();
  const q = state.quizQuestions[state.currentIndex];
  if (!q) return;

  const textToRead = `${q.question}. Pilihan: ${q.options.map(o => `${o.key}: ${o.text}`).join(', ')}`;
  const utterance = new SpeechSynthesisUtterance(textToRead);
  utterance.lang = 'id-ID';
  utterance.rate = 1.0;
  window.speechSynthesis.speak(utterance);
}

// ==========================================================================
// 2. VIEW CONTROLLER
// ==========================================================================
function switchView(viewName) {
  state.currentView = viewName;
  document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
  const target = document.getElementById(`view-${viewName}`);
  if (target) {
    target.classList.add('active');
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showToast(message) {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 3200);
}

// ==========================================================================
// 3. DASHBOARD & SEGMENT LOADING
// ==========================================================================
async function loadSegmentsAndStats() {
  try {
    let data = null;
    try {
      const res = await fetch('/api/segments');
      if (res.ok) {
        data = await res.json();
      }
    } catch (apiErr) {
      console.warn('API /api/segments unavailable, falling back to static data');
    }

    if (!data) {
      const staticDb = await getStaticQuizData();
      if (staticDb) {
        data = {
          segments: staticDb.segments,
          total_questions: staticDb.total_questions
        };
      }
    }

    if (data) {
      state.segments = data.segments || [];
      const totalEl = document.getElementById('stat-total-q');
      if (totalEl) totalEl.textContent = data.total_questions || 218;
      const countBadge = document.getElementById('segment-count-badge');
      if (countBadge) countBadge.textContent = `${state.segments.length} Segmen Ujian`;

      renderSegmentsGrid(state.segments);
    }

    // Also fetch user stats
    loadUserStats();
  } catch (err) {
    console.error('Error loading segments:', err);
    document.getElementById('segments-container').innerHTML = `
      <div class="error-msg">Gagal memuat segmen kuis.</div>
    `;
  }
}

function renderSegmentsGrid(segments) {
  const container = document.getElementById('segments-container');
  if (!container) return;
  container.innerHTML = '';

  segments.forEach(seg => {
    const card = document.createElement('div');
    card.className = 'segment-card';
    card.onclick = () => openSegmentConfigModal(seg);

    card.innerHTML = `
      <div class="segment-top">
        <div class="segment-icon">${seg.icon}</div>
        <div class="segment-info">
          <span class="segment-badge">${seg.badge}</span>
          <h3 class="segment-name">${seg.name}</h3>
          <p class="segment-desc">${seg.description}</p>
        </div>
      </div>
      <div class="segment-bottom">
        <span class="segment-count-tag">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
          ${seg.question_count} Soal
        </span>
        <button class="segment-action-btn">Mulai Latihan ➔</button>
      </div>
    `;
    container.appendChild(card);
  });
}

async function loadUserStats() {
  try {
    let stats = null;
    let historyList = [];

    try {
      const res = await fetch('/api/stats');
      if (res.ok) {
        stats = await res.json();
      }
      const histRes = await fetch('/api/history?limit=5');
      if (histRes.ok) {
        const histData = await histRes.json();
        historyList = histData.history || [];
      }
    } catch (e) {
      console.warn('Backend stats unavailable, using localStorage fallback');
    }

    // LocalStorage fallback if backend wasn't reachable
    if (!stats) {
      const localHist = JSON.parse(localStorage.getItem('paragon_quiz_history') || '[]');
      const totalQuizzes = localHist.length;
      let sumAcc = 0;
      localHist.forEach(h => { sumAcc += (h.accuracy || 0); });
      const avgAcc = totalQuizzes > 0 ? Math.round(sumAcc / totalQuizzes) : 0;
      stats = {
        total_quizzes: totalQuizzes,
        average_accuracy: avgAcc
      };
      historyList = localHist.slice(0, 5);
    }

    const qDoneEl = document.getElementById('stat-quizzes-done');
    if (qDoneEl) qDoneEl.textContent = stats.total_quizzes || 0;
    const avgAccEl = document.getElementById('stat-avg-acc');
    if (avgAccEl) avgAccEl.textContent = `${stats.average_accuracy || 0}%`;

    const historyListContainer = document.getElementById('history-list');
    const historyWrapper = document.getElementById('recent-history-wrapper');

    if (historyList && historyList.length > 0) {
      if (historyWrapper) historyWrapper.style.display = 'block';
      if (historyListContainer) {
        historyListContainer.innerHTML = '';
        historyList.forEach(h => {
          const row = document.createElement('div');
          row.className = 'history-row';
          const min = Math.floor((h.time_spent_sec || 0) / 60);
          const sec = (h.time_spent_sec || 0) % 60;
          const timeStr = `${min}:${sec < 10 ? '0' : ''}${sec}`;
          const dateStr = h.completed_at ? h.completed_at.slice(0, 16).replace('T', ' ') : 'Baru saja';
          row.innerHTML = `
            <div>
              <strong>${h.segment_icon || '📝'} ${h.segment_name || 'Kuis'}</strong>
              <span style="color:#64748B; font-size:0.75rem; margin-left:8px;">${dateStr}</span>
            </div>
            <div>
              <span style="font-weight:700; color: ${(h.accuracy || 0) >= 75 ? '#16A34A' : '#D97706'}">${h.score}/${h.total} (${h.accuracy || 0}%)</span>
              <span style="color:#94A3B8; font-size:0.75rem; margin-left:8px;">⏱ ${timeStr}</span>
            </div>
          `;
          historyListContainer.appendChild(row);
        });
      }
    }
  } catch (e) {
    console.warn('Failed loading history stats:', e);
  }
}


// ==========================================================================
// 4. SEGMENT CONFIG MODAL
// ==========================================================================
function openSegmentConfigModal(seg) {
  state.selectedSegmentId = seg.id;
  state.selectedSegmentObj = seg;

  document.getElementById('modal-seg-icon').textContent = seg.icon;
  document.getElementById('modal-seg-title').textContent = seg.name;
  document.getElementById('modal-seg-desc').textContent = `${seg.question_count} soal tersedia di bank data`;

  // populate subsegments
  const subSelect = document.getElementById('config-subsegment');
  subSelect.innerHTML = '<option value="">Semua Subtopik (Lengkap)</option>';
  if (seg.subsegments && seg.subsegments.length > 0) {
    seg.subsegments.forEach(sub => {
      const opt = document.createElement('option');
      opt.value = sub;
      opt.textContent = sub;
      subSelect.appendChild(opt);
    });
    document.getElementById('subsegment-filter-group').style.display = 'block';
  } else {
    document.getElementById('subsegment-filter-group').style.display = 'none';
  }

  document.getElementById('modal-segment-config').classList.add('active');
}

function closeSegmentConfigModal() {
  document.getElementById('modal-segment-config').classList.remove('active');
}

// ==========================================================================
// 5. QUIZ ENGINE (EXACT MATCH TO REFERENCE MOCKUP)
// ==========================================================================
async function startQuiz(segmentId, subsegment = '', limit = 10, timerSec = 30) {
  try {
    closeSegmentConfigModal();
    let questions = [];

    // Attempt API first
    try {
      let url = `/api/quiz?segment=${segmentId || 'all'}&limit=${limit}&shuffle=true`;
      if (subsegment) {
        url += `&subsegment=${encodeURIComponent(subsegment)}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        questions = data.questions || [];
      }
    } catch (e) {
      console.warn('API quiz endpoint unavailable, using static fallback:', e);
    }

    // Fallback to staticDb if needed
    if (!questions || questions.length === 0) {
      const db = await getStaticQuizData();
      if (db && db.questions) {
        let pool = db.questions;
        if (segmentId && segmentId !== 'all') {
          pool = pool.filter(q => q.segment_id === segmentId);
        }
        if (subsegment) {
          pool = pool.filter(q => q.subsegment === subsegment);
        }
        // Random shuffle
        pool = [...pool].sort(() => 0.5 - Math.random());
        const count = limit > 0 ? limit : 10;
        questions = pool.slice(0, Math.min(count, pool.length));
      }
    }

    if (!questions || questions.length === 0) {
      showToast('Tidak ada soal pada kategori ini.');
      return;
    }

    state.quizQuestions = questions;
    state.currentIndex = 0;
    state.userAnswers = [];
    state.selectedTimerSec = timerSec;
    state.quizStartTime = Date.now();

    // Setup Header Breadcrumb
    const segObj = state.segments.find(s => s.id === segmentId);
    const segTitle = segObj ? segObj.name : 'Simulasi Paragon';
    const subTitle = subsegment || (data && data.questions && data.questions[0] ? data.questions[0].subsegment : (questions[0] ? questions[0].subsegment : 'Umum'));

    document.getElementById('quiz-subsegment-title').textContent = subTitle;
    document.getElementById('quiz-breadcrumb').textContent = `${segTitle} • Paragon Scholarship • ${state.quizQuestions.length} Soal`;

    switchView('quiz');
    displayCurrentQuestion();
  } catch (err) {
    console.error('Error starting quiz:', err);
    showToast('Gagal memulai kuis.');
  }
}


function displayCurrentQuestion() {
  // Reset Bottom Sheet & Check Button
  closeBottomSheet();
  clearInterval(state.timerId);
  window.speechSynthesis && window.speechSynthesis.cancel();

  state.selectedOption = null;
  const q = state.quizQuestions[state.currentIndex];
  const total = state.quizQuestions.length;
  const currNum = state.currentIndex + 1;

  // 1. Progress Bar (Matches mockup: e.g. "1/12", green bar, target 🎯)
  document.getElementById('progress-text').textContent = `${currNum}/${total}`;
  const pct = (currNum / total) * 100;
  document.getElementById('progress-fill').style.width = `${pct}%`;

  // 2. Subsegment Title update
  if (q.subsegment) {
    document.getElementById('quiz-subsegment-title').textContent = q.subsegment;
  }

  // 3. Question statement
  document.getElementById('question-text').textContent = q.question;
  document.getElementById('question-source').textContent = q.source ? `Sumber: ${q.source}` : '';

  // 4. Render Options (Matches mockup cards with radio buttons)
  const optionsContainer = document.getElementById('options-container');
  optionsContainer.innerHTML = '';

  q.options.forEach(opt => {
    const card = document.createElement('div');
    card.className = 'option-card';
    card.dataset.key = opt.key;

    card.innerHTML = `
      <div class="radio-circle">
        <div class="radio-dot"></div>
      </div>
      <div class="option-text">${opt.text}</div>
    `;

    card.onclick = () => selectOption(opt.key, card);
    optionsContainer.appendChild(card);
  });

  // 5. Check Button: Disabled & Gray at start (Screen 1)
  const checkBtn = document.getElementById('btn-check-answer');
  checkBtn.disabled = true;
  checkBtn.className = 'check-btn disabled';
  checkBtn.textContent = 'Check';

  // 6. Start Timer if enabled
  initQuestionTimer();
}

function selectOption(key, cardEl) {
  // If already answered/sheet is open, ignore
  if (document.getElementById('bottom-sheet').classList.contains('active')) return;

  state.selectedOption = key;
  playSelectTone();

  // Highlight selected card (Screen 2: Teal/Blue outline & background tint)
  document.querySelectorAll('.option-card').forEach(el => {
    el.classList.remove('selected');
  });
  cardEl.classList.add('selected');

  // Turn Check Button ACTIVE (Screen 2: Vibrant Red/Coral #FF4B4B)
  const checkBtn = document.getElementById('btn-check-answer');
  checkBtn.disabled = false;
  checkBtn.className = 'check-btn';
}

function initQuestionTimer() {
  const timerBadge = document.getElementById('timer-display');
  const timerText = document.getElementById('timer-text');

  if (state.selectedTimerSec <= 0) {
    timerBadge.style.display = 'none';
    return;
  }

  timerBadge.style.display = 'inline-flex';
  timerBadge.classList.remove('urgent');
  state.timeRemaining = state.selectedTimerSec;
  updateTimerText();

  state.timerId = setInterval(() => {
    state.timeRemaining--;
    updateTimerText();

    if (state.timeRemaining <= 5 && state.timeRemaining > 0) {
      timerBadge.classList.add('urgent');
    }

    if (state.timeRemaining <= 0) {
      clearInterval(state.timerId);
      // Auto-check if timer expires
      handleTimerExpired();
    }
  }, 1000);
}

function updateTimerText() {
  const sec = state.timeRemaining;
  const timerText = document.getElementById('timer-text');
  timerText.textContent = `00:${sec < 10 ? '0' : ''}${sec} Sec`;
}

function handleTimerExpired() {
  showToast('⏰ Waktu habis untuk soal ini!');
  if (!state.selectedOption) {
    // default to empty answer and trigger check
    state.selectedOption = 'TIMEOUT';
  }
  handleCheckAnswer();
}

// ==========================================================================
// 6. CHECK ANSWER & BOTTOM SHEET MODAL (SCREEN 3)
// ==========================================================================
function handleCheckAnswer() {
  clearInterval(state.timerId);
  const q = state.quizQuestions[state.currentIndex];
  const userChoice = state.selectedOption;
  const correctChoice = q.correct_answer.trim().toUpperCase();

  const isCorrect = (userChoice === correctChoice);

  // Record Answer
  state.userAnswers.push({
    question_id: q.id,
    selected: userChoice,
    is_correct: isCorrect,
    question: q.question,
    options: q.options,
    correct_answer: correctChoice,
    explanation: q.explanation
  });

  // Highlight option cards on screen
  document.querySelectorAll('.option-card').forEach(card => {
    const key = card.dataset.key;
    if (key === correctChoice) {
      card.classList.add('correct');
    } else if (key === userChoice && !isCorrect) {
      card.classList.add('incorrect');
    }
  });

  // Open Bottom Sheet (Matches Screen 3)
  openBottomSheet(isCorrect, correctChoice, q.explanation);
}

function openBottomSheet(isCorrect, correctChoice, explanation) {
  const sheet = document.getElementById('bottom-sheet');
  const backdrop = document.getElementById('sheet-backdrop');
  const sheetTitle = document.getElementById('sheet-title');
  const iconBadge = document.getElementById('sheet-icon-badge');
  const sheetIcon = document.getElementById('sheet-icon');
  const sheetCheer = document.getElementById('sheet-cheer');
  const explText = document.getElementById('explanation-text');
  const nextBtn = document.getElementById('btn-sheet-next');

  if (isCorrect) {
    playCorrectTone();
    sheetTitle.textContent = 'Correct Answer';
    sheetTitle.className = 'sheet-title correct-title';

    iconBadge.className = 'sheet-icon-badge correct-badge';
    sheetIcon.textContent = '✔';

    const cheers = [
      'Wow! That is absolutely correct.',
      'Luar biasa! Analisis kamu sangat tepat.',
      'Mantap! Jawaban sesuai kunci soal Paragon.',
      'Hebat! Kamu memahami konsepnya dengan baik.'
    ];
    sheetCheer.textContent = cheers[Math.floor(Math.random() * cheers.length)];
  } else {
    playWrongTone();
    sheetTitle.textContent = 'Incorrect Answer';
    sheetTitle.className = 'sheet-title incorrect-title';

    iconBadge.className = 'sheet-icon-badge incorrect-badge';
    sheetIcon.textContent = '✖';

    sheetCheer.textContent = `Jawaban yang benar adalah pilihan (${correctChoice}).`;
  }

  // Set explanation
  explText.textContent = explanation || 'Tidak ada catatan pembahasan tambahan untuk soal ini.';

  // Next Button Label
  const isLast = (state.currentIndex >= state.quizQuestions.length - 1);
  nextBtn.textContent = isLast ? 'Selesaikan & Lihat Skor ➔' : 'Next';

  // Animate Slide Up
  backdrop.classList.add('active');
  sheet.classList.add('active');
}

function closeBottomSheet() {
  document.getElementById('bottom-sheet').classList.remove('active');
  document.getElementById('sheet-backdrop').classList.remove('active');
}

function handleNextQuestion() {
  closeBottomSheet();

  if (state.currentIndex < state.quizQuestions.length - 1) {
    state.currentIndex++;
    displayCurrentQuestion();
  } else {
    // Quiz finished!
    finishQuizSession();
  }
}

// ==========================================================================
// 7. QUIZ FINISH & RESULT CALCULATION
// ==========================================================================
async function finishQuizSession() {
  const total = state.userAnswers.length;
  const correctCount = state.userAnswers.filter(a => a.is_correct).length;
  const accuracy = Math.round((correctCount / total) * 100);
  const timeSpent = Math.round((Date.now() - state.quizStartTime) / 1000);

  let evaluation = "";
  let badge = "";
  if (accuracy >= 90) {
    evaluation = "🌟 Istimewa! Kemampuan Anda sangat kompetitif untuk lolos Paragon Scholarship & MT.";
    badge = "Exceptional Paragon Scholar";
  } else if (accuracy >= 75) {
    evaluation = "👍 Sangat Baik! Anda telah menguasai sebagian besar pola soal psikotes Paragon.";
    badge = "Strong Candidate";
  } else if (accuracy >= 55) {
    evaluation = "📈 Cukup Baik. Tingkatkan kecepatan dan ketelitian dengan latihan segmen berkala.";
    badge = "On Track";
  } else {
    evaluation = "💪 Perlu Latihan Tambahan. Pelajari pembahasan setiap butir soal untuk memahami polanya.";
    badge = "Keep Practicing";
  }

  const resultData = {
    score: correctCount,
    total: total,
    accuracy: accuracy,
    time_spent_sec: timeSpent,
    evaluation: evaluation,
    badge: badge
  };

  // Save to localStorage for instant offline & Vercel persistence
  const segObj = state.segments.find(s => s.id === state.selectedSegmentId);
  const histItem = {
    segment_id: state.selectedSegmentId || 'mixed',
    segment_name: segObj ? segObj.name : 'Simulasi Paragon',
    segment_icon: segObj ? segObj.icon : '📝',
    score: correctCount,
    total: total,
    accuracy: accuracy,
    time_spent_sec: timeSpent,
    completed_at: new Date().toISOString()
  };
  try {
    const localHist = JSON.parse(localStorage.getItem('paragon_quiz_history') || '[]');
    localHist.unshift(histItem);
    localStorage.setItem('paragon_quiz_history', JSON.stringify(localHist.slice(0, 50)));
  } catch (e) {}

  // Also try backend if alive
  try {
    const res = await fetch('/api/quiz/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        segment_id: state.selectedSegmentId || 'mixed',
        score: correctCount,
        total: total,
        accuracy: accuracy,
        time_spent_sec: timeSpent,
        details: state.userAnswers
      })
    });
    if (res.ok) {
      const apiResult = await res.json();
      displayResultScreen(apiResult, correctCount, total, accuracy, timeSpent);
      return;
    }
  } catch (err) {
    console.warn('Backend submit unavailable, using local result calculation');
  }

  displayResultScreen(resultData, correctCount, total, accuracy, timeSpent);
}

function displayResultScreen(apiResult, correct, total, accuracy, timeSpentSec) {
  switchView('result');

  // Format time
  const min = Math.floor(timeSpentSec / 60);
  const sec = timeSpentSec % 60;
  const timeFormatted = `${min < 10 ? '0' : ''}${min}:${sec < 10 ? '0' : ''}${sec}`;

  document.getElementById('result-score-num').textContent = correct;
  document.getElementById('result-total-denom').textContent = `/${total}`;
  document.getElementById('result-accuracy-label').textContent = `Akurasi: ${accuracy}%`;

  document.getElementById('res-correct-count').textContent = correct;
  document.getElementById('res-wrong-count').textContent = total - correct;
  document.getElementById('res-time-spent').textContent = timeFormatted;

  const titleEl = document.getElementById('result-title');
  const evalEl = document.getElementById('result-evaluation');
  const iconEl = document.getElementById('result-icon');

  if (accuracy >= 80) {
    iconEl.textContent = '🏆';
    titleEl.textContent = 'Luar Biasa!';
    evalEl.textContent = apiResult.evaluation || 'Skor Anda sangat kompetitif untuk lolos tahapan Paragon Scholarship.';
  } else if (accuracy >= 60) {
    iconEl.textContent = '🎯';
    titleEl.textContent = 'Bagus Sekali!';
    evalEl.textContent = apiResult.evaluation || 'Pemahaman Anda sudah baik. Perkuat lagi subtopik yang masih salah.';
  } else {
    iconEl.textContent = '💪';
    titleEl.textContent = 'Terus Berlatih!';
    evalEl.textContent = apiResult.evaluation || 'Pelajari kembali pembahasan di bawah untuk memahami polanya.';
  }

  // Populate Review items
  renderReviewSection();

  // Refresh stats
  loadUserStats();
}

function renderReviewSection() {
  const container = document.getElementById('review-items-container');
  container.innerHTML = '';

  state.userAnswers.forEach((item, idx) => {
    const card = document.createElement('div');
    card.className = 'review-item-card';

    const statusBadge = item.is_correct
      ? `<span style="color:#16A34A;">✔ Benar</span>`
      : `<span style="color:#DC2626;">✖ Salah</span>`;

    card.innerHTML = `
      <div class="review-item-header">
        <span>Soal #${idx + 1}</span>
        ${statusBadge}
      </div>
      <div class="review-q-text">${item.question}</div>
      <div class="review-ans-diff ${item.is_correct ? 'correct-diff' : 'wrong-diff'}">
        Jawaban kamu: <strong>${item.selected || 'Tidak Dijawab'}</strong> | Kunci Benar: <strong>${item.correct_answer}</strong>
      </div>
      <div class="review-expl-text">
        <strong>Pembahasan:</strong> ${item.explanation}
      </div>
    `;
    container.appendChild(card);
  });
}

// ==========================================================================
// 8. BANK SOAL & SEARCH ENGINE
// ==========================================================================
let bankSearchDebounce = null;

async function loadBankQuestions(query = '', segment = 'all') {
  const container = document.getElementById('bank-list-container');
  container.innerHTML = '<div class="spinner"></div>';

  try {
    let questions = [];

    try {
      let url = `/api/questions?limit=60`;
      if (query) url += `&q=${encodeURIComponent(query)}`;
      if (segment && segment !== 'all') url += `&segment=${segment}`;

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        questions = data.questions || [];
      }
    } catch (e) {
      console.warn('API questions endpoint unavailable, using static fallback');
    }

    // Static fallback search
    if (!questions || questions.length === 0) {
      const db = await getStaticQuizData();
      if (db && db.questions) {
        let pool = db.questions;
        if (segment && segment !== 'all') {
          pool = pool.filter(q => q.segment_id === segment);
        }
        if (query) {
          const qLower = query.toLowerCase();
          pool = pool.filter(q => 
            (q.question && q.question.toLowerCase().includes(qLower)) ||
            (q.explanation && q.explanation.toLowerCase().includes(qLower)) ||
            (q.subsegment && q.subsegment.toLowerCase().includes(qLower))
          );
        }
        questions = pool.slice(0, 60);
      }
    }

    document.getElementById('bank-results-count').textContent = `Ditemukan ${questions.length} butir soal`;

    if (!questions || questions.length === 0) {
      container.innerHTML = '<p style="text-align:center; color:#64748B; padding:30px;">Tidak ditemukan soal yang cocok.</p>';
      return;
    }

    container.innerHTML = '';
    questions.forEach((q, idx) => {
      const card = document.createElement('div');
      card.className = 'bank-item-card';

      const optionsHtml = q.options.map(o => `
        <div class="bank-opt-line ${o.key === q.correct_answer ? 'is-correct-opt' : ''}">
          <strong>${o.key}.</strong> ${o.text} ${o.key === q.correct_answer ? ' (Kunci Benar ✔)' : ''}
        </div>
      `).join('');

      card.innerHTML = `
        <div class="bank-item-top">
          <span class="bank-item-badge">${q.segment_id.toUpperCase()}</span>
          <span class="bank-item-sub">• ${q.subsegment || 'Umum'}</span>
        </div>
        <div class="bank-item-q">${idx + 1}. ${q.question}</div>
        <div class="bank-item-opts">${optionsHtml}</div>
        <div class="bank-item-expl">
          <strong>💡 Pembahasan:</strong> ${q.explanation}
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error('Error loading bank questions:', err);
    container.innerHTML = '<p style="color:red; text-align:center;">Gagal memuat bank soal.</p>';
  }
}

// ==========================================================================
// 9. EVENT LISTENERS & INITIALIZATION
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  // Check Password Gate Auth on load
  checkGateAuth();

  // Password gate controls
  const lockBtn = document.getElementById('btn-lock-app');
  if (lockBtn) lockBtn.onclick = lockApp;

  const togglePwdBtn = document.getElementById('gate-toggle-pwd');
  if (togglePwdBtn) togglePwdBtn.onclick = togglePasswordVisibility;

  // Brand logo click -> go to dashboard
  document.getElementById('btn-brand-home').onclick = () => switchView('dashboard');

  // Nav Actions
  document.getElementById('btn-open-bank').onclick = () => {
    switchView('bank');
    loadBankQuestions();
  };

  document.getElementById('btn-open-add-q').onclick = () => {
    document.getElementById('modal-add-question').classList.add('active');
  };

  document.getElementById('btn-close-add-modal').onclick = () => {
    document.getElementById('modal-add-question').classList.remove('active');
  };

  // Sound toggle
  const soundBtn = document.getElementById('btn-toggle-sound');
  soundBtn.onclick = () => {
    state.soundEnabled = !state.soundEnabled;
    document.getElementById('sound-icon').textContent = state.soundEnabled ? '🔊' : '🔇';
    showToast(state.soundEnabled ? 'Suara diaktifkan.' : 'Suara dimatikan.');
  };

  // Quick Mix
  document.getElementById('btn-quick-mix').onclick = () => {
    startQuiz('all', '', 10, 30);
  };

  // Quiz Top Bar Close
  document.getElementById('btn-quiz-close').onclick = () => {
    if (confirm('Yakin ingin mengakhiri sesi kuis ini?')) {
      clearInterval(state.timerId);
      switchView('dashboard');
    }
  };

  // Quiz Top Bar Share
  document.getElementById('btn-quiz-share').onclick = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href);
      showToast('Tautan kuis berhasil disalin!');
    } else {
      showToast('Kuis Paragon Scholarship 2026');
    }
  };

  // Quiz Top Bar More Menu
  document.getElementById('btn-quiz-more').onclick = () => {
    const isMuted = !state.soundEnabled;
    state.soundEnabled = isMuted;
    document.getElementById('sound-icon').textContent = state.soundEnabled ? '🔊' : '🔇';
    showToast(`Audio efek sekarang: ${state.soundEnabled ? 'ON' : 'OFF'}`);
  };

  // Speaker audio
  document.getElementById('btn-speak-question').onclick = speakCurrentQuestion;

  // Check Answer Button
  document.getElementById('btn-check-answer').onclick = handleCheckAnswer;

  // Sheet Next Button
  document.getElementById('btn-sheet-next').onclick = handleNextQuestion;

  // Result Screen Actions
  document.getElementById('btn-retry-segment').onclick = () => {
    startQuiz(state.selectedSegmentId, state.selectedSubsegment, state.selectedLimit, state.selectedTimerSec);
  };

  document.getElementById('btn-back-dashboard').onclick = () => {
    switchView('dashboard');
  };

  document.getElementById('btn-toggle-review').onclick = () => {
    const rev = document.getElementById('review-section');
    const isHidden = (rev.style.display === 'none');
    rev.style.display = isHidden ? 'block' : 'none';
    document.getElementById('btn-toggle-review').textContent = isHidden
      ? 'Sembunyikan Review ▲'
      : 'Review Semua Jawaban & Pembahasan ▼';
  };

  // Bank Soal Back
  document.getElementById('btn-bank-back').onclick = () => switchView('dashboard');

  // Bank Soal Live Search
  const searchInput = document.getElementById('bank-search-input');
  const segmentSelect = document.getElementById('bank-segment-select');

  searchInput.oninput = () => {
    clearTimeout(bankSearchDebounce);
    bankSearchDebounce = setTimeout(() => {
      loadBankQuestions(searchInput.value.trim(), segmentSelect.value);
    }, 300);
  };

  segmentSelect.onchange = () => {
    loadBankQuestions(searchInput.value.trim(), segmentSelect.value);
  };

  // Segment Config Modal Setup
  document.getElementById('btn-close-config-modal').onclick = closeSegmentConfigModal;

  // Config Limit Pills
  document.querySelectorAll('#config-limit-pills .pill-btn').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('#config-limit-pills .pill-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.selectedLimit = parseInt(btn.dataset.val);
    };
  });

  // Config Timer Pills
  document.querySelectorAll('#config-timer-pills .pill-btn').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('#config-timer-pills .pill-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.selectedTimerSec = parseInt(btn.dataset.val);
    };
  });

  // Start configured quiz
  document.getElementById('btn-start-configured-quiz').onclick = () => {
    const sub = document.getElementById('config-subsegment').value;
    state.selectedSubsegment = sub;
    startQuiz(state.selectedSegmentId, sub, state.selectedLimit, state.selectedTimerSec);
  };

  // Add Question Form (CRUD)
  document.getElementById('form-add-question').onsubmit = async (e) => {
    e.preventDefault();
    const seg = document.getElementById('new-q-segment').value;
    const sub = document.getElementById('new-q-subsegment').value.trim();
    const qText = document.getElementById('new-q-question').value.trim();
    const correct = document.getElementById('new-q-correct').value;
    const source = document.getElementById('new-q-source').value.trim();
    const expl = document.getElementById('new-q-explanation').value.trim();

    const options = [
      { key: 'A', text: document.getElementById('opt-text-A').value.trim() },
      { key: 'B', text: document.getElementById('opt-text-B').value.trim() }
    ];
    const optC = document.getElementById('opt-text-C').value.trim();
    const optD = document.getElementById('opt-text-D').value.trim();
    const optE = document.getElementById('opt-text-E').value.trim();

    if (optC) options.push({ key: 'C', text: optC });
    if (optD) options.push({ key: 'D', text: optD });
    if (optE) options.push({ key: 'E', text: optE });

    try {
      const res = await fetch('/api/questions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          segment_id: seg,
          subsegment: sub,
          question: qText,
          options: options,
          correct_answer: correct,
          explanation: expl,
          source: source
        })
      });
      const data = await res.json();
      if (data.success) {
        showToast('Soal berhasil ditambahkan ke database!');
        document.getElementById('modal-add-question').classList.remove('active');
        document.getElementById('form-add-question').reset();
        loadSegmentsAndStats();
      }
    } catch (err) {
      console.error('Error adding question:', err);
      showToast('Gagal menambahkan soal.');
    }
  };

  // Initial Load
  loadSegmentsAndStats();
});
