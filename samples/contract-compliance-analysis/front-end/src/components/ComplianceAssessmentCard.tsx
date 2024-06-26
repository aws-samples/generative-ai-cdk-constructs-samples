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
import {
  IconAlertTriangle,
  IconCheck,
  IconEyeQuestion,
} from "@tabler/icons-react";
import {
  ComplianceStatus,
  ComplianceStatusData,
  Job,
  ImpactLevel,
  TotalComplianceByImpact,
} from "@/types";
import {
  COMPLIANCE_STATUSES,
  RISK_COLORS,
  RISK_LEVELS,
  IMPACT_COLORS,
  IMPACT_LEVELS,
} from "@/constants";

type ImpactCount = Record<ImpactLevel, ComplianceStatusData>;

function getImpactCountFromComplianceStatus(
  status: ComplianceStatus,
  data: TotalComplianceByImpact,
): ImpactCount {
  const { low, medium, high } = data;
  return {
    low: low[status],
    medium: medium[status],
    high: high[status],
  };
}

export default function ComplianceAssessmentCard() {
  const loaderData = useLoaderData() as { job: Job };
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between">
          Compliance matrix
        </CardTitle>
        <CardDescription>
            Clause types compliance distribution by impact level<br />
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
                <Header />
                <div className="grid gap-[2px]">
                  {Object.keys(COMPLIANCE_STATUSES).map((key) => {
                    const complianceStatus = key as ComplianceStatus;
                    const complianceData = getImpactCountFromComplianceStatus(
                      complianceStatus,
                      loadedData.total_compliance_by_impact,
                    );
                    return (
                      <Line
                        key={key}
                        complianceStatus={complianceStatus}
                        data={complianceData}
                      />
                    );
                  })}
                </div>
              </CardContent>
              <CardFooter className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500">
                  Matrix legend:
                </span>
                <div className="items center flex gap-4">
                  {Object.entries(RISK_LEVELS).map(([key, label]) => {
                    const level = key as ImpactLevel;
                    return (
                      <div key={key} className="flex items-center gap-2">
                        <div
                          key={key}
                          className={`h-2 w-2 justify-center rounded-full ${RISK_COLORS[level]}`}
                        ></div>
                        <span className="text-xs">
                          {label}
                          {key != "none" && " Risk"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </CardFooter>
            </>
          )}
        </Await>
      </Suspense>
    </Card>
  );
}

function Header() {
  return (
    <div className="flex text-sm text-slate-500">
      <div className="invisible w-10 items-center text-xs font-bold">
        Impact
      </div>

      <div className="flex w-full gap-[2px]">
        {Object.entries(IMPACT_LEVELS).map(([key, label]) => (
          <div
            key={key}
            className={`flex-1 rounded-sm py-1 text-center text-xs font-semibold ${
              IMPACT_COLORS[key as ImpactLevel]
            }`}
          >
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}

function Line({
  complianceStatus,
  data,
}: {
  complianceStatus: ComplianceStatus;
  data: ImpactCount;
}) {
  return (
    <div className="flex text-sm text-slate-500">
      <div className="flex w-10 items-center justify-center gap-2 text-xs font-semibold">
        <div className="absolute flex -rotate-90 items-center gap-2">
          {complianceStatus === "compliant" ? (
            <IconCheck size={20} className="text-lime-500" />
          ) : complianceStatus === "non_compliant" ? (
            <IconAlertTriangle size={20} className="text-amber-500" />
          ) : (
            <IconEyeQuestion size={20} className="text-slate-500" />
          )}

          {COMPLIANCE_STATUSES[complianceStatus]}
        </div>
      </div>

      <div className="grid flex-1 grid-cols-3 gap-[2px]">
        {Object.keys(IMPACT_LEVELS).map((key) => {
          const level = key as ImpactLevel;
          const { risk, quantity } = data[level];
          return (
            <div
              className={`col-span-1 flex gap-[2px] p-2 py-14 ${RISK_COLORS[risk]}`}
              key={level}
            >
              <div className="flex flex-1 items-center justify-center gap-1 truncate text-lg font-bold">
                {quantity == 0 ? (
                  <span className="text-xs font-normal">None</span>
                ) : (
                  <>
                    {quantity}
                    <span className="text-xs font-normal">
                      occurrence{quantity != 1 ? "s" : ""}
                    </span>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
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
