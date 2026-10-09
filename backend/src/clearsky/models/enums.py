from enum import StrEnum


class FieldStatus(StrEnum):
    REGISTERED = "REGISTERED"
    HARVESTED = "HARVESTED"
    BOOKED = "BOOKED"
    CLEARED = "CLEARED"
    FIRE_REPORTED = "FIRE_REPORTED"


BOOKABLE_STATUSES = (FieldStatus.REGISTERED, FieldStatus.HARVESTED)


class BookingStatus(StrEnum):
    OFFERED = "OFFERED"  # sent to a baler, waiting for accept / decline (capacity already reserved)
    CONFIRMED = "CONFIRMED"
    DONE = "DONE"
    CANCELLED = "CANCELLED"
    DECLINED = "DECLINED"  # the baler said no → the matcher offers the field to the next baler
    EXPIRED = "EXPIRED"  # the baler did not answer in time → re-offered


# A pickup that will happen or has happened: what routes, stats and buyer supply count.
FIRM_BOOKING_STATUSES = (BookingStatus.CONFIRMED, BookingStatus.DONE)
# Holds baler capacity and the field: an open offer or a confirmed pickup.
OPEN_BOOKING_STATUSES = (BookingStatus.OFFERED, BookingStatus.CONFIRMED)
# An offer that ended without a pickup. That baler is never offered the same field again.
REFUSED_BOOKING_STATUSES = (BookingStatus.DECLINED, BookingStatus.EXPIRED)


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
