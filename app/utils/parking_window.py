from datetime import datetime, timedelta
from app.utils.common import parkinglot_overstay_limit
from app.utils.enum import ParkingOperations
from app.config import settings

class ParkingWindow:

#     @staticmethod
#     def __is_in_payment_window(current_time: datetime, windows: list):
#         for window in windows:
#             if window.start_time <= current_time.time() <= window.end_time:
#                 return True, None

#         # Find the next payment window's start time
#         next_window_start = min(
#             (
#                 datetime.combine(current_time.date(), window.start_time)
#                 for window in windows if window.start_time > current_time.time()
#             ),
#             default=datetime.combine(current_time.date() + timedelta(days=1), windows[0].start_time)  # Next day's first window
#         )
#         return False, next_window_start


#     @staticmethod
#     def check_payment_window(connect_parkinglot) -> dict:

#         current_time = datetime.utcnow()
#         overstay_limit = parkinglot_overstay_limit(connect_parkinglot, current_time)
#         payment_windows = connect_parkinglot.parking_time_slots
#         configured_time = timedelta(minutes=settings.VIOLATION_GRACE_PERIOD)
#         window_operation_type = connect_parkinglot.payment_window_operation_type

#         if window_operation_type == PaymentWindowOperationType.always_paid_parking:
#             status = True
#             next_at = current_time + configured_time

#         elif window_operation_type == PaymentWindowOperationType.always_free_parking:
#             status = False
#             next_at = current_time + overstay_limit
        
#         elif window_operation_type == PaymentWindowOperationType.specified_paid_timing:
#             is_paid, next_window_start = ParkingWindow.__is_in_payment_window(current_time, payment_windows)
            
#             if not is_paid:  # Non-payment window
#                 if current_time + overstay_limit <= next_window_start:
#                     next_at = current_time + overstay_limit
#                 else:
#                     next_at = next_window_start
#                 status = False
#             else:  # Payment window
#                 # Find the next non-payment window's start time
#                 next_free_window_start = min(
#                     (
#                         datetime.combine(current_time.date(), window.end_time)
#                         for window in payment_windows if window.end_time > current_time.time()
#                     ),
#                     default=datetime.combine(current_time.date() + timedelta(days=1), payment_windows[0].end_time)
#                 )

#                 if current_time + configured_time <= next_free_window_start:
#                     next_at = current_time + configured_time
#                 else:
#                     next_at = next_free_window_start
#                 status = True

#         else:
#             raise ValueError("Payment window operation type not matched.")

#         return status, next_at

    @staticmethod
    def is_in_payment_window(current_time: datetime, windows: list):
        start_time, end_time = None, None

        for window in windows:
            if window.start_time <= current_time.time() <= window.end_time:
                return True, None, datetime.combine(current_time.date(), window.end_time)

        # Find the next payment window's start time and end time
        if windows:
            next_window = min(
                (
                    (
                        datetime.combine(current_time.date(), window.start_time),
                        datetime.combine(current_time.date(), window.end_time),
                    )
                    for window in windows if window.start_time > current_time.time()
                ),
                default=(
                    datetime.combine(current_time.date() + timedelta(days=1), windows[0].start_time),
                    datetime.combine(current_time.date() + timedelta(days=1), windows[0].end_time),
                )
            )

            start_time = next_window[0]
            end_time = next_window[1]

        return False, start_time, end_time


    @staticmethod
    def check_payment_window(connect_parkinglot) -> dict:
        current_time = datetime.utcnow()
        overstay_limit = parkinglot_overstay_limit(connect_parkinglot, current_time)
        payment_windows = connect_parkinglot.parking_time_slots
        configured_time = timedelta(minutes=settings.VIOLATION_GRACE_PERIOD)
        window_operation_type = connect_parkinglot.parking_operations
        next_free_window_start = None

        if window_operation_type == ParkingOperations.paid_24_hours.value or window_operation_type == ParkingOperations.spot_based_24_hours_free_parking.value:
            status = True
            next_at = current_time + configured_time
            end_time = next_at + timedelta(hours=24)

        elif window_operation_type == ParkingOperations.lpr_based_24_hours_free_parking.value:
            status = False
            next_at = current_time + overstay_limit
            end_time = next_at + timedelta(hours=24)

        elif window_operation_type == ParkingOperations.specify_lpr_based_paid_parking_time.value:
            is_paid, next_window_start, current_window_end = ParkingWindow.is_in_payment_window(
                current_time, payment_windows
            )

            if not is_paid:  # Non-payment window
                if current_time + overstay_limit <= next_window_start:
                    next_at = current_time + overstay_limit
                else:
                    next_at = next_window_start
                status = False
                end_time = next_window_start
            else:  # Payment window
                # Find the next non-payment window's start time
                next_free_window_start = min(
                    (
                        datetime.combine(current_time.date(), window.end_time)
                        for window in payment_windows if window.end_time > current_time.time()
                    ),
                    default=datetime.combine(current_time.date() + timedelta(days=1), payment_windows[0].end_time)
                )

                if current_time + configured_time <= next_free_window_start:
                    next_at = current_time + configured_time
                else:
                    next_at = next_free_window_start
                status = True
                end_time = current_window_end

        else:
            raise ValueError("Payment window operation type not matched.")

        return {
            "status": status,
            "next_at": next_at,
            "end_time": end_time,
            "next_free_window_start": next_free_window_start
        }
