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

import { useParams, useLoaderData, Await } from "react-router-dom";
import { Suspense } from "react";
import { Job, ImpactLevel } from "@/types";
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
import {
  IconAlertTriangle,
  IconBulb,
  IconCheck,
  IconCheckbox,
  IconCornerDownRight,
  IconRobot,
  IconZoomQuestion,
} from "@tabler/icons-react";

import ComplianceAssessmentCard from "@/components/ComplianceAssessmentCard";
import RiskDistributionCard from "@/components/RiskDistributionCard";
import ClassificationOverviewCard from "@/components/ClassificationOverviewCard";
import { IMPACT_COLORS, IMPACT_LEVELS } from "@/constants";
// import { RiskClassificationSkeleton } from "@/components/ClassificationLevel";
// import ComplianceCount from "@/components/Compliance";

interface ClauseType {
  type_name: string;
  type_id: string;
  analysis: string;
  classification_analysis: string;
  compliant: boolean;
  level: string;
}

interface Clause {
  text: string;
  clause_number: string;
  types: ClauseType[];
}

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

export default function Jobs() {
  const params = useParams();
  const loaderData = useLoaderData() as { job: Job };

  return (
    <div className="grid grid-cols-12 gap-6">
      <div className="col-span-12 lg:col-span-7">
        <Card>
          <CardHeader>
            <CardTitle>
              <Suspense fallback={<Skeleton className="h-6 bg-slate-200" />}>
                <Await
                  resolve={loaderData.job}
                  errorElement={<p>An error ocurred while loading.</p>}
                >
                  {(loadedData) => (
                    <div className="flex justify-between gap-4">
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div className="truncate leading-relaxed">
                              {loadedData.filename}
                            </div>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>{loadedData.filename}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                      <Badge
                        className={`min-w-[120px] text-center ${
                          loadedData.needs_review
                            ? "bg-red-600 hover:bg-red-600"
                            : "bg-lime-600 hover:bg-lime-600"
                        }`}
                      >
                        {loadedData.needs_review ? (
                          <>
                            <IconAlertTriangle className="mr-1.5" size={18} />
                            <span className="w-full text-center">
                              Needs review
                            </span>
                          </>
                        ) : (
                          <>
                            <IconCheck className="mr-1.5" size={18} />
                            <span className="w-full text-center">
                              Seems compliant
                            </span>
                          </>
                        )}
                      </Badge>
                    </div>
                  )}
                </Await>
              </Suspense>
            </CardTitle>
            <CardDescription className="pt-2">
              <span className="mr-2 inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold text-foreground transition-colors">
                Job ID:
              </span>
              <span className="font-mono text-xs">{params.jobId}</span>
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            <Suspense fallback={<ClauseSkeleton />}>
              <Await resolve={loaderData.job} errorElement={<p>Error</p>}>
                {(loadedData) =>
                  loadedData.clauses.map(
                    (clause: Clause, clauseIdx: number) => {
                      const overallCompliance = countOverallCompliance(
                        clause.types,
                      );

                      const complianceByLevel = countComplianceByLevel(
                        clause.types,
                      );

                      return (
                        <div
                          key={clauseIdx}
                          className={`flex flex-col gap-3 rounded-md border border-l-[4px] p-3 text-sm shadow-sm ${
                            clause.types[0].type_id === "UNKNOWN"
                              ? "border-l-slate-300"
                              : overallCompliance.nonCompliant === 0
                              ? "border-l-lime-500"
                              : "border-l-amber-500"
                          }`}
                        >
                          <div
                            className={`whitespace-pre-line italic ${
                              clause.types[0].type_id === "UNKNOWN"
                                ? "text-slate-400"
                                : "text-slate-500"
                            }`}
                          >
                            {clause.text}
                          </div>

                          {clause.types[0].type_id === "UNKNOWN" ? (
                            <div className="flex items-center gap-1 text-xs italic text-slate-400">
                              <IconZoomQuestion
                                size={18}
                                className="text-slate-400"
                              />
                              Not matching any type from the guidelines
                            </div>
                          ) : (
                            <Collapsible>
                              <div className="flex justify-between">
                                <CollapsibleTrigger className="inline-flex h-9 items-center justify-center rounded-md border bg-background px-3 text-xs font-medium ring-offset-background transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=open]:bg-slate-800 data-[state=open]:text-white">
                                  <IconRobot size={18} className="mr-2" />
                                  Analysis
                                </CollapsibleTrigger>
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <div className="group flex flex-none cursor-pointer items-center gap-1">
                                        <span className="text-xs text-slate-500">
                                          Compliance:
                                        </span>
                                        <Badge
                                          className="h-auto gap-1.5 bg-white pl-2 pr-1"
                                          variant={"outline"}
                                        >
                                          <IconCheck
                                            className="text-lime-500"
                                            size={14}
                                          />
                                          <span className="pr-2">
                                            {overallCompliance.compliant}
                                          </span>
                                        </Badge>

                                        <Badge
                                          className="h-auto gap-1.5 bg-white pl-2 pr-1"
                                          variant={"outline"}
                                        >
                                          <IconAlertTriangle
                                            className="text-amber-500"
                                            size={14}
                                          />
                                          <span className="pr-2">
                                            {overallCompliance.nonCompliant}
                                          </span>
                                        </Badge>
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
                                                    IMPACT_COLORS[
                                                      level as ImpactLevel
                                                    ]
                                                  }`}
                                                >
                                                  {
                                                    IMPACT_LEVELS[
                                                      level as ImpactLevel
                                                    ]
                                                  }
                                                </Badge>
                                                <span className="ml-2 text-xs text-slate-600">
                                                  {
                                                    complianceByLevel[level]
                                                      .compliant
                                                  }{" "}
                                                  compliant
                                                  {complianceByLevel[level]
                                                    .compliant > 1 && "s"}
                                                  ,{" "}
                                                  {
                                                    complianceByLevel[level]
                                                      .nonCompliant
                                                  }{" "}
                                                  non-compliant
                                                  {complianceByLevel[level]
                                                    .nonCompliant > 1 && "s"}
                                                </span>
                                              </div>
                                            );
                                          })}
                                      </div>
                                    </TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                              </div>
                              <CollapsibleContent className="mt-3 rounded-md bg-slate-100 p-3">
                                <ul className="flex flex-col gap-6">
                                  {clause.types.map((type, index) => {
                                    return (
                                      <li
                                        className="flex flex-col gap-3"
                                        key={index}
                                      >
                                        <div>
                                          <div className="flex items-center justify-between">
                                            <Badge
                                              variant={"secondary"}
                                              className={`p-0 px-2 text-[11px] leading-6 ${
                                                IMPACT_COLORS[
                                                  type.level as ImpactLevel
                                                ]
                                              }`}
                                            >
                                              {
                                                IMPACT_LEVELS[
                                                  type.level as ImpactLevel
                                                ]
                                              }
                                            </Badge>
                                            <Badge
                                              variant={"secondary"}
                                              className={`h-auto px-2 text-[11px] text-white ${
                                                type.compliant
                                                  ? "bg-lime-600 hover:bg-lime-600"
                                                  : "bg-amber-500 hover:bg-amber-500"
                                              }`}
                                            >
                                              {type.compliant ? (
                                                <>
                                                  <IconCheck
                                                    size={14}
                                                    className="mr-1"
                                                  />
                                                  {`Compliant`}
                                                </>
                                              ) : (
                                                <>
                                                  <IconAlertTriangle
                                                    size={14}
                                                    className="mr-1"
                                                  />
                                                  {`Non-compliant`}
                                                </>
                                              )}
                                            </Badge>
                                          </div>
                                          <div className="mt-2 flex items-center gap-2 font-bold text-slate-700">
                                            <IconCornerDownRight />
                                            {type.type_id}: {type.type_name}
                                          </div>
                                        </div>
                                        {type.classification_analysis && (
                                          <div className="flex flex-col gap-2 rounded-md border bg-white p-3 text-xs text-slate-500">
                                            <div className="flex items-center gap-2 font-bold">
                                              <IconBulb className="w-5" />
                                              <span className="text-slate-800">
                                                Why does it fit this
                                                categorization?
                                              </span>
                                            </div>
                                            <div className="whitespace-pre-line">
                                              {type.classification_analysis}
                                            </div>
                                          </div>
                                        )}

                                        <div className="flex flex-col gap-3">
                                          <div className="flex flex-col gap-2 rounded-md border bg-white p-3 text-xs text-slate-500">
                                            <div className="flex items-center gap-2 font-bold">
                                              <IconCheckbox className="w-5" />
                                              <span className="text-slate-800">
                                                Compliance analysis:
                                              </span>
                                            </div>
                                            <div className="whitespace-pre-line">
                                              {type.analysis}
                                            </div>
                                          </div>
                                        </div>
                                      </li>
                                    );
                                  })}
                                </ul>
                              </CollapsibleContent>
                            </Collapsible>
                          )}
                        </div>
                      );
                    },
                  )
                }
              </Await>
            </Suspense>
          </CardContent>
        </Card>
      </div>

      <div className="col-span-12 flex flex-col gap-6 lg:col-span-5">
        <ClassificationOverviewCard />
        <ComplianceAssessmentCard />
        <RiskDistributionCard />
      </div>
    </div>
  );
}

export function Clause() {}

export function ClauseSkeleton({ rows = 7 }: { rows?: number }) {
  return (
    <div className="flex w-full flex-col items-center gap-4">
      {[...Array(rows)].map((_, index) => (
        <Skeleton key={index} className="h-36 w-full bg-slate-200" />
      ))}
    </div>
  );
}
