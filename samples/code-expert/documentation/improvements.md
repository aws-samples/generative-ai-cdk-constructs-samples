# Improvements

## Development and deployment

* **Exception handling:** All application function code needs to be reviewed to execute proper validation logic and
  exception handling. Not all cases were covered during prototype development.
* **Automated unit, integration and system tests:** In the prototype, some unit tests and manual tests were executed but
  they are by no means comprehensive. Automated test scripts are required to achieve higher code coverage and to ensure
  quality and robustness of the solution as it evolves from prototype to production.
* **Code repositories and pipelines:** Code repositories allow teams to collaborate and CI/CD pipelines allow frequent
  small improvements to be deployed.

## Operations

* **Monitoring:** The ability to properly monitor the system in production is crucial and the implemented code doesn't
  provide enough means to do so. Consider using both CloudWatch Logs and CloudWatch Metrics to have more visibility of
  all architecture components. For production, consider setting the log level to warning to reduce verbosity.
* **Auditing:** AWS CloudTrail can be used to implement detective controls. CloudTrail records AWS API calls for your
  account and delivers log files to you for auditing.
* **Tracing:** To help with the operations in the production environment, we recommend a tracing solution such as AWS
  X-Ray
* **VPC Flow Logs:** VPC Flow Logs capture network flow information for a VPC, subnet, or network interface and stores
  it in Amazon CloudWatch Logs and can help troubleshoot network issues.

## AI Model Flexibility

The prototype currently supports Anthropic Claude 3+ and Amazon Nova models. Extensibility for new models is built into
the system through the ModelAdapter interface. Customers can add support for additional models by implementing new
ModelAdapter classes in the
`packages/code-expert/code-expert/amzn_code_expert_code_expert/pace_core_utils/BedrockBatch/ConverseToBatch` directory.
This design allows for easy adaptation to new AI models or services as they become available or as customer needs
evolve.

## Scalability and Performance Strategies

### Handling Long Queue Times

Bedrock batch inference jobs may remain queued for days when they could have been completed in a few hours
synchronously.
One strategy could be to monitor Bedrock batch inference jobs that remain in the "Scheduled" status for more than *n*
hours, cancel them, and then run the job in synchronous mode. This would have to be monitored outside the Step
Functions execution.

### Managing Bedrock Queue Limits

Bedrock has a limit on the number of batch inference jobs that can be queued per model.

#### SQS Queue with Shovel Pattern

Implement an SQS queue for each model. Use the shovel pattern to control the flow of jobs into the Bedrock queue.

#### Step Functions Semaphore

Use a semaphore pattern within Step Functions to limit concurrent job submissions. A semaphore in Step Functions is
simpler, but will increase the relatively low cost of Step Functions state transitions.
