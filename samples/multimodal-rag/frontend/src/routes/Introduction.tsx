
export default function Introduction() {
    return (
        <div>
          <h1 className="text-2xl font-semibold mb-4">Introduction</h1>
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="mb-4">
              This demo showcases the Amazon Bedrock multimodal features applied to media and advertising use cases, including Amazon Bedrock Data Automation (BDA). 
              It highlights several popular media applications, such as:
            </p>
            <ul className="list-disc list-inside mb-4">
              <li>BDA for video metadata extraction</li>
              <li>BDA for contextual advertising analysis</li>
              <li>BDA combined with Bedrock Knowledge Bases for a RAG-based chatbot</li>
            </ul>
            <p className="mb-4">Follow these steps to get started:</p>
            <ol className="list-decimal list-inside mb-4">
              <li>Navigate to the BDA control plane page and select an existing BDA project or create a new one.</li>
              <li>Go to the Home page and upload a file to initiate a new job. The table will automatically refresh to display the newly added job.</li>
              <li>To refresh the table manually, click the "sync" button located at the top of the Home page.</li>
              <li>Once a job completes successfully, click on the filename in the jobs table to view the job-specific details.</li>
            </ol>
            <p className="text-sm text-gray-500">For further assistance, please refer to the documentation or contact support.</p>
          </div>
        </div>
      );
}