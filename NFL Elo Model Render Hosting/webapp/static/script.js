async function predict() {
  const home = document.getElementById('home').value;
  const away = document.getElementById('away').value;
  const resultEl = document.getElementById('result');
  resultEl.textContent = 'Predicting...';
  try {
    const res = await fetch('/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ home, away })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Prediction failed');
    }
    const data = await res.json();
    const pct = (data.home_win_prob * 100).toFixed(1);
    const spread = (data.spread).toFixed(2);
    resultEl.textContent = `${data.home} win prob: ${pct}% | Spread: ${spread}`;
  } catch (e) {
    resultEl.textContent = `Error: ${e.message}`;
  }
}

async function retune(mode) {
  const statusEl = document.getElementById('retuneStatus');
  statusEl.textContent = `Starting ${mode} retune...`;
  try {
    const res = await fetch(`/retune?mode=${mode}`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to start retune');
    statusEl.textContent = `${mode} retune started. This may take a while. You can continue predicting.`;
  } catch (e) {
    statusEl.textContent = `Error: ${e.message}`;
  }
}

document.getElementById('predictBtn').addEventListener('click', predict);
document.getElementById('quickRetune').addEventListener('click', () => retune('quick'));
document.getElementById('fullRetune').addEventListener('click', () => retune('full'));


