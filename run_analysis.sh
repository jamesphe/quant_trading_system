#!/bin/bash
source ~/anaconda3/etc/profile.d/conda.sh
conda activate quant
python /Users/james/private/Back-trader/quant_trading_system/portfolio_analysis.py >> /Users/james/private/Back-trader/quant_trading_system/logfile.log 2>&1