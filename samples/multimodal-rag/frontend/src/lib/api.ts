//
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
// with the License. A copy of the License is located at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
// OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
// and limitations under the License.
//

import { Amplify } from "aws-amplify";
import { fetchAuthSession } from "aws-amplify/auth";
import { get, post } from "aws-amplify/api";
import { getErrorMessage } from "./utils";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { fromCognitoIdentityPool } from "@aws-sdk/credential-provider-cognito-identity";
import { CognitoIdentityClient } from "@aws-sdk/client-cognito-identity";


const env = import.meta.env;

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: env.VITE_COGNITO_USER_POOL_ID,
      userPoolClientId: env.VITE_COGNITO_USER_POOL_CLIENT_ID,
      identityPoolId: env.VITE_COGNITO_IDENTITY_POOL_ID,
    },
  },
});

const existingConfig = Amplify.getConfig();

Amplify.configure({
  ...existingConfig,
  API: {
    REST: {
      [env.VITE_API_NAME]: {
        endpoint: env.VITE_API_GATEWAY_REST_API_ENDPOINT,
        region: env.VITE_AWS_REGION,
      },
    },
  },
});

const authToken = (await fetchAuthSession()).tokens?.idToken?.toString();

const defaultRestInput = {
  apiName: env.VITE_API_NAME,
  options: {
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  },
};

interface GetJobsParams {
  limit?: number;
  start_key?: string;
}

export async function getJobs(params?: GetJobsParams) {
  try {
    const queryParams = new URLSearchParams();
    
    if (params?.limit) {
      queryParams.append('limit', params.limit.toString());
    }
    if (params?.start_key) {
      queryParams.append('start_key', params.start_key);
    }

    const queryString = queryParams.toString();
    const path = `/jobs${queryString ? `?${queryString}` : ''}`;

    const restOperation = get({
      ...defaultRestInput,
      path,
    });
    const response = await restOperation.response;
    return response.body.json();
  } catch (e: unknown) {
    console.log("GET call failed: ", getErrorMessage(e));
  }
}

export async function getJob(jobId: string) {
  try {
    const restOperation = get({
      ...defaultRestInput,
      path: `/jobs/${jobId}`,
    });
    const response = await restOperation.response;
    return response.body.json();
  } catch (e: unknown) {
    console.log("GET call failed: ", getErrorMessage(e));
  }
}

export async function uploadDocument(file: File | Blob, filename: string) {
  try {
    // Create S3 client
    const s3Client = new S3Client({
      region: env.VITE_REGION_NAME,
      credentials: fromCognitoIdentityPool({
        client: new CognitoIdentityClient({ region: env.VITE_REGION_NAME }),
        identityPoolId: env.VITE_COGNITO_IDENTITY_POOL_ID,
        logins: {
          [`cognito-idp.${env.VITE_REGION_NAME}.amazonaws.com/${env.VITE_COGNITO_USER_POOL_ID}`]: authToken || ''
        }
      })
    });

    // Convert File/Blob to ArrayBuffer
    const fileBuffer = await file.arrayBuffer();

    // Create PutObject command
    const command = new PutObjectCommand({
      Bucket: env.VITE_S3_BUCKET_NAME,
      Key: filename,
      Body: new Uint8Array(fileBuffer),
      ContentType: file.type || 'application/octet-stream',
      ContentDisposition: `attachment; filename="${filename}"`,
    });

    // Upload file
    const response = await s3Client.send(command);
    return response;

  } catch (e: unknown) {
    console.error("Upload failed: ", getErrorMessage(e));
    throw e;
  }
}




export async function getDocument(filename: string) {
  try {
    const restOperation = get({
      ...defaultRestInput,
      path: `/documents/${filename}`,
    });
    const response = await restOperation.response;
    return response;
  } catch (e: unknown) {
    console.log("GET call failed: ", getErrorMessage(e));
  }
}

/**
 * 
 * Create a job
 * 
 * Parameters https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-data-automation-runtime/client/invoke_data_automation_async.html
response = client.invoke_data_automation_async(
    dataAutomationConfiguration={
        'dataAutomationProjectArn': 'string',
        'stage': 'LIVE'|'DEVELOPMENT'
    },
    blueprints=[
        {
            'blueprintArn': 'string',
            'version': 'string',
            'stage': 'DEVELOPMENT'|'LIVE'
        },
    ],
    dataAutomationProfileArn='string',
) 

*/

interface CreateJobRequest {
  filename: string,
  modality: string,
  bda_project_arn: string,
  dataAutomationProfileArn: string,
}

export async function createJob(jobRequest: CreateJobRequest) {
  try {
    const restOperation = post({
      ...defaultRestInput,
      path: `/jobs`,
      options: {
        ...defaultRestInput.options,
        body: {
          filename: jobRequest.filename,
          modality : jobRequest.modality,
          bda_project_arn: jobRequest.bda_project_arn,
          dataAutomationProfileArn: jobRequest.dataAutomationProfileArn
        },
      },
    });
    const response = await restOperation.response;
    return response.body.json();
  } catch (e: unknown) {
    console.log("POST call failed: ", getErrorMessage(e));
  }
}

/**
 * 
 * listBlueprints
 * 
 * response = client.list_blueprints(
    blueprintArn='string',
    resourceOwner='SERVICE'|'ACCOUNT',
    blueprintStageFilter='DEVELOPMENT'|'LIVE'|'ALL',
    maxResults=123,
    nextToken='string',
    projectFilter={
        'projectArn': 'string',
        'projectStage': 'DEVELOPMENT'|'LIVE'
    }
)
 */

export interface BlueprintListRequest {
  operation: string;
  blueprintArn?: string;
  resourceOwner?: 'SERVICE' | 'ACCOUNT';
  blueprintStageFilter?: 'DEVELOPMENT' | 'LIVE' | 'ALL';
  maxResults?: number;
  nextToken?: string;
  projectFilter?: {
    projectArn: string;
    projectStage?: 'DEVELOPMENT' | 'LIVE';
  };
}

/**
 * blueprintArn, resourceOwner, blueprintStageFilter, maxResults, nextToken, projectFilter"
 */
export async function listBlueprints(blueprintData: BlueprintListRequest) {
  try {
    // handle optional values
    blueprintData.maxResults = blueprintData.maxResults || 10;

    const restOperation = post({
      ...defaultRestInput,
      path: `/blueprint`,
      options: {
        ...defaultRestInput.options,
        body: {
          operation: blueprintData.operation,
          ...(blueprintData.projectFilter && {
            projectFilter: {
              projectArn: blueprintData.projectFilter.projectArn,
              ...(blueprintData.projectFilter.projectStage && {
                projectStage: blueprintData.projectFilter.projectStage
              })
            }
          })
        },
        headers: {
          ...defaultRestInput.options.headers,
          'Content-Type': 'application/json',
        },
      },
    });
    const response = await restOperation.response;
    return response.body.json();
  } catch (e: unknown) {
    console.log("POST call failed: ", getErrorMessage(e));
  }
}

/**
 * 
 * listProjects
 * 
 * response = client.list_data_automation_projects(
    maxResults=123,
    nextToken='string',
    projectStageFilter='DEVELOPMENT'|'LIVE'|'ALL',
    blueprintFilter={
        'blueprintArn': 'string',
        'blueprintVersion': 'string',
        'blueprintStage': 'DEVELOPMENT'|'LIVE'
    },
    resourceOwner='SERVICE'|'ACCOUNT'
)
 */

export interface ProjectListRequest {
  operation: string;
  resourceOwner?: 'SERVICE' | 'ACCOUNT';
  maxResults?: number;
  nextToken?: string;
  projectStageFilter?: 'DEVELOPMENT' | 'LIVE' | 'ALL';
  blueprintFilter?: {
    blueprintArn?: string;
    blueprintVersion?: string;
    blueprintStage?: 'DEVELOPMENT' | 'LIVE';
  };
}

/**
 * Represents a field in the blueprint schema for data extraction
 */
interface SchemaField {
  [key: string]: string;
  /** Unique identifier for the field */
  name: string;
  /** Description of what data should be extracted for this field */
  description: string;
  /** Data type of the field (e.g., 'string', 'number', 'array') */
  type: string;
  /** Type of inference to be performed (e.g., 'text', 'table', 'key-value') */
  inferenceType: string;
}

/**
 * Request parameters for creating a new blueprint
 */
interface BlueprintCreateRequest {
  /** Operation type for the API request */
  operation: string;
  /** Name of the blueprint (must be unique) */
  blueprint_name: string;
  /** Stage of the blueprint - either development or production */
  blueprint_stage: 'DEVELOPMENT' | 'LIVE';
  /** Type of data the blueprint processes */
  blueprint_type: 'DOCUMENT' | 'IMAGE';
  /** Optional description of the blueprint's purpose */
  description?: string;
  /** Array of schema fields defining what data to extract */
  schema_fields?: SchemaField[];
  /** Optional name of schema file if using file-based schema */
  schema_file_name?: string;
}


export async function createBlueprint(blueprintData: BlueprintCreateRequest) {
  try {
    const restOperation = post({
      ...defaultRestInput,
      path: `/blueprint`,
      options: {
        ...defaultRestInput.options,
        body: {
          operation: blueprintData.operation,
          blueprint_name: blueprintData.blueprint_name,
          blueprint_stage: blueprintData.blueprint_stage,
          blueprint_type: blueprintData.blueprint_type,
          description: blueprintData.description,
          schema_fields: blueprintData.schema_fields,
          schema_file_name: blueprintData.schema_file_name
        },
        headers: {
          ...defaultRestInput.options.headers,
          'Content-Type': 'application/json',
        },
      },
    });
    const response = await restOperation.response;
    return response.body.json();
  } catch (e: unknown) {
    console.log("POST call failed: ", getErrorMessage(e));
    throw e;
  }
}

interface ProjectCreateRequest {
  operation: string;
  projectName: string;
  projectStage: 'DEVELOPMENT' | 'LIVE';
  blueprint_arn: string;
  modality: 'document' | 'image' | 'video' | 'audio';
  description?: string;
  standardOutputConfiguration?: {
    document?: {
      extraction?: {
        granularity?: {
          types?: ('DOCUMENT' | 'PAGE' | 'ELEMENT' | 'WORD' | 'LINE')[];
        };
        boundingBox?: {
          state?: 'ENABLED' | 'DISABLED';
        };
      };
      generativeField?: {
        state?: 'ENABLED' | 'DISABLED';
      };
      outputFormat?: {
        textFormat?: {
          types?: ('PLAIN_TEXT' | 'MARKDOWN' | 'HTML' | 'CSV')[];
        };
        additionalFileFormat?: {
          state?: 'ENABLED' | 'DISABLED';
        };
      };
    };
    image?: {
      extraction?: {
        category?: {
          state?: 'ENABLED' | 'DISABLED';
          types?: ('CONTENT_MODERATION' | 'TEXT_DETECTION' | 'LOGOS')[];
        };
        boundingBox?: {
          state?: 'ENABLED' | 'DISABLED';
        };
      };
      generativeField?: {
        state?: 'ENABLED' | 'DISABLED';
        types?: ('IMAGE_SUMMARY' | 'IAB')[];
      };
    };
    video?: {
      extraction?: {
        category?: {
          state?: 'ENABLED' | 'DISABLED';
          types?: ('CONTENT_MODERATION' | 'TEXT_DETECTION' | 'TRANSCRIPT' | 'LOGOS')[];
        };
        boundingBox?: {
          state?: 'ENABLED' | 'DISABLED';
        };
      };
      generativeField?: {
        state?: 'ENABLED' | 'DISABLED';
        types?: ('VIDEO_SUMMARY' | 'IAB' | 'CHAPTER_SUMMARY')[];
      };
    };
    audio?: {
      extraction?: {
        category?: {
          state?: 'ENABLED' | 'DISABLED';
          types?: ('AUDIO_CONTENT_MODERATION' | 'TRANSCRIPT' | 'TOPIC_CONTENT_MODERATION')[];
        };
      };
      generativeField?: {
        state?: 'ENABLED' | 'DISABLED';
        types?: ('AUDIO_SUMMARY' | 'IAB' | 'TOPIC_SUMMARY')[];
      };
    };
  };
}

export async function createProject(projectData: ProjectCreateRequest) {
  try {
    const restOperation = post({
      ...defaultRestInput,
      path: `/project`,
      options: {
        ...defaultRestInput.options,
        body: {
          operation: projectData.operation,
          project_name: projectData.projectName,
          project_stage: projectData.projectStage,
          blueprint_arn: projectData.blueprint_arn,
          modality: projectData.modality,
          description: projectData.description,
          standardOutputConfiguration: projectData.standardOutputConfiguration
        } as any,
        headers: {
          ...defaultRestInput.options.headers,
          'Content-Type': 'application/json',
        },
      },
    });
    const response = await restOperation.response;
    return response.body.json();
  } catch (e: unknown) {
    console.log("POST call failed: ", getErrorMessage(e));
    throw e;
  }
}

interface QARequest {
  jobId: string;
  model: string;
  question: string;
}

export async function askQuestion(data: QARequest): Promise<Response> {
  try {
    const response = await fetch(`${env.VITE_API_GATEWAY_REST_API_ENDPOINT}/qa`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
      },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      throw new Error('Failed to get response from Q&A endpoint');
    }

    return response;
  } catch (e: unknown) {
    console.error("Q&A request failed:", getErrorMessage(e));
    throw e;
  }
}

export async function listProjects(projecData: ProjectListRequest) {
  try {

    // minimum required fields
    const body: Record<string, string | number | object> = {
      operation: projecData.operation,
    }

    if (projecData.resourceOwner) {
      body['resourceOwner'] = projecData.resourceOwner;
    }

    if (projecData.maxResults) {
      body['maxResults'] = projecData.maxResults;
    }
    
    if (projecData.blueprintFilter) {
      body['blueprintFilter'] = projecData.blueprintFilter;
    }

    const restOperation = post({
      ...defaultRestInput,
      path: `/project`,
      options: {
        ...defaultRestInput.options,
        body,
        headers: {
          ...defaultRestInput.options.headers,
          'Content-Type': 'application/json',
        },
      },
    });
    const response = await restOperation.response;
    return response.body.json();
  } catch (e: unknown) {
    console.log("POST call failed: ", getErrorMessage(e));
  }
}
