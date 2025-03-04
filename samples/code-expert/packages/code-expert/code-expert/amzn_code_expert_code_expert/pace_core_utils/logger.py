# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

"""
This module contains the logger for the application.
It is configured to log at the INFO level by default.
It can be configured to log at a different level by setting the LOG_LEVEL environment variable.

After importing, set the name of the logger at the top of the file.
For example:

logger.name = "myapp"
"""

import logging
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

# reducing noise from logs, if you really need DEBUG level logs from these libraries, customize the levels below
logging.getLogger('boto').setLevel(logging.INFO)
logging.getLogger('boto3').setLevel(logging.INFO)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('s3transfer').setLevel(logging.WARNING)
