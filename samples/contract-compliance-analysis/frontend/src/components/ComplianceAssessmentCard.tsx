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
import { AlertTriangleIcon, CheckIcon, FileQuestionIcon } from "lucide-react";
import {
  ComplianceStatus,
  ComplianceAttributes,
  Job,
  ImpactLevel,
  TotalComplianceByImpact,
} from "@/lib/types";
import {
  RISK_COLORS,
  RISK_LEVELS,
  IMPACT_COLORS,
  IMPACT_LEVELS,
  EMPTY_TOTALS,
} from "@/lib/constants";

type ImpactCount = Record<ImpactLevel, ComplianceAttributes>;

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

export default function ComplianceAssessmentCard({
  jobPromise,
}: {
  jobPromise: Promise<Job>;
}) {
  const { t } = useTranslation();
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between">
          {t("job.compliance.matrixTitle")}
        </CardTitle>
        <CardDescription>
          {t("job.compliance.matrixDescription")}
          <br />
        </CardDescription>
      </CardHeader>

      <Suspense
        fallback={
          <CardContent className="flex flex-col gap-2">
            <ComplianceCardSkeleton />
          </CardContent>
        }
      >
        <ResolvedCompliance jobPromise={jobPromise} />
      </Suspense>
    </Card>
  );
}

function ResolvedCompliance({ jobPromise }: { jobPromise: Promise<Job> }) {
  const loadedData = use(jobPromise);
  const { t } = useTranslation();
  const totals =
    loadedData.checks?.guidelines?.metrics?.totalComplianceByImpact ??
    EMPTY_TOTALS;

  return (
    <>
      <CardContent className="grid gap-3">
        <Header />
        <div className="grid gap-[2px]">
          {["compliant", "non_compliant", "missing"].map((key) => {
            const complianceStatus = key as ComplianceStatus;
            const ComplianceStatus = getImpactCountFromComplianceStatus(
              complianceStatus,
              totals,
            );
            return (
              <Line
                key={key}
                complianceStatus={complianceStatus}
                data={ComplianceStatus}
              />
            );
          })}
        </div>
      </CardContent>
      <CardFooter className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500">
          {t("job.compliance.legend")}
        </span>
        <div className="items center flex gap-4">
          {Object.entries(RISK_LEVELS).map(([key]) => {
            const level = key as ImpactLevel;
            return (
              <div key={key} className="flex items-center gap-2">
                <div
                  key={key}
                  className={`h-2 w-2 justify-center rounded-full ${RISK_COLORS[level]}`}
                ></div>
                <span className="text-xs">
                  {t(`job.risk.level.${key}`)}
                  {key != "none" && " " + t("job.compliance.risk")}
                </span>
              </div>
            );
          })}
        </div>
      </CardFooter>
    </>
  );
}

function Header() {
  const { t } = useTranslation();
  return (
    <div className="flex text-sm text-slate-500">
      <div className="invisible w-10 items-center text-xs font-bold">
        {t("job.compliance.impact")}
      </div>

      <div className="flex w-full gap-[2px]">
        {Object.entries(IMPACT_LEVELS).map(([key]) => (
          <div
            key={key}
            className={`flex-1 rounded-sm py-1 text-center text-xs font-semibold ${
              IMPACT_COLORS[key as ImpactLevel]
            }`}
          >
            {t(`job.compliance.impactLevel.${key}`)}
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
  const { t } = useTranslation();
  return (
    <div className="flex text-sm text-slate-500">
      <div className="flex w-10 items-center justify-center gap-2 text-xs font-semibold">
        <div className="absolute flex -rotate-90 items-center gap-2">
          {complianceStatus === "compliant" ? (
            <CheckIcon size={20} className="text-lime-500" />
          ) : complianceStatus === "non_compliant" ? (
            <AlertTriangleIcon size={20} className="text-amber-500" />
          ) : (
            <FileQuestionIcon size={20} className="text-slate-500" />
          )}
          {t(`job.compliance.status.${complianceStatus}`)}
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
                  <span className="text-xs font-normal">
                    {t("common.none")}
                  </span>
                ) : (
                  <>
                    {quantity}
                    <span className="text-xs font-normal">
                      {t("common.occurrence", { count: quantity })}
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
        <Skeleton key={index} className="h-[60px] w-full bg-accent/80" />
      ))}

      <Skeleton className="mt-3 h-[20px] w-[30%] rounded-full bg-accent/80" />
    </div>
  );
}
