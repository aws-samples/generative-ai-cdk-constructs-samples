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

import { useLoaderData, Await, useRevalidator } from "react-router-dom";
import { Suspense } from "react";

import { columns } from "@/components/jobs/columns";
import {
  DataTable as JobsTable,
  DataTableSkeleton,
} from "@/components/jobs/data-table";
import { Input } from "@/components/ui/input";
import { createJob, uploadDocument } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { IconRefresh } from "@tabler/icons-react";
import { Job } from "@/types";

type JobsData = {
  jobs: Job[];
};

export default function Home() {
  const loaderData = useLoaderData() as JobsData;
  const revalidator = useRevalidator();

  const handleOnChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];

    if (file) {
      await uploadDocument(file, file?.name);
      await createJob(file?.name);

      revalidator.revalidate();
    }
  };

  return (
    <div>
      <div className="mb-3 flex justify-between ">
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={() => {
              revalidator.revalidate();
            }}
            disabled={revalidator.state === "loading"}
          >
            <span
              className={revalidator.state === "loading" ? "animate-spin" : ""}
            >
              <IconRefresh className="-scale-x-100" />
            </span>
          </Button>
        </div>
        <div className="grid gap-3">
          <Input id="document" type="file" onChange={handleOnChange} />
        </div>
      </div>

      <Suspense fallback={<DataTableSkeleton />}>
        <Await resolve={loaderData.jobs} errorElement={<p>Error</p>}>
          {(loadedData) => <JobsTable columns={columns} data={loadedData} />}
        </Await>
      </Suspense>
    </div>
  );
}
