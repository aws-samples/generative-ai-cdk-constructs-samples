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

import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { DeleteConfirmationDialog } from "@/components/ui/confirmation-dialog";
import {
  EditIcon,
  TrashIcon,
  Loader2Icon,
} from "lucide-react";
import { IMPACT_COLORS } from "@/lib/constants";
import { useTranslation } from "react-i18next";
import type { Guideline, ImpactLevel, ContractType } from "@/lib/types";
import { GuidelinesEmptyState } from "./GuidelinesEmptyState";

interface GuidelinesListProps {
  guidelines: Guideline[];
  onEdit: (guideline: Guideline) => void;
  onDelete: (contractTypeId: string, clauseTypeId: string) => Promise<void>;
  loading: boolean;
  contractType?: ContractType;
  onCreateGuideline?: () => void;
  onImportFromDocument?: () => void;
  showImportOption?: boolean;
}

export function GuidelinesList({
  guidelines,
  onEdit,
  onDelete,
  loading,
  contractType,
  onCreateGuideline,
  onImportFromDocument,
  showImportOption = false,
}: GuidelinesListProps) {
  const { t } = useTranslation();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [guidelineToDelete, setGuidelineToDelete] = useState<Guideline | null>(null);

  const handleDeleteClick = (guideline: Guideline) => {
    setGuidelineToDelete(guideline);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!guidelineToDelete) return;

    const deleteId = `${guidelineToDelete.contractTypeId}-${guidelineToDelete.clauseTypeId}`;
    setDeletingId(deleteId);

    try {
      await onDelete(guidelineToDelete.contractTypeId, guidelineToDelete.clauseTypeId);
      setDeleteDialogOpen(false);
      setGuidelineToDelete(null);
    } finally {
      setDeletingId(null);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setGuidelineToDelete(null);
  };



  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  // Sort guidelines by clause type ID in numeric order
  const sortedGuidelines = [...guidelines].sort((a, b) => {
    const aId = parseInt(a.clauseTypeId, 10);
    const bId = parseInt(b.clauseTypeId, 10);

    // Handle cases where clauseTypeId might not be a pure number
    if (isNaN(aId) && isNaN(bId)) {
      return a.clauseTypeId.localeCompare(b.clauseTypeId);
    }
    if (isNaN(aId)) return 1;
    if (isNaN(bId)) return -1;

    return aId - bId;
  });

  if (loading) {
    return (
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('guidelines.table.columns.name')}</TableHead>
              <TableHead>{t('guidelines.table.columns.impactLevel')}</TableHead>
              <TableHead>{t('guidelines.table.columns.questions')}</TableHead>
              <TableHead>{t('guidelines.table.columns.examples')}</TableHead>
              <TableHead>{t('guidelines.table.columns.updated')}</TableHead>
              <TableHead className="text-right">{t('guidelines.table.columns.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 3 }).map((_, index) => (
              <TableRow key={index}>
                <TableCell>
                  <Skeleton className="h-4 w-32" />
                </TableCell>
                <TableCell>
                  <Skeleton className="h-6 w-16" />
                </TableCell>
                <TableCell>
                  <Skeleton className="h-4 w-8" />
                </TableCell>
                <TableCell>
                  <Skeleton className="h-4 w-8" />
                </TableCell>
                <TableCell>
                  <Skeleton className="h-4 w-20" />
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Skeleton className="h-8 w-8" />
                    <Skeleton className="h-8 w-8" />
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  }

  if (guidelines.length === 0) {
    return (
      <GuidelinesEmptyState
        contractType={contractType}
        onCreateGuideline={onCreateGuideline}
        onImportFromDocument={onImportFromDocument}
        showImportOption={showImportOption}
      />
    );
  }

  return (
    <>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('guidelines.table.columns.name')}</TableHead>
              <TableHead>{t('guidelines.table.columns.impactLevel')}</TableHead>
              <TableHead>{t('guidelines.table.columns.questions')}</TableHead>
              <TableHead>{t('guidelines.table.columns.examples')}</TableHead>
              <TableHead>{t('guidelines.table.columns.updated')}</TableHead>
              <TableHead className="text-right">{t('guidelines.table.columns.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedGuidelines.map((guideline) => {
              const deleteId = `${guideline.contractTypeId}-${guideline.clauseTypeId}`;
              const isDeleting = deletingId === deleteId;

              return (
                <TableRow key={deleteId}>
                  <TableCell>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{guideline.name}</span>
                        {contractType?.isImported && guideline.evaluationQuestions.length === 0 && (
                          <Badge variant="outline" className="text-xs text-amber-600 bg-amber-50 border-amber-200">
                            {t("guidelines.import.status.incomplete")}
                          </Badge>
                        )}
                      </div>
                      <div
                        className="text-xs text-muted-foreground mt-1 max-w-xs truncate"
                        title={guideline.standardWording}
                      >
                        {guideline.standardWording}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="secondary"
                      className={IMPACT_COLORS[guideline.level as ImpactLevel]}
                    >
                      {t(`job.compliance.impactLevel.${guideline.level}`)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <span className={`text-sm font-medium ${
                        guideline.evaluationQuestions.length === 0 ? 'text-amber-600' : 'text-muted-foreground'
                      }`}>
                        {guideline.evaluationQuestions.length}
                      </span>
                      {guideline.evaluationQuestions.length === 0 && contractType?.isImported && (
                        <span className="text-xs text-amber-600">{t("guidelines.import.status.required")}</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <span className="text-sm font-medium text-muted-foreground">
                        {guideline.examples.length}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-muted-foreground">
                      {formatDate(guideline.updatedAt)}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onEdit(guideline)}
                        disabled={isDeleting}
                        aria-label={t('guidelines.actions.edit', { name: guideline.name })}
                      >
                        <EditIcon className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDeleteClick(guideline)}
                        disabled={isDeleting}
                        className="text-red-600 hover:text-red-700"
                        aria-label={t('guidelines.actions.delete', { name: guideline.name })}
                      >
                        {isDeleting ? (
                          <Loader2Icon className="h-4 w-4 animate-spin" />
                        ) : (
                          <TrashIcon className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmationDialog
        open={deleteDialogOpen}
        onOpenChange={handleDeleteCancel}
        itemName={guidelineToDelete?.name || ''}
        itemType="guideline"
        loading={!!deletingId}
        onConfirm={handleDeleteConfirm}
      />
    </>
  );
}