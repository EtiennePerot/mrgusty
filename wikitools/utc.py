import datetime
ZERO = datetime.timedelta(0)
class UTC(datetime.tzinfo):
    """UTC

    Identical to the reference UTC implementation given in Python docs except
    that it unpickles using the single module global instance defined beneath
    this class declaration.

    Also contains extra attributes and methods to match other pytz tzinfo
    instances.
    """
    zone = "UTC"

    _utcoffset = ZERO
    _dst = ZERO
    _tzname = zone

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

    def __reduce__(self):
        return UTC, ()

    def localize(self, dt, is_dst=False):
        '''Convert naive time to local time'''
        if dt.tzinfo is not None:
            raise ValueError, 'Not naive datetime (tzinfo is already set)'
        return dt.replace(tzinfo=self)

    def normalize(self, dt, is_dst=False):
        '''Correct the timezone information on the given datetime'''
        if dt.tzinfo is None:
            raise ValueError, 'Naive time - no tzinfo set'
        return dt.replace(tzinfo=self)

    def __repr__(self):
        return "<UTC>"

    def __str__(self):
        return "UTC"
utc = UTC()