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

import { Workbook } from "exceljs";
import { saveAs } from "file-saver";
import { Questionnaire } from "./types";

export async function generateXLSX(
  originalFile: string,
  jobId: string,
  questionnaireByTopic: Record<string, Questionnaire[]>,
) {
  const wb = new Workbook();
  wb.creator = "AnyCompany";
  wb.created = new Date();
  wb.modified = new Date();

  const sheet = wb.addWorksheet("Questionnaire");
  sheet.columns = [
    { header: "Question", key: "question", width: 100 },
    { header: "Answer", key: "answer", width: 100 },
    { header: "Topic", key: "topic", width: 30 },
  ];

  for (let topic of Object.keys(questionnaireByTopic)) {
    questionnaireByTopic[topic].forEach((questionnaire) => {
      sheet.addRow({
        question: questionnaire.question,
        answer: questionnaire.answer,
        topic: topic,
      });
    });
  }

  const year = wb.created.getFullYear();
  const month = `${
    wb.created.getMonth() < 10 ? "0" : ""
  }${wb.created.getMonth()}`;

  wb.xlsx
    .writeBuffer()
    .then((buffer) =>
      saveAs(
        new Blob([buffer]),
        `${originalFile}_${jobId}_${year}-${month}.xlsx`,
      ),
    )
    .catch((err) => console.log("Error writing excel export", err));
}
