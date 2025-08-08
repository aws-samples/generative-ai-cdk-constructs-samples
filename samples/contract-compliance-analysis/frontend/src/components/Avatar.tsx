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

import { IconMessageChatbot, IconUser } from "@tabler/icons-react";
import { useAuthenticator } from "@aws-amplify/ui-react";

type AvatarProps = {
  avatarType: "user" | "bot";
  size: null | "user" | "small";
};

export default function Avatar({ avatarType, size }: AvatarProps) {
  const {
    user: { username },
  } = useAuthenticator((context) => [context.user]);

  const sizeVariants = {
    default: "h-10 w-10 leading-10 text-lg",
    small: "h-8 w-8 leading-8 text-sm",
  };

  const sizeClasses =
    size !== null
      ? sizeVariants[size as keyof typeof sizeVariants]
      : sizeVariants.default;

  return (
    <div
      className={`${sizeClasses} flex flex-none select-none rounded-full
        ${
          avatarType && avatarType === "bot"
            ? "mr-2 bg-blue-600 dark:bg-blue-500"
            : "ml-2 bg-slate-800 text-slate-200 dark:bg-slate-600 dark:text-slate-950"
        }`}
    >
      {avatarType === "user" && (
        <span className="flex-1 text-center font-semibold">
          {username?.charAt(0).toUpperCase()}
        </span>
      )}

      {avatarType === "bot" && (
        <IconMessageChatbot className="m-auto stroke-blue-200" />
      )}

      {!avatarType && (
        <IconUser size={20} className="m-auto stroke-slate-200" />
      )}
    </div>
  );
}
