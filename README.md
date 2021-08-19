# xchpool-stats
Extract metrics from [XCHPool](https://xchpool.org) API and calculate next expected payout.

## Prerequisites
Add your Launcher ID to `config.json`. \
(Your Launcher ID can be read by running `chia plotnft show`)


## Usage
```
python3 xchpool_stats.py
```

## Example output
```
Total netspace             :    34.01 EiB
Pool space                 :   292.41 PiB
Expected blocks today      :    38.69
Expected blocks until now  :    11.11
Actual blocks until now    :       11
Blocks ahead / behind      :    -0.11 (behind)

Points                     :     3128
Estimated member netspace  :    40.80 TiB
Poolshare                  : 0.010345 %

Current price              :   247.09 USD / XCH
Next payout until now      : 0.001991 XCH (0.49 USD)
Expected next payout       : 0.006985 XCH (1.73 USD)
```
