/**
 * SDR PSD Dashboard — real-time Plotly.js + SocketIO client.
 */
(function () {
  const socket = io();
  let connected = false;

  const $freq    = document.getElementById('ctrl-freq');
  const $gain    = document.getElementById('ctrl-gain');
  const $span    = document.getElementById('ctrl-span');
  const $nfft    = document.getElementById('ctrl-nfft');
  const $nps     = document.getElementById('ctrl-nperseg');
  const $novrlap = document.getElementById('ctrl-noverlap');
  const $start   = document.getElementById('btn-start');
  const $stop    = document.getElementById('btn-stop');
  const $apply   = document.getElementById('btn-apply');
  const $dot     = document.getElementById('status-dot');
  const $label   = document.getElementById('status-label');
  const $iFreq   = document.getElementById('info-freq');
  const $iGain   = document.getElementById('info-gain');
  const $iSpan   = document.getElementById('info-span');
  const $iBw     = document.getElementById('info-bw');
  const $iClip   = document.getElementById('info-clip');

  // ── Plotly chart ──────────────────────────────────────
  const layout = {
    paper_bgcolor: '#0d1117',
    plot_bgcolor: '#0d1117',
    font: { color: '#8b949e', size: 11 },
    xaxis: {
      title: { text: 'Frequency offset (MHz)', standoff: 8 },
      showgrid: true, gridcolor: '#21262d',
      zeroline: true, zerolinecolor: '#58a6ff', zerolinewidth: 1,
      range: [-0.12, 0.12],
    },
    yaxis: {
      title: { text: 'PSD (dB/Hz)', standoff: 8 },
      showgrid: true, gridcolor: '#21262d',
      range: [-120, -20],
    },
    margin: { t: 18, r: 24, b: 44, l: 56 },
    hovermode: 'x',
    showlegend: false,
    shapes: [
      {
        type: 'line', x0: 0, x1: 0, y0: 0, y1: 1,
        yref: 'paper',
        line: { color: '#f85149', width: 1.5, dash: 'dash' },
        visible: false,
      },
      {
        type: 'line', x0: 0, x1: 0, y0: 0, y1: 1,
        yref: 'paper',
        line: { color: '#f85149', width: 1.5, dash: 'dash' },
        visible: false,
      },
    ],
    annotations: [
      {
        x: 0, y: 0, xref: 'x', yref: 'paper',
        text: '', showarrow: false,
        font: { color: '#f85149', size: 11, family: 'monospace' },
        yanchor: 'bottom', y: 0.98,
        visible: false,
      },
    ],
  };

  const trace = {
    x: [], y: [],
    mode: 'lines',
    line: { color: '#58a6ff', width: 1.4 },
    fill: 'tozeroy',
    fillcolor: 'rgba(88,166,255,0.15)',
    hovertemplate: '%{x:.4f} MHz<br>%{y:.1f} dB/Hz<extra></extra>',
  };

  Plotly.newPlot('psd-chart', [trace], layout, {
    responsive: true,
    displayModeBar: false,
  });

  // ── Helpers ───────────────────────────────────────────
  function setStatus(online, label) {
    connected = online;
    $dot.className = 'dot' + (online ? ' online' : '');
    $label.textContent = label || (online ? 'online' : 'stopped');
  }

  async function fetchStatus() {
    try {
      const r = await fetch('/api/status');
      const d = await r.json();
      $freq.value   = d.center_freq;
      $gain.value   = d.gain;
      $span.value   = d.span_khz;
      $nfft.value   = d.nfft;
      $nps.value    = d.nperseg;
      $novrlap.value = d.noverlap;
      setStatus(d.running);
    } catch (_) { /* server not ready */ }
  }

  async function applyConfig() {
    const payload = {
      center_freq: parseFloat($freq.value),
      gain:        parseFloat($gain.value),
      span_khz:    parseFloat($span.value) || 0,
      nfft:        parseInt($nfft.value, 10),
      nperseg:     parseInt($nps.value, 10),
      noverlap:    parseInt($novrlap.value, 10),
    };
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  }

  // ── Immediate gain + frequency updates (real-time, no Apply needed) ──
  async function sendGain() {
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gain: parseFloat($gain.value) }),
    });
  }

  async function sendFreq() {
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ center_freq: parseFloat($freq.value) }),
    });
  }

  $gain.addEventListener('change', sendGain);
  $gain.addEventListener('input', function () {
    clearTimeout($gain._debounce);
    $gain._debounce = setTimeout(sendGain, 300);
  });

  $freq.addEventListener('change', sendFreq);

  // ── Buttons ───────────────────────────────────────────
  $start.addEventListener('click', async () => {
    await applyConfig();
    await fetch('/api/start', { method: 'POST' });
    fetchStatus();
  });

  $stop.addEventListener('click', async () => {
    await fetch('/api/stop', { method: 'POST' });
    setStatus(false, 'stopped');
    $iFreq.textContent = '--';
    $iGain.textContent = '--';
    $iSpan.textContent = '--';
    $iBw.textContent  = '--';
    $iClip.textContent = '--';
    Plotly.relayout('psd-chart', {
      'shapes[0].visible': false,
      'shapes[1].visible': false,
      'annotations[0].visible': false,
    });
  });

  $apply.addEventListener('click', applyConfig);

  // ── SocketIO events ───────────────────────────────────
  socket.on('connect', () => fetchStatus());

  socket.on('psd_update', function (data) {
    setStatus(true);

    $iFreq.textContent = data.center_freq.toFixed(3) + ' MHz';
    $iGain.textContent = data.gain.toFixed(1) + ' dB';
    $iClip.textContent = data.clipping.toFixed(6);

    const bwKHz = data.bw_khz || 0;
    const leftKHz = data.bw_left_khz || 0;

    if (bwKHz > 0) {
      $iBw.textContent = bwKHz.toFixed(1) + ' kHz';
    } else {
      $iBw.textContent = '--';
    }

    // ── X‑axis range (MHz) ────────────────────────────
    const userSpan = parseFloat($span.value) || 0;
    let halfSpanMHz;
    if (userSpan > 0) {
      halfSpanMHz = userSpan / 2000;
    } else {
      halfSpanMHz = 0.12;
    }
    $iSpan.textContent = (halfSpanMHz * 2000).toFixed(0) + ' kHz';

    // ── Bandwidth lines + annotation ───────────────────
    const updates = {};

    if (bwKHz > 0) {
      const leftMHz  = leftKHz / 1000;
      const rightMHz = leftMHz + bwKHz / 1000;
      updates['shapes[0].x0'] = leftMHz;
      updates['shapes[0].x1'] = leftMHz;
      updates['shapes[0].visible'] = true;
      updates['shapes[1].x0'] = rightMHz;
      updates['shapes[1].x1'] = rightMHz;
      updates['shapes[1].visible'] = true;

      const midMHz = (leftMHz + rightMHz) / 2;
      updates['annotations[0].x'] = midMHz;
      updates['annotations[0].text'] = 'BW = ' + bwKHz.toFixed(1) + ' kHz';
      updates['annotations[0].visible'] = true;
    } else {
      updates['shapes[0].visible'] = false;
      updates['shapes[1].visible'] = false;
      updates['annotations[0].visible'] = false;
    }

    Plotly.update('psd-chart', {
      x: [data.freq_mhz],
      y: [data.psd_db],
    }, Object.assign({
      'xaxis.range': [-halfSpanMHz, halfSpanMHz],
    }, updates));
  });

  socket.on('disconnect', function () {
    setStatus(false);
    $iFreq.textContent = '--';
    $iGain.textContent = '--';
    $iSpan.textContent = '--';
    $iBw.textContent  = '--';
    $iClip.textContent = '--';
  });

  fetchStatus();
})();
