from collections import namedtuple

history_price_group = namedtuple(
    "history_price_group",
    [
        "weekly_52_high",
        "weekly_52_low",
        "gap_from_the_last_high",
        "break_high",
        "break_low",
        "break_high_today",
        "big_volume",
        "above_all_moving_avg_line",
        "weekly_change",
        "yearly_change"
    ],
)

sliced_candle_info = namedtuple(
    "sliced_candle_info",
    [
        "opens",
        "closes",
        "lows",
        "highs",
        "volumes",
        "timestamps",
        "this_week",
        "today",
    ],
)

class market_group:
    def __init__(self) -> None:
        self.industry = {}
        self.max_ath = "n/a"
        self.max_atl = "n/a"
        self.ath_count = 0
        self.atl_count = 0

    def __repr__(self) -> str:
        return f"max_ath : {self.max_ath} , max_atl : {self.max_atl} , ath_count : {self.ath_count} , atl_count : {self.atl_count}"


class industry_group:
    def __init__(self) -> None:
        self.stock = {}
        self.ath_count = 0
        self.atl_count = 0
        self.week_change_avg = 0
        self.break_high_group = []
        self.break_low_group = []
        self.approach_high = []

    def __repr__(self) -> str:
        return f"break_high_group : {self.break_high_group} , break_low_group : {self.break_low_group} , approach_high : {self.approach_high} , ath_count : {self.ath_count} , atl_count : {self.atl_count}"
