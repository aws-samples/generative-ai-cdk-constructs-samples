# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

class RetryableError(Exception):
    pass


class RateLimitError(Exception):
    pass


class ModelResponseError(RetryableError):
    pass


class ModelResponseWarning(UserWarning):
    pass


class MaxTokensExceeded(Exception):
    pass
