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

import { IconAlertTriangle, IconCheck } from "@tabler/icons-react";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import { Badge } from "@/components/ui/badge";

interface ApprovedProps {
  approved: number;
  notApproved: number;
}

export default function Approved({ approved, notApproved }: ApprovedProps) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="group flex flex-none cursor-pointer items-center gap-1 rounded-full px-1">
            <Badge
              className="h-auto gap-1 bg-white pl-2 pr-1"
              variant={"outline"}
            >
              <IconCheck className="h-3 w-3 text-lime-500" />
              <span className="pr-2">{approved}</span>
            </Badge>
            <Badge
              className="h-auto gap-1 bg-white pl-2 pr-1"
              variant={"outline"}
            >
              <IconAlertTriangle className="h-3 w-3 text-amber-500" />
              <span className="pr-2">{notApproved}</span>
            </Badge>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <div className="flex flex-col gap-2 py-2">
            <span className="ml-2 text-xs text-gray-600">
              {approved} reviewed, {notApproved} pending review
            </span>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
