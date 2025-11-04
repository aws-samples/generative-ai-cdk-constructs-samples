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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  PlusCircleIcon,
  EditIcon,
  TrashIcon,
  SettingsIcon,
  Loader2Icon,
  AlertCircleIcon,
  BookOpenIcon,
  UploadIcon,
} from "lucide-react";
import { languages } from "@/lib/i18n";
import { getContractTypes, createContractType, updateContractType, deleteContractType } from "@/lib/api";
import type { ContractType } from "@/lib/types";
import { getErrorMessage } from "@/lib/utils";
import { toast } from "sonner";
import { useNavigate } from "react-router";
import { ImportContractType } from "@/components/ImportContractType";

interface ContractTypeFormData {
  name: string;
  description: string;
  companyPartyType: string;
  otherPartyType: string;
  highRiskThreshold: number;
  mediumRiskThreshold: number;
  lowRiskThreshold: number;
  defaultLanguage: string;
  isActive: boolean;
}

const defaultFormData: ContractTypeFormData = {
  name: "",
  description: "",
  companyPartyType: "",
  otherPartyType: "",
  highRiskThreshold: 0,
  mediumRiskThreshold: 1,
  lowRiskThreshold: 3,
  defaultLanguage: "en",
  isActive: true,
};

export function ContractTypeManagement() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [contractTypes, setContractTypes] = useState<ContractType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingType, setEditingType] = useState<ContractType | null>(null);
  const [formData, setFormData] = useState<ContractTypeFormData>(defaultFormData);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    loadContractTypes();
  }, []);

  const loadContractTypes = async () => {
    try {
      setLoading(true);
      setError(null);
      const types = await getContractTypes();
      setContractTypes(types);
    } catch (e) {
      console.error("Failed to load contract types:", e);
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingType(null);
    setFormData(defaultFormData);
    setDialogOpen(true);
  };

  const handleEdit = (contractType: ContractType) => {
    setEditingType(contractType);
    setFormData({
      name: contractType.name,
      description: contractType.description,
      companyPartyType: contractType.companyPartyType,
      otherPartyType: contractType.otherPartyType,
      highRiskThreshold: contractType.highRiskThreshold,
      mediumRiskThreshold: contractType.mediumRiskThreshold,
      lowRiskThreshold: contractType.lowRiskThreshold,
      defaultLanguage: contractType.defaultLanguage,
      isActive: contractType.isActive,
    });
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    if (!formData.name.trim() || !formData.description.trim()) {
      toast.error("Please fill in all required fields");
      return;
    }

    setIsSubmitting(true);
    try {
      if (editingType) {
        await updateContractType(editingType.contractTypeId, formData);
        toast.success("Contract type updated successfully");
      } else {
        await createContractType(formData);
        toast.success("Contract type created successfully");
      }

      setDialogOpen(false);
      await loadContractTypes();
    } catch (e) {
      console.error("Failed to save contract type:", e);
      toast.error(`Failed to save contract type: ${getErrorMessage(e)}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (contractType: ContractType) => {
    if (!confirm(`Are you sure you want to delete "${contractType.name}"?`)) {
      return;
    }

    try {
      await deleteContractType(contractType.contractTypeId);
      toast.success("Contract type deleted successfully");
      await loadContractTypes();
    } catch (e) {
      console.error("Failed to delete contract type:", e);
      toast.error(`Failed to delete contract type: ${getErrorMessage(e)}`);
    }
  };

  const handleToggleActive = async (contractType: ContractType) => {
    try {
      // Send all required fields along with the isActive change
      await updateContractType(contractType.contractTypeId, {
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
      toast.success(`Contract type ${contractType.isActive ? 'deactivated' : 'activated'} successfully`);
      await loadContractTypes();
    } catch (e) {
      console.error("Failed to toggle contract type status:", e);
      toast.error(`Failed to update contract type: ${getErrorMessage(e)}`);
    }
  };

  const handleManageGuidelines = (contractType: ContractType) => {
    navigate(`/contract-types/${encodeURIComponent(contractType.contractTypeId)}/guidelines`);
  };

  const handleImportComplete = (contractTypeId: string) => {
    // Reload contract types to show the new imported type
    loadContractTypes();
    // Navigate to the guidelines management for the new contract type
    navigate(`/contract-types/${encodeURIComponent(contractTypeId)}/guidelines`);
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <SettingsIcon className="h-5 w-5" />
            {t("contractType.management.title")}
          </CardTitle>
          <CardDescription>{t("contractType.management.description")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2Icon className="h-8 w-8 animate-spin" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <SettingsIcon className="h-5 w-5" />
            {t("contractType.management.title")}
          </CardTitle>
          <CardDescription>{t("contractType.management.description")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 p-4 text-red-700">
            <AlertCircleIcon className="h-5 w-5" />
            <span>Error loading contract types: {error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <SettingsIcon className="h-5 w-5" />
              {t("contractType.management.title")}
            </CardTitle>
            <CardDescription>{t("contractType.management.description")}</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <ImportContractType
              onImportComplete={handleImportComplete}
              trigger={
                <Button variant="outline">
                  <UploadIcon className="mr-2 h-4 w-4" />
                  {t("import.button")}
                </Button>
              }
            />
            <Button onClick={handleCreate}>
              <PlusCircleIcon className="mr-2 h-4 w-4" />
              {t("contractType.management.createNew")}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("contractType.form.name")}</TableHead>
                <TableHead>{t("contractType.form.description")}</TableHead>
                <TableHead>{t("contractType.management.statusColumn")}</TableHead>
                <TableHead>{t("contractType.management.riskThresholdsColumn")}</TableHead>
                <TableHead>{t("contractType.management.guidelinesColumn")}</TableHead>
                <TableHead className="text-right">{t("contractType.management.actionsColumn")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {contractTypes.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    {t("contractType.management.noContractTypes")}
                  </TableCell>
                </TableRow>
              ) : (
                contractTypes.map((contractType) => (
                  <TableRow key={contractType.contractTypeId}>
                    <TableCell>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{contractType.name}</span>
                          {contractType.isImported && (
                            <Badge variant="outline" className="text-xs">
                              {t("guidelines.import.status.imported")}
                            </Badge>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground font-mono">
                          {contractType.contractTypeId}
                        </div>
                        {contractType.isImported && contractType.importSourceDocument && (
                          <div className="text-xs text-muted-foreground mt-1">
                            Source: {contractType.importSourceDocument.split('/').pop()}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="max-w-xs truncate" title={contractType.description}>
                        {contractType.description}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <Badge variant={contractType.isActive ? "default" : "secondary"}>
                          {contractType.isActive ? "Active" : "Inactive"}
                        </Badge>
                        {contractType.isImported && !contractType.isActive && (
                          <div className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
                            {t("guidelines.import.status.needsReview")}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-xs space-y-1">
                        <div>High: {contractType.highRiskThreshold}</div>
                        <div>Med: {contractType.mediumRiskThreshold}</div>
                        <div>Low: {contractType.lowRiskThreshold}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleManageGuidelines(contractType)}
                        className="flex items-center gap-2"
                      >
                        <BookOpenIcon className="h-4 w-4" />
                        {t("contractType.management.manageGuidelines")}
                      </Button>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEdit(contractType)}
                        >
                          <EditIcon className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggleActive(contractType)}
                          className={contractType.isImported && !contractType.isActive ? "bg-green-50 hover:bg-green-100 text-green-700 border-green-200" : ""}
                        >
                          {contractType.isActive ? t("contractType.management.deactivate") :
                            contractType.isImported ? t("guidelines.import.status.activate") : t("contractType.management.activate")}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDelete(contractType)}
                          className="text-red-600 hover:text-red-700"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>
              {editingType ? t("contractType.management.dialog.editTitle") : t("contractType.management.dialog.createTitle")}
            </DialogTitle>
            <DialogDescription>
              {editingType ? t("contractType.management.dialog.editDescription") : t("contractType.management.dialog.createDescription")}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">{t("contractType.form.name")} *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder={t("contractType.form.placeholders.name")}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="defaultLanguage">{t("contractType.form.defaultLanguage")}</Label>
                <Select
                  value={formData.defaultLanguage}
                  onValueChange={(value) => setFormData({ ...formData, defaultLanguage: value })}
                >
                  <SelectTrigger>
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
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">{t("contractType.form.description")} *</Label>
              <Input
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder={t("contractType.form.placeholders.description")}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="companyPartyType">{t("contractType.form.companyPartyType")}</Label>
                <Input
                  id="companyPartyType"
                  value={formData.companyPartyType}
                  onChange={(e) => setFormData({ ...formData, companyPartyType: e.target.value })}
                  placeholder={t("contractType.form.placeholders.companyPartyType")}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="otherPartyType">{t("contractType.form.otherPartyType")}</Label>
                <Input
                  id="otherPartyType"
                  value={formData.otherPartyType}
                  onChange={(e) => setFormData({ ...formData, otherPartyType: e.target.value })}
                  placeholder={t("contractType.form.placeholders.otherPartyType")}
                />
              </div>
            </div>

            <div className="space-y-3">
              <Label>{t("contractType.form.riskThresholds")}</Label>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="highRisk" className="text-sm">{t("contractType.form.highRisk")}</Label>
                  <Input
                    id="highRisk"
                    type="number"
                    min="0"
                    step="1"
                    value={formData.highRiskThreshold}
                    onChange={(e) => setFormData({ ...formData, highRiskThreshold: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="mediumRisk" className="text-sm">{t("contractType.form.mediumRisk")}</Label>
                  <Input
                    id="mediumRisk"
                    type="number"
                    min="0"
                    step="1"
                    value={formData.mediumRiskThreshold}
                    onChange={(e) => setFormData({ ...formData, mediumRiskThreshold: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lowRisk" className="text-sm">{t("contractType.form.lowRisk")}</Label>
                  <Input
                    id="lowRisk"
                    type="number"
                    min="0"
                    step="1"
                    value={formData.lowRiskThreshold}
                    onChange={(e) => setFormData({ ...formData, lowRiskThreshold: parseInt(e.target.value) || 0 })}
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="isActive"
                checked={formData.isActive}
                onCheckedChange={(checked) => setFormData({ ...formData, isActive: checked })}
              />
              <Label htmlFor="isActive">{t("contractType.form.isActive")}</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleSubmit} disabled={isSubmitting}>
              {isSubmitting && <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />}
              {editingType ? t("contractType.management.dialog.updateButton") : t("contractType.management.dialog.createButton")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}