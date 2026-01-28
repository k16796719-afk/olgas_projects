from __future__ import annotations
import os
from dataclasses import dataclass
from typing import List, Optional

def _getenv(name: str, default: Optional[str] = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return v

def _getenv_opt(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name, default)
    if v is None or v == "":
        return None
    return v

def _parse_int_list(csv: str) -> List[int]:
    parts = [p.strip() for p in csv.split(",") if p.strip()]
    return [int(p) for p in parts]

@dataclass(frozen=True)
class Prices:
    trial_rub: int
    en_lesson_rub: int
    en_pack10_rub: int
    yoga_4_rub: int
    yoga_8_rub: int
    yoga_10ind_rub: int
    astro_1_rub: int
    astro_full_rub: int
    mentor_week_rub: int
    mentor_month_rub: int
    trial_china_rub: int
    china_lesson_rub: int
    china_pack10_rub: int

@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: List[int]
    database_url: str
    env: str
    tz: str

    channel_personal_id: int
    yoga_channel_4_id: int
    yoga_channel_8_id: int
    yoga_personal_channel_id: Optional[int]

    pay_rub_card_details: str
    pay_rub_card_owner: str | None
    pay_pix_key: str
    pay_pix_receiver_name: str
    pay_crypto_network: str
    pay_crypto_wallet: str

    prices: Prices
    yoga_subscription_days: int

    sweeper_hour: int
    sweeper_minute: int

    olga_telegram: str

def load_config() -> Config:
    bot_token = _getenv("BOT_TOKEN")
    admin_ids = _parse_int_list(_getenv("ADMIN_IDS"))
    database_url = _getenv("DATABASE_PUBLIC_URL")
    env = os.getenv("ENV", "prod")
    tz = os.getenv("TZ", "America/Sao_Paulo")

    olga_telegram = _getenv_opt("OLGA_TG_USERNAME", "@tabakaeva_olga")

    channel_personal_id = int(_getenv("CHANNEL_PERSONAL_ID"))
    yoga_channel_4_id = int(_getenv("YOGA_CHANNEL_4_ID"))
    yoga_channel_8_id = int(_getenv("YOGA_CHANNEL_8_ID"))
    ypc = _getenv_opt("YOGA_PERSONAL_CHANNEL_ID")
    yoga_personal_channel_id = int(ypc) if ypc else None

    pay_rub_card_details = _getenv("PAY_RUB_CARD_DETAILS")
    pay_rub_card_owner = _getenv_opt("PAY_RUB_CARD_OWNER", "Табакаева О.А.")
    pay_pix_key = _getenv("PAY_PIX_KEY")
    pay_pix_receiver_name = _getenv("PAY_PIX_RECEIVER_NAME")
    pay_crypto_network = _getenv("PAY_CRYPTO_NETWORK")
    pay_crypto_wallet = _getenv("PAY_CRYPTO_WALLET")

    prices = Prices(
        trial_rub=int(_getenv("PRICE_TRIAL_RUB")),
        en_lesson_rub=int(_getenv("PRICE_EN_LESSON_RUB")),
        en_pack10_rub=int(_getenv("PRICE_EN_PACK10_RUB")),
        trial_china_rub=int(_getenv("PRICE_TRIAL_CHINA_RUB")),
        china_lesson_rub=int(_getenv("PRICE_CHINA_LESSON_RUB")),
        china_pack10_rub=int(_getenv("PRICE_CHINA_PACK10_RUB")),
        yoga_4_rub=int(_getenv("PRICE_YOGA_4_RUB")),
        yoga_8_rub=int(_getenv("PRICE_YOGA_8_RUB")),
        yoga_10ind_rub=int(_getenv("PRICE_YOGA_10IND_RUB")),
        astro_1_rub=int(_getenv("PRICE_ASTRO_1_RUB")),
        astro_full_rub=int(_getenv("PRICE_ASTRO_FULL_RUB")),
        mentor_week_rub=int(_getenv("PRICE_MENTOR_WEEK_RUB")),
        mentor_month_rub=int(_getenv("PRICE_MENTOR_MONTH_RUB")),
    )

    yoga_subscription_days = int(os.getenv("YOGA_SUBSCRIPTION_DAYS", "30"))
    sweeper_hour = int(os.getenv("SWEEPER_HOUR", "9"))
    sweeper_minute = int(os.getenv("SWEEPER_MINUTE", "0"))


    return Config(
        bot_token=bot_token,
        admin_ids=admin_ids,
        database_url=database_url,
        env=env,
        tz=tz,
        channel_personal_id=channel_personal_id,
        yoga_channel_4_id=yoga_channel_4_id,
        yoga_channel_8_id=yoga_channel_8_id,
        yoga_personal_channel_id=yoga_personal_channel_id,
        pay_rub_card_details=pay_rub_card_details,
        pay_pix_key=pay_pix_key,
        pay_pix_receiver_name=pay_pix_receiver_name,
        pay_crypto_network=pay_crypto_network,
        pay_crypto_wallet=pay_crypto_wallet,
        prices=prices,
        yoga_subscription_days=yoga_subscription_days,
        sweeper_hour=sweeper_hour,
        sweeper_minute=sweeper_minute,
        pay_rub_card_owner=pay_rub_card_owner,
        olga_telegram=olga_telegram
    )

import os
print("CONFIG FILE LOADED:", __file__)
print("GIT SHA:", os.getenv("RAILWAY_GIT_COMMIT_SHA"))
print("PRICES FIELDS:", [f.name for f in __import__("dataclasses").fields(Prices)])
