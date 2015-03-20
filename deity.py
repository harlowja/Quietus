#!/usr/bin/env python

import heapq
import os
import sys
import threading
import time

try:
    from time import monotonic as now
except ImportError:
    from time import time as now

import argparse
import psutil
import yaml
import six

from quietus import util


class Binary(object):
    def __init__(self, name, target, start_after,
                 # May or may not be present in the config...
                 death_after=None, restart_after=None):
        self.name = name
        program = [target['location']] + target.get('arguments', [])
        self.program = program
        self.start_after = start_after
        self.death_after = death_after
        self.restart_after = restart_after
        self._process = None

    def start(self):
        if self.death_after is not None:
            return (self.death_after, self.stop)
        else:
            return (10, self.no_op)

    @property
    def pid(self):
        if self._process is None:
            return None
        else:
            return self._process.pid

    def no_op(self):
        return (10, self.check)

    def __repr__(self):
        p = self.pid
        prog = " ".join(self.program)
        if p is not None:
            return "<Binary '%s:%s'>" % (prog, p)
        else:
            return "<Binary '%s'>" % (prog)

    def stop(self, between_wait_for=0.001):
        if self._process is not None:
            if self._process.is_running():
                for f in [self._process.terminate,
                          self._process.terminate,
                          self._process.kill]:
                    f()
                    self._process.wait(timeout=between_wait_for)
                    if not self._process.is_running():
                        self._process = None
                        break
            else:
                self._process = None
        if self.restart_after is not None:
            return (self.restart_after, self.start)
        else:
            return (None, None)


def build(what, now):
    bins = what.get('binaries', {})
    schedule = []
    binaries = []
    for name, item in six.iteritems(what.get('schedule', {})):
        thing = bins[item.pop('binary')]
        b = Binary(name, thing, **item)
        binaries.append(b)
    for b in binaries:
        heapq.heappush(schedule, (b.start_after + now, b.start, b))
    return binaries, schedule


def dump_schedule(schedule):
    schedule = list(schedule)
    n = now()
    print("-- Schedule --")
    while schedule:
        run_when, func, binary = heapq.heappop(schedule)
        action = func.__name__
        delay_to = max(0, run_when - n)
        print("Run what: %s (%s)" % (binary.program, action))
        print(" - Expected next run in %0.2f seconds" % (delay_to))


def main():
    what = util.load_yaml(sys.argv[1])
    started_at = now()
    binaries, schedule = build(what, started_at)
    cond = threading.Condition()
    while schedule:
        n = now()
        run_when, func, binary = heapq.heappop(schedule)
        action = func.__name__
        if run_when > n:
            when_go = run_when - n
            print("Sleeping for %0.2f seconds until next"
                  " scheduled trigger of %s (%s)" % (when_go,
                                                     binary.program, action))
            heapq.heappush(schedule, (run_when, func, binary))
            dump_schedule(schedule)
            time.sleep(when_go)
        else:
            print("Running scheduled trigger of %s (%s)" % (binary.program,
                                                            action))
            next_up, followup_func = func()
            if followup_func is not None and next_up is not None:
                run_when = now() + next_up
                heapq.heappush(schedule, (run_when, followup_func, binary))


if __name__ == '__main__':
    main()
