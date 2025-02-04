/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
 * Licensed under the Amazon Software License  http://aws.amazon.com/asl/
 */

import { aws_s3 as s3, Duration, RemovalPolicy, Stack } from "aws-cdk-lib";
import { Construct } from "constructs";

export class AccessLogsBucket {
  public static getLogsBucket(
    scope: Construct,
    constructId: string = "AccessLogsBucket",
  ): s3.Bucket {
    if (!AccessLogsBucket.bucket) {
      AccessLogsBucket.bucket = new s3.Bucket(Stack.of(scope), constructId, {
        versioned: true,
        removalPolicy: RemovalPolicy.RETAIN, // Retain logs even if stack is destroyed
        objectOwnership: s3.ObjectOwnership.BUCKET_OWNER_PREFERRED,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        encryption: s3.BucketEncryption.S3_MANAGED,
        enforceSSL: true,
        lifecycleRules: [
          {
            enabled: true,
            expiration: Duration.days(365), // Adjust retention period as needed
          },
        ],
      });
    }
    return AccessLogsBucket.bucket;
  }

  private static bucket: s3.Bucket;

  private constructor() {} // Prevent direct instantiation
}

export class SecureBucket extends s3.Bucket {
  constructor(scope: Construct, id: string, props: s3.BucketProps) {
    const accessLogsBucket = AccessLogsBucket.getLogsBucket(scope);
    super(scope, id, {
      versioned: true,
      serverAccessLogsBucket: accessLogsBucket,
      serverAccessLogsPrefix: `${id}/`,
      removalPolicy: RemovalPolicy.DESTROY,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      lifecycleRules: [
        {
          enabled: true,
          expiration: Duration.days(90),
        },
      ],
      objectOwnership: s3.ObjectOwnership.BUCKET_OWNER_PREFERRED,
      ...props,
    });
  }
}
