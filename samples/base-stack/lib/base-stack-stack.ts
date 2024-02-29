import { Duration, Stack, StackProps } from 'aws-cdk-lib';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subs from 'aws-cdk-lib/aws-sns-subscriptions';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';

import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';

export class BaseStackStack extends Stack {

  public readonly vpc: ec2.Vpc;
  public readonly securityGroups: ec2.SecurityGroup[];
  public readonly privateSubnets: string[];


  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

  }
}
