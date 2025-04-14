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

import { useLoaderData, Await, useRevalidator } from "react-router-dom";
import { Suspense, useState, useEffect } from "react";

import { columns } from "@/components/jobs/columns";
import {
  DataTable as JobsTable,
  DataTableSkeleton,
} from "@/components/jobs/data-table";

import { Input } from "@/components/ui/input";
import { createJob, uploadDocument } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { IconRefresh } from "@tabler/icons-react";
import { Job } from "@/types";

type JobsData = {
  jobs: Job[];
};

enum Modality {
  Document = "Document",
  Image = "Image",
  Video = "Video",
  Audio = "Audio",
}

export default function Home() {
  const loaderData = useLoaderData() as JobsData;
  const revalidator = useRevalidator();
  const [showTooltip, setShowTooltip] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedProjectArn, setSelectedProjectArn] = useState<string>('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  
  // Load the selected project ARN from localStorage when the component mounts
  useEffect(() => {
    const storedProjectArn = localStorage.getItem('selectedProjectArn');
    if (storedProjectArn) {
      setSelectedProjectArn(storedProjectArn);
    }
  }, []);

  const handleOnChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    setErrorMessage(null); // Clear error message when clicking the button
    setUploadSuccess(null); // Clear success message
    const file = event.target.files?.[0];

    if (file) {
      const validFileTypes = [
        { type: 'application/pdf', maxSize: 500 * 1024 * 1024, modality: Modality.Document }, // PDF, max 500MB
        { type: 'image/jpeg', maxSize: 5 * 1024 * 1024, modality: Modality.Image }, // JPEG, max 5MB
        { type: 'image/png', maxSize: 5 * 1024 * 1024, modality: Modality.Image }, // PNG, max 5MB
        { type: 'image/tiff', maxSize: 500 * 1024 * 1024, modality: Modality.Document }, // TIFF, max 500MB
        { type: 'video/mp4', maxSize: 2 * 1024 * 1024 * 1024, modality: Modality.Video }, // MP4, max 2GB
        { type: 'video/quicktime', maxSize: 2 * 1024 * 1024 * 1024, modality: Modality.Video }, // MOV, max 2GB
        { type: 'video/x-m4v', maxSize: 2 * 1024 * 1024 * 1024, modality: Modality.Video }, // M4A, max 2GB
        { type: 'audio/flac', maxSize: 2 * 1024 * 1024 * 1024, modality: Modality.Audio }, // FLAC, max 2GB
        { type: 'audio/m4a', maxSize: 2 * 1024 * 1024 * 1024, modality: Modality.Audio }, // M4A, max 2GB
        { type: 'audio/mpeg', maxSize: 2 * 1024 * 1024 * 1024, modality: Modality.Audio }, // MP3, max 2GB
        { type: 'audio/ogg', maxSize: 2 * 1024 * 1024 * 1024, modality: Modality.Audio }, // Ogg, max 2GB
        { type: 'audio/wav', maxSize: 2 * 1024 * 1024 * 1024, modality: Modality.Audio }, // WAV, max 2GB
        { type: 'audio/webm', maxSize: 2 * 1024 * 1024 * 1024, modality: Modality.Audio }, // WebM, max 2GB
        { type: 'video/x-matroska', maxSize: 2 * 1024 * 1024 * 1024, modality: Modality.Video }, // MKV, max 2GB
        // Additional video codecs can be handled by the video container types
      ];

      const validFile = validFileTypes.find(validFile => 
        file.type === validFile.type && file.size <= validFile.maxSize
      );

      if (!validFile) {
        setErrorMessage(`Invalid file type or size: ${file.type}, File size: ${file.size}`); // Step 2: Set error message
        return; // Exit if the file is not valid
      }

      try {
        // Check if a project is selected
        if (!selectedProjectArn) {
          setErrorMessage("Please select a project first from the BDA Control Plane page");
          return;
        }
        
        // Parse the project ARN to extract account ID and region
        const arnParts = selectedProjectArn.split(':');
        if (arnParts.length < 6) {
          setErrorMessage("Invalid project ARN format");
          return;
        }
        
        const region = arnParts[3];
        const accountId = arnParts[4];
        const dataAutomationProfileArn = `arn:aws:bedrock:${region}:${accountId}:data-automation-profile/us.data-automation-v1`;
        
        // Set uploading state to true
        setIsUploading(true);
        
        await uploadDocument(file, file?.name);

        await createJob({
          filename: file?.name, 
          modality: validFile.modality, 
          bda_project_arn: selectedProjectArn,
          dataAutomationProfileArn: dataAutomationProfileArn
        });
        
        // Set success message
        setUploadSuccess(`Successfully uploaded ${file.name}`);
        
        revalidator.revalidate();
        setErrorMessage(null); // Clear error message on success
      } catch (error) {
        setErrorMessage(`Error: ${error}`); // Step 2: Set error message on catch
      } finally {
        // Reset uploading state
        setIsUploading(false);
      }
    }
  };


  return (
    <div>
      {errorMessage && ( // Step 3: Render error message
        <div className="bg-red-500 text-white p-2 rounded mb-4">
          {errorMessage}
        </div>
      )}
      {uploadSuccess && (
        <div className="bg-green-500 text-white p-2 rounded mb-4">
          {uploadSuccess}
        </div>
      )}
      <div className="mb-3 flex justify-between ">
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={() => {
              revalidator.revalidate();
            }}
            disabled={revalidator.state === "loading"}
          >
            <span
              className={revalidator.state === "loading" ? "animate-spin" : ""}
            >
              <IconRefresh className="-scale-x-100" />
            </span>
          </Button>
        </div>
        <div className="grid gap-3 relative">
          <Input 
            id="document" 
            type="file" 
            onChange={handleOnChange} 
            onMouseEnter={() => setShowTooltip(true)} 
            onMouseLeave={() => setShowTooltip(false)} 
            disabled={isUploading}
          />
          {isUploading && (
            <div className="absolute bg-blue-500 text-white text-sm p-2 rounded shadow-md" style={{ top: '100%', left: '0', zIndex: 10 }}>
              Uploading file...
            </div>
          )}
          {showTooltip && !isUploading && (
            <div className="absolute bg-gray-700 text-white text-sm p-2 rounded shadow-md" style={{ top: '100%', left: '0', whiteSpace: 'pre-line' }}>
            📄: PDF, TIFF, max 500MB{"\n"}
            🖼️: JPEG, PNG, max 5 MB.{"\n"}
            📹: MP4, MOV, MKV with H.264, H.265, VP8, VP9, max 2GB.{"\n"}
            🎧: FLAC, M4A, MP3, Ogg, WAV, WebM, max 2GB.
          </div>
          )}
        </div>
      </div>

      <Suspense fallback={<DataTableSkeleton />}>
        <Await resolve={loaderData.jobs} errorElement={<p>Error</p>}>
          {(loadedData) => <JobsTable columns={columns} data={loadedData} />}
          
        </Await>
      </Suspense>
    </div>
  );
}
