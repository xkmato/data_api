from django.http import JsonResponse

__author__ = 'kenneth'


def page_not_found_view(request):
    return JsonResponse({
        "detail": "Not found"
    }, status=404)


def server_error_view(request):
    return JsonResponse({
        "detail": "Server Error"
    }, status=500)


def request_forbidden_view(request):
    return JsonResponse({
        "detail": "Permission Denied"
    }, status=403)


def bad_request_view(request):
    return JsonResponse({
        "detail": "Bad request"
    }, status=400)
