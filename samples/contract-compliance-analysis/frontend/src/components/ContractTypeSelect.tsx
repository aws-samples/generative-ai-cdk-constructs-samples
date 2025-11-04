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

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircleIcon, FileText } from "lucide-react";
import { getContractTypes } from "@/lib/api";
import type { ContractType } from "@/lib/types";
import { cn, getErrorMessage } from "@/lib/utils";

interface ContractTypeSelectProps {
  value: string;
  onChange: (contractTypeId: string) => void;
  required?: boolean;
  disabled?: boolean;
  className?: string;
}

export function ContractTypeSelect({
  value,
  onChange,
  required = false,
  disabled = false,
  className,
}: ContractTypeSelectProps) {
  const { t } = useTranslation();
  const [contractTypes, setContractTypes] = useState<ContractType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadContractTypes = async () => {
      try {
        setLoading(true);
        setError(null);
        const types = await getContractTypes();
        const activeTypes = types.filter((type) => type.isActive);
        setContractTypes(activeTypes);

        // If no value is selected and there's only one active type, auto-select it
        if (!value && activeTypes.length === 1) {
          onChange(activeTypes[0].contractTypeId);
        }
      } catch (e) {
        console.error("Failed to load contract types:", e);
        setError(getErrorMessage(e));
      } finally {
        setLoading(false);
      }
    };

    loadContractTypes();
  }, [value, onChange]);

  if (loading) {
    return (
      <div className="space-y-2">
        <Label className="flex items-center gap-2 text-base font-medium">
          <FileText className="h-4 w-4 text-muted-foreground" />
          {t("contractType.label")}
          {required && <span className="text-red-500">*</span>}
        </Label>
        <Skeleton className="h-11 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-2">
        <Label className="flex items-center gap-2 text-base font-medium">
          <FileText className="h-4 w-4 text-muted-foreground" />
          {t("contractType.label")}
          {required && <span className="text-red-500">*</span>}
        </Label>
        <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <AlertCircleIcon className="h-4 w-4" />
          <span>
            {t("contractType.loadError")}: {error}
          </span>
        </div>
      </div>
    );
  }

  if (contractTypes.length === 0) {
    return (
      <div className="space-y-2">
        <Label className="flex items-center gap-2 text-base font-medium">
          <FileText className="h-4 w-4 text-muted-foreground" />
          {t("contractType.label")}
          {required && <span className="text-red-500">*</span>}
        </Label>
        <div className="flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
          <AlertCircleIcon className="h-4 w-4" />
          <span>{t("contractType.noTypesAvailable")}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <Label
        htmlFor="contract-type"
        className="flex items-center gap-2 text-base font-medium"
      >
        <FileText className="h-4 w-4 text-muted-foreground" />
        {t("contractType.label")}
        {required && <span className="text-red-500">*</span>}
      </Label>
      <Select value={value} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger
          id="contract-type"
          size="lg"
          className={cn(`h-14 w-full py-4 ${className}`)}
        >
          <SelectValue placeholder={t("contractType.placeholder")} />
        </SelectTrigger>
        <SelectContent>
          {contractTypes.map((contractType) => (
            <SelectItem
              key={contractType.contractTypeId}
              value={contractType.contractTypeId}
            >
              <div className="flex flex-col items-start">
                <span className="font-medium">{contractType.name}</span>
                {contractType.description && (
                  <span className="text-xs text-muted-foreground">
                    {contractType.description}
                  </span>
                )}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
