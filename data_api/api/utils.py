from datetime import datetime

__author__ = 'kenneth'


def get_date_from_param(param):
    if len(param) != 8:
        raise RuntimeError("Wrong date format. Use: ddmmyyyy")
    return datetime(int(param[4:8]), int(param[2:4]), int(param[:2]))