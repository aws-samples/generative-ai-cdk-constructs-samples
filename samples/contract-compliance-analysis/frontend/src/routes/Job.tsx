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
import { useParams } from "react-router";
import { use, Suspense, useEffect, useState } from "react";
import { Job, ImpactLevel, Clause as ClauseInterface } from "@/lib/types";
import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  // CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { getJob } from "@/lib/api";
import {
  AlertTriangleIcon,
  LightbulbIcon,
  CheckIcon,
  CheckSquareIcon,
  CornerDownRightIcon,
  SparklesIcon,
  ZoomOutIcon,
  ScaleIcon,
  FlaskConicalIcon,
  AlertCircleIcon,
} from "lucide-react";

import ComplianceAssessmentCard from "@/components/ComplianceAssessmentCard";
import RiskDistributionCard from "@/components/RiskDistributionCard";
import ClassificationOverviewCard from "@/components/ClassificationOverviewCard";
import { IMPACT_COLORS } from "@/lib/constants";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
// import { RiskClassificationSkeleton } from "@/components/ClassificationLevel";
// import ComplianceCount from "@/components/Compliance";

import { ClauseType } from "@/lib/types";
import { cn, isOverallCompliant } from "@/lib/utils";

interface LevelCounts {
  compliant: number;
  nonCompliant: number;
}

function countComplianceByLevel(
  arr: ClauseType[],
): Record<string, LevelCounts> {
  const levelCounts: Record<string, LevelCounts> = {};

  for (const item of arr) {
    const { level, compliant } = item;

    if (compliant) {
      if (levelCounts[level]) {
        levelCounts[level].compliant++;
      } else {
        levelCounts[level] = { compliant: 1, nonCompliant: 0 };
      }
    } else {
      if (levelCounts[level]) {
        levelCounts[level].nonCompliant++;
      } else {
        levelCounts[level] = { compliant: 0, nonCompliant: 1 };
      }
    }
  }

  return levelCounts;
}

interface ComplianceCounts {
  compliant: number;
  nonCompliant: number;
}

function countOverallCompliance(arr: ClauseType[]): ComplianceCounts {
  let compliantCount = 0;
  let nonCompliantCount = 0;

  for (const item of arr) {
    if (item.compliant) {
      compliantCount++;
    } else {
      nonCompliantCount++;
    }
  }

  return {
    compliant: compliantCount,
    nonCompliant: nonCompliantCount,
  };
}

/**
 * Determines if a clause is compliant across ALL check types (guidelines + legislation)
 */
function isClauseCompliantAcrossAllChecks(clause: ClauseInterface): boolean {
  // Check guidelines compliance (from clause.types)
  const guidelinesCompliance = countOverallCompliance(clause.types);
  const guidelinesCompliant = guidelinesCompliance.nonCompliant === 0;

  // Check legislation compliance (from additionalChecks)
  const legislationCompliant =
    clause.additionalChecks?.legislationCheck?.compliant ?? true;

  // Clause is compliant only if ALL checks pass
  return guidelinesCompliant && legislationCompliant;
}

/**
 * Get clause border color based on compliance hierarchy
 * Priority: Red (legislation issue) > Amber (guidelines issue) > Green (all compliant)
 */
function getClauseBorderColor(clause: ClauseInterface): string {
  // UNKNOWN clauses get gray
  if (clause.types[0].typeId === "UNKNOWN") {
    return "border-l-slate-300";
  }

  // Check if all compliant
  if (isClauseCompliantAcrossAllChecks(clause)) {
    return "border-l-lime-500"; // 🟢 Green: All good
  }

  // Check legislation compliance (higher priority)
  const legislationNonCompliant =
    clause.additionalChecks?.legislationCheck?.compliant === false;
  if (legislationNonCompliant) {
    return "border-l-red-500"; // 🔴 Red: Legislation issue (critical)
  }

  // Default: Guidelines non-compliant (lower priority)
  return "border-l-amber-500"; // 🟡 Amber: Guidelines issue (moderate)
}

export function Jobs() {
  const params = useParams();
  const jobId = params.jobId as string;
  const [jobPromise, setJobPromise] = useState<Promise<Job>>(() =>
    getJob(jobId),
  );
  const [clauseFilter, setClauseFilter] = useState<
    "all" | "compliant" | "non_compliant"
  >("all");
  const { t } = useTranslation();

  useEffect(() => {
    if (jobId) setJobPromise(getJob(jobId));
  }, [jobId]);

  return (
    <div className="flex flex-col">
      <div className="flex-1">
        <Suspense fallback={null}>
          <MockJobBanner jobPromise={jobPromise} />
        </Suspense>
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 lg:col-span-7">
            <Card>
              <CardHeader>
                <CardTitle>
                  <Suspense
                    fallback={<Skeleton className="h-6 bg-accent/80" />}
                  >
                    <ResolvedHeader jobPromise={jobPromise} />
                  </Suspense>
                </CardTitle>
                <CardDescription className="pt-2">
                  <span className="mr-2 inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold text-foreground transition-colors">
                    {t("job.idLabel")}
                  </span>
                  <span className="font-mono text-xs">{params.jobId}</span>
                </CardDescription>

                <div className="pt-3">
                  <div className="flex items-center gap-2 text-xs text-slate-600">
                    <span>{t("job.filters.filterClauses")}</span>
                    <Select
                      value={clauseFilter}
                      onValueChange={(value) =>
                        setClauseFilter(
                          value as "all" | "compliant" | "non_compliant",
                        )
                      }
                    >
                      <SelectTrigger
                        aria-label={t("job.filters.filterClauses")}
                        className="h-8"
                      >
                        <SelectValue placeholder={t("common.allClauses")} />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">{t("common.allClauses")}</SelectItem>
                        <SelectItem value="compliant">
                          {t("common.compliant")}
                        </SelectItem>
                        <SelectItem value="non_compliant">
                          {t("common.nonCompliant")}
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex flex-col gap-5">
                <Suspense fallback={<ClauseSkeleton />}>
                  <ResolvedClauses
                    jobPromise={jobPromise}
                    clauseFilter={clauseFilter}
                  />
                </Suspense>
              </CardContent>
            </Card>
          </div>

          <div className="col-span-12 flex flex-col gap-6 lg:col-span-5">
            <ClassificationOverviewCard jobPromise={jobPromise} />
            <ComplianceAssessmentCard jobPromise={jobPromise} />
            <RiskDistributionCard jobPromise={jobPromise} />
          </div>
        </div>
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

export function Clause() {}

export function ClauseSkeleton({ rows = 7 }: { rows?: number }) {
  return (
    <div className="flex w-full flex-col items-center gap-4">
      {[...Array(rows)].map((_, index) => (
        <Skeleton key={index} className="h-36 w-full bg-accent/80" />
      ))}
    </div>
  );
}

function ResolvedHeader({ jobPromise }: { jobPromise: Promise<Job> }) {
  const job = use(jobPromise);
  const { t } = useTranslation();
  const isCompliant = isOverallCompliant(job);

  return (
    <div className="flex justify-between gap-4">
      <div className="min-w-0 flex-1">
        <div className="truncate leading-relaxed">{job.jobDescription}</div>
        <Badge variant="secondary" className="text-xs">
          {job.documentS3Key.replace(/^.*\//, "")}
        </Badge>
      </div>
      <div className="flex items-center gap-2">
        <div
          className={cn(
            `flex h-12 min-w-[120px] grow-0 items-center rounded-full p-4 py-0 text-center text-sm text-white ${
              isCompliant
                ? "bg-lime-600 hover:bg-lime-600"
                : "bg-red-600 hover:bg-red-600"
            }`,
          )}
        >
          {isCompliant ? (
            <>
              <CheckIcon className="mr-1.5" size={18} />
              <span className="w-full text-center text-primary-foreground">
                {t("common.seemsCompliant")}
              </span>
            </>
          ) : (
            <>
              <AlertTriangleIcon className="mr-1.5" size={18} />
              <span className="w-full text-center text-primary-foreground">
                {t("common.nonCompliant")}
              </span>
            </>
          )}
        </div>

        {/* AI Disclaimer Tooltip */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <AlertCircleIcon
                size={16}
                className="cursor-help text-slate-400 hover:text-slate-600"
              />
            </TooltipTrigger>
            <TooltipContent>
              <div className="max-w-xs p-2">
                <p className="text-xs font-normal">
                  {t("aiDisclaimer.text")}{" "}
                  <a
                    href="https://aws.amazon.com/ai/responsible-ai/policy/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 underline hover:text-blue-300"
                  >
                    {t("aiDisclaimer.linkText")}
                  </a>
                </p>
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  );
}

function ResolvedClauses({
  jobPromise,
  clauseFilter,
}: {
  jobPromise: Promise<Job>;
  clauseFilter: "all" | "compliant" | "non_compliant";
}) {
  const loadedData = use(jobPromise);
  const clauses = loadedData.clauses ?? [];
  const { t } = useTranslation();
  return (
    <>
      {clauses
        .filter((clause: ClauseInterface) => {
          if (clauseFilter === "all") return true;
          const isCompliant = isClauseCompliantAcrossAllChecks(clause);
          return clauseFilter === "compliant" ? isCompliant : !isCompliant;
        })
        .map((clause: ClauseInterface, clauseIdx: number) => {
          const overallCompliance = countOverallCompliance(clause.types);
          const complianceByLevel = countComplianceByLevel(clause.types);
          const borderColor = getClauseBorderColor(clause);

          return (
            <div
              key={clauseIdx}
              className={`flex flex-col gap-3 rounded-md border border-l-[4px] p-3 text-sm shadow-sm ${borderColor}`}
            >
              <div
                className={`whitespace-pre-line italic ${
                  clause.types[0].typeId === "UNKNOWN"
                    ? "text-slate-400"
                    : "text-slate-500"
                }`}
              >
                {clause.text}
              </div>

              {clause.types[0].typeId === "UNKNOWN" ? (
                <div className="flex items-center gap-1 text-xs italic text-slate-400">
                  <ZoomOutIcon size={18} className="text-slate-400" />
                  {t("job.clauses.unknownType")}
                </div>
              ) : (
                <Collapsible>
                  <div className="flex justify-between">
                    <CollapsibleTrigger
                      data-testid={`clause-${clauseIdx}`}
                      className="inline-flex h-9 items-center justify-center rounded-md border bg-background px-3 text-xs font-medium ring-offset-background transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=open]:bg-slate-800 data-[state=open]:text-white"
                    >
                      <SparklesIcon size={18} className="mr-2" />
                      {t("job.clauses.analysis")}
                    </CollapsibleTrigger>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div className="group flex flex-none cursor-pointer items-center gap-1">
                            <span className="text-xs text-slate-500">
                              {t("job.clauses.complianceLabel")}
                            </span>
                            <Badge
                              className="h-auto gap-1.5 bg-background pl-2 pr-1"
                              variant={"outline"}
                            >
                              <CheckIcon className="text-lime-500" size={14} />
                              <span className="pr-2 text-primary">
                                {overallCompliance.compliant}
                              </span>
                            </Badge>

                            <Badge
                              className="h-auto gap-1.5 bg-background pl-2 pr-1"
                              variant={"outline"}
                            >
                              <AlertTriangleIcon
                                className="text-amber-500"
                                size={14}
                              />
                              <span className="pr-2 text-primary">
                                {overallCompliance.nonCompliant}
                              </span>
                            </Badge>

                            {/* Legislation Check Indicator - only show if legislation check exists */}
                            {clause.additionalChecks?.legislationCheck
                              ?.compliant !== undefined && (
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Badge
                                      className="h-auto gap-1.5 bg-background pl-2 pr-2"
                                      variant={"outline"}
                                    >
                                      <ScaleIcon
                                        className="mr-1 text-slate-500"
                                        size={12}
                                      />
                                      {clause.additionalChecks.legislationCheck
                                        .compliant ? (
                                        <CheckIcon
                                          className="text-lime-500"
                                          size={14}
                                        />
                                      ) : (
                                        <AlertTriangleIcon
                                          className="text-red-500"
                                          size={14}
                                        />
                                      )}
                                    </Badge>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <div className="flex items-center gap-2 py-2">
                                      <ScaleIcon
                                        className="text-slate-600"
                                        size={14}
                                      />
                                      <span className="text-xs font-semibold text-slate-600">
                                        {t("job.clauses.legislationCheck")}
                                      </span>
                                      <Badge
                                        variant={"secondary"}
                                        className={`h-auto px-2 text-[10px] ${
                                          clause.additionalChecks
                                            .legislationCheck.compliant
                                            ? "bg-lime-600 text-white hover:bg-lime-600"
                                            : "bg-red-600 text-white hover:bg-red-600"
                                        }`}
                                      >
                                        {clause.additionalChecks
                                          .legislationCheck.compliant ? (
                                          <>
                                            <CheckIcon
                                              size={10}
                                              className="mr-1"
                                            />
                                            {t("common.compliant")}
                                          </>
                                        ) : (
                                          <>
                                            <AlertTriangleIcon
                                              size={10}
                                              className="mr-1"
                                            />
                                            {t("common.nonCompliant")}
                                          </>
                                        )}
                                      </Badge>
                                    </div>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            )}
                          </div>
                        </TooltipTrigger>
                        <TooltipContent>
                          <div className="flex flex-col gap-2 py-2">
                            {Object.keys(complianceByLevel)
                              .sort()
                              .map((level) => {
                                return (
                                  <div key={level}>
                                    <Badge
                                      variant={"secondary"}
                                      className={`h-auto p-0 px-2 text-[11px] ${
                                        IMPACT_COLORS[level as ImpactLevel]
                                      }`}
                                    >
                                      {t(`job.compliance.impactLevel.${level}`)}
                                    </Badge>
                                    <span className="ml-2 text-xs text-slate-600">
                                      {t("job.clauses.compliantCount", {
                                        count:
                                          complianceByLevel[level].compliant,
                                      })}
                                      ,{" "}
                                      {t("job.clauses.nonCompliantCount", {
                                        count:
                                          complianceByLevel[level].nonCompliant,
                                      })}
                                    </span>
                                  </div>
                                );
                              })}
                          </div>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                  <CollapsibleContent
                    data-testid={`clause-${clauseIdx}-analysis`}
                    className="mt-3 rounded-md border bg-slate-50 p-3 text-foreground"
                  >
                    <ul className="flex flex-col gap-6">
                      {clause.types.map((type, index) => {
                        return (
                          <li className="flex flex-col gap-3" key={index}>
                            <div>
                              <div className="flex items-center justify-between">
                                <Badge
                                  variant={"secondary"}
                                  className={`p-0 px-2 text-[11px] leading-6 ${
                                    IMPACT_COLORS[type.level as ImpactLevel]
                                  }`}
                                >
                                  {t(
                                    `job.compliance.impactLevel.${type.level}`,
                                  )}
                                </Badge>
                                <Badge
                                  variant={"secondary"}
                                  className={`h-auto px-2 text-[11px] text-background ${
                                    type.compliant
                                      ? "bg-lime-600 hover:bg-lime-600"
                                      : "bg-amber-500 hover:bg-amber-500"
                                  }`}
                                >
                                  {type.compliant ? (
                                    <>
                                      <CheckIcon size={14} className="mr-1" />
                                      {t("common.compliant")}
                                    </>
                                  ) : (
                                    <>
                                      <AlertTriangleIcon
                                        size={14}
                                        className="mr-1"
                                      />
                                      {t("common.nonCompliant")}
                                    </>
                                  )}
                                </Badge>
                              </div>
                              <div className="mt-2 flex items-center gap-2 font-bold text-slate-600">
                                <CornerDownRightIcon />
                                {type.typeId}: {type.typeName}
                              </div>
                            </div>
                            {type.classificationAnalysis && (
                              <div className="flex flex-col gap-2 rounded-md border border-primary/10 bg-background p-3 text-xs text-slate-500">
                                <div className="flex items-center gap-2 font-bold text-slate-600">
                                  <LightbulbIcon className="w-5" />
                                  <span>{t("job.clauses.whyFits")}</span>
                                </div>
                                <div className="whitespace-pre-line">
                                  {type.classificationAnalysis}
                                </div>
                              </div>
                            )}

                            <div className="flex flex-col gap-3">
                              <div className="flex flex-col gap-2 rounded-md border border-primary/10 bg-background p-3 text-xs text-foreground">
                                <div className="flex items-center gap-2 font-bold text-slate-600">
                                  <CheckSquareIcon className="w-5" />
                                  <span>
                                    {t("job.clauses.complianceAnalysis")}
                                  </span>
                                </div>
                                <div className="whitespace-pre-line text-slate-500">
                                  {type.analysis}
                                </div>
                              </div>
                            </div>
                          </li>
                        );
                      })}

                      {/* Legislation Check Results */}
                      {clause.additionalChecks?.legislationCheck && (
                        <li className="flex flex-col gap-3">
                          <div className="flex flex-col gap-2 rounded-md border border-primary/10 bg-background p-3 text-xs text-foreground">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2 font-bold text-slate-600">
                                <ScaleIcon className="w-5" />
                                <span>{t("job.clauses.legislationCheck")}</span>
                              </div>
                              <Badge
                                variant={"secondary"}
                                className={`h-auto px-2 text-[11px] text-background ${
                                  clause.additionalChecks.legislationCheck
                                    .compliant
                                    ? "bg-lime-600 hover:bg-lime-600"
                                    : "bg-red-600 hover:bg-red-600"
                                }`}
                              >
                                {clause.additionalChecks.legislationCheck
                                  .compliant ? (
                                  <>
                                    <CheckIcon size={14} className="mr-1" />
                                    {t("common.compliant")}
                                  </>
                                ) : (
                                  <>
                                    <AlertTriangleIcon
                                      size={14}
                                      className="mr-1"
                                    />
                                    {t("common.nonCompliant")}
                                  </>
                                )}
                              </Badge>
                            </div>
                            {clause.additionalChecks.legislationCheck
                              .analysis && (
                              <div className="mt-2 whitespace-pre-line text-slate-500">
                                {
                                  clause.additionalChecks.legislationCheck
                                    .analysis
                                }
                              </div>
                            )}
                          </div>
                        </li>
                      )}
                    </ul>
                  </CollapsibleContent>
                </Collapsible>
              )}
            </div>
          );
        })}
    </>
  );
}

function MockJobBanner({ jobPromise }: { jobPromise: Promise<Job> }) {
  const job = use(jobPromise);
  const { t } = useTranslation();
  const isMockJob = job.contractType?.contractTypeId === "mock-contract";

  if (!isMockJob) return null;

  return (
    <>
      <Alert className="mb-4 flex items-center gap-2">
        <Badge className="gap-1 border border-amber-600 bg-amber-500 font-semibold text-amber-900 hover:bg-amber-500">
          <FlaskConicalIcon size={14} />
          {job.contractType?.name || "Mock Contract"}
        </Badge>
        <AlertDescription className="flex items-center text-xs text-muted-foreground">
          <span>{t("mockData.tooltip")}</span>
        </AlertDescription>
      </Alert>
    </>
  );
}
