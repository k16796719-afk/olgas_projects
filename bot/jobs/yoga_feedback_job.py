# jobs/yoga_feedback_job.py
from datetime import datetime, timedelta

async def yoga_feedback_cron(db, bot):
    tomorrow = datetime.utcnow() + timedelta(days=1)

    rows = await db.fetch(
        """
        SELECT u.tg_user_id
        FROM subscriptions s
        JOIN users u ON u.id = s.user_id
        WHERE s.product = 'yoga'
          AND s.expires_at::date = $1::date
        """,
        tomorrow
    )

    for r in rows:
        await bot.send_message(
            r["tg_user_id"],
            "📋 Завтра заканчивается ваш доступ к группе.\n\n"
            "Мы будем очень благодарны за обратную связь 💛\n\n"
            "Нажмите ниже, чтобы начать опрос 👇",
        )
        await bot.send_message(
            r["tg_user_id"],
            "/yoga_feedback_start"
        )
