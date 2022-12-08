import json
import random
import datetime
import pytz
from datetime import timedelta

MONTHS_STRING = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12}
MONTHS_NUMBER = {1 : "January", 2 : "February", 3 : "March", 4 : "April", 5 : "May", 6 : "June", 7 : "July", 8 : "August", 9  : "September", 10 : "October" , 11 : "November", 12 : "December"}

def check_answer(day, month, year, duration):
    if year == None:
        today = datetime.date.today()

        year = today.year
    return int(day) and MONTHS_STRING[month.lower()] and int(year) and int(duration)

def save_duration(duration):
    return int(duration)

def translate_to_datetime(day, month, year):
    print('translating...')
    print(day)
    print(month)
    print(year)
    datetime_object = datetime.datetime.strptime(month, "%B")
    month_number = datetime_object.month
    print(month_number)
    dt = datetime.datetime(int(year), int(month_number), int(day))
    return dt

def datetime_to_string(dt):
    date_time = dt.strftime("%m/%d/%Y")
    print("date and time:",date_time)
    return date_time

def int_to_str(duration):
    print('Int to str...')
    print(duration)
    duration_string = str(duration)
    return duration_string

def get_hour(user_time_zone):
    d = datetime.datetime.now(pytz.timezone(user_time_zone))
    return d.hour

def period_recorded(handler_input):
    """Función que enseña si ya tienes el periodo guardado."""
    # type: (HandlerInput) -> bool
    is_period_recorded = False
    session_attr = handler_input.attributes_manager.session_attributes

    if ("last_period" in session_attr):
        is_period_recorded = True

    return is_period_recorded

def translate_to_datetime_pill(hour):
    print('translating...')
    print(hour)
    print(month_number)
    dt = datetime.datetime(int(year), int(month_number), int(day))
    return dt

def check_time(time):
    print("HERE COMES THE TIME!!! -->",time)
    return time

def datetime_to_string_pill(dt):
    date_time_hour = dt.strftime("%H:%M")
    print("date and time:",date_time_hour)
    return date_time_hour

def string_to_datetime(sdt):
    print('THIS IS THE STRING DATETIME--->',sdt)
    date_time = datetime.datetime.strptime(sdt, "%m/%d/%Y")
    print("date and time converted:",date_time)
    return date_time

def calculate_next_period(period):
    next_period_date = period + timedelta(days=28)
    print('NEXT PERIOD INCOMING ---->',next_period_date)
    return next_period_date

def calculate_fertile_day(period):
    next_fertile_date = period + timedelta(days=14)
    print('FERTILE DAY INCOMING ---->',next_fertile_date)
    return next_fertile_date