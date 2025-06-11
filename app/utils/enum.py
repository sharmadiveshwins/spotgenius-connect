from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DELETED = "DELETE"
    CLOSED = "CLOSED"


class SubTaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DELETED = "DELETED"
    CLOSED = "CLOSED"


class AuthType(str, Enum):
    BASIC = "basic"
    OAUTH = "oauth"
    JCOOKIE = "jcookie"
    LOGIN = "Login"
    BASIC_BASE_64 = "basicbase64"
    TOKEN = "Token"


class EventTypes(Enum):
    SPOT_OCCUPIED = "spot.occupied"
    SPOT_FREE = "spot.free"
    CAR_EXIT = "car.exit"
    CAR_ENTRY = "car.entry"
    PAYMENT_VIOLATION = "payment.violation"
    OVERSTAY_VIOLATION = "overstay.violation"
    VIOLATION = "violation"
    PARKING_VIOLATION = "parking.violation"
    VIOLATION_INACTIVE = "violation.inactivation"
    GROUPED_EVENTS = (
        SPOT_OCCUPIED,
        SPOT_FREE,
        CAR_EXIT,
        CAR_ENTRY
    )


class ViolationStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class PricingType(str, Enum):
    FIXED = "FIXED"
    VARIABLE = "VARIABLE"


class ProviderTypes(str, Enum):
    PAYMENT_PROVIDER = "provider.payment"
    PROVIDER_RESERVATION = "provider.reservation"
    PROVIDER_ENFORCEMENT = "provider.enforcement"
    PROVIDER_PUSH_CHECK = "provider.push.check"
    PROVIDER_VIOLATION = "provider.violation"
    PROVIDER_FAKE = "admin.fake"


class Provider(str, Enum):
    PROVIDER_PAYMENT_ARRIVE = "provider.payment.arrive"
    PROVIDER_PAYMENT_T2 = "provider.payment.t2"
    PROVIDER_PAYMENT_OOBEO = "provider.payment.oobeo"
    PROVIDER_RESERVATION_TIBA = "provider.reservation.tiba"
    PROVIDER_PARK_PLIANT = "ParkPliant"
    PROVIDER_ENFORCEMENT_ADMIN = "provider.enforcement.admin"
    PROVIDER_DEMO = "SpotgeniusDemo"


class PushPaymentStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class FeatureRequestType(str, Enum):
    PULL = 'PULL'
    PUSH = 'PUSH'


class ApiType(str, Enum):
    REST = 'REST'
    SOAP = 'SOAP'


class RequestMethod(str, Enum):
    POST = 'POST'
    GET = 'GET'


class Feature(str, Enum):
    PAYMENT_CHECK_LPR = 'payment.check.lpr'
    PAYMENT_CHECK_SPOT = 'payment.check.spot'
    PAYMENT_MAKE_LPR = 'payment.make.lpr'
    ENFORCEMENT_CITATION = 'enforcement.citation'
    RESERVATION_CHECK_LPR = 'reservation.check.lpr'
    RESERVATION_CHECK_SPOT = 'reservation.check.spot'
    PAYMENT_VIOLATION = "violation.payment"
    NOTIFY_SG_ADMIN = "notify.sg.admin"
    ENFORCEMENT_NOTIFICATION = "enforcement.inactivate"


class Event(str, Enum):
    unavailable = "spot.occupied"
    available = "spot.free"
    lpr_entry = "car.entry"
    lpr_exit = "car.exit"
    payment_violation = "payment.violation"
    overstay_violation = "overstay.violation"
    parking_spot_updates = "parking_spot_updates"
    parking_violations = "parking.violation"
    lpr_to_spot = "lpr.spot"
    lpr_to_spot_free = "lpr.spot.free"


class ActionType(str, Enum):
    CHECK_PAYMENT = "waiting for payment"
    PAID = "paid"
    NOT_PAID = "not paid"
    ALERT_SENT = "alert sent"
    ALERT_CLOSED = "alert closed"
    lpr_entry = "Entry"
    lpr_exit = "Exit"
    Meter_Expired = "Meter Expired"
    CITATION = "citation"
    SYSTEM_CLOSED = "System Closed"


class AuthLevel(str, Enum):
    GLOBAL = 'GLOBAL'
    CUSTOMER = 'CUSTOMER'
    PARKING_LOT = 'PARKING_LOT'


class Encryption(Enum):
    COLUMNS = ('access_token', 'client_secret')


class FeatureType(Enum):
    UNDEFINED = 'UNDEFINED'
    PAYMENT = 'PAYMENT'
    RESERVATION = 'RESERVATION'
    ENFORCEMENT = 'ENFORCEMENT'


class EventsForSessionLog(Enum):
    entry = "Entry"
    exit = "Exit"
    occupied = "occupied"
    free = "free"
    violation = "violation"
    reservation_expired = "Reservation Expired"
    unreserved = "Unreserved"
    reservation_remaining = "Reservation Remaining"
    monthly_pass = "Monthly Pass"
    not_paid = "Not Paid"
    paid = "Paid"
    non_payment_time = "Non Billable"
    overstay = "Overstay"
    alert_closed = "Alert Closed"
    Overstay_alert = "Overstay Alert sent"
    Payment_alert = "Payment Alert sent"
    OVERSTAY_ALERT_CLOSED = "Overstay Alert Closed"
    PAYMENT_ALERT_CLOSED = "Payment Alert Closed"
    PRIVILEGE_PERMIT = "Privilege Permit"
    VIOLATION_SENT = "Violation Sent"
    LPR_TO_SPOT = "Spot Matched: {spot_name}"
    LPR_TO_SPOT_FREE = "Spot Free: {spot_name}"
    inactivation = "Violation inactivated"
    Valid_PERMIT = "Valid Permit"
    PERMIT_EXPIRED = "Permit Expired"
    LPR_Entry_Description = "This session was automatically closed after another session was detected for the same vehicle."
    Occupied_Description = "This session was automatically closed after a new vehicle session was detected for the same spot."
    Forced_Exit_Description = "This session was automatically closed for exceeding the maximum session duration configured for this parking lot."
    Unknown_Event_Description = "This session was automatically closed due to an unexpected system event, such as a camera restart."
    SKIP_INSERT_IF_LAST_LOG_MATCHES = (
        not_paid,
        PERMIT_EXPIRED,
        Valid_PERMIT,
        unreserved
    )
    DURATION_ON_LOG = (
        paid,
        reservation_remaining,
        monthly_pass
    )

    def format(self, **kwargs):
        """Format the enum value with dynamic arguments."""
        return self.value.format(**kwargs)


class SpotLprEventsMapping(Enum):
    ENTRY = (EventTypes.SPOT_OCCUPIED.value, EventTypes.CAR_ENTRY.value)
    EXIT = (EventTypes.SPOT_FREE.value, EventTypes.CAR_EXIT.value)


class FacilityId(Enum):
    Facility_Id = "facility_id"


class Operators(Enum):
    ADD = "add"
    SUBTRACT = "subtract"
    TIME = "time"


class IsWaitingForPaymentMapping(Enum):
    ENTRY = True
    EXIT = False
    OCCUPIED = True
    FREE = False


class DefaultFacilityCode(Enum):

    ADMIN = "Admin"


class ProviderConfigurationDataType(Enum):

    MASKED = "masked"
    NUMBER = "number"
    DROPDOWN = "dropdown"
    TEXT = "text"


class DataTicket(Enum):
    AUTH_ERROR_MESSAGE = ('Expired Token', 'Invalid Token')


class ParkingOperations(str, Enum):
    spot_based_24_hours_free_parking = 'spot_based_24_hours_free_parking'
    lpr_based_24_hours_free_parking = 'lpr_based_24_hours_free_parking'
    paid_24_hours = 'paid_24_hours'
    specify_lpr_based_paid_parking_time = 'specify_lpr_based_paid_parking_time'


class TimeUnits(str, Enum):
    minutes = 'Minutes'
    hours = 'Hours'
    seconds = 'Seconds'


class AccessControl(Enum):

    CAN_VIEW = {"superadmin", "spotgenius.com"}


class AlertInactiveReason(Enum):

    PAYMENT_WINDOW_TO_FREE = "System marked as inactive as window is switching from payment to non-payment."
    FREE_TO_PAYMENT_WINDOW = "System marked as inactive as window is switching from non-payment to payment."
    PAYMENT_FOUND = "System marked as inactive as Payment was made."
    EXIT_DETECT = "System marked as inactive as Vehicle has exited the parking lot."
    LPR_TO_SPOT_FREE = "System marked as inactive as Vehicle has exited from the spot."
    LPR_SPOT_DETECTED = "System marked as inactive as the vehicle occupied a different spot"
    FORCED_EXIT = "System marked as inactive as this session was automatically closed for exceeding the maximum session duration configured for this parking lot."
    SAME_LPR_ENTRY = "System marked as inactive as this session was automatically closed after another session was detected for the same vehicle."
    SAME_OCCUPIED_EVENT = "System marked as inactive as this session was automatically closed after a new vehicle session was detected for the same spot."
    UNKNOWN_EVENT = "System marked as inactive as this session was automatically closed due to an unexpected system event, such as a camera restart."


class ViolationType(Enum):
    Overstay = "Overstay"
    Payment = "Payment"


class Scope(Enum):
    Org = "org"
    Lot = "lot"
    Spot = "spot"
    Zone = "zone"

class ProviderApiRequestType(Enum):
    Connect = "sgconnect"
    Northstar = "northstar"

class PaymentServiceFeature(Enum):
    LPR = "lpr"
    SPOT = "spot"


class ConfigLevel(Enum):
    GLOBAL = "global_level_config"
    CUSTOMER = "customer_level_config"
    PARKING_LOT = "parking_lot_level_config"


class ProviderTextKey(Enum):
    Arrive = "arrive.parkwhiz"
    AdminFake = "admin.fake"
