#!/usr/bin/env python3
import os

import aws_cdk as cdk

from bin.llamaindex_basic_data_loader_stack import LlamaindexBasicDataLoaderStack


app = cdk.App()
LlamaindexBasicDataLoaderStack(app, "LlamaindexBasicDataLoaderStack",
)

app.synth()
