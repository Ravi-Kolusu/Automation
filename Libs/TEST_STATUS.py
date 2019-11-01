
"""
from UniAutos.Util.TestStatus import TEST_STATUS

Function: Define test run status

Copyright Information: Huawei Technologies Co., Ltd., Copyright (C) 2014-2015.

"""


class TEST_STATUS(object):
"""State definition"""
RUNNING = 'Running'
COMPLETE = 'Complete'
PASS = 'Pass'
FAILED = 'Fail'
INCOMPLETE = 'Incomplete'
NOT_RUN = 'NotRun'
CONFIG_ERROR = 'ConfigError'
CONFIGURED = 'Configured'
KILLED = 'Kill'
DE_CONFIGURED = 'deConfigured'

# Status list definition.
STATUS_UNITS = (TEST_STATUS.RUNNING, TEST_STATUS.COMPLETE, TEST_STATUS.PASS, TEST_STATUS.FAILED,
TEST_STATUS.INCOMPLETE, TEST_STATUS.NOT_RUN, TEST_STATUS.CONFIG_ERROR,
TEST_STATUS.CONFIGURED, TEST_STATUS.KILLED, TEST_STATUS.DE_CONFIGURED)
