from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])
def tester(request):
    return Response({'ok': True, 'msg': 'reports tester ok'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trial_balance_api(request):
    as_of = request.query_params.get('as_of')
    # TODO: replace stub with real trial balance logic
    return Response({'ok': True, 'endpoint': 'trial-balance', 'as_of': as_of})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profit_loss_api(request):
    start = request.query_params.get('start')
    end   = request.query_params.get('end')
    # TODO: replace stub with real P&L logic
    return Response({'ok': True, 'endpoint': 'profit-loss', 'start': start, 'end': end})
