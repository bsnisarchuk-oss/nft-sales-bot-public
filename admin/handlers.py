from aiogram import Router

from admin.commands import router as commands_router
from admin.config_handlers import router as config_router
from admin.demo_handlers import router as demo_router
from admin.settings_handlers import router as settings_router
from admin.test_handlers import router as test_router

router = Router()
router.include_router(commands_router)
router.include_router(settings_router)
router.include_router(demo_router)
router.include_router(test_router)
router.include_router(config_router)
