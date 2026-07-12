/**
 * NCE1 单词练习 v2.0 - 前端逻辑
 * PPT全屏风格 + 用户系统 + 课时选择
 */

// ========== 全局状态 ==========
const state = {
    mode: 'en2cn',
    currentLesson: '',
    questions: [],
    currentIndex: 0,
    combo: 0,
    maxCombo: 0,
    score: 0,
    correctCount: 0,
    wrongCount: 0,
    totalScoreAdd: 0,
    isReviewing: false,
    lessonGridData: {}, // lesson -> { count, hasErr }
    currentView: 'home'
};

// ========== 音效 ==========
const AudioCtx = window.AudioContext || window.webkitAudioContext;
let audioCtx = null;

function playSound(type) {
    if (!audioCtx) { try { audioCtx = new AudioCtx(); } catch (e) { return; } }
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain); gain.connect(audioCtx.destination);
    if (type === 'correct') {
        osc.frequency.setValueAtTime(523, audioCtx.currentTime);
        osc.frequency.setValueAtTime(659, audioCtx.currentTime + 0.1);
        osc.frequency.setValueAtTime(784, audioCtx.currentTime + 0.2);
        gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.4);
        osc.start(); osc.stop(audioCtx.currentTime + 0.4);
    } else if (type === 'wrong') {
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(200, audioCtx.currentTime);
        osc.frequency.setValueAtTime(150, audioCtx.currentTime + 0.2);
        gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.4);
        osc.start(); osc.stop(audioCtx.currentTime + 0.4);
    } else if (type === 'combo') {
        osc.frequency.setValueAtTime(440, audioCtx.currentTime);
        osc.frequency.setValueAtTime(554, audioCtx.currentTime + 0.08);
        osc.frequency.setValueAtTime(659, audioCtx.currentTime + 0.16);
        osc.frequency.setValueAtTime(880, audioCtx.currentTime + 0.24);
        gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.5);
        osc.start(); osc.stop(audioCtx.currentTime + 0.5);
    }
}

// ========== Toast ==========
function showToast(msg, type = 'info') {
    const c = document.getElementById('toastContainer');
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => t.remove(), 2500);
}

// ========== 烟花效果 ==========
const fireworkColors = [
    '#ff6b6b', '#fbbf24', '#34d399', '#60a5fa', '#a78bfa',
    '#f472b6', '#fb923c', '#2dd4bf', '#818cf8', '#e879f9'
];

function launchFirework(container, x, y) {
    const color = fireworkColors[Math.floor(Math.random() * fireworkColors.length)];
    const particleCount = 20 + Math.floor(Math.random() * 15);
    const rect = container.getBoundingClientRect();

    // 上升阶段 - 小光点
    const riseEl = document.createElement('div');
    riseEl.style.cssText = `
        position:absolute; left:${x}px; bottom:0;
        width:4px; height:4px; border-radius:50%;
        background:${color}; pointer-events:none;
        box-shadow: 0 0 6px ${color};
        animation: fireworkRise 0.5s ease-out forwards;
    `;
    container.appendChild(riseEl);
    setTimeout(() => riseEl.remove(), 500);

    // 爆炸阶段
    setTimeout(() => {
        for (let i = 0; i < particleCount; i++) {
            const angle = (Math.PI * 2 * i) / particleCount + (Math.random() - 0.5) * 0.3;
            const dist = 30 + Math.random() * 60;
            const dx = Math.cos(angle) * dist;
            const dy = Math.sin(angle) * dist;
            const size = 3 + Math.random() * 4;
            const p = document.createElement('div');
            p.className = 'firework-particle';
            p.style.left = x + 'px';
            p.style.top = y + 'px';
            p.style.width = size + 'px';
            p.style.height = size + 'px';
            p.style.background = color;
            p.style.boxShadow = `0 0 ${size}px ${color}`;
            p.style.setProperty('--fw-dx', `translateX(${dx}px)`);
            p.style.setProperty('--fw-dy', `translateY(${dy}px)`);
            p.style.animationDuration = (0.6 + Math.random() * 0.5) + 's';
            container.appendChild(p);
            setTimeout(() => p.remove(), 1200);
        }
    }, 450);
}

// 烟花上升动画（动态添加）
if (!document.getElementById('fireworkRiseStyle')) {
    const style = document.createElement('style');
    style.id = 'fireworkRiseStyle';
    style.textContent = `
        @keyframes fireworkRise {
            0% { opacity: 1; transform: translateY(0); }
            100% { opacity: 0.3; transform: translateY(var(--rise-dist, -120px)); }
        }
    `;
    document.head.appendChild(style);
}

// ========== 多种反馈效果 ==========
const correctEffects = [
    { icon: '🎆', text: 'Yes!', hasFirework: true },
    { icon: '🎉', text: '正确!', hasFirework: true },
    { icon: '✨', text: '太棒了!', hasFirework: false },
    { icon: '👏', text: '厉害!', hasFirework: false },
    { icon: '🌟', text: 'Perfect!', hasFirework: true },
    { icon: '💪', text: '好样的!', hasFirework: false },
    { icon: '🎊', text: 'Nice!', hasFirework: true },
    { icon: '🏆', text: '优秀!', hasFirework: true },
];

const wrongEffects = [
    { icon: '😢', text: '别灰心!' },
    { icon: '😔', text: '再想想~' },
    { icon: '🤔', text: '不对哦~' },
    { icon: '💪', text: '加油!' },
    { icon: '😤', text: '别放弃!' },
    { icon: '🥺', text: '再试试!' },
];

// ========== 侧边反馈动画 ==========
function showSideFeedback(correct, scoreMsg) {
    // 随机选择一个效果
    const effects = correct ? correctEffects : wrongEffects;
    const effect = effects[Math.floor(Math.random() * effects.length)];

    // 随机选择左侧或右侧
    const sideIdx = Math.random() > 0.5 ? 'Left' : 'Right';
    const container = document.getElementById('quizSide' + sideIdx);
    if (!container) return;

    // 清除旧的反馈
    const oldFeedbacks = container.querySelectorAll('.side-feedback');
    oldFeedbacks.forEach(f => f.remove());

    // 创建反馈元素
    const fb = document.createElement('div');
    fb.className = 'side-feedback ' + (correct ? 'side-feedback-correct' : 'side-feedback-wrong');

    const iconEl = document.createElement('div');
    iconEl.className = 'side-feedback-icon';
    iconEl.textContent = effect.icon;

    const textEl = document.createElement('div');
    textEl.className = 'side-feedback-text';
    textEl.textContent = scoreMsg || effect.text;

    fb.appendChild(iconEl);
    fb.appendChild(textEl);

    // 随机垂直位置 (20%-70% 之间)
    const topPercent = 20 + Math.random() * 50;
    fb.style.top = topPercent + '%';

    // 水平居中在侧边栏
    if (sideIdx === 'Left') {
        fb.style.left = '50%';
        fb.style.transform = 'translateX(-50%)';
    } else {
        fb.style.right = '50%';
        fb.style.transform = 'translateX(50%)';
    }

    container.appendChild(fb);

    // 如果是正确答案且有烟花效果
    if (correct && effect.hasFirework) {
        const rect = container.getBoundingClientRect();
        const fxX = container.offsetWidth * (0.3 + Math.random() * 0.4);
        const fyY = container.offsetHeight * (0.2 + Math.random() * 0.3);
        launchFirework(container, fxX, fyY);
        // 有时放两个烟花
        if (Math.random() > 0.5) {
            setTimeout(() => {
                const fx2 = container.offsetWidth * (0.2 + Math.random() * 0.6);
                const fy2 = container.offsetHeight * (0.15 + Math.random() * 0.4);
                launchFirework(container, fx2, fy2);
            }, 300);
        }
    }

    // 错误时也放一个小烟花（冷色调）
    if (!correct) {
        const fxX = container.offsetWidth * (0.3 + Math.random() * 0.4);
        const fyY = container.offsetHeight * (0.3 + Math.random() * 0.3);
        // 简单的红色小爆炸
        for (let i = 0; i < 8; i++) {
            const angle = (Math.PI * 2 * i) / 8;
            const dist = 15 + Math.random() * 25;
            const dx = Math.cos(angle) * dist;
            const dy = Math.sin(angle) * dist;
            const p = document.createElement('div');
            p.className = 'firework-particle';
            p.style.left = fxX + 'px';
            p.style.top = fyY + 'px';
            p.style.width = '4px';
            p.style.height = '4px';
            p.style.background = '#f87171';
            p.style.boxShadow = '0 0 4px #f87171';
            p.style.setProperty('--fw-dx', `translateX(${dx}px)`);
            p.style.setProperty('--fw-dy', `translateY(${dy}px)`);
            container.appendChild(p);
            setTimeout(() => p.remove(), 1000);
        }
    }

    // 自动移除
    setTimeout(() => {
        fb.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        fb.style.opacity = '0';
        fb.style.transform = fb.style.transform.replace('translateX', 'translateX') + ' scale(0.5)';
        setTimeout(() => fb.remove(), 400);
    }, 1200);
}

// ========== 旧粒子函数（保留兼容但不再主动使用）==========
function spawnParticles(x, y, emoji, count = 6) {
    // 不再使用粒子效果，改用侧边反馈
}

// ========== 认证 ==========
async function doLogin() {
    const username = document.getElementById('loginUser').value.trim();
    const password = document.getElementById('loginPass').value.trim();
    if (!username || !password) { showToast('请输入用户名和密码', 'error'); return; }
    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById('authOverlay').style.display = 'none';
            document.getElementById('appContainer').style.display = '';
            document.getElementById('topNickname').textContent = data.user.nickname;
            initApp();
        } else {
            showToast(data.error || '登录失败', 'error');
        }
    } catch (e) { showToast('网络错误', 'error'); }
}

async function doRegister() {
    const username = document.getElementById('regUser').value.trim();
    const nickname = document.getElementById('regNick').value.trim() || username;
    const password = document.getElementById('regPass').value.trim();
    if (!username || !password) { showToast('请填写所有必填项', 'error'); return; }
    try {
        const res = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, nickname })
        });
        const data = await res.json();
        if (data.success) {
            showToast('注册成功！请登录', 'success');
            showLogin();
        } else {
            showToast(data.error || '注册失败', 'error');
        }
    } catch (e) { showToast('网络错误', 'error'); }
}

async function doLogout() {
    await fetch('/api/logout', { method: 'POST' });
    document.getElementById('authOverlay').style.display = '';
    document.getElementById('appContainer').style.display = 'none';
    document.getElementById('loginUser').value = '';
    document.getElementById('loginPass').value = '';
    sessionStorage.clear();
}

async function checkLogin() {
    try {
        const res = await fetch('/api/user');
        const data = await res.json();
        if (data.logged_in) {
            document.getElementById('authOverlay').style.display = 'none';
            document.getElementById('appContainer').style.display = '';
            document.getElementById('topNickname').textContent = data.user.nickname;
            initApp();
        }
    } catch (e) { /* 保持登录界面 */ }
}

function showRegister() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = '';
}
function showLogin() {
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('loginForm').style.display = '';
}

// 登录框回车键
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        const overlay = document.getElementById('authOverlay');
        if (overlay.style.display !== 'none') {
            const regVisible = document.getElementById('registerForm').style.display !== 'none';
            if (regVisible) doRegister(); else doLogin();
        }
    }
});

// ========== 视图切换 ==========
function switchView(viewName) {
    state.currentView = viewName;
    document.querySelectorAll('.view').forEach(v => { v.classList.remove('active'); v.style.display = 'none'; });
    const target = document.getElementById('view-' + viewName);
    if (target) { target.classList.add('active'); target.style.display = ''; }

    document.querySelectorAll('.bottombar .nav-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector(`.nav-btn[data-view="${viewName}"]`);
    if (btn) btn.classList.add('active');

    const titles = { home: '选择练习', quiz: '答题中', result: '练习完成', stats: '学习统计', errorbook: '错题本' };
    document.getElementById('pageTitle').textContent = titles[viewName] || '';

    if (viewName === 'stats') loadStats();
    if (viewName === 'errorbook') loadErrorBook();
}

function goHome() {
    switchView('home');
    loadLessonGrid();
    updateTopBar();
}

// ========== 初始化 ==========
async function initApp() {
    await loadLessonGrid();
    await updateTopBar();
    updateErrorDot();
    switchView('home');
}

// ========== 课程网格 ==========
async function loadLessonGrid() {
    try {
        const [lRes, eRes] = await Promise.all([
            fetch('/api/lessons'),
            fetch('/api/error_words')
        ]);
        const lessons = await lRes.json();
        const errors = await eRes.json();

        // 构建错题课程集合
        const errLessons = new Set();
        if (errors.data) {
            errors.data.forEach(w => { if (w.lesson) errLessons.add(w.lesson); });
        }

        const grid = document.getElementById('lessonGrid');
        if (!lessons.data || lessons.data.length === 0) {
            grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text-light)">暂无课程数据</div>';
            return;
        }

        state.lessonGridData = {};
        grid.innerHTML = lessons.data.map(l => {
            state.lessonGridData[l.lesson] = { count: l.cnt, hasErr: errLessons.has(l.lesson) };
            const errClass = errLessons.has(l.lesson) ? ' has-err' : '';
            return `<button class="lesson-btn${errClass}" onclick="startQuiz(${l.lesson})" title="Lesson ${l.lesson}: ${l.cnt}个单词${errLessons.has(l.lesson) ? ' (有错题)' : ''}">${l.lesson}</button>`;
        }).join('');
    } catch (e) { showToast('加载课程失败', 'error'); }
}

// ========== 模式选择 ==========
function selectModeBtn(btn) {
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.mode = btn.dataset.mode;
}

// ========== 开始练习 ==========
async function startQuiz(lesson) {
    state.currentLesson = lesson;
    state.isReviewing = false;

    switchView('quiz');

    // 重置
    state.questions = [];
    state.currentIndex = 0;
    state.combo = 0;
    state.maxCombo = 0;
    state.score = 0;
    state.correctCount = 0;
    state.wrongCount = 0;
    state.totalScoreAdd = 0;

    document.getElementById('quizSideLeft').innerHTML = '';
    document.getElementById('quizSideRight').innerHTML = '';

    try {
        const res = await fetch('/api/words/quiz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: state.mode, lesson: lesson })
        });
        const data = await res.json();
        if (data.error) { showToast(data.error, 'error'); goHome(); return; }
        if (!data.data || data.data.length === 0) {
            showToast('该课程没有单词', 'error');
            goHome();
            return;
        }
        state.questions = data.data;
        showQuestion();
    } catch (e) { showToast('加载题目失败', 'error'); goHome(); }
}

async function reviewErrors() {
    try {
        const res = await fetch('/api/error_words');
        const data = await res.json();
        if (!data.data || data.data.length === 0) {
            showToast('没有错题可复习！', 'info');
            return;
        }
        state.isReviewing = true;
        state.currentLesson = '';
        switchView('quiz');

        state.questions = [];
        state.currentIndex = 0;
        state.combo = 0;
        state.maxCombo = 0;
        state.score = 0;
        state.correctCount = 0;
        state.wrongCount = 0;
        state.totalScoreAdd = 0;

        document.getElementById('quizSideLeft').innerHTML = '';
    document.getElementById('quizSideRight').innerHTML = '';

        // 错题做 en2cn 练习
        state.mode = 'en2cn';
        document.querySelector('.mode-btn[data-mode="en2cn"]')?.classList.add('active');

        // 用错题单词ID请求题目
        const errIds = data.data.map(w => w.id).join(',');
        const qRes = await fetch('/api/words/quiz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: 'en2cn', lesson: '' })
        });
        const qData = await qRes.json();
        // 只保留错题相关的
        if (qData.data) {
            const errIdSet = new Set(data.data.map(w => w.id));
            state.questions = qData.data.filter(q => errIdSet.has(q.word_id));
        }
        if (!state.questions.length) {
            showToast('无法生成错题练习', 'error');
            goHome();
            return;
        }
        showQuestion();
    } catch (e) { showToast('加载错题失败', 'error'); }
}

// ========== 显示题目 ==========
function showQuestion() {
    if (state.currentIndex >= state.questions.length) {
        showResults();
        return;
    }

    const q = state.questions[state.currentIndex];
    const total = state.questions.length;
    const idx = state.currentIndex;

    // 进度
    document.getElementById('progressFill').style.width = ((idx / total) * 100) + '%';
    document.getElementById('progressLabel').textContent = `${idx + 1}/${total}`;
    document.getElementById('quizCombo').textContent = `⚡${state.combo}`;
    document.getElementById('quizScore').textContent = state.score;

    document.getElementById('quizSideLeft').innerHTML = '';
    document.getElementById('quizSideRight').innerHTML = '';

    // 题目
    document.getElementById('questionMain').textContent = q.question;

    // 提示行
    let hint = '';
    if (state.mode === 'cloze') {
        hint = `释义: ${q.chinese}  ·  Lesson ${q.lesson || '—'}`;
    } else if (state.mode === 'en2cn') {
        hint = `音标: /${q.phonetic || '—'}/  ·  Lesson ${q.lesson || '—'}`;
    } else {
        hint = `Lesson ${q.lesson || '—'}`;
    }
    document.getElementById('questionSub').textContent = hint;

    // 选项
    const grid = document.getElementById('optionsGrid');
    grid.innerHTML = '';
    const isCloze = state.mode === 'cloze';
    q.options.forEach(opt => {
        const btn = document.createElement('button');
        btn.className = 'option-btn' + (isCloze ? ' option-cloze' : '');
        btn.textContent = opt;
        btn.addEventListener('click', (e) => handleAnswer(opt, q.answer, e, btn));
        grid.appendChild(btn);
    });

    // 内容静默更新，不闪动
}

// ========== 处理答案 ==========
async function handleAnswer(userAnswer, correctAnswer, event, btn) {
    const q = state.questions[state.currentIndex];
    const isCorrect = userAnswer === correctAnswer;

    if (isCorrect) {
        // 答对了 → 全部禁用，高亮正确答案
        document.querySelectorAll('.option-btn').forEach(b => b.disabled = true);
        document.querySelectorAll('.option-btn').forEach(b => {
            if (b.textContent === correctAnswer) b.classList.add('correct');
        });

        const wasFirstTry = !q._wrongTries;
        state.correctCount++;
        if (wasFirstTry) state.combo++;
        const comboBonus = Math.floor(state.combo / 3) * 5;
        const points = 10 + comboBonus;
        state.score += points;
        state.totalScoreAdd += points;
        if (state.combo > state.maxCombo) state.maxCombo = state.combo;
        playSound('correct');

        if (state.combo >= 3 && state.combo % 3 === 0) {
            playSound('combo');
            showToast(`🔥 ${state.combo} 连击！`, 'success');
        }

        let msg = `+${points}分`;
        if (!wasFirstTry) msg = `答对了! +${points}分`;
        showSideFeedback(true, msg);

        // 记录正确到后端（如果之前有过错误尝试也一并记录）
        try {
            await fetch('/api/log_answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ word_id: q.word_id, correct: true, mode: state.mode, user_answer: userAnswer })
            });
            if (state.combo > 0 && state.combo % 5 === 0) {
                await fetch('/api/combo_update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ combo: state.combo })
                });
            }
        } catch (e) { console.error('log_answer error:', e); }

        document.getElementById('quizCombo').textContent = `⚡${state.combo}`;
        document.getElementById('quizScore').textContent = state.score;

        // 自动跳到下一题
        setTimeout(() => {
            state.currentIndex++;
            showQuestion();
        }, 800);

    } else {
        // 答错了 → 仅禁用当前按钮，其余可继续选
        btn.classList.add('wrong');
        btn.disabled = true;
        q._wrongTries = (q._wrongTries || 0) + 1;
        state.combo = 0;
        state.wrongCount++;
        playSound('wrong');
        showSideFeedback(false, '');

        // 记录错误
        try {
            await fetch('/api/log_answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ word_id: q.word_id, correct: false, mode: state.mode, user_answer: userAnswer })
            });
        } catch (e) { console.error('log_answer error:', e); }

        document.getElementById('quizCombo').textContent = `⚡${state.combo}`;
        document.getElementById('quizScore').textContent = state.score;

        // 反馈已在侧边自动消失，无需额外处理
    }
}

// showFeedback 已替换为 showSideFeedback



// ========== 显示结果 ==========
async function showResults() {
    switchView('result');

    const total = state.questions.length;
    const rate = total > 0 ? Math.round(state.correctCount / total * 100) : 0;

    document.getElementById('resultCorrect').textContent = state.correctCount;
    document.getElementById('resultWrong').textContent = state.wrongCount;
    document.getElementById('resultRate').textContent = rate + '%';
    document.getElementById('resultCombo').textContent = state.maxCombo;

    // 等级
    const grade = document.getElementById('resultGrade');
    grade.className = 'result-grade';
    if (rate >= 95) { grade.textContent = '🏅 完美 S级！'; grade.classList.add('grade-S'); }
    else if (rate >= 80) { grade.textContent = '👏 优秀 A级'; grade.classList.add('grade-A'); }
    else if (rate >= 65) { grade.textContent = '💪 不错 B级'; grade.classList.add('grade-B'); }
    else { grade.textContent = '📚 继续加油 C级'; grade.classList.add('grade-C'); }

    // 撒花
    if (rate >= 50) startConfetti();

    // 保存连击
    if (state.maxCombo > 0) {
        fetch('/api/combo_update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ combo: state.maxCombo })
        }).catch(() => {});
    }

    await updateTopBar();
    await updateErrorDot();
    await loadLessonGrid(); // 刷新错题红点

    const msgs = ['继续加油！📚', '不错哦！💪', '很棒！🌟', '太厉害了！🔥', '单词之王！👑'];
    const mi = Math.min(Math.floor(rate / 20), msgs.length - 1);
    showToast(msgs[mi], rate >= 60 ? 'success' : 'info');
}

// ========== 撒花 ==========
function startConfetti() {
    const canvas = document.getElementById('confettiCanvas');
    if (!canvas) return;
    const parent = canvas.parentElement;
    canvas.width = parent.offsetWidth;
    canvas.height = parent.offsetHeight;
    const ctx = canvas.getContext('2d');
    const colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4'];
    const particles = [];
    for (let i = 0; i < 50; i++) {
        particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height * 0.4,
            vx: (Math.random() - 0.5) * 4,
            vy: Math.random() * 3 + 1,
            size: Math.random() * 6 + 3,
            color: colors[Math.floor(Math.random() * colors.length)],
            rot: Math.random() * 360,
            rotSpeed: (Math.random() - 0.5) * 10
        });
    }
    let frame = 0;
    function anim() {
        if (frame > 120) { ctx.clearRect(0, 0, canvas.width, canvas.height); return; }
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach(p => {
            p.y += p.vy; p.x += p.vx; p.vy += 0.05; p.rot += p.rotSpeed;
            ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot * Math.PI / 180);
            ctx.fillStyle = p.color; ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
            ctx.restore();
        });
        frame++;
        requestAnimationFrame(anim);
    }
    anim();
}

function retryLesson() {
    startQuiz(state.currentLesson);
}

// ========== 更新顶部栏 ==========
async function updateTopBar() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        if (data.progress) {
            document.getElementById('topScore').textContent = data.progress.score || 0;
            document.getElementById('topStreak').textContent = data.progress.study_streak || 0;
        }
    } catch (e) { /* quiet */ }
}

async function updateErrorDot() {
    try {
        const res = await fetch('/api/error_words');
        const data = await res.json();
        const count = data.data ? data.data.length : 0;
        const dot = document.getElementById('errDot');
        if (dot) {
            dot.style.display = count > 0 ? '' : 'none';
            dot.textContent = count > 0 ? count : '';
        }
    } catch (e) { /* quiet */ }
}

// ========== 统计 ==========
async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        const p = data.progress || {};
        document.getElementById('statTotal').textContent = p.total_practice_count || 0;
        document.getElementById('statScore').textContent = p.score || 0;
        document.getElementById('statStreak').textContent = p.study_streak || 0;
        document.getElementById('statCombo').textContent = p.max_combo || 0;

        // 模式统计
        const mg = document.getElementById('modeStatsGrid');
        if (data.mode_stats && data.mode_stats.length) {
            const mn = { 'en2cn': '英译汉', 'cn2en': '汉译英', 'cloze': '单词补全' };
            mg.innerHTML = data.mode_stats.map(m => {
                const rate = m.total_q > 0 ? Math.round(m.total_c / m.total_q * 100) : 0;
                const hue = rate >= 80 ? 160 : rate >= 60 ? 200 : 0;
                return `<div class="mode-stat-card">
                    <div class="rate-circle" style="border-color:hsl(${hue},60%,50%);color:hsl(${hue},60%,45%)">${rate}%</div>
                    <div style="font-weight:600;font-size:14px">${mn[m.mode]||m.mode}</div>
                    <div style="font-size:12px;color:var(--text-light)">${m.total_q}题 | 对${m.total_c}</div>
                </div>`;
            }).join('');
        } else {
            mg.innerHTML = '<div style="text-align:center;padding:10px;color:var(--text-light)">暂无数据</div>';
        }

        // 最近
        const rl = document.getElementById('recentList');
        if (data.recent && data.recent.length) {
            const mn = { 'en2cn': '英译汉', 'cn2en': '汉译英', 'cloze': '单词补全' };
            rl.innerHTML = data.recent.slice(0, 15).map(r => {
                const rate = r.total_questions > 0 ? Math.round(r.correct_count / r.total_questions * 100) : 0;
                return `<div class="recent-item">
                    <span class="recent-mode">${mn[r.mode]||r.mode}</span>
                    <span class="recent-score">✅${r.correct_count} ❌${r.wrong_count} (${rate}%)</span>
                    <span class="recent-date">${r.created_at||''}</span>
                </div>`;
            }).join('');
        } else {
            rl.innerHTML = '<div style="text-align:center;padding:16px;color:var(--text-light)">暂无练习记录</div>';
        }
    } catch (e) { showToast('加载统计失败', 'error'); }
}

// ========== 错题本 ==========
let currentErrorMode = ''; // 当前选中的题型 Tab

const modeNames = { 'en2cn': '英译汉', 'cn2en': '汉译英', 'cloze': '单词补全' };
const modeIcons = { 'en2cn': '🇬🇧→🇨🇳', 'cn2en': '🇨🇳→🇬🇧', 'cloze': '🔤' };

let _errorBookRetry = 0;
async function loadErrorBook(retryCount = 0) {
    try {
        const url = currentErrorMode
            ? `/api/error_words?mode=${currentErrorMode}`
            : '/api/error_words';
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        // 更新 Tab 计数（从 mode_stats 获取）
        if (data.mode_stats) {
            let totalCount = 0;
            data.mode_stats.forEach(ms => {
                totalCount += ms.word_count;
                const el = document.getElementById('errCount' + ms.mode.charAt(0).toUpperCase() + ms.mode.slice(1));
                if (el) el.textContent = ms.word_count;
            });
            document.getElementById('errCountAll').textContent = totalCount;
            // 清空没有数据的 tab 计数
            ['en2cn', 'cn2en', 'cloze'].forEach(m => {
                const found = data.mode_stats.find(ms => ms.mode === m);
                const el = document.getElementById('errCount' + m.charAt(0).toUpperCase() + m.slice(1));
                if (el && !found) el.textContent = '0';
            });
        }

        const list = document.getElementById('errorList');
        const empty = document.getElementById('errorEmpty');
        if (!data.data || !data.data.length) {
            list.innerHTML = '';
            list.appendChild(empty);
            empty.style.display = '';
            return;
        }
        empty.style.display = 'none';

        const modeLabel = currentErrorMode || '';
        list.innerHTML = data.data.map(w => {
            const modeTag = w.error_type ? `<span class="error-mode-tag">${modeIcons[w.error_type] || ''} ${modeNames[w.error_type] || w.error_type}</span>` : '';
            return `
            <div class="error-item">
                <div class="error-word-info">
                    <span class="error-word">${w.word}</span>
                    <span class="error-chinese">${w.chinese}</span>
                    <span style="color:#64748b;font-size:12px">/${w.phonetic||'—'}/</span>
                    <span style="color:#64748b;font-size:11px">L${w.lesson||'—'}</span>
                    ${modeTag}
                    <span class="error-count-tag">${w.error_count}次</span>
                </div>
            </div>`;
        }).join('');
    } catch (e) {
        if (retryCount < 2) {
            await new Promise(r => setTimeout(r, 500));
            return loadErrorBook(retryCount + 1);
        }
        showToast('加载错题本失败', 'error');
    }
}

function switchErrorTab(btn, mode) {
    currentErrorMode = mode;
    document.querySelectorAll('.error-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    loadErrorBook();
}

async function reviewErrorsByMode() {
    const mode = currentErrorMode || 'en2cn';
    try {
        const res = await fetch('/api/error_words' + (currentErrorMode ? `?mode=${currentErrorMode}` : ''));
        const data = await res.json();
        if (!data.data || !data.data.length) {
            showToast('没有错题可复习！', 'info');
            return;
        }
        state.isReviewing = true;
        state.currentLesson = '';
        state.mode = mode;
        switchView('quiz');

        state.questions = [];
        state.currentIndex = 0;
        state.combo = 0;
        state.maxCombo = 0;
        state.score = 0;
        state.correctCount = 0;
        state.wrongCount = 0;
        state.totalScoreAdd = 0;

        document.getElementById('quizSideLeft').innerHTML = '';
        document.getElementById('quizSideRight').innerHTML = '';

        // 用错题单词ID请求对应模式的题目
        const errIds = data.data.map(w => w.id).join(',');
        const qRes = await fetch('/api/words/quiz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: mode, lesson: '' })
        });
        const qData = await qRes.json();
        if (qData.data) {
            const errIdSet = new Set(data.data.map(w => w.id));
            state.questions = qData.data.filter(q => errIdSet.has(q.word_id));
        }
        if (!state.questions.length) {
            showToast('无法生成错题练习', 'error');
            goHome();
            return;
        }
        showQuestion();
    } catch (e) { showToast('加载错题失败', 'error'); }
}

async function clearErrors() {
    const modeText = currentErrorMode ? `${modeNames[currentErrorMode]}的` : '';
    if (!confirm(`确定清空${modeText}错题？`)) return;
    await fetch('/api/error_words/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: currentErrorMode })
    });
    showToast(`${modeText}错题已清空`, 'info');
    loadErrorBook();
    updateErrorDot();
    loadLessonGrid();
}

async function resetProgress() {
    if (!confirm('确定重置所有学习进度？不可恢复！')) return;
    await fetch('/api/reset_progress', { method: 'POST' });
    showToast('进度已重置', 'info');
    updateTopBar();
    updateErrorDot();
    loadStats();
    loadLessonGrid();
}

// ========== 启动 ==========
document.addEventListener('DOMContentLoaded', () => {
    checkLogin();
});
