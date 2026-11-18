# gta6-twitch-ccu-forecast-01

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/gusde2021/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/gusde2021/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Launch-day Twitch viewer forecaster (Python, standard library only) that reads a case file with hour 1 known plus history and comparable launches, builds a similarity-weighted median log-ratio curve from the comparables, and emits calibrated log-space quantiles for hours 2-24; cut mean pinball loss ~44% vs the persistence baseline in local cross-validation on the kit practice cases.

## Run it

```sh
python main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=9UreHffHnNFKPEc27LRb3tguq2QesRQ7P998xkC4Woz&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
