from django.shortcuts import render


def page_not_found(request, exception):
    return render(request, "core/404.html", {"path": request.path}, status=404)


def csrf_failure(request, exception):
    return render(request, "core/csrf.html")


def permission_denied(request, exception):
    return render(request, "core/403.html", {"path": request.path}, status=403)
