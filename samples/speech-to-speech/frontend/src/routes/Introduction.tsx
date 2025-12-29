export default function Introduction() {
    return (
        <div>
          <h1 className="text-2xl font-semibold mb-4">Introduction</h1>
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="mb-4">
              This demo showcases the Speech to Speech feature using Amazon Nova 2 Sonic, a next-generation speech-to-speech 
              foundation model that delivers industry-leading conversational quality and natural, real-time voice interactions.
            </p>
            <p className="mb-4">
              The Speech to Speech feature enables real-time conversational AI with natural turn-taking, allowing seamless 
              communication through voice. Nova 2 Sonic supports advanced features including crossmodal input (text and voice), 
              polyglot voices, and asynchronous tool calling.
            </p>
            <p className="mb-4">Follow these steps to get started:</p>
            <ol className="list-decimal list-inside mb-4 space-y-2">
              <li>Navigate to the Speech to Speech page.</li>
              <li>Configure Nova 2 Sonic features (optional):
                <ul className="list-disc list-inside ml-6 mt-1 space-y-1">
                  <li>Select Voice Activity Detection Sensitivity (High/Medium/Low) to control response timing</li>
                  <li>Choose a voice, including polyglot voices like "Tiffany" that can switch between languages</li>
                </ul>
              </li>
              <li>Enter a system prompt (optional) to customize the assistant's behavior.</li>
              <li>Click the "Start Streaming" button to begin capturing your voice.</li>
              <li>Speak clearly into your microphone - your speech will be transcribed in real-time.</li>
              <li>The assistant will automatically process your message and respond through speech.</li>
              <li><strong>Crossmodal Input:</strong> While streaming, you can type text messages in the text input field 
                to switch between voice and text input within the same session.</li>
              <li>Click "Stop Streaming" when you're finished.</li>
            </ol>
            <div className="mt-6 p-4 bg-blue-50 rounded-lg">
              <h3 className="font-semibold mb-2">Nova 2 Sonic Features:</h3>
              <ul className="list-disc list-inside space-y-1 text-sm">
                <li><strong>Configurable Turn-Taking:</strong> Adjust voice activity detection sensitivity for optimal response timing</li>
                <li><strong>Crossmodal Support:</strong> Switch between text and voice input during active sessions</li>
                <li><strong>Polyglot Voices:</strong> Use voices that can naturally switch between multiple languages</li>
                <li><strong>Asynchronous Tool Calling:</strong> Tools execute in the background while the model continues responding</li>
              </ul>
            </div>
            <p className="text-sm text-gray-500 mt-4">For further assistance, please refer to the documentation or open an issue on the GitHub repository.</p>
          </div>
        </div>
      );
}