# Copyright 2017 QuantRocket LLC - All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from moonshot import Moonshot
from moonshot.commission import PerShareCommission

class UpMinusDown(Moonshot):
    """
    Strategy that buys recent winners and sells recent losers.

    Specifically:

    - rank stocks by their performance over the past MOMENTUM_WINDOW days
    - ignore very recent performance by excluding the last RANKING_PERIOD_GAP
    days from the ranking window (as commonly recommended for UMD)
    - buy the TOP_N_PCT percent of highest performing stocks and short the TOP_N_PCT
    percent of lowest performing stocks
    - rebalance the portfolio according to REBALANCE_INTERVAL
    """

    CODE = "umd"
    MOMENTUM_WINDOW = 252 # rank by twelve-month returns
    RANKING_PERIOD_GAP = 22 # but exclude most recent 1 month performance
    LOOKBACK_WINDOW = MOMENTUM_WINDOW # tell Moonshot how much data to fetch prior to the desired start date
    TOP_N_PCT = 10 # Buy/sell the top/bottom decile
    REBALANCE_INTERVAL = "M" # M = monthly; see http://pandas.pydata.org/pandas-docs/stable/timeseries.html#offset-aliases

    def get_signals(self, prices):
        closes = prices.loc["Close"]

        # Calculate the returns
        returns = closes.shift(self.RANKING_PERIOD_GAP)/closes.shift(self.MOMENTUM_WINDOW) - 1

        # Rank the best and worst
        top_ranks = returns.rank(axis=1, ascending=False, pct=True)
        bottom_ranks = returns.rank(axis=1, ascending=True, pct=True)

        top_n_pct = self.TOP_N_PCT / 100

        # Get long and short signals and convert to 1, 0, -1
        longs = (top_ranks <= top_n_pct)
        shorts = (bottom_ranks <= top_n_pct)

        longs = longs.astype(int)
        shorts = -shorts.astype(int)

        # Combine long and short signals
        signals = longs.where(longs == 1, shorts)

        # Resample using the rebalancing interval.
        # Keep only the last signal of the month, then fill it forward
        signals = signals.resample(self.REBALANCE_INTERVAL).last()
        signals = signals.reindex(closes.index, method="ffill")

        return signals

    def allocate_weights(self, signals, prices):
        weights = self.allocate_equal_weights(signals)
        return weights

    def simulate_positions(self, weights, prices):
        # Enter the position in the period/day after the signal
        return weights.shift()

    def simulate_gross_returns(self, positions, prices):
        # We'll enter on the open, so our return is today's open to
        # tomorrow's open
        opens = prices.loc["Open"]
        gross_returns = opens.pct_change() * positions.shift()
        return gross_returns

class USStockCommission(PerShareCommission):
    IB_COMMISSION_PER_SHARE = 0.005

class UpMinusDownAmex(UpMinusDown):

    CODE = "umd-amex"
    DB = "amex-1d"
    COMMISSION_CLASS = USStockCommission
