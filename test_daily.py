from datetime import datetime, timezone

from daily import wait_seconds


def at(h, m):
    return datetime(2026, 10, 3, h, m, tzinfo=timezone.utc)


assert wait_seconds(at(21, 30), "23:00") == 5400  # on time: wait out the buffer
assert wait_seconds(at(23, 40), "23:00") == 0     # late, same UTC day
assert wait_seconds(at(0, 34), "23:00") == 0      # late past UTC midnight (the 6h hang)
print("ok")
