"""A bunch of functions that are used by multiple threads.
"""


import re
import subprocess


def split_size(content, size):
    total = len(content)
    bin_count = (total / size) + 1
    bins = [0] * bin_count
    for i in range(bin_count):
        bins[i] = content[i * size:(i + 1) * size]
    return bins


def kill_processes_using_ports(ports):
    popen = subprocess.Popen(['netstat', '-lpn'],
                             shell=False,
                             stdout=subprocess.PIPE)
    (data, err) = popen.communicate()
    pattern = "^tcp.*((?:{0})).* (?P<pid>[0-9]*)/.*$"
    pattern = pattern.format(')|(?:'.join(ports))
    prog = re.compile(pattern)
    for line in data.split('\n'):
        match = re.match(prog, line)
        if match:
            pid = match.group('pid')
            subprocess.Popen(['kill', '-9', pid])


def buffer_(str_to_pad, size):
    return str_to_pad.rjust(size, '0')
