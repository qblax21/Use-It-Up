"""Benchmark Ollama models on Use It Up's own recipe prompt (5 fixed pantries).

    py tools\bench.py [reps=3] [models=qwen2.5:14b,qwen2.5:7b] [out=docs\bench-raw.json]

Uses the same request the app sends (stream, format=json, num_ctx 2048, temperature 0.3, num_predict 400).
Each model is first loaded and warmed, so timings are "warm" numbers; the cold load time is recorded separately.
"""
import json, sys, time, urllib.request

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


def prompt(p):
    lines = '\n'.join(f'- {x[0]}{" [cooked leftover]" if len(x) > 2 else ""}: {x[1]} days left' for x in sorted(p, key=lambda x: x[1]))
    return (f'Pantry (soonest-expiring first):\n{lines}\n\nSuggest 3 simple meals that use the soonest-expiring items. For a cooked leftover, '
            'suggest how to reheat or repurpose it. STRICT RULE: ingredients may only be pantry items above plus oil, salt, pepper, water and '
            'common spices — never add anything else (no eggs, onions, cheese, etc. unless listed).\n\nReply with JSON only: '
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


results = {'when': time.strftime('%Y-%m-%d %H:%M'), 'reps': REPS, 'models': {}}
for model in MODELS:
    unload_all()
    t0 = time.perf_counter()
    w = json.load(post('/api/generate', {'model': model, 'prompt': 'Say OK.', 'stream': False, 'keep_alive': '30m', 'options': {'num_ctx': 2048, 'num_predict': 3}}))
    cold = {'first_request_s': time.perf_counter() - t0, 'load_s': w.get('load_duration', 0) / 1e9}
    ps = json.load(urllib.request.urlopen(OLLAMA + '/api/ps'))['models']
    cold['vram_gb'] = next((m['size_vram'] / 1e9 for m in ps if m['name'] == model), None)
    runs = {}
    for name, p in PANTRIES.items():
        runs[name] = [run(model, prompt(p)) for _ in range(REPS)]
        print(model, name, [(round(x['ttft'] or 0, 2), round(x['total'], 1), x['valid_json'], x['usable']) for x in runs[name]], flush=True)
    results['models'][model] = {'cold': cold, 'runs': runs}
unload_all()
json.dump(results, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('saved', OUT)
