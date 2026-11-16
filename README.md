# Use It Up

Track groceries and leftovers, get reminded before they expire, and get recipe ideas.
Live: https://qblax21.github.io/Use-It-Up/

## AI helper (optional, runs on your PC)

Recipe ideas and shelf-life estimates use [Ollama](https://ollama.com) on your own computer.
No API key, nothing leaves your network. Defaults: `http://localhost:11434`, main model `qwen2.5:14b`,
fallback `qwen2.5:7b`. If the main model is missing, runs out of memory, or takes longer than the
timeout (90 s by default), the app retries once with the fallback. All of these are editable under
**More** in the app (a web page can't read environment variables, so they live in settings).

**On the PC itself** it works as-is (Chrome/Edge allow the HTTPS page to call `localhost`).

**On your phone** the page is HTTPS, so it can only call another HTTPS address. Easiest way:

1. Install [Tailscale](https://tailscale.com) on the PC and the phone (same account).
2. On the PC run: `tailscale serve --bg --https=443 http://localhost:11434`
3. In the app's **More** tab set the Ollama address to `https://<your-pc>.<tailnet>.ts.net`.

Without this, everything else (pantry, scanning, TheMealDB recipes) still works on the phone.
