from aiogram import Router
from aiogram.types import CallbackQuery

from bot.handlers.start_menu import router as start_router
from bot.handlers.languages import router as lang_router
from bot.handlers.yoga import router as yoga_router
from bot.handlers.astrology import router as astro_router
from bot.handlers.mentoring import router as mentor_router
from bot.handlers.payments import router as pay_router
from bot.handlers.admin import router as admin_router
from bot.handlers.yoga_feedback.handlers import router as yoga_feedback_router

router = Router()


# @router.callback_query()
# async def _debug_all_callbacks(q: CallbackQuery):
#     print("RAW CALLBACK DATA:", q.data)
#     await q.answer()

router.include_router(start_router)
router.include_router(yoga_feedback_router)
router.include_router(lang_router)
router.include_router(yoga_router)
router.include_router(astro_router)
router.include_router(mentor_router)
router.include_router(pay_router)
router.include_router(admin_router)

