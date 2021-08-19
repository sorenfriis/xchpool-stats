#!/usr/bin/python3

import os
import sys
import requests
import json
from datetime import datetime, timedelta


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


def xchpool_stats(launcher_id):
    now = datetime.utcnow()
    last_calc_time = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if last_calc_time > now:
        one_day = timedelta(hours=24)
        last_calc_time -= one_day

    member_data = get_member_data(launcher_id)
    pool_stats = get_pool_stats()
    price = get_current_price()

    total_space = pool_stats['blockchainTotalSpace']
    pool_space = pool_stats['poolCapacityBytes']
    blocks_today = pool_stats['blocksFoundSofarToday']
    expected_blocks_today = 4608 * pool_space / total_space

    time_since_last_calc = now - last_calc_time
    time_since_last_calc_secs = time_since_last_calc.total_seconds()
    secs_pr_day = 24*60*60
    expected_blocks_now = expected_blocks_today * \
        time_since_last_calc_secs / secs_pr_day

    diff = blocks_today - expected_blocks_now
    if diff >= 0:
        ahead_behind = colored('ahead', colored.GREEN)
    else:
        ahead_behind = colored('behind', colored.RED)

    points = get_points(member_data)
    poolshare = get_pool_share(member_data)
    member_netspace = get_member_netspace(member_data)
    payout_until_now = poolshare * blocks_today * 1.75

    time_remaining_days = 1 - (time_since_last_calc_secs / secs_pr_day)
    expected_remaining_payout = time_remaining_days * expected_blocks_today * 1.75 * poolshare
    expected_next_payout = payout_until_now + expected_remaining_payout

    print(f'Total netspace             : {format_bytes(total_space)}')
    print(f'Pool space                 : {format_bytes(pool_space)}')

    print(f'Expected blocks today      : {expected_blocks_today:8.2f}')
    print(f'Expected blocks until now  : {expected_blocks_now:8.2f}')
    print(f'Actual blocks until now    : {blocks_today:8}')
    print(f'Blocks ahead / behind      : {diff:8.2f} ({ahead_behind})')
    print('')
    print(f'Points                     : {points:8}')
    print(f'Estimated member netspace  : {format_bytes(member_netspace)}')
    print(f'Poolshare                  : {(poolshare*100):8.6f} %')
    print('')
    print(f'Current price              : {price:8.2f} USD / XCH')
    print(
        f'Next payout until now      : {payout_until_now:8.6f} XCH ({payout_until_now*price:.2f} USD)')
    print(
        f'Expected next payout       : {expected_next_payout:8.6f} XCH ({expected_next_payout*price:.2f} USD)')


if __name__ == "__main__":
    try:
        launcher_id = read_launcher_id()
        xchpool_stats(launcher_id)
    except Error as e:
        print("Error:", e)
        sys.exit(1)