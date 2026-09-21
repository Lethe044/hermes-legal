"""
Local web dashboard - lets a non-technical user (paralegal, small firm
staff, a freelancer's client) drag a contract file onto a browser page
and get an analysis, without ever touching the command line.

Deliberately built on Python's standard library http.server instead of
Flask/FastAPI so it adds zero new required dependencies - "free" here
means free to install, not just free to run.
"""

from __future__ import annotations

import base64
import json
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

from .analysis.engine import analyze_contract
from .ingest import read_document
from .memory.store import MemoryStore
from .playbook import Playbook
from .providers import get_provider

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Hermes Legal Advisor</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { color-scheme: dark; }
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; background: #0f1115; color: #e6e6e6;
         max-width: 900px; margin: 0 auto; padding: 32px 20px; }
  h1 { font-size: 1.5rem; margin-bottom: 4px; }
  .sub { color: #9aa0a6; margin-bottom: 24px; }
  #drop { border: 2px dashed #3a3f4b; border-radius: 12px; padding: 48px 20px; text-align: center;
          cursor: pointer; transition: border-color .15s; }
  #drop.drag { border-color: #5b8def; background: #151925; }
  #drop p { margin: 0; color: #9aa0a6; }
  select, input, button { background: #1b1f2a; color: #e6e6e6; border: 1px solid #3a3f4b;
         border-radius: 8px; padding: 8px 10px; font-size: 0.95rem; }
  button { cursor: pointer; background: #5b8def; border: none; color: white; font-weight: 600; }
  button:hover { background: #4a76d4; }
  .row { display: flex; gap: 10px; align-items: center; margin: 16px 0; flex-wrap: wrap; }
  table { width: 100%; border-collapse: collapse; margin-top: 12px; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #2a2f3a; font-size: 0.9rem; }
  th { color: #9aa0a6; font-weight: 600; }
  .badge { padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }
  .CRITICAL, .REJECT { background: #4a1414; color: #ff6b6b; }
  .HIGH, .NEGOTIATE { background: #4a2f0f; color: #ffb454; }
  .MEDIUM { background: #4a3f0f; color: #ffd866; }
  .LOW, .SIGN { background: #14351f; color: #6bdb8f; }
  .flag { color: #ff6b6b; font-weight: 700; }
  #status { margin-top: 12px; color: #9aa0a6; }
  #result { margin-top: 24px; display: none; }
  .disclaimer { margin-top: 32px; color: #6b7280; font-size: 0.8rem; }
  a { color: #5b8def; }
</style>
</head>
<body>
  <h1>Hermes Legal Advisor</h1>
  <div class="sub">Drop a contract below (.txt, .md, .pdf, .docx) for a free risk analysis.</div>

  <div id="drop">
    <p>Drag and drop a contract file here, or click to choose one</p>
    <input type="file" id="fileInput" style="display:none" accept=".txt,.md,.pdf,.docx">
  </div>

  <div class="row">
    <label for="perspective">Perspective:</label>
    <select id="perspective">
      <option value="neutral">Neutral</option>
      <option value="client">Client</option>
      <option value="vendor">Vendor</option>
      <option value="contractor">Contractor</option>
      <option value="employer">Employer</option>
      <option value="employee">Employee</option>
      <option value="tenant">Tenant</option>
      <option value="landlord">Landlord</option>
    </select>
    <button onclick="showHistory()">View history</button>
  </div>

  <div id="status"></div>
  <div id="result"></div>
  <div id="historyBox"></div>

  <div class="disclaimer">
    Hermes Legal Advisor provides contract analysis, not legal advice.
    Always consult a qualified attorney before signing any contract.
  </div>

<script>
const API_KEY = new URLSearchParams(location.search).get('key') || '';
const authHeaders = API_KEY ? {'X-API-Key': API_KEY} : {};

const drop = document.getElementById('drop');
const fileInput = document.getElementById('fileInput');
const statusEl = document.getElementById('status');
const resultEl = document.getElementById('result');
const historyBox = document.getElementById('historyBox');

drop.addEventListener('click', () => fileInput.click());
drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('drag'); });
drop.addEventListener('dragleave', () => drop.classList.remove('drag'));
drop.addEventListener('drop', e => {
  e.preventDefault();
  drop.classList.remove('drag');
  if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => { if (fileInput.files.length) handleFile(fileInput.files[0]); });

function handleFile(file) {
  const reader = new FileReader();
  reader.onload = async () => {
    const base64 = reader.result.split(',')[1];
    statusEl.textContent = 'Analyzing ' + file.name + ' ...';
    resultEl.style.display = 'none';
    try {
      const resp = await fetch('/api/analyze', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', ...authHeaders},
        body: JSON.stringify({
          filename: file.name,
          content_base64: base64,
          perspective: document.getElementById('perspective').value
        })
      });
      const data = await resp.json();
      if (data.error) { statusEl.textContent = 'Error: ' + data.error; return; }
      statusEl.textContent = '';
      renderResult(data);
    } catch (err) {
      statusEl.textContent = 'Error: ' + err;
    }
  };
  reader.readAsDataURL(file);
}

function renderResult(data) {
  let html = `<h2>${data.contract_type}</h2>`;
  html += `<div class="row">
    <span class="badge ${data.overall_risk}">${data.overall_risk}</span>
    <span class="badge ${data.verdict}">${data.verdict}</span>
    <span>Provider: ${data.provider}</span>
  </div>`;
  html += `<p>${data.summary || ''}</p>`;
  html += '<table><tr><th>Clause</th><th>Score</th><th></th><th>Finding</th></tr>';
  for (const c of data.clauses) {
    html += `<tr><td>${c.name}</td><td>${c.score}/10</td>
      <td>${c.is_red_flag ? '<span class="flag">FLAG</span>' : ''}</td>
      <td>${c.finding || ''}</td></tr>`;
  }
  html += '</table>';
  if (data.missing_clauses && data.missing_clauses.length) {
    html += '<h3>Missing Clauses</h3><ul>' + data.missing_clauses.map(m => `<li>${m}</li>`).join('') + '</ul>';
  }
  if (data.recommendations && data.recommendations.length) {
    html += '<h3>Recommended Actions</h3><ol>' + data.recommendations.map(r => `<li>${r}</li>`).join('') + '</ol>';
  }
  resultEl.innerHTML = html;
  resultEl.style.display = 'block';
}

async function showHistory() {
  const resp = await fetch('/api/history', {headers: authHeaders});
  const data = await resp.json();
  if (!data.length) { historyBox.innerHTML = '<p>No contracts analyzed yet.</p>'; return; }
  let html = '<h2>History</h2><table><tr><th>Date</th><th>Type</th><th>Parties</th><th>Risk</th><th>Verdict</th></tr>';
  for (const c of data.slice().reverse()) {
    html += `<tr><td>${(c.timestamp||'').slice(0,10)}</td><td>${c.contract_type||''}</td>
      <td>${c.parties||''}</td><td><span class="badge ${c.risk_level}">${c.risk_level||''}</span></td>
      <td><span class="badge ${c.verdict}">${c.verdict||''}</span></td></tr>`;
  }
  html += '</table>';
  historyBox.innerHTML = html;
}
</script>
</body>
</html>
"""


class _Handler(BaseHTTPRequestHandler):
    provider_name = "auto"
    api_key: Optional[str] = None

    def log_message(self, fmt, *args):
        pass  # keep stdout clean; rely on CLI output instead

    def _is_authorized(self) -> bool:
        if not self.api_key:
            return True
        header_key = self.headers.get("X-API-Key")
        if header_key and header_key == self.api_key:
            return True
        query = parse_qs(urlparse(self.path).query)
        query_key = query.get("key", [None])[0]
        return query_key == self.api_key

    def _send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            body = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/history":
            if not self._is_authorized():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            memory = MemoryStore()
            self._send_json(memory.contracts())
        else:
            self._send_json({"error": "not found"}, status=404)

    def do_POST(self):
        if urlparse(self.path).path != "/api/analyze":
            self._send_json({"error": "not found"}, status=404)
            return
        if not self._is_authorized():
            self._send_json({"error": "unauthorized"}, status=401)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            filename = payload["filename"]
            content = base64.b64decode(payload["content_base64"])
            perspective = payload.get("perspective", "neutral")

            suffix = Path(filename).suffix or ".txt"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)

            try:
                text = read_document(tmp_path)
                provider = get_provider(self.provider_name)
                outcome = analyze_contract(text, provider=provider, perspective=perspective, playbook=Playbook())
                result = outcome["result"]
                data = result.to_dict()
                data["hash"] = outcome["hash"]
                data["trend"] = outcome["trend"]
                self._send_json(data)
            finally:
                tmp_path.unlink(missing_ok=True)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)


def run_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    provider_name: str = "auto",
    open_browser: bool = True,
    api_key: Optional[str] = None,
):
    _Handler.provider_name = provider_name
    _Handler.api_key = api_key
    server = ThreadingHTTPServer((host, port), _Handler)
    url = f"http://{host}:{port}"
    if api_key:
        url_with_key = f"{url}/?key={api_key}"
        print(f"Hermes Legal Advisor dashboard running at {url} (API key required)")
        print(f"Open with the key already filled in: {url_with_key}")
    else:
        url_with_key = url
        print(f"Hermes Legal Advisor dashboard running at {url}")
    print("Press Ctrl+C to stop.")

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url_with_key)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
