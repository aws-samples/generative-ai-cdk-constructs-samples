# Welcome to your CDK TypeScript project

This is a blank project for CDK development with TypeScript.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

## Useful commands

* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `npx cdk deploy`  deploy this stack to your default AWS account/region
* `npx cdk diff`    compare deployed stack with current state
* `npx cdk synth`   emits the synthesized CloudFormation template


# upload file

aws s3 cp path/to/your/local/file.pdf s3://your-bucket-name/
aws s3 cp ./document/noa.pdf s3://cb-input-documents/

# publish event bridge event

```
// Example event structure
const event = {
  detail: {
    input_file_name: "noa.pdf"
  },
  detail-type: "FileProcessingEvent",
  source: "custom.fileprocessing"
}

aws events put-events --entries '[{
    "Source": "custom.fileprocessing",
    "DetailType": "File ProcessingEvent",
    "Detail": "{\"input_file_name\": \"noa.pdf\"}",
    "EventBusName": "default"
}]'


```


# Then run the put-events command
aws events put-events --cli-input-json file://document/bp_event.json


## api - create project
```json 

             {
             "operation":"create","projectName":"bp_project_1","projectStage":"LIVE","projectDescription":"sample","customOutputConfiguration":
             {"blueprints":[{"blueprintArn":"arn:aws:bedrock:us-west-2:551246883740:blueprint/7966fd852869","blueprintStage":"LIVE"}]}

  
}

```

project delete
```json 
{
             "operation":"delete","projectArn":"arn:aws:bedrock:us-west-2:551246883740:data-automation-project/c322bca4452b"
}
   
   ```


project get

```json
{
             "operation":"get","projectArn":"arn:aws:bedrock:us-west-2:551246883740:data-automation-project/a2c4b11e123e",
             "projectStage":"LIVE"
}
```







