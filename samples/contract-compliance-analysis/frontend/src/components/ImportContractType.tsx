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

import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  UploadIcon,
  Loader2Icon,
  CheckCircleIcon,
  AlertCircleIcon,
  RefreshCwIcon,
} from "lucide-react";
import { toast } from "sonner";
import UploadButton from "@/components/UploadButton";
import { createImportJob, getImportJobStatus } from "@/lib/api";
import type { ImportJob } from "@/lib/types";
import { getErrorMessage } from "@/lib/utils";

interface ImportContractTypeProps {
  onImportComplete: (contractTypeId: string) => void;
  onCancel?: () => void;
  trigger?: React.ReactNode;
}

type ImportState = 'idle' | 'uploading' | 'processing' | 'completed' | 'failed';

export function ImportContractType({
  onImportComplete,
  onCancel,
  trigger
}: ImportContractTypeProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [documentS3Key, setDocumentS3Key] = useState<string | null>(null);
  const [importState, setImportState] = useState<ImportState>('idle');
  const [importJob, setImportJob] = useState<ImportJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // Start polling for import status
  const startPolling = (importJobId: string) => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const status = await getImportJobStatus(importJobId);

        setImportJob(prev => prev ? { ...prev, ...status } : null);

        if (status.status === 'completed') {
          setImportState('completed');
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
          }
          toast.success(t("import.success"));

          // Auto-navigate after a short delay to show success state
          setTimeout(() => {
            const contractTypeId = status.contractTypeId || importJob?.contractTypeId;
            if (contractTypeId) {
              setOpen(false);
              onImportComplete(contractTypeId);
              // Reset state after navigation
              setTimeout(() => {
                setDocumentS3Key(null);
                setImportState('idle');
                setImportJob(null);
                setError(null);
              }, 100);
            }
          }, 2000); // Show success state for 2 seconds before auto-navigating
        } else if (status.status === 'failed') {
          setImportState('failed');
          setError(status.error || t("import.errorUnknown"));
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
          }
          toast.error(t("import.error"), {
            description: status.error || t("import.errorUnknown"),
          });
        }
      } catch (e) {
        console.error("Failed to poll import status:", e);
        setImportState('failed');
        setError(getErrorMessage(e));
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
        }
      }
    }, 2000); // Poll every 2 seconds
  };

  const handleSubmit = async () => {
    if (!documentS3Key) {
      toast.error(t("import.errorNoFile"));
      return;
    }

    setImportState('processing');
    setError(null);

    try {
      console.log('Submitting import with documentS3Key:', documentS3Key);
      const result = await createImportJob({
        documentS3Key,
      });

      const newImportJob: ImportJob = {
        importJobId: result.importJobId,
        contractTypeId: result.contractTypeId,
        status: result.status as 'processing' | 'completed' | 'failed',
        progress: 0,
      };

      setImportJob(newImportJob);
      startPolling(result.importJobId);

      toast.success(t("import.started"));
    } catch (e) {
      console.error("Failed to start import:", e);
      setImportState('failed');
      setError(getErrorMessage(e));
      toast.error(t("import.error"), {
        description: getErrorMessage(e),
      });
    }
  };

  const handleComplete = () => {
    const contractTypeId = importJob?.contractTypeId;
    if (contractTypeId) {
      // Close the modal first, then navigate
      setOpen(false);
      onImportComplete(contractTypeId);
      // Reset state after navigation
      setTimeout(() => {
        setDocumentS3Key(null);
        setImportState('idle');
        setImportJob(null);
        setError(null);
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
        }
      }, 100);
    }
  };

  const handleRetry = () => {
    setImportState('idle');
    setError(null);
    setImportJob(null);
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }
  };

  const handleClose = () => {
    // Stop polling
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    // Reset state
    setDocumentS3Key(null);
    setImportState('idle');
    setImportJob(null);
    setError(null);
    setOpen(false);

    // Call onCancel if provided
    onCancel?.();
  };

  const isSubmitDisabled = !documentS3Key || importState === 'processing';

  const renderContent = () => {
    switch (importState) {
      case 'processing':
        return (
          <div className="space-y-6 py-4">
            <div className="text-center space-y-4">
              <div className="flex justify-center">
                <Loader2Icon className="h-12 w-12 animate-spin text-primary" />
              </div>
              <div>
                <h3 className="text-lg font-medium">{t("import.processing.title")}</h3>
                <p className="text-sm text-muted-foreground">
                  {t("import.processing.description")}
                </p>
              </div>
            </div>

            {importJob && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span>{t("import.processing.progress")}</span>
                  <Badge variant="secondary">
                    {importJob.progress}%
                  </Badge>
                </div>
                <Progress value={importJob.progress} className="h-2" />
                <div className="text-xs text-muted-foreground text-center">
                  {t("import.processing.steps")}
                </div>
              </div>
            )}
          </div>
        );

      case 'completed':
        return (
          <div className="space-y-6 py-4">
            <div className="text-center space-y-4">
              <div className="flex justify-center">
                <CheckCircleIcon className="h-12 w-12 text-green-600" />
              </div>
              <div>
                <h3 className="text-lg font-medium text-green-600">
                  {t("import.completed.title")}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {t("import.completed.description")}
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  {t("import.completed.redirecting")}
                </p>
              </div>
            </div>
          </div>
        );

      case 'failed':
        return (
          <div className="space-y-6 py-4">
            <div className="text-center space-y-4">
              <div className="flex justify-center">
                <AlertCircleIcon className="h-12 w-12 text-red-600" />
              </div>
              <div>
                <h3 className="text-lg font-medium text-red-600">
                  {t("import.failed.title")}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {error || t("import.errorUnknown")}
                </p>
              </div>
            </div>
          </div>
        );

      default:
        return (
          <div className="space-y-6 py-4">
            <div className="space-y-3">
              <Label
                htmlFor="file"
                className="flex items-center gap-2 text-base font-medium"
              >
                <UploadIcon className="h-4 w-4 text-muted-foreground" />
                {t("import.fields.file")} *
              </Label>
              <UploadButton
                uploadPath="import-documents"
                acceptedTypes={{
                  ".pdf": ["application/pdf"],
                  ".doc": ["application/msword"],
                  ".docx": [
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                  ],
                  ".txt": ["text/plain"],
                }}
                showUploadedFile={true}
                onFileUploaded={(_file, _url, s3Key) => {
                  setDocumentS3Key(s3Key);
                }}
                onFileRemoved={() => {
                  setDocumentS3Key(null);
                }}
              />
              <p className="text-xs text-muted-foreground">
                {t("import.fields.fileHint")}
              </p>
            </div>
          </div>
        );
    }
  };

  const renderFooter = () => {
    switch (importState) {
      case 'processing':
        return (
          <DialogFooter>
            <Button variant="outline" onClick={handleClose}>
              {t("common.cancel")}
            </Button>
          </DialogFooter>
        );

      case 'completed':
        return (
          <DialogFooter>
            <Button variant="outline" onClick={handleClose}>
              {t("import.completed.close")}
            </Button>
            <Button onClick={handleComplete} className="bg-primary hover:bg-primary/90">
              {t("import.completed.continueNow")}
            </Button>
          </DialogFooter>
        );

      case 'failed':
        return (
          <DialogFooter>
            <Button variant="outline" onClick={handleClose}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleRetry} className="flex items-center gap-2">
              <RefreshCwIcon className="h-4 w-4" />
              {t("import.failed.retry")}
            </Button>
          </DialogFooter>
        );

      default:
        return (
          <DialogFooter>
            <Button variant="outline" onClick={handleClose}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleSubmit} disabled={isSubmitDisabled}>
              {t("import.start")}
            </Button>
          </DialogFooter>
        );
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(newOpen) => {
        // Prevent closing during processing unless explicitly handled
        if (!newOpen && importState === 'processing') {
          return;
        }
        if (!newOpen) {
          handleClose();
        } else {
          setOpen(newOpen);
        }
      }}
    >
      <DialogTrigger asChild>
        {trigger || (
          <Button>
            <UploadIcon className="mr-2 h-4 w-4" />
            {t("import.button")}
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px] md:max-w-[700px]">
        <DialogHeader>
          <DialogTitle>{t("import.title")}</DialogTitle>
          <DialogDescription>{t("import.description")}</DialogDescription>
        </DialogHeader>
        {renderContent()}
        {renderFooter()}
      </DialogContent>
    </Dialog>
  );
}