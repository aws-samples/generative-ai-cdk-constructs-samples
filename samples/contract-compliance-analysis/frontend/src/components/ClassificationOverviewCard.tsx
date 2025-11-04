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
import {
  AlertTriangleIcon,
  CheckIcon,
  FileQuestionIcon,
  FileTextIcon,
  GlassesIcon,
} from "lucide-react";
import { Job, ImpactLevel, TotalComplianceByImpact } from "@/lib/types";
import { IMPACT_LEVELS, EMPTY_TOTALS } from "@/lib/constants";
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

export default function ClassificationOverviewCard({
  jobPromise,
}: {
  jobPromise: Promise<Job>;
}) {
  const { t } = useTranslation();
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between">
          {t("job.classification.title")}
          {/* <IconInfoCircle /> */}
        </CardTitle>
        <CardDescription>{t("job.classification.description")}</CardDescription>
      </CardHeader>

      <Suspense
        fallback={
          <CardContent className="flex flex-col gap-2">
            <ComplianceCardSkeleton />
          </CardContent>
        }
      >
        <ResolvedOverview jobPromise={jobPromise} />
      </Suspense>
    </Card>
  );
}

function ResolvedOverview({ jobPromise }: { jobPromise: Promise<Job> }) {
  const loadedData = use(jobPromise);

  const complianceData =
    loadedData.checks?.guidelines?.metrics?.totalComplianceByImpact ??
    EMPTY_TOTALS;
  const unknownTotal =
    loadedData.checks?.guidelines?.metrics?.unknownTotal ?? 0;

  const totals = calculateTotals(complianceData);
  const { compliant, non_compliant, missing } = totals;
  const { t } = useTranslation();

  return (
    <>
      <CardContent>
        <div className="flex w-full flex-col justify-around gap-3 rounded-md border p-2">
          <span className="ml-3 text-center text-lg font-bold">
            {t("job.classification.guidelinesAlignment")}
          </span>
          <div className="flex">
            <Counter
              label={t("common.compliant")}
              count={compliant}
              icon={<CheckIcon size={24} className=" text-lime-500" />}
            />
            <Counter
              label={t("common.nonCompliant")}
              count={non_compliant}
              icon={<AlertTriangleIcon size={24} className=" text-amber-500" />}
            />
            <Counter
              label={t("common.missing")}
              count={missing}
              icon={<FileQuestionIcon size={24} className=" text-slate-500" />}
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
            <FileTextIcon size={16} />
            {t("job.classification.totalClauses")}:
          </span>
          <span>{loadedData.clauses?.length ?? 0}</span>
        </Badge>
        <Badge
          variant={"outline"}
          className="flex w-full justify-between text-slate-500"
        >
          <span className="flex items-center gap-1">
            <GlassesIcon size={16} />
            {t("job.classification.unknownClauses")}:
          </span>
          <span>{unknownTotal}</span>
        </Badge>
      </CardFooter>
    </>
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
      <div className="flex h-5 items-center justify-center text-wrap text-center text-[9px] font-bold uppercase text-slate-500">
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
        <Skeleton key={index} className="h-[60px] w-full bg-accent/80" />
      ))}

      <Skeleton className="mt-3 h-[20px] w-[30%] rounded-full bg-accent/80" />
    </div>
  );
}
