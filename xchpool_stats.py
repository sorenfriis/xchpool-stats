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


def read_config():
    class config:
        pass

    cfg = config()
    dir = os.path.dirname(__file__)
    file = os.path.join(dir, 'config.json')
    with open(file, 'r') as f:
        data = json.load(f)
    cfg.launcher_id = data['launcher_id']
    if cfg.launcher_id == 'your-launcher-id':
        raise Error("Launcher ID not set in config.json")

    cfg.real_netspace = 1024**4 * float(data['real_netspace_tib'])

    return cfg


def get_json(url, timeout=5):
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != requests.codes.ok:
            raise Error(f"GET request failed: {url}")
        data = resp.json()
        return data
    except requests.exceptions.ConnectionError as e:
        raise Error(f'ConnectionError during GET from: {url}')
    except requests.exceptions.Timeout: 
        raise Error(f'Timeout during GET from: {url}')


def post_json(url, req_json, timeout=5):
    try:
        resp = requests.post(url=url, json=req_json, timeout=timeout)
        if resp.status_code != requests.codes.ok:
            raise Error(f"POST request failed: {url}")
        data = resp.json()
        return data
    except ConnectionError as e:
        raise Error(f'ConnectionError during POST to: {url}')
    except requests.exceptions.Timeout:
        raise Error(f'Timeout during POST to: {url}')


def get_xch_pr_tib():
    query = """
    {
        daily_stats(order_by: {date: desc}){
            date
            xch_per_tib
        }
    }
    """
    j = {
        "query": query
    }
    resp = post_json('https://api.xchscan.com/v1/graphql', req_json=j)
    data = resp['data']
    return data

def get_pool_stats():
    return get_json('https://api.xchpool.org/v1/poolstats')


def get_member_data(launcher_id):
    return get_json(f'https://api.xchpool.org/v1/members/get?search={launcher_id}')


def get_current_price():
    try:
        data = get_json('https://api.coingecko.com/api/v3/simple/price?ids=chia&vs_currencies=usd')
        price = float(data['chia']['usd'])
        return price
    except Error:
        pass
    
    try:
        data = get_json('https://xchscan.com/api/chia-price')
        price = float(data['usd'])
        return price
    except Error:
        raise 

def get_pool_share(memberdata):
    poolshare = float(memberdata['currentPoolShare'])
    return poolshare


def get_points(memberdata):
    points = int(memberdata['points'])
    return points


def get_earnings(memberdata):
    payouts = memberdata['payouts']
    earnings = payouts['earnings']
    return earnings

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


def colored_percentage(perc):
    perc_str = f'{perc:6.2f} %'
    if perc >= 100:
        return colored(perc_str, colored.GREEN)
    else:
        return colored(perc_str, colored.RED)

class stats:
    def __init__(self, price):
        self.price = price

    def print(self, n_days):
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

        real_netspace_str = format_bytes(self.real_netspace)
        member_netspace_str = format_bytes(self.member_netspace)
        if self.member_netspace >= self.real_netspace:
            member_netspace = colored(member_netspace_str, colored.GREEN)
        else:
            member_netspace = colored(member_netspace_str, colored.RED)

        payout_until_now_str = f'{self.payout_until_now:8.6f}'
        if self.payout_until_now >= self.expected_xch_pr_round:
            payout_until_now_str = colored(payout_until_now_str, colored.GREEN)

        expected_next_payout_str = f'{self.expected_next_payout:.6f}'
        if self.expected_next_payout >= self.expected_xch_pr_round:
            expected_next_payout_str = colored(expected_next_payout_str, colored.GREEN)
        else:
            expected_next_payout_str = colored(expected_next_payout_str, colored.RED)

        profitability_str = f'{self.profitability:.6f}'
        if self.profitability >= self.xch_pr_tib:
            profitability_str = colored(profitability_str, colored.GREEN)
        else:
            profitability_str = colored(profitability_str, colored.RED)

        print(f'Blocks ahead / behind      : {diff:8.2f} ({ahead_behind})')
        print('')
        print(f'Real netspace (from config): {real_netspace_str}')
        print(f'Estimated member netspace  : {member_netspace}')
        print(f'Points                     : {self.points:8}')
        print(f'Poolshare                  : {(self.poolshare*100):8.6f} %')
        print('')
        print(f'Current price              : {self.price:8.2f} USD / XCH')
        print(f'Next payout until now      : '
              f'{payout_until_now_str} XCH ({self.payout_until_now * self.price:.2f} USD)')
        print(f'Expected next payout       : '
              f'{expected_next_payout_str} XCH ({self.expected_next_payout * self.price:.2f} USD)')
        print(f'Estimated profitability    : {profitability_str} XCH / TiB')
        print('')
        print(f'Expected earning pr round  : {self.expected_xch_pr_round:8.6f} XCH / TiB')
        print(f'Expected profitability     : {self.xch_pr_tib:8.6f} XCH / TiB ({self.xch_pr_tib_date})')

        print('')
        n = n_days * 24//round_time_hours
        sum = 0
        for i in range(n):
            e = self.earnings[i]
            sum += e['amount']
        exp = self.expected_xch_pr_round * n
        perc = 100*sum / exp

        print(f'Last {n_days:2}d earnings          : '
              f'{sum:.12f} XCH ({sum * self.price:5.2f} USD)'
              f' ({colored_percentage(perc)})')

        for i in range(n):
            e = self.earnings[i]
            state = e["state"]
            transaction_id = e["transaction_id"]
            if state == "paid":
                paid = "("+transaction_id[:4]+")"
            else:
                paid = "(unpaid)"
            amount = e["amount"]
            perc = 100*amount / self.expected_xch_pr_round
            print(f'  {e["singleton"]:17s}{paid:8s}:'
                  f' {amount:.12f} XCH'
                  f' ({e["amount"] * self.price:5.2f} USD)'
                  f' ({colored_percentage(perc)})')

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


def xchpool_stats(cfg):
    member_data = get_member_data(cfg.launcher_id)
    pool_stats = get_pool_stats()
    price = get_current_price()
    xch_pr_tib_data = get_xch_pr_tib()
    xch_pr_tib_data_element = xch_pr_tib_data['daily_stats'][0]
    xch_pr_tib = xch_pr_tib_data_element['xch_per_tib'] * 7 / 8
    xch_pr_tib_date = xch_pr_tib_data_element['date']

    s = stats(price)
    s.xch_pr_tib = xch_pr_tib
    s.xch_pr_tib_date = xch_pr_tib_date
    s.expected_xch_pr_round = (cfg.real_netspace / 1024**4) * xch_pr_tib * round_time_hours / 24

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
    s.real_netspace = cfg.real_netspace
    s.payout_until_now = s.poolshare * s.blocks_this_round * 1.75

    time_remaining_days = 1 - (time_since_last_calc_secs / secs_pr_round)
    expected_remaining_payout = time_remaining_days * s.expected_blocks_this_round * 1.75 * s.poolshare
    s.expected_next_payout = s.payout_until_now + expected_remaining_payout
    s.profitability = 24/round_time_hours * 1024**4 * s.expected_next_payout / s.member_netspace
    s.earnings = get_earnings(member_data)
    return s


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract metrics from XCHPool and calculate expected next payout')
    parser.add_argument('--days', dest='days', help='Number of days to print')
    parser.add_argument('--log', dest='logfile', help='Log to LOGFILE')
    args = parser.parse_args()
    try:
        cfg = read_config()
        stats = xchpool_stats(cfg)
    except Error as e:
        print("Error:", e)
        sys.exit(1)

    days = int(args.days) if args.days else 7
    stats.print(days)

    if args.logfile:
        stats.log(args.logfile)
