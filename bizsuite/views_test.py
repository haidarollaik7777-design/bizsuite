from django.http import HttpResponse

def test_invoices(request):
    return HttpResponse("<!doctype html><meta charset='utf-8'><h1>BizSuite Invoice Tester</h1><p>Page loaded.</p>")
