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

import { useState, useEffect, useRef, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ErrorBanner, FieldError } from "@/components/ui/error-message";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Loader2Icon,
  PlusIcon,
  XIcon,
  SparklesIcon,
} from "lucide-react";
import { GuidelineValidator } from "@/lib/validation";
import { useFormReset } from "@/hooks/useFormReset";
import { IMPACT_COLORS } from "@/lib/constants";
import { useTranslation } from "react-i18next";
import { generateEvaluationQuestions, generateClauseExamples } from "@/lib/api";
import { GenerationReviewDialog } from "./GenerationReviewDialog";
import type { Guideline, GuidelineFormData, ImpactLevel, ContractType } from "@/lib/types";

interface GuidelineFormProps {
  guideline?: Guideline;
  contractTypeId: string;
  contractType?: ContractType;
  onSubmit: (data: GuidelineFormData) => Promise<void>;
  onCancel: () => void;
  loading: boolean;
  error?: string | null;
  onClearError?: () => void;
}

export function GuidelineForm({
  guideline,
  contractTypeId,
  contractType,
  onSubmit,
  onCancel,
  loading,
  error,
  onClearError
}: GuidelineFormProps) {
  const { t } = useTranslation();
  const isEditing = !!guideline;

  const impactLevels: { value: ImpactLevel; label: string; description: string }[] = [
    {
      value: 'high',
      label: t('job.compliance.impactLevel.high'),
      description: t('guidelines.form.fields.impactLevel.description.high')
    },
    {
      value: 'medium',
      label: t('job.compliance.impactLevel.medium'),
      description: t('guidelines.form.fields.impactLevel.description.medium')
    },
    {
      value: 'low',
      label: t('job.compliance.impactLevel.low'),
      description: t('guidelines.form.fields.impactLevel.description.low')
    },
  ];

  // Initial form data
  const initialFormData = useMemo(() => ({
    name: guideline?.name || '',
    standardWording: guideline?.standardWording || '',
    level: guideline?.level || 'medium',
    evaluationQuestions: (guideline?.evaluationQuestions && guideline.evaluationQuestions.length > 0) ? guideline.evaluationQuestions : [''],
    examples: (guideline?.examples && guideline.examples.length > 0) ? guideline.examples : [''],
  }), [guideline]);

  // Form state
  const [formData, setFormData] = useState<GuidelineFormData>(() => initialFormData);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [newQuestion, setNewQuestion] = useState('');
  const [newExample, setNewExample] = useState('');

  // AI Generation state
  const [generatingQuestions, setGeneratingQuestions] = useState(false);
  const [generatingExamples, setGeneratingExamples] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [reviewDialogType, setReviewDialogType] = useState<'questions' | 'examples'>('questions');
  const [generatedContent, setGeneratedContent] = useState<string[]>([]);
  const applyingGeneratedContentRef = useRef(false);

  // Form reset functionality
  const { markAsChanged, handleCancel } = useFormReset(
    initialFormData,
    setFormData,
    setErrors,
    { resetOnCancel: true, confirmReset: true }
  );

  // Track if form has been modified by user
  const hasUserModificationsRef = useRef(false);

  // Reset form when guideline changes (but preserve user modifications)
  useEffect(() => {
    // Skip reset if we're currently applying generated content
    if (applyingGeneratedContentRef.current) {
      return;
    }

    // If user has made modifications, don't reset the form automatically
    if (hasUserModificationsRef.current) {
      return;
    }

    const newFormData: GuidelineFormData = {
      name: guideline?.name || '',
      standardWording: guideline?.standardWording || '',
      level: guideline?.level || 'medium',
      evaluationQuestions: (guideline?.evaluationQuestions && guideline.evaluationQuestions.length > 0) ? guideline.evaluationQuestions : [''],
      examples: (guideline?.examples && guideline.examples.length > 0) ? guideline.examples : [''],
    };

    setFormData(newFormData);
    setErrors({});
    hasUserModificationsRef.current = false; // Reset user modifications flag
    onClearError?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [guideline?.clauseTypeId, onClearError]); // Only reset when the actual guideline changes (by ID), not when arrays change

  // Validation using the validation utility
  const validateForm = (): boolean => {
    const validation = GuidelineValidator.validateForm(formData);
    setErrors(validation.errors);
    return validation.isValid;
  };

  // Form handlers
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Clear any existing server errors
    onClearError?.();

    if (!validateForm()) {
      return;
    }

    try {
      // Clean up arrays by removing empty strings
      const cleanedData = {
        ...formData,
        evaluationQuestions: formData.evaluationQuestions.filter(q => q.trim()),
        examples: formData.examples.filter(e => e.trim()),
      };

      // Submit the cleaned data (clauseTypeId will be auto-generated for new guidelines)
      await onSubmit(cleanedData);
    } catch (error) {
      // Error handling is done by the parent component
      console.error('Form submission error:', error);
    }
  };

  const handleFormCancel = () => {
    if (handleCancel()) {
      onCancel();
    }
  };

  // Track form changes
  const handleFormDataChange = (updates: Partial<GuidelineFormData>) => {
    // Mark that user has made modifications (unless it's during content application)
    if (!applyingGeneratedContentRef.current) {
      hasUserModificationsRef.current = true;
    }

    setFormData(prev => ({ ...prev, ...updates }));
    markAsChanged();

    // Clear field-specific errors when user starts typing
    if (Object.keys(updates).length > 0) {
      const fieldsToUpdate = Object.keys(updates);
      setErrors(prev => {
        const newErrors = { ...prev };
        fieldsToUpdate.forEach(field => {
          delete newErrors[field];
        });
        return newErrors;
      });
    }
  };

  // Dynamic array handlers
  const addEvaluationQuestion = () => {
    if (newQuestion.trim() && formData.evaluationQuestions.length < 10) {
      const newQuestions = [...formData.evaluationQuestions, newQuestion.trim()];
      handleFormDataChange({ evaluationQuestions: newQuestions });
      setNewQuestion('');
    }
  };

  const removeEvaluationQuestion = (index: number) => {
    const newQuestions = formData.evaluationQuestions.filter((_, i) => i !== index);
    handleFormDataChange({ evaluationQuestions: newQuestions });
  };

  const updateEvaluationQuestion = (index: number, value: string) => {
    const newQuestions = formData.evaluationQuestions.map((q, i) => i === index ? value : q);
    handleFormDataChange({ evaluationQuestions: newQuestions });
  };

  const addExample = () => {
    if (newExample.trim() && formData.examples.length < 20) {
      const newExamples = [...formData.examples, newExample.trim()];
      handleFormDataChange({ examples: newExamples });
      setNewExample('');
    }
  };

  const removeExample = (index: number) => {
    const newExamples = formData.examples.filter((_, i) => i !== index);
    handleFormDataChange({ examples: newExamples });
  };

  const updateExample = (index: number, value: string) => {
    const newExamples = formData.examples.map((e, i) => i === index ? value : e);
    handleFormDataChange({ examples: newExamples });
  };

  // AI Generation handlers
  const handleGenerateQuestions = async () => {
    if (!formData.standardWording.trim()) {
      setGenerationError(t('guidelines.form.aiGeneration.errors.requiresStandardWording'));
      return;
    }

    if (!contractType) {
      setGenerationError(t('guidelines.form.aiGeneration.errors.requiresContractType'));
      return;
    }

    setGeneratingQuestions(true);
    setGenerationError(null);

    try {
      // For new guidelines, we need to use a temporary clauseTypeId
      const clauseTypeId = guideline?.clauseTypeId || 'temp';
      const result = await generateEvaluationQuestions(
        contractTypeId,
        clauseTypeId,
        formData.standardWording
      );

      setGeneratedContent(result.questions);
      setReviewDialogType('questions');
      setReviewDialogOpen(true);
    } catch (error) {
      console.error('Failed to generate questions:', error);
      setGenerationError(t('guidelines.form.aiGeneration.errors.generateQuestions'));
    } finally {
      setGeneratingQuestions(false);
    }
  };

  const handleGenerateExamples = async () => {
    if (!formData.standardWording.trim()) {
      setGenerationError(t('guidelines.form.aiGeneration.errors.requiresStandardWording'));
      return;
    }

    if (!contractType) {
      setGenerationError(t('guidelines.form.aiGeneration.errors.requiresContractType'));
      return;
    }

    setGeneratingExamples(true);
    setGenerationError(null);

    try {
      // For new guidelines, we need to use a temporary clauseTypeId
      const clauseTypeId = guideline?.clauseTypeId || 'temp';
      const result = await generateClauseExamples(
        contractTypeId,
        clauseTypeId,
        formData.standardWording
      );

      setGeneratedContent(result.examples);
      setReviewDialogType('examples');
      setReviewDialogOpen(true);
    } catch (error) {
      console.error('Failed to generate examples:', error);
      setGenerationError(t('guidelines.form.aiGeneration.errors.generateExamples'));
    } finally {
      setGeneratingExamples(false);
    }
  };

  const handleApplyGeneratedContent = (content: string[]) => {
    // Set flag to prevent form reset during content application
    applyingGeneratedContentRef.current = true;

    if (reviewDialogType === 'questions') {
      // Ensure we have at least one empty string for the add new question functionality
      const questionsToApply = content.length > 0 ? content : [''];
      handleFormDataChange({ evaluationQuestions: questionsToApply });
    } else {
      // For examples, we can have an empty array since examples are optional
      const examplesToApply = content.length > 0 ? content : [''];
      handleFormDataChange({ examples: examplesToApply });
    }

    // Mark as user modification after applying content
    setTimeout(() => {
      applyingGeneratedContentRef.current = false;
      hasUserModificationsRef.current = true;
    }, 100);

    setReviewDialogOpen(false);
  };

  const clearGenerationError = () => {
    setGenerationError(null);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Server Error Banner */}
      {error && (
        <ErrorBanner
          error={error}
          onDismiss={onClearError}
        />
      )}

      {/* Generation Error Banner */}
      {generationError && (
        <ErrorBanner
          error={generationError}
          onDismiss={clearGenerationError}
        />
      )}

      {/* Clause Type ID is now auto-generated, so no input field needed */}

      {/* Name */}
      <div className="space-y-2">
        <Label htmlFor="name">
          {t('guidelines.form.fields.name.label')} *
        </Label>
        <Input
          id="name"
          value={formData.name}
          onChange={(e) => handleFormDataChange({ name: e.target.value })}
          placeholder={t('guidelines.form.fields.name.placeholder')}
          className={errors.name ? 'border-red-500' : ''}
        />
        <FieldError error={errors.name} />
      </div>

      {/* Standard Wording */}
      <div className="space-y-2">
        <Label htmlFor="standardWording">
          {t('guidelines.form.fields.standardWording.label')} *
        </Label>
        <textarea
          id="standardWording"
          value={formData.standardWording}
          onChange={(e) => handleFormDataChange({ standardWording: e.target.value })}
          placeholder={t('guidelines.form.fields.standardWording.placeholder')}
          rows={4}
          className={`flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${errors.standardWording ? 'border-red-500' : ''}`}
        />
        <FieldError error={errors.standardWording} />
        <p className="text-xs text-muted-foreground">
          {t('guidelines.form.fields.standardWording.characterCount', { count: formData.standardWording.length })}
        </p>
      </div>

      {/* Impact Level */}
      <div className="space-y-2">
        <Label htmlFor="level">
          {t('guidelines.form.fields.impactLevel.label')} *
        </Label>
        <Select
          value={formData.level}
          onValueChange={(value: ImpactLevel) => handleFormDataChange({ level: value })}
        >
          <SelectTrigger className={errors.level ? 'border-red-500' : ''}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {impactLevels.map((level) => (
              <SelectItem key={level.value} value={level.value}>
                <div className="flex items-center gap-2">
                  <Badge
                    variant="secondary"
                    className={IMPACT_COLORS[level.value]}
                  >
                    {level.label}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {level.description}
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <FieldError error={errors.level} />
      </div>

      {/* Evaluation Questions */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>
            {`${t('guidelines.form.fields.evaluationQuestions.label')} * ${t('guidelines.form.fields.evaluationQuestions.maxLabel')}`}
          </Label>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleGenerateQuestions}
                  disabled={generatingQuestions || !formData.standardWording.trim() || !contractType}
                  className="flex items-center gap-2"
                >
                  {generatingQuestions ? (
                    <Loader2Icon className="h-4 w-4 animate-spin" />
                  ) : (
                    <SparklesIcon className="h-4 w-4" />
                  )}
                  {generatingQuestions
                    ? t('guidelines.form.aiGeneration.generateQuestions.generating')
                    : t('guidelines.form.aiGeneration.generateQuestions.button')
                  }
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{t('guidelines.form.aiGeneration.generateQuestions.tooltip')}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        <div className="space-y-2">
          {formData.evaluationQuestions.map((question, index) => (
            <div key={`question-${index}-${question.slice(0, 20)}`} className="flex items-center gap-2">
              <Input
                value={question}
                onChange={(e) => updateEvaluationQuestion(index, e.target.value)}
                placeholder={t('guidelines.form.fields.evaluationQuestions.placeholder')}
                className="flex-1"
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => removeEvaluationQuestion(index)}
                disabled={formData.evaluationQuestions.length <= 1}
              >
                <XIcon className="h-4 w-4" />
              </Button>
            </div>
          ))}

          {formData.evaluationQuestions.length < 10 && (
            <div className="flex items-center gap-2">
              <Input
                value={newQuestion}
                onChange={(e) => setNewQuestion(e.target.value)}
                placeholder={t('guidelines.form.fields.evaluationQuestions.addPlaceholder')}
                className="flex-1"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addEvaluationQuestion();
                  }
                }}
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addEvaluationQuestion}
                disabled={!newQuestion.trim()}
              >
                <PlusIcon className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
        <FieldError error={errors.evaluationQuestions} />
        <p className="text-xs text-muted-foreground">
          {t('guidelines.form.fields.evaluationQuestions.description')}
        </p>
      </div>

      {/* Examples */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>
            {`${t('guidelines.form.fields.examples.label')} ${t('guidelines.form.fields.examples.optionalLabel')}`}
          </Label>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleGenerateExamples}
                  disabled={generatingExamples || !formData.standardWording.trim() || !contractType}
                  className="flex items-center gap-2"
                >
                  {generatingExamples ? (
                    <Loader2Icon className="h-4 w-4 animate-spin" />
                  ) : (
                    <SparklesIcon className="h-4 w-4" />
                  )}
                  {generatingExamples
                    ? t('guidelines.form.aiGeneration.generateExamples.generating')
                    : t('guidelines.form.aiGeneration.generateExamples.button')
                  }
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{t('guidelines.form.aiGeneration.generateExamples.tooltip')}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        <div className="space-y-2">
          {formData.examples.map((example, index) => (
            <div key={`example-${index}-${example.slice(0, 20)}`} className="flex items-center gap-2">
              <Input
                value={example}
                onChange={(e) => updateExample(index, e.target.value)}
                placeholder={t('guidelines.form.fields.examples.placeholder')}
                className="flex-1"
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => removeExample(index)}
              >
                <XIcon className="h-4 w-4" />
              </Button>
            </div>
          ))}

          {formData.examples.length < 20 && (
            <div className="flex items-center gap-2">
              <Input
                value={newExample}
                onChange={(e) => setNewExample(e.target.value)}
                placeholder={t('guidelines.form.fields.examples.addPlaceholder')}
                className="flex-1"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addExample();
                  }
                }}
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addExample}
                disabled={!newExample.trim()}
              >
                <PlusIcon className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
        <FieldError error={errors.examples} />
        <p className="text-xs text-muted-foreground">
          {t('guidelines.form.fields.examples.description')}
        </p>
      </div>

      {/* Form Actions */}
      <div className="flex items-center justify-end gap-3 pt-4 border-t">
        <Button
          type="button"
          variant="outline"
          onClick={handleFormCancel}
          disabled={loading}
        >
          {t('guidelines.form.actions.cancel')}
        </Button>
        <Button
          type="submit"
          disabled={loading}
        >
          {loading && <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />}
          {isEditing ? t('guidelines.form.actions.update') : t('guidelines.form.actions.create')}
        </Button>
      </div>

      {/* Generation Review Dialog */}
      <GenerationReviewDialog
        open={reviewDialogOpen}
        onOpenChange={setReviewDialogOpen}
        type={reviewDialogType}
        generatedContent={generatedContent}
        onApply={handleApplyGeneratedContent}
        loading={false}
      />
    </form>
  );
}