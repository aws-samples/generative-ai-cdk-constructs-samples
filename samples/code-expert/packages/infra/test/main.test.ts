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

import { App, Aspects } from "aws-cdk-lib";
import { Annotations, Match } from "aws-cdk-lib/assertions";
import { AwsSolutionsChecks } from "cdk-nag";
import { ApplicationStack } from "../src/stacks/application-stack";

test("No unsuppressed Errors", () => {
  const app = new App();
  Aspects.of(app).add(new AwsSolutionsChecks());
  const stack = new ApplicationStack(app, "test", {
    env: {
      region: "us-east-1",
    },
  });
  app.synth();
  const errors = Annotations.fromStack(stack).findError(
    "*",
    Match.stringLikeRegexp("AwsSolutions-.*"),
  );
  const errorData = errors.map((error) => error.entry.data);
  expect(errorData).toHaveLength(0);
});
