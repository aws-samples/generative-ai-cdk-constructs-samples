/**
 * Speech-to-Speech Page component for the NovaSonicSolution frontend
 */

import { SpeechToSpeech } from "@/components/speech-to-speech/SpeechToSpeech";

export default function SpeechToSpeechPage() {
  return (
    <div className="h-[calc(100vh-120px)]">
      <h1 className="text-2xl font-semibold mb-4">Speech to Speech</h1>
      <div className="h-[calc(100%-40px)]">
        <SpeechToSpeech />
      </div>
    </div>
  );
}