#!/usr/bin/env python

import copy
import heapq
import os
import sys
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
    def __init__(self, name, thing, start_after=0,
                 # May or may not be present in the config...
                 death_after=None, restart_delay=None):
        self.name = name
        self.path = thing['path']
        self.arguments = thing.get('arguments', [])
        self.program = [self.path] + self.arguments
        self.start_after = start_after
        self.death_after = death_after
        self.restart_delay = restart_delay
        self._process = None

    def _spawn(self):
        p = os.fork()
        if p == 0:
            try:
                arguments = list(self.arguments)
                arguments.insert(0, self.path)
                os.execv(self.path, arguments)
            except OSError as e:
                sys.stderr.write("!! Failed to spawn '%s'\n" % self.program)
                sys.stderr.write("!! %s\n" % e)
                sys.stderr.flush()
                os._exit(-1)
        else:
            return psutil.Process(p)

    def start(self):
        self._process = self._spawn()
        if self.death_after is not None:
            return (self.death_after, self.stop)
        else:
            return (10, self.dump_status)

    @property
    def pid(self):
        if self._process is None:
            return None
        else:
            return self._process.pid

    def dump_status(self):
        prog = " ".join(self.program)
        if self._process is None:
            status = "??"
        else:
            prog += " (%s)" % (self.pid)
            status = self._process.status()
        print("Status of %s is %s" % (prog, status))
        return (10, self.dump_status)

    def __repr__(self):
        p = self.pid
        prog = " ".join(self.program)
        if p is not None:
            return "<Binary '%s:%s'>" % (prog, p)
        else:
            return "<Binary '%s'>" % (prog)

    def stop(self, between_wait_for=0.01):
        if self._process is not None:
            if self._process.is_running():
                attempts = [self._process.terminate,
                            self._process.terminate,
                            self._process.kill]
                for func in attempts:
                    func()
                    try:
                        self._process.wait(timeout=between_wait_for)
                    except psutil.TimeoutExpired:
                        pass
                    if not self._process.is_running():
                        self._process = None
                        break
                if self._process is not None and self._process.is_running():
                    # Try again in a little bit...
                    return (1, self.stop)
            else:
                self._process = None
        if self.restart_delay is not None:
            return (self.restart_delay, self.start)
        else:
            return (None, None)


def build(what, now):
    bins = what.get('binaries', {})
    schedule = []
    binaries = []
    for name, item in six.iteritems(what.get('schedule', {})):
        thing = copy.deepcopy(bins[item.pop('binary')])
        arguments = thing.setdefault('arguments', [])
        arguments.extend(item.pop('arguments', []))
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
    try:
        while schedule:
            n = now()
            run_when, func, binary = heapq.heappop(schedule)
            action = func.__name__
            if run_when > n:
                when_go = run_when - n
                print("Sleeping for %0.2f seconds until next"
                      " scheduled trigger of %s (%s)" % (when_go,
                                                         binary.program,
                                                         action))
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
    except KeyboardInterrupt:
        for b in binaries:
            b.stop(between_wait_for=1.0)

if __name__ == '__main__':
    main()
