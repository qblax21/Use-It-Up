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
fallback `qwen2.5:7b`. Replies are streamed. If the main model errors, runs out of memory, or sends no first
word within 15 s (when it's already loaded in GPU memory), the app retries once with the fallback. A model that still
has to be loaded from disk gets 150 extra seconds first, because qwen2.5:14b takes about 2 minutes to load from the D: hard
disk and switching to a fallback that is also cold would be slower. Meanwhile the app shows **AI warming up…**. Requests
use a 2048-token context window and ask Ollama to keep the model loaded for 4 hours. The model is also pre-loaded when you
open the Recipes tab. All of these are editable under **More** (a web page can't read environment variables, so they
live in settings). Timings and quality: [docs/benchmarks.md](docs/benchmarks.md).

**Warm at login (recommended):** run `powershell -ExecutionPolicy Bypass -File tools\install-preload-autostart.ps1` once.
It loads qwen2.5:14b into GPU memory at every login and again at 11:30 and 16:30 if it was unloaded, so the first request
from a phone takes well under a second instead of about 2 minutes. While loaded it holds about 9 GB of the 12 GB GPU; run
`ollama stop qwen2.5:14b` to free it. Log: `%LOCALAPPDATA%\UseItUp\preload.log`.

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

## Shared pantry (two phones, one pantry)

By default each phone keeps its own pantry in its browser storage. To share one pantry, run the tiny sync server on the PC
(`tools/sync-server.py`, standard-library Python, loopback only) behind the same Tailscale proxy:

1. `powershell -ExecutionPolicy Bypass -File tools\install-sync-autostart.ps1` (installs to `%LOCALAPPDATA%\UseItUp`,
   starts at login, restarts itself; pantry data is a small JSON file in `%USERPROFILE%\UseItUpData`).
2. `tailscale serve --bg --set-path /sync http://127.0.0.1:11437`
3. On phone 1: **More → Shared pantry**, address `https://<your-pc>.<tailnet>.ts.net/sync`, tap **New code**, **Save & sync**.
   On phone 2 (must be on the same tailnet, or have the PC shared to it): open the invite link from phone 1
   (**Copy invite link**) and tap **Join** on the card that appears, or enter the same address and code by hand.
   To test with two phones, use [docs/two-phone-test.md](docs/two-phone-test.md).

Items never change after they're added, so merging is a union minus deletions (deletions are remembered for 120 days) — no
conflicts. Each phone keeps working offline and catches up on the next sync (on open, every minute while open, after each change).
The pantry code is the only password, so treat it like one; the server is reachable only inside your tailnet.
