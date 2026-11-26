// Use It Up: does a recipe ingredient match something in the pantry? Pure functions, shared by index.html and tests/matching.html.
//
// Rules (see README): an ingredient is "in the pantry" only if every meaningful word of it is part of the pantry item's
// name (so "chicken broth" != "chicken breast"), AND the pantry item's own form/variety words (powder, sauce, almond,
// peanut…) also appear in the ingredient (so "garlic" != "garlic powder"). Exception: an ingredient may name a cut
// ("chicken thighs") that a generic pantry item ("Chicken") doesn't specify.
//
// On top of that come the household's own match rules (shared between synced phones):
//   {kind:'alias', ing:'parmigiano', item:'parmesan'}  "parmigiano" counts as any pantry item matching "parmesan"
//   {kind:'not',   ing:'pepper',     item:'bell pepper'} "pepper" never matches a pantry item matching "bell pepper"
// `ing` and `item` are stored as normalized words (matchKey), so "Scallions" and "scallion" are the same rule.
const SYN = [[/\bscallions?\b/g, 'green onion'], [/\bcilantro\b/g, 'coriander'], [/\bcourgettes?\b/g, 'zucchini'], [/\baubergines?\b/g, 'eggplant'],
  [/\bcapsicums?\b/g, 'bell pepper'], [/\bchilli\b/g, 'chili'], [/\byoghurt\b/g, 'yogurt'], [/\bgarbanzo( beans?)?\b/g, 'chickpea'], [/\b(stock|bouillon)\b/g, 'broth']];
const STOP = new Set('whole fresh cooked leftover leftovers sliced slice raw ground large small baby organic the and with of boneless skinless chopped diced minced shredded grated frozen canned extra virgin low fat free unsalted salted dried cup tbsp tsp tablespoon teaspoon clove pound lb oz ounce pinch handful can package piece dash bunch head stick medium half optional taste some few plain lean thin thick ripe good quality cut bite size little more for serving about any your favorite leaf cubed crushed peeled trimmed halved rinsed drained melted softened beaten quartered torn mashed sifted toasted steamed boiled warm cold finely roughly thinly freshly splash drizzle sprinkle dollop knob'.split(' '));
const FORM = new Set('powder broth sauce paste juice flour vinegar oil ketchup jam jelly syrup soup puree extract flake cream seasoning mix cube dressing gravy salsa relish starch zest butter'.split(' '));
const ALT = new Set('almond coconut soy oat peanut cashew hazelnut sweet sour smoked'.split(' '));
const CUT = new Set('breast thigh wing drumstick leg fillet loin steak chop rib tender tenderloin shoulder belly roast'.split(' '));
const sing2 = w => /(us|ss|is)$/.test(w) ? w : w === 'leaves' ? 'leaf' : w.replace(/ies$/, 'y').replace(/oes$/, 'o').replace(/(ch|sh|x|z)es$/, '$1').replace(/s$/, '');
const words = s => { let t = String(s).toLowerCase().replace(/\(.*?\)|\[.*?\]/g, ' ').replace(/:\s*\d+\s*days?\s*left/g, ' '); SYN.forEach(([re, to]) => { t = t.replace(re, to); });
  return t.split(/[^a-z]+/).filter(w => w.length > 2).map(sing2).filter(w => !STOP.has(w)); };
const matchKey = s => words(s).join(' ');
function itemMatches(ingW, itemName) {
  const iw = words(itemName); if (!iw.length || !ingW.length) return false;
  const itemHasCut = iw.some(w => CUT.has(w));
  if (ingW.some(w => !iw.includes(w) && !(CUT.has(w) && !itemHasCut))) return false;   // unexplained extra word in the ingredient
  if (iw.some(w => (FORM.has(w) || ALT.has(w)) && !ingW.includes(w))) return false;   // pantry item is a specific form the ingredient doesn't ask for
  return ingW.some(w => iw.includes(w));
}
function isStaple(s) {
  s = String(s).toLowerCase();
  // "pepper" alone / black / white / cracked / ground pepper is a seasoning; bell, chili, ghost… pepper is a vegetable
  if (/\b(black|white|cracked|ground|cayenne)\s+pepper\b|\bsalt\s*(and|&)\s*pepper\b|\bpepper\s+flakes?\b|^\W*(\d[\d\/. ]*\s*(tsp|tbsp|teaspoons?|tablespoons?|pinch(es)?)?\s*(of\s+)?)?pepper\W*$/.test(s)) return true;
  return /(^|\W)(oil|salt|water|spices?|seasoning|paprika|cumin|oregano|thyme|basil|cinnamon|cayenne|turmeric|nutmeg|rosemary|herbs?|garlic powder|onion powder|chili powder|chili flakes?)(\W|$)/.test(s);
}
// Does this pantry item satisfy this ingredient, after the household's rules?
function itemSatisfies(ing, itemName, rules = []) {
  const key = matchKey(ing), w = key ? key.split(' ') : [];
  if (!w.length) return false;
  const mine = rules.filter(r => r && r.ing === key);
  if (mine.some(r => r.kind === 'not' && itemMatches(r.item.split(' '), itemName))) return false;
  return itemMatches(w, itemName) || mine.some(r => r.kind === 'alias' && itemMatches(r.item.split(' '), itemName));
}
// The pantry item an ingredient matches (fresh ones first), or null.
function findItemIn(ing, items, rules, isFresh, fresh = true) {
  return items.find(it => isFresh(it) === fresh && itemSatisfies(ing, it.name, rules)) || null;
}
// -> 'have' | 'expired' | 'staple' | 'similar' (right ingredient, wrong form) | 'missing'
function checkIngredientIn(ing, items, rules, isFresh) {
  if (!words(ing).length) return 'staple';
  if (findItemIn(ing, items, rules, isFresh, true)) return 'have';
  if (findItemIn(ing, items, rules, isFresh, false)) return 'expired';
  if (isStaple(ing)) return 'staple';
  return nearItemIn(ing, items, rules, isFresh) ? 'similar' : 'missing';
}
// A fresh pantry item that shares a word with the ingredient (a look-alike), unless a rule says it isn't one.
function nearItemIn(ing, items, rules, isFresh) {
  const w = words(ing), key = w.join(' '), nots = (rules || []).filter(r => r && r.kind === 'not' && r.ing === key);
  return items.find(it => isFresh(it) && words(it.name).some(x => w.includes(x)) && !nots.some(r => itemMatches(r.item.split(' '), it.name))) || null;
}
if (typeof module !== 'undefined') module.exports = { words, matchKey, itemMatches, isStaple, itemSatisfies, findItemIn, checkIngredientIn, nearItemIn };
