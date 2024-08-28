# Multiple Document Question & Answering Modification
Follow the instructions in this guidance to modify the Document Explorer sample so that it can perform Question & Answering on multiple documents.

## Instructions

### Update the API Stack

Update the `document_explorer/lib/api-stack.ts` file with the following edits:

Add the following imports:
```
import * as path from 'path'
import * as lambda from 'aws-cdk-lib/aws-lambda'
```

Add the following custom Lambda code property to the `QaAppsyncOpensearch` construct props object:
```
customDockerLambdaProps: {
    code: lambda.DockerImageCode.fromImageAsset(path.join(
        __dirname,
        '..',
        'multi-doc-mod',
        'lambda',
        'aws-qa-custom',
        'question_answering',
        'src'
    ))
}
```

### Update the Client App

Copy `document_explorer/multi-doc-mod/client_app/pages` to `document_explorer/client_app/pages` and replace the current Streamlit pages to update the front end to allow multiple document selection.

### Deploy

Deploy following the Document Explorer instructions.