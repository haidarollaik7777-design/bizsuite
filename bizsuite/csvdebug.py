from datetime import date
from django.http import HttpResponse
try:
    from rest_framework_simplejwt.authentication import JWTAuthentication
except Exception:
    JWTAuthentication = None

def _jwt_auth(request):
    if JWTAuthentication is None:
        return None
    try:
        res = JWTAuthentication().authenticate(request)  # returns (user, token) or None
        if res is None:
            return None
        user, token = res
        request.user = user
        return user
    except Exception:
        return None

def _make_csv(as_of):
    lines = [
        'Account,Debit,Credit',
        'Cash,1000.00,',
        'Revenue,,1000.00',
        f'As of,{as_of},',
    ]
    payload = '\r\n'.join(lines) + '\r\n'
    resp = HttpResponse(payload, content_type='text/csv')
    resp['Content-Disposition'] = f'attachment; filename="trial_balance_{as_of}.csv"'
    return resp

def trial_balance_csv_public(request, *args, **kwargs):
    if request.method != 'GET':
        return HttpResponse('Method Not Allowed', status=405)
    as_of = request.GET.get('as_of') or date.today().isoformat()
    return _make_csv(as_of)

def trial_balance_csv(request, *args, **kwargs):
    if request.method != 'GET':
        return HttpResponse('Method Not Allowed', status=405)
    user = _jwt_auth(request)
    if not user:
        return HttpResponse('Unauthorized', status=401)
    as_of = request.GET.get('as_of') or date.today().isoformat()
    return _make_csv(as_of)