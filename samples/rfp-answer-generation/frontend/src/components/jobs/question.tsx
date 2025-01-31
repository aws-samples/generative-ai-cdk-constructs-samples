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

import { useState } from "react";
import { IconCheckbox, IconEdit, IconX } from "@tabler/icons-react";
import { Button } from "../ui/button";
import { Questionnaire } from "@/lib/types";
import { editQuestionnaireEntry } from "@/lib/api";
import { Skeleton } from "../ui/skeleton";

interface QuestionProps {
  questionnaire: Questionnaire;
  id: string;
  editQuestionnaire: (questionnaire: Questionnaire) => void;
}

export default function Question({
  questionnaire,
  id,
  editQuestionnaire,
}: QuestionProps) {
  const [editing, setEditing] = useState(false);
  const [localEdit, setLocalEdit] = useState(questionnaire.answer);

  const handleOnChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setLocalEdit(event.target.value);
  };

  return (
    <li key={id} className="flex flex-col gap-4">
      <span className="text-lg font-bold ">{questionnaire.question}</span>
      {editing ? (
        <textarea
          id="edit-answer"
          value={localEdit}
          onChange={handleOnChange}
          rows={localEdit.match(/\n/g)?.length || 2}
          className="whitespace-pre-line break-words border-2 border-solid border-orange-200 p-3 text-sm font-normal focus:border-2 focus:border-solid focus:border-orange-400 focus:outline-none"
        ></textarea>
      ) : (
        <span className="whitespace-pre-line text-sm font-normal">
          {questionnaire.answer}
        </span>
      )}
      <div className="flex justify-end">
        {editing ? (
          <Button
            variant="ghost"
            onClick={() => {
              setEditing(false);
              setLocalEdit(questionnaire.answer);
            }}
            disabled={!editing}
            aria-label="Cancel edit"
          >
            <IconX className="-scale-x-100" />
          </Button>
        ) : (
          <Button
            variant="ghost"
            onClick={() => {
              setEditing(true);
            }}
            aria-label="Edit answer"
          >
            <IconEdit className="-scale-x-100" />
          </Button>
        )}
        <Button
          variant="ghost"
          onClick={async () => {
            await editQuestionnaireEntry({
              ...questionnaire,
              answer: localEdit,
              approved: true,
            });

            editQuestionnaire({
              ...questionnaire,
              answer: localEdit,
              approved: true,
            });

            setEditing(false);
          }}
          aria-label="Approve answer"
          disabled={questionnaire.approved && !editing}
        >
          <IconCheckbox className="-scale-x-100 stroke-green-700" />
        </Button>
      </div>
    </li>
  );
}

export function QuestionsSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="flex w-full flex-col gap-2">
      {[...Array(rows)].map((_, index) => (
        <Skeleton key={index} className="h-[60px] w-full bg-gray-200" />
      ))}

      <Skeleton className="mt-3 h-[20px] w-[30%] rounded-full bg-gray-200" />
    </div>
  );
}
