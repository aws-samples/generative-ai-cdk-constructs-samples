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

import { Suspense, use } from "react";
import { useTranslation } from "react-i18next";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { Skeleton } from "./ui/skeleton";
import { AlertTriangleIcon, CheckIcon } from "lucide-react";
import { Job, RiskLevel } from "@/lib/types";
import { Badge } from "./ui/badge";
import { RISK_COLORS, RISK_LEVELS } from "@/lib/constants";

export default function RiskDistributionCard({
  jobPromise,
}: {
  jobPromise: Promise<Job>;
}) {
  const { t } = useTranslation();
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between">
          {t("job.risk.title")}
          {/* <IconInfoCircle /> */}
        </CardTitle>
        <CardDescription>
          {t("job.risk.description")}
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
        <ResolvedRisk jobPromise={jobPromise} />
      </Suspense>
    </Card>
  );
}

function ResolvedRisk({ jobPromise }: { jobPromise: Promise<Job> }) {
  const { t } = useTranslation();
  const loadedData = use(jobPromise);
  const riskData = loadedData.checks.guidelines.metrics!.totalClauseTypesByRisk;

  return (
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
                  {t(`job.risk.level.${level}`)}
                  {level != "none" && ` ${t("job.compliance.risk")}`}
                </span>
              </div>

              <div className="flex gap-2">
                {riskData[level]?.threshold != undefined && (
                  <span className="rounded-full bg-slate-100 p-1 px-2 text-xs text-slate-500">
                    {t("job.risk.tolerance")} {""}
                    {riskData[level].threshold}
                  </span>
                )}
                <Badge variant="secondary">
                  {riskData[level]?.quantity || 0}
                  {` ${t("common.occurrence", { count: riskData[level]?.quantity || 0 })}`}
                </Badge>
              </div>
            </div>
          );
        })}
      </CardContent>
      <CardFooter className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500">
          {t("job.risk.complianceStatusLabel")}
        </span>
        <Badge
          className={`min-w-[120px] text-center ${
            !loadedData.checks.guidelines.compliant
              ? "bg-red-600 hover:bg-red-600"
              : "bg-lime-600 hover:bg-lime-600"
          }`}
        >
          {!loadedData.checks.guidelines.compliant ? (
            <>
              <AlertTriangleIcon className="mr-1.5" size={18} />
              <span className="w-full text-center">
                {t("job.risk.exceedsRiskTolerance")}
              </span>
            </>
          ) : (
            <>
              <CheckIcon className="mr-1.5" size={18} />
              <span className="w-full text-center">
                {t("job.risk.withinRiskTolerance")}
              </span>
            </>
          )}
        </Badge>
      </CardFooter>
    </>
  );
}

export function ComplianceCardSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="flex w-full flex-col gap-2">
      {[...Array(rows)].map((_, index) => (
        <Skeleton key={index} className="h-[60px] w-full bg-accent/80" />
      ))}

      <Skeleton className="mt-3 h-[20px] w-[30%] rounded-full bg-accent/80" />
    </div>
  );
}
