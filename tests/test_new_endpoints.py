"""Quick test for session health and history report endpoints."""
import os
os.environ['DATABASE_URL'] = 'postgresql+psycopg://monitor:monitor@localhost:5432/monitoring'

from fastapi.testclient import TestClient
from src.app.api.main import app

c = TestClient(app)
PASS = 0
FAIL = 0

def check(name, cond, detail=''):
    global PASS, FAIL
    if cond:
        print(f'  PASS  {name}')
        PASS += 1
    else:
        print(f'  FAIL  {name}' + (f': {detail}' if detail else ''))
        FAIL += 1

# 1. Health
print('=== 1. Health ===')
r = c.get('/health')
check('GET /health', r.status_code == 200 and r.json()['status'] == 'ok')

# 2. Session health - all customers
print('\n=== 2. Session Health (all) ===')
r = c.get('/api/v1/sessions/health')
check('status 200', r.status_code == 200, r.text[:100])
d = r.json()
check('has total_profiles', 'total_profiles' in d)
check('has sso_sessions', 'sso_sessions' in d)
check('32 profiles', d.get('total_profiles') == 32, str(d.get('total_profiles')))
check('aryanoble-sso detected', 'aryanoble-sso' in d.get('sso_sessions', {}))
check('Nabati detected', 'Nabati' in d.get('sso_sessions', {}))
check('all expired', d.get('expired') == 32, str(d.get('expired')))

# 3. Session health - customer filter
print('\n=== 3. Session Health (customer filter) ===')
r2 = c.get('/api/v1/customers')
customers = {x['name']: x['id'] for x in r2.json()['customers']}
aryanoble_id = customers.get('aryanoble')
ksni_id = customers.get('ksni')
check('customers found', bool(aryanoble_id and ksni_id))

r = c.get(f'/api/v1/sessions/health?customer_id={aryanoble_id}')
check('filter by customer 200', r.status_code == 200)
d = r.json()
check('aryanoble 17 profiles', d.get('total_profiles') == 17, str(d.get('total_profiles')))
check('only aryanoble-sso', list(d.get('sso_sessions', {}).keys()) == ['aryanoble-sso'])

# 4. History report regeneration
print('\n=== 4. History Report Regeneration ===')
accts = c.get(f'/api/v1/customers/{aryanoble_id}').json()['accounts']
connect_prod_id = next((a['id'] for a in accts if a['profile_name'] == 'connect-prod'), None)
check('connect-prod found', bool(connect_prod_id))

# Single mode
r = c.post('/api/v1/checks/execute', json={
    'customer_id': aryanoble_id,
    'mode': 'single',
    'check_name': 'guardduty',
    'account_ids': [connect_prod_id],
})
check('execute single 200', r.status_code == 200, r.text[:100])
run_id = r.json().get('check_run_id')
check('got run_id', bool(run_id))

r = c.get(f'/api/v1/history/{run_id}/report')
check('GET /history/{id}/report 200', r.status_code == 200, r.text[:100])
d = r.json()
check('has report', 'report' in d)
check('report not empty', len(d.get('report', '')) > 50)
check('report has account', 'Connect' in d.get('report', '') or 'connect-prod' in d.get('report', ''))
print(f'  Preview: {d.get("report", "")[:120]}')

# All mode
r = c.post('/api/v1/checks/execute', json={
    'customer_id': aryanoble_id,
    'mode': 'all',
    'account_ids': [connect_prod_id],
})
check('execute all 200', r.status_code == 200, r.text[:100])
all_run_id = r.json().get('check_run_id')

r = c.get(f'/api/v1/history/{all_run_id}/report')
check('GET /history/{id}/report all 200', r.status_code == 200)
d = r.json()
report = d.get('report', '')
check('has DAILY MONITORING REPORT', 'DAILY MONITORING REPORT' in report)
check('has EXECUTIVE SUMMARY', 'EXECUTIVE SUMMARY' in report)
print(f'  Report length: {len(report)} chars')

# 5. 404
print('\n=== 5. 404 cases ===')
r = c.get('/api/v1/history/nonexistent/report')
check('404 for missing run', r.status_code == 404)

print(f'\n=== Results: {PASS} passed, {FAIL} failed ===')
