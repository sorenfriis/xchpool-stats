#!/usr/bin/python3

import os
import sys
import requests
import json
from datetime import datetime, timedelta
import argparse

round_time_hours = 6

class Error(Exception):
    pass


class colored:
    GREEN = '\033[1;32;48m'
    RED = '\033[1;31;48m'
    END = '\033[1;37;0m'

    def __init__(self, string, color):
        self.color = color
        self.string = string

    def __str__(self):
        return self.color + self.string + colored.END


def read_launcher_id():
    dir = os.path.dirname(__file__)
    file = os.path.join(dir, 'config.json')
    with open(file, 'r') as f:
        data = json.load(f)
    launcher_id = data['launcher_id']
    if launcher_id == 'your-launcher-id':
        raise Error("Launcher ID not set in config.json")
    return launcher_id


def get_json(url):
    resp = requests.get(url)
    if resp.status_code != requests.codes.ok:
        raise Error(f"GET request failed: {url}")
    data = resp.json()
    return data


def get_pool_stats():
    return get_json('https://api.xchpool.org/v1/poolstats')


def get_member_data(launcher_id):
    return get_json(f'https://api.xchpool.org/v1/members/get?search={launcher_id}')


def get_current_price():
    data = get_json('https://api.chiaprofitability.com/market')
    return float(data['price'])


def get_pool_share(memberdata):
    poolshare = float(memberdata['currentPoolShare'])
    return poolshare


def get_points(memberdata):
    points = int(memberdata['points'])
    return points


def get_last_earnings(memberdata, n):
    payouts = memberdata['payouts']
    earnings = payouts['earnings']
    result = []
    for i in range(n):
        result.append(earnings[i])
    return result

def get_member_netspace(memberdata):
    netspace = int(memberdata['netspace'])
    return netspace


def format_bytes(bytes):
    exa = 1024**6
    peta = 1024**5
    tera = 1024**4
    giga = 1024**3
    mega = 1024**2
    kilo = 1024
    if bytes >= exa:
        return f'{bytes / exa:8.2f} EiB'
    if bytes >= peta:
        return f'{bytes / peta:8.2f} PiB'
    if bytes >= tera:
        return f'{bytes / tera:8.2f} TiB'
    if bytes >= giga:
        return f'{bytes / giga:8.2f} GiB'
    if bytes >= mega:
        return f'{bytes / mega:8.2f} MiB'
    if bytes >= kilo:
        return f'{bytes / kilo:8.2f} KiB'
    return f'{bytes} B'


class stats:
    def __init__(self, price):
        self.price = price

    def print(self):
        print(f'Total netspace             : {format_bytes(self.total_space)}')
        print(f'Pool netspace              : {format_bytes(self.pool_space)}')
        print(f'Expected blocks this round : {self.expected_blocks_this_round:8.2f}')
        print(f'Expected blocks until now  : {self.expected_blocks_now:8.2f}')
        print(f'Actual blocks until now    : {self.blocks_this_round:8}')

        diff = self.blocks_this_round - self.expected_blocks_now
        if diff >= 0:
            ahead_behind = colored('ahead', colored.GREEN)
        else:
            ahead_behind = colored('behind', colored.RED)

        print(f'Blocks ahead / behind      : {diff:8.2f} ({ahead_behind})')
        print('')
        print(f'Points                     : {self.points:8}')
        print(f'Estimated member netspace  : {format_bytes(self.member_netspace)}')
        print(f'Poolshare                  : {(self.poolshare*100):8.6f} %')
        print('')
        print(f'Current price              : {self.price:8.2f} USD / XCH')
        print(f'Next payout until now      : '
              f'{self.payout_until_now:8.6f} XCH ({self.payout_until_now * self.price:.2f} USD)')
        print(f'Expected next payout       : '
              f'{self.expected_next_payout:8.6f} XCH ({self.expected_next_payout * self.price:.2f} USD)')
        print(f'Estimated profitability    : {self.profitability:8.6f} XCH / TiB')

        print('')
        sum = 0
        for i in range(4):
            e = self.last_4_earnings[i]
            sum += e['amount']
        print(f'Last earnings              : {sum:8.6f} XCH ({sum * self.price:.2f} USD)')

        for i in range(4):
            e = self.last_4_earnings[i]
            print(f'  {e["singleton"]:25s}: {e["amount"]:8.6f} XCH ({e["amount"] * self.price:.2f} USD)')

    def log(self, file):
        if not os.path.isfile(file):
            header = [
                'Time',
                'Total netspace',
                'Pool netspace',
                'Expected blocks this round',
                'Expected blocks until now',
                'Actual blocks until now',
                'Ahead / behind',
                'Points',
                'Estimated member netspace',
                'Poolshare',
                'Current price',
                'Next payout until now',
                'Expected next payout'
            ]
            with open(file, 'w') as f:
                f.writelines(h + ';' for h in header)
                f.write('\n')

        data = [
            self.time,
            self.total_space,
            self.pool_space,
            self.expected_blocks_this_round,
            self.expected_blocks_now,
            self.blocks_this_round,
            self.blocks_this_round - self.expected_blocks_now,
            self.points,
            self.member_netspace,
            self.poolshare,
            self.price,
            self.payout_until_now,
            self.expected_next_payout
        ]
        with open(file, 'a') as f:
            f.writelines(str(d) + ';' for d in data)
            f.write('\n')


def xchpool_stats(launcher_id):
    member_data = get_member_data(launcher_id)
    pool_stats = get_pool_stats()
    price = get_current_price()

    s = stats(price)
    s.total_space = pool_stats['blockchainTotalSpace']
    s.pool_space = pool_stats['poolCapacityBytes']
    s.blocks_this_round = pool_stats['blocksFoundSofarToday']
    s.expected_blocks_this_round = 4608 * round_time_hours/24 * s.pool_space / s.total_space

    now = datetime.utcnow()
    s.time = int(now.timestamp())
    last_calc_hour = round_time_hours * (now.hour // round_time_hours)
    last_calc_time = now.replace(hour=last_calc_hour, minute=0, second=0, microsecond=0)

    if last_calc_time > now:
        one_round = timedelta(hours=round_time_hours)
        last_calc_time -= one_round

    time_since_last_calc = now - last_calc_time
    time_since_last_calc_secs = time_since_last_calc.total_seconds()
    secs_pr_round = round_time_hours * 60 * 60
    s.expected_blocks_now = s.expected_blocks_this_round * time_since_last_calc_secs / secs_pr_round

    s.points = get_points(member_data)
    s.poolshare = get_pool_share(member_data)
    s.member_netspace = get_member_netspace(member_data)
    s.payout_until_now = s.poolshare * s.blocks_this_round * 1.75

    time_remaining_days = 1 - (time_since_last_calc_secs / secs_pr_round)
    expected_remaining_payout = time_remaining_days * s.expected_blocks_this_round * 1.75 * s.poolshare
    s.expected_next_payout = s.payout_until_now + expected_remaining_payout
    s.profitability = 24/round_time_hours * 1024**4 * s.expected_next_payout / s.member_netspace
    s.last_4_earnings = get_last_earnings(member_data, 4)
    return s


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract metrics from XCHPool and calculate expected next payout')
    parser.add_argument('--log', dest='logfile', help='Log to LOGFILE')
    args = parser.parse_args()
    try:
        launcher_id = read_launcher_id()
        stats = xchpool_stats(launcher_id)
    except Error as e:
        print("Error:", e)
        sys.exit(1)

    stats.print()
    if args.logfile:
        stats.log(args.logfile)
