from enum import StrEnum


class FieldStatus(StrEnum):
    REGISTERED = "REGISTERED"
    HARVESTED = "HARVESTED"
    BOOKED = "BOOKED"
    CLEARED = "CLEARED"
    FIRE_REPORTED = "FIRE_REPORTED"


BOOKABLE_STATUSES = (FieldStatus.REGISTERED, FieldStatus.HARVESTED)


class BookingStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class ApplicationStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"  # approved earlier, later deactivated by the officer


class RiskLevel(StrEnum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class BuyerType(StrEnum):
    PELLET = "pellet"
    CBG = "cbg"
    BOILER = "boiler"
    BIOMASS_POWER = "biomass_power"


class Language(StrEnum):
    HINDI = "hi"
    PUNJABI = "pa"
    ENGLISH = "en"
