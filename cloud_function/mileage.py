import math


YDS_TO_CHN = 0.0454545
YDS_TO_MIL = 0.000568182

class Mileage:
    """
    How to use:
    ==========
    ```ge
    print(Mileage(149.088).miles_decimal)
    > 149.5
    ```
    """

    def __str__(self):
        # return f"Miles (float): {self.miles_decimal}, Miles (int): {self.miles}, Yards: {self.yards}, Chains: {self.chains}"
        return f"{self.miles_decimal}"

    def __init__(self, miles_yards=0):
        self.miles = 0
        self.chains = 0
        self.yards = 0
        self.miles_decimal = 0

        self.define_from_miles_yards(miles_yards)

    def define_from_miles_yards(self, miles_yards):
        if miles_yards < 0:
            self.miles = math.ceil(miles_yards)
        else:
            self.miles = math.floor(miles_yards)

        self.yards = (miles_yards - self.miles) * 10000
        self.chains = YDS_TO_CHN * self.yards
        self.miles_decimal = self.miles + self.yards * YDS_TO_MIL