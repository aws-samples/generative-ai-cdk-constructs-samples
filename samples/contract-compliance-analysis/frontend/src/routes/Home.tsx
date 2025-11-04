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

import { useLocation } from "react-router";
import {
  use,
  Suspense,
  useMemo,
  useState,
  useEffect,
  useCallback,
} from "react";
import type { ColumnFiltersState } from "@tanstack/react-table";

import { getJobColumns } from "@/components/jobs/columns";
import {
  DataTable as JobsTable,
  DataTableSkeleton,
} from "@/components/jobs/data-table";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { createJob, getJobs, getContractTypes } from "@/lib/api";
import { MOCK_CONTRACT_TYPE } from "@/test/mockData";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileIcon, Loader2Icon, RefreshCcwIcon } from "lucide-react";
import { Job, ContractType } from "@/lib/types";
import { useTranslation } from "react-i18next";
import { NewAnalysisModal } from "@/components/NewAnalysisModal";
import { toast } from "sonner";
import { removePrefix } from "@/lib/utils";

export function Home() {
  const location = useLocation();
  const { t } = useTranslation();

  const [isRefreshing, setIsRefreshing] = useState(false);
  const [jobsPromise, setJobsPromise] = useState<Promise<Job[]>>(() =>
    getJobs(),
  );
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [contractTypes, setContractTypes] = useState<ContractType[]>([]);

  const filenameFilter = useMemo(
    () =>
      (columnFilters.find((f) => f.id === "documentS3Key")?.value as string) ||
      "",
    [columnFilters],
  );

  const statusFilter = useMemo(
    () => (columnFilters.find((f) => f.id === "status")?.value as string) || "",
    [columnFilters],
  );

  const needsReviewFilter = useMemo(
    () =>
      (columnFilters.find((f) => f.id === "needsReviewOverall")?.value as
        | string
        | boolean) ?? "",
    [columnFilters],
  );

  const contractTypeFilter = useMemo(
    () =>
      (columnFilters.find((f) => f.id === "contractTypeId")?.value as string) ||
      "",
    [columnFilters],
  );

  const refresh = useCallback(() => {
    setIsRefreshing(true);
    // Convert "all" to undefined for API call
    const contractTypeId =
      contractTypeFilter && contractTypeFilter !== "all"
        ? contractTypeFilter
        : undefined;

    // Mock logic is now handled in api.ts
    const next = getJobs(contractTypeId);

    next.finally(() => setIsRefreshing(false));
    setJobsPromise(next);
  }, [contractTypeFilter, setJobsPromise]);

  // Load contract types on component mount
  useEffect(() => {
    const loadContractTypes = async () => {
      try {
        const types = await getContractTypes();
        const activeTypes = types.filter((type) => type.isActive);

        // Add mock contract types only for filtering context
        if (import.meta.env.VITE_ENABLE_MOCK_JOBS === "true") {
          console.log(
            `📊 Filter context: Adding 1 mock contract type for filtering`,
          );
          activeTypes.push(MOCK_CONTRACT_TYPE);
        }

        setContractTypes(activeTypes);
      } catch (error) {
        console.error("Failed to load contract types:", error);
      }
    };
    loadContractTypes();
  }, []);

  // Refresh jobs when contract type filter changes
  useEffect(() => {
    refresh();
  }, [contractTypeFilter, refresh]);

  const handleNewAnalysis = async (data: {
    documentS3Key: string;
    description: string;
    contractTypeId: string;
    reportLanguage: string;
    legislationId?: string;
  }): Promise<void> => {
    const createJobParams = {
      documentS3Key: data.documentS3Key,
      jobDescription: data.description,
      contractTypeId: data.contractTypeId,
      outputLanguage: data.reportLanguage,
      // Only add legislationId if provided
      ...(data.legislationId && {
        legislationId: data.legislationId,
      }),
    };

    console.log("Creating new analysis with parameters:", createJobParams);

    await createJob(createJobParams);

    // Show success toast with job description and cleaned filename
    const cleanedFilename = removePrefix("documents/", data.documentS3Key);
    toast.success(t("newAnalysis.success"), {
      description: (
        <div className="mt-1 flex flex-col gap-1">
          <div>{data.description}</div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <FileIcon size={16} />
            {cleanedFilename}
          </div>
        </div>
      ),
    });

    refresh();
  };

  return (
    <div className="flex flex-col">
      <div className="flex-1">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="my-6 text-2xl font-semibold tracking-tight">
              {t("home.header")}
            </h2>
            <Suspense
              key={`header-badge-${location.key}`}
              fallback={
                <Badge
                  variant="secondary"
                  className="rounded-full bg-blue-500 px-1  text-blue-100 hover:bg-blue-500"
                >
                  <Loader2Icon className="animate-spin" size={16} />
                </Badge>
              }
            >
              <JobsCountBadge jobsPromise={jobsPromise} />
            </Suspense>
          </div>
        </div>
        <div className="mb-3 flex flex-col gap-3 text-sm md:flex-row md:items-center md:justify-between">
          <div className="flex w-full flex-1 flex-col gap-2 md:flex-row md:items-center">
            <Input
              placeholder={t("home.searchPlaceholder")}
              className="md:max-w-sm"
              value={filenameFilter}
              onChange={(e) => {
                const value = e.target.value;
                setColumnFilters((prev) => {
                  const others = prev.filter((f) => f.id !== "documentS3Key");
                  return value
                    ? [...others, { id: "documentS3Key", value }]
                    : others;
                });
              }}
            />
            <Select
              value={statusFilter || "all"}
              onValueChange={(value) => {
                setColumnFilters((prev) => {
                  const others = prev.filter((f) => f.id !== "status");
                  return [...others, { id: "status", value }];
                });
              }}
            >
              <SelectTrigger
                aria-label="Filter by status"
                className=" bg-white  md:w-48"
              >
                <SelectValue placeholder={t("home.status.placeholder")} />
              </SelectTrigger>
              <SelectContent className="border bg-white shadow-lg">
                <SelectItem value="all">{t("home.status.all")}</SelectItem>
                <SelectItem value="RUNNING">
                  {t("home.status.RUNNING")}
                </SelectItem>
                <SelectItem value="SUCCEEDED">
                  {t("home.status.SUCCEEDED")}
                </SelectItem>
                <SelectItem value="FAILED">
                  {t("home.status.FAILED")}
                </SelectItem>
                <SelectItem value="TIMED_OUT">
                  {t("home.status.TIMED_OUT")}
                </SelectItem>
                <SelectItem value="ABORTED">
                  {t("home.status.ABORTED")}
                </SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={
                needsReviewFilter === "" ? "all" : String(needsReviewFilter)
              }
              onValueChange={(value) => {
                setColumnFilters((prev) => {
                  const others = prev.filter(
                    (f) => f.id !== "needsReviewOverall",
                  );
                  return [...others, { id: "needsReviewOverall", value }];
                });
              }}
            >
              <SelectTrigger
                aria-label="Filter by compliance"
                className="bg-white md:w-44"
              >
                <SelectValue placeholder={t("home.review.placeholder")} />
              </SelectTrigger>
              <SelectContent className="border bg-white shadow-lg">
                <SelectItem value="all">{t("home.review.all")}</SelectItem>
                <SelectItem value="true">{t("common.nonCompliant")}</SelectItem>
                <SelectItem value="false">{t("common.compliant")}</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={contractTypeFilter || "all"}
              onValueChange={(value) => {
                setColumnFilters((prev) => {
                  const others = prev.filter((f) => f.id !== "contractTypeId");
                  return [...others, { id: "contractTypeId", value }];
                });
              }}
            >
              <SelectTrigger
                aria-label="Filter by contract type"
                className="bg-white md:w-48"
              >
                <SelectValue placeholder={t("home.contractType.placeholder")} />
              </SelectTrigger>
              <SelectContent className="border bg-white shadow-lg">
                <SelectItem value="all">
                  {t("home.contractType.all")}
                </SelectItem>
                {contractTypes.map((contractType) => (
                  <SelectItem
                    key={contractType.contractTypeId}
                    value={contractType.contractTypeId}
                  >
                    {contractType.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-3">
            <Button
              data-testid="refresh-button"
              variant="outline"
              onClick={refresh}
              disabled={isRefreshing}
            >
              <span className={isRefreshing ? "animate-spin" : ""}>
                <RefreshCcwIcon className="-scale-x-100" size={18} />
              </span>
            </Button>
            <NewAnalysisModal onSubmit={handleNewAnalysis} />
          </div>
        </div>

        <Suspense key={location.key} fallback={<DataTableSkeleton />}>
          <ResolvedTable
            jobsPromise={jobsPromise}
            columnFilters={columnFilters}
            setColumnFilters={setColumnFilters}
          />
        </Suspense>
      </div>

      {/* AI Disclaimer - Classic Sticky Footer */}
      <div className="py-8 text-right">
        <div className="text-xs text-slate-500">
          {t("aiDisclaimer.text")}{" "}
          <a
            href="https://aws.amazon.com/ai/responsible-ai/policy/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:text-blue-700"
          >
            {t("aiDisclaimer.linkText")}
          </a>
        </div>
      </div>
    </div>
  );
}

// componente auxiliar que resolve a Promise usando `use()` e passa os dados já resolvidos para a tabela
function ResolvedTable({
  jobsPromise,
  columnFilters,
  setColumnFilters,
}: {
  jobsPromise: Promise<Job[]>;
  columnFilters: ColumnFiltersState;
  setColumnFilters: React.Dispatch<React.SetStateAction<ColumnFiltersState>>;
}) {
  const jobs = use(jobsPromise);
  const { t } = useTranslation();
  return (
    <JobsTable
      columns={getJobColumns(t)}
      data={jobs}
      columnFilters={columnFilters}
      onColumnFiltersChange={setColumnFilters}
    />
  );
}

function JobsCountBadge({ jobsPromise }: { jobsPromise: Promise<Job[]> }) {
  const jobs = use(jobsPromise);
  return (
    <Badge
      variant="secondary"
      className="rounded-full bg-blue-500 text-blue-100 hover:bg-blue-600"
    >
      {jobs.length}
    </Badge>
  );
}
