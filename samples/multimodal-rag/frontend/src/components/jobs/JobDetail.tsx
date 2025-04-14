import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Job } from "../../types";
import { useEffect, useState, Suspense } from "react";
import QATab from "./QATab";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "../ui/accordion";

interface JobDetailProps {
  job: Job;
}

type JsonValue = string | number | boolean | null | { [key: string]: JsonValue } | JsonValue[];

async function fetchContent(url: string): Promise<JsonValue> {
  try {
    const response = await fetch(url);
    const text = await response.text();
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  } catch (error) {
    console.error('Error fetching content:', error);
    return 'Error loading content';
  }
}

function JsonDisplay({ data }: { data: JsonValue }) {
  if (typeof data !== 'object' || data === null) {
    return <span className="text-sm">{JSON.stringify(data)}</span>;
  }

  return (
    <div className="space-y-2">
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="border rounded-lg">
          <Accordion type="single" collapsible>
            <AccordionItem value={key}>
              <AccordionTrigger className="px-4 hover:no-underline">
                <span className="font-semibold text-sm">{key}</span>
              </AccordionTrigger>
              <AccordionContent className="px-4 pb-4">
                {typeof value === 'object' && value !== null ? (
                  <JsonDisplay data={value} />
                ) : (
                  <span className="text-sm">{JSON.stringify(value)}</span>
                )}
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      ))}
    </div>
  );
}

export default function JobDetail({ job }: JobDetailProps) {
  const [standardOutput, setStandardOutput] = useState<JsonValue>(null);
  const [customOutput, setCustomOutput] = useState<JsonValue>(null);

  useEffect(() => {
    if (job.demo_metadata.result_file?.presigned_url) {
      fetchContent(job.demo_metadata.result_file.presigned_url)
        .then(content => setStandardOutput(content));
    }
    if (job.demo_metadata.custom_output_file?.presigned_url) {
      fetchContent(job.demo_metadata.custom_output_file.presigned_url)
        .then(content => setCustomOutput(content));
    }
  }, [job]);

  return (
    <div className="w-full h-full">
      <Tabs defaultValue="standard" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="standard">BDA Standard Output</TabsTrigger>
          <TabsTrigger value="custom">BDA Custom Output</TabsTrigger>
          <TabsTrigger value="qa">Q&A</TabsTrigger>
        </TabsList>

        <TabsContent value="standard" className="space-y-4">
          <div className="p-4">
            <div className="mb-4">
              <h4 className="font-semibold mb-2">Standard Output</h4>
              {standardOutput ? (
                typeof standardOutput === 'object' ? (
                  <JsonDisplay data={standardOutput} />
                ) : (
                  <pre className="whitespace-pre-wrap bg-gray-50 p-4 rounded-lg text-sm">
                    {standardOutput}
                  </pre>
                )
              ) : (
                'Loading...'
              )}
            </div>
            {job.result && (
              <>
                <div className="mb-4">
                  <h4 className="font-semibold mb-2">Summary</h4>
                  <p>{job.result.summary}</p>
                </div>

                {job.result.iab_categories && (
                  <div className="mb-4">
                    <h4 className="font-semibold mb-2">IAB Categories</h4>
                    {job.result.iab_categories.map((iab, index) => (
                      <p key={index}>{iab.category}</p>
                    ))}
                  </div>
                )}

                {job.result.content_moderation && (
                  <div className="mb-4">
                    <h4 className="font-semibold mb-2">Content Moderation</h4>
                    {job.result.content_moderation.map((cm, index) => (
                      <p key={index}>
                        {cm.type} ({Math.floor(cm.confidence * 100)}%)
                      </p>
                    ))}
                  </div>
                )}

                {job.result.text_lines && (
                  <div className="mb-4">
                    <h4 className="font-semibold mb-2">Text Lines</h4>
                    {job.result.text_lines.map((line, index) => (
                      <p key={index}>{line.text}</p>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </TabsContent>

        <TabsContent value="custom" className="space-y-4">
          <div className="p-4">
            {customOutput ? (
              typeof customOutput === 'object' ? (
                <JsonDisplay data={customOutput} />
              ) : (
                <pre className="whitespace-pre-wrap bg-gray-50 p-4 rounded-lg text-sm">
                  {String(customOutput)}
                </pre>
              )
            ) : (
              'Loading...'
            )}
          </div>
        </TabsContent>

        <TabsContent value="qa" className="space-y-4">
          <Suspense fallback={<div className="p-4">Loading Q&A interface...</div>}>
            <QATab jobId={job.id} />
          </Suspense>
        </TabsContent>

      </Tabs>
    </div>
  );
}
