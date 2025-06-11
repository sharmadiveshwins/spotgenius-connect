from datetime import datetime
from fastapi import HTTPException

class SimulationUtils:
    def parse_tiba_datetime(date_str: str) -> datetime:
        try:
            return datetime.strptime(date_str, "%d-%m-%YT%H:%M:%S")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Expected format: d-m-yTH:m:s")

    @staticmethod
    def parse_valid_from(ValidFrom: str) -> datetime:
        return SimulationUtils.parse_tiba_datetime(ValidFrom)

    @staticmethod
    def parse_valid_to(ValidTo: str) -> datetime:
        return SimulationUtils.parse_tiba_datetime(ValidTo)
    
    @staticmethod
    def month_date_range():
        from datetime import datetime
        import calendar

        now = datetime.now()
        month_start_date = datetime(now.year, now.month, 1)
        month_end_date = datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1], 23, 59, 59)

        return {
            "start_date": month_start_date,
            "end_date": month_end_date
        }