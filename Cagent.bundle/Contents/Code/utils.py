from datetime import datetime

def get_date(s_date):
    date_patterns = ["%d.%m.%Y", "%Y %m %d", "%Y-%m-%d"]

    for pattern in date_patterns:
        try:
            return datetime.strptime(s_date, pattern).date()
        except:
            pass

    Log.Info("[" + utils + "] [get_date] Could not format date " + s_date)
    return None