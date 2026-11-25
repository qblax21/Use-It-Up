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
- **Prompt issue (not fixed here).** Both models read "no eggs, onions, cheese… unless listed" as "avoid eggs and cheese" even when they *are* listed: see the breakfast row. Rewording that rule should improve quality more than switching models would.

## Cold start (item 3)

See the "Cold start" section added below once measured.
