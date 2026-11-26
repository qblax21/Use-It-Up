# qwen2.5:14b vs qwen2.5:7b — recipe benchmark

**Run:** 2026-11-25 on the home PC (RTX 3060 12 GB, 32 GB RAM, Ollama 0.40.16, models on `D:\Ollama\models`, a 7200 rpm SATA hard disk).
**Script:** `py tools\bench.py 3`. Raw replies and timings are in [bench-raw.json](bench-raw.json).

**Method.** The script sends the same request the app's "Ask my AI" button sends:
- the stage-1 recipe prompt
- `format: json`
- `num_ctx` 2048, temperature 0.3, `num_predict` 400

It used 5 fixed pantries and ran each prompt 3 times per model, for 15 replies per model. Each model was loaded and warmed first, so the per-prompt numbers are **warm** (model already in GPU memory). Cold load is measured separately at the bottom.

**What the columns mean:**
- *Valid JSON:* the reply parses as strict JSON.
- *Usable:* every recipe has a name and a non-empty ingredient list, which is what the app needs.
- *First token:* the median over 3 runs. The first run of each prompt is slower (0.09–0.18 s) because later runs reuse Ollama's prompt cache.
- *Quality:* my 1–5 judgement of all 3 replies, based on whether the meals are real, use the soonest-expiring items, and follow the "pantry + staples only" rule.

| Pantry | Model | First token (s) | Total (s) | Tokens/s | Valid JSON | Usable | Quality (1–5) |
|---|---|---|---|---|---|---|---|
| chicken-veg (chicken 1d, broccoli 2d, pepper 3d, rice, soy sauce) | 14b | 0.04 | 3.6 | 34.8 | 3/3 | 3/3 | **4**: a proper stir-fry and rice bowl. The third idea is "soup from the leftover stir-fry" before it was cooked. |
| | 7b | 0.02 | 1.2 | 67.4 | 3/3 | 3/3 | **4**: stir-fry, soup and fried rice. Simple and all sensible. |
| breakfast (spinach 1d, bread 2d, milk 3d, eggs 4d, cheddar) | 14b | 0.06 | 2.4 | 34.9 | 3/3 | **2/3** | **2**: never uses the eggs, gives "spinach and bread soup" and plain toast, and one recipe had an empty ingredient list. |
| | 7b | 0.02 | 1.3 | 66.4 | 3/3 | 3/3 | **2**: French toast with no eggs and a spinach-milk smoothie. Uses eggs in only 1 of 3 runs. |
| leftovers (mashed potato 1d, roast chicken 2d, carrots, onion) | 14b | 0.14 | 3.0 | 34.4 | 3/3 | 3/3 | **4**: potato patties or pancakes, chicken and carrot stir-fry, chicken soup. Good repurposing. |
| | 7b | 0.02 | 1.1 | 66.7 | 3/3 | 3/3 | **3**: fine but bland ("mashed potatoes with roast chicken"). |
| pasta (ground beef 0d, tomato 1d, garlic, parmesan, pasta) | 14b | 0.04 | 3.6 | 34.6 | 3/3 | 3/3 | **3**: always makes the obvious beef and tomato pasta. It copies "0 days left" into ingredient names and once suggests "garlic infused oil" as a meal. |
| | 7b | 0.03 | 1.4 | 66.5 | 3/3 | 3/3 | **2**: beef "stir-fry" plus a duplicate "leftover beef stir-fry". It puts the beef in the pasta only in the separate tomato-garlic pasta. |
| odd-mix (banana 1d, zucchini 2d, yogurt 4d, tortillas, black beans) | 14b | 0.04 | 2.4 | 34.8 | 3/3 | 3/3 | **2**: banana smoothie with pepper, yogurt in a zucchini stir-fry, and it ignores the beans. |
| | 7b | 0.03 | 1.2 | 66.3 | 3/3 | 3/3 | **2**: tortilla "banana pancakes" and a zucchini "frittata" with no eggs. Black bean soup is fine. |

## Summary

| | qwen2.5:14b (default) | qwen2.5:7b (fallback) |
|---|---|---|
| Median first token, warm | 0.04 s (0.18 s uncached) | 0.02 s (0.09 s uncached) |
| Median total per reply, warm | 3.2 s (max 4.7 s) | 1.2 s (max 1.4 s) |
| Generation speed | 34.6 tokens/s | 66.7 tokens/s |
| Valid JSON | 15/15 (100%) | 15/15 (100%) |
| Usable recipe list | 14/15 (93%) | 15/15 (100%) |
| Average quality | **3.0** | **2.6** |
| GPU memory (num_ctx 2048) | 9.1 GB | 4.6 GB |
| Cold load from D: (first request after unload) | **112 s** | **41 s** |

**Conclusions.** The default stays at 14b.
- **Warm speed is not a problem for either model.** Both finish a recipe list in under 5 s once loaded. The 7b is about 2× faster, but 3 s versus 1 s barely matters on a phone.
- **14b is somewhat better at cooking.** Its meals are more often real dishes, and it repurposes leftovers better. Both models do poorly on awkward pantries.
- **JSON is reliable.** With `format: json`, every reply was valid JSON. The one unusable 14b reply had a recipe with an empty ingredient list, and the app's built-in retry handles that.
- **The real cost is the cold start.** D: is a spinning hard disk, so loading 9 GB takes about 112 s (14b) versus 41 s (7b). The app allows 15 + 60 s on a cold start before switching to the fallback, so the first request after the model has been unloaded **would currently time out on 14b and fall back to 7b**. See *Cold start* below.
- **Prompt issue (fixed later, see *Recipe prompt* below).** Both models read "no eggs, onions, cheese… unless listed" as "avoid eggs and cheese" even when they *are* listed: see the breakfast row. The tables above use that original (v1) prompt.

## Recipe prompt (2026-11-25)

The same 5 pantries × 3 runs per model, one row per rule wording. The full texts are in `RULES` in `tools/bench.py`; raw replies are in `docs/bench-raw-prompt-*.json`.
- *Eggs / cheese used:* breakfast recipes (9 per model) that use the listed eggs or cheese.
- *Off-list:* recipes (out of about 45) that add an ingredient that is neither in the pantry nor a basic staple.

| Prompt | What it changes | 14b eggs / cheese used | 14b off-list | 7b eggs / cheese used | 7b off-list |
|---|---|---|---|---|---|
| v1 (old) | "never add anything else (no eggs, onions, cheese, etc. unless listed)" | 0/9 · 1/9 | 0/46 | 1/9 · 0/9 | 0/45 |
| v2 | "use any of them freely, including eggs, cheese or milk when they are listed" | 8/9 · 9/9 | **20/45** | 5/9 · 3/9 | 13/45 |
| v3 | "nothing else counts as a staple (not butter, flour, sugar, eggs, milk, cheese…)" | 2/9 · 0/9 | 1/45 | 3/9 · 0/9 | 10/45 |
| v4 | names no foods: "all the items listed above are available… use only the listed items plus oil, salt…" | 8/9 · 5/9 | 9/45 | 5/9 · 2/9 | 7/45 |
| v5 | v4 + "before answering, check every ingredient" | 3/9 · 3/9 | 7/45 | 4/9 · 2/9 | 0/45 |
| **v4 + re-ask (now in the app)** | v4, then one re-ask if the answer uses something you don't have | **8/9 · 2/9** | **1/45** | 4/9 · 1/9 | 3/45 |

**Findings**
- **Naming foods in the rule backfires either way.** Telling the model *not* to add eggs or cheese makes it avoid them even when they're listed (v1, v3). Telling it that it *may* use them makes it add them when they aren't listed (v2).
- **v4 names no foods,** so the model judges from the list itself.
- **A code check catches what wording can't.** The app runs each answer through the same `checkIngredient()` that draws the ⚠️ marks, including your saved match fixes. If any recipe uses something that isn't in the pantry and isn't a staple, it asks once more, naming exactly those ingredients and dishes. It keeps whichever answer has fewer of them.
  - The re-ask was needed in 5 of 15 runs for the 14b and 3 of 15 for the 7b, and took off-list ingredients from 9 to 1 (14b) and from 39 to 6 (7b).
  - Cost: the median reply stays at 3.3 s for the 14b. With a re-ask the worst case was 7.0 s.
- **The days-left and "[cooked leftover]" tags no longer leak into ingredient names.** The prompt now says "write each ingredient as just its name", and `match.js` strips those tags anyway.
- Run-to-run variation is real at temperature 0.3: cheese use for the 14b with v4 ranged from 2/9 to 5/9 across two runs. Treat single-digit differences as noise.

**GPU contention.** During the in-app test, the 14b slowed from 34 to 5–9 tokens/s, and a recipe answer took 15–45 s. The cause was another program, QuickTurnSimDemo, using about 90% of the GPU. A 12 GB card can't run a 3D app and the 14b at full speed together.

## Cold start

The models stay on D:. All measurements below are of qwen2.5:14b with `num_ctx` 2048, asking for one short answer.

| Situation | First token | Notes |
|---|---|---|
| **Before:** model not in GPU memory, read from the D: hard disk | **112 s** (bench run), **116 s** (repeat run 10 min later) | Longer than the app's old 15 + 60 s cold allowance, so the app gave up on 14b and loaded the 7b instead. That meant another 41 s load, and evicting the 14b. |
| Model not in GPU memory, file still in Windows' file cache | 2–4 s | Happens sometimes (the preloader's load took 4 s and the app's test took 2 s). You can't rely on it: the 116 s run above happened 10 minutes after a read. |
| **After:** preloaded at login (`tools\ollama-preload.ps1`) | **0.3 s** (total 0.4 s) | The model is already in GPU memory when the phone asks. |

**What changed**
- **Preload at login:** `tools\install-preload-autostart.ps1` puts `UseItUp-Preload.vbs` in the Startup folder. After login it waits for Ollama and loads qwen2.5:14b with `keep_alive` 4h. It also reloads at **11:30 and 16:30** if the model was unloaded, so it's warm before lunch and dinner. Log: `%USERPROFILE%\UseItUp\preload.log`.
- **keep_alive 4h (was 30m):** every request resets Ollama's unload timer to *that request's* keep_alive. I saw this in testing: a test request with `5m` cut the preloader's 4 h down to 5 minutes. So the app's default is now `4h`. Phones that had the old default `30m` saved are moved to 4h automatically. Any other value someone typed in is kept.
- **Longer cold allowance:** `coldGrace` went from 60 s to 150 s and the per-call cap from 180 s to 300 s. A cold 14b now waits about 2 minutes instead of falling back to a 7b that also has to load from disk.
- **"Warming up AI…" state:** when the model isn't loaded, the header pill shows an amber **AI warming up…**. The Recipes card shows **⏳ Warming up AI…** with a seconds counter, and a toast says **AI is warmed up and ready** when it's done. The shelf-life button shows the same message.

**VRAM tradeoff (12 GB RTX 3060)**
- qwen2.5:14b at `num_ctx` 2048 uses **9.1 GB**. With Windows and the desktop using about 1.3 GB, about **1.7 GB is left** while it is loaded (`nvidia-smi` showed 10.4 / 12.3 GB used).
- That's fine for browsing and video. Anything else that wants the GPU while the model is loaded (games, Demucs, other AI tools) will be short of memory and may fail or crawl. To free the GPU: `ollama stop qwen2.5:14b` (it reloads at the next use or the next warm-up time).
- The 14b and 7b **can't both be in GPU memory** (9.1 + 4.6 GB > 12 GB). Using the fallback evicts the 14b, so the next 14b request is cold again. That's another reason to wait for the 14b rather than fall back quickly.
- **Why 4h and not `-1` (forever):** `-1` would make cold starts disappear, but it would hold 9 GB of GPU memory permanently. 4 h plus the meal-time reloads covers the times the app is actually used. If you'd rather never wait, set "Keep model loaded for" to `-1` in More → AI helper, and reinstall the preloader with `-KeepAlive -1`.
