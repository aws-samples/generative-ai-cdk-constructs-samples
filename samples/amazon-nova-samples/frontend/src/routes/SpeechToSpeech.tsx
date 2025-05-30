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

import { SpeechToSpeech as SpeechToSpeechComponent } from "@/components/speech-to-speech/SpeechToSpeech";

export default function SpeechToSpeech() {
  return (
    <div className="container mx-auto py-6 h-full">
      <h1 className="text-2xl font-bold mb-6">Speech-to-Speech Interface</h1>
      <div className="h-[calc(100vh-200px)]">
        <SpeechToSpeechComponent />
      </div>
    </div>
  );
}
