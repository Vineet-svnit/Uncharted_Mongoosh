"""Standalone validation that only uses stdlib."""
import sys
import os
import types

# Stub missing deps
for mod in ['pymongo', 'bson', 'gridfs']:
    stub = types.SimpleNamespace(
        ASCENDING=1, ObjectId=str, GridFS=object,
        errors=types.SimpleNamespace(OperationFailure=Exception),
        UpdateOne=None
    )
    sys.modules[mod] = stub
sys.modules['pymongo.errors'] = types.SimpleNamespace(OperationFailure=Exception)
sys.modules['dotenv'] = types.SimpleNamespace(load_dotenv=lambda **kw: None)

import importlib.util


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


base = os.path.join(os.path.dirname(__file__), '..', '..')
base = os.path.abspath(base)

scenario = load_module(os.path.join(base, 'data_layer', 'seed', 'scenario.py'),
                       'data_layer.seed.scenario')
gd = load_module(os.path.join(base, 'data_layer', 'seed', 'generate_dataset.py'),
                 'data_layer.seed.generate_dataset')

svcs = gd.generate_services()
deps = gd.generate_deployments()
msgs = gd.generate_slack_messages()
tel = gd.generate_telemetry()
rbs = gd.generate_runbooks()
pms = gd.generate_postmortems()
inc = gd.generate_incident()
sla = gd.generate_sla_data()

errors = 0


def ck(label, cond, detail=''):
    global errors
    if cond:
        print(f'  OK  {label}')
    else:
        print(f'  FAIL {label} {detail}')
        errors += 1


print('=== Count checks ===')
ck('Services == 8', len(svcs) == 8, len(svcs))
ck('Deployments == 9', len(deps) == 9, len(deps))
ck('Slack messages == 50', len(msgs) == 50, len(msgs))
ck('Telemetry == 180', len(tel) == 180, len(tel))
ck('Runbooks == 4', len(rbs) == 4, len(rbs))
ck('Postmortems >= 2', len(pms) >= 2, len(pms))
ck('SLA contracts == 2', len(sla) == 2, len(sla))

print('\n=== Ground-truth checks ===')
pr812 = next(d for d in deps if d['pr_number'] == 812)
ck('PR 812 at 13:58 UTC', pr812['deployed_at'] == '2026-10-28T13:58:00Z', pr812['deployed_at'])
old = pr812['previous_config'].get('redis_pool_max_connections')
new = pr812['updated_config'].get('redis_pool_max_connections')
ck('PR 812 pool change 500->50', old == 500 and new == 50, f'{old}->{new}')
ck('PR 812 service = auth-service', pr812['service_id'] == 'auth-service')

pr813 = next(d for d in deps if d['pr_number'] == 813)
ck('PR 813 rollback at 14:22', pr813['deployed_at'] == '2026-10-28T14:22:00Z', pr813['deployed_at'])
ck('PR 813 rollback_of = DEP-812', pr813['rollback_of'] == 'DEP-812', pr813['rollback_of'])

mx = max(e['metric_value'] for e in tel if e['metric_name'] == 'redis_pool_utilization')
ck(f'Redis pool reached 100% (got {mx})', mx == 100.0)

mr = max(e['metric_value'] for e in tel if e['metric_name'] == 'internal_retry_per_minute')
ck(f'Retries >= 840/min = 15x baseline (got {mr:.0f})', mr >= 840)

ing = [e['metric_value'] for e in tel if e['metric_name'] == 'ingress_requests_per_second']
ck(f'Ingress stable, max={max(ing):.0f} rps', max(ing) < 2400)

ck('Incident downtime = 23 min', inc['downtime_minutes'] == 23, inc['downtime_minutes'])
ck('Incident ID correct', inc['incident_id'] == 'INC-2026-10-28-001')

acme = next(s for s in sla if s['customer_id'] == 'acme-corp')
c32 = next(c for c in acme['clauses'] if c['clause_number'] == '3.2')
ck('Acme 3.2: rca=True, credit=0%', c32['rca_required'] is True and c32['financial_credit_pct'] == 0.0)
ck('Acme 3.2: range 20-30 min', c32['downtime_min_minutes'] == 20 and c32['downtime_max_minutes'] == 30)

print('\n=== Referential integrity ===')
svc_ids = {s['service_id'] for s in svcs}
exp_svcs = {
    'api-gateway', 'checkout-api', 'auth-service', 'redis-cluster-east',
    'payment-service', 'orders-db', 'notification-service', 'user-profile-api',
}
ck('All 8 required services present', svc_ids == exp_svcs, str(svc_ids - exp_svcs))

for svc in svcs:
    svc_id = svc['service_id']
    for dep_id in svc.get('depends_on', []):
        ck(f'  {svc_id} -> {dep_id}', dep_id in svc_ids)

for dep in deps:
    ck(f'  deployment {dep["deployment_id"]} svc valid', dep['service_id'] in svc_ids)

inc_ids = {m['incident_id'] for m in msgs}
ck('All messages share incident_id', inc_ids == {'INC-2026-10-28-001'}, str(inc_ids))

print(f'\n{"=" * 40}')
print(f'Total errors: {errors}')
if errors == 0:
    print('ALL CHECKS PASSED')
else:
    print(f'{errors} FAILURES')
sys.exit(errors)
