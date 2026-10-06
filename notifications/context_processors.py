def unread_count(request):
    if request.user.is_authenticated:
        return {
            "unread_count": request.user.notifications.filter(
                read_at__isnull=True
            ).count()
        }
    return {"unread_count": 0}
