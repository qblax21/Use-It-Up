"""Merge tests for tools/sync-server.py:  py tests\\test_sync_server.py"""
import importlib.util, os, sys, tempfile, time

spec = importlib.util.spec_from_file_location('sync_server', os.path.join(os.path.dirname(__file__), '..', 'tools', 'sync-server.py'))
sys.argv = ['x', '0', tempfile.mkdtemp()]   # the module reads port / data dir from argv at import
srv = importlib.util.module_from_spec(spec); spec.loader.exec_module(srv)

empty = {'items': [], 'hist': [], 'tomb': {}, 'rules': []}
now = int(time.time() * 1000)
a1 = {'id': 'r1', 'kind': 'alias', 'ing': 'parmigiano', 'item': 'parmesan'}
n2 = {'id': 'r2', 'kind': 'not', 'ing': 'pepper', 'item': 'bell pepper'}

m = srv.merge(empty, {'items': [], 'rules': [a1]})
m = srv.merge(m, {'rules': [n2]})
assert sorted(r['id'] for r in m['rules']) == ['r1', 'r2'], m
m = srv.merge(m, {'tomb': {'r1': now}})                      # removed on one phone
assert [r['id'] for r in m['rules']] == ['r2'], m
m = srv.merge(m, {'rules': [a1]})                            # a stale phone can't bring it back
assert [r['id'] for r in m['rules']] == ['r2'], m
m = srv.merge(m, {'items': [{'id': 'i1', 'name': 'Milk'}]})  # an old app version that doesn't send rules keeps them
assert [r['id'] for r in m['rules']] == ['r2'] and m['items'][0]['name'] == 'Milk', m
assert srv.read_state('nonexistentcode123456')['rules'] == []
print('sync server merge tests: all passed')
