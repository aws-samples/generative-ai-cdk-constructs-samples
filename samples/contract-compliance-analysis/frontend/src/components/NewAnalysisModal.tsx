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

import { useState, useEffect } from "react";
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
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { languages } from "@/lib/i18n";
import {
  PlusCircleIcon,
  FileTextIcon,
  UploadIcon,
  GlobeIcon,
  ScaleIcon,
  InfoIcon,
  Loader2Icon,
} from "lucide-react";
import { getLegislations } from "@/lib/api";
import type { Legislation } from "@/lib/types";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import UploadButton from "@/components/UploadButton";
import { ContractTypeSelect } from "@/components/ContractTypeSelect";

interface NewAnalysisModalProps {
  onSubmit: (data: {
    documentS3Key: string;
    description: string;
    contractTypeId: string;
    reportLanguage: string;
    legislationId?: string;
  }) => Promise<void>;
}

export function NewAnalysisModal({ onSubmit }: NewAnalysisModalProps) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const [description, setDescription] = useState("");
  const [documentS3Key, setDocumentS3Key] = useState<string | null>(null);
  const [contractTypeId, setContractTypeId] = useState("");
  const [reportLanguage, setReportLanguage] = useState(i18n.language);
  const [selectedLegislationId, setSelectedLegislationId] =
    useState<string>("");
  const [legislations, setLegislations] = useState<Legislation[]>([]);
  const [isLoadingLegislations, setIsLoadingLegislations] = useState(false);
  const [legislationCheckEnabled, setLegislationCheckEnabled] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Load legislations when legislation check is enabled
  useEffect(() => {
    if (legislationCheckEnabled && open) {
      setIsLoadingLegislations(true);
      getLegislations()
        .then((data) => {
          setLegislations(data);
        })
        .catch((error) => {
          console.error("Failed to load legislations:", error);
          setLegislations([]);
        })
        .finally(() => {
          setIsLoadingLegislations(false);
        });
    } else if (!legislationCheckEnabled) {
      // Reset legislation selection when disabled
      setSelectedLegislationId("");
      setLegislations([]);
    }
  }, [legislationCheckEnabled, open]);

  // Sync report language with UI language changes
  useEffect(() => {
    setReportLanguage(i18n.language);
  }, [i18n.language]);

  const handleSubmit = async () => {
    if (documentS3Key && description.trim() && contractTypeId) {
      setIsSubmitting(true);

      try {
        const submitData: {
          documentS3Key: string;
          description: string;
          contractTypeId: string;
          reportLanguage: string;
          legislationId?: string;
        } = {
          documentS3Key,
          description,
          contractTypeId,
          reportLanguage,
        };

        // Only add legislationId if legislation check is enabled and one is selected
        if (legislationCheckEnabled && selectedLegislationId) {
          submitData.legislationId = selectedLegislationId;
        }

        await onSubmit(submitData);

        // Reset form and close modal only after success
        setDescription("");
        setDocumentS3Key(null);
        setContractTypeId("");
        setReportLanguage(i18n.language);
        setSelectedLegislationId("");
        setLegislationCheckEnabled(false);
        setOpen(false);
      } catch (error) {
        console.error("Failed to create analysis:", error);
        // Modal stays open on error
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  const isSubmitDisabled =
    !documentS3Key ||
    !description.trim() ||
    !contractTypeId ||
    (legislationCheckEnabled && !selectedLegislationId) ||
    isSubmitting;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <PlusCircleIcon className="mr-2 h-4 w-4" />
          {t("newAnalysis.button")}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px] md:max-w-[700px]">
        <DialogHeader>
          <DialogTitle>{t("newAnalysis.title")}</DialogTitle>
          <DialogDescription>{t("newAnalysis.description")}</DialogDescription>
        </DialogHeader>
        <div className="space-y-8 pt-4">
          <div className="space-y-3">
            <Label
              htmlFor="description"
              className="flex items-center gap-2 text-base font-medium"
            >
              <FileTextIcon className="h-4 w-4 text-muted-foreground" />
              {t("newAnalysis.fields.description")}
            </Label>
            <Input
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("newAnalysis.fields.descriptionPlaceholder")}
              className="h-11 w-full"
            />
          </div>

          {/* Contract Upload Field */}
          <div className="space-y-3">
            <Label
              htmlFor="file"
              className="flex items-center gap-2 text-base font-medium"
            >
              <UploadIcon className="h-4 w-4 text-muted-foreground" />
              {t("newAnalysis.fields.file")}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <InfoIcon className="h-4 w-4 cursor-help text-muted-foreground" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{t("newAnalysis.fields.fileTooltip")}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </Label>
            <UploadButton
              uploadPath="documents"
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
          </div>

          {/* Contract Type Field */}
          <ContractTypeSelect
            value={contractTypeId}
            onChange={setContractTypeId}
            required={true}
            disabled={isSubmitting}
          />

          {/* Report Language Field */}
          <div className="space-y-3">
            <Label
              htmlFor="language"
              className="flex items-center gap-2 text-base font-medium"
            >
              <GlobeIcon className="h-4 w-4 text-muted-foreground" />
              {t("newAnalysis.fields.reportLanguage")}
            </Label>
            <Select value={reportLanguage} onValueChange={setReportLanguage}>
              <SelectTrigger id="language" className="h-11 w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {languages.map((lang) => (
                  <SelectItem key={lang.code} value={lang.code}>
                    <span className="flex items-center gap-2">
                      <span className="text-lg">{lang.flag}</span>
                      <span>{t(`languages.${lang.code}`)}</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Legislation Check Field */}
          <div className="space-y-4 rounded-lg border border-slate-300 bg-slate-50 p-4">
            <div className="flex items-center justify-between">
              <Label
                htmlFor="legislationToggle"
                className="flex items-center gap-2 text-base font-medium"
              >
                <ScaleIcon
                  className={`h-4 w-4 transition-colors ${
                    legislationCheckEnabled
                      ? "text-lime-600 dark:text-lime-400"
                      : "text-muted-foreground"
                  }`}
                />
                {t("newAnalysis.fields.legislationCheck")}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <InfoIcon className="h-4 w-4 cursor-help text-muted-foreground" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>
                        {t("newAnalysis.fields.legislationCheckDescription")}
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                {legislationCheckEnabled && (
                  <span className="ml-2 rounded-full bg-lime-100 px-2 py-0.5 text-xs font-medium text-lime-800 dark:bg-lime-900 dark:text-lime-200">
                    {t("common.active")}
                  </span>
                )}
              </Label>
              <Switch
                id="legislationToggle"
                checked={legislationCheckEnabled}
                onCheckedChange={setLegislationCheckEnabled}
                disabled={isSubmitting}
              />
            </div>

            {/* Legislation Select - only show when enabled */}
            {legislationCheckEnabled && (
              <div className="space-y-3 pt-2">
                <Label
                  htmlFor="legislation"
                  className="text-sm font-medium text-muted-foreground"
                >
                  {t("newAnalysis.fields.selectLegislation")}
                </Label>
                <Select
                  value={selectedLegislationId}
                  onValueChange={setSelectedLegislationId}
                  disabled={isLoadingLegislations || isSubmitting}
                >
                  <SelectTrigger id="legislation" className="h-11 w-full">
                    <SelectValue
                      placeholder={
                        isLoadingLegislations
                          ? t("newAnalysis.fields.loadingLegislations")
                          : t("newAnalysis.fields.selectLegislationRequired")
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {legislations.map((legislation) => (
                      <SelectItem key={legislation.id} value={legislation.id}>
                        <div className="flex flex-col">
                          <span className="font-medium">
                            {legislation.name}
                          </span>
                          <span className="text-sm text-muted-foreground">
                            {legislation.subjectMatter}
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        </div>
        <DialogFooter className=" pt-6">
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            className="min-w-[100px]"
          >
            {t("common.cancel")}
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitDisabled}
            className="min-w-[100px]"
          >
            {isSubmitting && (
              <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
            )}
            {isSubmitting ? t("newAnalysis.creating") : t("newAnalysis.create")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
