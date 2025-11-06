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

import { useAuthenticator } from "@aws-amplify/ui-react";
import { SparklesIcon, UserIcon } from "lucide-react";
// import { getGravatarUrl } from "@/lib/utils";

type AvatarProps = {
  avatarType: "human" | "bot";
  size: null | "user" | "small";
};

export default function Avatar({ avatarType, size }: AvatarProps) {
  const { user } = useAuthenticator((context) => [context.user]);

  const email = user?.username;
  const displayName = email || user?.username || "Guest";

  const sizeVariants = {
    default: "h-10 w-10 leading-10 text-lg",
    small: "h-8 w-8 leading-8 text-sm",
  };

  const sizeClasses =
    size !== null
      ? sizeVariants[size as keyof typeof sizeVariants]
      : sizeVariants.default;

  if (avatarType === "human") {
    // const gravatarUrl = getGravatarUrl(email);
    return (
      <div
        className={`${sizeClasses} ml-2 flex flex-none select-none overflow-hidden rounded-full`}
      >
        <div className="flex h-full w-full items-center justify-center bg-slate-800 text-slate-200 dark:bg-slate-600 dark:text-slate-950">
          <span className="text-center font-semibold">
            {displayName ? displayName.substring(0, 2).toUpperCase() : ""}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`${sizeClasses} flex flex-none select-none rounded-full
        ${
          avatarType && avatarType === "bot"
            ? "mr-2 bg-gradient-to-tr from-[#341478] via-[#7E34E2] to-[#3E8DFF]"
            : "ml-2 bg-slate-800 text-slate-200 dark:bg-slate-600 dark:text-slate-950"
        }`}
    >
      {avatarType === "bot" && (
        <SparklesIcon size={18} className="m-auto stroke-white" />
      )}

      {!avatarType && (
        <UserIcon size={18} className="m-auto stroke-slate-200" />
      )}
    </div>
  );
}
