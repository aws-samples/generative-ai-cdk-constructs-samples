export default function Introduction() {
    return (
        <div>
          <h1 className="text-2xl font-semibold mb-4">Introduction</h1>
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="mb-4">
              This demo showcases the Speech to Speech translation feature using Amazon Nova multimodal capabilities.
            </p>
            <p className="mb-4">
              The Speech to Speech feature allows real-time translation of spoken language, enabling seamless communication
              across different languages.
            </p>
            <p className="mb-4">Follow these steps to get started:</p>
            <ol className="list-decimal list-inside mb-4">
              <li>Navigate to the Speech to Speech page.</li>
              <li>Click the "Start Streaming" button to begin capturing your voice.</li>
              <li>Speak clearly into your microphone.</li>
              <li>The system will translate your speech in real-time.</li>
              <li>Click "Stop Streaming" when you're finished.</li>
            </ol>
            <p className="text-sm text-gray-500">For further assistance, please refer to the documentation or contact support.</p>
          </div>
        </div>
      );
}