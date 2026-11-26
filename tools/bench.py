"""Benchmark Ollama models on Use It Up's own recipe prompt (5 fixed pantries).

    py tools\bench.py [reps=3] [models=qwen2.5:14b,qwen2.5:7b] [out=docs\bench-raw.json] [prompt=v4] [fix]

Uses the same request the app sends (stream, format=json, num_ctx 2048, temperature 0.3, num_predict 400).
Each model is first loaded and warmed, so timings are "warm" numbers; the cold load time is recorded separately.
"""
import json, re, sys, time, urllib.request

OLLAMA = 'http://127.0.0.1:11434'
REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
MODELS = (sys.argv[2] if len(sys.argv) > 2 else 'qwen2.5:14b,qwen2.5:7b').split(',')
OUT = sys.argv[3] if len(sys.argv) > 3 else 'docs/bench-raw.json'

PANTRIES = {
    'chicken-veg': [('Chicken breast', 1), ('Broccoli', 2), ('Rice', 60), ('Bell pepper', 3), ('Soy sauce', 90)],
    'breakfast': [('Eggs', 4), ('Spinach', 1), ('Cheddar cheese', 10), ('Bread', 2), ('Milk', 3)],
    'leftovers': [('Leftovers: roast chicken', 2, True), ('Leftovers: mashed potatoes', 1, True), ('Carrots', 6), ('Onion', 20)],
    'pasta': [('Pasta', 120), ('Tomato', 1), ('Garlic', 15), ('Ground beef', 0), ('Parmesan', 20)],
    'odd-mix': [('Tortillas', 5), ('Black beans', 200), ('Banana', 1), ('Greek yogurt', 4), ('Zucchini', 2)],
}


# The rule text the app sends. v1 = before 2026-11-25 (models avoided listed eggs/cheese); v2 = current index.html.
RULES = {
    'v1': 'Suggest 3 simple meals that use the soonest-expiring items. For a cooked leftover, suggest how to reheat or repurpose it. '
          'STRICT RULE: ingredients may only be pantry items above plus oil, salt, pepper, water and common spices — never add anything '
          'else (no eggs, onions, cheese, etc. unless listed).',
    'v2': 'Suggest 3 simple, real dishes that use up the soonest-expiring items. Every item in the list above is available, so use any of '
          'them freely, including eggs, cheese or milk when they are listed. For a cooked leftover, suggest how to reheat or repurpose it. '
          'The only things you may add are basic staples: oil, salt, black pepper, water and dried spices. Do not add any other ingredient '
          'that is not in the list. Write each ingredient as just its name, without quantities, days left or notes.',
    'v3': 'Suggest 3 simple, real dishes that use up the soonest-expiring items. You can use any item in the list above. For a cooked '
          'leftover, suggest how to reheat or repurpose it. Besides the listed items you may add only oil, salt, black pepper, water and '
          'dried spices; nothing else counts as a staple (not butter, flour, sugar, eggs, milk, cheese or fresh herbs, unless they are in '
          'the list). Check every ingredient against the list before answering. Write each ingredient as just its name, without '
          'quantities, days left or notes.',
    'v4': 'Suggest 3 simple, real dishes that use up the soonest-expiring items. All the items listed above are available to cook with, '
          'and a dish may combine several of them. For a cooked leftover, suggest how to reheat or repurpose it. Use only the listed items '
          'plus oil, salt, black pepper, water and dried spices — nothing else. Write each ingredient as just its name, without quantities, '
          'days left or notes.',
    'v5': 'Suggest 3 simple, real dishes that use up the soonest-expiring items. All the items listed above are available to cook with, '
          'and a dish may combine several of them. For a cooked leftover, suggest how to reheat or repurpose it. Use only the listed items '
          'plus oil, salt, black pepper, water and dried spices — nothing else. Before answering, check every ingredient: if it is neither '
          'in the list nor one of those staples, change the dish. Write each ingredient as just its name, without quantities, days left or notes.',
}
PROMPT = sys.argv[4] if len(sys.argv) > 4 else 'v4'


def prompt(p):
    lines = '\n'.join(f'- {x[0]}{" [cooked leftover]" if len(x) > 2 else ""}: {x[1]} days left' for x in sorted(p, key=lambda x: x[1]))
    return (f'Pantry (soonest-expiring first):\n{lines}\n\n{RULES[PROMPT]}\n\nReply with JSON only: '
            '{"recipes":[{"name":"...","ingredients":["every ingredient, including staples"]}]}')


def post(path, body, stream=False):
    req = urllib.request.Request(OLLAMA + path, json.dumps(body).encode(), {'content-type': 'application/json'})
    return urllib.request.urlopen(req, timeout=600)


def unload_all():
    for m in json.load(urllib.request.urlopen(OLLAMA + '/api/ps')).get('models', []):
        post('/api/generate', {'model': m['name'], 'keep_alive': 0}).read()
    time.sleep(2)


def run(model, text):
    t0 = time.perf_counter(); ttft = None; out = ''; fin = {}
    r = post('/api/chat', {'model': model, 'stream': True, 'format': 'json', 'keep_alive': '30m', 'messages': [{'role': 'user', 'content': text}],
                           'options': {'num_predict': 400, 'temperature': 0.3, 'num_ctx': 2048}})
    for line in r:
        j = json.loads(line)
        c = j.get('message', {}).get('content')
        if c:
            if ttft is None: ttft = time.perf_counter() - t0
            out += c
        if j.get('done'): fin = j
    total = time.perf_counter() - t0
    try:
        data = json.loads(out); valid = True
    except ValueError:
        data = None; valid = False
    recs = data.get('recipes') if isinstance(data, dict) else None
    usable = isinstance(recs, list) and len(recs) > 0 and all(isinstance(x, dict) and x.get('name') and x.get('ingredients') for x in recs)
    return {'ttft': ttft, 'total': total, 'tokens': fin.get('eval_count'), 'tps': fin['eval_count'] / (fin['eval_duration'] / 1e9) if fin.get('eval_duration') else None,
            'valid_json': valid, 'usable': usable, 'done_reason': fin.get('done_reason'), 'raw': out}


FIX = len(sys.argv) > 5 and sys.argv[5] == 'fix'   # mimic the app's one corrective retry for off-list ingredients
STAPLE = re.compile(r'\b(oil|salt|pepper|water|spices?|garlic powder|onion powder|paprika|cumin|oregano|thyme|basil|cinnamon|chili|herbs?|turmeric|nutmeg|rosemary|cayenne)\b', re.I)


def off_list(raw, pantry):
    """Rough Python stand-in for the app's checkIngredient(): [(dish, ingredient)] not in the pantry and not a staple."""
    words = ' '.join(x[0].lower() for x in pantry)
    try: recs = json.loads(raw).get('recipes') or []
    except (ValueError, AttributeError): return []
    out = []
    for r in recs:
        for i in map(str, r.get('ingredients', []) if isinstance(r, dict) else []):
            if STAPLE.search(i) and 'bell pepper' not in i.lower(): continue
            w = [x for x in re.findall(r'[a-z]+', i.lower()) if len(x) > 2 and x not in ('and', 'the', 'leftover', 'cooked', 'fresh')]
            if not any(x.rstrip('s') in words for x in w): out.append((r.get('name', '?'), i))
    return out


def fix_prompt(text, bad):   # keep in step with index.html (fixPrompt)
    names = '; '.join(f'{i} (in "{d}")' for d, i in bad)
    return (text + f'\n\nYour previous answer used ingredients that are not in the pantry: {names}. Answer again with 3 dishes that use only '
            'the listed items plus oil, salt, black pepper, water and dried spices. Keep any dish that already follows this rule.')


def run_fixed(model, p):
    text = prompt(p); a = run(model, text); a['off_list'] = off_list(a['raw'], p)
    if FIX and a['off_list']:
        b = run(model, fix_prompt(text, a['off_list'])); b['off_list'] = off_list(b['raw'], p)
        best = b if b['usable'] and len(b['off_list']) < len(a['off_list']) else a
        best = dict(best, total=a['total'] + b['total'], retried=True, first_off_list=a['off_list'])
        return best
    return a


results = {'when': time.strftime('%Y-%m-%d %H:%M'), 'reps': REPS, 'prompt': PROMPT, 'fix': FIX, 'models': {}}
for model in MODELS:
    unload_all()
    t0 = time.perf_counter()
    w = json.load(post('/api/generate', {'model': model, 'prompt': 'Say OK.', 'stream': False, 'keep_alive': '30m', 'options': {'num_ctx': 2048, 'num_predict': 3}}))
    cold = {'first_request_s': time.perf_counter() - t0, 'load_s': w.get('load_duration', 0) / 1e9}
    ps = json.load(urllib.request.urlopen(OLLAMA + '/api/ps'))['models']
    cold['vram_gb'] = next((m['size_vram'] / 1e9 for m in ps if m['name'] == model), None)
    runs = {}
    for name, p in PANTRIES.items():
        runs[name] = [run_fixed(model, p) for _ in range(REPS)]
        print(model, name, [(round(x['ttft'] or 0, 2), round(x['total'], 1), x['valid_json'], x['usable']) for x in runs[name]], flush=True)
    results['models'][model] = {'cold': cold, 'runs': runs}
unload_all()
json.dump(results, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('saved', OUT)
