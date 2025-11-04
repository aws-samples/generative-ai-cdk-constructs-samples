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

import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  EditIcon,
  TrashIcon,
  CheckIcon,
  XIcon,
  PlusIcon,
} from "lucide-react";
import { useTranslation } from "react-i18next";

interface GenerationReviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  type: 'questions' | 'examples';
  generatedContent: string[];
  onApply: (content: string[]) => void;
  loading?: boolean;
}

export function GenerationReviewDialog({
  open,
  onOpenChange,
  type,
  generatedContent,
  onApply,
  loading = false,
}: GenerationReviewDialogProps) {
  const { t } = useTranslation();
  const [editableContent, setEditableContent] = useState<string[]>([]);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');
  const [newItem, setNewItem] = useState('');

  // Initialize editable content when dialog opens
  React.useEffect(() => {
    if (open) {
      setEditableContent([...generatedContent]);
      setEditingIndex(null);
      setEditValue('');
      setNewItem('');
    }
  }, [open, generatedContent]);

  const handleEdit = (index: number) => {
    setEditingIndex(index);
    setEditValue(editableContent[index]);
  };

  const handleSaveEdit = () => {
    if (editingIndex !== null && editValue.trim()) {
      const newContent = [...editableContent];
      newContent[editingIndex] = editValue.trim();
      setEditableContent(newContent);
      setEditingIndex(null);
      setEditValue('');
    }
  };

  const handleCancelEdit = () => {
    setEditingIndex(null);
    setEditValue('');
  };

  const handleRemove = (index: number) => {
    const newContent = editableContent.filter((_, i) => i !== index);
    setEditableContent(newContent);
    if (editingIndex === index) {
      setEditingIndex(null);
      setEditValue('');
    }
  };

  const handleAddNew = () => {
    if (newItem.trim()) {
      setEditableContent([...editableContent, newItem.trim()]);
      setNewItem('');
    }
  };

  const handleApply = () => {
    const filteredContent = editableContent.filter(item => item.trim());
    onApply(filteredContent);
    onOpenChange(false);
  };

  const handleCancel = () => {
    onOpenChange(false);
  };

  const isQuestions = type === 'questions';
  const titleKey = isQuestions ? 'questionsTitle' : 'examplesTitle';
  const maxItems = isQuestions ? 10 : 20;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {t('guidelines.form.aiGeneration.reviewDialog.title')}
          </DialogTitle>
          <DialogDescription>
            {t('guidelines.form.aiGeneration.reviewDialog.description')}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4">
          <div>
            <div className="flex items-center justify-between mb-3">
              <Label className="text-base font-medium">
                {t(`guidelines.form.aiGeneration.reviewDialog.${titleKey}`)}
              </Label>
              <Badge variant="secondary">
                {editableContent.length} / {maxItems}
              </Badge>
            </div>

            {editableContent.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                {t('guidelines.form.aiGeneration.reviewDialog.empty')}
              </div>
            ) : (
              <div className="space-y-2">
                {editableContent.map((item, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-2 p-3 border rounded-lg"
                  >
                    <div className="flex-1">
                      {editingIndex === index ? (
                        <div className="space-y-2">
                          <Input
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            placeholder={t('guidelines.form.aiGeneration.reviewDialog.placeholder')}
                            className="w-full"
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.preventDefault();
                                handleSaveEdit();
                              } else if (e.key === 'Escape') {
                                handleCancelEdit();
                              }
                            }}
                            autoFocus
                          />
                          <div className="flex items-center gap-2">
                            <Button
                              size="sm"
                              onClick={handleSaveEdit}
                              disabled={!editValue.trim()}
                            >
                              <CheckIcon className="h-4 w-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={handleCancelEdit}
                            >
                              <XIcon className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm leading-relaxed">{item}</p>
                      )}
                    </div>
                    {editingIndex !== index && (
                      <div className="flex items-center gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleEdit(index)}
                          aria-label={t('guidelines.form.aiGeneration.reviewDialog.actions.edit')}
                        >
                          <EditIcon className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleRemove(index)}
                          className="text-red-600 hover:text-red-700"
                          aria-label={t('guidelines.form.aiGeneration.reviewDialog.actions.remove')}
                        >
                          <TrashIcon className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Add new item */}
            {editableContent.length < maxItems && (
              <>
                <div className="border-t my-4" />
                <div className="flex items-center gap-2">
                  <Input
                    value={newItem}
                    onChange={(e) => setNewItem(e.target.value)}
                    placeholder={isQuestions
                      ? t('guidelines.form.fields.evaluationQuestions.addPlaceholder')
                      : t('guidelines.form.fields.examples.addPlaceholder')
                    }
                    className="flex-1"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddNew();
                      }
                    }}
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleAddNew}
                    disabled={!newItem.trim()}
                  >
                    <PlusIcon className="h-4 w-4" />
                  </Button>
                </div>
              </>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={loading}
          >
            {t('guidelines.form.aiGeneration.reviewDialog.actions.cancel')}
          </Button>
          <Button
            onClick={handleApply}
            disabled={loading || editableContent.length === 0}
          >
            {t('guidelines.form.aiGeneration.reviewDialog.actions.apply')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}