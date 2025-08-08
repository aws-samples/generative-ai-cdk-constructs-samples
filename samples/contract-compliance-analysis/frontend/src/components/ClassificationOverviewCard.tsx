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
  IconFileText,
  IconZoomQuestion,
} from "@tabler/icons-react";
import { Job, ImpactLevel, TotalComplianceByImpact } from "@/types";
import { IMPACT_LEVELS } from "@/constants";
import { Badge } from "./ui/badge";

type CalculatedTotals = {
  compliant: number;
  missing: number;
  non_compliant: number;
};
const calculateTotals = (
  totalComplianceByImpact: TotalComplianceByImpact,
): CalculatedTotals => {
  let totalCompliant = 0;
  let totalMissing = 0;
  let totalNonCompliant = 0;

  for (const level in IMPACT_LEVELS) {
    const { compliant, missing, non_compliant } =
      totalComplianceByImpact[level as ImpactLevel];
    totalCompliant += compliant.quantity;
    totalMissing += missing.quantity;
    totalNonCompliant += non_compliant.quantity;
  }

  return {
    compliant: totalCompliant,
    non_compliant: totalNonCompliant,
    missing: totalMissing,
  };
};

export default function ClassificationOverviewCard() {
  const loaderData = useLoaderData() as { job: Job };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between">
          Categorization overview
          {/* <IconInfoCircle /> */}
        </CardTitle>
        <CardDescription>
          Overall clause types distribution per guidelines alignment
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
          {(loadedData) => {
            const totals = calculateTotals(
              loadedData.total_compliance_by_impact,
            );
            const { compliant, non_compliant, missing } = totals;
            return (
              <>
                <CardContent>
                  <div className="flex w-full flex-col justify-around gap-3 rounded-md border p-2">
                    <span className="ml-3 text-center text-lg font-bold">
                      Guidelines alignment
                    </span>
                    <div className="flex">
                      <Counter
                        label={"Compliant"}
                        count={compliant}
                        icon={
                          <IconCheck size={24} className=" text-lime-500" />
                        }
                      />
                      <Counter
                        label={"Non-compliant"}
                        count={non_compliant}
                        icon={
                          <IconAlertTriangle
                            size={24}
                            className=" text-amber-500"
                          />
                        }
                      />
                      <Counter
                        label={"Missing"}
                        count={missing}
                        icon={
                          <IconEyeQuestion
                            size={24}
                            className=" text-slate-500"
                          />
                        }
                      />
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="flex flex-col gap-2">
                  <Badge
                    variant={"outline"}
                    className="flex w-full justify-between text-slate-500"
                  >
                    <span className="flex items-center gap-1">
                      <IconFileText size={16} />
                      Total clauses in this contract:
                    </span>
                    <span>{loadedData.clauses.length}</span>
                  </Badge>
                  <Badge
                    variant={"outline"}
                    className="flex w-full justify-between text-slate-500"
                  >
                    <span className="flex items-center gap-1">
                      <IconZoomQuestion size={16} />
                      Clauses not matching any type from the guidelines:
                    </span>
                    <span>{loadedData.unknown_total}</span>
                  </Badge>
                </CardFooter>
              </>
            );
          }}
        </Await>
      </Suspense>
    </Card>
  );
}

function Counter({
  label,
  count,
  icon,
}: {
  label: string;
  count: number;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex flex-1 flex-col">
      <div className="text-wrap flex h-5 items-center justify-center text-center text-[9px] font-bold uppercase text-slate-500">
        {label}
      </div>
      <div className="flex items-center justify-center gap-1.5 pb-1 pt-2 text-2xl font-bold">
        {icon}
        <span className="pr-2">{count}</span>
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
