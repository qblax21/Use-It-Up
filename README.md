# Use It Up

Track groceries and leftovers, get reminded before they expire, and get recipe ideas.
Live: https://qblax21.github.io/Use-It-Up/

## How AI recipes are checked

Every ingredient the AI proposes is compared with your pantry:
an ingredient counts as "in your pantry" only if all its meaningful words appear in the pantry item's name
(so *chicken broth* ≠ *chicken breast*), and the pantry item's own form/variety words (*powder, sauce, almond, peanut…*)
also appear in the ingredient (so *garlic* ≠ *garlic powder*). A generic pantry item (*Chicken*) still satisfies a specific
cut (*chicken thighs*). Look-alikes show as ⚠️ with "you have X, but a different form". Expired items are never offered to
the AI, and any expired item that slips into a recipe is flagged ⛔.

Recipes load in two steps: names + ingredients first (about 3 s), then **Show steps** per recipe on demand.
The model is pre-loaded when you open the Recipes tab. If the AI's reply isn't usable JSON the app tolerates common
formatting slips and otherwise retries once automatically.

## AI helper (optional, runs on your PC)

Recipe ideas and shelf-life estimates use [Ollama](https://ollama.com) on your own computer.
No API key, nothing leaves your network. Defaults: `http://localhost:11434`, main model `qwen2.5:14b`,
fallback `qwen2.5:7b`. If the main model is missing, runs out of memory, or takes longer than the
timeout (90 s by default), the app retries once with the fallback. All of these are editable under
**More** in the app (a web page can't read environment variables, so they live in settings).

**On the PC itself** it works as-is (Chrome/Edge allow the HTTPS page to call `localhost`).

**On your phone** the page is HTTPS, so it can only call another HTTPS address. Easiest way:

1. Install [Tailscale](https://tailscale.com) on the PC and the phone (same account) and turn on HTTPS certificates
   for the tailnet.
2. Ollama refuses requests that arrive under a `*.ts.net` hostname (HTTP 403), so run the tiny loopback-only proxy
   in `tools/ollama-proxy.py`, which rewrites the Host header:
   `pythonw tools/ollama-proxy.py 11436 11434` (listen port, Ollama port). On Windows, run
   `powershell -ExecutionPolicy Bypass -File tools\install-proxy-autostart.ps1` once: it copies the proxy to
   `%LOCALAPPDATA%\UseItUp`, starts it at every login and restarts it within ~5 s if it ever stops.
3. Point Tailscale at the proxy. Use a **path** so you don't overwrite anything you already serve on :443:
   `tailscale serve --bg --set-path /ollama http://127.0.0.1:11436`
4. In the app's **More** tab set the Ollama address to `https://<your-pc>.<tailnet>.ts.net/ollama` and tap
   **Save & test**.

The PC must be on and awake, and the Tailscale app must be connected on the phone.
Without any of this, everything else (pantry, scanning, TheMealDB recipes) still works on the phone.
