# iPortfolio

## Overview
This project aims to track and visualize the performance of a portfolio overtime by plotting the profit/loss curve based on local transaction data. 

## Features
- **Transactions Management**: Read transactions from a local CSV file and store them in a database for efficient querying and processing.

## Prerequisite
1. Create `transaction` directory
 ```
transactions/
  - exchange1/
    - stock1.csv
    - stock2.csv
  - exchange2/
    - stock1.csv
    - stock2.csv
  - cash/
    - cash.csv
 ```

2. All transactions MUST be formatted as
```
YYYY-MM-DD,STOCK,COST,QUANTITY
```

e.g.

```2024-10-01,MSFT,4206.9,10.00``` means buying 10 shares of MSFT at 2024-10-01, cost 4206.9 dollars

```2024-11-21,MSFT,-2064.35,-5.00``` means selling 5 shares of MSFT at 2024-11-21, earn 2064.35 dollars

```2025-03-13,MSFT,-83.00,0``` means receiving 83 dollars dividends from MSFT at 2025-03-13

## Execute 
`docker-compose build`

`docker-compose up -d`

`docker-compose exec app /bin/bash`

`./app.py`

## TODO  
1. Total period should be the holding period. e.g. holding stock A from day1 to day10, and then from day100 to day110. Then total period should be 20 days, instead of 110 days. 