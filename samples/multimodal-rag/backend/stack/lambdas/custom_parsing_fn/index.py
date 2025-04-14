#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
import boto3
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
import json
import uuid
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError

# Constants for output types
STANDARD_OUTPUT = "standard_output"
CUSTOM_OUTPUT = "custom_output"

KB_DATA_SOURCE_ID = os.environ.get("KB_DATA_SOURCE_ID")
KB_ID = os.environ.get("KB_ID") 
KB_DATA_SOURCE_PREFIX = os.environ.get("KB_DATA_SOURCE_PREFIX")
OUTPUT_BUCKET= os.environ.get("OUTPUT_BUCKET")

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
bda_runtime = boto3.client('bedrock-data-automation-runtime')
jobs_table = dynamodb.Table(os.environ['JOBS_TABLE'])
bedrock_agent = boto3.client('bedrock-agent')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'WARNING').upper())

def validate_event(event_obj: dict) -> None:
    """Validates the input event object for required fields and constraints."""
    # Check if this is an EventBridge event
    if 'detail' in event_obj and 'output_s3_location' in event_obj['detail']:
        if 'job_id' not in event_obj['detail']:
            raise ValueError("job_id must be present in event.")
        eventbridge_info = event_obj['detail']['output_s3_location']
        if 's3_bucket' not in eventbridge_info or 'name' not in eventbridge_info:
            raise ValueError("S3 bucket and name information is required in output_s3_location.")
    else:
        raise ValueError("Event must contain EventBridge detail.")

def convert_decimal_to_float(obj):
    if isinstance(obj, list):
        return [convert_decimal_to_float(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj

def dynamodb_get_by_id(key_value, key_name="id"):
    logger.info('Getting job from DynamoDB')
    try:
        response = jobs_table.get_item(Key={key_name: key_value})
        if 'Item' in response:
            return convert_decimal_to_float(response['Item'])
        else:
            logger.warning(f"No item found with id: {key_value}")
            return None
    except ClientError as e:
        logger.error(f"Client error occurred while fetching from DynamoDB: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        logger.error(f"An error occurred, dynamodb_get_by_id: {e}")
        return None
    
def update_job(job):
    """Records a job in the DynamoDB jobs table."""
    logger.info('Updating job')
    jobs_table.put_item(Item=job)
    
def get_json_from_s3(bucket_name: str, key: str) -> dict:
    # Fetch the object
    try:
        logger.info(f"Fetching JSON from S3: {key} from {bucket_name}")
        response = s3.get_object(Bucket=bucket_name, Key=key)
        # Read the object content and load it as JSON
        content = response['Body'].read().decode('utf-8')
        return json.loads(content)
    except ClientError as ex:
        logger.error(f"Error fetching JSON from S3: {ex.response['Error']['Message']}")
    except Exception as ex:
        logger.error(f"An unexpected error occurred while fetching JSON from S3: {ex}")
    
    return None

def upload_to_s3(key: str, body: str, bucket: str) -> bool:
    """
    Upload content to S3 with error handling and retries
    
    Args:
        key: S3 object key
        body: Content to upload
        bucket: S3 bucket name
    
    Returns:
        bool: Success status of upload
    """
    if not key or not bucket:
        logger.error("Missing required parameters for S3 upload: key or bucket")
        return False
        
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"Uploading to S3: {bucket}/{key} (attempt {retry_count + 1})")
            s3.put_object(Bucket=bucket, Key=key, Body=body)
            logger.info(f"Successfully uploaded to S3: {bucket}/{key}")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"S3 ClientError on attempt {retry_count + 1}: {error_code} - {str(e)}")
            retry_count += 1
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3 on attempt {retry_count + 1}: {str(e)}")
            retry_count += 1
            
    logger.error(f"Failed to upload to S3 after {max_retries} attempts: {bucket}/{key}")
    return False
    
def create_kb_input_document(
    result: Dict[str, Any], 
    custom_output: Optional[Dict[str, Any]], 
    task_id: str, 
    file_name: str, 
    file_format: str,
    bucket: str
) -> None:
    """
    Create knowledge base input files for document analysis results
    
    Args:
        result: Document analysis result
        custom_output: Custom output from processing
        task_id: Task identifier
        file_name: Original file name without extension
        file_format: File format/extension
    """
    # Document summary file with summary and description
    key = f"{KB_DATA_SOURCE_PREFIX}/{task_id}/document-{file_name}.txt"
    summary = f'Document name: {file_name}.{file_format}'
    
    if result.get("document", {}).get("description"):
        summary += f'\nDescription: {result["document"]["description"]}'
    
    if result.get("document", {}).get("summary"):
        summary += f'\nSummary: {result["document"]["summary"]}'
    
    if summary:
        upload_to_s3(key, summary, bucket)

    # Document page files
    for page in result.get("pages", []):
        if "representation" in page:
            key = f"{KB_DATA_SOURCE_PREFIX}/{task_id}/document-page-{page['page_index']}.txt"
            content = None
            
            for content_type in ["text", "markdown", "html"]:
                if content_type in page.get("representation", {}):
                    content = page["representation"][content_type]
                    break
            
            if content:
                page_content = f'Document name: {file_name}.{file_format}\n{content}'
                upload_to_s3(key, page_content, bucket)

    # Custom output
    if custom_output and custom_output.get("inference_result"):
        key = f"{KB_DATA_SOURCE_PREFIX}/{task_id}/document-custom-output.txt"
        custom = f'Custom output: {json.dumps(custom_output["inference_result"])}'
        upload_to_s3(key, custom, bucket)

def create_kb_input_image(
    result: Dict[str, Any], 
    custom_output: Optional[Dict[str, Any]], 
    task_id: str, 
    file_name: str, 
    file_format: str,
    bucket: str
) -> None:
    """
    Create knowledge base input files for image analysis results
    
    Args:
        result: Image analysis result
        custom_output: Custom output from processing
        task_id: Task identifier
        file_name: Original file name without extension
        file_format: File format/extension
    """
    # Image summary file with full transcript
    summary = f'Image name: {file_name}.{file_format}'
    
    # IAB categories
    iabs = []
    for iab in result.get("image", {}).get("iab_categories", []):
        iabs.append(iab.get("category", ""))
    
    if iabs:
        summary += f'\nIAB categories: {", ".join(iabs)}'
    
    # Content moderation
    cms = []
    for cm in result.get("image", {}).get("content_moderation", []):
        cms.append(cm.get("category", ""))
    
    if cms:
        summary += f'\nContent moderation labels: {", ".join(cms)}'
    
    # Text lines
    txts = []
    for t in result.get("image", {}).get("text_lines", []):
        if t.get("text") and t["text"] not in txts:
            txts.append(t["text"])
    
    if txts:
        summary += f'\nText detected:\n{"\n".join(txts)}'
    
    # Custom output
    if custom_output and custom_output.get("inference_result"):
        summary += f'\nCustom output: {json.dumps(custom_output["inference_result"])}'
    
    # Add summary if available
    if result.get("image", {}).get("summary"):
        summary += f'\nSummary: {result["image"]["summary"]}'

    key = f"{KB_DATA_SOURCE_PREFIX}/{task_id}/image-{file_name}.txt"
    upload_to_s3(key, summary, bucket)

def create_kb_input_audio(
    result: Dict[str, Any], 
    custom_output: Optional[Dict[str, Any]], 
    task_id: str, 
    file_name: str, 
    file_format: str,
    bucket: str
) -> None:
    """Create knowledge base input files for audio analysis results.
    
    Args:
        result: Audio analysis result dictionary
        custom_output: Optional custom processing output
        task_id: Unique task identifier
        file_name: Name of original file without extension
        file_format: Format/extension of original file
    """
    audio_data = result.get("audio", {})
    
    # Audio summary file with full transcript
    summary = f'Audio name: {file_name}.{file_format}'
    
    if audio_data.get("summary"):
        summary += f'\nSummary: {audio_data["summary"]}'
        
    # Add transcript if available
    transcript = audio_data.get("transcript", {}).get("representation", {}).get("text", "")
    if transcript:
        summary += f'\nTranscript: {transcript}'
        
    key = f"{KB_DATA_SOURCE_PREFIX}/{task_id}/audio-{file_name}.txt"
    upload_to_s3(key, summary, bucket)

    # Audio segment transcript file with moderation result
    audio_segments = audio_data.get("audio_segments", [])
    if audio_segments:
        key = f"{KB_DATA_SOURCE_PREFIX}/{task_id}/audio-transcript.txt"
        transcripts = []
        
        for idx, segment in enumerate(audio_segments):
            start_time = segment.get("start_timestamp_millis", 0) / 1000
            end_time = segment.get("end_timestamp_millis", 0) / 1000
            trans = f"[{start_time}-{end_time}] {segment.get('text', '')}"
            
            # Fix: Changed < to > in the condition
            content_moderation = result.get("content_moderation", [])
            if content_moderation and idx < len(content_moderation):
                acms = []
                acm = content_moderation[idx]
                if acm.get("confidence", 0) >= 0.4:
                    for mc in acm.get("moderation_categories", []):
                        if mc.get("confidence", 0) > 0.4 and mc.get("category") not in acms:
                            acms.append(mc.get("category"))
                            
                if acms:
                    trans += f" (toxicity: {', '.join(acms)})"
                    
            transcripts.append(trans)
            
        upload_to_s3(key, '\n'.join(transcripts), bucket)

    # Chapter files: summary and transcripts
    for chapter in result.get("chapters", []):
        chapter_index = chapter.get("chapter_index", "unknown")
        start_time = chapter.get("start_timestamp_millis", 0)
        end_time = chapter.get("end_timestamp_millis", 0)
        
        key = f"{KB_DATA_SOURCE_PREFIX}/{task_id}/audio-chapter-{chapter_index}-{start_time}-{end_time}.txt"
        
        chapter_summary = f'Audio name: {file_name}.{file_format}'
        if chapter.get("summary"):
            chapter_summary += f'\nSummary: {chapter["summary"]}'
            
        chapter_transcript = chapter.get("transcript", {}).get("representation", {}).get("text", "")
        if chapter_transcript:
            chapter_summary += f'\nTranscript: {chapter_transcript}'
            
        upload_to_s3(key, chapter_summary, bucket)

def create_kb_input_video(
    result: Dict[str, Any], 
    custom_output: Optional[Dict[str, Any]], 
    task_id: str, 
    video_file_name: str, 
    video_format: str,
    bucket: str
) -> None:
    """Create knowledge base input files for video analysis results.
    
    Args:
        result: Video analysis result dictionary
        custom_output: Optional custom processing output
        task_id: Unique task identifier
        video_file_name: Name of original file without extension
        video_format: Format/extension of original file
    """
    # Create video summary file
    video_data = result.get("video", {})
    summary = f'Video name: {video_file_name}.{video_format}'
    
    if video_data.get("summary"):
        summary += f'\n{video_data["summary"]}'
        
    key = f"{KB_DATA_SOURCE_PREFIX}/{task_id}/video-{video_file_name}.txt"
    upload_to_s3(key, summary, bucket)

    # Process scenes
    for scene in result.get("scenes", []):
        scene_index = scene.get("scene_index", "unknown")
        start_time = scene.get("start_timestamp_millis", 0)
        end_time = scene.get("end_timestamp_millis", 0)
        
        # Create scene level transcript file
        key = f"{KB_DATA_SOURCE_PREFIX}/{task_id}/video-transcript-{scene_index}-{start_time}-{end_time}.txt"
        transcripts = []
        
        for segment in scene.get("audio_segments", []):
            seg_start = segment.get("start_timestamp_millis", 0) / 1000
            seg_end = segment.get("end_timestamp_millis", 0) / 1000
            text = segment.get("text", "")
            transcripts.append(f"[{seg_start}-{seg_end}] {text}")

        if transcripts:
            upload_to_s3(key, '\n'.join(transcripts), bucket)

        # Create scene summary files
        key = f"{KB_DATA_SOURCE_PREFIX}/{task_id}/video-scene-{scene_index}-{start_time}-{end_time}.txt"
        
        txts, vcms, acms, iabs = [], [], [], []

        # Process IAB categories
        for iab in scene.get("iab_categories", []):
            category = iab.get("category")
            if category:
                iabs.append(category)

        # Process audio content moderation
        for acm in scene.get("content_moderation", []):
            if acm.get("confidence", 0) >= 0.4:
                for mc in acm.get("moderation_categories", []):
                    if mc.get("confidence", 0) > 0.4 and mc.get("category") not in acms:
                        acms.append(mc.get("category"))

        # Process frames for visual elements
        for frame in scene.get("frames", []):
            # Visual content moderation
            for vcm in frame.get("content_moderation", []):
                category = vcm.get("category")
                if category and category not in vcms:
                    vcms.append(category)
                    
            # Text lines
            for t in frame.get("text_lines", []):
                text = t.get("text")
                if text and text not in txts:
                    txts.append(text)

        # Build scene summary
        scene_summary = f"""Video name: {video_file_name}.{video_format}
        Scene {scene_index}
        Scene start millisecond: {start_time}
        Scene end millisecond: {end_time}"""
        
        if txts:
            scene_summary += f"\nText lines detected in the scene: {', '.join(txts)}"
        if vcms:
            scene_summary += f"\nUnsafe visual content detected in the scene: {', '.join(vcms)}"
        if acms:
            scene_summary += f"\nToxic language detected in the scene: {', '.join(acms)}"
        if iabs:
            scene_summary += f"\nIAB categories: {', '.join(iabs)}"

        if scene.get("summary"):
            scene_summary += f"\n\nScene summary: {scene['summary']}"
        
        upload_to_s3(key, scene_summary, bucket)

def create_kb_input(
    result: Dict[str, Any],
    custom_output: Optional[Dict[str, Any]],
    task_id: str,
    file_name: str,
    file_format: str,
    modality: str,
    bucket: str
) -> bool:
    """
    Create knowledge base input files based on modality type
    
    Args:
        result: Analysis result dictionary
        custom_output: Custom processing output
        task_id: Task identifier
        file_name: Original file name without extension
        file_format: File format/extension
        modality: Content modality (document, image, audio, video)
        bucket: S3 bucket name
        
    Returns:
        bool: Success status
    """
    logger.info(f"Creating KB input files for {modality} task {task_id}, file: {file_name}.{file_format}")
    
    try:
        if modality == "document":
            create_kb_input_document(result, custom_output, task_id, file_name, file_format, bucket)
        elif modality == "image":
            create_kb_input_image(result, custom_output, task_id, file_name, file_format, bucket)
        elif modality == "audio":
            create_kb_input_audio(result, custom_output, task_id, file_name, file_format, bucket)
        elif modality == "video":
            create_kb_input_video(result, custom_output, task_id, file_name, file_format, bucket)
        else:
            logger.warning(f"Unsupported modality: {modality}")
            return False
            
        logger.info(f"Successfully created KB input files for {modality} task {task_id}")
        return True
    except Exception as e:
        logger.error(f"Error creating KB input files for {modality}: {str(e)}", exc_info=True)
        return False
    
def extract_object_key(s3_file_path: str):
    # Extract object keys from S3 paths
    if s3_file_path:
        # Remove s3:// prefix and split by /
        parts = s3_file_path.replace('s3://', '').split('/', 1)
        if len(parts) > 1:
            return parts[1]  # Everything after the bucket name
        else:
            return None

def handler(event, _context):
    """Main handler function for processing the event."""

    logger.debug(event)

    validate_event(event)
    bucket_name = event['detail']['output_s3_location']['s3_bucket']
    output_key = event['detail']['output_s3_location']['name']
    task_id = event['detail']['job_id']
    bda_job_status = event['detail']['job_status']

    standard_output_key = output_key+'/'+STANDARD_OUTPUT+'/0/result.json'
    custom_output_key = output_key+'/'+CUSTOM_OUTPUT+'/0/result.json'

    # retrieve job from dynamo db table
    logger.info(f"Retrieved task ID: {task_id}")
    task = dynamodb_get_by_id(task_id)
    if task is None:
        logger.error(f"Failed to retrieve task: {task_id}")
        return {
                'statusCode': 500,
                'body': f'Failed to retrieve: {task_id}'
            }
    
    # check if the BDA job failed
    if bda_job_status != 'SUCCESS':
        task["demo_metadata"]["job_status"] = "FAILED_BDA"
        update_job(task)
        return {
            'statusCode': 500,
            'body': f'BDA job failed with status {bda_job_status}'
        }
        
    logger.info(f"standard_output_key: {standard_output_key}")
    logger.info(f"custom_output_key: {custom_output_key}")

    standard_output = get_json_from_s3(bucket_name, standard_output_key)
    custom_output = get_json_from_s3(bucket_name, custom_output_key)

    if standard_output:
        modality = standard_output.get("metadata",{}).get("semantic_modality")
        if modality:
            modality = modality.lower()
        if task:
            task["demo_metadata"]["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            task["demo_metadata"]["job_status"] = "CUSTOM_PARSING"
            task["demo_metadata"]["modality"] = modality

            task["demo_metadata"]["result_file"] = {
                "s3_bucket": bucket_name,
                "s3_key": standard_output_key
            }

    if custom_output:
            task["demo_metadata"]["custom_output_file"] = {
                "s3_bucket": bucket_name,
                "s3_key": custom_output_key
            }

    update_job(task)

    arr = standard_output["metadata"]["s3_key"].split('/')[-1].split('.')
    file_name = arr[0]
    file_format = arr[1]

    creation_status = create_kb_input(standard_output, custom_output, task_id, file_name, file_format, modality, OUTPUT_BUCKET)
    if not creation_status:
        task["demo_metadata"]["job_status"] = "FAILED_KB_INPUT"
        update_job(task)
        return {
            'statusCode': 500,
            'body': f'Updated DB. Failed task: {task_id}'
        }
    
    task["demo_metadata"]["job_status"] = "COMPLETED"
    update_job(task)

    # Refresh KB data source
    try:
        bedrock_agent.start_ingestion_job(
            clientToken=str(uuid.uuid4()),
            dataSourceId=KB_DATA_SOURCE_ID,
            description='New asset uploaded',
            knowledgeBaseId=KB_ID
        )
    except Exception as ex:
        logger.error("Failed to trigger ingestion job in KB.")
        logger.error(ex)

    logger.info(f"Successfully processed task: {task_id}")
    return {
        'statusCode': 200,
        'body': f'Updated DB. task: {task_id}'
    }