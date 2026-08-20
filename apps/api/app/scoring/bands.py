from decimal import ROUND_HALF_UP, Decimal


def clamp_band(value: float) -> float:
    return max(0.0, min(9.0, float(value)))


def round_half_band(value: float) -> float:
    """Round to the nearest 0.5 using IELTS half-up rules (.25 → .5, .75 → next whole)."""
    doubled = Decimal(str(clamp_band(value))) * 2
    return float(doubled.to_integral_value(rounding=ROUND_HALF_UP) / 2)


def mean_band(values: list[float]) -> float:
    if not values:
        return 0.0
    average = sum(clamp_band(v) for v in values) / len(values)
    return round_half_band(average)


def combine_writing_bands(task1: float, task2: float) -> float:
    """Official-style Writing overall: Task 1 is one third, Task 2 is two thirds."""
    return round_half_band((clamp_band(task1) + 2.0 * clamp_band(task2)) / 3.0)
