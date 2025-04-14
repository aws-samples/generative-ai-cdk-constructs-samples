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
      id: "filename", // Add this id for the filter to work
      accessorKey: "demo_metadata.file.s3_key",
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
        const job_status = row.original.demo_metadata.job_status;
        const filename = row.original.demo_metadata.file.s3_key;
        const id = row.original.id;

        if (job_status === "COMPLETED") {
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
      id: "modality",
      accessorKey: "demo_metadata.modality",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Modality
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => {

        const modality = row.original.demo_metadata.modality.toUpperCase();
        
        const modalityDictionary: { [key: string]: string } = {
            DOCUMENT: "Document",
            VIDEO: "Video",
            IMAGE: "Image",
            AUDIO: "Audio",
          };
  
          const modalityClassNames: { [key: string]: string } = {
            DOCUMENT: "bg-cyan-600 hover:bg-cyan-600",
            VIDEO: "bg-violet-600 hover:bg-violet-600",
            IMAGE: "bg-orange-600 hover:bg-orange-600",
            AUDIO: "bg-yellow-600 hover:bg-yellow-600",
          };

        return (
            <div className="flex justify-center">
              <Badge
                className={`h-auto py-0 text-[10px] uppercase ${modalityClassNames[modality]}`}
              >
                {modalityDictionary[modality]}
              </Badge>
            </div>
          );
      },
    },
    {
      accessorKey: "demo_metadata.requested_at",
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
        const date = row.original.demo_metadata.requested_at;
        if (date) {
          return new Date(date).toLocaleString();
        }
      },
    },
    {
      accessorKey: "demo_metadata.completed_at",
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
        const date = row.original.demo_metadata.completed_at;
        if (date) {
          return new Date(date).toLocaleString();
        }
      },
    },
    {
      accessorKey: "demo_metadata.job_status",
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
        const status = row.original.demo_metadata.job_status;

        const statusDictionary: { [key: string]: string } = {
          PROCESSING: "Processing",
          CUSTOM_PARSING: "Parsing",
          COMPLETED: "Finished",
          FAILED_BDA: "Failed_BDA",
          FAILED_KB_INPUT: "Failed_kb",
        };

        const statusClassNames: { [key: string]: string } = {
          PROCESSING: "bg-black hover:bg-black animate-pulse",
          CUSTOM_PARSING: "bg-black hover:bg-black animate-pulse",
          COMPLETED: "bg-lime-600 hover:bg-lime-600",
          FAILED_KB_INPUT: "bg-red-600 hover:bg-red-600",
          FAILED_BDA: "bg-red-600 hover:bg-red-600",
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
    }
];