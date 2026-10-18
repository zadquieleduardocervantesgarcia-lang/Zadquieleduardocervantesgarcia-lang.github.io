const clamp = (v, min = 0, max = 1) => Math.min(max, Math.max(min, v));

// ===== Intro: letras que aparecen una por una =====
document.querySelectorAll('[data-letters]').forEach(el => {
  const words = el.textContent.trim().split(/\s+/);
  el.textContent = '';
  let i = 0;
  words.forEach((word, wi) => {
    // cada palabra va junta para que no se corte a la mitad
    const wordSpan = document.createElement('span');
    wordSpan.className = 'word';
    [...word].forEach(ch => {
      const span = document.createElement('span');
      span.className = 'ch';
      span.textContent = ch;
      span.style.animationDelay = `${0.5 + i++ * 0.07}s`;
      wordSpan.appendChild(span);
    });
    el.appendChild(wordSpan);
    if (wi < words.length - 1) el.appendChild(document.createTextNode(' '));
  });
});

// ===== Separar textos en palabras =====
function splitWords(el) {
  const words = el.textContent.trim().split(/\s+/);
  el.innerHTML = words.map(w => `<span class="w">${w}</span>`).join(' ');
  return [...el.querySelectorAll('.w')];
}

// "Todo empezó el 17 de abril de 2024": se ilumina palabra por palabra
const startWords = splitWords(document.querySelector('[data-words]'));
startWords.forEach((w, i) => { if (i >= 3) w.classList.add('is-date'); });

// Carta: las palabras aparecen en cascada
document.querySelectorAll('[data-reveal-words]').forEach(p => {
  splitWords(p).forEach((w, i) => { w.style.transitionDelay = `${i * 0.035}s`; });
});

// ===== Animaciones ligadas al scroll =====
const scrollies = [...document.querySelectorAll('[data-scrolly]')];
const polaroids = [...document.querySelectorAll('.polaroid')];
let ticking = false;

function update() {
  const vh = window.innerHeight;

  scrollies.forEach(sec => {
    const rect = sec.getBoundingClientRect();
    if (rect.bottom < -vh || rect.top > vh * 2) return;
    const p = clamp(-rect.top / (rect.height - vh));
    sec.style.setProperty('--p', p);

    sec.querySelectorAll('.moment__img').forEach(img => img.style.setProperty('--p', p));

    if (sec.classList.contains('start')) {
      const n = startWords.length;
      startWords.forEach((w, i) => {
        w.style.opacity = clamp(p * 1.4 * n - i, 0.12, 1);
      });
    }

    if (sec.classList.contains('collage')) {
      polaroids.forEach((card, i) => {
        const t = clamp((p - i * 0.18) / 0.4);
        const eased = 1 - Math.pow(1 - t, 3);
        card.style.setProperty('--t', eased);
      });
    }
  });

  const max = document.documentElement.scrollHeight - vh;
  document.documentElement.style.setProperty('--page', clamp(window.scrollY / max));
  ticking = false;
}

window.addEventListener('scroll', () => {
  if (!ticking) { requestAnimationFrame(update); ticking = true; }
}, { passive: true });
window.addEventListener('resize', update);
update();

// ===== Aparecer al entrar en pantalla =====
const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('is-visible');
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.2 });
document.querySelectorAll('.reveal, [data-reveal-words]').forEach(el => observer.observe(el));

// ===== Corazones flotando =====
const heartsBox = document.querySelector('.hearts');
const heartChars = ['❤', '♥', '❥'];

function spawnHeart() {
  const h = document.createElement('span');
  h.className = 'heart';
  h.textContent = heartChars[Math.floor(Math.random() * heartChars.length)];
  const duration = 9 + Math.random() * 8;
  h.style.left = `${Math.random() * 100}vw`;
  h.style.fontSize = `${10 + Math.random() * 18}px`;
  h.style.animationDuration = `${duration}s`;
  h.style.setProperty('--o', (0.15 + Math.random() * 0.35).toFixed(2));
  h.style.setProperty('--drift', `${(Math.random() - 0.5) * 120}px`);
  h.style.setProperty('--spin', `${(Math.random() - 0.5) * 120}deg`);
  heartsBox.appendChild(h);
  setTimeout(() => h.remove(), duration * 1000);
}
if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  setInterval(spawnHeart, 900);
}

// ===== Contador desde el 17 de abril de 2024, 8:00 pm =====
const START = new Date(2024, 3, 17, 20, 0, 0); // los meses empiezan en 0: 3 = abril
const els = {
  years: document.getElementById('c-years'),
  days: document.getElementById('c-days'),
  hours: document.getElementById('c-hours'),
  minutes: document.getElementById('c-minutes'),
  seconds: document.getElementById('c-seconds'),
};
const pad = n => String(n).padStart(2, '0');

function setValue(el, value) {
  if (el.textContent === value) return;
  el.textContent = value;
  el.classList.remove('tick');
  void el.offsetWidth; // reinicia la animación
  el.classList.add('tick');
}

function updateCounter() {
  const now = new Date();

  // años completos (cada aniversario el 17 de abril a las 8 pm)
  let years = now.getFullYear() - START.getFullYear();
  const anniversary = new Date(START);
  anniversary.setFullYear(START.getFullYear() + years);
  if (anniversary > now) {
    years--;
    anniversary.setFullYear(START.getFullYear() + years);
  }

  let diff = Math.floor((now - anniversary) / 1000);
  const days = Math.floor(diff / 86400); diff %= 86400;
  const hours = Math.floor(diff / 3600); diff %= 3600;
  const minutes = Math.floor(diff / 60);
  const seconds = diff % 60;

  setValue(els.years, String(years));
  setValue(els.days, String(days));
  setValue(els.hours, pad(hours));
  setValue(els.minutes, pad(minutes));
  setValue(els.seconds, pad(seconds));
}
updateCounter();
setInterval(updateCounter, 1000);

// ===== Reproductor con vinilo =====
const audio = document.getElementById('audio');
const playBtn = document.getElementById('play');
const vinyl = document.getElementById('vinyl');
const tonearm = document.getElementById('tonearm');
const fill = document.getElementById('fill');
const bar = document.querySelector('.player__bar');
const tCurrent = document.getElementById('t-current');
const tTotal = document.getElementById('t-total');

const fmt = s => `${Math.floor(s / 60)}:${pad(Math.floor(s % 60))}`;

const mini = document.getElementById('mini');

function setPlaying(on) {
  playBtn.classList.toggle('is-playing', on);
  vinyl.classList.toggle('is-playing', on);
  tonearm.classList.toggle('is-on', on);
  mini.classList.toggle('is-playing', on);
  playBtn.setAttribute('aria-label', on ? 'Pausar' : 'Reproducir');
  mini.setAttribute('aria-label', on ? 'Pausar canción' : 'Reproducir canción');
}

playBtn.addEventListener('click', () => {
  if (audio.paused) {
    const fromStart = audio.currentTime < 1;
    tonearm.classList.add('is-on');
    // pequeña pausa para que el brazo llegue al disco antes de sonar
    setTimeout(() => {
      audio.play()
        .then(() => { if (fromStart) startAutoScroll(); })
        .catch(() => setPlaying(false));
    }, 500);
  } else {
    audio.pause();
  }
});

// Botón flotante para pausar/reanudar mientras se recorre la página
mini.addEventListener('click', () => {
  if (audio.paused) audio.play(); else audio.pause();
});

audio.addEventListener('play', () => { setPlaying(true); mini.classList.add('is-visible'); });
audio.addEventListener('pause', () => { setPlaying(false); stopAutoScroll(); });
audio.addEventListener('ended', () => { setPlaying(false); audio.currentTime = 0; mini.classList.remove('is-visible'); });

// ===== Recorrido automático con la canción =====
// Al iniciar la canción, sube al principio y baja solita al ritmo de la música
// hasta llegar de nuevo al vinilo justo antes de que termine.
let autoId = null;
let autoPos = 0;
let autoLast = 0;
let autoSpeed = 0;

// Segundos que tarda en recorrer toda la página (menos = más rápido)
const AUTO_SCROLL_SECONDS = 75;

function startAutoScroll() {
  stopAutoScroll();
  window.scrollTo({ top: 0, behavior: 'instant' });
  autoPos = 0;
  // espera a que se vea la portada antes de empezar a bajar
  setTimeout(() => {
    if (audio.paused) return;
    const end = document.documentElement.scrollHeight - window.innerHeight;
    autoSpeed = end / AUTO_SCROLL_SECONDS; // píxeles por segundo
    autoLast = performance.now();
    autoId = requestAnimationFrame(autoStep);
  }, 2500);
}

function autoStep(now) {
  const dt = (now - autoLast) / 1000;
  autoLast = now;
  const end = document.documentElement.scrollHeight - window.innerHeight;
  autoPos = Math.min(autoPos + autoSpeed * dt, end);
  window.scrollTo({ top: autoPos, behavior: 'instant' });
  if (autoPos >= end) { autoId = null; return; }
  autoId = requestAnimationFrame(autoStep);
}

function stopAutoScroll() {
  if (autoId) cancelAnimationFrame(autoId);
  autoId = null;
}

// si ella toca la pantalla o usa la rueda, el recorrido se detiene (la música sigue)
['wheel', 'touchstart', 'keydown', 'mousedown'].forEach(evt =>
  window.addEventListener(evt, e => {
    if (e.target.closest && e.target.closest('#mini, #play')) return;
    stopAutoScroll();
  }, { passive: true })
);
audio.addEventListener('loadedmetadata', () => { tTotal.textContent = fmt(audio.duration); });
audio.addEventListener('timeupdate', () => {
  if (!audio.duration) return;
  fill.style.width = `${(audio.currentTime / audio.duration) * 100}%`;
  tCurrent.textContent = fmt(audio.currentTime);
});

bar.addEventListener('click', e => {
  if (!audio.duration) return;
  const rect = bar.getBoundingClientRect();
  audio.currentTime = ((e.clientX - rect.left) / rect.width) * audio.duration;
});
