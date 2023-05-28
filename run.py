import requests
import datetime
from dateutil.relativedelta import relativedelta
from pycoingecko import CoinGeckoAPI

# List of validator indexes
validators = [1]

tax_year = 2022

mgno_decimals = 9

# The API at beacon.gnosischain.com returns data with a "day index" which starts at 0.
# Day 0 is the day of the beacon chain genesis, which was Dec 8, 2021 (Epoch 1638993340).

# Translate start and end date to "day index"

start_date = datetime.date(tax_year,1,1)
end_date = datetime.date(tax_year,12,31)
genesis_date = datetime.date(2021,12,8)

start_day_index = (start_date - genesis_date).days
end_day_index = (end_date - genesis_date).days

# Rewards are aggregated by month
rewards = [0 for i in range(12)]

for v in validators:
    path = 'https://beacon.gnosischain.com/api/v1/validator/stats/{}'.format(v)
    response = requests.get(path)

    if not response.status_code == 200:
        raise Exception('Unable to load: {}\nStatus code: {}'.format(path,response.status_code))
    
    response_status = response.json()['status']

    if not response_status == 'OK':
        raise Exception('Unable to load: {}\nStatus: {}'.format(path, response_status))

    data = response.json()['data']

    for day in reversed(data):  # Reversed to iterate through the days from oldest to most recent.
        day_index = day['day']
        if (day_index < start_day_index) or (day_index > end_day_index):
            continue

        end_balance = day['end_balance'] / (10**mgno_decimals)
        is_deposit_day = (day['start_balance'] == 0 and end_balance > 0)

        balance_change = end_balance - day['start_balance'] / (10**mgno_decimals)
        if is_deposit_day:
            # we don't want the deposit t show up, it's added manually in koinly.
            balance_change -= 32

        day_date = genesis_date + datetime.timedelta(days=day_index)

        rewards[day_date.month - 1] += balance_change

# Output
# https://help.koinly.io/en/articles/3662999-how-to-create-a-custom-csv-file-with-your-data    
print('Koinly Date,Amount,Currency,Label,Description,Net Worth Amount,Net Worth Currency')

cg = CoinGeckoAPI()

for i,reward in enumerate(rewards):
    if reward == 0:
        continue
    
    date = datetime.date(tax_year,i + 1,1)
    # get the last day of that month.
    date = date + relativedelta(months=+1) - datetime.timedelta(days=1) 
    
    koinly_date = date.strftime('%Y-%m-%d 23:59 UTC')  # we hardcode 1 min before midnight
    koinly_amount = reward
    koinly_label = 'reward' if reward > 0 else 'cost'
    koinly_description = 'penalty' if reward < 0 else ''

    gno_coingecko = cg.get_coin_history_by_id(id='gnosis', date=date.strftime('%d-%m-%Y'))
    gno_price = gno_coingecko['market_data']['current_price']['eur']
    koinly_price = reward * gno_price / 32

    print('{},{},MGNO,{},{},{},EUR'.format(koinly_date, koinly_amount, koinly_label, koinly_description, koinly_price))
