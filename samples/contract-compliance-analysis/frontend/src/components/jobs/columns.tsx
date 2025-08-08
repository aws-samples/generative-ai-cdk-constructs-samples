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
import { IconFile } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import { ArrowUpDown } from "lucide-react";
import { Button } from "../ui/button";
import { Job } from "@/types";

export const columns: ColumnDef<Job>[] = [
  {
    accessorKey: "filename",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Filename
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      const { status, filename, id } = row.original;

      if (status === "SUCCEEDED") {
        return (
          <Link to={`/jobs/${id}`} className="flex items-center gap-2">
            <IconFile />
            <span className="font-medium text-blue-600">{filename}</span>
          </Link>
        );
      } else {
        return (
          <div className="flex items-center gap-2 text-slate-400">
            <IconFile />
            <span className="italic">{filename}</span>
          </div>
        );
      }
    },
  },
  {
    accessorKey: "start_date",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Created at
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      const rowDate = row.getValue("start_date");
      if (rowDate) {
        const date = new Date(rowDate as string);
        return date.toLocaleString();
      }
    },
  },
  {
    accessorKey: "end_date",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Finished at
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      const rowDate = row.getValue("end_date");
      if (rowDate) {
        const date = new Date(rowDate as string);
        return date.toLocaleString();
      }
    },
  },
  {
    accessorKey: "status",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Status
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      const status = row.getValue<string>("status");

      const statusDictionary: { [key: string]: string } = {
        RUNNING: "Processing",
        SUCCEEDED: "Finished",
        FAILED: "Failed",
        TIMED_OUT: "Failed",
        ABORTED: "Canceled",
      };

      const statusClassNames: { [key: string]: string } = {
        RUNNING: "bg-black hover:bg-black animate-pulse",
        SUCCEEDED: "bg-lime-600 hover:bg-lime-600",
        FAILED: "bg-red-600 hover:bg-red-600",
        TIMED_OUT: "bg-red-600 hover:bg-red-600",
        ABORTED: "bg-slate-600 hover:bg-slate-600",
      };

      return (
        <div className="flex justify-center">
          <Badge
            className={`h-auto py-0 text-[10px] uppercase ${statusClassNames[status]}`}
          >
            {statusDictionary[status]}
          </Badge>
        </div>
      );
    },
  },
  {
    accessorKey: "needs_review",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Needs review
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      const status = row.getValue<string>("status");
      const text = row.getValue<boolean>("needs_review") ? "Yes" : "No";
      return (
        <div className="flex justify-center">
          {!["FAILED", "TIMED_OUT"].includes(status) && (
            <Badge variant="outline">{text}</Badge>
          )}
        </div>
      );
    },
  },
];
