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

import { useLoaderData, Await } from "react-router-dom";
import { Suspense, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

import { IconAlertTriangle, IconRobot } from "@tabler/icons-react";
import { Questionnaire } from "@/lib/types";
import Approved from "@/components/jobs/approved";
import Question, { QuestionsSkeleton } from "@/components/jobs/question";
import { generateXLSX } from "@/lib/excel";
import { approveQuestionnaire } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";

interface QuestionnaireDataType {
  questionnaire: Record<string, Questionnaire[]>;
  filename: string;
  job_id: string;
  start_date: string;
}

interface QuestionnaireLoaderType {
  data: QuestionnaireDataType;
}

interface ApprovedCounts {
  approved: number;
  notApproved: number;
}

function countApproved(arr: Questionnaire[]): ApprovedCounts {
  const approved = arr.reduce((r, n) => (n.approved ? r + 1 : r), 0);
  const notApproved = arr.length - approved;

  return {
    approved,
    notApproved,
  };
}

export default function Jobs() {
  const loaderData = useLoaderData() as QuestionnaireLoaderType;
  const { toast } = useToast();

  return (
    <div className="grid grid-cols-12 gap-6">
      <div className="col-span-12">
        <Suspense
          fallback={
            <div className="flex flex-col gap-2">
              <QuestionsSkeleton />
            </div>
          }
        >
          <Await
            resolve={loaderData.data}
            errorElement={
              <div className="flex flex-col gap-2">
                <IconAlertTriangle className="h-6 w-6" /> Error
              </div>
            }
          >
            {(loadedData: QuestionnaireDataType) => {
              const [questionnaireByTopic, setQuestionnaireByTopic] = useState<
                Record<string, Questionnaire[]>
              >(loadedData.questionnaire);

              const editQuestionnaire = (questionnaire: Questionnaire) => {
                const { topic, question_number } = questionnaire;

                let topicQuestions = [...questionnaireByTopic[topic]];
                const oldQuestionIndex = topicQuestions.findIndex(
                  (item: Questionnaire) =>
                    item.question_number === question_number,
                );

                topicQuestions[oldQuestionIndex] = questionnaire;

                setQuestionnaireByTopic({
                  ...questionnaireByTopic,
                  [topic]: [...topicQuestions],
                });
              };

              return (
                <div className="mb-6 flex flex-col gap-6">
                  <div className="flex flex-col gap-4 p-6">
                    <h1 className="text-3xl font-extrabold">{`${loadedData.filename}`}</h1>
                    <div className="flex items-center justify-between ">
                      <span className="align-middle text-lg font-normal">{`Job ID: ${loadedData.job_id}`}</span>
                      <div className="flex gap-4">
                        <Button
                          variant="outline"
                          onClick={() => {
                            approveQuestionnaire(loadedData.job_id);
                            toast({
                              title: "All answers have been approved.",
                              description: "Please refresh the page.",
                            });
                          }}
                          aria-label="Approve All"
                        >
                          Approve All
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => {
                            generateXLSX(
                              loadedData.filename,
                              loadedData.job_id,
                              questionnaireByTopic,
                            );
                          }}
                          aria-label="Generate XLSX"
                        >
                          Generate XLSX
                        </Button>
                      </div>
                    </div>
                  </div>
                  {Object.keys(questionnaireByTopic).map((topic) => (
                    <Card key={topic}>
                      <CardHeader>
                        <CardTitle className="flex justify-between">
                          <span className="w-full">{topic}</span>
                          <div className="flex w-full justify-end">
                            <Approved
                              {...countApproved(questionnaireByTopic[topic])}
                            />
                          </div>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="flex w-full flex-col gap-2">
                        <Collapsible id={`${topic}-questions`}>
                          <CollapsibleTrigger className="flex items-center gap-2 rounded-full bg-slate-700 px-2 py-1 pr-3 text-xs font-bold text-white hover:bg-slate-500">
                            <IconRobot className="w-4" />
                            Show/hide questions for topic
                          </CollapsibleTrigger>
                          <CollapsibleContent className="mt-3 rounded-md border p-3">
                            <ul className="flex flex-col gap-8">
                              {questionnaireByTopic[topic].map(
                                (question, index, arr) => (
                                  <>
                                    <Question
                                      id={`${question.job_id}#${question.question_number}`}
                                      questionnaire={question}
                                      editQuestionnaire={editQuestionnaire}
                                    />
                                    {index != arr.length - 1 ? <hr /> : null}
                                  </>
                                ),
                              )}
                            </ul>
                          </CollapsibleContent>
                        </Collapsible>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              );
            }}
          </Await>
        </Suspense>
      </div>
    </div>
  );
}
