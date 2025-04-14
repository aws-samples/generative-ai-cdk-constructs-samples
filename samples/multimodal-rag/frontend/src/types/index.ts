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
export type S3File = {
    s3_bucket: string;
    s3_key: string;
    presigned_url: string;
};

export type IABCategory = {
    category: string;
    confidence?: number;
};

export type ContentModeration = {
    type: string;
    confidence: number;
};

export type TextLine = {
    text: string;
    confidence?: number;
};

export type BDAResult = {
    summary?: string;
    iab_categories?: IABCategory[];
    content_moderation?: ContentModeration[];
    text_lines?: TextLine[];
};

export type FMResult = {
    model_id: string;
    prompts: string;
    results?: string[];
    elapsed_s?: number;
};

export type InferenceValue = string | number | boolean | null | { [key: string]: InferenceValue } | InferenceValue[];

export type CustomOutput = {
    inference_result: Record<string, InferenceValue>;
};

export type Job = {
    id: string;
    demo_metadata: {
        job_status: string;
        completed_at: string;
        requested_at: string;
        requested_by: string;
        modality: string;
        file: S3File;
        result_file: S3File;
        custom_output_file?: S3File;
    };
    result?: BDAResult;
    custom_output?: CustomOutput;
    fm_result?: FMResult[];
};

/*
Example of a job
{
    "id": "cd373b99-115b-4dfd-9b54-787c569c9444",
    "demo_metadata": {
        "job_status": "COMPLETED",
        "completed_at": "2025-02-25 23:08:49 UTC",
        "file": {
            "s3_key": "lending_package_check.pdf",
            "s3_bucket": "bdamediasolutionbackendst-bdaconstruct92ac1753cbb6-gmnavmmijs8u"
            "presigned_url":""
        },
        "requested_by": "toto",
        "modality": "document",
        "result_file": {
            "s3_key": "/cd373b99-115b-4dfd-9b54-787c569c9444/0/standard_output/0/result.json",
            "s3_bucket": "bdamediasolutionbackendst-bdaconstruct92ac1753cbb6-z3njbwkwv0yn",
            "presigned_url":""
        },
        "requested_at": "2025-02-25 23:08:36 UTC"
    }
},
*/
