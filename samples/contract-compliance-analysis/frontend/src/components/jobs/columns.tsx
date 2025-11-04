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

import { ColumnDef } from "@tanstack/react-table";
import { Badge } from "@/components/ui/badge";
import { Link } from "react-router";
import {
  ArrowUpDownIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  FileTextIcon,
  CheckIcon,
  AlertTriangleIcon,
  XOctagonIcon,
  XIcon,
  FlaskConicalIcon,
  AlertCircleIcon,
} from "lucide-react";
import { Button } from "../ui/button";
import { Spinner } from "../ui/spinner";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../ui/tooltip";
import { Job } from "@/lib/types";
import type { TFunction } from "i18next";
import i18n from "@/lib/i18n";
import {
  cn,
  removePrefix,
  isOverallCompliant,
  getOverallProcessingStatus,
  isJobClickable,
} from "@/lib/utils";

// Shared status configuration
const STATUS_DICTIONARY: { [key: string]: string } = {
  RUNNING: "home.status.RUNNING",
  SUCCEEDED: "home.status.SUCCEEDED",
  FAILED: "home.status.FAILED",
  TIMED_OUT: "home.status.TIMED_OUT",
  ABORTED: "home.status.ABORTED",
};

const STATUS_CLASS_NAMES: { [key: string]: string } = {
  RUNNING: "bg-blue-500 hover:bg-blue-500",
  SUCCEEDED: "bg-lime-600 hover:bg-lime-600",
  FAILED: "bg-slate-400 hover:bg-slate-400",
  TIMED_OUT: "bg-slate-400 hover:bg-slate-400",
  ABORTED: "bg-slate-400 hover:bg-slate-400",
};

const STATUS_ICONS: { [key: string]: React.ReactElement } = {
  RUNNING: <Spinner className="size-[14px]" />,
  SUCCEEDED: <CheckIcon size={14} />,
  FAILED: <XIcon size={14} />,
  TIMED_OUT: <XIcon size={14} />,
  ABORTED: <XOctagonIcon size={14} />,
};

const getCheckIcon = (processingStatus: string) => {
  if (processingStatus === "RUNNING")
    return <Spinner className="size-3 text-blue-500" />;
  if (processingStatus === "SUCCEEDED")
    return <CheckIcon className="text-green-500" size={12} />;
  if (processingStatus === "FAILED")
    return <XIcon className="text-slate-400" size={12} />;
  if (processingStatus === "TIMED_OUT")
    return <XIcon className="text-slate-400" size={12} />;
  if (processingStatus === "ABORTED")
    return <XOctagonIcon className="text-slate-400" size={12} />;
  return null;
};

/**
 * Get tooltip icon with appropriate color based on context
 * @param isSuccess - true if SUCCEEDED and compliant
 * @param isProcessingError - true if FAILED/TIMED_OUT/ABORTED
 * @param useAmber - true for Guidelines (amber), false for Legislation (red)
 */
const getTooltipIcon = (
  isSuccess: boolean,
  isProcessingError: boolean,
  useAmber: boolean,
) => {
  if (isSuccess) {
    return <CheckIcon size={12} className="text-green-500" />;
  }
  if (isProcessingError) {
    return <XIcon size={12} className="text-slate-400" />;
  }
  // Non-compliant: amber for Guidelines, red for Legislation
  const color = useAmber ? "text-amber-500" : "text-red-500";
  return <AlertTriangleIcon size={12} className={color} />;
};

export const getJobColumns = (t: TFunction): ColumnDef<Job>[] => [
  {
    accessorKey: "documentS3Key",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          {t("jobs.columns.filename")}
          {column.getIsSorted() === "asc" ? (
            <ArrowUpIcon className="ml-2 h-4 w-4" />
          ) : column.getIsSorted() === "desc" ? (
            <ArrowDownIcon className="ml-2 h-4 w-4" />
          ) : (
            <ArrowUpDownIcon className="ml-2 h-4 w-4 opacity-50" />
          )}
        </Button>
      );
    },
    cell: ({ row }) => {
      const { checks, documentS3Key, id } = row.original;
      const fileName = removePrefix("documents/", documentS3Key);
      const clickable = isJobClickable(checks);
      const overallStatus = getOverallProcessingStatus(checks);

      if (clickable) {
        return (
          <Link
            to={`/jobs/${id}`}
            className="flex items-center gap-2 text-blue-500 hover:text-blue-600"
          >
            <FileTextIcon size={16} className="text-slate-500" />
            <span className="text-sm font-medium">{fileName}</span>
          </Link>
        );
      } else if (
        overallStatus === "FAILED" ||
        overallStatus === "TIMED_OUT" ||
        overallStatus === "ABORTED"
      ) {
        return (
          <div className="flex items-center gap-2 text-muted-foreground line-through">
            <FileTextIcon size={16} />
            <span className="text-sm">{fileName}</span>
          </div>
        );
      } else {
        return (
          <div className="flex animate-pulse items-center gap-2 text-muted-foreground">
            <FileTextIcon size={16} />
            <span className="text-sm italic">{fileName}</span>
          </div>
        );
      }
    },
  },
  {
    accessorKey: "jobDescription",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          {t("jobs.columns.description")}
          {column.getIsSorted() === "asc" ? (
            <ArrowUpIcon className="ml-2 h-4 w-4" />
          ) : column.getIsSorted() === "desc" ? (
            <ArrowDownIcon className="ml-2 h-4 w-4" />
          ) : (
            <ArrowUpDownIcon className="ml-2 h-4 w-4 opacity-50" />
          )}
        </Button>
      );
    },
    cell: ({ row }) => {
      const description = row.getValue<string>("jobDescription");
      return (
        <div className="max-w-[200px] truncate text-sm text-muted-foreground">
          {description}
        </div>
      );
    },
  },
  {
    accessorKey: "contractTypeId",
    filterFn: (row, id, value) => {
      if (value == null || value === "" || value === "all") return true;
      const cell = row.getValue<string>(id);
      return cell === value;
    },
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          {t("jobs.columns.contractType")}
          {column.getIsSorted() === "asc" ? (
            <ArrowUpIcon className="ml-2 h-4 w-4" />
          ) : column.getIsSorted() === "desc" ? (
            <ArrowDownIcon className="ml-2 h-4 w-4" />
          ) : (
            <ArrowUpDownIcon className="ml-2 h-4 w-4 opacity-50" />
          )}
        </Button>
      );
    },
    cell: ({ row }) => {
      const contractType = row.original.contractType;
      const contractTypeId = row.getValue<string>("contractTypeId");
      const isMockContract = contractTypeId === "mock-contract";

      return (
        <div className="flex justify-center">
          {contractType ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge
                    variant="secondary"
                    className={cn(
                      "cursor-help text-xs",
                      isMockContract &&
                        "gap-1 border border-amber-600 bg-amber-500 font-semibold text-amber-900 hover:bg-amber-500",
                    )}
                  >
                    {" "}
                    {isMockContract && <FlaskConicalIcon size={14} />}
                    {contractType.name}
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  <div className="text-xs">{contractType.description}</div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <span className="font-mono text-xs text-muted-foreground">
              {contractTypeId}
            </span>
          )}
        </div>
      );
    },
  },
  {
    accessorKey: "startDate",
    sortingFn: (rowA, rowB, columnId) => {
      const a = rowA.getValue<string | undefined>(columnId);
      const b = rowB.getValue<string | undefined>(columnId);
      const ta = a ? Date.parse(a) : 0;
      const tb = b ? Date.parse(b) : 0;
      return ta - tb;
    },
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          className="w-full"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          {t("jobs.columns.createdAt")}
          {column.getIsSorted() === "asc" ? (
            <ArrowUpIcon className="ml-2 h-4 w-4" />
          ) : column.getIsSorted() === "desc" ? (
            <ArrowDownIcon className="ml-2 h-4 w-4" />
          ) : (
            <ArrowUpDownIcon className="ml-2 h-4 w-4 opacity-50" />
          )}
        </Button>
      );
    },
    cell: ({ row }) => {
      const rowDate = row.getValue("startDate");
      if (rowDate) {
        const date = new Date(rowDate as string);
        return (
          <div className="block w-full text-center text-sm">
            {date.toLocaleDateString()}
            <div className="text-xs text-muted-foreground">
              {date.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </div>
          </div>
        );
      }
    },
  },
  {
    accessorKey: "status",
    filterFn: (row, _id, value) => {
      if (value == null || value === "" || value === "all") return true;
      // Use getOverallProcessingStatus instead of legacy job.status field
      const actualStatus = getOverallProcessingStatus(row.original.checks);
      return actualStatus === value;
    },
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          className="w-full"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          {t("jobs.columns.status")}
          {column.getIsSorted() === "asc" ? (
            <ArrowUpIcon className="ml-2 h-4 w-4" />
          ) : column.getIsSorted() === "desc" ? (
            <ArrowDownIcon className="ml-2 h-4 w-4" />
          ) : (
            <ArrowUpDownIcon className="ml-2 h-4 w-4 opacity-50" />
          )}
        </Button>
      );
    },
    cell: ({ row }) => {
      const job = row.original;
      const { checks, endDate } = job;
      const status = getOverallProcessingStatus(checks);

      const tooltipContent = () => {
        const { guidelines, legislation } = checks;

        return (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              {getCheckIcon(guidelines.processingStatus)}
              <span className="text-slate-700">
                {i18n.t("jobs.columns.guidelines")}:
              </span>
              <span className="text-slate-600">
                {i18n.t(STATUS_DICTIONARY[guidelines.processingStatus])}
              </span>
            </div>

            {legislation && (
              <div className="flex items-center gap-2">
                {getCheckIcon(legislation.processingStatus)}
                <span className="text-slate-700">
                  {i18n.t("jobs.columns.legislation")}:
                </span>
                <span className="text-slate-600">
                  {i18n.t(STATUS_DICTIONARY[legislation.processingStatus])}
                </span>
              </div>
            )}

            {endDate &&
              endDate !== "None" &&
              (status === "SUCCEEDED" ||
                status === "FAILED" ||
                status === "TIMED_OUT" ||
                status === "ABORTED") && (
                <div className="mt-2 border-t border-slate-200 pt-2">
                  <div className="text-[10px] text-slate-500">
                    {i18n.t("jobs.columns.finishedAt")}:{" "}
                    {new Date(endDate).toLocaleString()}
                  </div>
                </div>
              )}
          </div>
        );
      };

      return (
        <div className="flex justify-center">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <Badge
                    className={cn(
                      `h-6 w-6 cursor-help items-center justify-center rounded-full p-0 ${STATUS_CLASS_NAMES[status]} ${status === "RUNNING" ? "animate-pulse" : ""}`,
                    )}
                  >
                    {STATUS_ICONS[status]}
                  </Badge>
                </div>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <div className="text-xs">{tooltipContent()}</div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      );
    },
  },
  {
    id: "guidelines",
    header: () => {
      return <div className="text-center">{t("jobs.columns.guidelines")}</div>;
    },
    cell: ({ row }) => {
      const job = row.original;
      const guidelinesCheck = job.checks?.guidelines;

      if (!guidelinesCheck) {
        return (
          <div className="flex w-full justify-center text-slate-400">-</div>
        );
      }

      const { processingStatus, compliant } = guidelinesCheck;

      // Show badge for RUNNING (consistent with other status badges)
      if (processingStatus === "RUNNING") {
        return (
          <div className="flex w-full justify-center">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div>
                    <Badge
                      className={cn(
                        "h-6 w-6 animate-pulse cursor-help items-center justify-center rounded-full bg-blue-500 p-0 hover:bg-blue-500",
                      )}
                    >
                      <Spinner className="size-[14px]" />
                    </Badge>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <div className="text-xs">
                    <div className="flex items-center gap-2">
                      <Spinner className="size-2 text-blue-500" />
                      <span>{i18n.t("home.status.RUNNING")}</span>
                    </div>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        );
      }

      // Separate processing errors from content errors
      const isProcessingError =
        processingStatus === "FAILED" ||
        processingStatus === "TIMED_OUT" ||
        processingStatus === "ABORTED";
      const isContentError = processingStatus === "SUCCEEDED" && !compliant;
      const isSuccess = processingStatus === "SUCCEEDED" && compliant;

      // Determine icon based on status
      const icon = isSuccess ? (
        <CheckIcon size={14} className="text-white" />
      ) : processingStatus === "ABORTED" ? (
        <XOctagonIcon size={14} className="text-white" />
      ) : isProcessingError ? (
        <XIcon size={14} className="text-white" />
      ) : (
        <AlertTriangleIcon size={14} className={cn("mt-[-2px] text-white")} />
      );

      // Determine color: green for success, amber for content errors (Guidelines), gray for processing errors
      const className = isSuccess
        ? "bg-lime-600 hover:bg-lime-600"
        : isContentError
          ? "bg-amber-500 hover:bg-amber-500"
          : "bg-slate-400 hover:bg-slate-400";

      return (
        <div className="flex w-full justify-center">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <Badge
                    className={cn(
                      `h-6 w-6 cursor-help items-center justify-center rounded-full p-0 ${className}`,
                    )}
                  >
                    {icon}
                  </Badge>
                </div>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <div className="text-xs">
                  <div className="flex items-center gap-2">
                    {getTooltipIcon(isSuccess, isProcessingError, true)}
                    <span>
                      {isProcessingError
                        ? i18n.t(STATUS_DICTIONARY[processingStatus])
                        : isContentError
                          ? i18n.t("common.nonCompliant")
                          : i18n.t("common.compliant")}
                    </span>
                  </div>
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      );
    },
  },
  {
    id: "legislation",
    header: () => {
      return <div className="text-center">{t("jobs.columns.legislation")}</div>;
    },
    cell: ({ row }) => {
      const job = row.original;
      const legislationCheck = job.checks?.legislation;

      if (!legislationCheck) {
        return (
          <div className="flex w-full justify-center text-slate-400">-</div>
        );
      }

      const { processingStatus, compliant } = legislationCheck;

      // Show badge for RUNNING (consistent with other status badges)
      if (processingStatus === "RUNNING") {
        return (
          <div className="flex w-full justify-center">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div>
                    <Badge
                      className={cn(
                        "h-6 w-6 animate-pulse cursor-help items-center justify-center rounded-full bg-blue-500 p-0 hover:bg-blue-500",
                      )}
                    >
                      <Spinner className="size-[14px]" />
                    </Badge>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <div className="text-xs">
                    <div className="flex items-center gap-2">
                      <Spinner className="size-3 text-blue-500" />
                      <span>{i18n.t("home.status.RUNNING")}</span>
                    </div>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        );
      }

      // Separate processing errors from content errors
      const isProcessingError =
        processingStatus === "FAILED" ||
        processingStatus === "TIMED_OUT" ||
        processingStatus === "ABORTED";
      const isContentError = processingStatus === "SUCCEEDED" && !compliant;
      const isSuccess = processingStatus === "SUCCEEDED" && compliant;

      // Determine icon based on status
      const icon = isSuccess ? (
        <CheckIcon size={14} className="text-white" />
      ) : processingStatus === "ABORTED" ? (
        <XOctagonIcon size={14} className="text-white" />
      ) : isProcessingError ? (
        <XIcon size={14} className="text-white" />
      ) : (
        <AlertTriangleIcon size={14} className={cn("mt-[-2px] text-white")} />
      );

      // Determine color: green for success, red for content errors, gray for processing errors
      const className = isSuccess
        ? "bg-lime-600 hover:bg-lime-600"
        : isContentError
          ? "bg-red-600 hover:bg-red-600"
          : "bg-slate-400 hover:bg-slate-400";

      return (
        <div className="flex w-full justify-center">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <Badge
                    className={cn(
                      `h-6 w-6 cursor-help items-center justify-center rounded-full p-0 ${className}`,
                    )}
                  >
                    {icon}
                  </Badge>
                </div>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <div className="text-xs">
                  <div className="flex items-center gap-2">
                    {getTooltipIcon(isSuccess, isProcessingError, false)}
                    <span>
                      {isProcessingError
                        ? i18n.t(STATUS_DICTIONARY[processingStatus])
                        : isContentError
                          ? i18n.t("common.nonCompliant")
                          : i18n.t("common.compliant")}
                    </span>
                  </div>
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      );
    },
  },
  {
    id: "needsReviewOverall",
    filterFn: (row, _id, value) => {
      if (value == null || value === "" || value === "all") return true;

      // Only filter jobs that have completed successfully (SUCCEEDED)
      // Jobs that are RUNNING/FAILED/TIMED_OUT/ABORTED don't have compliance defined yet
      const overallStatus = getOverallProcessingStatus(row.original.checks);
      if (overallStatus !== "SUCCEEDED") return false;

      const isCompliant = isOverallCompliant(row.original);
      // Filter expects needsReview (true/false), so invert isCompliant
      const needsReview = !isCompliant;
      if (typeof value === "boolean") return needsReview === value;
      if (typeof value === "string") return needsReview === (value === "true");
      return true;
    },
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          className="w-full"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          <span className="flex items-center gap-1">
            {t("jobs.columns.compliant")}
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <AlertCircleIcon
                    size={14}
                    className="cursor-help text-slate-400 hover:text-slate-600"
                  />
                </TooltipTrigger>
                <TooltipContent>
                  <div className="max-w-xs p-2">
                    <p className="text-xs font-normal">
                      {i18n.t("aiDisclaimer.text")}{" "}
                      <a
                        href="https://aws.amazon.com/ai/responsible-ai/policy/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-400 underline hover:text-blue-300"
                      >
                        {i18n.t("aiDisclaimer.linkText")}
                      </a>
                    </p>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </span>
          {column.getIsSorted() === "asc" ? (
            <ArrowUpIcon className="ml-2 h-4 w-4" />
          ) : column.getIsSorted() === "desc" ? (
            <ArrowDownIcon className="ml-2 h-4 w-4" />
          ) : (
            <ArrowUpDownIcon className="ml-2 h-4 w-4 opacity-50" />
          )}
        </Button>
      );
    },
    cell: ({ row }) => {
      const job = row.original;
      const overallStatus = getOverallProcessingStatus(job.checks);
      const isCompliant = isOverallCompliant(job);

      // Don't show badge for RUNNING, FAILED, or TIMED_OUT - we don't have results yet
      if (
        ["RUNNING", "FAILED", "TIMED_OUT", "ABORTED"].includes(overallStatus)
      ) {
        return (
          <div className="flex w-full justify-center text-slate-400">-</div>
        );
      }

      // Use colored badges: green for compliant, red for non-compliant
      const icon = isCompliant ? (
        <CheckIcon size={14} className="text-white" />
      ) : (
        <AlertTriangleIcon size={14} className="text-white" />
      );

      const className = isCompliant
        ? "bg-lime-600 hover:bg-lime-600"
        : "bg-red-600 hover:bg-red-600";

      const text = isCompliant ? i18n.t("common.yes") : i18n.t("common.no");

      return (
        <div className="flex w-full justify-center">
          <Badge className={cn(`${className} gap-1 text-white`)}>
            {icon}
            {text}
          </Badge>
        </div>
      );
    },
  },
];
