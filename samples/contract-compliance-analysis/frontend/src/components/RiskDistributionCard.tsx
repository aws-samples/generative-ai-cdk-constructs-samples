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

import { Suspense } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { Skeleton } from "./ui/skeleton";
import { useLoaderData, Await } from "react-router-dom";
import { IconAlertTriangle, IconCheck } from "@tabler/icons-react";
import { Job, RiskLevel } from "@/types";
import { Badge } from "./ui/badge";
import { RISK_COLORS, RISK_LEVELS } from "@/constants";

export default function RiskDistributionCard() {
  const loaderData = useLoaderData() as { job: Job };
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between">
          Risk assessment
          {/* <IconInfoCircle /> */}
        </CardTitle>
        <CardDescription>
            Grouping of occurrences to determine contract risk

          {/*Contract risk classification by impact and compliance alignment*/}
        </CardDescription>
      </CardHeader>

      <Suspense
        fallback={
          <CardContent className="flex flex-col gap-2">
            <ComplianceCardSkeleton />
          </CardContent>
        }
      >
        <Await
          resolve={loaderData.job}
          errorElement={
            <CardContent className="flex flex-col gap-2">
              <IconAlertTriangle className="h-6 w-6" /> Error loading data
            </CardContent>
          }
        >
          {(loadedData) => (
            <>
              <CardContent className="grid gap-3">
                {Object.keys(RISK_LEVELS).map((key) => {
                  const level = key as RiskLevel;
                  return (
                    <div
                      key={key}
                      className="flex items-center justify-between rounded-sm border p-2 "
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded-sm p-2 text-xs font-bold ${RISK_COLORS[level]}`}
                        >
                          {RISK_LEVELS[level]}
                          {level != "none" && " Risk"}
                        </span>
                      </div>

                      <div className="flex gap-2">
                        {loadedData.total_clause_types_by_risk[level]
                          ?.threshold != undefined && (
                          <span className="rounded-full bg-slate-100 p-1 px-2 text-xs text-slate-500">
                            Tolerance:{" "}
                            {
                              loadedData.total_clause_types_by_risk[level]
                                ?.threshold
                            }
                          </span>
                        )}
                        <Badge variant="secondary">
                          {
                            loadedData.total_clause_types_by_risk[level]
                              .quantity
                          }
                          {` occurrence${
                            loadedData.total_clause_types_by_risk[level]
                              .quantity != 1
                              ? "s"
                              : ""
                          }`}
                        </Badge>
                      </div>
                    </div>
                  );
                })}
              </CardContent>
              <CardFooter className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500">
                  Risk assessment result:
                </span>
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
                      <span className="w-full text-center">Needs review</span>
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
              </CardFooter>
            </>
          )}
        </Await>
      </Suspense>
    </Card>
  );
}

export function ComplianceCardSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="flex w-full flex-col gap-2">
      {[...Array(rows)].map((_, index) => (
        <Skeleton key={index} className="h-[60px] w-full bg-slate-200" />
      ))}

      <Skeleton className="mt-3 h-[20px] w-[30%] rounded-full bg-slate-200" />
    </div>
  );
}
