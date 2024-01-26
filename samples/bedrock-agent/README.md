# Sample Bedrock Agent app with CDK custom constructs

A chat assistant designed to answer questions about literature using RAG from a
selection of books from Project Gutenburg.

This app deploys a Bedrock Agent that can consult a Bedrock Knowledge Base
backed by OpenSearch Serverless as a vector store. An S3 bucket is created to
store the books for the Knowledge Base.

## Deployment
### Local generative-ai-cdk-constructs Package
Build https://github.com/awslabs/generative-ai-cdk-constructs .

Copy **dist/js/generative-ai-cdk-constructs@0.0.0.jsii.tgz** to this directory.

### Build
~~~sh
pnpm install # Install dependencies
pnpm cdk synth # build
~~~

### Deploy
~~~sh
pnpm cdk deploy
~~~

Note the outputs to load books into the Knowledge Base.

~~~
Outputs:
BedrockAgentStack.AgentId = <AgentID>
BedrockAgentStack.DataSourceId = <DataSourceID>
BedrockAgentStack.DocumentBucket = <DocBucket>
BedrockAgentStack.KnowledgeBaseId = <KBID>
~~~

### Load Books
You will need the DocumentBucket, KnowledgeBaseId, and DataSourceId.

~~~sh
./scripts/load-kb.sh s3://<DocBucket>/ <KBID> <DataSourceID>
~~~

## Try it out
Navigate to the [Bedrock Agents console](https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents) in your region and find your new agent.

Ask some questions. You may need to tell the agent what book you want to ask about or refresh the session when asking about different books.

### Frankenstein
* What does the Creature want Victor to do?

### Pride and Prejudice
* Who is Mr. Bingley quite taken with at the ball in Meryton?
* How does Mr. Darcy offend Elizabeth at the first ball?
* Why does Jane’s visit to the Bingleys end up lasting for days?

### Moby Dick
* What does Ahab nail to the ship’s mast to motivate his crew in his quest for Moby Dick?
* What frightens Ishmael the most about Moby Dick? 

### Romeo and Juliet
* Why is Romeo exiled?
* Where do Romeo and Juliet meet?
