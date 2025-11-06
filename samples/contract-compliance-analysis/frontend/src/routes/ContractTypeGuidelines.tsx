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

import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router";
import { useTranslation } from "react-i18next";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ErrorBoundaryWrapper } from "@/components/ui/error-boundary";
import { LoadingState } from "@/components/ui/loading-spinner";
import { ErrorBanner } from "@/components/ui/error-message";
import {
  PlusCircleIcon,
  BookOpenIcon,
  Loader2Icon,
  ArrowLeftIcon,
  SettingsIcon,
  AlertCircleIcon,
} from "lucide-react";
import { getContractType, updateContractType } from "@/lib/api";
import { useGuidelines } from "@/hooks/useGuidelines";
import { guidelineToasts } from "@/lib/toast";
import { toast } from "sonner";
import { parseServerError } from "@/lib/validation";
import type {
  Guideline,
  ContractType,
  GuidelineFormData,
  GuidelinesFilters
} from "@/lib/types";
import { getErrorMessage } from "@/lib/utils";
import { GuidelinesList } from "@/components/guidelines/GuidelinesList";
import { GuidelineForm } from "@/components/guidelines/GuidelineForm";
import { GuidelinesFilters as GuidelinesFiltersComponent } from "@/components/guidelines/GuidelinesFilters";

export function ContractTypeGuidelines() {
  const { t } = useTranslation();
  const { contractTypeId } = useParams<{ contractTypeId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Use the custom guidelines hook
  const {
    guidelines,
    loading: guidelinesLoading,
    error: guidelinesError,
    loadGuidelines,
    createNewGuideline,
    updateExistingGuideline,
    deleteExistingGuideline,
    clearError: clearGuidelinesError,
  } = useGuidelines();

  // Contract type state
  const [contractType, setContractType] = useState<ContractType | null>(null);
  const [contractTypeLoading, setContractTypeLoading] = useState(true);
  const [contractTypeError, setContractTypeError] = useState<string | null>(null);

  // Modal state management for create/edit operations
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingGuideline, setEditingGuideline] = useState<Guideline | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Filter state from URL params
  const filters: Omit<GuidelinesFilters, 'contractTypeId'> = useMemo(() => ({
    search: searchParams.get('search') || '',
    level: searchParams.get('level') || '',
  }), [searchParams]);

  // Load contract type on component mount
  useEffect(() => {
    const loadContractTypeData = async () => {
      if (!contractTypeId) {
        setContractTypeError("Contract type ID is required");
        setContractTypeLoading(false);
        return;
      }

      try {
        setContractTypeLoading(true);
        const type = await getContractType(contractTypeId);
        setContractType(type);
      } catch (e) {
        console.error("Failed to load contract type:", e);
        setContractTypeError(getErrorMessage(e));
      } finally {
        setContractTypeLoading(false);
      }
    };
    loadContractTypeData();
  }, [contractTypeId]);

  // Load guidelines when contract type or filters change
  useEffect(() => {
    if (contractTypeId) {
      loadGuidelines(contractTypeId, {
        search: filters.search,
        level: filters.level,
      });
    }
  }, [contractTypeId, filters.search, filters.level, loadGuidelines]);

  // Filter handlers
  const handleSearchChange = (search: string) => {
    setSearchParams((prev: URLSearchParams) => {
      if (search) {
        prev.set('search', search);
      } else {
        prev.delete('search');
      }
      return prev;
    });
  };

  const handleLevelFilterChange = (level: string) => {
    setSearchParams((prev: URLSearchParams) => {
      if (level && level !== 'all') {
        prev.set('level', level);
      } else {
        prev.delete('level');
      }
      return prev;
    });
  };

  const clearFilters = () => {
    setSearchParams((prev: URLSearchParams) => {
      prev.delete('search');
      prev.delete('level');
      return prev;
    });
  };

  // CRUD handlers
  const handleCreate = () => {
    setEditingGuideline(null);
    setFormError(null);
    setCreateModalOpen(true);
  };

  const handleEdit = (guideline: Guideline) => {
    setEditingGuideline(guideline);
    setFormError(null);
    setEditModalOpen(true);
  };

  const handleCreateSubmit = async (formData: GuidelineFormData) => {
    if (!contractTypeId) return;

    setIsSubmitting(true);
    setFormError(null);

    try {
      const newGuideline = await createNewGuideline(contractTypeId, formData);
      guidelineToasts.createSuccess(newGuideline?.name || 'Guideline');
      setCreateModalOpen(false);
    } catch (e) {
      const errorMessage = parseServerError(e);
      setFormError(errorMessage);
      guidelineToasts.createError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditSubmit = async (formData: GuidelineFormData) => {
    if (!editingGuideline) return;

    setIsSubmitting(true);
    setFormError(null);

    try {
      // For editing, we exclude clauseTypeId from the update data
      const { name, standardWording, level, evaluationQuestions, examples } = formData;
      const updateData = { name, standardWording, level, evaluationQuestions, examples };

      const updatedGuideline = await updateExistingGuideline(
        editingGuideline.contractTypeId,
        editingGuideline.clauseTypeId,
        updateData
      );
      guidelineToasts.updateSuccess(updatedGuideline?.name || 'Guideline');
      setEditModalOpen(false);
      setEditingGuideline(null);
    } catch (e) {
      const errorMessage = parseServerError(e);
      setFormError(errorMessage);
      guidelineToasts.updateError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (contractTypeId: string, clauseTypeId: string) => {
    const guideline = guidelines.find(g =>
      g.contractTypeId === contractTypeId && g.clauseTypeId === clauseTypeId
    );

    if (!guideline) return;

    try {
      await deleteExistingGuideline(contractTypeId, clauseTypeId);
      guidelineToasts.deleteSuccess(guideline?.name || 'Guideline');
    } catch (e) {
      const errorMessage = parseServerError(e);
      guidelineToasts.deleteError(errorMessage);
    }
  };

  const clearFormError = () => {
    setFormError(null);
  };

  const handleBackToContractTypes = () => {
    navigate('/contract-types');
  };

  const handleToggleActive = async (contractType: ContractType) => {
    // Validation for activation
    if (!contractType.isActive) {
      // Check if there are guidelines
      if (guidelines.length === 0) {
        toast.error(t("guidelines.import.validation.noGuidelines"));
        return;
      }

      // Check if guidelines are complete (have evaluation questions)
      const incompleteGuidelines = guidelines.filter(g =>
        !g.evaluationQuestions || g.evaluationQuestions.length === 0
      );

      if (incompleteGuidelines.length > 0) {
        toast.error(t("guidelines.import.validation.incompleteGuidelines", { count: incompleteGuidelines.length }));
        return;
      }
    }

    try {
      // Send all required fields along with the isActive change
      const updatedContractType = await updateContractType(contractType.contractTypeId, {
        name: contractType.name,
        description: contractType.description,
        companyPartyType: contractType.companyPartyType,
        otherPartyType: contractType.otherPartyType,
        highRiskThreshold: contractType.highRiskThreshold,
        mediumRiskThreshold: contractType.mediumRiskThreshold,
        lowRiskThreshold: contractType.lowRiskThreshold,
        defaultLanguage: contractType.defaultLanguage,
        isActive: !contractType.isActive
      });

      // Update local state
      setContractType(updatedContractType);

      toast.success(`Contract type ${contractType.isActive ? 'deactivated' : 'activated'} successfully`);
    } catch (e) {
      console.error("Failed to toggle contract type status:", e);
      toast.error(`Failed to update contract type: ${getErrorMessage(e)}`);
    }
  };

  // Loading state for contract type
  if (contractTypeLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpenIcon className="h-5 w-5" />
            {t('guidelines.title')}
          </CardTitle>
          <CardDescription>
            {t('guidelines.description')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <LoadingState loading={true}>
            <div className="flex items-center gap-2">
              <Loader2Icon className="h-5 w-5 animate-spin" />
              <span>{t('contractType.loading')}</span>
            </div>
          </LoadingState>
        </CardContent>
      </Card>
    );
  }

  // Error state for contract type
  if (contractTypeError || !contractType) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpenIcon className="h-5 w-5" />
            {t('guidelines.title')}
          </CardTitle>
          <CardDescription>
            {t('guidelines.description')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ErrorBanner error={contractTypeError || "Contract type not found"} />
          <div className="mt-4">
            <Button onClick={handleBackToContractTypes} variant="outline">
              <ArrowLeftIcon className="mr-2 h-4 w-4" />
              Back to Contract Types
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <ErrorBoundaryWrapper>
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleBackToContractTypes}
                    className="p-1 h-auto"
                  >
                    <ArrowLeftIcon className="h-4 w-4" />
                  </Button>
                  <CardTitle className="flex items-center gap-2">
                    <BookOpenIcon className="h-5 w-5" />
                    {t("guidelines.guidelinesFor")} {contractType.name}
                    {contractType.isImported && (
                      <Badge variant="outline" className="text-xs">
                        {t("guidelines.import.status.imported")}
                      </Badge>
                    )}
                  </CardTitle>
                </div>
                <div>
                  <CardDescription>
                    {t('guidelines.description')}
                  </CardDescription>
                  <div className="mt-1 flex items-center gap-4 text-sm">
                    <span className="flex items-center gap-1">
                      <SettingsIcon className="h-3 w-3" />
                      {contractType.description}
                    </span>
                    <span className="text-muted-foreground">
                      ID: {contractType.contractTypeId}
                    </span>
                  </div>
                  {contractType.isImported && contractType.importSourceDocument && (
                    <div className="mt-2 text-sm text-muted-foreground">
                      Imported from: {contractType.importSourceDocument.split('/').pop()}
                    </div>
                  )}
                </div>
              </div>
              <Button onClick={handleCreate}>
                <PlusCircleIcon className="mr-2 h-4 w-4" />
                {t('guidelines.createNew')}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {/* Import Status Banner */}
            {contractType.isImported && !contractType.isActive && (
              <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0">
                    <AlertCircleIcon className="h-5 w-5 text-amber-600" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-sm font-medium text-amber-800">
                      {t("guidelines.import.status.activateTitle")}
                    </h4>
                    <p className="mt-1 text-sm text-amber-700">
                      {t("guidelines.import.status.activateDescription")}
                    </p>
                    <div className="mt-3">
                      <Button
                        size="sm"
                        onClick={() => handleToggleActive(contractType)}
                        className="bg-amber-600 hover:bg-amber-700 text-white"
                      >
                        {t("guidelines.import.status.activate")}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Guidelines Error Banner */}
            {guidelinesError && (
              <div className="mb-4">
                <ErrorBanner
                  error={guidelinesError}
                  onDismiss={clearGuidelinesError}
                />
              </div>
            )}

            <GuidelinesFiltersComponent
              searchTerm={filters.search}
              onSearchChange={handleSearchChange}
              levelFilter={filters.level}
              onLevelFilterChange={handleLevelFilterChange}
              contractTypeId={contractTypeId || ''}
              onContractTypeChange={() => {}} // Not used in this context
              contractTypes={[]} // Not used in this context
              onClearFilters={clearFilters}
              hideContractTypeFilter={true} // Hide contract type filter since we're in a specific contract type context
            />

            <div className="mt-6">
              <GuidelinesList
                guidelines={guidelines}
                onEdit={handleEdit}
                onDelete={handleDelete}
                loading={guidelinesLoading}
                contractType={contractType}
                onCreateGuideline={handleCreate}
                showImportOption={false} // Will be enabled in future tasks
              />
            </div>
          </CardContent>
        </Card>

        {/* Create Modal */}
        <Dialog open={createModalOpen} onOpenChange={setCreateModalOpen}>
          <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{t('guidelines.form.title.create')}</DialogTitle>
              <DialogDescription>
                {t('guidelines.form.title.create')} for {contractType.name}
              </DialogDescription>
            </DialogHeader>
            <GuidelineForm
              contractTypeId={contractTypeId || ''}
              contractType={contractType}
              onSubmit={handleCreateSubmit}
              onCancel={() => setCreateModalOpen(false)}
              loading={isSubmitting}
              error={formError}
              onClearError={clearFormError}
            />
          </DialogContent>
        </Dialog>

        {/* Edit Modal */}
        <Dialog open={editModalOpen} onOpenChange={setEditModalOpen}>
          <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{t('guidelines.form.title.edit')}</DialogTitle>
              <DialogDescription>
                {editingGuideline ? `${t('guidelines.form.title.edit')} "${editingGuideline.name}"` : t('guidelines.form.title.edit')}
              </DialogDescription>
            </DialogHeader>
            {editingGuideline && (
              <GuidelineForm
                guideline={editingGuideline}
                contractTypeId={contractTypeId || ''}
                contractType={contractType}
                onSubmit={handleEditSubmit}
                onCancel={() => {
                  setEditModalOpen(false);
                  setEditingGuideline(null);
                }}
                loading={isSubmitting}
                error={formError}
                onClearError={clearFormError}
              />
            )}
          </DialogContent>
        </Dialog>
      </div>
    </ErrorBoundaryWrapper>
  );
}