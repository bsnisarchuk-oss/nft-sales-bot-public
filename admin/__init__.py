from .handlers import router

# Админский модуль: экспортируем router, чтобы подключать админку в основном приложении.
__all__ = ["router"]
