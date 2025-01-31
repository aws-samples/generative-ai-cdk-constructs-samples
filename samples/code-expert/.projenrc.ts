/**
 *  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
 *  with the License. A copy of the License is located at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 *  and limitations under the License.
 */

import { monorepo } from "@aws/pdk";
import { InfrastructureTsProject } from "@aws/pdk/infrastructure";
import { javascript } from "projen";
import { PythonProject } from "projen/lib/python";

const context = {
  /**
   * Bedrock model id to use in rule evaluation.
   *
   * Default - "anthropic.claude-3-5-sonnet-20241022-v2:0"
   */
  // modelId: "anthropic.claude-3-5-sonnet-20241022-v2:0",
};

const cdkVersion = "2.173.2";
const pdkVersion = "0.25.13";
const projectName = "code-expert";
const npmPrefix = "@amzn/";
const pypiPrefix = "amzn-";

const toSnakeCase = (str: string): string => {
  return str
    .split(/(?=[A-Z])|[\s-]+/) // Split on uppercase letters, spaces, or hyphens
    .map((word) => word.toLowerCase())
    .join("_");
};

const project = new monorepo.MonorepoTsProject({
  devDeps: [`@aws/pdk@${pdkVersion}`],
  name: npmPrefix + projectName,
  packageManager: javascript.NodePackageManager.PNPM,
  projenrcTs: true,
  gitignore: [
    ".bashrc",
    ".profile",
    ".idea",
    ".venv",
    ".DS_Store",
    "__pycache__",
    "mermaid-filter.err",
  ],
  prettier: true,
  license: "Apache-2.0",
  licenseOptions: {
    disableDefaultLicenses: true,
  },
});

const codeExpert = new PythonProject({
  parent: project,
  name: `${pypiPrefix}${projectName}-code-expert`,
  outdir: `packages/${projectName}/code-expert`,
  moduleName: `${toSnakeCase(pypiPrefix + projectName)}_code_expert`,
  authorName: "AWS Latam PACE",
  authorEmail: "aws-latam-pace@amazon.com",
  version: "0.1.0",
  deps: [
    "boto3@^1.35.37",
    "Jinja2@^3.1.5",
    "pydantic@^2.10.4",
    "python@^3.12",
    "aws-lambda-powertools@{version = '^3.4.0', extras = ['parser']}",
    "lxml@^5.3.0",
    "tenacity@^9.0.0",
  ],
  devDeps: [
    "boto3-stubs-lite@{version = '^1.35.37', extras = ['bedrock', 'bedrock-runtime', 'dynamodb', 'firehose', 's3', 'ssm', 'stepfunctions']}",
    "moto@{version = '^5.0.16', extras = ['all']}",
    "mypy@^1.11.2",
    "black@^24.10.0",
    "python-dotenv@^1.0.1",
  ],
  poetry: true,
  pip: false,
  setuptools: false,
  venv: false,
});

const demo = new PythonProject({
  parent: project,
  name: `${pypiPrefix}${projectName}-demo`,
  outdir: `demo`,
  moduleName: `${toSnakeCase(pypiPrefix + projectName)}demo`,
  authorName: "AWS Latam PACE",
  authorEmail: "aws-latam-pace@amazon.com",
  version: "0.1.0",
  deps: ["boto3@^1.35.37", "python@^3.12", "streamlit@^1.41.1"],
  devDeps: [
    "boto3-stubs-lite@{version = '^1.35.37', extras = ['bedrock-runtime', 'dynamodb', 'firehose', 's3', 'sagemaker-a2i-runtime', 'ssm', 'stepfunctions']}",
    "mypy@^1.11.2",
    "black@^24.10.0",
  ],
  poetry: true,
  pip: false,
  setuptools: false,
  venv: false,
  pytest: false,
  sample: false,
});

const demoPyprojectToml = demo.tryFindObjectFile("pyproject.toml");
if (demoPyprojectToml) {
  demoPyprojectToml.addOverride("tool.poetry.package-mode", false);
}
demo.tasks.removeTask("build");

const infra = new InfrastructureTsProject({
  parent: project,
  name: `${npmPrefix}${projectName}-infra`,
  outdir: "packages/infra",
  cdkVersion: cdkVersion,
  deps: [
    `@aws/pdk@^${pdkVersion}`,
    "cdk-nag",
    `@aws-cdk/aws-lambda-python-alpha@^${cdkVersion}-alpha.0`,
  ],
  context: { ...context },
  prettier: true,
  gitignore: ["cdk.context.json"],
});
project.addImplicitDependency(infra, codeExpert);

project.synth();
