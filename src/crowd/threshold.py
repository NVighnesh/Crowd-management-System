class ThresholdEngine:

    def evaluate(self, count: int, threshold: int) -> str:

        if count < threshold:
            return "GREEN"

        if count == threshold:
            return "YELLOW"

        return "RED"