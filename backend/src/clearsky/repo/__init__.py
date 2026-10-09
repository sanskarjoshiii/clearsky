"""DynamoDB repositories, one class per table. Table names come from `settings.table_prefix`."""

from clearsky.repo.alerts import AlertsRepo
from clearsky.repo.applications import ApplicationsRepo
from clearsky.repo.balers import BalerDaysRepo, BalersRepo
from clearsky.repo.bookings import BookingsRepo
from clearsky.repo.buyers import BuyersRepo
from clearsky.repo.conversations import ConversationsRepo
from clearsky.repo.farmers import FarmersRepo
from clearsky.repo.fields import FieldsRepo
from clearsky.repo.settings_repo import SettingsRepo
from clearsky.repo.villages import VillagesRepo

__all__ = [
    "AlertsRepo",
    "ApplicationsRepo",
    "BalerDaysRepo",
    "BalersRepo",
    "BookingsRepo",
    "BuyersRepo",
    "ConversationsRepo",
    "FarmersRepo",
    "FieldsRepo",
    "SettingsRepo",
    "VillagesRepo",
]
