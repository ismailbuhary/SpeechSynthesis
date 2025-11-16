#!/usr/bin/env python
import io
import numpy as np
import soundfile as sf
from flask import Flask, request, send_file, render_template_string, jsonify

from kokoro import KPipeline

# -----------------------------
# Model setup (loaded once)
# -----------------------------
# 'a' => American English (see README for other lang codes)
# voices (e.g. 'af_heart') are documented in VOICES.md on the model page.
# :contentReference[oaicite:1]{index=1}
pipeline = KPipeline(lang_code="a")
DEFAULT_VOICE = "am_echo"
SAMPLE_RATE = 24000

app = Flask(__name__)


def synthesize_to_wav_bytes(text: str, voice: str = DEFAULT_VOICE) -> io.BytesIO:
    """
    Run Kokoro TTS and return audio as an in-memory WAV file.
    """
    # generator yields (graphemes, phonemes, audio_chunk)
    generator = pipeline(
        text,
        voice=voice,
        speed=1.0,
        split_pattern=r"\n+",
    )

    chunks = []
    for _, _, audio in generator:
        chunks.append(audio)

    if not chunks:
        raise RuntimeError("No audio generated from Kokoro pipeline.")

    # Concatenate segments into a single waveform
    full_audio = np.concatenate(chunks).astype("float32")

    # Write to BytesIO as WAV
    buf = io.BytesIO()
    sf.write(buf, full_audio, SAMPLE_RATE, format="WAV")
    buf.seek(0)
    return buf


# -----------------------------
# Simple HTML form for testing
# -----------------------------
INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Kokoro TTS Test</title>
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 2rem;
      background: #111;
      color: #eee;
    }
    textarea {
      width: 100%;
      max-width: 640px;
    }
    button {
      padding: 0.5rem 1rem;
      font-size: 1rem;
      cursor: pointer;
    }
    #status {
      margin-top: 1rem;
      font-size: 0.95rem;
      font-style: italic;
    }
  </style>
</head>
<body>
  <h1>Kokoro-82M TTS Test</h1>
  <form id="tts-form">
    <textarea name="text" id="text" rows="5" cols="60"
              placeholder="Type some text to synthesize..."></textarea><br><br>
    <button type="submit" id="submit-btn">Generate Speech</button>
  </form>

  <div id="status"></div>

  <h2>Output</h2>
  <audio id="player" controls></audio>

  <script>
    const form = document.getElementById('tts-form');
    const player = document.getElementById('player');
    const statusEl = document.getElementById('status');
    const submitBtn = document.getElementById('submit-btn');

    let timerId = null;
    let elapsed = 0;

    function startTimer() {
      elapsed = 0;
      statusEl.textContent = 'Processing... 0.0s';
      statusEl.style.visibility = 'visible';

      // Update every 100ms
      timerId = setInterval(() => {
        elapsed += 0.1;
        statusEl.textContent = 'Processing... ' + elapsed.toFixed(1) + 's';
      }, 100);
    }

    function stopTimer(success = true, errorMsg = '') {
      if (timerId !== null) {
        clearInterval(timerId);
        timerId = null;
      }
      if (success) {
        statusEl.textContent = 'Done in ' + elapsed.toFixed(1) + 's';
      } else {
        statusEl.textContent = 'Error after ' + elapsed.toFixed(1) + 's: ' + errorMsg;
      }
    }

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = document.getElementById('text').value;
      if (!text.trim()) {
        alert("Please enter some text.");
        return;
      }

      const formData = new FormData();
      formData.append('text', text);

      // Disable button + start timer
      submitBtn.disabled = true;
      startTimer();

      try {
        const resp = await fetch('/tts', {
          method: 'POST',
          body: formData
        });

        if (!resp.ok) {
          let errText = resp.statusText;
          try {
            const errJson = await resp.json();
            if (errJson && errJson.error) {
              errText = errJson.error;
            }
          } catch (_) {}

          stopTimer(false, errText);
          alert('Error: ' + errText);
        } else {
          const blob = await resp.blob();
          const url = URL.createObjectURL(blob);
          player.src = url;
          player.play();
          stopTimer(true);
        }
      } catch (err) {
        stopTimer(false, err.message || err);
        alert('Error: ' + (err.message || err));
      } finally {
        submitBtn.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(INDEX_HTML)


# -----------------------------
# API endpoint: /tts
# -----------------------------
@app.route("/tts", methods=["POST"])
def tts():
    """
    Accepts text via form-data or JSON and returns audio/wav.
    """
    text = None

    # form-data (from HTML form)
    if "text" in request.form:
        text = request.form["text"]

    # JSON body
    if text is None and request.is_json:
        text = request.json.get("text")

    if not text or not text.strip():
        return jsonify({"error": "No text provided"}), 400

    try:
        wav_buf = synthesize_to_wav_bytes(text)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return send_file(
        wav_buf,
        mimetype="audio/wav",
        as_attachment=False,
        download_name="speech.wav",
    )


if __name__ == "__main__":
    # Host 0.0.0.0 so you can hit it from other devices on LAN if needed
    app.run(host="172.0.0.1", port=10000, debug=False)
