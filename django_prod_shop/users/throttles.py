from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class BurstRateUserThrottle(UserRateThrottle):
    scope = 'user_burst'


class SustainedRateUserThrottle(UserRateThrottle):
    scope = 'user_sustained'


class BurstRateAnonThrottle(AnonRateThrottle):
    scope = 'anon_burst'


class SustainedRateAnonThrottle(AnonRateThrottle):
    scope = 'anon_sustained'
