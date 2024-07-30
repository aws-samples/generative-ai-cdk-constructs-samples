import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
// import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as emergingTech from '@cdklabs/generative-ai-cdk-constructs';


export class TextToSqlStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

  const textT  = new  emergingTech.TextToSql(this, "TextToSql1", {
      databaseType: emergingTech.DatabaseType.AURORA,
      dbName: emergingTech.DbName.MYSQL,
      metadataSource:"config_file",
      stage:"dev",
    })

  }
}
