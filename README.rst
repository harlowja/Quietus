-------
Quietus
-------

What
----

Death or something that causes death, regarded as a release from life.

Really what
-----------

A tiny Python program that can take files that define lifecycles of other
binaries via a simple `yaml`_ configuration file and attempts to
realize the lifecycle defined there-in.

It contains support for the following:

* Starting a process after a given amount of time.
* Stopping a started process after a given amount of time.
* Restarting a process after death.

It is meant to be able to easily define a set of binaries lifecycle together
for uses such as HA testing; or failover testing where having a repeatable
and easy to read lifecycle is key for continuous testing (and helps in
sharing those same lifecycles for others to test with).

.. _yaml: http://yaml.org/

