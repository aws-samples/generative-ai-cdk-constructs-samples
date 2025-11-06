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

import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { BookOpenIcon, PlusCircleIcon, FileTextIcon } from "lucide-react";
import type { ContractType } from "@/lib/types";

interface GuidelinesEmptyStateProps {
  contractType?: ContractType;
  onCreateGuideline?: () => void;
  onImportFromDocument?: () => void;
  showImportOption?: boolean;
}

export function GuidelinesEmptyState({
  contractType,
  onCreateGuideline,
  onImportFromDocument,
  showImportOption = false,
}: GuidelinesEmptyStateProps) {
  const { t } = useTranslation();

  return (
    <div className="rounded-md border">
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <BookOpenIcon className="h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium text-muted-foreground mb-2">
          {t('guidelines.noGuidelines.title')}
        </h3>
        <p className="text-sm text-muted-foreground max-w-md mb-6">
          {contractType
            ? `No guidelines have been created for "${contractType.name}" yet. You can create guidelines manually or import them from a reference contract document.`
            : t('guidelines.noGuidelines.description')
          }
        </p>

        <div className="flex flex-col sm:flex-row gap-3">
          {onCreateGuideline && (
            <Button onClick={onCreateGuideline}>
              <PlusCircleIcon className="mr-2 h-4 w-4" />
              {t('guidelines.createNew')}
            </Button>
          )}

          {showImportOption && onImportFromDocument && (
            <Button variant="outline" onClick={onImportFromDocument}>
              <FileTextIcon className="mr-2 h-4 w-4" />
              Import from Document
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}