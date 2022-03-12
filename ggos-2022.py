import datetime
import os
import pathlib
import platform
import random
import re
import threading
import time
import traceback

import requests
from torpy import TorClient
from torpy.http.adapter import TorHttpAdapter

from params import *

line_separator = '\n\n' + '-' * 64 + '\n\n'


class SiteThread(threading.Thread):
    def __init__(self, url):
        threading.Thread.__init__(self)
        self.url = url
        self.counter = 0
        self.exceptions_counter = 0
        self.current_exceptions_counter = 0

    def run(self):
        time.sleep(random.random() * len(list_of_target_sites) * 5)

        log_file_path = '{}/{}.txt'.format(
            pathlib.Path(__file__).parent / 'logs',
            replace_bad_symbols(self.url)
        )
        with open(log_file_path, 'w') as handler:
            handler.write('')

        while True:
            try:
                with TorClient() as tor:
                    with tor.get_guard() as guard:
                        adapter = TorHttpAdapter(guard, 3, retries=1)
                        with requests.Session() as s:
                            s.headers.update({'User-Agent': 'Mozilla/5.0'})
                            s.mount('http://', adapter)
                            s.mount('https://', adapter)

                            while True:
                                r = s.get(self.url, timeout=5)
                                webpage_code = r.text

                                if write_webpage_code_to_log_file:
                                    with open(log_file_path, 'a') as handler:
                                        info = '{}\n' \
                                               '\n' \
                                               'webpage code:\n' \
                                               '\n' \
                                               '{}' \
                                               '{}'.format(
                                            datetime.datetime.utcnow(),
                                            webpage_code,
                                            line_separator
                                        )
                                        handler.write(info)

                                self.counter += 1
                                self.current_exceptions_counter = 0

                                time.sleep(sleep_after_success_request)

            except Exception as exc:
                self.exceptions_counter += 1
                self.current_exceptions_counter += 1

                with open(log_file_path, 'a') as handler:
                    info = '{}\n\n{}{}'.format(
                        datetime.datetime.utcnow(),
                        '{}: {}'.format(exc.__class__.__name__, exc),
                        line_separator
                    )
                    handler.write(info)

                time.sleep(2 ** self.current_exceptions_counter)


def replace_bad_symbols(string):
    characters_list = ['/', '\\']

    for char in characters_list:
        string = string.replace(char, '_')

    return string


def clean_logs_directory():
    gag = (pathlib.Path(__file__).parent / 'logs').glob('*')

    gag = list(gag)

    for i in gag:
        if i.is_file():
            i.unlink()


def get_list_of_target_sites():
    ### via file

    filepath = pathlib.Path(__file__).parent / 'target_sites.txt'

    with open(filepath, 'r') as handler:
        text = handler.read()

    ### via github

    # gag = 'https://raw.githubusercontent.com/natiarr/target_sites_list/main/target_sites_list.txt'
    #
    # req = urllib.request.Request(gag, headers={'User-Agent': 'Mozilla/5.0'})
    # with urllib.request.urlopen(req) as response:
    #     text = response.read().decode()

    ###

    gag = text.strip()
    gag = re.split('\n+', gag)
    gag = [i.strip() for i in gag if i.strip() and i.strip()[0] != '#']
    gag = sorted(gag)

    return gag


def clear_screen():
    if os.name in ('linux', 'osx', 'posix'):
        os.system('clear')
    elif os.name in ('nt', 'dos'):
        os.system('cls')
    else:
        print('Cannot clear screen. Unsupported OS.')
        print(line_separator)


def gaga():
    start_time = datetime.datetime.utcnow()
    start_time = start_time.replace(microsecond=0)

    clean_logs_directory()

    global list_of_target_sites
    list_of_target_sites = get_list_of_target_sites()

    max_site_length = len('changes from latest update:')
    for site in list_of_target_sites:
        if len(site) + len('""') > max_site_length:
            max_site_length = len(site) + len('""')

    template = '%{0}s%{1}s%{2}s%{2}s'.format(
        max_site_length,
        12,
        9
    )

    changing_template = '%{0}s%+{1}d%+{2}d%+{2}d'.format(
        max_site_length,
        12,
        9
    )

    list_of_threads = []
    for site_url in list_of_target_sites:
        thread = SiteThread(site_url)
        list_of_threads.append(thread)
        thread.start()

    previous_counter_sum = 0
    previous_current_exceptions_counter_sum = 0
    previous_exceptions_counter_sum = 0
    counter_sum = 0
    current_exceptions_counter_sum = 0
    exceptions_counter_sum = 0

    while True:
        info = ''

        current_time = datetime.datetime.utcnow().replace(microsecond=0)

        info += 'working {} ({} seconds)'.format(
            current_time - start_time,
            int(current_time.timestamp() - start_time.timestamp())
        )

        info += '\n' * 2
        info += 'last updated {}'.format(current_time.time())
        info += '\n' * 2
        info += '{} target sites:'.format(len(list_of_target_sites))
        info += '\n' * 2

        for thread in list_of_threads:
            counter_sum += thread.counter
            current_exceptions_counter_sum += thread.current_exceptions_counter
            exceptions_counter_sum += thread.exceptions_counter

        info += changing_template % (
            'changes from latest update:',
            counter_sum - previous_counter_sum,
            current_exceptions_counter_sum - previous_current_exceptions_counter_sum,
            exceptions_counter_sum - previous_exceptions_counter_sum
        )
        info += '\n' * 2

        previous_counter_sum = counter_sum
        previous_current_exceptions_counter_sum = current_exceptions_counter_sum
        previous_exceptions_counter_sum = exceptions_counter_sum
        counter_sum = 0
        current_exceptions_counter_sum = 0
        exceptions_counter_sum = 0

        for thread in list_of_threads:
            info_line = template % (
                '"{}"{}'.format(
                    thread.url,
                    (max_site_length - (len(thread.url) + len('""'))) * ' '
                ),
                thread.counter,
                thread.current_exceptions_counter,
                thread.exceptions_counter
            )
            info += info_line + '\n'

        info += '\n' * 2

        clear_screen()
        print(info)

        time.sleep(screen_update_period)


try:
    gaga()
except:
    traceback.print_exc()
    input()
