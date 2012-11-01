#!/usr/bin/env python2

"""
A service that does nothing at all but block.
Running this will keep the session alive even if all
other services manage to crash at the same time
"""
import time
# There should be a nicer way for this, but this
# should suffice
while True:
	time.sleep(10**6)
