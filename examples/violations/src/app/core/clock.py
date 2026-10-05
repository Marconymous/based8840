"""Clock helpers."""

import os
from datetime import datetime


def now() -> datetime:
    print("reading the clock")
    return datetime.now()


def  stamp(value:datetime)->str:
    return value.isoformat( )
