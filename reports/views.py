from rest_framework.permissions import IsAuthenticated
# reports/views.py
from datetime import datetime
from typing import Optional
from django.apps import apps
from django.conf import settings
from django.db.models import Sum, DecimalField, ForeignKey, DateField, DateTimeField
from django.db.models.functions import Coalesce
from django.db.models import F, Q, Value
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

# ---- helpers ---------------------------------------------------------------
def _posting_mapping():
    """
    Returns (model, fields) where fields = dict with keys:
      account, date, debit, credit, (optional) company
    Priority: settings.REPORTS_POSTING -> auto-detect -> None
    """
    cfg = getattr(settings, "REPORTS_POSTING", None)
    if cfg:
        # Explicit mapping like:
        # REPORTS_POSTING = {
        #   "model": "ledger.Posting",
        #   "account": "account",
        #   "date": "date",
        #   "debit": "debit",
        #   "credit": "credit",
        #   "company": "company",  # optional
        # }
        model_label = cfg["model"]
        model = apps.get_model(model_label)
        return model, cfg

    # Auto-detect a reasonable posting model
    candidates = []
    for m in apps.get_models():
        flds = {f.name: f for f in m._meta.get_fields() if hasattr(f, "attname")}
        # likely field names
        debit = next((n for n,f in flds.items() if isinstance(f, DecimalField) and n.lower() in ("debit","debit_amount","dr")), None)
        credit= next((n for n,f in flds.items() if isinstance(f, DecimalField) and n.lower() in ("credit","credit_amount","cr")), None)
        date  = next((n for n,f in flds.items() if isinstance(f,(DateField,DateTimeField)) and n.lower() in ("date","posting_date","entry_date","invoice_date","created_at")), None)
        acct  = next((n for n,f in flds.items() if isinstance(f, ForeignKey) and f.related_model and "account" in f.related_model.__name__.lower()), None)
        comp  = next((n for n,f in flds.items() if isinstance(f, ForeignKey) and "company" in f.related_model.__name__.lower()), None)
        if debit and credit and date and acct:
            candidates.append((m, {"model": f"{m._meta.app_label}.{m.__name__}",
                                   "account": acct, "date": date, "debit": debit, "credit": credit,
                                   **({"company": comp} if comp else {})}))
    return (apps.get_model(candidates[0][0]._meta.label), candidates[0][1]) if candidates else (None, None)

def _account_fields(account_model):
    """
    Best-effort to find 'code' and 'name' fields on the account model.
    """
    flds = {f.name for f in account_model._meta.get_fields() if hasattr(f, "attname")}
    code = "code" if "code" in flds else None
    name = "name" if "name" in flds else ( "title" if "title" in flds else None )
    return code, name

def _parse_date(s: Optional[str]):
    if not s: return None
    return datetime.fromisoformat(s).date()

# ---- public endpoints -------------------------------------------------------
@api_view(["GET"])
@permission_classes([AllowAny])
def tester(request):
    return Response({"ok": True, "msg": "reports tester ok"})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trial_balance_api(request):
    as_of = _parse_date(request.query_params.get("as_of"))
    if not as_of:
        return Response({"ok": False, "error": "Missing ?as_of=YYYY-MM-DD"}, status=400)

    Posting, mp = _posting_mapping()
    if not Posting:
        return Response({
            "ok": False,
            "error": "Could not auto-detect a posting model.",
            "how_to_fix": "Define settings.REPORTS_POSTING mapping (model, account, date, debit, credit[, company])."
        }, status=501)

    acct_field = mp["account"]; date_field = mp["date"]
    debit_field= mp["debit"];   credit_field= mp["credit"]
    comp_field = mp.get("company")

    qs = Posting.objects.filter(**{f"{date_field}__lte": as_of})
    # Optional company filter ?company_id=
    company_id = request.query_params.get("company_id")
    if company_id and comp_field:
        qs = qs.filter(**{f"{comp_field}_id": company_id})

    # group by account
    account_rel = Posting._meta.get_field(acct_field).related_model
    code_field, name_field = _account_fields(account_rel)

    aggs = qs.values(f"{acct_field}").annotate(
        debit = Coalesce(Sum(debit_field), 0),
        credit= Coalesce(Sum(credit_field), 0),
    )

    # hydrate account info in a second pass (cheap N lookups or a join-like step)
    acc_ids = [row[f"{acct_field}"] for row in aggs]
    acc_map = {a.pk: a for a in account_rel.objects.filter(pk__in=acc_ids)}
    lines = []
    total_debit = total_credit = 0
    for row in aggs:
        aid = row[f"{acct_field}"]
        acc = acc_map.get(aid)
        code = getattr(acc, code_field) if acc and code_field else None
        name = getattr(acc, name_field) if acc and name_field else str(acc) if acc else f"Account {aid}"
        d = row["debit"] or 0
        c = row["credit"] or 0
        bal = float(d) - float(c)
        total_debit += float(d)
        total_credit += float(c)
        lines.append({"account_id": aid, "code": code, "name": name, "debit": float(d), "credit": float(c), "balance": bal})

    return Response({
        "ok": True,
        "as_of": as_of.isoformat(),
        "lines": sorted(lines, key=lambda x: (x["code"] or x["name"] or "")),
        "totals": {"debit": total_debit, "credit": total_credit, "balance": total_debit - total_credit},
        "source": mp
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profit_loss_api(request):
    start = _parse_date(request.query_params.get("start"))
    end   = _parse_date(request.query_params.get("end"))
    if not (start and end):
        return Response({"ok": False, "error": "Missing ?start=YYYY-MM-DD&end=YYYY-MM-DD"}, status=400)

    Posting, mp = _posting_mapping()
    if not Posting:
        return Response({
            "ok": False,
            "error": "Could not auto-detect a posting model.",
            "how_to_fix": "Define settings.REPORTS_POSTING mapping (model, account, date, debit, credit[, company])."
        }, status=501)

    acct_field = mp["account"]; date_field = mp["date"]
    debit_field= mp["debit"];   credit_field= mp["credit"]
    comp_field = mp.get("company")

    qs = Posting.objects.filter(**{f"{date_field}__gte": start, f"{date_field}__lte": end})

    company_id = request.query_params.get("company_id")
    if company_id and comp_field:
        qs = qs.filter(**{f"{comp_field}_id": company_id})

    account_rel = Posting._meta.get_field(acct_field).related_model
    code_field, name_field = _account_fields(account_rel)

    aggs = qs.values(f"{acct_field}").annotate(
        debit = Coalesce(Sum(debit_field), 0),
        credit= Coalesce(Sum(credit_field), 0),
    )

    acc_ids = [row[f"{acct_field}"] for row in aggs]
    acc_map = {a.pk: a for a in account_rel.objects.filter(pk__in=acc_ids)}
    lines = []
    total_rev = total_exp = 0.0

    # Try to detect account type so we can separate revenue/expense
    # If type field not found, we’ll classify by net sign (credit=rev, debit=exp) as a neutral fallback.
    type_field = None
    for candidate in ("type","account_type","category","kind","nature"):
        if hasattr(account_rel, candidate):
            type_field = candidate
            break

    for row in aggs:
        aid = row[f"{acct_field}"]
        acc = acc_map.get(aid)
        code = getattr(acc, code_field) if acc and code_field else None
        name = getattr(acc, name_field) if acc and name_field else str(acc) if acc else f"Account {aid}"
        d = float(row["debit"] or 0)
        c = float(row["credit"] or 0)
        net = c - d  # credit positive = income, debit positive = expense (common convention)

        kind = None
        if type_field and acc:
            kind = str(getattr(acc, type_field)).lower()

        if kind and ("income" in kind or "revenue" in kind or kind in ("i","rev")):
            total_rev += net
        elif kind and ("expense" in kind or kind in ("e","exp")):
            total_exp += (d - c)  # expense as positive
        else:
            # fallback by sign
            if net >= 0:
                total_rev += net
            else:
                total_exp += -net

        lines.append({"account_id": aid, "code": code, "name": name, "debit": d, "credit": c, "net": net})

    return Response({
        "ok": True,
        "start": start.isoformat(),
        "end":   end.isoformat(),
        "lines": sorted(lines, key=lambda x: (x["code"] or x["name"] or "")),
        "totals": {"revenue": total_rev, "expense": total_exp, "net_income": total_rev - total_exp},
        "source": mp
    })
from django.http import HttpResponse
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date
from django.apps import apps
from django.conf import settings
import csv
from datetime import date

def _posting_qs_and_cfg():
    cfg = getattr(settings, "REPORTS_POSTING", None)
    if not cfg:
        raise RuntimeError("REPORTS_POSTING not configured")
    Model = apps.get_model(cfg["model"])
    return Model.objects.all(), cfg

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trial_balance_csv(request):
    qs, cfg = _posting_qs_and_cfg()
    as_of = parse_date(request.query_params.get("as_of") or "") or date.today()
    qs = qs.filter(**{f"{cfg['date']}__lte": as_of})
    rows = (qs.values(cfg['account'])
              .annotate(debits=Coalesce(Sum(cfg['debit']), 0.0),
                        credits=Coalesce(Sum(cfg['credit']), 0.0))
              .order_by(cfg['account']))

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="trial_balance_{as_of.isoformat()}.csv"'
    w = csv.writer(resp)
    w.writerow(["account", "debits", "credits", "net (debits-credits)"])
    td = tc = 0.0
    for r in rows:
        acc = r[cfg['account']]
        d = float(r["debits"] or 0.0)
        c = float(r["credits"] or 0.0)
        td += d; tc += c
        w.writerow([acc, f"{d:.2f}", f"{c:.2f}", f"{(d-c):.2f}"])
    w.writerow([])
    w.writerow(["TOTAL", f"{td:.2f}", f"{tc:.2f}", f"{(td-tc):.2f}"])
    return resp

def reports_tester(request):
    return HttpResponse("reports tester ok")




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trial_balance_csv_simple(request):
    as_of = request.query_params.get('as_of') or date.today().isoformat()
    payload = (
        "Account,Debits,Credits\r\n"
        "Cash,1000.00,\r\n"
        "Revenue,,1000.00\r\n"
        f"As of,{as_of},\r\n"
    )
    resp = HttpResponse(payload, content_type='text/csv')
    resp['Content-Disposition'] = f'attachment; filename="trial_balance_{as_of}.csv"'
    return resp


