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

import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { S3Client } from "@aws-sdk/client-s3";
import { Upload } from "@aws-sdk/lib-storage";
import { fetchAuthSession } from "aws-amplify/auth";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { UploadIcon, FileTextIcon, ImageIcon, XIcon } from "lucide-react";

/**
 * Configuration object for accepted file types
 * @example
 * ```typescript
 * const config = {
 *   ".pdf": ["application/pdf"],
 *   ".doc": ["application/msword"],
 *   ".docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
 *   "image/*": ["image/*"] // Wildcards supported
 * }
 * ```
 */
interface FileTypeConfig {
  /** Extension as key (e.g., ".pdf", ".jpg", "image/*"), MIME types as values */
  [extension: string]: string[];
}

/**
 * Props for the UploadButton component
 */
interface UploadButtonProps {
  /**
   * S3 upload path (without filename)
   * @default "uploads"
   * @example "documents/analysis"
   */
  uploadPath?: string;

  /**
   * Accepted file types configuration
   * @default { ".pdf": ["application/pdf"], ".doc": [...], ".docx": [...] }
   */
  acceptedTypes?: FileTypeConfig;

  /**
   * Whether to show uploaded file with download link and remove option
   * @default false
   */
  showUploadedFile?: boolean;

  /**
   * Callback fired when file is successfully uploaded
   * @param file - The uploaded file object
   * @param url - Presigned URL for downloading the file
   * @param s3Key - The S3 key/path of the uploaded file
   */
  onFileUploaded?: (file: File, url: string, s3Key: string) => void;

  /**
   * Callback fired when uploaded file is removed
   */
  onFileRemoved?: () => void;
}

const DEFAULT_ACCEPTED_TYPES: FileTypeConfig = {
  ".pdf": ["application/pdf"],
  ".doc": ["application/msword"],
  ".docx": [
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ],
};

/**
 * A versatile file upload button with progress tracking and file management
 *
 * Features:
 * - Configurable file type validation
 * - Progress tracking during upload
 * - Show uploaded files with download links
 * - Remove uploaded files from state
 * - Full i18n support
 * - Presigned URL generation for secure downloads
 *
 * @example
 * ```tsx
 * <UploadButton
 *   uploadPath="analysis-documents"
 *   acceptedTypes={{
 *     ".pdf": ["application/pdf"],
 *     ".jpg": ["image/jpeg"],
 *     ".png": ["image/png"]
 *   }}
 *   showUploadedFile={true}
 *   onFileUploaded={(file, url) => console.log('Uploaded:', file.name, url)}
 * />
 * ```
 */
export default function UploadButton({
  uploadPath = "uploads",
  acceptedTypes = DEFAULT_ACCEPTED_TYPES,
  showUploadedFile = false,
  onFileUploaded,
  onFileRemoved,
}: UploadButtonProps) {
  const { t } = useTranslation();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  /**
   * Generate accept attribute for file input from acceptedTypes config
   */
  const acceptAttribute = Object.keys(acceptedTypes).join(",");

  /**
   * Get all allowed MIME types from acceptedTypes config
   */
  const allowedMimeTypes = Object.values(acceptedTypes).flat();

  /**
   * Get file type icon based on file extension or MIME type
   */
  const getFileIcon = (file: File) => {
    if (file.type.startsWith("image/") || acceptedTypes["image/*"]) {
      return <ImageIcon className="h-4 w-4" />;
    }
    return <FileTextIcon className="h-4 w-4" />;
  };

  /**
   * Handle file selection and upload
   */
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) {
      return;
    }

    // Validate file type
    if (
      !allowedMimeTypes.includes(file.type) &&
      !allowedMimeTypes.includes("*/*")
    ) {
      toast.error(t("upload.error"), {
        description: t("upload.errorType"),
      });
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    const { name: fileName } = file;
    const path = `${uploadPath}/${fileName}`;
    console.log("Uploading file: ", path);

    try {
      // Get Cognito credentials
      const session = await fetchAuthSession();
      if (!session.credentials) {
        throw new Error("No credentials available");
      }

      // Initialize S3 client
      const s3Client = new S3Client({
        region: import.meta.env.VITE_AWS_REGION,
        credentials: session.credentials,
      });

      // Use Upload class for multipart upload with progress
      const upload = new Upload({
        client: s3Client,
        params: {
          Bucket: import.meta.env.VITE_S3_BUCKET_NAME,
          Key: path,
          Body: file,
          ExpectedBucketOwner: import.meta.env.VITE_AWS_ACCOUNT_ID, // Anti-sniping control
        },
      });

      // Track progress
      upload.on("httpUploadProgress", (progress) => {
        if (progress.loaded && progress.total) {
          const percent = Math.round((progress.loaded / progress.total) * 100);
          setUploadProgress(percent);
          console.log(`Upload progress ${percent} %`);
        }
      });

      // Execute upload
      await upload.done();

      console.log("Upload succeeded: ", path);

      // Generate download URL (using Amplify for consistency)
      let downloadUrl = "";
      try {
        const { getUrl } = await import("aws-amplify/storage");
        const urlResult = await getUrl({ path });
        downloadUrl = urlResult.url.toString();
      } catch (urlError) {
        console.warn("Could not generate download URL:", urlError);
      }

      setUploadedFile(file);
      toast.success(t("upload.success"), {
        description: fileName,
      });

      // Call callback if provided
      onFileUploaded?.(file, downloadUrl, path);

      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (error) {
      console.error("Error : ", error);
      let errorDescription = t("upload.errorUnknown");

      if (error instanceof Error) {
        if (error.message.includes("Network")) {
          errorDescription = t("upload.errorNetwork");
        } else if (error.message.includes("size")) {
          errorDescription = t("upload.errorSize");
        } else if (
          error.message.includes("Auth") ||
          error.message.includes("auth")
        ) {
          errorDescription = t("upload.errorAuth");
        } else if (error.message.includes("ExpectedBucketOwner")) {
          errorDescription = "Bucket ownership verification failed";
        }
      }

      toast.error(t("upload.error"), {
        description: errorDescription,
      });
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  /**
   * Handle removing uploaded file from state
   */
  const handleRemoveFile = () => {
    setUploadedFile(null);
    onFileRemoved?.();
  };

  /**
   * Handle opening file input dialog
   */
  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="space-y-3">
      <input
        ref={fileInputRef}
        type="file"
        accept={acceptAttribute}
        onChange={handleFileChange}
        className="hidden"
        disabled={isUploading}
      />

      {isUploading ? (
        <div className="flex items-center gap-2">
          <Button disabled className="relative w-full gap-1 pb-4 !opacity-100">
            <UploadIcon size={16} className="mr-2" />
            <span className="text-sm">{t("upload.uploading")}</span>
            <Progress
              value={uploadProgress}
              className="absolute bottom-[4px] h-[4px] w-[calc(100%-8px)] bg-primary-foreground/20 [&>div]:rounded-full [&>div]:bg-lime-500"
            />
            <Badge className="-mr-3 ml-2 bg-primary-foreground/20 text-primary-foreground">
              {uploadProgress} <span className="ml-1 font-bold">%</span>
            </Badge>
          </Button>
        </div>
      ) : (
        showUploadedFile &&
        !uploadedFile && (
          <Button className="w-full" onClick={handleButtonClick}>
            <UploadIcon size={16} className="mr-2" />
            {t("upload.button")}
          </Button>
        )
      )}

      {/* Show uploaded file if enabled and file exists */}
      {showUploadedFile && uploadedFile && (
        <div className="flex items-center gap-2 rounded-lg border border-slate-200/70 bg-slate-200/20 p-3">
          <div className="flex flex-1 items-center gap-2">
            {getFileIcon(uploadedFile)}
            <span className="truncate text-sm font-medium">
              {uploadedFile.name}
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRemoveFile}
            className="h-8 w-8 cursor-pointer p-0 text-destructive hover:bg-destructive/20 hover:text-destructive"
            title={t("upload.removeFile")}
          >
            <XIcon size={18} />
          </Button>
        </div>
      )}
    </div>
  );
}
